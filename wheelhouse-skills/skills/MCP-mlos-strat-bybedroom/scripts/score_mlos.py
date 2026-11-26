#!/usr/bin/env python3
"""Score a single market's MLOS strategy from summarized Wheelhouse market data.

Usage:
    python score_mlos.py input.json [--out-dir DIR] [--final]

--final: score with whatever data exists (no NEEDS_DATA exit). Missing months are skipped and
listed; a season missing lead time borrows the nearest group's or holds its far-out value; a Low
season missing average-performer data is held at the floor.

Reads the summary JSON assembled from the MCP execute blocks (schema in
references/input-schema.md) and writes:
    <out>/mlos_report.md   season tables, threshold comparison, 1-night flags, rationale facts
    <out>/mlos_plan.json   machine-readable rule plan (API shapes), one block per bedroom group
Prints the report to stdout as well.

Pure standard library. All rules are deterministic so two runs on the same data agree.
"""
import json
import os
import sys

RUNGS = [7, 14, 30, 60, 90, 120]
STEP_CAPS = {"high": 4, "shoulder": 3, "low": 1}
FIRST_STEP_TARGET = {"high": 0.35, "shoulder": 0.50, "low": 0.65}
BAR_OFFSET = {"high": 0.0, "shoulder": 0.05, "low": 0.10}
PROFILES = {"protective": 0.55, "balanced": 0.60, "open": 0.65}
HIGH_IDX, LOW_IDX = 1.20, 0.85
WEEKEND_PREMIUM = 1.15
THU_POSITION = 0.75
SHORT_PRESSURE = 0.40
ONE_NIGHT_FLAG = 0.07
MAX_ABOVE_FLOOR = 4
BORDERLINE = 0.05          # within 5 pts of the bar
MIN_CELL_BOOKINGS = 10     # own bookings needed in a group/season to use them
MIN_SHORT_STAYS = 8        # own short stays needed to judge step timing
MIN_GROUP_BOOKINGS = 40    # gate 1: trailing-year bookings for a group to qualify
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # input order
# API day_of_week_values order is Sunday-first
API_ORDER = [6, 0, 1, 2, 3, 4, 5]  # API index -> input weekday index


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def avg_pmf(pmfs):
    n = max(len(p) for p in pmfs)
    out = []
    for i in range(n):
        out.append(mean([p[i] if i < len(p) else 0.0 for p in pmfs]))
    return out


def share_ge(pmf, n):
    return sum(pmf[n:]) if n < len(pmf) else 0.0


def nights_at_risk(pmf, n):
    tot = sum(k * p for k, p in enumerate(pmf) if k >= 1)
    lost = sum(k * p for k, p in enumerate(pmf) if 1 <= k < n)
    return lost / tot if tot else 0.0


def classify_seasons(index):
    months = sorted(index)
    rp = {m: (index[m]["revpar"] if "revpar" in index[m] else index[m]["occ"] * index[m]["adr"]) for m in months}
    avg = mean(list(rp.values()))
    seasons = {"high": [], "shoulder": [], "low": []}
    idx = {}
    for m in months:
        r = rp[m] / avg
        idx[m] = round(r, 2)
        s = "high" if r >= HIGH_IDX else ("low" if r <= LOW_IDX else "shoulder")
        seasons[s].append(m)
    return seasons, idx


def month_num(m):
    return int(m[5:7])


def weekend_profile(weekday_occ, months):
    rows = [weekday_occ[m] for m in months if m in weekday_occ]
    if not rows:
        return None
    d = [mean([r[i] for r in rows]) for i in range(7)]
    base = mean([d[6], d[0], d[1], d[2]])  # Sun-Wed
    wknd = mean([d[4], d[5]])  # Fri/Sat
    days = [4, 5]
    pos = (d[3] - base) / (wknd - base) if wknd > base else 0
    if pos >= THU_POSITION:
        days = [3, 4, 5]
    ratio = mean([d[i] for i in days]) / base if base else 1.0
    return {"weekend_days": days, "ratio": round(ratio, 2), "split": ratio >= WEEKEND_PREMIUM,
            "thu_position": round(pos, 2)}


def far_out(pmf_hi, pmf_avg, season, T, floor):
    bar = T + BAR_OFFSET[season]
    best = floor
    for n in range(floor + 1, floor + MAX_ABOVE_FLOOR + 1):
        ok = share_ge(pmf_hi, n) >= bar
        if season == "low" and pmf_avg is not None:
            ok = ok and share_ge(pmf_hi, n) >= share_ge(pmf_avg, n)
        if ok:
            best = n
    return best, bar


