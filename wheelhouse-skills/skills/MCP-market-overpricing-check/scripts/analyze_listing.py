# analyze_listing.py
# Paste this whole file into the Wheelhouse MCP `execute` tool (one listing per call).
# It reads live data, does the daily-level comparison, and RETURNS one JSON-able dict
# that assets/report_template.html renders. Edit only the PARAMETERS block.
#
# Sandbox notes (verified): ~30 s limit per execute block, no % string formatting,
# `import datetime` works. ~6 MCP calls per listing, so one listing per block is safe.

# ----------------------------- PARAMETERS -----------------------------
LISTING_ID = "12345678"   # Wheelhouse listing id (wheelhouse_id) as a string
CHANNEL = "wheelhouse"
BENCHMARK = "p75"         # "p75" (default) or "median"
WINDOW_DAYS = 60          # analysis window; the 0-30 day window is the first 30 of these
MIN_RUN = 3               # ignore open stretches shorter than this many nights (orphan gaps)
OCC_CEILING = 0.80        # skip the listing when adjusted occupancy is at/above this
STALL_MIN_OPEN = 10       # open nights needed before "stalled" can be true
BIG = 0.15                # check 3 threshold: more than 15% above the benchmark
FLAG_MIN = 0.005          # a night counts as "above" at +0.5% or more (rounds to +1%)
# ----------------------------------------------------------------------

import datetime as dt
try:
    import asyncio
    async def nap(s):
        await asyncio.sleep(s)
except Exception:
    async def nap(s):
        return

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


async def call(tool, args):
    last = None
    for attempt in range(4):
        try:
            return await call_tool(tool, args)
        except Exception as e:
            last = e
            msg = str(e)
            if "429" in msg or "ate limit" in msg:
                await nap(6)
            else:
                raise
    raise last


def iso(d):
    return d.isoformat()


def fmt(d):
    return MON[d.month - 1] + " " + str(d.day)


def mean(a):
    a = [v for v in a if v is not None]
    return sum(a) / len(a) if a else None


# ---- 1. listing + KPIs (KPIs return every metric/window in one call) ----
lst = await call("wheelhouse_rmGetListing", {"listing_id": LISTING_ID, "channel": CHANNEL})
l = lst.get("result", lst)
title = l.get("title")
bedrooms = l.get("num_bedrooms") or 0
market_id = l.get("market_id")
units = l.get("number_of_active_units") or 1
listing_info = {"id": LISTING_ID, "title": title, "bedrooms": bedrooms, "units": units,
                "access": l.get("access_level"),
                "auto": (l.get("listing_preferences") or {}).get("automatic_rate_posting_enabled")}

k = await call("wheelhouse_rmGetListingKpis", {"listing_id": LISTING_ID, "channel": CHANNEL, "days": WINDOW_DAYS})
today = dt.date.fromisoformat(k["model_date"])
last_day = today + dt.timedelta(days=WINDOW_DAYS - 1)
pad_day = last_day + dt.timedelta(days=7)   # look past the window so run lengths are measured correctly


def kv(m, w):
    return (k.get(m) or {}).get(w)


params = {"benchmark": BENCHMARK, "big": BIG, "window_days": WINDOW_DAYS}
occ30 = kv("occupancy_adjusted", "0_30")
occ60 = kv("occupancy_adjusted", "0_60")
if occ30 is not None and occ60 is not None and occ30 >= OCC_CEILING and occ60 >= OCC_CEILING:
    return {"status": "skipped_high_occupancy", "listing": listing_info, "params": params,
            "message": "Skipped: adjusted occupancy is " + str(round(occ60 * 100)) + "% or higher, so there is no stalled-sales or underperformance question to check."}

# ---- 2. calendar, fee multiplier, neighborhood pricing (+ market-high occupancy for p75) ----
pc = await call("wheelhouse_rmGetPriceCalendar", {"listing_id": LISTING_ID, "channel": CHANNEL,
                                                   "start_date": iso(today), "end_date": iso(pad_day)})
