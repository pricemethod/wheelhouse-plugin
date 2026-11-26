#!/usr/bin/env python3
"""Render the MLOS recommendation as a Wheelhouse-style HTML report.

Usage:
    python render_report.py OUT_DIR --group 2 [--today 2026-11-20] [--out report.html]

Reads OUT_DIR/mlos_plan.json and OUT_DIR/mlos_evidence.json (written by score_mlos.py) and writes
a single self-contained HTML page: a 12-month min-stay chart evaluated from the proposed rules,
a condensed "Minimum stays" rules panel laid out like Wheelhouse, season tables with a short
reason for each, and the threshold comparison / 1-night / refinement notes.
Standard library only; the page uses no external scripts.
"""
import datetime as dt
import html
import json
import os
import sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SEASON_NAME = {"high": "High season", "shoulder": "Shoulder", "low": "Low season"}
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def e(x):
    return html.escape(str(x))


def pct(x):
    return "{:.0%}".format(x) if x is not None else "n/a"


def month_list(ms):
    return ", ".join(MONTHS[m - 1] for m in ms)


def rule_value(rule, api_dow):
    if "day_of_week_values" in rule and rule["day_of_week_values"]:
        return rule["day_of_week_values"][api_dow]
    return rule.get("value")


def min_stay_on(day, today, rules, abs_min):
    api_dow = (day.weekday() + 1) % 7
    out = (day - today).days
    best = None
    tb = [r for r in rules if r["type"] == "time_based" and day.month in r.get("months", range(1, 13))
          and "days_before" in r and out <= r["days_before"]]
    for r in sorted(tb, key=lambda r: r["days_before"]):
        v = rule_value(r, api_dow)
        if v is not None:
            best = v
            break
    if best is None:
        for r in rules:
            if r["type"] == "monthly" and day.month in r["months"]:
                v = rule_value(r, api_dow)
                if v is not None:
                    best = v
                    break
    if best is None:
        for r in rules:
            if r["type"] == "global":
                best = r["value"]
    return max(best or 0, abs_min)


BUCKETS = ["1", "2", "3", "4", "5+"]


def market_by_month(monthly):
    """month number -> {"avg": mean LOS, "shares": [1, 2, 3, 4, 5+]} from high-performer PMFs."""
    out = {}
    for m, r in (monthly or {}).items():
        p = r.get("los_high")
        if not p:
            continue
        tot = sum(p[1:]) or 1.0
        avg = sum(k * v for k, v in enumerate(p) if k >= 1) / tot
        sh = [(p[1] + p[0]) if len(p) > 1 else 0, p[2] if len(p) > 2 else 0, p[3] if len(p) > 3 else 0,
              p[4] if len(p) > 4 else 0, sum(p[5:])]
        t = sum(sh) or 1.0
        out[int(m[5:7])] = {"avg": round(avg, 2), "shares": [round(x / t, 3) for x in sh]}
    return out


