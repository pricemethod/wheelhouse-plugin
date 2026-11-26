---
name: MCP-booking-window-diagnosis
description: "Diagnoses why ONE Wheelhouse listing under-books a booking window (default 30-59 days before arrival) vs. its other windows, the bedroom-matched market and a portfolio segment over the trailing 12 months, live via the connected Wheelhouse MCP. Checks price vs. market, final occupancy vs. market, market year-over-year trends and (optionally) reviews, then gives a one-line verdict. Trigger on 'why has my 30-60 day booking window slowed down,' 'why don't I get bookings a month or two out,' 'booking window diagnosis,' or 'is my lead time off vs. the market.' Read-only, except an optional segment creation that it confirms first. Not for pace vs. last year (MCP-stly-pacing-calculations) or future posted rates vs. last year (MCP-future-rate-overpricing); any price fix goes through xContext-preferences or xContext-custom-rates."
---

# Booking Window Diagnosis (30-59 days)

Answers a customer question like "why has my 30-60 day booking window slowed down?" for ONE listing. Compares how the listing's bookings split across booking windows (0-29 / 30-59 / 60+ days before arrival) with the market and a portfolio segment, month by month over the trailing 12 complete months. Then checks price vs. market, final occupancy vs. market, market year-over-year trends, and (optionally) reviews. Ends in a short verdict the user can act on or pass to an owner.

Serves the Identify stage of Active Revenue Management. Read-only: never writes prices or settings. Hand any fix to xContext-preferences / xContext-custom-rates.

---

## 1. Questions

### Ask every run (one message, before any data pull)
1. **Which listing?** Resolve name/ID with `wheelhouse_rmGetListings` (paginate). Every listing call needs the `channel` (key of `channel_ids`). If several match, list them and ask.
2. **Which segment to compare against?** Call `wheelhouse_rmGetSegments`. List segments whose `filter_backend` matches the listing's `market_id` and bedroom count first. Offer "create a new segment" — that is a write (`wheelhouse_rmPostSegments`): show the exact filter and get an explicit yes before creating.
3. **Check reviews?** If yes, ask for the Airbnb listing URL. If no, the output says "Reviews: not checked."

### State as defaults (change only if the user asks)
- Date range: trailing 12 complete months, current month excluded (run on Nov 23, 2026 -> Nov 1, 2025 to Oct 31, 2026). Prior-year comparison = the 12 months before that.
- Booking windows: 0-29, 30-59, 60+ days (30-59, not 30-60, so no booking counts twice). Focus window = 30-59 unless the user names another.
- Market benchmark: `performance=high`, `bedrooms` = listing's bedroom count.

### Ask only when it happens
- Segment mixes bedroom counts or markets -> "Filter to this listing's bedroom count, or keep all?"
- Segment has fewer than 20 bookings in a month -> label that month's segment result "low confidence"; if most months are under 20, ask whether to proceed or pick another segment.
- Segment has more than 60 listings -> give the estimate (about 1 minute per 60 listings at the 60 req/min limit) and wait for a go-ahead.
- Listing has less than 12 months of reservations -> "Run on the shorter period without year-over-year?"

---

## 2. Definitions

```
lead_time_days = start_date - date(booked_at)
window         = 0-29 if lead < 30 | 30-59 if lead < 60 | 60+
arrival_month  = month of start_date (whole booking credited to its arrival month)
share(window)  = bookings in window / all bookings, per arrival month (bookings, not nights,
                 so listing, segment and market use the same unit)
```
Reservations: keep `status == "Accepted"` with non-null `booked_at`. Declined/Expired/Pending/Ignored/Canceled never count.

ADR + fees per booking = (`total_price` - `taxes`) / nights. Real PMS-connected listings return fees in `total_price`. If `total_price == nightly_subtotal` (no fees returned, e.g. test accounts), add the listing's per-stay fees from `wheelhouse_rmGetListing` (`listing_preferences.fees`) and note "fees estimated" in the output.

---

## 3. Data pulls

The blocks below assume the Wheelhouse MCP's code-execution tool (named `execute` or similar, with `call_tool` in scope). Limits seen in testing: max 50 `call_tool` per block and a per-block time limit -> keep each block to about 15-25 calls. If your client has no execute tool, make the same `wheelhouse_rm*` calls directly, one at a time. `import json` / `import datetime` / `import asyncio` explicitly. No `calendar` or `statistics` modules. Market endpoints return intermittent 502s: wrap every market call in up to 3 attempts with `await asyncio.sleep(1)` between.

