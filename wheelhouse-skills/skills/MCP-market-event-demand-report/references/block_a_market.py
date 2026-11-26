# Block A - market + events. Paste into ONE call of the Wheelhouse MCP `execute` tool.
# Fill in the CONFIG values. Nothing else should need editing.
# Returns compact JSON (never the daily rows) - save it as report.json.
import datetime

# ---------------- CONFIG ----------------
MARKET_ID = 0                 # market_id from wheelhouse_rmGetMarketReport
TODAY = "YYYY-MM-DD"          # today's date
TRY_STLY = True               # set False to skip the early-access attempt
EVENTS = [
    # {"name": "Great American Beer Festival", "dates_label": "Oct 8-10, 2027",
    #  "next_start": "2027-10-08", "note": "",
    #  "editions": [{"label": "\u201924", "start": "2024-10-10", "end": "2024-10-12"},
    #               {"label": "\u201925", "start": "2025-10-09", "end": "2025-10-11"}]},
]
# ----------------------------------------
HIGH_SCORE = 20      # tier thresholds (see SKILL.md, "Scoring")
MID_SCORE = 8
BASE_WEEKS = 4       # same-weekday baseline, weeks either side

D = datetime.date
ONE = datetime.timedelta(days=1)
def P(s): return D.fromisoformat(s)
def S(d): return d.isoformat()
def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return D(y, m, 1)
def unwrap(r):
    if isinstance(r, dict) and "result" in r and "data" not in r:
        return r["result"]
    return r

today = P(TODAY)
ov_start = add_months(today.replace(day=1), 1)
ov_end = add_months(ov_start, 6) - ONE

def ev_nights(start, end):
    # night before day one through the night before the last day
    s = P(start); e = P(end)
    n = max((e - s).days, 0) + 1
    return [s - ONE + datetime.timedelta(days=k) for k in range(n)]

def nth_weekday(y, m, wd, n):
    d = D(y, m, 1)
    while d.weekday() != wd: d += ONE
    return d + datetime.timedelta(days=7 * (n - 1))
def last_weekday(y, m, wd):
    d = add_months(D(y, m, 1), 1) - ONE
    while d.weekday() != wd: d -= ONE
    return d
def holiday_nights(y):
    out = set()
    th = nth_weekday(y, 11, 3, 4)                        # Thanksgiving: Wed-Sat nights
    for k in range(-1, 3): out.add(th + datetime.timedelta(days=k))
    for dd in range(20, 32): out.add(D(y, 12, dd))       # Christmas - New Year
    out.add(D(y, 1, 1))
    for dd in range(1, 6): out.add(D(y, 7, dd))          # July 4th
    for mon in (last_weekday(y, 5, 0), nth_weekday(y, 9, 0, 1)):   # Memorial, Labor Day
        for k in (1, 2, 3): out.add(mon - datetime.timedelta(days=k))
    return out

# ---- every date the report needs ----
blocked = set()
all_nights = []
for ev in EVENTS:
    for ed in ev.get("editions", []):
        ns = ev_nights(ed["start"], ed["end"])
        ed["_n"] = ns
        all_nights += ns
        blocked.update(ns)
for y in range(today.year - 4, today.year + 2):
    blocked.update(holiday_nights(y))

earliest_ok = today - datetime.timedelta(days=365 * 3 - 5)   # API keeps 3 years back
ref_start = add_months(today.replace(day=1), -12)
start = min(add_months(ov_start, -12), ref_start)
if all_nights:
    start = min(start, min(all_nights) - datetime.timedelta(days=7 * BASE_WEEKS))
start = max(start, earliest_ok)

r = unwrap(await call_tool("wheelhouse_rmGetMarketTimeSeries",
           {"market_id": MARKET_ID, "start_date": S(start), "end_date": S(ov_end)}))
currency = r.get("currency")
updated_at = r.get("updated_at")
def clean(rows):
    out = {}
    for row in rows:
        if row.get("occupancy_adjusted") is not None and (row.get("nights_bookable") or 0) > 0:
            out[row["stay_date"]] = row
    return out
day = clean(r.get("data", []))

stly_day = None
stly_note = ""
if TRY_STLY:
    try:
        rs = unwrap(await call_tool("wheelhouse_rmGetMarketTimeSeries",
                    {"market_id": MARKET_ID, "start_date": S(ov_start), "end_date": S(ov_end), "basis": "stly"}))
        stly_day = clean(rs.get("data", []) if isinstance(rs, dict) else [])
        if not stly_day:
            stly_day = None
            stly_note = "stly returned no rows"
    except Exception as e:
        stly_note = str(e)[:160]

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
    return {"occ": booked / b, "adr": adr, "ask": ask, "booked": booked,
            "bookable": b, "listings": b / len(rows), "days": len(rows)}

