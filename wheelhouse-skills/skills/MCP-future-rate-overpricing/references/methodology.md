# Methodology & Worked Example

Detailed calculation logic for the per-month, per-bucket comparison described in SKILL.md Steps 1-6. Read this before implementing the calculation; read `exclusion-and-edge-cases.md` before implementing Step 3 and the tenure guard.

## Per-night rollup (Step 2)

`GetReservations` returns `nightly_subtotal` as the **total** for the stay, not a per-night figure, and does not break out which portion of that total applied to which specific night. The correct approach:

1. `nights = (end_date − start_date)` in days.
2. `avg_nightly_rate = nightly_subtotal ÷ nights`.
3. Classify each night in the stay as WE (Fri/Sat) or WD (Sun-Thu) by its calendar date.
4. Add `avg_nightly_rate` to the running revenue total for each bucket the stay touches, once per night in that bucket. A 4-night stay with 2 WD nights and 2 WE nights contributes `2 × avg_nightly_rate` to WD revenue and `2 × avg_nightly_rate` to WE revenue.
5. Bucket ADR = (summed revenue for the bucket) ÷ (summed nights for the bucket), across all qualifying reservations in the month.

This is a deliberate approximation — the endpoint doesn't expose true intra-stay nightly variation — and is the same principle already established for per-night rollup in `price-drop-pickup-analysis`.

## Historical occupancy (Step 2)

`Occupancy (Adjusted) = Nights(Booked) ÷ Nights(Bookable)` for the bucket, using the count of WE or WD nights actually booked (from the reservations pulled above) against the count of WE or WD calendar nights available in that month (excluding owner-blocked nights if that data is available; otherwise total calendar nights for the bucket is an acceptable fallback — note which one was used in output).

## Confidence weighting matrix (Step 5)

| Historical Occupancy | Headline Flag | Confidence | Interpretation |
|---|---|---|---|
| Low (<~50%) | Overpriced | High | Demand already rejected a lower rate; a higher future rate is unlikely to do better |
| High (≥~70%) | Overpriced | Low | Sold through at the lower rate; may reflect legitimate repositioning (renovation, new comp set data, inflation) rather than overpricing |
| Low (<~50%) | Underpriced | Low | Soft demand at the historical rate could just mean weak demand, not necessarily room to raise |
| High (≥~70%) | Underpriced | High | Sold through easily at a lower rate — real evidence of room to raise |
| Mid-range | Either | Medium | No strong tempering signal either way |

These thresholds (50%/70%) are starting points, not hard-coded constants — treat them the same way the pace-signal-guide treats its bands, and revisit if a listing's own historical occupancy distribution suggests different natural breakpoints.

## Worked example (validated against real data — The Luzianne, listing 3995218, rentalsunited)

This is the actual dry-run result that validated the design, kept here as a reference case for what correct output looks like, including a genuine market/headline disagreement.

**November, WD bucket:**
- Future Asking Rate (Nov 2026, Sun-Thu nights): $159.50
- Last Year ADR (Nov 2025, Sun-Thu nights, per-night rollup): $71.85
- Last Year Occupancy (Adjusted): 43% (9 of 21 WD nights booked)
- Delta: +122% → **Overpriced**
- Confidence: Medium (43% sits between the low/high bands)

**November, WE bucket:**
- Future Asking Rate (Nov 2026, Fri/Sat nights): $330.00
- Last Year ADR (Nov 2025, Fri/Sat nights): $120.85
- Last Year Occupancy (Adjusted): 100% (9 of 9 WE nights booked)
- Delta: +173% → **Overpriced** on raw delta, but confidence **Low** per the matrix above (sold through completely last year at the lower rate)

**Market cross-check (Step 7, triggered because both buckets flagged):**
- `GetNeighborhoodPricing` for the same November dates showed a neighborhood median around $331 (WD) and $403 (WE) — meaning the future Asking Rate is actually **at or below** the neighborhood median, not above it.

**Read:** The headline ADR-based signal says heavily overpriced; the market check says priced under the neighborhood median. This is not a contradiction to resolve away — it's the intended output of Phase 2. Here the disagreement points toward the *historical* side being the less reliable baseline (this listing had under 12 months of operating history at the time, and its first-year pricing likely reflected new-listing ramp-up discounting — see `exclusion-and-edge-cases.md` for the tenure guard that would flag this in future runs). Report both signals plainly and let the disagreement itself be part of the takeaway, rather than picking one to lead with.
