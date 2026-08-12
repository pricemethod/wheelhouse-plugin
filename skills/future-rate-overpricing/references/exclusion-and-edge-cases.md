# Exclusion Layer & Edge Cases

Detail for SKILL.md Step 0 (tenure guard) and Step 3 (exclusion layer), plus other edge cases found during design and dry-run validation.

## Tenure guard (Step 0)

Use `wheelhouse_created_at` from `GetListing`/`GetListings` (already fetched for `listing_id`+`channel` resolution, so this costs nothing extra) as the tenure signal. For any target month where the same calendar month last year falls before that date, skip the month and report it as "insufficient history," never as a 0% or blended delta.

**Known gap in this approach:** `wheelhouse_created_at` marks when the listing was set up in Wheelhouse, not when it had its first guest stay — dry-run validation found a ~5-month gap between the two for one listing. This means the tenure guard can occasionally be a little optimistic about which months have real history. The cheap mitigation: if Step 2's historical pull comes back completely empty for a month that passed the `wheelhouse_created_at` check, treat that as "insufficient history" too rather than a genuine zero-demand finding — unless `wheelhouse_created_at` is comfortably more than a year before that month, in which case a zero-booking month is a real (if concerning) data point worth reporting as such. This avoids a dedicated full-history `GetReservations` pull just to pin down the exact earliest stay date, which would otherwise return a large, mostly-wasted payload for any listing with a long booking history.

**Why this matters beyond the missing-data case:** even where a sliver of prior-year data exists, a listing in its first 12-18 months commonly carries artificially low pricing while it builds reviews and channel ranking. A YoY comparison against that ramp-up period will systematically read as "overpriced" even when the current rate is reasonable. There is no clean fix for this short of the skip-and-label rule — don't try to correct for it with a multiplier or discount factor, since that just substitutes one guess for another. If a user wants this listing's rates checked despite thin history, the market cross-check (Step 7) is the more trustworthy read for those months, and worth surfacing even outside the normal "flagged months only" trigger for a listing that fails the tenure guard broadly.

## Floating holiday table

Maintain US floating holidays for both years in the comparison (current forward-window year and the equivalent prior year):

- Easter (and the immediately surrounding weekend)
- Memorial Day
- July 4th (observed date, which can shift to an adjacent weekday)
- Labor Day
- Thanksgiving (and the following Friday-Sunday, which behaves like its own demand period)
- MLK Day
- Presidents Day

Nights falling in these windows are excluded from both sides of the WE/WD average and reported as their own line, e.g. "Nov 26-29 (Thanksgiving window) — excluded from monthly average, see below."

## Statistical outlier detection

The holiday table catches known, named, calendar-fixed dates. It does **not** catch local recurring events (music festivals, conventions, sporting events) that spike demand on dates that vary by year or aren't federally recognized. Dry-run validation against a New Orleans listing found exactly this: a multi-day demand spike in October/early November (asking rates 2-4x the surrounding days) with no federal holiday behind it.

Approach:
1. Compute the month's typical price range (on whichever side — future or historical — is being evaluated) excluding already-known holiday nights.
2. Flag any day priced well outside that typical range (a simple threshold like "more than double the month's median" is a reasonable starting point; tune based on what a listing's own price volatility looks like rather than a single fixed global constant).
3. Before reporting a flagged outlier as a generic anomaly, cross-reference the listing's `custom_date_ranges` (from `GetPreferences`) for an `event`/`seasonal` entry covering those dates. If one exists, label the outlier with that event's name instead of "unidentified spike" — this is usually available since a well-configured listing already has its major local events set up as named seasons/events.
4. If no matching `custom_date_ranges` entry exists, report it plainly as an unlabeled demand spike and suggest the user may want to configure it as a named event going forward (informational only — this skill doesn't write preferences).

## Partial-overlap reservations

A reservation can span into or out of an excluded holiday/event window without being fully contained by it (e.g., a 5-night stay where only the final night is Thanksgiving Day). Since `GetReservations` doesn't expose true per-night rates, there's no clean way to strip just the holiday-night's contribution from the stay's blended average. Rather than approximating further, flag the whole reservation's contribution as "includes a holiday/event night — blended rate, interpret with caution" and let it flow into the normal bucket calculation with that caveat attached, rather than silently treating it as clean data or arbitrarily discarding the whole reservation.

## Multi-unit listings

If `number_of_active_units` is non-null, both `GetPriceCalendar` and the historical reservation data can carry multiple rows per date (one per unit). Group by `unit_number` before computing any WE/WD average — mixing units together will produce a meaningless blended rate.

## Market payload size

`GetNeighborhoodPricing` and `GetNeighborhoodOccupancy` take no `start_date`/`end_date` parameters — each call returns the tool's full available horizon (in dry-run testing, this spanned roughly two years and produced a very large payload). Fetch each once per listing per session, then slice the returned array client-side for whichever months are flagged. Do not call these per flagged month — that repeats the same expensive full-horizon fetch for no additional data.

## Market signal disagreeing with the headline

Treat this as a genuine finding, not noise to average away. In dry-run validation, the headline ADR-based signal and the market-percentile signal pointed in opposite directions for the same listing/month — and the disagreement itself was the most useful piece of information, since it pointed toward the historical baseline (not the future rate) being the less trustworthy side of the comparison. Report both signals plainly in output rather than collapsing them into a single resolved verdict.