fee = await call("wheelhouse_rmGetFeeImpactCalendar", {"listing_id": LISTING_ID, "channel": CHANNEL, "fallback": "estimate",
                                                        "start_date": iso(today), "end_date": iso(today + dt.timedelta(days=2))})
nb = await call("wheelhouse_rmGetNeighborhoodPricing", {"listing_id": LISTING_ID, "channel": CHANNEL})

fe = fee.get("result") or fee.get("data") or []
fee_mult = fe[0].get("fee_multiplier", 1.0) if fe else 1.0
fee_src = fe[0].get("source") if fe else None
NB = {}
for x in nb.get("data", []):
    NB[x["stay_date"]] = x

MO = {}
if BENCHMARK == "p75":
    try:
        bed = "4+" if bedrooms >= 4 else str(bedrooms)
        mo = await call("wheelhouse_rmGetMarketTimeSeries", {"market_id": market_id, "metric": ["occupancy_adjusted"],
                                                              "start_date": iso(today), "end_date": iso(last_day),
                                                              "performance": "high", "bedrooms": bed})
        for x in mo.get("data", []):
            MO[x["stay_date"]] = x["occupancy_adjusted"]
    except Exception:
        MO = {}

# ---- 3. daily table. Multi-unit listings return one calendar row per unit per date:
#         a date is open if ANY unit is open, and its rate is the mean of the open units' rates.
by_date = {}
for x in pc["result"]:
    by_date.setdefault(x["stay_date"], []).append(x)

days = []
for i in range(WINDOW_DAYS + 7):
    d = today + dt.timedelta(days=i)
    rows = by_date.get(iso(d), [])
    open_rows = [r for r in rows if r["is_available"] and not r["is_booked"] and r["price"]]
    days.append({"d": d, "i": i, "open": len(open_rows) > 0,
                 "price": mean([r["price"] for r in open_rows]) if open_rows else None})

# open stretches shorter than MIN_RUN (not touching either edge of the look-ahead) are noise
runs = []
cur = []
for x in days:
    if x["open"]:
        cur.append(x)
    else:
        if cur:
            runs.append(cur)
        cur = []
if cur:
    runs.append(cur)
for r in runs:
    touches_edge = (r[0]["i"] == 0) or (r[-1]["i"] == len(days) - 1)
    for x in r:
        x["short"] = (len(r) < MIN_RUN) and not touches_edge

W = [x for x in days if x["i"] < WINDOW_DAYS]
for x in W:
    n = NB.get(iso(x["d"]))
    x["used"] = bool(x["open"] and not x.get("short") and x["price"] is not None and n is not None)
    if x["used"]:
        x["eff"] = x["price"] * fee_mult                  # fee-inclusive, like neighborhood prices
        x["bench"] = n["median_price"] if BENCHMARK == "median" else n["high_price"]
        x["over"] = x["eff"] / x["bench"] - 1
used = [x for x in W if x["used"]]

# ---- 4. the three checks (Yes/No) ----
def occ_bench(window, n_days):
    if BENCHMARK == "p75" and MO:
        m = mean([MO.get(iso(today + dt.timedelta(days=i))) for i in range(n_days)])
        if m is not None:
            return m, "market high"
    return kv("occupancy_neighborhood_adjusted", window), "neighborhood"

behind = False
occ_detail = {}
bench_label = "neighborhood"
for window, n_days in (("0_30", 30), ("0_60", 60)):
    lo = kv("occupancy_adjusted", window)
    hi, bench_label = occ_bench(window, n_days)
    occ_detail[window] = {"listing": None if lo is None else round(lo, 3), "benchmark": None if hi is None else round(hi, 3)}
    if lo is not None and hi is not None and lo < hi and lo < OCC_CEILING:
        behind = True

open_count = len([x for x in W if x["open"]])
pb7 = kv("pickup_bookings", "7_0")
stalled = bool(pb7 == 0 and open_count >= STALL_MIN_OPEN)

