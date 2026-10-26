---
name: MCP-future-rate-overpricing
description: Checks whether a listing's future posted rates are too high (or too low) vs. what actually transacted the same calendar month last year, broken out by month and by weekend (Fri/Sat) vs. weekday (Sun-Thu). Trigger for "are my future rates too high," "check for overpricing next season," "is [listing] priced too aggressively for [month]," "which months are overpriced," "future rate health check," or any forward-looking ask about posted rates being out of line with historical demand. Serves the Identify stage of Active Revenue Management — distinct from MCP-stly-pacing-calculations (on-the-books pace vs. last year, not posted vs. transacted rate) and MCP-price-change-attribution (backward-looking — did an edit already made lead to bookings). Not for writing a new rate — this only flags risk; any resulting write goes through Context-CustomRates.
---

# Future Rate Overpricing Check

Flags which future months (and which weekend/weekday buckets within them) a listing's posted Asking Rate looks out of line with what the listing actually transacted for during the same calendar month last year — surfacing both overpriced and underpriced risk, with market and model context layered in only where the historical signal already fired. Shared conventions: always pass `listing_id` together with its `channel`; `revenue_basis` `rent` means `nightly_subtotal` (rent only, no fees or taxes); the RM API allows 60 requests/minute, so on a `429` wait for `Retry-After` before retrying. The rest of this file covers what's specific to this workflow.

**Read-only.** This skill never writes a preference, rate, or rule — it produces a diagnostic report. If the findings lead the user to want a rate change, that's `Context-CustomRates`, which confirms with the user before writing — not this skill.

## When to use this skill

- "Are my future rates too high for the fall?"
- "Check next year's holiday pricing against what we actually sold for"
- "Which months look overpriced on the Smith property?"
- "Is my base pricing tracking market, or am I just guessing at high numbers?"

Not for: on-the-books pace vs. last year (`MCP-stly-pacing-calculations`), or checking whether a change you already made worked (`MCP-price-change-attribution`), or actually changing a rate (`Context-CustomRates`).

## Inputs

| Param | Default | Notes |
|---|---|---|
| `listing_id` + `channel` | — | Required pair, resolved via `GetListings` if not already known this session |
| `forward_window` | Next 6 months | User-adjustable — extend on request. Step 1's single `GetPriceCalendar` call also covers the prior-year span, and its range is capped at 3 years, so one call handles a forward window of up to ~24 months; beyond that, split into two calls |
| `weekend_definition` | Fri & Sat nights | Fixed for this skill — not user-configurable |
| `dead_band` | ±10% | The delta range treated as "in-line" rather than flagged |
| `revenue_basis` | `rent` | Default for this skill — state it in output |

## Workflow

### Step 0 — Tenure guard (run before anything else)

Resolve `listing_id`+`channel` via `GetListings` if not already cached this session — this call (or the singular `GetListing`, if the pair is already known) already returns `wheelhouse_created_at` at no extra cost, so use that as the tenure signal rather than issuing a separate unfiltered `GetReservations` pull just to find the earliest stay date (that pull can return a large, mostly-wasted payload for any listing with a long history).

For any target month where the same calendar month last year falls **before** `wheelhouse_created_at`, skip the month entirely and report it under a distinct "insufficient history" line — never blend partial data, and never silently drop it from the output. Note the one known gap in this approach: a listing's Wheelhouse creation date can predate its actual first guest stay by a few months (seen in dry-run validation), so `wheelhouse_created_at` is a slightly optimistic proxy for "real history exists." If Step 2's historical pull comes back completely empty for a month that passed this check, treat that as the same "insufficient history" case rather than a genuine zero-demand data point — only treat a zero-booking month as a real (if concerning) finding when `wheelhouse_created_at` is comfortably earlier (a year or more) than that month.

This is not optional: a listing's first partial year is commonly priced low to build reviews/ranking, and treating that as a stable YoY baseline produces a false overpricing signal (see the worked example in `references/methodology.md`).

### Step 1 — Future side (always runs, per month × bucket)

One `wheelhouse_rmGetPriceCalendar` call with `start_date` = the first day of the first **prior-year** month (forward window start − 12 months) and `end_date` = the end of the forward window — the 3-year range cap leaves room for this at the default window. Use the forward-window rows here: split each date into **WE** (Friday & Saturday nights) or **WD** (Sunday–Thursday nights) and average Asking Rate per bucket per month. Group by `unit_number` first if the listing is multi-unit (`number_of_active_units` non-null), then average.

