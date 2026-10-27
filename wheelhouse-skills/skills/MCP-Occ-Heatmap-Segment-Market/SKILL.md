---
name: MCP-Occ-Heatmap-Segment-Market
description: "Builds a night-by-night occupancy heatmap for one Wheelhouse portfolio segment against the bedroom-matched market benchmark, live through the connected Wheelhouse MCP, in Wheelhouse brand colors. Use when the user wants an occupancy heatmap or calendar, a night-by-night 'occupancy vs market' view for a segment, or asks where the soft nights are in a month. For a month-by-month line chart against market high performers use MCP-segment-vs-market-occupancy-graph; for pace vs. last year use MCP-stly-pacing-calculations."
---

# Segment vs. market occupancy heatmap

One heatmap: every night of the chosen month(s) as a cell, colored by the
segment's booked share **minus** the market's for the same bedroom mix, in
percentage points. Delivered as a self-contained HTML page (an artifact, where the client supports them).

Needs the Wheelhouse MCP connected, plus at least one Pro tier listing in the
segment's market — the market benchmark is Pro-gated and returns nothing
otherwise. No API key, no files.

## Ask first: which segment, which months

Neither has a safe default. A guessed segment silently reports on the wrong
listings; "the next few months" means something different every week.

Call `wheelhouse_rmGetSegments`, show the real id / name list, let the user pick
one. Ask for calendar months — one to four reads well. Worth mentioning: extra
months are nearly free, extra listings cost one call each.

## Cap: 75 listings

Count the segment before pulling anything.

- **75 or fewer** — pull them all.
- **More** — sample 75, spread across the bedroom buckets in proportion to the
  segment's own mix (not the first 75 the API returns; listing order is not
  random and skews the comparison). Then **label every figure as a sample** —
  in the chat, under the title, and in the footer: "75 of 240 listings,
  sampled". An unlabelled sample looks identical to full coverage, which is the
  worst thing this skill can produce.

For portfolios in the hundreds or thousands, say plainly that the result is a
sample and offer to narrow to a smaller segment instead.

## Step 1 — the segment's nights

Use the Wheelhouse MCP's `execute` tool. It takes Python and runs it in the
MCP's own sandbox — **not a script on anyone's machine**, just the tool's input
language. It is the only way to loop over listings without putting every night
into the conversation: a month for 75 listings is ~2,300 night objects, and
aggregating in the block returns about 30 numbers instead.

```python
SEG, START, END = 12345, "2026-09-01", "2026-09-30"   # example values

r = await call_tool("wheelhouse_rmGetSegmentListings",
                    {"segment_id": SEG, "exclude_inactive": True, "per_page": 100})
L = r["result"] if isinstance(r, dict) and "result" in r else r

mix, markets = {}, {}          # bedroom counts -> benchmark weights (mapped to market groups in step 2)
for x in L:
    b = x.get("num_bedrooms"); k = "unknown" if b is None else int(b)
    mix[k] = mix.get(k, 0) + 1
    m = x.get("market_id");    markets[m] = markets.get(m, 0) + 1

day, fails = {}, []
for x in L:                                    # ~25 listings per block
    ch = x.get("channel") or list(x["channel_ids"].keys())[0]
    try:
        c = await call_tool("wheelhouse_rmGetPriceCalendar",
              {"listing_id": str(x["id"]), "channel": ch,
               "start_date": START, "end_date": END})
        nights = c["result"] if isinstance(c, dict) and "result" in c else c
    except Exception as e:
        fails.append([x["id"], str(e)[:80]]); continue
    for n in nights:
        d = day.setdefault(n["stay_date"], {"bk": 0, "av": 0, "bl": 0})
        if n.get("is_booked"):      d["bk"] += 1
        elif n.get("is_available"): d["av"] += 1
        else:                       d["bl"] += 1

return {"n": len(L), "mix": mix, "markets": markets, "fails": fails, "counts": day}
```

Three things that will bite otherwise: the sandbox has **no standard library**
(any `import` raises), `call_tool` wraps results in `{"result": ...}`, and a
block **hard-times-out at 30 seconds** — hence ~25 listings each, continued
across blocks for a bigger segment. Never parallelise; the API allows 60
requests/minute and concurrency just hits the ceiling sooner.