def schedule(n, floor, season, lead_within, pmf_hi, shift=0):
    """Return list of (rung_or_None, value). First entry rung None = far-out value."""
    if n <= floor:
        return [(None, floor)]
    steps = min(n - floor, STEP_CAPS[season])
    values = []
    for k in range(1, steps + 1):
        values.append(int(round(n - (n - floor) * k / steps)))
    target = FIRST_STEP_TARGET[season]
    i = None
    for j, r in enumerate(RUNGS):
        if lead_within.get(str(r), 0) >= target:
            i = j
            break
    if i is None:
        i = len(RUNGS) - 1
    if 1 - share_ge(pmf_hi, n) > SHORT_PRESSURE:
        i = min(i + 1, len(RUNGS) - 1)
    i = max(0, min(i + shift, len(RUNGS) - 1))
    sched = [(None, n)]
    for k, v in enumerate(values):
        j = i - k
        if j < 0:
            # out of rungs: merge into the last (closest) rung
            sched[-1] = (sched[-1][0], v)
        else:
            sched.append((RUNGS[j], v))
    return sched


def cell(v, floor, wk):
    if wk and wk["split"] and v > floor:
        return {"weekend": v, "weekday": max(floor, v - 1)}
    return {"all": v}


def fmt(c):
    return "{} / {}".format(c["weekend"], c["weekday"]) if "weekend" in c else str(c["all"])


def value_at(sched, days_out):
    """Value applying at a lead time of days_out (narrowest rung containing it wins)."""
    v = sched[0][1]
    for r, val in sched[1:]:
        if days_out <= r:
            v = val
    return v


def dow_values(c, wk):
    if "all" in c:
        return None
    arr = []
    for api_i in range(7):
        wi = API_ORDER[api_i]
        arr.append(c["weekend"] if wi in wk["weekend_days"] else c["weekday"])
    return arr


def rule_body(c, wk):
    dv = dow_values(c, wk)
    return {"day_of_week_values": dv} if dv else {"value": c["all"]}


def merge_rules(rules):
    merged = []
    for r in rules:
        key = json.dumps({k: v for k, v in r.items() if k != "months"}, sort_keys=True)
        for m in merged:
            if m["_key"] == key:
                m["months"] = sorted(set(m["months"]) | set(r["months"]))
                break
        else:
            r2 = dict(r)
            r2["_key"] = key
            merged.append(r2)
    for m in merged:
        m.pop("_key")
    return merged