**Block A - listing + market time series (about 10 calls)**
- `wheelhouse_rmGetListing` -> `market_id`, `num_bedrooms`, fees, `automatic_rate_posting_enabled`.
- `wheelhouse_rmGetReservations` `date_filter_type=stay_date`, start = first day of prior-year period - 30 days, end = last day of the trailing period, `per_page=100`, paginate until a page returns < 100.
- `wheelhouse_rmGetPriceCalendar` over the trailing 12 months (blocked = `is_available` false AND `is_booked` false).
- `wheelhouse_rmGetFlags`.
- `wheelhouse_rmGetMarketTimeSeries` - ONE metric per call (multi-metric requests return only the last metric). One call each for `adr_w_fees`, `occupancy_adjusted`, `lead_time`, each covering prior-year start through trailing end (24 months in one call works). Params: `market_id`, `bedrooms`, `performance=high`.

**Block B - market booking-window shares (12 calls)**
- `wheelhouse_rmGetMarketDistribution` `metric=["lead_time"]`, `month=YYYY-MM`, `bedrooms`, `performance=high`, one call per trailing month.
- Buckets are 5 days wide with negative values (-31 = booked 31 days ahead). Map by `bucket_min_incl`: >= -30 -> 0-29; >= -60 -> 30-59; else 60+. Sum `probability`, normalize to 100%. (Bucket edges make this +/-1 day approximate; say so only if asked.)
- Prior-year distributions: pull ONLY if market lead time moved 5+ days year over year, and only for the standout months.

**Block C - segment (1-2 calls per listing, 15-20 listings per block)**
- `wheelhouse_rmGetSegmentListings` (paginate), keep same bedroom count unless the user chose otherwise, exclude the target listing.
- For each listing: the same reservations pull as Block A. Sum bookings by arrival month and window across listings, then compute shares from the sums (never average per-listing percentages).
- Do NOT use `wheelhouse_rmGetSegmentAggregatedMetrics`: it returns one month per call, ADR without fees, and an unweighted lead time, and it has no booking-window split.

---

## 4. Checks and calculations

### Check 1 - Is 30-59 the weakest window? (listing)
Per arrival month, 30-59 is "weakest" if its share is <= both other windows' shares (**ties count as weakest**).
```
listing_gap_pct = (share_30_59 - avg(share_0_29, share_60_plus)) / avg(share_0_29, share_60_plus)
```
Computed on trailing-12-month totals. Report: "30-59 was X% of bookings vs Y% average for the other windows (-Z%). Weakest in N of 12 months."

