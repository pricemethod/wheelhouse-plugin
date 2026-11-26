# Paste this whole file as the `code` of ONE Wheelhouse MCP `execute` call,
# after filling in CONFIG. It runs inside the Wheelhouse sandbox: only
# asyncio/datetime/json/math/re exist, call_tool() is in scope, and at most
# 50 call_tool() calls are allowed. Returns compact JSON for the picker.

CONFIG = {
    "lat": 0.0, "long": 0.0,          # example listing / complex coordinates
    "radius_mi": 0.6,                  # search filter only, never scored
    "bedrooms": 2,
    "sources": None,                   # None = all; else subset of ["A","V","B"]
    "example_class": "apartment",      # apartment | house | room | hotel
    "complex_name": "",                # exact name, lowercase
    "complex_variations": [],          # lowercase variations, e.g. "lakeside resort"
    "fwd_min_bookable_365": 122,       # user's future minimum, pro-rated to 365 days
    "lookback": "365",                 # "365" or "90" (only trailing windows the API has)
    "lookback_min_nights": 150,        # minimum bookable nights actually available within that window
    "min_adjusted_occupancy": 0.2,     # trailing adjusted occupancy must exceed this (strict >)
    "own_channel_ids": [],             # strings, from rmGetListings channel_ids values
    "own_owner_names": [],             # lowercase host names to treat as "own"
    "include": [],                     # listing_ids (int) or url / title fragments (lowercase str)
    "exclude": [],                     # same format
    "view_terms": [],                  # lowercase, e.g. ["ocean view", "oceanfront"]
    # Thresholds: ask the user every run (defaults in brackets in SKILL.md)
    "prox_full_mi": 0.12,              # full proximity credit within this distance
    "prox_zero_mi": 0.6,               # no proximity credit at or beyond this distance
    "stale_days": 30,                  # last scrape older than this = dead listing
    "fwd_bookable_bands": [180, 270],  # future bookable nights (next 365) for 0.75 / 1.0 openness credit
    "open_full": 0.8,                  # lookback open share that earns full openness credit
    "fwd_occ_full": 0.75,              # forward open occupancy that earns full credit
    "fwd_occ_band_floor": 0.4,         # lowest forward-occupancy threshold tested (bands step up 5pts from here to fwd_occ_full)
    "trail_occ_full": 0.8,             # trailing adjusted occupancy that earns full credit
    "weight_same": 0.40, "weight_open": 0.25, "weight_perf": 0.35,  # overall-score weights, must sum to 1.0
    "max_pages": 4,
}

import json, math, re, datetime

C = CONFIG
MI = 1609.34
CALLS = [0]
LIMIT = 48
BASE = {"lat": C["lat"], "long": C["long"], "radius": int(C["radius_mi"] * MI),
        "min_bedrooms": C["bedrooms"], "max_bedrooms": C["bedrooms"],
        "min_open_occupancy_365_0": 0, "min_bookable_nights_365_0": 0,
        "per_page": 100}

async def pull(extra, keep_rows=False):
    out = {} if keep_rows else set()
    truncated = False
    for p in range(1, C["max_pages"] + 1):
        if CALLS[0] >= LIMIT:
            truncated = True
            break
        a = dict(BASE); a.update(extra); a["page"] = p
        CALLS[0] += 1
        r = await call_tool("wheelhouse_rmGetSetCandidates", a)
        res = (r or {}).get("result", []) or []
        for x in res:
            if keep_rows:
                out[x["listing_id"]] = x
            else:
                out.add(x["listing_id"])
        if len(res) < 100:
            break
        if p == C["max_pages"]:
            truncated = True
    return out, truncated

rows, trunc_all = await pull({}, keep_rows=True)
fwd_gate, t1 = await pull({"min_bookable_nights_0_365": C["fwd_min_bookable_365"]})
FB = sorted(C["fwd_bookable_bands"])
fwd_180, _ = await pull({"min_bookable_nights_0_365": max(FB[0], C["fwd_min_bookable_365"])})
fwd_270, _ = await pull({"min_bookable_nights_0_365": max(FB[1], C["fwd_min_bookable_365"])})
lo = min(C["fwd_occ_band_floor"], C["fwd_occ_full"])
hi = max(C["fwd_occ_band_floor"], C["fwd_occ_full"])
_bands = []
_b = lo
while _b < hi - 1e-9:
    _bands.append(round(_b, 4))
    _b += 0.05
_bands.append(round(hi, 4))
OCC_BANDS = sorted(set(_bands))
occ_sets = {}
for b in OCC_BANDS:
    occ_sets[b], _ = await pull({"min_open_occupancy_0_365": b})

CLASS = {"apartment": "apartment", "house": "house", "cabin": "house",
         "room": "room", "hotel": "hotel", "bnb": "other", "other": "other",
         "camping": "camping"}
PT_APT = ("condo", "apartment")

def cls(x):
    rt = CLASS.get((x.get("room_type") or "").lower(), "other")
    pt = (x.get("property_type") or "").lower()
    if rt == "other" and any(k in pt for k in PT_APT):
        return "apartment"
    return rt

def url_id(u):
    m = re.findall(r"(\d{5,})", u or "")
    return m[-1] if m else ""

def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())

