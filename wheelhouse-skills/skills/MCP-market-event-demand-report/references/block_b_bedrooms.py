# Block B - 6-month overview for each bedroom group (feeds the page's bedroom filter).
# Run after Block A. Pulls run in parallel: up to 5 groups per `execute`
# (about 8 seconds), or 3 when BASIS is "stly" since that doubles the calls.
# Merge each returned {group_key: {...}} into report.json -> overview.groups.
import datetime, asyncio

# ---------------- CONFIG ----------------
MARKET_ID = 0                 # same market_id as Block A
TODAY = "YYYY-MM-DD"
BASIS = "ly_final"            # copy overview.basis from Block A's result
GROUPS = [                    # from wheelhouse_rmGetMarketBedroomGroups
    # {"bedrooms": "1", "listings": 1000},
]
# ----------------------------------------
D = datetime.date
ONE = datetime.timedelta(days=1)
def S(d): return d.isoformat()
def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return D(y, m, 1)
def unwrap(r):
    if isinstance(r, dict) and "result" in r and "data" not in r:
        return r["result"]
    return r
def clean(rows):
    out = {}
    for row in rows:
        if row.get("occupancy_adjusted") is not None and (row.get("nights_bookable") or 0) > 0:
            out[row["stay_date"]] = row
    return out
def agg(dates, src):
    rows = [src[S(d)] for d in dates if S(d) in src]
    if not rows: return None
    b = sum(x["nights_bookable"] for x in rows)
    booked = sum(x["occupancy_adjusted"] * x["nights_bookable"] for x in rows)
    avail = b - booked
    adr = None
    if booked > 0:
        adr = sum((x.get("adr_w_fees") or 0) * x["occupancy_adjusted"] * x["nights_bookable"] for x in rows) / booked
    ask = None
    if avail > 0:
        ask = sum((x.get("asking_rate_w_fees") or 0) * (1 - x["occupancy_adjusted"]) * x["nights_bookable"] for x in rows) / avail
    return {"occ": booked / b, "adr": adr, "ask": ask, "listings": b / len(rows)}
def month_dates(m0):
    m1 = add_months(m0, 1)
    return [m0 + datetime.timedelta(days=k) for k in range((m1 - m0).days)]
def rnd(v, n):
    return None if v is None else round(v, n)
def label_for(key):
    if key == "0": return "Studio"
    if key.endswith("+"): return key[:-1] + "+ bedrooms"
    return key + (" bedroom" if key == "1" else " bedrooms")

today = D.fromisoformat(TODAY)
ov_start = add_months(today.replace(day=1), 1)
ov_end = add_months(ov_start, 6) - ONE
async def pull(key, basis):
    p = {"market_id": MARKET_ID, "bedrooms": key, "start_date": S(add_months(ov_start, -12)), "end_date": S(ov_end)}
    if basis == "stly":
        p = {"market_id": MARKET_ID, "bedrooms": key, "basis": "stly", "start_date": S(ov_start), "end_date": S(ov_end)}
    try:
        return unwrap(await call_tool("wheelhouse_rmGetMarketTimeSeries", p))
    except Exception as e:
        return {"_err": str(e)[:160]}

# gather() takes no keyword arguments in this sandbox, so errors are caught inside pull()
cur_res = await asyncio.gather(*[pull(g["bedrooms"], "current") for g in GROUPS])
stly_res = None
if BASIS == "stly":
    stly_res = await asyncio.gather(*[pull(g["bedrooms"], "stly") for g in GROUPS])

out = {}
for i, g in enumerate(GROUPS):
    key = g["bedrooms"]
    r = cur_res[i]
    if "_err" in r:
        out[key] = {"label": label_for(key), "error": r["_err"]}
        continue
    day = clean(r.get("data", []))
    sday = None
    if stly_res is not None and "_err" not in stly_res[i]:
        sday = clean(stly_res[i].get("data", []))
    months = []
    for j in range(6):
        m0 = add_months(ov_start, j)
        cur = agg(month_dates(m0), day)
        ly = agg(month_dates(m0), sday) if sday else agg(month_dates(add_months(m0, -12)), day)
        row = {"month": S(m0)[:7]}
        for k in ("occ", "adr", "ask"):
            row[k] = rnd(cur[k], 3 if k == "occ" else 0) if cur else None
            row[k + "_ly"] = rnd(ly[k], 3 if k == "occ" else 0) if ly else None
        row["listings"] = round(cur["listings"]) if cur else None
        months.append(row)
    out[key] = {"label": label_for(key), "market_listings": g.get("listings"), "months": months}
return out