big_days = [x["d"] for x in used if x["over"] > BIG]
if not big_days:
    c3 = "No"
else:
    c3 = "Yes" if len(big_days) / float(len(used)) >= 0.10 else "Yes, but small"
    if len(big_days) >= 3:   # "mostly <range>" when >=70% of the flagged nights sit inside 14 days
        best = (0, 0)
        for a in range(len(big_days)):
            cnt = 0
            end = a
            for b in range(a, len(big_days)):
                if (big_days[b] - big_days[a]).days <= 13:
                    cnt += 1
                    end = b
            if cnt > best[0]:
                best = (cnt, a, end)
        if best[0] >= 0.7 * len(big_days):
            c3 = c3 + ", mostly " + fmt(big_days[best[1]]) + "\u2013" + fmt(big_days[best[2]])

checks = {"c1": "Yes" if behind else "No", "c1_label": "Occupancy behind " + ("market high" if bench_label == "market high" else "the neighborhood"),
          "c2": "Yes" if stalled else "No", "c3": c3}

# ---- 5. weekly rollup: Sunday-Saturday weeks, weekday = Sun-Thu, weekend = Fri/Sat ----
def week_start(d):
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


weeks = {}
for x in W:
    ws = iso(week_start(x["d"]))
    weeks.setdefault(ws, {"WD": [], "WE": []})
    if x["used"] and x["over"] >= FLAG_MIN:
        weeks[ws]["WE" if x["d"].weekday() in (4, 5) else "WD"].append(x["over"] * 100)
weekly = []
for ws in sorted(weeks):
    wd, we = weeks[ws]["WD"], weeks[ws]["WE"]
    tot = wd + we
    s = dt.date.fromisoformat(ws)
    weekly.append({"start": ws,
                   "wd": round(mean(wd)) if wd else None,
                   "we": round(mean(we)) if we else None,
                   "tot": round(mean(tot)) if tot else None,
                   "partial": bool(s < today or (s + dt.timedelta(days=6)) > last_day)})

# ---- 6. heatmap rows: [iso date, day-of-week (Sun=0), % vs benchmark | "unavail" | "skip", rate, benchmark] ----
daily = []
for x in W:
    dow = (x["d"].weekday() + 1) % 7
    if x["used"]:
        daily.append([iso(x["d"]), dow, round(x["over"] * 100, 1), round(x["eff"]), round(x["bench"])])
    else:
        daily.append([iso(x["d"]), dow, "skip" if x["open"] else "unavail", None, None])

notes = []
if units > 1:
    notes.append("Multi-unit listing (" + str(units) + " units): rates are averaged across the open units on each date.")
if fee_src in (None, "none"):
    notes.append("No fee setting found, so the fee multiplier is 1.0 and guest fees are not included in the comparison.")
elif fee_src == "estimate":
    notes.append("Fee multiplier is estimated from recent reservations.")
skipped = len([x for x in W if x["open"] and x.get("short")])
if skipped:
    notes.append(str(skipped) + " open night(s) skipped (open stretches shorter than " + str(MIN_RUN) + " nights).")
if BENCHMARK == "p75" and not MO:
    notes.append("Market-high occupancy was unavailable, so occupancy was compared with the neighborhood instead.")
if pb7 is None:
    notes.append("Recent-booking data was unavailable, so the stalled check defaulted to No.")

return {"status": "ok", "listing": listing_info, "params": params, "today": iso(today),
        "fee": {"mult": round(fee_mult, 2), "source": fee_src}, "checks": checks, "weekly": weekly,
        "daily": daily, "notes": notes,
        "stats": {"open_nights": open_count, "nights_compared": len(used),
                  "nights_above": len([x for x in used if x["over"] >= FLAG_MIN]),
                  "nights_big": len(big_days), "occupancy": occ_detail, "bookings_7d": pb7}}
