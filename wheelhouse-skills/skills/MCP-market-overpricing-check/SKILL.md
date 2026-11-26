---
name: MCP-market-overpricing-check
description: Checks one Wheelhouse listing's next 60 days of rates against the neighborhood (75th percentile by default, or the median; fee-adjusted) and returns ONE report with Yes/No checks (occupancy behind the neighborhood, stalled sales with availability, more than 15% above market), a weekly table of how far above the benchmark the listing is priced (weekday, weekend, total week) and a night-by-night heatmap. Use whenever the user asks whether a listing is overpriced versus the market or neighborhood, which weeks or dates are priced above market and by how much, why a listing with open nights has stalled, to run the overpricing or price-gap check, or to compare rates to the neighborhood median, p75 or high performers, even without the words heatmap or report. Live via the Wheelhouse MCP, one listing at a time. Not for pace vs last year (MCP-stly-pacing-calculations), posted rates vs the listing's own history (MCP-future-rate-overpricing), portfolio rankings (MCP-leaderboard-price-gap-priority-neighborhood) or changing rates (xContext-custom-rates).
---

# Market Overpricing Check (single listing)

Answers: "Where in the next 60 days am I priced above the market, by how much, and does it matter for this listing right now?" It is the single-listing building block for a later portfolio version, so the analysis is kept separate from the display.

## What you return

Exactly one report that holds all three parts together. In Claude chat, render it as one inline widget (`show_widget`). If your client has no inline widget tool, save the filled template as an HTML file in the user's working folder (or publish it as an artifact), open or link it, and say where it is.

1. **Checks** - three rows, Yes or No.
2. **Weeks priced above the benchmark** - a table, one row per week.
3. **Night-by-night heatmap** - weeks as rows, Sun to Sat as columns, plus a total-week column.

Put everything in the one report. Text written before a widget can be lost on some screens, and the tables and heatmap read best side by side. After the report, write at most one short sentence. Do not repeat the tables in text.

## Workflow

1. **Resolve the listing.** Use the listing's `wheelhouse_id` as `listing_id` with `channel = "wheelhouse"`. If the user gives a name, find it with `wheelhouse_rmGetListings`. Ask only if the name is ambiguous.
2. **Pick the benchmark.** Default `p75` (the neighborhood 75th percentile). Use `median` when the user asks for the median or the neighborhood average. Say which one you used in the report (the template does this).
3. **Run the analysis.** `view` `scripts/analyze_listing.py`, set the PARAMETERS block, and paste the whole file into the Wheelhouse `execute` tool. One listing per call (about 6 MCP calls, well inside the roughly 30-second sandbox limit). The script returns one dict.
4. **Render.** `view` `assets/report_template.html`, replace the JSON between `DATA_START` and `DATA_END` with the dict from step 3 (valid JSON; keep `null`, drop nothing), and pass the result to `show_widget` (or save it as an HTML file, as above). Do not edit the template's logic or styling unless the user asks.
5. **Close** with one short sentence at most (for example, that gray cells are nights that are not available).

If the script returns `status: "skipped_high_occupancy"`, render the template anyway; it shows the one-line message instead of the tables.

## Output rules

- **Checks table:** Yes or No only, no data values, no noise-filter row. Check 3 may carry a short qualifier ("Yes, but small", "Yes, mostly Nov 13-20"); the script writes it.
- **Weekly table:** percentages only. Cells show the average % over the benchmark on the nights that are over it. Columns: Week of (Sun), Weekday (Sun-Thu), Weekend (Fri/Sat), Total week. Use a dash where nothing is above. Partial weeks are labeled.
- **No separate ">15%" table.** The weekly table and heatmap already show magnitude.
- **No "How to read it" section.**
- **Heatmap:** diverging scale, blue below the benchmark and orange to red above, so the user can also see underpriced stretches. Gray cells are not available; "skip" cells are open stretches too short to count.

