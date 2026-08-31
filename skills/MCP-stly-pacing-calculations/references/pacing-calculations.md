# Pacing Calculations Reference

Full arithmetic for `stly-pacing`. Read this when actually computing a pacing report; the SKILL.md body covers when/how to orchestrate the tool calls.

---

## 1. Resolving the target date range into periods

The workflow always ends up with one overall `[overall_start, overall_end]` range, which is then sliced into **periods** for the trend view. A period is usually a calendar month, but doesn't have to be.

**Resolving the overall range from the user's request:**
- Explicit dates given ("June through September") → use them directly.
- "N months" (the classic case, default when the user just says "pacing" with no range) → Period 1 is the **full current calendar month** (all stay dates, not just remaining days — this gives a true full-month view no matter where in the month "today" falls), then N−1 more full calendar months after it.
- "next N days" / a rolling window ("next 60 days") → `overall_start = today`, `overall_end = today + N days`.
- A named single period ("this month," "August," "Q3") → resolve to its calendar boundaries directly.
- No range given at all → default to the 4-full-month view (today's month + next 3), matching the standard pacing check-in.

**Slicing into periods for the trend table:**
- If the overall range was built from calendar months, each month is its own period (this is the common case and matches the worked example below).
- If the overall range is a rolling day-count or a single short custom range (under ~40 days), don't fragment it — treat it as one period, unless the user explicitly asks for a weekly breakdown, in which case slice into 7-day chunks starting from `overall_start`.
- The **combined total** row always aggregates every period together, regardless of how they were sliced.

**Worked example (calendar-month case):** if today is June 15, 2026 and the user asked for 4 months:
- Period 1: June 1–30, 2026 (full month)
- Period 2: July 1–31, 2026
- Period 3: August 1–31, 2026
- Period 4: September 1–30, 2026

---

## 2. Booking window classification

Every period gets a `days_to_period_end` value (calendar days from today to the last day of that period, inclusive) and a `booking_window` label. This drives which interpretation guidance applies (see `pace-signal-guide.md`) and lets downstream automation weight urgency.

```
days_to_period_end = last_day_of_period − today
```

| `booking_window` | `days_to_period_end` | Typical mapping (4-month view) |
|---|---|---|
| `immediate` | 0–15 | Period 1, mid-to-late in the month |
| `short` | 16–45 | Period 2 |
| `medium` | 46–75 | Period 3 |
| `long` | 76–135 | Period 4 |
| `far` | 136+ | Periods beyond a standard 4-month view |

When today is mid-month, Period 1 legitimately lands in `immediate` — that's correct and meaningful, not a bug: it signals limited runway on that period. For non-calendar-month periods (rolling windows, weekly slices), compute `days_to_period_end` the same way from each slice's own end date.

---

## 3. STLY cutoff and fetch strategy

**Cutoff:** `stly_cutoff_date = today − 365 days`. For each period, STLY = reservations with stay dates in the *equivalent period one year earlier*, filtered to `booked_at ≤ stly_cutoff_date`. This reconstructs "what was on the books at the equivalent point in last year's booking cycle" — not last year's final actuals.

Apply the same cutoff uniformly across the whole period, including any portion of a current, partially-elapsed period — a stay date that's already passed will always satisfy `booked_at ≤ cutoff` on the prior-year side (it had to be booked before the night occurred), so no special-casing is needed for past-vs-future portions of Period 1.

**Reservations fetch (per listing, per side):**
```
Wheelhouse:wheelhouse_rmGetReservations
  listing_id, channel
  date_filter_type = stay_date
  start_date = first_day_of_period_1 − 30 days     (current side)
             = first_day_of_period_1_prior_year − 30 days   (STLY side)
  end_date   = last_day_of_final_period            (current side)
             = last_day_of_final_period_prior_year (STLY side)
  per_page = 100, paginate until a page returns < 100
```
The 30-day backward extension guarantees you catch reservations that check in before the window but have some stay nights falling inside it (a booking spanning May 28–June 3 needs to be caught even though the window starts June 1). Then pro-rate (§4) so only nights actually inside a target period count toward that period.

For the STLY side, after fetching, filter client-side to `booked_at ≤ stly_cutoff_date` before pro-rating.

**Reservation status:** confirmed field name is `status` (observed value `"Accepted"` in a live sample). Include only reservations whose `status` matches the accepted/confirmed value; exclude anything else (e.g. a cancellation status) once its exact string is observed — the sample pulled so far hasn't contained one.

**When STLY is unavailable** (listing under 12 months old, or zero prior-year reservations found): return `null` for all STLY/variance fields on that listing with `stly_available: false`.

---

## 4. Pro-ration for cross-boundary reservations

**Confirmed reservation fields from a live call:** `start_date`, `end_date` (stay dates), `booked_at`, `status` (observed value: `"Accepted"` — other values such as cancellations likely exist but weren't present in the sample pulled; exclude any reservation whose `status` isn't the confirmed/accepted value once more values are observed), `nightly_subtotal` (this is the **total** subtotal for the whole stay, not a per-night figure — divide by nights as below), `extra_guest`, `security_deposit`, `extras`, `taxes` (all frequently `null` — treat as 0 per the null-fee handling below), `total_price`, `currency`, `confirmation_code`, `source_name`.

```
total_nights        = end_date − start_date   (days)
nightly_rate        = nightly_subtotal / total_nights
gross_nightly_rate  = (nightly_subtotal + extra_guest + extras) / total_nights

nights_in_period    = count of nights from this reservation's stay falling inside the target period
revenue_for_period       = nightly_rate × nights_in_period
gross_revenue_for_period = gross_nightly_rate × nights_in_period
```

- **Taxes and security deposits are excluded** from every revenue figure — taxes are a pass-through, not revenue, and a security deposit is a hold. This means this skill's revenue figures are Revenue (Rent) and Revenue (+Fees) only; it does not produce an `all_in` (+Taxes) figure. If the user specifically needs a taxes-inclusive gross figure, that's a different workflow (Daily Booking Review / Owner Reporting), not this one.
- **Null fee handling:** treat missing `extra_guest`/`extras` as 0; still include the reservation using `nightly_subtotal` alone for the gross figure.

---

## 5. Metric formulas

| Metric | Formula | Null guard |
|---|---|---|
| Nights (Booked) | sum of pro-rated nights in the period | — |
| Revenue (Rent) | sum of pro-rated `revenue_for_period` | — |
| Revenue (+ Fees) | sum of pro-rated `gross_revenue_for_period` | — |
| ADR (Rent) | Revenue (Rent) ÷ Nights (Booked) | `null` if Nights (Booked) = 0 |
| ADR (+ Fees) | Revenue (+ Fees) ÷ Nights (Booked) | `null` if Nights (Booked) = 0 |
| Occupancy (unadjusted) | Nights (Booked) ÷ Nights (Calendar) | Nights (Calendar) = total days in the period |
| Occupancy (Adjusted) | Nights (Booked) ÷ Nights (Bookable) | Nights (Bookable) = Nights (Calendar) − Nights (Blocked); see §6 |

**Important:** the `Nights (Booked)` in the Adjusted Occupancy formula is the *same* reservations-derived figure computed above (STLY-cutoff-filtered on the prior-year side) — not a recount of `is_booked: true` rows from `price_calendar`. `price_calendar` is consulted only to get `Nights (Blocked)` for the denominator. This matters specifically on the STLY side: `price_calendar` reflects how each date *ultimately* settled, so a `price_calendar`-based booked-night count would include reservations made *after* the STLY cutoff and silently break the on-the-books comparison. Keep the numerator and denominator sourced from two different fetches on purpose.

**Variance (absolute):** current − STLY.
**Variance (%):**
```
if stly_value is null                        → variance_pct = null
if stly_value == 0 and current_value == 0    → variance_pct = 0.0
if stly_value == 0 and current_value > 0     → variance_pct = null   (not meaningful)
otherwise                                    → round((current − stly) / stly × 100, 1)
```

---

## 6. Adjusted Occupancy via price_calendar

`wheelhouse_rmGetPriceCalendar` returns, per stay date, the price/availability/booking state — and critically, **for past dates it returns the state the date ended up in** (booked, blocked, or left available), not just a live snapshot. That makes it usable for the STLY side, not only the current side.

**Fetch (per listing, per side, one call each — no pagination, no 30-day lookback needed since each row is a single date, not a multi-night stay):**
```
Wheelhouse:wheelhouse_rmGetPriceCalendar
  listing_id, channel
  start_date = first_day_of_period_1                        (current side)
             = first_day_of_period_1_prior_year              (STLY side)
  end_date   = last_day_of_final_period                      (current side)
             = last_day_of_final_period_prior_year            (STLY side)
```
Max range is 3 years, so a STLY-shifted window is always within bounds.

**Classify each row** using the confirmed fields from a live call: `is_booked` (boolean), `is_available` (boolean), `reservation_id`, `block_time`. In every row observed so far, `is_available` is exactly the complement of `is_booked` (booked → `is_available: false`; open → `is_available: true`) — no row has shown both `false`, which is what a genuine owner-hold (blocked) night would look like. So: **booked** = `is_booked: true`; **available** = `is_available: true`; **blocked** = `is_available: false` AND `is_booked: false` (inferable from the schema, not yet observed in a live sample — if a listing truly has no owner holds in the requested window, Nights (Blocked) is legitimately 0, which makes Adjusted Occupancy equal Unadjusted Occupancy for that window). For **multi-unit listings**, group rows by `unit_number` first (single-unit listings report `unit_number: 0`) — don't mix units together when counting.

```
Nights (Bookable)      = Nights (Calendar) − Nights (Blocked)
Occupancy (Adjusted)   = Nights (Booked) ÷ Nights (Bookable)
```

**Caveat to disclose to the user:** unlike the reservations-based booked-nights comparison (which uses a strict `booked_at ≤ cutoff` filter to reconstruct the exact on-the-books position a year ago), the STLY blocked-night count reflects however that calendar day *ultimately* settled — not necessarily its blocked state as of the STLY cutoff date specifically. In practice this is a minor caveat (owner holds are usually set well in advance and rarely revised after the fact), but it means Adjusted Occupancy's STLY comparison is a slightly looser apples-to-apples match than the Nights Booked / Revenue / ADR comparison.

**Speed trade-off:** this doubles the calendar-side API calls (2 extra per listing: current + STLY `price_calendar`, on top of the 2 reservations calls). If a user wants a fast preliminary pass, offer `include_adjusted_occupancy: false` to skip it and return unadjusted occupancy only.

---

## 7. Currency grouping and aggregation (multi-listing / segment scope)

1. Compute each listing's per-period metrics independently (§1–§6).
2. Group listings by `currency` (from `GetListings`); aggregate only within a currency group.
3. Within a group, sum `nights_booked`, `revenue_rent`, `revenue_gross`, `calendar_days`, `blocked_days` across listings for each period.
4. Recompute ratios from the summed values — don't average per-listing ratios:
   ```
   occupancy_pct     = sum(nights_booked) / sum(calendar_days)
   occupancy_adj_pct = sum(nights_booked) / sum(calendar_days − blocked_days)
   adr_rent          = sum(revenue_rent) / sum(nights_booked)   (null if 0)
   ```
5. Apply variance/pace-signal math (§5, and `pace-signal-guide.md`) to the aggregated current/STLY totals — same formulas, just fed with summed inputs.
6. `days_to_period_end` and `booking_window` are calendar-derived, not listing-derived — identical across all listings and the aggregate.
7. Listings with `stly_available: false` are included in current-year totals but excluded from STLY/variance math; call out their names in the output rather than silently dropping them.
8. If per-listing detail is requested, sort by `total.variance.adr_rent_pct` descending (best ADR pace first, consistent with ADR driving the signal) — listings without STLY sort after, by current `adr_rent` descending.

---

## 8. Call-volume estimate and rate-limit guardrail

Per listing, with both STLY and Adjusted Occupancy on (the default per this skill):
```
~2 calls  — reservations, current side (1–2 pages typically)
~2 calls  — reservations, STLY side
1 call    — price_calendar, current side
1 call    — price_calendar, STLY side
──────────
~6 calls per listing (fewer if include_stly or include_adjusted_occupancy is turned off)
```
Plus 1–3 calls to resolve the listing set itself (`GetListings` or `GetSegmentListings`, paginated).

Per the project's general rate-limit rule: **before running more than ~20 total calls, tell the user the estimate and let them choose to proceed, narrow scope, or turn off STLY/adjusted-occupancy for a faster pass.** At ~6 calls/listing that threshold arrives around 3–4 listings — call this out plainly rather than silently batching through it. Batch actual execution in groups of ~5 listings with pauses so as not to exceed 20 requests/minute; back off exponentially (1s → 2s → 4s → … capped at 60s, ±10–20% jitter) on any `429`.
