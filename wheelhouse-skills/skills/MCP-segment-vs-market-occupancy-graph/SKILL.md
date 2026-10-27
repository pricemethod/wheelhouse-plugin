---
name: MCP-segment-vs-market-occupancy-graph
description: "Builds an interactive month-by-month occupancy line chart for one Wheelhouse portfolio segment against a market's high performers — current on-the-books position only, no last-year comparison — live through the connected Wheelhouse MCP, in Wheelhouse brand colors. Use for 'how are we pacing against the market right now', a current occupancy graph by month, or a two-line segment-vs-market chart. For a night-by-night view use MCP-Occ-Heatmap-Segment-Market; for pace vs. last year use MCP-stly-pacing-calculations."
---

# Segment vs. market occupancy graph (current only)

Two lines, one point per calendar month:

| Series | What it is |
|---|---|
| `<Segment name>` | The segment's adjusted occupancy **on the books today** |
| `<Market> high performers` | The benchmark's adjusted occupancy on the books today |

Nothing else. **No last-year lines, no final actuals, no year-over-year.** If
the user wants a comparison with last year, that is `MCP-stly-pacing-calculations`
(on-the-books pace vs. the same time last year). Don't bolt last-year series
onto this chart.

Both series toggle from the legend and the y-axis rescales to what is left on.
Delivered as a self-contained HTML page (an artifact, where the client supports them).

Needs the Wheelhouse MCP connected and at least one Pro tier listing in the
chosen market - the market report is Pro-gated and returns nothing otherwise.
No API key, no files, no cache.

## The benchmark is high performers

`performance: "high"` on the market series, every time, unless the user says
otherwise. The point of this chart is "how do we pace against the homes that win
this market," not against a market average dragged down by listings nobody is
competing with.

Don't ask about the tier - just use it, and say which benchmark you used in the
reply. The endpoint also accepts `average` and `low`, and omitting `performance`
gives the whole market; switch only when the user asks for one of those in
words ("against the whole market", "versus average listings"). When you do
switch, relabel the series, the eyebrow and the footer to match - a chart
labelled "high performers" showing whole-market numbers is the worst failure
this skill has.

The tier is a **subset** of the market's listings, so it is narrower and noisier
than the whole market. Quote how narrow in the reply (see below).

## Ask first - three things

Ask all three together (in one question tool call, if your client has one). Don't start pulling until they
are answered.

1. **Which segment.** Call `wheelhouse_rmGetSegments` and show the real id /
   name list. The chosen segment's **name goes on the artifact** - never "my
   segment", never "your portfolio".
2. **Which market.** Pull `wheelhouse_rmGetSegmentListings` for the chosen
   segment and collect the distinct `market_id` values with a listing count
   each; those are the natural candidates. Get their names from
   `wheelhouse_rmGetMarketReport` (takes a country; the segment's listings carry
   `location.country`). A single-market segment with one obvious answer can skip
   straight to it; say which one you used. A multi-market segment benchmarked
   against one market is legitimate but must be said out loud.
3. **Which months.** Ask for calendar months. The market time series runs
   **3 years back to 1 year forward**, so a month more than ~12 months out has
   no benchmark at all. Three to six months reads best.

Unattended and unable to ask: use the default segment, its dominant market and
the next four months, and state all three assumptions at the top of the reply.

## Step 1 - the segment, month by month

`wheelhouse_rmGetSegmentAggregatedMetrics`, through the MCP's `execute` tool.
One window only - no last-year loop.

```python
SEG = 12345   # example value
MONTHS = ["2026-09-01","2026-10-01","2026-11-01","2026-12-01"]
out = {}
for d in MONTHS:
    r = await call_tool("wheelhouse_rmGetSegmentAggregatedMetrics",
                        {"segment_id": SEG, "dates": [d]})
    row = r["data"][0]
    out[d] = {"occ_adj": row["occupancy_adjusted"],
              "occ": row["occupancy"],
              "booked": row["nights_booked"],
              "bookable": row["nights_bookable"],
              "calendar": row["nights_calendar"]}
return out
```