### Check 2 - Is the market in line?
Same weakest test and gap % on the market's average shares (Block B). "In line" = 30-59 is also the market's weakest window in at least half the months. Otherwise "not in line" (the market books this window; the listing doesn't).

### Check 3 - Is the segment in line?
Same test on the summed segment shares. Add "low confidence" when segment bookings < 20 in most months.

### Check 4 - Price vs market
```
index = sum(listing ADR+fees revenue) / sum(market adr_w_fees for the same stay nights x nights) - 1
```
Market `adr_w_fees` per stay date from Block A, averaged over each booking's nights. Show as +/-% vs market.
- Window price = bookings in the 30-59 window over the trailing 12 months.
- Monthly price (standout table) = all bookings arriving that month, labeled as such (most weak months have no 30-59 bookings to price).
- Caveat to keep: past-date market ADR is FINAL (all bookings for that night), not as of booking time. Comparing windows to each other cancels most of that bias.

### Check 5 - Final occupancy vs market
```
listing_occ(month) = booked nights (Accepted reservations, by stay date) / (calendar nights - blocked nights)
market_occ(month)  = mean of daily occupancy_adjusted
```
"Room to raise price" when, in a month, listing_occ >= market_occ AND the listing's price index is below market. Meaning: it sells out early because it is cheap; 60+ day prices can go up.

### Check 6 - Market year over year (trailing 12 vs prior 12, completed months only)
```
ADR + fees  = sum(adr_w_fees x occupancy) / sum(occupancy) over all days
Occupancy   = mean(occupancy_adjusted)
Lead time   = -sum(lead_time x occupancy) / sum(occupancy)   (days ahead)
```
Report ADR % change, occupancy point change, lead-time day change. Never use lead time for future stay dates (only early bookers are counted, so it reads far too long).

### Check 7 - Reviews (only if the user said yes and gave a URL)
Needs a browser tool that can open pages and run JavaScript (for example Claude in Chrome; open a NEW tab and close it when done):
1. Navigate to `<listing URL>/reviews`, click "Show all N reviews".
2. With the browser tool's JavaScript runner, scroll the dialog's scroll container to the bottom several times, then read each "Rating, N stars" line and the date in the next few lines ("Month YYYY" or relative like "4 weeks ago" -> convert to a month).
3. Per month: new review count and rolling average of the last 10 reviews.
4. Flag: any review <= 3 stars, a drop of 0.1+ in the 10-review average, or 2+ consecutive months with no new reviews. Then say whether the 30-59 share or occupancy fell in the 1-3 months after a flag.
- If no browser tool is available or the page does not load reviews: say "Reviews: couldn't read dated reviews" and report only overall rating, count and category ratings if visible. Never guess.

### Check 8 - Context flags (no extra cost)
From Block A: say in one line if `automatic_rate_posting_enabled` is false, or `wheelhouse_rmGetFlags` returns settings/engine flags (e.g. Max Rate Conflict, No Global Minimum). These explain current-calendar behavior; they are not the verdict unless nothing else fits.

---

## 5. Standout months

1. Flag every month where the listing's 30-59 share is **10+ percentage points above or below** the market's 30-59 share. Above = what worked; below = the problem months.
2. If no month crosses 10 points, show the **3 months with the largest shortfall** instead.
3. Cap the table at 5 rows (largest gaps first). Columns: Month | Listing 30-59 | Market 30-59 | Segment 30-59 | Listing occ | Market occ | Price vs market (all bookings that month).

---

## 6. Verdict (pick the first that fits)

1. **Market and segment are both in line** (30-59 is weakest for them too) -> "Normal for this market and season; the window is slow for everyone."
2. **Listing priced 5%+ above market in 30-59 and the market books that window** -> "Price issue: 30-59 priced X% above market."
3. **Listing occupancy >= market in most months while priced below market** -> "Sells out early at below-market prices; raise prices for bookings made 60+ days ahead in [months]."
4. **Review flag that lines up in time with the drop** -> "Reviews likely contributing since [month]."
5. Otherwise -> "Listing-specific, not price or market: check visibility, settings and posting." Mention any Check 8 flags.

Seasonal split is allowed: e.g. verdict 3 for Oct-May and verdict 5 for Jun-Sep.

---

## 7. Output

Keep it succinct: verdict first, bold headline, no preamble.

```
**[Listing] under-books the 30-59 day window because [verdict].**

- Listing: 30-59 days was X% of bookings vs Y% for other windows (-Z%). Weakest in N of 12 months.
- Market and segment: [in line / not in line]. Market 30-59 = A%, segment = B% [low confidence].
- Price: X% [above/below] market in this window ($L vs $M ADR + fees).
- Final occupancy vs market: [higher/lower] in N of 12 months ([months]).
- Market year over year: ADR +/-X%, occupancy +/-Y pts, booking window Z days [earlier/later].
- Reviews: [not checked / not a factor / flag + timing].

**Months that stand out:** [table, max 5 rows]

**Recommendation:** [one sentence]

Source: Wheelhouse reservations, price calendar and [market] [N]BR high-performer market data, pulled [date].
```

After the output, ask once:
> "Save this market data and track it for future runs?"

- **Yes:** ask which folder. Save completed months (time series + distributions) as JSON keyed by `market_id`/`bedrooms`/`performance`/`month`; on later runs read the cache and pull only months not cached. Then, if the client supports scheduled tasks, offer a weekly one that snapshots future `adr_w_fees` and `occupancy_adjusted` for the next 90 days, so later runs can compare prices as of the booking date. Confirm the schedule before creating it.
- **No:** save nothing.

---

## 8. Known API behavior

- `wheelhouse_rmGetMarketTimeSeries`: one metric per call (seen in testing); past dates = final values, future dates = on the books today; no "as of" parameter. Intermittent 502.
- `wheelhouse_rmGetMarketDistribution`: one month per call; intermittent 502 (about half of first attempts in testing).
- `wheelhouse_rmGetListingKpis` windows are cumulative (`0_30`, `0_60`), not 30-60; this skill uses reservations instead.
- `wheelhouse_rmGetCalendarDayHistory` only goes back 180 days and costs one call per date; not used.
- Listing calls require `channel`; they error without it.
- Market report data is available only for markets where the user has at least one Pro-tier listing -> if the market is missing or refused, tell the user plainly.

## 9. Edge cases

- No 30-59 bookings at all: price check uses all-bookings index by month and says so.
- Month with zero listing bookings: show "no bookings", exclude from the weakest count.
- Segment month with zero bookings: show "-".
- Multi-unit listings: group the price calendar by `unit_number` before counting blocked nights.
- Mixed currencies in a segment: shares are unitless, so they are fine; skip segment price comparisons.