def month_dates(m0):
    m1 = add_months(m0, 1)
    return [m0 + datetime.timedelta(days=k) for k in range((m1 - m0).days)]
def rnd(v, n):
    return None if v is None else round(v, n)

# ---- trailing-12-month reference ----
ref = []
for i in range(12):
    m0 = add_months(ref_start, i)
    a = agg(month_dates(m0), day)
    if a: ref.append({"month": S(m0)[:7], "occ": a["occ"], "listings": a["listings"],
                      "booked": a["booked"], "bookable": a["bookable"]})
ref_avg = None
reference = None
if ref:
    ref_avg = sum(x["booked"] for x in ref) / sum(x["bookable"] for x in ref)
    pk = max(ref, key=lambda x: x["occ"]); sf = min(ref, key=lambda x: x["occ"])
    reference = {"from": ref[0]["month"], "to": ref[-1]["month"], "avg_occ": rnd(ref_avg, 3),
                 "peak": {"month": pk["month"], "occ": rnd(pk["occ"], 3)},
                 "soft": {"month": sf["month"], "occ": rnd(sf["occ"], 3)},
                 "listings": round(sum(x["listings"] for x in ref) / len(ref))}

# ---- 6-month overview, whole market ----
months = []
for i in range(6):
    m0 = add_months(ov_start, i)
    cur = agg(month_dates(m0), day)
    if stly_day is not None:
        ly = agg(month_dates(m0), stly_day)
    else:
        ly = agg(month_dates(add_months(m0, -12)), day)
    row = {"month": S(m0)[:7]}
    for k in ("occ", "adr", "ask"):
        row[k] = rnd(cur[k], 3 if k == "occ" else 0) if cur else None
        row[k + "_ly"] = rnd(ly[k], 3 if k == "occ" else 0) if ly else None
    row["listings"] = round(cur["listings"]) if cur else None
    months.append(row)

# ---- events ----
events = []; unrated = []
for ev in EVENTS:
    eds = []
    for ed in ev.get("editions", []):
        ns = [n for n in ed["_n"] if n < today]
        if not ns or len(ns) < len(ed["_n"]):
            continue                                   # edition not fully in the past
        base = set()
        for n in ns:
            for k in range(1, BASE_WEEKS + 1):
                for sg in (-1, 1):
                    c = n + datetime.timedelta(days=7 * k * sg)
                    if c not in blocked and c < today: base.add(c)
        a = agg(ns, day); b = agg(sorted(base), day)
        if a is None or b is None: continue
        eds.append({"label": ed["label"], "occ": a["occ"], "base": b["occ"], "adr": a["adr"],
                    "base_adr": b["adr"], "booked": a["booked"], "listings": a["listings"],
                    "nights": len(ns), "base_nights": len(base)})
    if not eds:
        unrated.append({"name": ev["name"], "dates_label": ev.get("dates_label", ""),
                        "reason": "No past edition inside the market data"})
        continue
    occ = sum(e["occ"] for e in eds) / len(eds)
    base = sum(e["base"] for e in eds) / len(eds)
    lift = (occ - base) * 100
    bk = sum(e["booked"] for e in eds)
    adr = sum((e["adr"] or 0) * e["booked"] for e in eds) / bk if bk else None
    prems = [e["adr"] / e["base_adr"] - 1 for e in eds if e["adr"] and e["base_adr"]]
    prem = sum(prems) / len(prems) * 100 if prems else 0
    level = (occ - ref_avg) * 100 if ref_avg is not None else 0
    score = lift + 0.4 * prem + 0.3 * level
    tier = "high" if score >= HIGH_SCORE else ("mid" if score >= MID_SCORE else "low")
    events.append({"name": ev["name"], "dates_label": ev.get("dates_label", ""),
                   "next_start": ev.get("next_start", ""), "note": ev.get("note", ""),
                   "occ": rnd(occ, 3), "base_occ": rnd(base, 3), "lift_pts": rnd(lift, 1),
                   "adr": rnd(adr, 0), "adr_prem": rnd(prem, 1), "score": rnd(score, 1), "tier": tier,
                   "listings": round(eds[-1]["listings"]),
                   "editions": [{"label": e["label"], "occ": rnd(e["occ"], 3),
                                 "nights": e["nights"], "base_nights": e["base_nights"]} for e in eds]})

events.sort(key=lambda e: e["next_start"])
return {"market_id": MARKET_ID, "currency": currency, "data_updated_at": updated_at,
        "data_from": S(start), "data_to": S(ov_end), "generated": TODAY,
        "reference": reference,
        "overview": {"basis": "stly" if stly_day is not None else "ly_final", "stly_note": stly_note,
                     "groups": {"all": {"label": "All bedrooms", "months": months}}},
        "events": events, "unrated": unrated}
