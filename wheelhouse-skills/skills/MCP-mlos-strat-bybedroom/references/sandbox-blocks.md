# Sandbox blocks (Wheelhouse MCP `execute`)

Run each block as one call to the Wheelhouse MCP's `execute` tool (its name carries your client's prefix, e.g. `mcp__wheelhouse__execute`; `call_tool` is already in scope inside it). Values in the CONFIG lines below are placeholders; fill in your own.

Rules for every block: ~30 s budget; about 18 calls per block is safe; one `metric` per call (MCP array bug). The blocks below do their own date math, but `datetime` and `json` can be imported if a change needs them. Every block uses the `call()` retry helper and returns partial data instead of raising.

```python
async def call(name, args):
    err = None
    for attempt in range(4):
        try:
            return await call_tool(name, args)
        except Exception as e:
            err = e
    raise err
```

## Block A — market, user listings, bedroom groups

```python
MARKET = "Example City"   # substring of market_name
# + call() helper
items, page = [], 1
while True:
    r = await call("wheelhouse_rmGetListings", {"per_page": 100, "page": page})
    batch = r["result"]
    items = items + batch
    if len(batch) < 100:
        break
    page += 1
mine = [l for l in items if MARKET.lower() in str(l.get("market_name", "")).lower()]
out = {"market_id": None, "market_name": None, "user_by_bedrooms": {}, "listings": []}
for l in mine:
    out["market_id"], out["market_name"] = l.get("market_id"), l.get("market_name")
    b = str(l.get("num_bedrooms"))
    out["user_by_bedrooms"][b] = out["user_by_bedrooms"].get(b, 0) + 1
    out["listings"].append([l.get("id"), l.get("channel"), l.get("num_bedrooms"), l.get("title")])
if out["market_id"]:
    try:
        out["bedroom_groups"] = (await call("wheelhouse_rmGetMarketBedroomGroups", {"market_id": out["market_id"]}))["bedroom_groups"]
    except Exception as e:
        out["access_error"] = str(e)[:200]
# Gate 1 for the optional portfolio layer: trailing-year bookings per listing, one ranked call per 100 listings.
# Hypothetical/test listings are excluded by channel - their booking counts are synthetic.
real = {str(l.get("wheelhouse_id")): l for l in mine if l.get("channel") != "hypothetical"}
elig = {}
if real:
    page = 1
    try:
        while True:
            r = await call("wheelhouse_rmGetBulkListingKpis", {"metric": "bookings", "window": "365_0", "per_page": 100, "page": page})
            batch = r["result"]
            for x in batch:
                l = real.get(str(x.get("listing_id")))
                if l:
                    g = str(l.get("num_bedrooms"))
                    elig.setdefault(g, {"listings": 0, "bookings": 0})
                    elig[g]["listings"] += 1
                    elig[g]["bookings"] += int(x.get("value") or 0)
            if len(batch) < 100:
                break
            page += 1
    except Exception as e:
        out["eligibility_error"] = str(e)[:200]
out["portfolio_eligibility"] = elig
return out
```

## Block B — season index and weekday occupancy

Weekday index: Mon=0 … Sun=6 (computed, since `datetime` is unavailable).

```python
MID, START, END, BASE_BR = 68, "2025-11-01", "2026-10-31", "2"
# + call() helper
def weekday(y, m, d):
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if m < 3:
        y -= 1
    return ((y + y // 4 - y // 100 + y // 400 + t[m - 1] + d) % 7 + 6) % 7
def monthly(rows, key):
    agg = {}
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        m = r["stay_date"][:7]
        agg.setdefault(m, [0, 0])
        agg[m][0] += v
        agg[m][1] += 1
    return {m: a[0] / a[1] for m, a in agg.items()}
ts = lambda met, extra: call("wheelhouse_rmGetMarketTimeSeries", dict({"market_id": MID, "metric": [met], "start_date": START, "end_date": END}, **extra))
mr = monthly((await ts("revpar_w_fees", {}))["data"], "revpar_w_fees")
season_index = {m: {"revpar": round(mr[m], 2)} for m in sorted(mr)}
acc = {}
for r in (await ts("occupancy_adjusted", {"bedrooms": BASE_BR}))["data"]:
    v = r.get("occupancy_adjusted")
    if v is None:
        continue
    s = r["stay_date"]
    m, wd = s[:7], weekday(int(s[:4]), int(s[5:7]), int(s[8:10]))
    acc.setdefault(m, [[0, 0] for i in range(7)])
    acc[m][wd][0] += v
    acc[m][wd][1] += 1
weekday_occ = {m: [round(a[0] / a[1], 4) if a[1] else None for a in acc[m]] for m in sorted(acc)}
return {"season_index": season_index, "weekday_occ": weekday_occ}
```

## Block C — distributions for the chosen group (pass 1), ~12–18 calls per block

Build `SEASON` from the scorer's season classification (run the scorer's season step, or classify from Block B: High ≥ 1.20, Low ≤ 0.85 of the annual mean). Per month, pass 1 pulls:
- high-performer LOS — every month, every group
- high-performer lead time — High and Shoulder months
- average-performer LOS — Low months only (feeds the low-season openness test)

