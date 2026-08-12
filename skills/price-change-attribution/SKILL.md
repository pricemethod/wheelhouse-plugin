---
name: price-change-attribution
description: Checks whether recent pricing changes (custom rates, seasonal/event rules, monthly rules, base price, global minimums, day-of-week, etc.) actually correlate with subsequent bookings, over a configurable 7- or 30-day lookback. Trigger for "did that price change work," "did my rate change get bookings," "check if pricing changes led to bookings," "price change impact," "did raising/lowering rates help," or any ask to review recent pricing edits against booking activity for a listing. Serves the Identify stage of Active Revenue Management — this is a post-hoc effectiveness check, distinct from stly-pacing (which compares current pace to last year, not to your own recent edits) and distinct from making a new rate change (see custom-rate-intervention workflow in project instructions §9 for that). Not for forward-looking "should I change my price" recommendations — this looks backward at changes already made.
---

# Price Change Attribution

Correlates recent pricing/preference changes on a listing with the bookings that followed, distinguishing changes that can be tied to specific dates from changes that can only be read as a pace trend. See the project instructions document for shared conventions (terminology, `listing_id`+`channel` pairing, rate limiting, revenue basis) — this file only covers what's specific to this workflow.

## When to use this skill

- "Did the rate change I made on the Smith property lead to bookings?"
- "Check if my custom rates for August actually booked"
- "Has raising the base price hurt or helped pace?"
- "Review the last 30 days of pricing changes against bookings"

Not for: making a new pricing decision (that's the Intervention Matrix / custom-rate-intervention workflow), or comparing pace to last year (that's `stly-pacing`).

## Inputs

| Param | Default | Notes |
|---|---|---|
| `listing_id` + `channel` | — | Required pair, resolved via `GetListings` if not already known this session |
| `lookback_days` | 30 | How far back to check for changes. Configurable to 7, or any value up to the API's 90-day changelog ceiling |
| `revenue_basis` | `rent` | Per project convention — state the default in output |

## Workflow

### Step 1 — Resolve listing and pull the changelog

