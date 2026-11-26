# STAGE 2 -- paste into the Wheelhouse MCP `execute` tool (call_tool is already in scope).
# Read-only. 2 calls per listing (neighborhood pricing + fee multiplier).
# Keep ROWS to <= ~20 listings per run: the API allows 60 requests/minute and this script
# retries on rate limits, but long runs can time out. Run extra batches and concatenate the output.
#
# ROWS = the candidate dicts from stage 1 (copy them in as-is; only id, ar and acur are read).

ROWS = [
    # {"id": 12345678, "t": "Example 3BR Beach House", "ar": 202, "acur": "USD", ...},
]

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

def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None

out = []
for row in ROWS:
    r = dict(row)
    r.update({"nmed": None, "np25": None, "np75": None, "cnt": None, "ncur": None,
              "mult": None, "src": None, "err": None})
    try:
        # Neighborhood = comparable same-bedroom listings nearby. Prices INCLUDE guest fees.
        nb = await call("wheelhouse_rmGetNeighborhoodPricing", {"listing_id": str(r["id"]), "channel": "wheelhouse"})
        data = sorted((nb.get("data") or nb.get("result") or []), key=lambda x: x["stay_date"])[:30]   # next 30 nights
        r["nmed"] = avg([x.get("median_price") for x in data])
        r["np25"] = avg([x.get("low_price") for x in data])
        r["np75"] = avg([x.get("high_price") for x in data])
        cnts = [x["listings_count"] for x in data if x.get("listings_count") is not None]
        r["cnt"] = min(cnts) if cnts else None            # smallest comp set across the window
        r["ncur"] = nb.get("currency")
        if data:
            # Fee multiplier turns the listing's nightly rate into a fee-inclusive rate.
            fc = await call("wheelhouse_rmGetFeeImpactCalendar", {
                "listing_id": str(r["id"]), "channel": "wheelhouse", "fallback": "estimate",
                "start_date": data[0]["stay_date"], "end_date": data[-1]["stay_date"]})
            fe = fc.get("result") or fc.get("data") or [] if isinstance(fc, dict) else []
            r["mult"] = avg([x.get("fee_multiplier") for x in fe])
            r["src"] = fe[0].get("source") if fe else None   # 'setting' = real; 'none'/'estimate' with 1.0 = fees not configured
    except Exception as e:
        r["err"] = str(e)[:120]
    out.append(r)
return out
