---
name: stly-pacing
description: Runs a Same-Time-Last-Year (STLY) pacing analysis — Nights Booked, Revenue, ADR, and Occupancy (adjusted and unadjusted) vs. the on-the-books position one year ago — for a listing or saved Wheelhouse segment, over any date range (months, a rolling day count, a named period, or explicit dates). Produces a pace signal (ADR x Occupancy vs. STLY) with booking-window-aware interpretation, serving the Identify stage of Active Revenue Management. Trigger for any "pacing," "pickup," or "pace report" ask, comparisons to "last year" / "STLY" / "on the books," pacing charts/tables, or segment booking-trend reviews — even without the word "pacing" ("how does this month look vs last June"). Also trigger for single-KPI asks like "ADR pacing," "booked nights pacing," "revenue pacing," or "occupancy pacing" vs. last year — these need on-the-books STLY comparison, not a rolling-window KPI lookup. Not for forward-looking calendar checks, or when only final last-year actuals are wanted.
---

# STLY Pacing

Compares current booking pace against the equivalent point in last year's booking cycle — not last year's final numbers — for Nights Booked, Revenue, ADR, and Occupancy, then derives a pace signal and actionable interpretation per period. This is workflow #3 ("Pick-Up Analysis & STLY Pacing") from the project's Identify-stage catalog.

Full arithmetic lives in `references/pacing-calculations.md`. The pace-signal derivation and the full interpretation-string table live in `references/pace-signal-guide.md`. Read both before computing a report the first time in a session; skim them again if a detail (e.g. an exact formula or an interpretation line) needs checking.

This skill computes Revenue (Rent) and Revenue (+ Fees) only — taxes and security deposits are excluded from every figure (standard RM practice: taxes are a pass-through, deposits are a hold, neither is revenue). If the user specifically wants a taxes-inclusive `all_in` figure, that's a different workflow, not this one.

---

## 1. Resolve scope

Three supported scopes for v1 — no ad hoc filter-building (bedrooms/market/tags) yet; that's a documented fast-follow (see §6).

- **Single listing** — resolve the `listing_id` + `channel` pair via `wheelhouse_rmGetListings` (paginate if needed) by matching the name/nickname the user gave. Never accept a bare ID without its channel.
- **Explicit multiple listings** — same resolution, for each named listing.
- **Saved segment** — call `wheelhouse_rmGetSegments` to find the segment by name, then `wheelhouse_rmGetSegmentListings` (paginated, `exclude_inactive` defaults true) to get the listing set.

If the user names a segment or filter criteria that doesn't map to an existing saved segment, say so and offer the two real options: pick an existing segment, or list the specific listings by name.

## 2. Resolve the date range and periods

Ask for a timeframe only if genuinely ambiguous; otherwise apply the defaults in `pacing-calculations.md` §1 (a bare "how's pacing" request defaults to the classic 4-full-month view starting with the current calendar month). Build the overall range, then slice into periods — calendar months by default, a single block for short custom ranges, or weekly if the user asks for that granularity. Compute `days_to_period_end` and `booking_window` for each period per §2 of the calculations reference.

## 3. Check the call budget before running anything at scale

Estimate total calls using `pacing-calculations.md` §8 (~6 calls/listing with STLY + Adjusted Occupancy both on, fewer with either off, plus 1–3 to resolve the listing set). If the estimate exceeds ~20 calls, tell the user the number and the choices before proceeding:

> "This will run about [X] API calls across [N] listings against Wheelhouse's 20/minute limit — roughly [Y] minutes. I can (a) proceed as-is, (b) narrow the scope, or (c) skip STLY or Adjusted Occupancy for a faster pass. Which would you like?"

Wait for a choice before firing off calls at that scale. For runs at or under budget, just proceed.

## 4. Fetch and compute, per listing

For each listing in scope:

