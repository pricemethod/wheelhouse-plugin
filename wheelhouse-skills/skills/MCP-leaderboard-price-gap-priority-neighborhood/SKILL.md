---
name: MCP-leaderboard-price-gap-priority-neighborhood
description: "Finds which Wheelhouse listings are highest priority right now by combining three live signals from the Wheelhouse MCP: (1) how far next-30-day adjusted occupancy trails the neighborhood, (2) pickup over the last 7 and 14 days (are they selling?), and (3) the listing's fee-adjusted asking rate vs the neighborhood median and 75th percentile (is it overpriced?). Splits results into 'likely a price problem' vs 'behind but not overpriced' so the next action is obvious. Use whenever the user asks which listings are high priority, need attention, are underperforming their neighborhood or market, are overpriced vs the neighborhood, or haven't sold lately, or wants a price-vs-neighborhood check added to a priority list, even if they never name this skill. Read-only. Not for pace vs last year (use MCP-stly-pacing-calculations), overpricing vs the listing's own history (MCP-future-rate-overpricing), a single listing's night-by-night check vs the neighborhood (MCP-market-overpricing-check), or an occupancy-and-pickup list with no neighborhood or price comparison (MCP-leaderboard-poor-occ-pickup)."
---

# Neighborhood Price + Gap Priority List

A live, read-only scan for the Identify stage of revenue management. It answers: **which listings are way behind their neighborhood, haven't sold in the last week or two, and are they priced too high?**

The point of combining the signals is diagnosis, not just ranking. A listing that trails its neighborhood *and* is priced above it probably needs a rate change. A listing that trails its neighborhood while priced *below* it has a different problem (minimum price floor, min stay, blocked nights, the listing itself), and cutting price would not help. The skill therefore reports the two groups separately.

Everything comes from the connected Wheelhouse MCP; no cache or sync skill is needed. Nothing is written. Any rate change that follows goes through `xContext-custom-rates` or `xContext-preferences` after the user confirms. Neighborhood prices are fee-inclusive; `xContext-market-data` explains the fee basis.

## Defaults (tell the user, change on request)

| Setting | Default | Where |
|---|---|---|
| "Behind the neighborhood" | adjusted occupancy, next 30 days, at least 10 points below the neighborhood | `GAP_THRESHOLD_PP` in stage 1 |
| "Not selling" | nights picked up in the last 7 and last 14 days | stage 1 |
| Availability gate | at least 30 open nights in the next 60 | `MIN_NIGHTS_AVAILABLE_60` in stage 1 |
| Price comparison | fee-adjusted asking rate vs neighborhood median, next 30 nights; 75th percentile marks "way overpriced" | stages 2-3 |
| Score weights | price 35%, occupancy gap 35%, 7-day pickup 15%, 14-day pickup 15% | `WEIGHTS` in stage 3 |
| Minimum comparable listings | 10 | `MIN_COMPS` in stage 3 |

If the user says price matters most, raise the price weight. The 10-point cutoff and the weights are judgment calls, not Wheelhouse standards.

## Workflow

Run each stage by reading the script, pasting it into the Wheelhouse MCP's `execute` tool (its full name carries your client's prefix, e.g. `mcp__wheelhouse__execute`; the `call_tool` function is already in scope), and editing only the CONFIG or `ROWS` block at the top. If the Wheelhouse tools are not loaded yet, search your client's tool list for "Wheelhouse" first.

### Stage 1: find listings behind their neighborhood
`scripts/stage1_pull.py` (about 12 calls). It pulls the listing roster plus ten bulk KPIs, joins them on Wheelhouse listing ID, drops listings with missing data or fewer than 30 open nights, and keeps those at or below the gap threshold. Report how many were dropped and why.

### Stage 2: add neighborhood price and fee multiplier
`scripts/stage2_price.py`. Paste the stage 1 candidates into `ROWS`. It makes two calls per listing (neighborhood pricing, fee multiplier). Before running, tell the user the call count (about twice the number of candidates) because it can be 40 to 60 calls; this is read-only and well within limits, but it is more than a casual lookup. Run at most about 20 listings per execute call and concatenate the outputs if there are more. The script retries on rate limits (60 requests per minute).