**`dates` takes an array but only honours the last entry.** Passing four dates
returns one row - for the *last* month in the list, with no error and no hint
that three were dropped. Call it once per month, in a loop, as above. This is
the single most likely way to ship a chart of the wrong months.

Keep `booked` and `bookable` for every month. They go in the tooltip, and they
are what tells a reader whether a low figure is a problem or three nights of
noise.

## Step 2 - the benchmark

`wheelhouse_rmGetMarketTimeSeries` returns **daily** rows; aggregate to months
yourself.

```python
def roll(r):
    agg = {}
    for row in r["data"]:
        m = row["stay_date"][:7]
        a = agg.setdefault(m, {"n":0,"wb":0.0,"woa":0.0})
        nb = row.get("nights_bookable") or 0
        a["n"] += 1; a["wb"] += nb
        a["woa"] += (row.get("occupancy_adjusted") or 0) * nb
    return {m: {"occ_adj": v["woa"]/v["wb"], "bookable_avg": v["wb"]/v["n"]}
            for m, v in agg.items()}

hi = await call_tool("wheelhouse_rmGetMarketTimeSeries",
      {"market_id": 678, "start_date": "2026-09-01", "end_date": "2026-12-31",
       "performance": "high"})
allm = await call_tool("wheelhouse_rmGetMarketTimeSeries",
      {"market_id": 678, "start_date": "2026-09-01", "end_date": "2026-12-31"})
return {"updated_at": hi.get("updated_at"), "high": roll(hi), "whole": roll(allm)}
```

**Do not pass the `metric` parameter.** Sending
`metric=["occupancy_adjusted", ...]` returns rows containing only
`nights_bookable` - the occupancy fields vanish, with no error. Omit `metric`
entirely and take every field. If the market line comes back flat at zero, this
is why.

Weight each day by `nights_bookable`, never a plain mean of daily rates: market
inventory moves day to day and an unweighted average quietly overweights thin
days.

The second call (no `performance`) is the whole market, pulled **only** to
compare `bookable_avg` so the reply can say how narrow the tier is. It never
goes on the chart.

Both calls fit one `execute` block for a four-to-six month window, which is the
whole reason this skill is cheaper than the night-by-night heatmap. Watch the **30-second hard
timeout** if the window is longer - split then. The sandbox has no standard
library (any `import` raises) and `call_tool` may wrap results in
`{"result": ...}`.

`bedrooms` and `property_type` are available if the user asks for a
bedroom-matched benchmark; `bedrooms` is an enum read from
`wheelhouse_rmGetMarketBedroomGroups`, not a free number.

## Step 3 - the page

If your client has `dataviz` or `artifact-design` skills, load them before
writing it. Publish it as an artifact where the client supports them;
otherwise save it as an HTML file and give the user the path.

**Colors - Wheelhouse brand, light only.** The brand rule is a white ground,
never a dark page, so commit to one theme and paint every color explicitly
rather than shipping half a dark palette.

| Role | Hex |
|---|---|
| Segment | `#DF00B8` (brand magenta), solid, 2.5px |
| Benchmark | `#57534E` (warm stone), solid, 2.5px |
| Header band | `linear-gradient(90deg, #FF32DB, #DF00B8)` |
| Page / surface | `#FAF9F8` / `#FFFFFF` |
| Ink / secondary / muted | `#121212` / `#57534E` / `#78716C` |
| Rules / grid / axis | `#E7E5E4` / `#EFEDEB` / `#D6D3D1` |
| Table header fill | `#FCE7F6` |

Two series, two hues, no dashes and no light tints - lighter tints would only be
needed to mark last year, and there is no last year here. Both
hexes clear 3:1 on white and clear the CVD and normal-vision gates as a pair.
Magenta is the segment because it is Wheelhouse's "this is you" accent; the
benchmark is a deliberate warm neutral because a benchmark should recede.