Any rate change that follows goes through `xContext-custom-rates` (date-specific) or `xContext-preferences` (engine settings) after the user confirms. Neighborhood prices are fee-inclusive; `xContext-market-data` explains the fee basis.

## Definitions

- **Fee-adjusted rate** = posted rate x the fee multiplier from `wheelhouse_rmGetFeeImpactCalendar` (`fallback = "estimate"`). Neighborhood and market prices include fees, so comparing without the multiplier understates how high a listing is priced. If there is no fee setting the multiplier is 1.0 and the template says so.
- **Benchmark** = the neighborhood price for that night: `high_price` (75th percentile) or `median_price`, bedroom-adjusted, from `wheelhouse_rmGetNeighborhoodPricing`. Compared night by night; weeks are only for display.
- **Check 1, occupancy behind:** with `p75`, adjusted occupancy below the market's high-performer tier for the same bedroom count (`wheelhouse_rmGetMarketTimeSeries`, `performance = "high"`) in either the 0-30 or 0-60 day window. With `median`, below neighborhood adjusted occupancy. A listing at or above 80% adjusted occupancy never counts as behind.
- **Check 2, stalled with availability:** zero bookings in the last 7 days (`pickup_bookings`, window `7_0`) and at least 10 open nights in the window. Use `pickup_bookings`, not `last_booked_days`, which is unreliable looking forward.
- **Check 3, more than 15% above market:** at least one open night more than 15% above the benchmark. "Yes" when those nights are 10% or more of the compared nights, otherwise "Yes, but small"; a ", mostly <range>" suffix is added when 70% of them fall inside 14 days.
- **Open night:** available and not booked or blocked. Open stretches shorter than 3 nights that do not touch either edge of the window are skipped as orphan-gap noise.
- **Weeks** run Sunday to Saturday so the Fri/Sat weekend stays inside one week. A night counts as "above" at +0.5% or more (it displays as +1%).

## Things that can surprise you

- **Multi-unit listings** return one calendar row per unit per date. The script treats a date as open if any unit is open and averages the open units' rates; the report notes the unit count. Do not compare their occupancy with single-unit listings without saying so.
- **Underpriced listings are valid results.** A listing can be behind the market and still show no overpriced nights (priced far below the neighborhood). Report that plainly: the heatmap is mostly blue and price is not the lever. Some sample or hypothetical listings have neighborhood comps far above their own rates; if a listing is below the neighborhood 25th percentile on nearly every night, mention that the comps may not be a fair comparison.
- **View-only listings are fine.** Every call here is a read.
- **MCP array parameters** silently honor only the last value, so pass one `metric` per call (the script already does).
- **Rate limit** is 60 requests a minute. The script retries on 429; do not loop several listings inside one `execute` block.

## Scope and what comes next

This skill handles one listing per run. For a portfolio-wide scan ranked by occupancy gap, pickup and price vs the neighborhood, use `MCP-leaderboard-price-gap-priority-neighborhood`. A portfolio version of this night-by-night check (up to about 200 listings) needs two calls per listing at minimum (price calendar and neighborhood pricing), so roughly 450-500 calls, around 8-9 minutes at 60 a minute. That should run as a script or app using an API key (the chat sandbox's per-block limit rules it out), with the same daily logic, the same JSON per listing, and a ranking on top: listings by flagged nights times percent over, and date ranges by how many listings are over-priced in them.

## Output schema (returned by the script, read by the template)

`status`, `listing {id, title, bedrooms, units, access, auto}`, `params {benchmark, big, window_days}`, `today`, `fee {mult, source}`, `checks {c1, c1_label, c2, c3}`, `weekly [{start, wd, we, tot, partial}]`, `daily [[iso date, day of week (Sun=0), % vs benchmark or "unavail"/"skip", rate, benchmark]]`, `notes []`, `stats {...}`. `stats` is for your own sanity checks and is not displayed.
