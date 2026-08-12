---
name: custom-rate-intervention
description: Applies a manual custom rate (fixed nightly price or percentage adjustment) to a listing date range via wheelhouse_rmPutCustomRate or bulk equivalents. Trigger for "set a custom rate," "override prices for these dates," "put a fixed rate on the holiday weekend," "adjust rates +10% for August," or after a diagnostic skill (future-rate-overpricing, Intervention Matrix) leads the user to want a rate write. Serves the Intervene stage of Active Revenue Management. Not for checking whether a past change worked (price-change-attribution), on-the-books pacing (stly-pacing), or preference/rule-array edits (use wheelhouse-rm-mcp + wheelhouse_rmPutPreferences).
---

# Custom Rate Intervention

Write a **custom rate** for a listing date range — a date-scoped override that sits on top of the recommendation engine. Shared conventions (auth, `listing_id`+`channel`, write confirmation, rate limits) live in `skill://wheelhouse-project-instructions/SKILL.md` and `skill://wheelhouse-rm-mcp/SKILL.md`; this skill covers only the custom-rate write path.

**Mutating.** Confirm with the user before every write. Show the proposed rate type, dates, per-day values, overlap impact, and (for adjustments) replace-vs-combine choice.

## When to use this skill

- "Set a fixed $350 rate for Memorial Day weekend on the Smith property"
- "Bump August midweek rates +10%"
- "Put an expiring custom rate on next month's gap nights"
- After `future-rate-overpricing` (or similar) flags risk and the user wants to act

Not for: reviewing whether a past rate edit led to bookings (`price-change-attribution`), STLY pacing (`stly-pacing`), or editing preference rule arrays (`minimum_price_rules_v3`, etc. — that is `wheelhouse_rmPutPreferences` via `wheelhouse-rm-mcp`).

## Tools

| Step | Tool |
|---|---|
| Resolve listing | `wheelhouse_rmGetListings` / `wheelhouse_rmGetListing` |
| See existing rates | `wheelhouse_rmGetCustomRates` |
| Optional preview context | `wheelhouse_rmGetPriceCalendar`, `wheelhouse_rmGetPriceRecommendations` |
| Single write | `wheelhouse_rmPutCustomRate` |
| Multi-range / multi-listing | `wheelhouse_rmBulkPutCustomRates` |
| Remove | `wheelhouse_rmDeleteCustomRate` / `wheelhouse_rmBulkDeleteCustomRates` |
| Optional log | `wheelhouse_rmPostNote` |

## Workflow

### 1. Resolve listing and date range

Confirm `listing_id` + `channel`. Normalize dates to `YYYY-MM-DD`. Validate `start_date ≤ end_date`.

### 2. Fetch overlapping custom rates

Call `wheelhouse_rmGetCustomRates` for the listing. A new rate **replaces/splits** overlapping rates — it does not stack. Show the user which existing ranges will be shortened or split before writing.

### 3. Choose `fixed` vs `adjustment`

| `rate_type` | Meaning | Per-day fields (`sunday`–`saturday`) | Min-price interaction |
|---|---|---|---|
| `fixed` | Absolute nightly price | Dollar amounts; `currency` required | Constrained only by `min_min_price` (bypasses `minimum_price_rules_v3`) |
| `adjustment` | Multiplier on Wheelhouse recommendation | Percentages where **100 = no change**, 110 = +10%, 90 = −10% | Also floored by per-date `minimum_price_rules_v3` |

### 4. Replace vs combine (adjustments only)

The API never compounds. If an overlapping `adjustment` already exists and the user asks to "add another 10%":

1. Fetch the current multiplier.
2. Ask whether they want to **replace** it or **combine** it.
3. If combining, confirm **additive** (10% + 10% → submit `120`) vs **multiplicative** (1.10 × 1.10 → submit `121`).
4. Show the final per-day values before writing.

### 5. Confirm, write, verify

Show a concise plan: listing name/`listing_id`, dates, rate type, per-day values, currency (if fixed), `expires_at` (if any), and overlap impact. After explicit approval:

1. Call `wheelhouse_rmPutCustomRate` (or bulk).
2. Re-read with `wheelhouse_rmGetCustomRates` (and optionally the price calendar) to verify.
3. Offer `wheelhouse_rmPostNote` for speculative or owner-requested changes.

For speculative rates, prefer an `expires_at` so the override does not linger forever.

## Output

After a successful write, report:

- Listing title/nickname and `listing_id` + `channel`
- Date range and rate type
- Per-day values (and currency for fixed)
- Whether an existing rate was replaced/split
- `expires_at` if set
- Verification result from the re-read

## Edge cases

- **Day-of-week partial fills** — omit unused weekday fields only if the tool schema allows; prefer sending explicit values for every day in the requested pattern so the intent is clear.
- **Read vs write type name** — writes use `adjustment`; recommendation/calendar reads may show `custom_type: "adjusted"`. Match them deliberately when reconciling.
- **Bulk partial failure** — `207` means some succeeded; surface per-item errors. `424` means all failed.
- **Read-only key / 403** — stop; tell the user write access is required.
- **Preference rule change vs custom rate** — if the user wants a lasting seasonal/event minimum or seasonality rule, that is `wheelhouse_rmPutPreferences` (fetch-then-merge rule arrays), not this skill.