Confirm `listing_id`+`channel` (via `GetListings` if not already cached this session). Call `wheelhouse_rmGetPreferencesChangelog` with `start_date = today - lookback_days`, `end_date = tomorrow` (the endpoint's own default). Remember: **values earlier than 90 days back are silently clamped** — if the user asks for a longer lookback, tell them the actual window used.

Drop every event where `source == "Wheelhouse"` (these are `"Prices posted"` sync confirmations, not preference changes, and carry no `msg` content worth parsing).

**Exclude same-day changes from attribution.** Any change with a `time` on today's calendar date hasn't had time to generate bookings yet — comparing it against reservations would just produce a false "no impact" read. Don't silently drop these, though: list them in output under a distinct "too recent to evaluate" note (what changed, when, today) so the RM knows it exists and can re-check tomorrow, but skip Step 4/5 attribution logic for them entirely.

### Step 2 — Parse and classify changes

Each remaining event's `msg` is an HTML string with `<br>`-separated lines, not structured fields. Split on `<br>` and classify each line independently — one event commonly bundles several unrelated changes (e.g. a Global + Monthly + Date-specific minimum-price edit fired together). Full parsing rules, regex patterns, and worked examples are in `references/changelog-parsing.md` — **read that file before implementing this step**. Summary of the three buckets:

| Bucket | Signal | Attribution method |
|---|---|---|
| **Date-scoped** | Explicit date range in the line ("From Aug 01, 26 to Aug 31, 26"), or a Custom Rates "added"/"Fixed rate added" line | Direct join to reservations on `stay_date` in range |
| **Month-scoped** | "Monthly ... modified: [Jan, Feb, ...]" | Filter reservations by `stay_date` month membership, any year |
| **General** | Global, Default, Time-based ("After N day(s)"), or base price lines | Pace-trend comparison, not a booking join |

For Custom Rates events specifically: **only "added" / "Fixed rate added" lines are actionable changes.** "Removed" and "split off" lines are bookkeeping byproducts of the same edit (Wheelhouse reshapes overlapping date ranges internally) — ignore them for attribution. When the same date range has multiple "added" events within the lookback window, use the **most recent one** as the effective change (and its timestamp as the booking cutoff), but surface the edit count as context ("this range was edited 3 times in the last 7 days").

**This latest-wins-plus-edit-count rule isn't specific to Custom Rates** — any date-scoped setting can be edited more than once within the lookback window (e.g. a "Date-specific minimum stays" range widened from one edit to the next a minute later). Apply the same rule generally: for any date-scoped or month-scoped change bucket, if the same setting+range is touched more than once in the window, use the latest value and its timestamp, and note the edit count.

For a "Base price changed to recommended" line (no dollar figure given), only call `wheelhouse_rmGetBasePriceHistory` to resolve the actual dollar value **if the user's output would otherwise be incomplete** — skip this call when the line already states a dollar amount, to avoid burning a call that isn't needed.

### Step 3 — One reservations pull covers everything

Do **not** make a separate `GetReservations` call per change. Make a single call:

- `date_filter_type=booked_at`
- `start_date = today - lookback_days - 30` (the extra 30 days covers the pace-baseline window from Step 5)
- `end_date = today + 1`
- Paginate (`per_page=100`) until a page returns fewer than 100 results.

**Filter to `status == "Accepted"` before any counting.** Canceled reservations show up in this same pull and must not be counted as bookings resulting from a change — a canceled stay isn't evidence a price change worked.

Every downstream step (date-scoped joins, month-scoped joins, and the general pace comparison) filters this same in-memory result set rather than issuing new calls. This keeps the whole skill to roughly 3 API calls (`GetListings` if needed, `GetPreferencesChangelog`, one paginated `GetReservations` pull) regardless of how many changes are found — well under the ~20-call confirmation threshold in the project instructions, so no call-budget warning is needed for single-listing use.

### Step 4 — Date-scoped and month-scoped attribution

For each date-scoped change: from the Step 3 result set, take reservations where `stay_date` falls in the change's date range AND `booked_at` ≥ the change's timestamp. Report booking count, nights, revenue, and ADR (per `revenue_basis`) for that set.

For each month-scoped change: same, but filter on `stay_date`'s month being in the change's month list (any year present in the data) AND `booked_at` ≥ the change's timestamp.

If a date-scoped or month-scoped change has zero qualifying bookings, say so plainly — that's a real (negative) signal, not a null result to omit.

**Display merge:** when a single changelog event produces several "added" sub-ranges with the same value (e.g. a Sun–Thu −15% rate rolled out across five near-contiguous ranges in one edit), merge them into one displayed change for readability. This is presentation-only — each sub-range is still independently joined against reservations in Step 3/4; only the reporting groups them back together under the one underlying decision.

**Month-scoped matching uses the reservation's stay *start* date's month** — not any-night overlap. A stay spanning a month boundary (e.g. Jul 31 – Aug 2) is attributed to whichever month-scoped change covers July, not August, even though it has a night in August. Simple and deliberate, not an oversight.

### Step 5 — General/pace-trend attribution

For each general change, compute a **stable 30-day baseline pace** and compare it to the **pace during the lookback window itself**:

- **Baseline**: the 30 days immediately before the lookback window starts (i.e., `today - lookback_days - 30` through `today - lookback_days`), expressed as a per-day rate (nights/day, bookings/day, revenue/day → ADR).
- **Check window**: the lookback window itself (7 or 30 days), same per-day rate calculation.
- Compare the two per-day rates directly — this is what makes a 7-day check window comparable to a 30-day baseline without a raw-total mismatch.

Full formulas and a worked example are in `references/pace-benchmark-calculations.md`.

This is a trend correlation, not a causal claim — **always label it as such in output**, and note that the baseline period may itself contain other changes (expected; it's a "normal pace" reference, not a controlled comparison).

### Step 6 — Output

Structure output as three sections, in this order, followed by a short closing assessment. Same-day ("too recent to evaluate") changes get their own short list after the three tables, not folded into them.

**1. Positive Attribution — Date-Scoped & Month-Scoped Changes**

One row per change that has at least one qualifying booking. Table columns:

| Change | Date Range / Months | Made At | Edits in Window | Bookings | Nights | Revenue | ADR |
|---|---|---|---|---|---|---|---|

"Change" is the plain-language setting + value (e.g. "Fixed rate $60/$98"). "Edits in Window" is the count from the latest-wins rule (only show if >1). Revenue/ADR follow `revenue_basis`. Omit this table entirely if nothing qualifies, and say so in one line rather than showing an empty table.

**2. General Changes — Pace Impact**

One row per general change evaluated (i.e., not same-day). Table columns:

| Setting | New Value | Edits in Window | Nights/day (baseline → check, Δ%) | Bookings/day (baseline → check, Δ%) | ADR (baseline → check, Δ%) | Read |
|---|---|---|---|---|---|---|

"Read" is the interpretation band from `references/pace-benchmark-calculations.md` (increased / no material change / decreased). If a base price line was "changed to recommended" and required `GetBasePriceHistory` to resolve, show the resolved dollar figure in "New Value."

**3. No-Impact Zones (negative signal)**

Date-scoped or month-scoped changes with **zero** qualifying bookings — this is a real finding, not a null result to omit. Columns:

| Change | Date Range / Months | Made At | Edits in Window | Days Since Change | Note |
|---|---|---|---|---|---|

Use "Note" for anything that changes how the zero should be read — e.g. "stay dates still ~3 weeks out, too early to call this a miss" vs. "dates are imminent and still empty."

**Too recent to evaluate:** a short list (not a table) of same-day changes, so the RM knows they exist without their being scored — "re-check tomorrow."

**Closing assessment:** 2–4 sentences of plain-language takeaways and caveats — correlation-not-causation reminder for the general table, any edit-cascade complexity worth flagging (e.g. rapid same-day rate churn that makes per-edit attribution noisy), and anything from the Edge Cases list below that applied to this run.

## Edge cases

- **Multiple overlapping changes to the same setting within the window** — resolved by latest-wins per §2 above; don't attempt to reconstruct full edit history.
- **Change made very recently (e.g., yesterday)** — the check window will be very short; report the raw numbers plainly rather than trying to project or annualize them.
- **No changes found in the window** — say so; don't run the reservations pull for nothing.
- **Listing has fewer than ~30 days of reservation history** (new listing) — the baseline pace will be noisy or unavailable; flag this rather than presenting a misleading comparison.