def portfolio_rows(pf, g, months):
    ms = set(months)
    return [r for r in pf.get("rows", []) if str(r[0]) == g and r[1] in ms]


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if n == 0 else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    data = json.load(open(args[0]))
    out_dir = "."
    if "--out-dir" in args:
        out_dir = args[args.index("--out-dir") + 1]
    os.makedirs(out_dir, exist_ok=True)
    final = "--final" in args   # proceed with whatever data exists; never ask for more

    p = data.get("params", {})
    floor = int(p.get("floor", 2))
    profile = p.get("profile", "balanced")
    T = float(p.get("T", PROFILES.get(profile, 0.60)))
    one = p.get("one_night", {"opt_in": False})
    abs_min = 1 if one.get("opt_in") else floor

    seasons, idx = classify_seasons(data["season_index"])
    if p.get("season_override"):
        seasons = p["season_override"]
    wk = {s: weekend_profile(data["weekday_occ"], ms) for s, ms in seasons.items()}

    groups = data["groups"]
    gorder = sorted(groups, key=lambda g: (int(g.rstrip("+")), g))
    results = {}
    flags = []
    needs = []
    pf = data.get("portfolio")
    skipped = []
    elig = data.get("portfolio_eligibility")
    for g in gorder:
        gd = groups[g]
        res = {}
        for s, ms in seasons.items():
            mrows = [gd["months"][m] for m in ms if m in gd["months"]]
            if not mrows:
                skipped.append("{}BR {}".format(g, s))
                continue
            hi = avg_pmf([r["los_high"] for r in mrows])
            arows = [r["los_avg"] for r in mrows if "los_avg" in r]
            av = avg_pmf(arows) if arows else None
            lrows = [x["lead_high_within"] for x in mrows if "lead_high_within" in x]
            lead = {str(r): mean([x.get(str(r)) for x in lrows]) for r in RUNGS} if lrows else None
            gnotes = []
            if s == "low" and av is None:
                if not final:
                    needs.append({"group": g, "season": s, "months": ms, "pull": "los_avg"})
                else:
                    gnotes.append("average-performer data missing - openness test not run, held at floor")
                    hi_for_low = None
            comp = {name: far_out(hi, av, s, t, floor)[0] for name, t in PROFILES.items()}
            if s == "low" and av is None and final:
                comp = {name: floor for name in PROFILES}
            if lead is None and max(comp.values()) > floor:
                if not final:
                    needs.append({"group": g, "season": s, "months": ms, "pull": "lead_high"})
                    continue
                donor = None
                for g2 in sorted(gorder, key=lambda x: abs(int(x.rstrip("+")) - int(g.rstrip("+")))):
                    rows2 = [gd2 for gd2 in [groups[g2]["months"].get(m) for m in ms] if gd2 and "lead_high_within" in gd2]
                    if g2 != g and rows2:
                        donor = g2
                        lead = {str(r): mean([x["lead_high_within"].get(str(r)) for x in rows2]) for r in RUNGS}
                        break
                gnotes.append("lead time missing - borrowed from {}BR".format(donor) if donor else
                              "lead time missing - no step-down, far-out value held")
            n, bar = far_out(hi, av, s, T, floor)
            if s == "low" and av is None and final:
                n = floor
            reasons = []
            if n > floor:
                if len(set(comp.values())) > 1 or abs(share_ge(hi, n) - bar) <= BORDERLINE:
                    reasons.append("borderline")
                if s == "high":
                    reasons.append("high-season timing")
            shift, pnote = 0, None
            if reasons and pf is not None and any(str(r[0]) == g for r in pf.get("rows", [])):
                rows = portfolio_rows(pf, g, ms)
                if len(rows) < MIN_CELL_BOOKINGS:
                    pnote = "own bookings: {} (too few to use)".format(len(rows))
                else:
                    own_ge = sum(1 for r in rows if r[2] >= n) / len(rows)
                    notes = []
                    if "borderline" in reasons:
                        if own_ge >= 0.999:
                            notes.append("no own stays under {} nights - inconclusive (current rules may block them)".format(n))
                        elif own_ge < share_ge(hi, n) - BORDERLINE:
                            notes.append("own {}+ share {:.0%} vs market high performers {:.0%} - lowered to {}".format(
                                n, own_ge, share_ge(hi, n), n - 1))
                            n -= 1
                        else:
                            notes.append("own {}+ share {:.0%} - confirms {}".format(n, own_ge, n))
                    if n > floor:
                        short = [r[3] for r in rows if r[2] < n]
                        first = schedule(n, floor, s, lead or {}, hi)
                        r1 = first[1][0] if len(first) > 1 else None
                        if len(short) >= MIN_SHORT_STAYS and r1:
                            md = median(short)
                            if md > r1:
                                shift = 1
                                notes.append("own short stays book {:.0f} days out (median) - first step moved one rung earlier".format(md))
                            else:
                                notes.append("own short stays book {:.0f} days out (median) - step at {} days confirmed".format(md, r1))
                        elif r1:
                            notes.append("only {} own short stays - timing not judged".format(len(short)))
                    pnote = "own bookings: {}; ".format(len(rows)) + "; ".join(notes)
            sched = schedule(n, floor, s, lead or {}, hi, shift) if (lead or n <= floor) else [(None, n)]
            missing = [m for m in ms if m not in gd["months"]]
            if missing:
                gnotes.append("months missing (failed pulls): " + ", ".join(missing))
            res[s] = {
                "far_out": n, "bar": bar, "schedule": sched, "profiles": comp,
                "refine": reasons, "portfolio_note": pnote, "data_notes": gnotes,
                "share_ge": {k: round(share_ge(hi, k), 3) for k in range(2, 6)},
                "share_ge_avg": {k: round(share_ge(av, k), 3) for k in range(2, 6)} if av else None,
                "one_night": round(hi[1], 3) if len(hi) > 1 else None,
                "nights_at_risk": round(nights_at_risk(hi, n), 3) if n > floor else 0.0,
                "lead_within": {k: round(v, 3) for k, v in (lead or {}).items() if v is not None},
            }
        for m, r in sorted(gd["months"].items()):
            one_share = r["los_high"][1] if len(r["los_high"]) > 1 else 0
            if one_share >= ONE_NIGHT_FLAG:
                flags.append((g, m, round(one_share, 3)))
        results[g] = res

    if needs:
        print("NEEDS_DATA " + json.dumps(needs))
        print("Pull these with Block C (pass 2) and re-run the scorer.")
        sys.exit(3)

    # ---------- report ----------
    L = []
    mk = data.get("market", {})
    L.append("# MLOS strategy — {} (market {})".format(mk.get("name", ""), mk.get("id", "")))
    L.append("")
    L.append("Profile: **{}** (bar T = {:.0%}; Shoulder +5 pts, Low +10 pts). Data: trailing {} months.".format(
        profile, T, len(data["season_index"])))
    L.append("")
    one_txt = "not opted in"
    if one.get("opt_in"):
        one_txt = "opted in for months {} within {} days".format(one.get("months"), one.get("days_before", 7))
    flag_groups = {}
    for g, m, v in flags:
        flag_groups.setdefault(g, []).append(m[5:7])
    ftxt = "; ".join("{}BR months {}".format(g, ",".join(ms)) for g, ms in flag_groups.items()) or "none"
    L.append("**Applies to all seasons:** absolute minimum stay {} · gap fill down to {} · 1-night stays {} "
             "(opportunity flags, high-performer 1-night share ≥ {:.0%}: {})".format(abs_min, abs_min, one_txt, ONE_NIGHT_FLAG, ftxt))
    L.append("")
    L.append("Cells read **weekend / weekday**; a single number applies to all days.")
    names = {"high": "High season", "shoulder": "Shoulder", "low": "Low season"}
    for s in ["high", "shoulder", "low"]:
        ms = seasons.get(s, [])
        if not ms:
            continue
        L.append("")
        mlabel = ", ".join(sorted({str(month_num(m)) for m in ms}, key=int))
        w = wk.get(s)
        wtxt = ""
        if w:
            wtxt = " · weekend = {} (premium {}×{})".format(
                "/".join(WEEKDAY_NAMES[i] for i in w["weekend_days"]), w["ratio"], "" if w["split"] else ", no split")
        L.append("## {} (months {}){}".format(names[s], mlabel, wtxt))
        L.append("")
        rungs = sorted({r for g in gorder if s in results[g] for r, _ in results[g][s]["schedule"] if r},
                       reverse=True)
        bounds = []
        if not rungs:
            bounds = [("All", 10 ** 6)]
        else:
            bounds.append(("{}+".format(rungs[0] + 1), 10 ** 6))
            for a, b in zip(rungs, rungs[1:]):
                bounds.append(("{}–{}".format(b + 1, a), a))
            bounds.append(("0–{}".format(rungs[-1]), rungs[-1]))
        hdr = "| Days before stay | " + " | ".join("{}BR".format(g) for g in gorder if s in results[g]) + " |"
        L.append(hdr)
        L.append("|" + "---|" * (1 + sum(1 for g in gorder if s in results[g])))
        for label, d in bounds:
            row = [label]
            for g in gorder:
                if s not in results[g]:
                    continue
                v = value_at(results[g][s]["schedule"], d)
                row.append(fmt(cell(v, floor, w)))
            L.append("| " + " | ".join(row) + " |")
        L.append("")
        L.append("Evidence (high performers, season average):")
        for g in gorder:
            if s not in results[g]:
                continue
            r = results[g][s]
            avg3 = r["share_ge_avg"][3] if r["share_ge_avg"] else None
            L.append("- {}BR: books 3+ nights {:.0%} (average performers {}); 4+ {:.0%}; 1-night {:.0%}; "
                     "far-out {} vs bar {:.0%}; nights at risk at far-out {:.0%}; {}.".format(
                         g, r["share_ge"][3], "{:.0%}".format(avg3) if avg3 is not None else "not pulled", r["share_ge"][4],
                         r["one_night"] or 0, r["far_out"], r["bar"], r["nights_at_risk"],
                         ("booked within 30 days {:.0%}, within 60 {:.0%}".format(r["lead_within"]["30"], r["lead_within"]["60"])
                          if "30" in r["lead_within"] else "lead time not pulled (season at the floor)")))
            for dn in r.get("data_notes", []):
                L.append("  - Data note ({}BR): {}".format(g, dn))
            if r.get("portfolio_note"):
                L.append("  - Portfolio check ({}BR): {}".format(g, r["portfolio_note"]))
    L.append("")
    cands = [(g, s, results[g][s]["refine"]) for g in gorder for s in ["high", "shoulder", "low"]
             if s in results[g] and results[g][s]["refine"]]
    if pf is None:
        L.append("## Optional refinement with your own bookings")
        L.append("")
        if not cands:
            L.append("No borderline or high-season cells - the market data settles every recommendation.")
        else:
            L.append("Cells your own reservations could sharpen:")
            for g, s, why in cands:
                L.append("- {}BR {}: {}".format(g, names[s].lower(), ", ".join(why)))
            if elig:
                ok = {g: e for g, e in elig.items() if e.get("bookings", 0) >= MIN_GROUP_BOOKINGS and
                      any(c[0] == g for c in cands)}
                if ok:
                    lst = sum(e["listings"] for e in ok.values())
                    calls = sum(e["listings"] + e["bookings"] // 100 for e in ok.values())
                    L.append("")
                    L.append("Eligible: {} ({} listings with real booking history). Estimated cost: ~{} calls. Opt in to run it.".format(
                        ", ".join("{}BR".format(g) for g in ok), lst, calls))
                else:
                    L.append("")
                    L.append("No group has enough real booking history (≥ {} bookings in the trailing year) - refinement not available.".format(MIN_GROUP_BOOKINGS))
        L.append("")
    L.append("## Threshold comparison (far-out MLOS, Low / Shoulder / High)")
    L.append("")
    L.append("| Profile | " + " | ".join("{}BR".format(g) for g in gorder) + " |")
    L.append("|" + "---|" * (1 + len(gorder)))
    for name, t in PROFILES.items():
        row = ["{} ({:.0%})".format(name, t)]
        for g in gorder:
            vals = [str(results[g][s]["profiles"][name]) if s in results[g] else "–" for s in ["low", "shoulder", "high"]]
            row.append(" / ".join(vals))
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("Season index (RevPAR vs annual mean): " + ", ".join("{} {}".format(m, v) for m, v in idx.items()))
    if skipped:
        L.append("")
        L.append("**Not scored (no data pulled):** " + ", ".join(skipped))
    report = "\n".join(L)

    # ---------- plan ----------
    plan = {"market": mk, "profile": profile, "T": T, "floor": floor,
            "seasons": {s: sorted({month_num(m) for m in ms}) for s, ms in seasons.items()},
            "replace_scope": ["global", "day_of_week", "monthly", "time_based", "gap", "min_min_stay"],
            "preserve": ["seasonal", "event", "custom", "adjacency", "apply_gap_night_rules_to_overrides"],
            "groups": {}}
    for g in gorder:
        rules = [{"type": "global", "value": floor},
                 {"type": "gap", "gap_enabled": True, "value": abs_min}]
        for s in ["high", "shoulder", "low"]:
            if s not in results[g]:
                continue
            sched = results[g][s]["schedule"]
            w = wk.get(s)
            months = sorted({month_num(m) for m in seasons[s]})
            far = cell(sched[0][1], floor, w)
            if far != {"all": floor}:
                rules.append(dict({"type": "monthly", "months": months, "step": True}, **rule_body(far, w)))
                for r, v in sched[1:]:
                    rules.append(dict({"type": "time_based", "months": months, "days_before": r},
                                      **rule_body(cell(v, floor, w), w)))
        if one.get("opt_in"):
            rules.append({"type": "time_based", "months": one.get("months", []),
                          "days_before": one.get("days_before", 7), "value": 1})
        rules = rules[:2] + merge_rules(rules[2:])
        plan["groups"][g] = {
            "bedrooms": g,
            "min_stays_enabled": True,
            "min_min_stay": abs_min,
            "minimum_stay_rules_v3": rules,
        }
    evidence = {
        "market": mk, "profile": profile, "T": T, "floor": floor, "abs_min": abs_min,
        "one_night": one, "one_night_flags": flags,
        "seasons": {s: sorted({month_num(m) for m in ms}) for s, ms in seasons.items()},
        "season_index": idx,
        "weekend": wk,
        "groups": {g: {s: {k: v for k, v in r.items()} for s, r in res.items()} for g, res in results.items()},
        "refine_candidates": [[g, s, why] for g in gorder for s in ["high", "shoulder", "low"]
                              if s in results[g] and results[g][s]["refine"]],
        "portfolio_eligibility": elig, "portfolio_applied": pf is not None,
        "skipped": skipped,
        "monthly": {g: {m: {k: v for k, v in r.items() if k in ("los_high", "los_avg")}
                        for m, r in sorted(groups[g]["months"].items())} for g in gorder},
    }
    json.dump(evidence, open(os.path.join(out_dir, "mlos_evidence.json"), "w"), indent=1)
    open(os.path.join(out_dir, "mlos_report.md"), "w").write(report)
    json.dump(plan, open(os.path.join(out_dir, "mlos_plan.json"), "w"), indent=2)
    print(report)


if __name__ == "__main__":
    main()