### Stage 3: score and diagnose
`scripts/stage3_score.py`. Paste all stage 2 rows into `ROWS`. No API calls. It computes the fee-adjusted price index (asking rate times fee multiplier, divided by the neighborhood median), assigns a tier (above p75, above median, at/below median, or no reliable comp), computes the composite score, and returns three groups.

### Present
Use the format below. Close with one question about which listing to dig into.

## Output format

1. One line stating the definitions used (gap threshold, pickup windows, how price was measured) and counts: how many listings were ranked, how many were behind the neighborhood, how many of those have pricing turned on.
2. **Behind the neighborhood and priced above it**: table with listing, gap in points, pickup 7d / 14d in nights, your fee-adjusted rate vs the neighborhood median (with the ratio and the 75th percentile). Flag "above p75" as way overpriced.
3. **Behind the neighborhood but not overpriced**: the worst few with the same columns. State plainly that cutting price will not fix these and name the other levers.
4. **Pricing off**: mention listings Wheelhouse is not pricing (`auto` false) and whether they matter; they are the least actionable but sometimes the most neglected.
5. **Caveats**, only the ones that apply (see below).
6. Offer the next step.

Keep tables to the top 5 to 10 rows per group. Say "points" for occupancy gaps, and "nights" for pickup.

## Gotchas learned the hard way

- **`asking_rate_fees` is not reliable for this.** In testing it returned exactly the same number as `asking_rate`, so it did not add fees. Neighborhood prices include guest fees, so the scripts use `asking_rate` times the fee multiplier from `wheelhouse_rmGetFeeImpactCalendar` (fallback `estimate`).
- **Listings with no fee setting get a multiplier of 1.0**, which can understate how high their price really is. Stage 3 marks listings between 0.8x and 1.0x with no fee setting as borderline. Say so rather than calling them fine.
- **Comp sets can be tiny.** Under 10 comparable listings means low confidence; the script leaves price unscored and ranks on the other signals instead of treating the listing as fairly priced. Never present a comparison across mismatched currencies.
- **ID spaces.** Bulk KPI `listing_id` is the Wheelhouse ID (matches `wheelhouse_id` on the listing), so per-listing calls use `channel: "wheelhouse"`.
- **Response shapes differ.** Lists come back as `{"result": [...]}`, neighborhood pricing as `{"data": [...], "currency": ...}`. `per_page` is capped at 100.
- **Multi-unit listings** (`number_of_active_units` above 1) pool nights and pickup across units, so zero pickup is less alarming and availability looks huge.
- **Pickup counts nights and `pickup_bookings` counts bookings; they can disagree** (a booking with zero nights of pickup). Lean on nights, and flag listings where they diverge.
- **Several listings in one property share a neighborhood**, so identical gaps are expected, not an error.
- **Sandbox and sample data.** Hypothetical or sample listings may carry modeled rather than real bookings, which can produce odd results like a listing priced at 0.4x the market with no sales. Mention this when most of the portfolio is hypothetical. Also note `access_level`: view-only listings usually cannot be edited by the user.
- **`min_price_occurrence`** is returned as a floor lead, but its units were never verified. Use it only to suggest "check the floor", not to quote a number.
- The execute sandbox has `asyncio` but not the `statistics` module.

## Next steps to offer

- **Price problem listings:** use the preview endpoint (`wheelhouse_rmPreviewPreferences`) to show what a rate or setting change would do without saving it, then hand any write to `xContext-custom-rates` or `xContext-preferences` after explicit confirmation.
- **Not-price listings:** check the minimum price floor and min-stay rules, blocked nights, base price vs recommendation (`wheelhouse_rmGetBasePriceRecommendation`, weighted by `anchor_credibility`), and the neighborhood comparison day by day (`MCP-market-overpricing-check`).
- **Own-history angle:** hand off to `MCP-future-rate-overpricing` for posted rates vs what transacted last year, or `MCP-price-change-attribution` to see whether a recent change led to bookings.