Return the raw `bk / av / bl` counts, not a finished share. They drive the
tooltip and are what make a surprising cell interpretable.

**Booked share** = `booked / (booked + available)`. Blocked nights are excluded
from both sides — that is what makes it *adjusted* occupancy. Classify in this
order: `is_booked` → booked, else `is_available` → open, else blocked. Testing
availability first inflates occupancy.

A multi-unit listing returns one row per unit per date; count every row, don't
de-duplicate by date.

Only one page is read above (`per_page` 100). For a bigger segment, keep paging
until a page returns fewer than `per_page` items before counting.

**Don't substitute a KPI endpoint.** `rmGetListingKpis` and
`rmGetBulkListingKpis` give rolling windows, not per-night values.
`rmGetSegmentAggregatedMetrics` is your own listings, monthly, and it lags — on
a live segment it showed 11 booked nights where the calendars showed 20. Fine
as a sanity check, never as the source.

## Step 2 — the market benchmark

First call `wheelhouse_rmGetMarketBedroomGroups` for the market. Bedroom groups
differ from market to market (one market might use `0`, `1`, `2+`; another goes
up to `6+`) and can change when the report is regenerated, so never hard-code
them. Map each bedroom count from step 1 into its group: the exact group if one
exists, otherwise the `N+` group it falls under. Passing a value that isn't one
of the market's groups returns a 400.

Then call `wheelhouse_rmGetMarketTimeSeries` once per bedroom group present in
the segment and read `occupancy_adjusted` from each daily row. This is the
whole-market series, not a neighborhood one — don't relabel it.

Omit the `metric` parameter and take every field. One live run found that
passing `metric` returned rows without the occupancy fields and no error. If
you do pass it and the occupancy fields are missing, that is why.

These calls have taken about **7 seconds each** in testing, so only 2–3 fit per block — five in
one block times out. Split across two blocks and return the raw daily series.

A bucket can come back with an **empty `data` array** without raising, usually
where the market has no Pro coverage. Check it. Never treat a missing series as
zero: that paints the month green and reads as huge outperformance.

## Step 3 — blend, then difference

The market series is far broader than one segment, so an unfiltered comparison
mostly measures composition. Weight each bedroom bucket's market series by that
bucket's share of the segment:

```
benchmark(night) = Σ  (listings in bucket / total listings) × market_bucket(night)
difference       = segment booked share − benchmark          → percentage POINTS
```

Worked example — six homes (one 1BR, one 2BR, one 3BR, three 4BR+), Fri 18 Sep,
market at 22.3 / 23.4 / 22.1 / 26.5%:

```
(0.223 × 1/6) + (0.234 × 1/6) + (0.221 × 1/6) + (0.265 × 3/6) = 0.246
segment 33.3% − benchmark 24.6% = +8.8pp
```

If a bucket has no market series, drop it **and renormalise** so the remaining
weights still sum to 1 — otherwise the benchmark comes out low and every cell
drifts green.

Percentage **points**, always: 42% against a market at 55% is −13pp, not −24%.
Label it "pp" and say "percentage points" in the footer.

Do this arithmetic in the artifact's JavaScript — inline the day counts, the mix
weights and the raw series, and let the page compute on load, so every figure on
it is auditable from its own inputs.