1. **Reservations, current side and STLY side** — `wheelhouse_rmGetReservations` with `date_filter_type=stay_date`, the fetch windows from `pacing-calculations.md` §3 (30-day lookback, paginated to exhaustion). Filter the STLY side to `booked_at ≤ stly_cutoff_date` client-side. **Always compute Nights Booked, Revenue (Rent/Gross), ADR (Rent/Gross), and Occupancy (Unadjusted) together from this one fetch, regardless of which single KPI the user named** — they're all derived from the same rows (ADR is just Revenue ÷ Nights), so there is zero marginal API cost to having all four ready. Never re-fetch reservations to "just get ADR" or "just get nights" — that duplicates the expensive part of the call for no benefit.
2. **Price calendar, current side and STLY side** (skip if `include_adjusted_occupancy: false`) — `wheelhouse_rmGetPriceCalendar` over the exact target window per §6 of the calculations reference. Group by `unit_number` for multi-unit listings.
3. Pro-rate reservations across period boundaries (§4), compute all metrics and their variances (§5), compute Adjusted Occupancy (§6).
4. Derive `pace_signal` per period from ADR (Rent) × Occupancy (Adjusted) using the dead-band table in `pace-signal-guide.md`.
5. If a listing has no STLY data (new listing, no prior-year reservations), mark `stly_available: false` and carry it through — don't drop it from current-year totals, but exclude it from variance/signal math and call it out by name in the output.

**Batching for multi-listing scope:** process in batches of ~5 listings, pausing so the running total stays under 20 requests/minute; on `429`, back off exponentially (1s → 2s → 4s → … capped at 60s, ±10–20% jitter), up to 3 retries, then record the listing in `fetch_errors` and continue with the rest.

## 5. Aggregate (multi-listing / segment scope only)

