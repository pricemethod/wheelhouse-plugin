# STAGE 1 -- paste into the Wheelhouse MCP `execute` tool (call_tool is already in scope).
# Read-only. ~12 calls total. Returns the listings that are behind their neighborhood
# on occupancy, with pickup + asking rate attached, ready to feed into stage 2.

# ---------------- CONFIG (edit if the user asks for different thresholds) ----------------
GAP_THRESHOLD_PP = -10         # "behind" = adjusted occupancy this many pts (or more) below neighborhood
MIN_NIGHTS_AVAILABLE_60 = 30   # need enough open nights in the next 60 for a fix to matter
# ------------------------------------------------------------------------------------------

try:
    import asyncio
    async def nap(s): await asyncio.sleep(s)
except Exception:
    async def nap(s): return

async def call(tool, args, tries=6):
    last = None
    for _ in range(tries):
        try:
            return await call_tool(tool, args)
        except Exception as e:
            last = e
            if "ate limit" in str(e) or "429" in str(e):
                await nap(8)
            else:
                raise
    raise last

def rows_of(res):
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for k in ("result", "value", "data", "items"):
            if k in res:
                return rows_of(res[k])
    return []

async def fetch_all(tool, args):
    out, page = [], 1
    while True:
        r = await call(tool, {**args, "per_page": 100, "page": page})   # per_page max is 100
        rs = rows_of(r)
        out += rs
        if len(rs) < 100:
            break
        page += 1
    return out

listings = await fetch_all("wheelhouse_rmGetListings", {})
lmap = {}
for l in listings:
    lmap[l["wheelhouse_id"]] = {
        "t": l.get("title"), "ch": l.get("channel"), "u": l.get("number_of_active_units"),
        "auto": (l.get("listing_preferences") or {}).get("automatic_rate_posting_enabled"),
        "acc": l.get("access_level"),
    }

SPECS = {
    "gap":  ("occupancy_neighborhood_adjusted_pp", "0_30"),   # listing minus neighborhood, in points
    "occ":  ("occupancy_adjusted", "0_30"),
    "nocc": ("occupancy_neighborhood_adjusted", "0_30"),
    "p7":   ("pickup", "7_0"),                                # nights picked up
    "p14":  ("pickup", "14_0"),
    "b7":   ("pickup_bookings", "7_0"),                       # bookings, as a cross-check
    "b14":  ("pickup_bookings", "14_0"),
    "av":   ("nights_available", "0_60"),
    "ar":   ("asking_rate", "0_30"),                          # NOT asking_rate_fees (it returned the same number)
    "mpo":  ("min_price_occurrence", "0_30"),                 # floor lead only; units unverified
}
d, acur = {}, {}
for k, (m, w) in SPECS.items():
    rs = await fetch_all("wheelhouse_rmGetBulkListingKpis", {"metric": m, "window": w})
    d[k] = {r["listing_id"]: r.get("value") for r in rs}    # bulk listing_id == wheelhouse_id
    if k == "ar":
        acur = {r["listing_id"]: r.get("currency") for r in rs}

dropped_missing, dropped_avail, not_behind = 0, 0, 0
cands = []
for i, gap in d["gap"].items():
    if i not in lmap:
        continue
    if gap is None or any(d[k].get(i) is None for k in ("p7", "p14", "av")):
        dropped_missing += 1
        continue
    if d["av"][i] < MIN_NIGHTS_AVAILABLE_60:
        dropped_avail += 1
        continue
    if gap > GAP_THRESHOLD_PP:
        not_behind += 1
        continue
    occ, nocc = d["occ"].get(i), d["nocc"].get(i)
    cands.append({
        "id": i, **lmap[i],
        "gap": round(gap, 1),
        "occ": None if occ is None else round(occ * 100, 1),
        "nocc": None if nocc is None else round(nocc * 100, 1),
        "p7": d["p7"][i], "p14": d["p14"][i], "b7": d["b7"][i], "b14": d["b14"][i],
        "av": d["av"][i], "ar": d["ar"].get(i), "acur": acur.get(i), "mpo": d["mpo"].get(i),
    })
cands.sort(key=lambda r: r["gap"])
return {
    "total_listings": len(listings),
    "dropped_missing_kpi": dropped_missing,
    "dropped_low_availability": dropped_avail,
    "not_behind": not_behind,
    "n_candidates": len(cands),
    "n_candidates_auto_on": sum(1 for r in cands if r["auto"]),
    "candidates": cands,
}