A ratio view (segment ÷ market, hotel-RM's Market Penetration Index) was built
and deliberately removed: on a near-empty market it swung to 24× off three
bookings. Don't re-add it without a reason.

## Colors — Wheelhouse brand

Seven bands cut at **±3, ±10, ±20 pp**. Magenta behind the market, grey level,
brand green ahead. Magenta is deliberate: it is Wheelhouse's "where I'd focus
next" accent, and the brand rule is that green means up and never marks a
declining metric. Don't swap in red.

| Band | Light bg / text | Dark bg / text |
|---|---|---|
| below −20 | `#7A0064` / `#FFFFFF` | `#FBA8E4` / `#121212` |
| −20 to −10 | `#DF00B8` / `#FFFFFF` | `#DF00B8` / `#FFFFFF` |
| −10 to −3 | `#FBA8E4` / `#121212` | `#5C0A4C` / `#FCE7F6` |
| within ±3 | `#EDEBEE` / `#3A3A3A` | `#2B2830` / `#D6D2DA` |
| +3 to +10 | `#8FE0C0` / `#121212` | `#12503B` / `#E8F7F0` |
| +10 to +20 | `#1AA179` / `#FFFFFF` | `#22C58B` / `#0B1013` |
| above +20 | `#0B5C42` / `#FFFFFF` | `#8DE6C4` / `#0B1013` |

Give each band a **paired** background and text token (`--b3` / `--b3t`) and
define all 14 in each theme state — bare `:root`, `prefers-color-scheme: dark`
guarded as `:root:not([data-theme="light"])`, and `:root[data-theme="dark"]`.
One shared "text on dark" token puts unreadable text on at least one band,
because the ramp inverts between themes.

Page chrome, from the Wheelhouse email spec: banner
`linear-gradient(120deg, #FF32DB, #DF00B8)` with an uppercase letter-spaced
`WHEELHOUSE · REVENUE SUCCESS` eyebrow in `#FFE3F6`; page `#F4F2F5`; white
cards with `#EDEBEE` borders; footer `#FAF7FB`; text `#121212` / `#3A3A3A` /
`#6B6B6B`; section headings led by a colored dot (magenta `#DF00B8`, green
`#22C58B`, blue `#2D9CDB`); up figures `#1AA179`, flat or down grey `#8A8590`,
never red. Dark mode grounds on `#121212` and brightens the magenta to
`#FF32DB`.

## The page

Brand banner, coverage tags, a four-figure stat strip, the heatmap, a few
read-out notes, provenance footer.

The grid is one row per month, columns 1–31, month label at left, weekday
initials above when the window is a single month. Days past a month's end are
empty cells, not zeros. A small dot on Friday and Saturday cells, with
"· dot = Fri/Sat" in the legend.

Hover any night for the long date, both booked shares, the difference in pp, and
the `booked / open / blocked` counts — those counts are what tell a reader
whether a −30pp cell is a problem or four nights of noise.

Footer carries provenance: endpoints, call count, the benchmark's `updated_at`,
failed calendar calls, nights with no benchmark.

If your client has `dataviz` or `artifact-design` skills, load them before
writing the page.

## Say these out loud rather than hiding them

- **Long lead times make the scale forgiving.** Three months out the benchmark
  can sit at 2–10%, so a night with nothing booked scores only −2pp and lands
  in the grey band. Name the lead time, and don't let grey imply a night is fine
  when the counts say zero booked.
- **A uniformly ahead or behind segment saturates the scale.** Seen live: all 30
  nights ahead, 26 by more than 20pp, every cell pinned, only 2 nights in a
  middle band. Correct and useless. When it happens, say so and name the
  narrowest nights in prose.
- **The cut points are unvalidated.** ±3/±10/±20 have only run against a
  six-listing sample portfolio. On the first real
  segment, check how nights spread across the bands and move them if everything
  still bunches at the ends.
- **A small segment swings on single bookings.** At six listings one booking
  moves the figure 17 points.
- **Occupancy alone doesn't diagnose.** Behind the market could be price,
  minimum stay, listing quality, or a calendar opened late. Offer
  `MCP-future-rate-overpricing` or `MCP-stly-pacing-calculations` rather than
  implying a cause.
- Bedroom-matched but **market-wide geography**, and a multi-market segment is
  blended by listing share — no single cell is one market's story.

## When it comes back wrong

- `ModuleNotFoundError` → an import crept into an `execute` block.
- `TimeoutError ... > 30s` → too many calls in one block. Cut it, don't retry.
- `400 bedrooms does not have a valid value` → use a group returned by
  `wheelhouse_rmGetMarketBedroomGroups` for that market.
- Occupancy fields missing from market rows → `metric` was passed; omit it.
- Every cell green → missing benchmark treated as zero, or weights not
  renormalised after dropping a bucket.
- Every cell empty → benchmark returned nothing; check Pro coverage.
- Occupancy too high → availability tested before booked.
- Disagrees with the app → same segment? same `exclude_inactive`? or the app is
  showing the monthly aggregate, which lags.