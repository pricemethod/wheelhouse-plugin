# STAGE 3 -- pure computation, no API calls. Paste into the Wheelhouse MCP `execute` tool (or run with any Python).
# ROWS = the stage-2 output (list of dicts), concatenated if stage 2 ran in batches.
# Percentile ranks are computed within this pool, so score ALL candidates together.

ROWS = [
    # {"id": 12345678, "t": "Example 3BR Beach House", "gap": -29.3, "p7": 0, "p14": 0, "ar": 202, "acur": "USD",
    #  "nmed": 316, "np25": 227, "np75": 414, "cnt": 981, "ncur": "USD", "mult": 1.0, "src": "none", ...},
]

# ---------------- CONFIG ----------------
WEIGHTS = {"price": 0.35, "gap": 0.35, "p7": 0.15, "p14": 0.15}   # change if the user wants price weighted higher
MIN_COMPS = 10                 # fewer comparable listings than this = low-confidence price comp
PLAUSIBLE_INDEX = (0.1, 10.0)  # price index outside this range = data artifact, not a signal
BORDERLINE = (0.8, 1.0)        # at/below median but close, and fees unconfigured -> could really be above
# ----------------------------------------

def pct_rank(vals, higher_is_more_urgent):
    # Tie-averaged percentile rank in 0..1 (1 = most urgent).
    n = len(vals)
    out = []
    for v in vals:
        if n == 1:
            out.append(0.5)
            continue
        less = sum(1 for x in vals if x < v)
        eq = sum(1 for x in vals if x == v)
        p = (less + (eq - 1) / 2) / (n - 1)
        out.append(p if higher_is_more_urgent else 1 - p)
    return out

for r in ROWS:
    why = []
    m = r.get("mult")
    r["fee_assumed"] = (m is None) or (r.get("src") in ("none", "estimate", None) and abs(m - 1.0) < 1e-9)
    m = 1.0 if m is None else m
    r["adj"] = None if not r.get("ar") else r["ar"] * m          # fee-inclusive nightly rate, comparable to neighborhood
    r["idx"] = None
    if r.get("err"):
        why.append("lookup failed")
    elif not r.get("nmed") or not r["adj"]:
        why.append("no neighborhood/asking rate")
    else:
        if r.get("ncur") and r.get("acur") and r["ncur"] != r["acur"]:
            why.append("currency mismatch (%s vs %s)" % (r["acur"], r["ncur"]))
        if r.get("cnt") is not None and r["cnt"] < MIN_COMPS:
            why.append("thin comps (%s)" % r["cnt"])
        r["idx"] = r["adj"] / r["nmed"]
        if not (PLAUSIBLE_INDEX[0] <= r["idx"] <= PLAUSIBLE_INDEX[1]):
            why.append("implausible ratio")
    r["no_comp_reason"] = why
    r["price_ok"] = not why and r["idx"] is not None

u_gap = pct_rank([r["gap"] for r in ROWS], False)       # more negative gap = more urgent
u_p7 = pct_rank([r["p7"] for r in ROWS], False)         # fewer nights picked up = more urgent
u_p14 = pct_rank([r["p14"] for r in ROWS], False)
ok = [r for r in ROWS if r["price_ok"]]
u_price = dict(zip([r["id"] for r in ok], pct_rank([r["idx"] for r in ok], True)))   # higher premium = more urgent

W = WEIGHTS
for r, a, b, c in zip(ROWS, u_gap, u_p7, u_p14):
    if r["price_ok"]:
        s = W["price"] * u_price[r["id"]] + W["gap"] * a + W["p7"] * b + W["p14"] * c
    else:   # no reliable comp: renormalize over the other signals instead of treating price as "fine"
        tot = W["gap"] + W["p7"] + W["p14"]
        s = (W["gap"] * a + W["p7"] * b + W["p14"] * c) / tot
    r["score"] = round(s, 3)
    if not r["price_ok"]:
        r["tier"], r["read"] = "no reliable comp", "Price unscored (" + "; ".join(r["no_comp_reason"]) + ")"
    elif r["adj"] > r["np75"]:
        r["tier"], r["read"] = "above p75", "Way overpriced vs neighborhood - rate cut candidate"
    elif r["adj"] > r["nmed"]:
        r["tier"], r["read"] = "above median", "Priced above neighborhood median - price may be a factor"
    else:
        r["tier"] = "at/below median"
        r["read"] = "Not overpriced - look at floor, min stay, blocked nights, listing quality"
        if r["fee_assumed"] and BORDERLINE[0] <= r["idx"] <= BORDERLINE[1]:
            r["read"] += " (borderline: no fee setting, so true index could be ~1.0 or higher)"

ROWS.sort(key=lambda r: -r["score"])
def view(r):
    f = lambda x, n=0: None if x is None else round(x, n)
    return {"id": r["id"], "t": r.get("t"), "auto": r.get("auto"), "acc": r.get("acc"), "u": r.get("u"),
            "gap": r["gap"], "occ": r.get("occ"), "nocc": r.get("nocc"), "p7": r["p7"], "p14": r["p14"],
            "b7": r.get("b7"), "b14": r.get("b14"), "ar": r.get("ar"), "mult": f(r.get("mult"), 2),
            "adj": f(r["adj"]), "nmed": f(r.get("nmed")), "np75": f(r.get("np75")), "idx": f(r["idx"], 2),
            "cnt": r.get("cnt"), "mpo": r.get("mpo"), "tier": r["tier"], "score": r["score"], "read": r["read"]}
res = [view(r) for r in ROWS]
return {
    "n": len(res),
    "price_problem": [x for x in res if x["tier"] in ("above p75", "above median")],
    "not_price": [x for x in res if x["tier"] == "at/below median"],
    "no_comp": [x for x in res if x["tier"] == "no reliable comp"],
    "ranked_overall": [[x["id"], x["t"], x["score"], x["tier"]] for x in res],
}