**Layout - these seven things and nothing else:**

1. Brand gradient band, an eyebrow reading `<Market> - high performers`, the
   title, and one sentence naming the segment and defining adjusted occupancy.
2. A gap strip above the chart: one small tile per month showing the segment's
   lead or deficit in **percentage points**, signed, magenta when ahead and
   muted grey when behind. Never red - the brand rule is that green means up
   and red is not a brand color. Percentage *points*, always: 42% against a
   benchmark at 55% is -13pp, not -24%.
3. Legend of two toggle chips. Never let the last one be turned off - guard it,
   an empty chart is a bug.
4. The line chart: recessive grid, month labels with the year beneath, 4-5px
   markers with a 2px white ring. Direct labels at the right edge - a short
   colored stroke, the final value in ink, the series short name in muted -
   pushed apart on collision, clamped inside the plot, and dropped below ~580px
   in favour of the legend.
5. Crosshair tooltip listing both visible series at the hovered month, value
   first and series name second, plus the segment's `booked / bookable` night
   counts and the gap in pp. Same readout on keyboard arrow keys.
6. A "Show data table" toggle with every figure including the gap row, so
   nothing lives only in a tooltip. A one-line footer stamp: the benchmark used,
   "on the books, not a forecast", the series' `updated_at`, and the date the
   segment was read.
7. Redraw on resize against measured pixel width - a fixed viewBox scaled down
   turns 12px axis text into 6px on a phone.

**No prose block on the page.** No "what the lines say", no "about this data",
no takeaways, no caveats panel. The artifact is the gap strip, the chart, the
legend, the table and the one-line footer. Everything else - interpretation
*and* caveats - goes in the chat reply.

## Read it out in the chat

Name the benchmark in the first sentence: high performers in `<market>`, not
the whole market. Then which months the segment leads, which it trails, and
where the gap is widest. Then the caveats that did not go on the page:

- **How narrow the benchmark is** - quote the tier's average `nights_bookable`
  against the whole market's from step 2.
- **A month already underway is not pace.** If the window starts in the current
  month, most of it is settled actuals with only the remaining nights still
  sellable. Say so rather than letting it sit on the same line as forward
  months.
- **Long lead times make small absolute gaps look dramatic.** If the benchmark
  itself is only single-digit occupied, say that before drawing a conclusion -
  at 5% benchmark occupancy a 5pp gap is a handful of bookings.
- **A small segment swings on single bookings.** Quote the segment's bookable
  nights so the reader can size one booking's effect.

Offer two follow-ups in one line each: the whole-market version (a single re-run
with `performance` omitted), and `MCP-Occ-Heatmap-Segment-Market` if they want
to see which individual nights are soft.

Occupancy alone doesn't diagnose. Behind the benchmark could be price, minimum
stay, listing quality or a calendar opened late - offer
`MCP-future-rate-overpricing` or `MCP-stly-pacing-calculations` rather than implying a cause.

## When it comes back wrong

- **One month of segment data instead of all of them** - `dates` was passed as
  an array. Loop one date per call.
- **Market line flat at zero, or only `nights_bookable` in the rows** - the
  `metric` parameter was passed. Omit it.
- **Market data empty** - no Pro tier listing in that market, or the window
  falls outside 3 years back / 1 year forward.
- **Benchmark looks suspiciously like the whole market** - the whole-market
  call's result was charted instead of the `performance: "high"` one. They are
  two variables in the same block; check which one reached the page.
- **`TimeoutError ... > 30s`** - too many calls in one `execute` block. Split
  it; don't retry unchanged.
- **`ModuleNotFoundError`** - an `import` crept into an `execute` block.
- **Segment occupancy higher than the app shows** - check `occupancy` vs
  `occupancy_adjusted`. Adjusted excludes blocked nights and is the right
  like-for-like against the benchmark's `occupancy_adjusted`; mixing the two
  inflates one side.
- **Four lines on the page** - last year crept in. This skill is two series.