def matches(x, terms):
    t = norm(x.get("title")); u = (x.get("url") or "").lower()
    for term in terms:
        if isinstance(term, int) and term == x["listing_id"]:
            return True
        if isinstance(term, str) and term and (norm(term) in t or term in u):
            return True
    return False

def parse_ts(s):
    try:
        return datetime.datetime.strptime((s or "")[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None

try:
    now = datetime.datetime.now()
except Exception:
    now = max([t for t in (parse_ts(x.get("updated_at")) for x in rows.values()) if t] or [None])

def age_days(s):
    d = parse_ts(s)
    if d is None or now is None:
        return 999
    return (now - d).days

own_ids = set(str(i) for i in C["own_channel_ids"])
counts = {"pulled": len(rows), "excluded_list": 0, "own": 0, "ota": 0,
          "type_mismatch": 0, "insufficient_history": 0, "stale": 0,
          "low_adjusted_occupancy": 0, "future_bookable": 0}
names_exact = [norm(C["complex_name"]).strip()] if C["complex_name"] else []
names_var = [norm(v).strip() for v in C["complex_variations"] if v]
out = []

for lid, x in rows.items():
    pinned = matches(x, C["include"])
    if matches(x, C["exclude"]):
        counts["excluded_list"] += 1; continue
    if url_id(x.get("url")) in own_ids or (x.get("owner_name") or "").lower() in C["own_owner_names"]:
        counts["own"] += 1; continue
    if C["sources"] and x.get("source") not in C["sources"] and not pinned:
        counts["ota"] += 1; continue
    k = cls(x)
    title = norm(x.get("title"))
    named = any(n and n in title for n in names_exact + names_var)
    if k == C["example_class"]:
        type_s = 1.0
    elif k == "other" or (named and k == "hotel" and C["example_class"] == "apartment"):
        type_s = 0.5
    else:
        if not pinned:
            counts["type_mismatch"] += 1; continue
        type_s = 0.0
    if C["lookback"] == "90":
        open_share = x.get("nights_percent_open_90_0") or 0
        raw_nights = round(open_share * 90)
    else:
        raw_nights = x.get("nights_bookable_365_0") or 0
        open_share = raw_nights / 365.0
    stale = age_days(x.get("updated_at") or "")
    if raw_nights < C["lookback_min_nights"] and not pinned:
        counts["insufficient_history"] += 1; continue
    if stale > C["stale_days"] and not pinned:
        counts["stale"] += 1; continue
    if (x.get("occupancy_adjusted_365_0") or 0) <= C["min_adjusted_occupancy"] and not pinned:
        counts["low_adjusted_occupancy"] += 1; continue
    if lid not in fwd_gate and not pinned:
        counts["future_bookable"] += 1; continue

    if any(n and n in title for n in names_exact):
        name_s = 1.0
    elif any(n and n in title for n in names_var):
        name_s = 0.75
    else:
        name_s = 0.0
    d = (x.get("distance_meters") or 0) / MI
    tol = C["prox_full_mi"]; span = max(0.01, C["prox_zero_mi"] - tol)
    prox_s = 1.0 if d <= tol else max(0.0, 1 - (d - tol) / span)
    same = 0.5 * name_s + 0.35 * prox_s + 0.15 * type_s

    fwd_b = 1.0 if lid in fwd_270 else (0.75 if lid in fwd_180 else (0.5 if lid in fwd_gate else 0.0))
    openness = 0.5 * min(1.0, open_share / C["open_full"]) + 0.5 * fwd_b

    band = 0.0
    for b in OCC_BANDS:
        if lid in occ_sets[b]:
            band = b
    trail = x.get("occupancy_adjusted_365_0") or 0
    perf = 0.6 * min(1.0, band / C["fwd_occ_full"]) + 0.4 * min(1.0, trail / C["trail_occ_full"])

    overall = C["weight_same"] * same + C["weight_open"] * openness + C["weight_perf"] * perf
    hay = title + " " + " ".join(x.get("amenities") or [])
    view = any(norm(v).strip() in hay for v in C["view_terms"]) if C["view_terms"] else None
    out.append([lid, (x.get("title") or "")[:90], x.get("source"), x.get("url") or "",
                round(d, 2), k, round(name_s, 2), round(same * 100), round(openness * 100),
                round(perf * 100), round(overall * 100), round(band * 100),
                round(trail * 100), round(open_share * 100), 1 if pinned else 0,
                1 if view else 0, round(x.get("adr_365_0") or 0)])

dup = {}
for r in out:
    key = re.sub(r"\s+", " ", norm(r[1])).strip()
    dup.setdefault(key, set()).add(r[2])
for r in out:
    key = re.sub(r"\s+", " ", norm(r[1])).strip()
    r.append(",".join(sorted(s for s in dup[key] if s != r[2])))
out.sort(key=lambda r: -r[10])
counts["scored"] = len(out)
return json.dumps({"cols": ["id", "title", "src", "url", "dist_mi", "type", "name_match",
                            "same", "open", "perf", "overall", "fwd_occ_band", "trail_occ",
                            "open_share", "pinned", "view", "adr", "also_on"],
                   "rows": out, "counts": counts, "calls": CALLS[0],
                   "truncated": trunc_all or t1, "radius_mi": C["radius_mi"]}, separators=(",", ":"))