Keep the prior-year rows for Step 2: for past dates the calendar returns the state each date ended up in, so blocked nights (`is_available: false` AND `is_booked: false`) per LY month × bucket come from this same call at no extra cost. Don't use the prior-year rows' `price` as a posted rate — for booked or blocked dates it's the price the night booked at, not what was posted (Step 6 covers posted rates).

### Step 2 — Historical side (always runs, per month × bucket)

`GetReservations` for the same calendar month last year (`date_filter_type=stay_date`), one call covering the full forward window's equivalent prior-year span where tenure allows. Include only `status == "Accepted"` (documented values are `Accepted`, `Declined`, `Expired`, `Canceled`, `Pending`, `Ignored` — declined, expired, pending and ignored inquiries never became stays and would inflate LY nights/occupancy and distort LY ADR). Per-night rollup: `nightly_subtotal ÷ (end_date − start_date)` gives the stay's average nightly rate; allocate that same average across each night of the stay by its WE/WD bucket (the endpoint doesn't return a true per-night breakdown, so this is the correct approximation — see `references/methodology.md` for the worked calculation). Also compute historical Occupancy (Adjusted) per bucket, using the LY blocked-night counts from Step 1's calendar rows for the denominator.

### Step 3 — Exclusion layer (always runs, before computing averages)

Two independent mechanisms, both required — full detail and worked thresholds in `references/exclusion-and-edge-cases.md`:

1. **Floating holiday table** — a maintained set of US floating holiday date ranges (Easter, Memorial Day, July 4th observed, Labor Day, Thanksgiving, MLK Day, Presidents Day) for both the current and prior year. Nights in these ranges are pulled out of both sides' WE/WD averages and reported as their own callout line.
2. **Statistical outlier detection** — any day priced well outside that month's typical range (on either the future or historical side) gets pulled out the same way, catching local recurring events (festivals, conventions) that a fixed holiday table won't. Cross-reference the listing's own `custom_date_ranges` (from `GetPreferences`) for named events/seasons and label outliers that match a configured event by name rather than as a generic anomaly.

A reservation that only partially overlaps an excluded window (e.g., a 5-night stay where only 1 night is Thanksgiving Day) can't be cleanly split with the data available — flag the whole stay's blended rate as "includes a holiday/event night, interpret with caution" rather than pretending precision that isn't there.

### Step 4 — Headline delta and flag

Per month × bucket: `(Future Asking Rate − Last Year ADR) ÷ Last Year ADR`.

- **Overpriced**: delta > +10%
- **Underpriced**: delta < −10%
- **In-line**: within ±10%

### Step 5 — Confidence modifier

Weight the flag by last year's Occupancy (Adjusted) for that same bucket:

- Low historical occupancy (roughly <50%) + Overpriced → **high confidence** (the market already showed it wouldn't pay that rate)
- High historical occupancy (roughly ≥70%) + Overpriced → **low confidence** ("sold through last year — may reflect legitimate repositioning, not overpricing")
- Mirror the same logic for Underpriced: high occupancy + Underpriced → high confidence there's room to raise; low occupancy + Underpriced → low confidence (soft demand, not necessarily a pricing gap)

### Step 6 — Posted-vs-posted secondary signal (one extra call)

Alongside the headline, compute future Asking Rate vs. **last year's posted rate** for the same bucket. The price calendar can't supply this (its past-date `price` is the transacted price for booked/blocked nights), so make one `wheelhouse_rmGetLastPostedPrices` call over the prior-year span (same LY start/end as Step 2). Each row's `last_posted_price` is the most recent posted price for an available night, or the last price posted at or before `block_time` for a booked night. Group by `unit_number` for multi-unit listings, drop nulls (no posting history) and Step 3's excluded nights, average per LY month × WE/WD bucket, then: `Posted-vs-Posted Δ = (Future Asking Rate − LY posted rate) ÷ LY posted rate`. If a bucket has no non-null `last_posted_price`, leave its Δ blank and say "no posting history." This distinguishes "raising faster than your own historical posture" from a genuine market misread.

### Step 7 — Market cross-check (flagged months/buckets only)

Only for buckets that came out Overpriced or Underpriced in Step 4 — this keeps the call budget lean:

- `GetNeighborhoodPricing` + `GetNeighborhoodOccupancy` — **fetch each at most once per listing per session**, the first time anything flags, then reuse/slice for every subsequently flagged month. Neither tool accepts a date range; each returns the full available horizon and must be sliced client-side for the relevant dates. Never re-fetch these per flagged month — that repeats the same expensive full-horizon payload for no new data.
- `wheelhouse_rmGetFeeImpactCalendar` — also once, the first time anything flags (`fallback=estimate`, `start_date`/`end_date` = the forward window). Neighborhood prices include the fees guests pay on top of the nightly rate, while the Asking Rate is rent only, so multiply the Asking Rate by that date's `fee_multiplier` before comparing it with the neighborhood median / p25 (`low_price`) / p75 (`high_price`). State the multiplier's `source` (`setting`, `estimate`, or `none`); if it's `none` (multiplier 1.0), note that the comparison is still rent vs. fee-inclusive and understates the listing's price relative to market.

That's it for Phase 2. `GetMarketTimeSeries` was cut as redundant with `GetNeighborhoodOccupancy` (both answer "is local demand under pressure," just at different geographic granularity — the neighborhood cluster is the tighter, more relevant comparison). `GetBasePriceRecommendation` and `GetMonthlySeasonality` were also cut: both are useful in isolation, but neither is bucket-specific, and the call/token cost wasn't earning its keep against the two signals that remain.

### Step 8 — Output

One row per month × bucket:

| Month | Bucket | Future Asking Rate | LY ADR | LY Occ (Adj) | Delta | Flag | Confidence | Posted-vs-Posted Δ | Market context |
|---|---|---|---|---|---|---|---|---|---|

Rules for populating this table:
- "Market context" only populates for flagged rows (Step 7); leave it blank for In-line rows rather than burning calls to fill it in. It compares the fee-adjusted Asking Rate (× `fee_multiplier`) with the neighborhood figures; state the multiplier and its `source` once.
- Holiday/event/outlier nights get their own separate line per month (not folded into the WE/WD averages), labeled with the specific holiday/event name where known.
- Insufficient-history months get their own line stating exactly that, with no delta or flag computed.
- State the `revenue_basis` and `weekend_definition` once, near the top of the output, rather than repeating them per row.

Close with 2–4 sentences of plain-language takeaway: which months carry the strongest signal, which flags are low-confidence and why, and any months worth a second look once more history accumulates.

## Call budget

Single listing, 6-month scan (the default): `GetListings` (1, if needed — also covers the Step 0 tenure check at no extra cost) + `GetPriceCalendar` (1, spanning the prior-year months through the end of the forward window) + `GetReservations` historical pull (1, covering the full historical span in one call) + `wheelhouse_rmGetLastPostedPrices` (1, Step 6) + Phase 2 (`GetNeighborhoodPricing` + `GetNeighborhoodOccupancy` + `wheelhouse_rmGetFeeImpactCalendar`, each fired at most once, only if something flags) + `GetPreferences` (only if an outlier needs name-matching against `custom_date_ranges`). Realistically 4–9 calls total for the default window — comfortably under the 60/min limit; no pre-run volume confirmation needed at single-listing scope. Extending the window or scope to segment/portfolio can run past ~60 calls — estimate the total first, tell the user the number, and let them choose to proceed or narrow scope before running.

## Edge cases

Full detail in `references/exclusion-and-edge-cases.md`. Summary:

- **New listing, insufficient history** — handled by the Step 0 tenure guard; skip and label, never blend.
- **Reservation straddling an excluded holiday/event window** — flag the blended rate as low-precision rather than trying to split it.
- **Local recurring event not in any federal holiday table** — caught by the Step 3 statistical outlier check, cross-referenced against the listing's own `custom_date_ranges` for a name where possible.
- **Multi-unit listings** — group by `unit_number` before averaging, both on the future and historical side.
- **Market signal disagrees with the headline ADR signal** — this is a real and useful finding, not a bug; report both and let the disagreement itself be part of the takeaway (it often means the historical baseline, not the future rate, is the less reliable side of the comparison).