Group by currency, sum raw counts within each group, and recompute ratios from the sums — never average per-listing percentages. Full method in `pacing-calculations.md` §7. `days_to_period_end` and `booking_window` are identical across listings and the aggregate (they're calendar-derived).

---

## KPI-scoped requests

The underlying fetch and computation never change based on which KPI was named (see §4) — only the **displayed columns** narrow. When the user names a specific KPI rather than asking for "the full picture" or bare "pacing," lead with just that KPI's column(s) — keep the initial answer lean and answer exactly what was asked. Then, in the same reply, **offer** the natural companion metric as a one-line follow-up rather than including it automatically, since any of these can read misleadingly alone — the whole point of the Matrix Pacing framework is that rate and volume explain each other:

| User asked about | Primary column(s) shown | Companion to offer (not shown unless asked) | Why it's worth offering |
|---|---|---|---|
| ADR / rate pacing | ADR (Rent), ADR (+ Fees) | Nights Booked | A rate gain that cost volume looks the same as a real rate gain until you see nights moved too. |
| Booked Nights / pickup pacing | Nights Booked | ADR (Rent) | A nights gain from discounting looks the same as organic demand until you see rate moved too. |
| Revenue pacing | Revenue (Rent), Revenue (+ Fees) | Nights Booked, ADR (Rent) | Revenue is the product of the two — showing both explains *why* it moved. |
| Occupancy pacing (adjusted or unadjusted, unspecified which) | Occupancy (Adjusted) primary, Occupancy (Unadjusted) alongside it | ADR (Rent) | Same logic as ADR pacing, in reverse. |
| "Pacing," "full pacing," "all the KPIs," or no KPI specified | Everything | — | Full table as in Output format below. |

Since the metric was already computed in step 4 regardless (zero marginal API cost), the offer is free to make and free to fulfill if accepted — e.g., after answering an ADR-pacing question: *"Want me to add Nights Booked alongside this so you can see whether volume moved with it?"* Don't ask this as a blocking question before answering — answer first, offer after.

`booking_window` and `pace_signal` are always shown regardless of scope — they're derived, cost nothing extra, and are the fastest way to read urgency at a glance.

---

## Output format

Lead with a one-line summary, then a period-by-period table, then interpretation text for any non-neutral, non-`no_stly` period.

**Summary line (single listing):**
> **Beach House — 4-Month Pacing (June–Sept 2026)**
> **+7 nights | ADR +$4.63 (+2.5%) | Adj. Occ +5.7 pp (+11.4%) | +$1,600 rent revenue (+14.3%) vs. STLY**

**Summary line (segment):**
> **2BR Miami Beach Segment — 4-Month Pacing (June–Sept 2026)**
> **12 listings | 2 without STLY data (excluded from variance) | ADR +$4.64 (+2.6%) | Adj. Occ +4.9 pp (+9.6%) | +$16,800 rent revenue vs. STLY**

**Period table columns (full "all KPIs" case — see "KPI-scoped requests" above for narrower asks):** Period | Window (icon) | Nights Booked | vs STLY (abs, %) | ADR (Rent) | vs STLY | Occ (Adjusted) | vs STLY (pp, %) | Occ (Unadjusted) | Rev (Rent) | vs STLY | Signal (icon).

Sort chronologically. Bold the total row. Use the icon legend from `pace-signal-guide.md` for both the window and signal columns.

**Interpretation block:** one line per non-neutral, non-`no_stly` period, pulled verbatim from `pace-signal-guide.md`'s table for that period's `pace_signal` × `booking_window`. Skip neutral periods here (they still appear in the table).

**Listings without STLY (segment scope only):** list them by name in their own short block so the user knows they're in current totals but out of the variance math.

**Follow-up offer (segment scope, when `include_listing_detail` wasn't requested):** if any period came back non-neutral, offer a per-listing breakdown for that period, sorted by ADR pace per `pacing-calculations.md` §7.8.

**Automation payloads:** if the caller is downstream automation rather than a person reading the reply, state fields only — no prose interpretation, no icons, all variance fields present even when zero. `pace_signal`, `booking_window`, and `days_to_period_end` are always included regardless.

---

## Toggles

| Toggle | Default | Effect |
|---|---|---|
| `include_stly` | `true` | Skips the STLY fetch/comparison entirely when `false` — returns current-period absolutes only. |
| `include_adjusted_occupancy` | `true` | Skips the `price_calendar` calls when `false` — Occupancy (Adjusted) and its variance are omitted, `pace_signal` falls back to driving off Occupancy (unadjusted) instead. |
| `include_listing_detail` | `false` (segment scope) | Adds the full per-listing breakdown to the output instead of just the aggregate. |
| `include_interpretation` | `true` | Set `false` for automation payloads to drop the prose interpretation lines. |

State whichever defaults you're using in the summary if the user didn't specify — don't silently assume a fast, stripped-down pass when they asked for "the full picture."

---

## Edge cases

- **Listing/segment with zero reservations in range:** return zeros for all metrics, don't omit it from output.
- **`stly_value == 0`, `current_value > 0`:** variance % is `null` (not meaningful, not zero) — see the guard in `pacing-calculations.md` §5.
- **Multi-unit listings:** both `GetReservations` (implicitly, via the listing's units) and `GetPriceCalendar` need `unit_number` grouping — never sum across units as if they were one calendar.
- **Currency mismatch across a segment:** group and report separately per currency (§7 of the calculations reference); never sum raw amounts across currencies.
- **Reservation status field:** confirmed as `status` (e.g. `"Accepted"`) via a live call — filter out anything that isn't the accepted/confirmed value once a cancellation-style value is actually observed.

## 6. Documented v1 limitations (don't build silently — say so if asked)

- **No ad hoc filter scope.** Bedrooms/market/property-type filtering isn't built for v1 — only explicit listing lists and saved segments. If a user wants a filter that doesn't exist as a segment yet, the clean fast-follow is creating one via `wheelhouse_rmPostSegments`' `filter_backend` query language — that's a write action, so it needs explicit confirmation before creating it, same as any other write in this project.
- **Adjusted Occupancy's STLY side is a slightly looser comparison** than the Nights/Revenue/ADR STLY figures — see the caveat in `pacing-calculations.md` §6. Worth surfacing if a user leans heavily on the Adjusted Occupancy variance for a decision.
- **Field names for reservation status and price_calendar's booked/blocked state are now confirmed** via a live call: reservations use `status` (only `"Accepted"` observed so far — treat other values as excluded once seen); `price_calendar` uses `is_booked`/`is_available` (booked and available are confirmed complements in every row seen; a true blocked night would be `is_available: false` AND `is_booked: false`, not yet observed live but consistent with the schema). See `pacing-calculations.md` §4 and §6.