def chart_svg(series, today, abs_min, seasons, mkt):
    W, L, R, T, H1, B = 1000, 34, 40, 14, 230, 26
    H = T + H1 + B
    n = len(series)
    ymax = max([v for _, v in series] + [abs_min] + [d["avg"] for d in mkt.values()]) + 1
    ymax = max(int(ymax + 0.999), 4)
    x = lambda i: L + (W - L - R) * i / (n - 1)
    y = lambda v: T + H1 * (1 - v / ymax)
    yp = lambda f: T + H1 * (1 - f)          # share axis (right), 0-100%
    dx = (W - L - R) / (n - 1)
    parts = []
    month_season = {}
    for s, ms in seasons.items():
        for m in ms:
            month_season[m] = s
    segs, start = [], 0
    for i in range(1, n + 1):
        if i == n or series[i][0].month != series[start][0].month:
            segs.append((series[start][0].month, start, i - 1))
            start = i
    # season bands
    bands, start = [], 0
    for i in range(1, n + 1):
        if i == n or month_season.get(series[i][0].month) != month_season.get(series[start][0].month):
            s = month_season.get(series[start][0].month)
            if s:
                bands.append('<rect class="band band-{}" x="{:.1f}" y="{}" width="{:.1f}" height="{}"/>'.format(
                    s, x(start), T, x(i - 1) - x(start) + dx, H1))
                if i - start > 20:
                    bands.append('<text class="band-label" x="{:.1f}" y="{}">{}</text>'.format(
                        x(start) + 4, T + 11, SEASON_NAME[s]))
            start = i
    parts.append('<g id="bands">{}</g>'.format("".join(b for b in bands if b.startswith("<rect"))))
    # market mix: stacked area through month midpoints, flat to the edges
    if mkt:
        pts = [((x(a) + x(b) + dx) / 2, mkt[m]["shares"]) for m, a, b in segs if m in mkt]
        if pts:
            pts = [(L, pts[0][1])] + pts + [(W - R, pts[-1][1])]
            layers = []
            for bi in range(5):
                lo = [(px, sum(sh[:bi])) for px, sh in pts]
                hi = [(px, sum(sh[:bi + 1])) for px, sh in pts]
                d = "M" + " L".join("{:.1f},{:.1f}".format(px, yp(f)) for px, f in hi)
                d += " L" + " L".join("{:.1f},{:.1f}".format(px, yp(f)) for px, f in reversed(lo)) + " Z"
                layers.append('<path class="mix mix-{}" d="{}"/>'.format(bi, d))
            ticks = "".join('<text class="axis axis-r" x="{}" y="{:.1f}">{}%</text>'.format(W - R + 6, yp(f) + 3, int(f * 100))
                            for f in (0, 0.25, 0.5, 0.75, 1))
            parts.append('<g id="mixLayer">{}{}</g>'.format("".join(layers), ticks))
    step = 2 if ymax > 6 else 1
    for v in range(0, int(ymax) + 1, step):
        parts.append('<line class="grid" x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(L, W - R, y(v), y(v)))
        parts.append('<text class="axis" x="{}" y="{:.1f}">{}</text>'.format(L - 6, y(v) + 3, v))
    parts.append('<g id="bandLabels">{}</g>'.format("".join(b for b in bands if b.startswith("<text"))))
    for i, (d, _) in enumerate(series):
        if d.day == 1:
            parts.append('<text class="axis axis-x" x="{:.1f}" y="{}">{} {}</text>'.format(
                x(i), H - 8, MONTHS[d.month - 1], str(d.year)[2:]))
    if mkt:
        pts = []
        for m, a, b in segs:
            if m in mkt:
                pts.append("M{:.1f},{:.1f}H{:.1f}".format(x(a), y(mkt[m]["avg"]), x(b) + dx))
        parts.append('<g id="avgLayer"><path class="mkt" d="{}"/></g>'.format("".join(pts)))
    parts.append('<line class="absmin" x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(L, W - R, y(abs_min), y(abs_min)))
    parts.append('<text class="absmin-label" x="{}" y="{:.1f}">Abs. min</text>'.format(L + 4, y(abs_min) + 12))
    pts = []
    for i, (d, v) in enumerate(series):
        pts.append(("M{:.1f},{:.1f}" if i == 0 else "H{:.1f}V{:.1f}").format(x(i), y(v)))
    pts.append("H{:.1f}".format(W - R))
    parts.append('<path class="line" d="{}"/>'.format("".join(pts)))
    parts.append('<line id="cursor" class="cursor" x1="0" x2="0" y1="{}" y2="{}" visibility="hidden"/>'.format(T, T + H1))
    parts.append('<circle id="dot" class="dot" r="4" cx="0" cy="0" visibility="hidden"/>')
    return ('<svg id="chart" data-mix="off" data-avg="on" viewBox="0 0 {} {}" role="img" aria-label="Proposed minimum stay by date, with optional market overlays">'
            '{}</svg>').format(W, H, "".join(parts)), (W, H, L, R, T, H1, ymax)


def day_boxes(vals):
    cells = []
    for i, d in enumerate(DAYS):
        v = vals[i] if vals else None
        cells.append('<div class="dow"><span class="dow-name">{}</span><span class="box{}">{}</span></div>'.format(
            d, " box-empty" if v is None else "", "" if v is None else "{} nights".format(v)))
    return '<div class="dows">{}</div>'.format("".join(cells))


def month_chips(ms):
    return '<div class="chips">{}</div>'.format("".join(
        '<span class="chip{}">{}</span>'.format(" on" if i + 1 in ms else "", m) for i, m in enumerate(MONTHS)))


def rule_vals(r):
    if r.get("day_of_week_values"):
        return r["day_of_week_values"]
    return [r.get("value")] * 7


def section(title, count_txt, body, open_=True, help_txt=None):
    h = ' <span class="help" title="{}">?</span>'.format(e(help_txt)) if help_txt else ""
    return ('<details class="rule"{}><summary><span class="rule-title">{}</span>{}'
            '<span class="count">{}</span></summary><div class="rule-body">{}</div></details>').format(
        " open" if open_ else "", e(title), h, e(count_txt), body)


def season_reason(s, r, wk, floor):
    n, bar = r["far_out"], r["bar"]
    sg = {int(k): v for k, v in r["share_ge"].items()}
    sga = {int(k): v for k, v in (r.get("share_ge_avg") or {}).items()}
    parts = []
    if n > floor:
        share = sg.get(n)
        wkd = ""
        if wk and wk.get("split"):
            wkd = " on weekends ({}), {} on other days".format(
                "/".join(WEEKDAY_NAMES[i] for i in wk["weekend_days"]), max(floor, n - 1))
        parts.append("High performers book {}+ nights {} of the time (bar {}), so {} nights holds far out{}.".format(
            n, pct(share), pct(bar), n, wkd))
        steps = [st for st in r["schedule"][1:] if st[0]]
        if steps:
            r1 = steps[0][0]
            parts.append("{} of bookings arrive within {} days, so it opens up from {} days out.".format(
                pct(r["lead_within"].get(str(r1))), r1, r1))
    else:
        nxt = sg.get(floor + 1)
        parts.append("Only {} of high-performer bookings run {}+ nights (bar {}), so this season stays at the {}-night floor.".format(
            pct(nxt), floor + 1, pct(bar), floor))
    if s == "low" and sga:
        a = sga.get(max(n, floor + 1))
        h = sg.get(max(n, floor + 1))
        if a is not None and h is not None:
            if h < a:
                parts.append("Average performers book longer ({} vs {}) - the winners take the shorter stays.".format(pct(a), pct(h)))
            else:
                parts.append("High performers book longer than average performers ({} vs {}).".format(pct(h), pct(a)))
    for dn in r.get("data_notes") or []:
        parts.append("Data note: {}.".format(dn))
    if r.get("portfolio_note"):
        parts.append("Your bookings: {}.".format(r["portfolio_note"]))
    return " ".join(parts)


def season_table(r, wk, floor):
    sched = r["schedule"]
    rungs = sorted([st[0] for st in sched[1:] if st[0]], reverse=True)

    def at(d):
        v = sched[0][1]
        for rr, val in sched[1:]:
            if rr and d <= rr:
                v = val
        return v

    def fmt(v):
        if wk and wk.get("split") and v > floor:
            return "{} / {}".format(v, max(floor, v - 1))
        return str(v)
    rows = []
    if not rungs:
        rows.append(("All dates", fmt(sched[0][1])))
    else:
        rows.append(("{}+ days out".format(rungs[0] + 1), fmt(at(10 ** 6))))
        for a, b in zip(rungs, rungs[1:]):
            rows.append(("{}–{} days".format(b + 1, a), fmt(at(a))))
        rows.append(("Within {} days".format(rungs[-1]), fmt(at(rungs[-1]))))
    return "".join('<tr><td>{}</td><td class="num">{}</td></tr>'.format(e(a), e(b)) for a, b in rows)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    out_dir = a[0]
    g = a[a.index("--group") + 1] if "--group" in a else None
    today = dt.date.fromisoformat(a[a.index("--today") + 1]) if "--today" in a else dt.date.today()
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(out_dir, "mlos_report.html")
    plan = json.load(open(os.path.join(out_dir, "mlos_plan.json")))
    ev = json.load(open(os.path.join(out_dir, "mlos_evidence.json")))
    if g is None:
        g = list(plan["groups"])[0]
    gp = plan["groups"][g]
    rules = gp["minimum_stay_rules_v3"]
    abs_min = gp["min_min_stay"]
    floor = plan["floor"]
    seasons = {s: ms for s, ms in ev["seasons"].items() if ms}
    series = [(today + dt.timedelta(days=i), min_stay_on(today + dt.timedelta(days=i), today, rules, abs_min))
              for i in range(366)]
    mkt = market_by_month((ev.get("monthly") or {}).get(g))
    svg, geo = chart_svg(series, today, abs_min, seasons, mkt)
    mk = ev["market"].get("name", "")

    glob = [r for r in rules if r["type"] == "global"]
    monthly = [r for r in rules if r["type"] == "monthly"]
    tbased = sorted([r for r in rules if r["type"] == "time_based"], key=lambda r: -r["days_before"])
    gap = [r for r in rules if r["type"] == "gap"]

    mbody = "".join('<div class="row">{}{}</div>'.format(month_chips(r["months"]), day_boxes(rule_vals(r))) for r in monthly) \
        or '<p class="muted">None - the default applies.</p>'
    tbody = "".join('<div class="row"><div class="row-head">Within <b>{}</b> days of today</div>{}{}</div>'.format(
        r["days_before"], month_chips(r["months"]), day_boxes(rule_vals(r))) for r in tbased) \
        or '<p class="muted">None.</p>'
    rules_html = "".join([
        '<div class="rule rule-flat"><div class="rule-title">Default</div><span class="box wide">{} nights</span></div>'.format(
            glob[0]["value"] if glob else floor),
        section("Day of week rules", "0 values",
                '<p class="muted">Not used. Weekend and weekday values live inside the monthly and time-based rules so each season can differ.</p>',
                open_=False),
        section("Monthly rules", "{} values".format(len(monthly)), mbody,
                help_txt="Sets the far-out minimum stay for each season's months."),
        section("Time-based rules", "{} values".format(len(tbased)), tbody,
                help_txt="Lowers the minimum stay as dates get close; the narrowest window wins."),
        section("Season rules", "unchanged", '<p class="muted">Left as you have them. Use these for your own exceptions.</p>', open_=False),
        section("Event rules", "unchanged", '<p class="muted">Left as you have them. Event rules still win over this structure on their dates.</p>', open_=False),
        section("Date-specific overrides", "unchanged", '<p class="muted">Left as you have them.</p>', open_=False),
        section("Adjacency rules", "unchanged", '<p class="muted">Left as you have them.</p>', open_=False),
        section("Gap night rules", "Enabled" if gap else "Disabled",
                '<p>Open runs between bookings can be booked down to <b>{} nights</b>.</p>'.format(gap[0]["value"]) if gap else ""),
        '<div class="rule rule-flat"><div class="rule-title">Absolute minimum stay</div><span class="box wide">{} nights</span></div>'.format(abs_min),
    ])

    seasons_html = []
    gres = ev["groups"].get(g, {})
    for s in ["high", "shoulder", "low"]:
        if s not in gres or s not in seasons:
            continue
        r = gres[s]
        wk = ev["weekend"].get(s)
        seasons_html.append(
            '<section class="season season-{s}"><h3>{name} <span class="muted">{months}</span></h3>'
            '<table><thead><tr><th>Days before stay</th><th class="num">{g}BR</th></tr></thead><tbody>{rows}</tbody></table>'
            '<p class="why">{why}</p></section>'.format(
                s=s, name=SEASON_NAME[s], months=e(month_list(seasons[s])), g=e(g),
                rows=season_table(r, wk, floor), why=e(season_reason(s, r, wk, floor))))

    comp_rows = "".join('<tr><td>{}</td><td class="num">{}</td><td class="num">{}</td><td class="num">{}</td></tr>'.format(
        e(name.title()), *[gres[s]["profiles"][name] if s in gres else "–" for s in ["low", "shoulder", "high"]])
        for name in ["protective", "balanced", "open"])

    one_flags = [f for f in ev["one_night_flags"] if f[0] == g]
    one_txt = ("Not opted in. Worth considering in {} ({} of high-performer bookings are 1 night), within 7 days of arrival."
               .format(", ".join(MONTHS[int(f[1][5:7]) - 1] for f in one_flags), " / ".join(pct(f[2]) for f in one_flags))
               if one_flags else ("Opted in." if ev["one_night"].get("opt_in") else "Not opted in. No month shows meaningful 1-night demand."))

    cands = [c for c in ev["refine_candidates"] if c[0] == g]
    elig = (ev.get("portfolio_eligibility") or {}).get(g)
    if ev.get("portfolio_applied"):
        ref_txt = "Applied - see “Your bookings” notes in each season."
    elif not cands:
        ref_txt = "Not needed - market data settles every season."
    elif elig and elig.get("bookings", 0) >= 40:
        ref_txt = "{} could be sharpened with your own bookings ({} listings, ~{} calls). Ask to run it.".format(
            ", ".join(SEASON_NAME[c[1]] for c in cands), elig["listings"], elig["listings"] + elig["bookings"] // 100)
    else:
        ref_txt = "{} would benefit, but there isn't enough real booking history in this bedroom count (40+ bookings in the last year).".format(
            ", ".join(SEASON_NAME[c[1]] for c in cands))

    W, H, L, R, T, H1, ymax = geo
    page = TEMPLATE.format(
        title=e("Minimum stays · {} · {}BR".format(mk, g)),
        market=e(mk), group=e(g), profile=e(ev["profile"].title()), bar=pct(ev["T"]),
        today=e(today.isoformat()), svg=svg, rules=rules_html, seasons="".join(seasons_html),
        comp=comp_rows, one=e(one_txt), refine=e(ref_txt),
        data=json.dumps([[d.isoformat(), v] for d, v in series]),
        geo=json.dumps({"W": W, "H": H, "L": L, "R": R, "T": T, "H1": H1, "ymax": ymax}),
        mkt=json.dumps({str(k): v for k, v in mkt.items()}),
    )
    open(out, "w").write(page)
    print(out)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f6f7f9;--panel:#ffffff;--ink:#1f2328;--muted:#6b7280;--line:#e5e7eb;--line2:#d1d5db;--chart:#7a7f87;
--red:#e5484d;--pink:#d6249f;--chip:#f3f4f6;--high:rgba(214,36,159,.07);--shoulder:rgba(122,127,135,.07);--low:rgba(0,0,0,0);
--warn-bg:#fdf6d8;--warn-line:#ecd77a;--mkt:#0f7b8a;
--m0:#e7e9ec;--m1:#c5cad1;--m2:#8d949e;--m3:#e9a3cf;--m4:#c2257f;color-scheme:light;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#15171a;--panel:#1d2024;--ink:#e8eaed;--muted:#9aa0a6;--line:#2c3035;--line2:#3a3f45;
--chart:#b4b9c0;--chip:#2a2e33;--high:rgba(214,36,159,.14);--shoulder:rgba(180,185,192,.08);--warn-bg:#3a3420;--warn-line:#6b5d2a;
--mkt:#4fc3d1;--m0:#33373d;--m1:#4b5058;--m2:#6e757e;--m3:#9a4f7f;--m4:#e05aa8;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#15171a;--panel:#1d2024;--ink:#e8eaed;--muted:#9aa0a6;--line:#2c3035;--line2:#3a3f45;
--chart:#b4b9c0;--chip:#2a2e33;--high:rgba(214,36,159,.14);--shoulder:rgba(180,185,192,.08);--warn-bg:#3a3420;--warn-line:#6b5d2a;
--mkt:#4fc3d1;--m0:#33373d;--m1:#4b5058;--m2:#6e757e;--m3:#9a4f7f;--m4:#e05aa8;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:13px/1.45 Inter,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:18px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:8px}}
.chart-card{{padding:12px 14px 6px;position:relative}}
.chart-head{{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}}
.chart-head h1{{font-size:17px;font-weight:600;margin:0}}
.chart-head .meta{{color:var(--muted)}}
.tag{{display:inline-block;border:1px solid var(--line2);border-radius:999px;padding:1px 8px;color:var(--muted);font-size:12px;margin-left:6px}}
#chart{{width:100%;height:auto;display:block;margin-top:6px}}
.grid{{stroke:var(--line);stroke-width:1}}
.axis{{fill:var(--muted);font-size:10px;text-anchor:end}}
.axis-x{{text-anchor:start}}
.band-high{{fill:var(--high)}}.band-shoulder{{fill:var(--shoulder)}}.band-low{{fill:var(--low)}}
.band-label{{fill:var(--muted);font-size:10px}}
.line{{fill:none;stroke:var(--chart);stroke-width:1.6}}
.absmin{{stroke:var(--red);stroke-width:1.4}}
.absmin-label{{fill:var(--red);font-size:10px}}
.cursor{{stroke:var(--line2);stroke-dasharray:3 3}}
.mkt{{fill:none;stroke:var(--mkt);stroke-width:1.6;stroke-dasharray:5 3}}
.mix-0{{fill:var(--m0)}}.mix-1{{fill:var(--m1)}}.mix-2{{fill:var(--m2)}}.mix-3{{fill:var(--m3)}}.mix-4{{fill:var(--m4)}}
.mix{{stroke:none;opacity:.32}}
#chart[data-mix="on"] .line{{stroke:var(--ink);stroke-width:1.8}}
.axis-r{{text-anchor:start}}
#chart[data-mix="off"] #mixLayer{{display:none}}
#chart[data-mix="on"] #bands{{display:none}}
#chart[data-avg="off"] #avgLayer{{display:none}}
.overlays{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px}}
.overlays span.lbl{{color:var(--muted);font-size:12px;margin-right:2px}}
.ov{{font:inherit;font-size:12px;border:1px solid var(--line2);background:var(--panel);color:var(--muted);border-radius:999px;padding:2px 10px;cursor:pointer}}
.ov[aria-pressed="true"]{{color:var(--ink);border-color:var(--ink)}}
.ov:focus-visible{{outline:2px solid var(--pink);outline-offset:2px}}
.mixkey{{display:none}}
#wrapChart[data-mix="on"] .mixkey{{display:inline-flex}}
.key{{display:inline-flex;align-items:center;gap:5px;margin-right:12px;white-space:nowrap}}
.sw{{display:inline-block;width:12px;height:10px;border-radius:2px}}
.sw-line{{height:0;border-top:2px solid var(--chart)}}.sw-mkt{{height:0;border-top:2px dashed var(--mkt)}}.sw-abs{{height:0;border-top:2px solid var(--red)}}
.dot{{fill:var(--panel);stroke:var(--chart);stroke-width:2}}
.tip-m{{color:var(--muted)}}
#tip{{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line2);border-radius:4px;padding:3px 7px;font-size:12px;white-space:nowrap;display:none}}
.layout{{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:14px;margin-top:14px}}
@media (max-width:900px){{.layout{{grid-template-columns:1fr}}}}
.panel-head{{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--line)}}
.panel-head h2{{font-size:15px;font-weight:600;margin:0}}
.notice{{margin:12px 14px 0;padding:8px 10px;background:var(--warn-bg);border:1px solid var(--warn-line);border-radius:6px;font-size:12px}}
.rules{{margin:12px 14px 14px;border:1px solid var(--line);border-radius:8px}}
.rules-title{{padding:10px 12px;font-weight:600;border-bottom:1px solid var(--line)}}
.rule{{border-bottom:1px solid var(--line)}}.rule:last-child{{border-bottom:0}}
.rule-flat{{padding:10px 12px;display:flex;align-items:center;gap:14px}}
summary{{list-style:none;cursor:pointer;padding:10px 12px;display:flex;align-items:center;gap:8px}}
summary::-webkit-details-marker{{display:none}}
summary::after{{content:"";width:6px;height:6px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);transform:rotate(45deg);margin-left:2px}}
details[open] summary::after{{transform:rotate(-135deg)}}
summary:focus-visible{{outline:2px solid var(--pink);outline-offset:-2px}}
.rule-title{{font-weight:500}}
.count{{border:1px solid var(--line);background:var(--chip);border-radius:4px;padding:0 6px;font-size:11px;color:var(--muted)}}
.help{{display:inline-grid;place-items:center;width:14px;height:14px;border:1px solid var(--line2);border-radius:50%;font-size:9px;color:var(--muted)}}
.rule-body{{padding:0 12px 12px}}
.row{{padding:8px 0;border-top:1px dashed var(--line)}}.row:first-child{{border-top:0}}
.row-head{{margin-bottom:6px}}
.chips{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}}
.chip{{font-size:11px;padding:1px 7px;border-radius:4px;background:var(--chip);color:var(--muted)}}
.chip.on{{background:var(--ink);color:var(--panel)}}
.dows{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}}
@media (max-width:620px){{.dows{{grid-template-columns:repeat(4,minmax(0,1fr))}}}}
.dow{{display:flex;flex-direction:column;gap:3px}}
.dow-name{{font-size:11px;color:var(--muted)}}
.box{{border:1px solid var(--line2);border-radius:4px;padding:4px 8px;font-size:12px;min-height:26px;text-align:right}}
.box-empty{{color:transparent}}
.box.wide{{min-width:110px}}
.muted{{color:var(--muted)}}
.side{{display:flex;flex-direction:column;gap:14px}}
.side .card{{padding:12px 14px}}
.side h2{{font-size:14px;font-weight:600;margin:0 0 6px}}
.season{{padding:12px 14px;border-top:1px solid var(--line)}}
.season h3{{font-size:14px;font-weight:600;margin:0 0 6px}}
.season h3 .muted{{font-weight:400;font-size:12px;margin-left:4px}}
.season-high{{box-shadow:inset 3px 0 0 var(--pink)}}.season-shoulder{{box-shadow:inset 3px 0 0 var(--chart)}}.season-low{{box-shadow:inset 3px 0 0 var(--line2)}}
table{{border-collapse:collapse;width:100%;max-width:360px}}
th,td{{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line);font-size:12px}}
th{{color:var(--muted);font-weight:500}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.why{{margin:8px 0 0;max-width:72ch;color:var(--ink)}}
.foot{{color:var(--muted);font-size:12px;margin:14px 2px}}
.legend{{font-size:12px;color:var(--muted);margin:2px 0 0}}
</style></head><body><div class="wrap">

<div class="card chart-card" id="wrapChart" data-mix="off">
  <div class="chart-head"><h1>Minimum stays <span class="tag">Proposed, not applied</span></h1>
  <div class="meta">{market} · {group}BR · {profile} profile (bar {bar}) · as of {today}</div></div>
  {svg}
  <div id="tip"></div>
  <div class="overlays"><span class="lbl">Market overlays</span>
    <button class="ov" type="button" data-ov="avg" aria-pressed="true">Average stay</button>
    <button class="ov" type="button" data-ov="mix" aria-pressed="false">Booking mix by length of stay</button></div>
  <p class="legend"><span class="key"><span class="sw sw-line"></span>Proposed min. stay (as of today)</span><span class="key"><span class="sw sw-abs"></span>Absolute minimum</span><span class="key ovkey-avg"><span class="sw sw-mkt"></span>Market average stay</span>
  <span class="key mixkey"><span class="sw" style="background:var(--m0)"></span>1 night</span><span class="key mixkey"><span class="sw" style="background:var(--m1)"></span>2</span><span class="key mixkey"><span class="sw" style="background:var(--m2)"></span>3</span><span class="key mixkey"><span class="sw" style="background:var(--m3)"></span>4</span><span class="key mixkey"><span class="sw" style="background:var(--m4)"></span>5+ nights (right axis, % of bookings)</span>
  <span class="key muted">Market = high performers, same month last year</span></p>
</div>

<div class="layout">
  <div class="card">
    <div class="panel-head"><h2>Minimum stays</h2></div>
    <div class="notice">Only Default, Monthly, Time-based, Gap night and Absolute minimum would change. Season rules, Event rules, date-specific overrides and Adjacency rules stay as they are.</div>
    <div class="rules"><div class="rules-title">Rules</div>{rules}</div>
    <div class="panel-head"><h2>By season</h2><span class="muted">weekend / weekday</span></div>
    {seasons}
  </div>
  <aside class="side">
    <div class="card"><h2>Threshold profiles</h2>
      <table><thead><tr><th>Profile</th><th class="num">Low</th><th class="num">Shoulder</th><th class="num">High</th></tr></thead><tbody>{comp}</tbody></table>
      <p class="muted">Far-out minimum stay each profile would hold. Balanced is the default.</p></div>
    <div class="card"><h2>1-night stays</h2><p>{one}</p></div>
    <div class="card"><h2>Refine with your bookings</h2><p>{refine}</p></div>
    <div class="card"><h2>Next step</h2><p>Review and edit anything above. When it looks right, ask for the Wheelhouse write-back. Nothing has been changed on your listings.</p></div>
  </aside>
</div>
<p class="foot">Based on trailing 12 months of Wheelhouse market data for this bedroom count: high- vs average-performer length of stay and booking window.</p>
</div>
<script>
(function(){{
  var data={data}, g={geo}, mkt={mkt};
  var svg=document.getElementById('chart'), tip=document.getElementById('tip');
  var cur=document.getElementById('cursor'), dot=document.getElementById('dot');
  var M=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  function show(evt){{
    var r=svg.getBoundingClientRect(), sx=(evt.clientX-r.left)/r.width*g.W;
    var i=Math.round((sx-g.L)/(g.W-g.L-g.R)*(data.length-1));
    if(i<0||i>=data.length){{hide();return;}}
    var x=g.L+(g.W-g.L-g.R)*i/(data.length-1), v=data[i][1], y=g.T+g.H1*(1-v/g.ymax);
    cur.setAttribute('x1',x);cur.setAttribute('x2',x);cur.setAttribute('visibility','visible');
    dot.setAttribute('cx',x);dot.setAttribute('cy',y);dot.setAttribute('visibility','visible');
    var p=data[i][0].split('-');
    var mk=mkt[String(+p[1])], extra='';
    if(mk){{var B=['1','2','3','4','5+'];extra='<br><span class="tip-m">Market, '+M[+p[1]-1]+': avg stay '+mk.avg.toFixed(1)+' nights';
      for(var k=0;k<5;k++){{extra+=' · '+B[k]+(k==0?' night ':' ')+Math.round(mk.shares[k]*100)+'%';}} extra+='</span>';}}
    tip.innerHTML='Min. stay is <b>'+v+' nights</b> on '+M[+p[1]-1]+' '+(+p[2])+', '+p[0]+extra;
    tip.style.display='block';
    var left=x/g.W*r.width+14, w=tip.offsetWidth;
    if(left+w>r.width) left=x/g.W*r.width-w-14;
    tip.style.left=(left+14)+'px'; tip.style.top=(y/g.H*r.height+20)+'px';
  }}
  function hide(){{tip.style.display='none';cur.setAttribute('visibility','hidden');dot.setAttribute('visibility','hidden');}}
  svg.addEventListener('mousemove',show); svg.addEventListener('mouseleave',hide);
  var wrap=document.getElementById('wrapChart');
  document.querySelectorAll('.ov').forEach(function(b){{
    b.addEventListener('click',function(){{
      var on=b.getAttribute('aria-pressed')!=='true', k=b.getAttribute('data-ov');
      b.setAttribute('aria-pressed',on?'true':'false');
      svg.setAttribute('data-'+k,on?'on':'off');
      if(k==='mix') wrap.setAttribute('data-mix',on?'on':'off');
      document.querySelectorAll('.ovkey-'+k).forEach(function(e){{e.style.display=on?'':'none';}});
    }});
  }});
}})();
</script>
</body></html>"""


if __name__ == "__main__":
    main()