That is 24 calls for the group: run it as two blocks of six months. Failed months go into the retry queue (see SKILL.md, Reliability).

```python
MID = 123   # market_id from Block A
SEASON = {"2025-11": "S", "2025-12": "H", "2026-01": "L"}   # all 12 months
JOBS = [("3", ["2025-11", "2025-12", "2026-01"])]          # (bedrooms, months)
RUNGS, MAXN = [7, 14, 30, 60, 90, 120], 15
# + call() helper
def pmf(b):
    p = [0.0] * (MAXN + 1)
    for x in b:
        k = int(x["bucket_min_incl"])
        if k >= 0:
            p[min(k, MAXN)] += x["probability"]
    while len(p) > 2 and p[-1] == 0:
        p.pop()
    return [round(v, 3) for v in p]
def within(b):
    return {str(r): round(sum(x["probability"] for x in b if x["bucket_min_incl"] >= -r), 3) for r in RUNGS}
out, failed = {}, []
for br, months in JOBS:
    out.setdefault(br, {})
    for m in months:
        base = {"market_id": MID, "month": m, "bedrooms": br}
        try:
            row = {"los_high": pmf((await call("wheelhouse_rmGetMarketDistribution", dict(base, metric=["length_of_stay"], performance="high")))["data"]["length_of_stay"])}
            if SEASON[m] == "L":
                row["los_avg"] = pmf((await call("wheelhouse_rmGetMarketDistribution", dict(base, metric=["length_of_stay"], performance="average")))["data"]["length_of_stay"])
            else:
                row["lead_high_within"] = within((await call("wheelhouse_rmGetMarketDistribution", dict(base, metric=["lead_time"], performance="high")))["data"]["lead_time"])
            out[br][m] = row
        except Exception as e:
            failed.append([br, m])
out["failed"] = failed
return out
```

## Block C2 — pass 2 (only what the scorer asks for)

When the scorer exits with `NEEDS_DATA [...]`, it lists group/season/months whose Low season could rise above the floor under at least one profile and therefore needs lead time. Pull lead time for exactly those months, add each result as `lead_high_within` to the month's entry, and re-run the scorer.

```python
MID = 123   # market_id from Block A
JOBS = [("3", ["2026-01", "2026-02", "2026-05", "2026-09"])]
RUNGS = [7, 14, 30, 60, 90, 120]
# + call() helper
def within(b):
    return {str(r): round(sum(x["probability"] for x in b if x["bucket_min_incl"] >= -r), 3) for r in RUNGS}
out, failed = {}, []
for br, months in JOBS:
    out.setdefault(br, {})
    for m in months:
        try:
            d = await call("wheelhouse_rmGetMarketDistribution", {"market_id": MID, "month": m, "bedrooms": br, "metric": ["lead_time"], "performance": "high"})
            out[br][m] = within(d["data"]["lead_time"])
        except Exception as e:
            failed.append([br, m])
out["failed"] = failed
return out
```

Notes: LOS buckets are one night wide (`bucket_min_incl` = nights); lead-time buckets are 5 days wide and negative (days before stay), so "booked within r days" = sum of buckets with `bucket_min_incl >= -r`.

## Block D — own reservations (opt-in portfolio layer)

Run only after the user opts in, only for eligible listings in groups the report names. `LISTINGS` rows are `[listing_id, channel, group]`, where `group` matches the report's bedroom-group key (pooled groups such as `"10+"` included). ~10 listings per block.

```python
LISTINGS = [["12345678", "airbnb", "3"]]
START, END = "2025-11-01", "2026-10-31"   # trailing 12 months of stay dates
# + call() helper
def jd(s):
    y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10])
    a = (14 - m) // 12
    y2, m2 = y + 4800 - a, m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400
rows, failed = [], []
for lid, ch, g in LISTINGS:
    page = 1
    try:
        while True:
            r = await call("wheelhouse_rmGetReservations", {"listing_id": lid, "channel": ch, "date_filter_type": "stay_date",
                                                            "start_date": START, "end_date": END, "per_page": 100, "page": page})
            batch = r["result"] if isinstance(r, dict) and "result" in r else r
            for x in batch:
                if x.get("status") != "Accepted" or not x.get("booked_at"):
                    continue
                if not (START <= x["start_date"] <= END):
                    continue
                rows.append([g, x["start_date"][:7], jd(x["end_date"]) - jd(x["start_date"]),
                             jd(x["start_date"]) - jd(x["booked_at"][:10])])
            if len(batch) < 100:
                break
            page += 1
    except Exception as e:
        failed.append(lid)
return {"rows": rows, "failed": failed}
```

Add the rows to the scorer input as `"portfolio": {"rows": rows}` and re-run. The scorer only applies them to the cells it flagged.

⚠️ Counts `Accepted` reservations only; which statuses should count is still an open question in the project instructions. `rmGetReservations` is untested in this skill - verify the tool name and response shape on first run.
