---
name: Context-CustomRates
description: Use when a Wheelhouse client wants to set, replace, combine, or remove a Custom Rate via the connected Wheelhouse MCP -- a date-range price override that overrides the pricing engine's recommendation rather than participating in the preference rule hierarchy. Covers fixed vs. adjustment rate types, how overlapping date ranges silently split/replace existing rates, and the exact compounding math for combining a new instruction with an existing rate. Trigger on "set a custom rate for July 4th," "override my price for this weekend," "combine this with the existing rate," "did my custom rate replace the old one," or any one-off date-specific price override request. Not for changing what the pricing engine recommends going forward (see Context-Preferences) and not for the Season/Event date-range definition itself (see Context-Events&Seasons) -- a Custom Rate can cover an event's dates without being an event-type preference rule.
---

# Context-CustomRates (MCP)

Guidance for Wheelhouse Custom Rates: date-range price overrides that sit on top of the pricing engine's recommendation and don't participate in the rule hierarchy Context-Preferences governs. A Custom Rate on a holiday weekend doesn't remove or interact with a seasonal/event preference rule covering the same dates — it just overrides the *displayed price* for those dates.

**Before interpreting any request, check `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`.** "Custom rate" is explicitly flagged there — a client saying "custom price" or "custom rate" may actually mean a preference rule, not this object. Get this distinction right before calling anything: the giveaway is whether the client wants a one-off override for specific dates that wins regardless of other rules (→ this skill) vs. wants to change what the engine recommends going forward (→ Context-Preferences).

## Confirmed MCP tools (verified live)

- `wheelhouse_rmGetCustomRates(listing_id, channel)` — returns all **currently active, future-affecting** custom rate periods. Expired (`expires_at` passed) rates are excluded. This is current state, not history.
- `wheelhouse_rmGetPreferencesChangelog(listing_id, channel, start_date?, end_date?)` — despite the name, this is where **custom rate history** lives (added/split/removed events) — the Custom Rates endpoints themselves only report what's in force now. Read `event` on each entry to isolate `Custom rates` events from other changelog entries.
- `wheelhouse_rmPutCustomRate(listing_id, channel, start_date, end_date, rate_type, currency?, sunday..saturday?, expires_at?)` — single-listing, single-date-range create/replace.
- `wheelhouse_rmBulkPutCustomRates(listing_id, channel, custom_rates[])` — multiple date ranges in one request, single listing. `207` on partial success, `424` if all fail. **Live-tested 2026-09-15** on a real listing: two non-overlapping rates (one `fixed`, one `adjustment`) written in a single call, both landed correctly on the next `GetCustomRates` read alongside pre-existing rates, no unintended splits. **Confirmed response shape** (previously undocumented — the schema's `outputSchema` is an opaque `additionalProperties: true`): `{"updated_custom_rates": [<custom rate object>, ...]}`, one entry per rate written in the call.
- `wheelhouse_rmDeleteCustomRate(listing_id, channel, start_date, end_date)` — removes rates overlapping the range; truncates or splits a rate that only partially overlaps.
- `wheelhouse_rmBulkDeleteCustomRates(listing_id, channel, delete_ranges[])` — multiple date-range deletions in one request, single listing. `207`/`424` semantics match the bulk-put tool. **Live-tested 2026-09-15**: cleanly removed the two test rates above with a single call; the listing's rates reverted to exactly the pre-test state on the next read. **Confirmed response:** empty body on success (not a JSON object) — don't expect a parseable payload back from this call.

All four write/delete tools carry their own mandatory confirmation requirement baked directly into the live tool description — this section restates it because it's central to this skill, but always re-read the live tool description before calling, since it may be updated with more specifics than captured here.

## `fixed` vs. `adjustment` — verified field shapes

`wheelhouse_rmPutCustomRate` required fields: `listing_id`, `channel`, `start_date`, `end_date`, `rate_type` (`"fixed"` or `"adjustment"`). Optional: `currency`, `sunday`–`saturday` (per-weekday integer values, minimum 1), `expires_at`.

- **`fixed`**: an absolute nightly price. **Requires `currency`.** Per-day values are absolute prices in that currency. Bypasses `minimum_price_rules_v3` entirely — constrained only by `min_min_price` (the account-wide absolute floor).
- **`adjustment`**: a percentage multiplier on the Wheelhouse recommendation. Per-day values are percentages where **100 = no adjustment, 110 = +10%, 90 = −10%**. Additionally constrained by per-date `minimum_price_rules_v3` floors (unlike `fixed`, which bypasses them).

**Read-side tense mismatch:** when reading prices via price-recommendation endpoints, an `adjustment`-type custom rate appears as `custom_type: "adjusted"` (past tense). Reconcile this explicitly when comparing what was written (`rate_type: "adjustment"`) against what's read back (`custom_type: "adjusted"`) — they're the same thing under different field names at different points in the tense.

## Overlap behavior — rates don't stack by default

If a new date range overlaps an existing custom rate, **the existing rate is shortened, split, or fully replaced** so the new rate wins for the overlapping dates. This happens automatically and silently on write — there is no separate "are you sure" from the API itself beyond the tool's own confirmation requirement. Custom rates are **never additive by default**: a new `adjustment` rate does not compound with an existing one just because the date ranges overlap.

## Combining values — the mandatory protocol (verified from the live tool description, matches project instructions §10)

**Step 1 — Check for an existing rate first.** Before writing any rate for a listing/date range, call `wheelhouse_rmGetCustomRates` and check for an overlapping existing rate. Do not assume intent based on whether one exists.

**Step 2 — If an existing rate is found, ask the client to choose:**
- **(a) Adjust existing** — compound the requested change on top of what's already there, or
- **(b) Replace** — discard the existing rate and set only the new value

**Step 3 — If "adjust existing," compute the combined value yourself before calling the tool.** The tool does not compound automatically — whatever value is submitted is treated as final, verbatim, no server-side math.

- **`adjustment`-type: additive on percentage points.** Existing rate is 110 (+10%). Client requests +10% more. Submit **120** (+20% total) — **not** 110 × 1.10 = 121. Formula: `new_value = existing_value + requested_delta_points`.
- **`fixed`-type: multiplicative on the dollar value.** Existing rate is $100. Client requests +10%. Submit **$110** (100 × 1.10). Formula: `new_value = round(existing_value × (1 + requested_delta_pct / 100))`.

These two formulas are opposite operations — do not apply the `adjustment` math to a `fixed` rate or vice versa. Confirm which `rate_type` is in force before computing.

**Step 4 — Before calling, state to the client:** the listing, the exact date range(s), the rate type, the existing value (if any), the computed new value, which mode was used (adjust/replace), and flag explicitly if this overlaps (and will shorten/split/replace) an existing rate. Do not call until the client has explicitly confirmed the specific dates and values — not just the general intent.

## Deletion behavior

`wheelhouse_rmDeleteCustomRate`/`BulkDeleteCustomRates` remove all custom rates overlapping the given range(s). If a rate period extends beyond the deleted range on one side only, it's truncated to the non-overlapping portion. If the deleted range falls in the middle of an existing period, that period is **split into two** — before and after the deleted range. Deleted dates revert to the Wheelhouse recommended price (not to zero, not to a blank state). Confirm this outcome with the client before deleting, especially for a mid-period deletion that will produce two separate remaining rate periods where there was one.

## `expires_at` for speculative rates

Offer an expiring rate (`expires_at`, ISO date-time) for anything speculative — a rate the client wants to try but isn't committed to keeping indefinitely. This avoids a rate silently persisting past its intended relevance and being discovered months later as an unexplained override.

## Write protocol

1. Resolve ambiguity against the shared lexicon reference — confirm this is genuinely a Custom Rate request, not a preference-rule request.
2. Check for an existing overlapping rate (`wheelhouse_rmGetCustomRates`).
3. If one exists, ask adjust-vs-replace; if adjusting, compute the combined value using the correct formula for the rate type.
4. State the full plan to the client (listing, dates, rate type, existing value, computed new value, mode, overlap warning) and get explicit confirmation of the specific values — this is stricter than a general "yes, go ahead," per the tool's own description.
5. Write via `wheelhouse_rmPutCustomRate`/`BulkPutCustomRates`.
6. Offer to log a note (`wheelhouse_rmPostNote`) capturing the reasoning — especially valuable for a client-requested change or a speculative event rate flagged for future review.
7. For post-hoc verification of whether a custom rate led to bookings, hand off to the `custom-rate-attribution` skill rather than re-deriving that analysis here.

## See also

- **Context-Preferences** — for changing what the engine recommends going forward, rather than overriding it for specific dates.
- **Context-Events&Seasons** — a Custom Rate covering an event's dates is not the same as an `event`-type preference rule; don't conflate creating a Season/Event entry with setting a Custom Rate for those dates.
- **`${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** — terminology ambiguity, load before interpreting any request.
- **Context-PriceLabsMigration** — if the client says "Date-Specific Override" or expects rates to stack rather than replace, that's PriceLabs' mental model, not Wheelhouse's; see that skill before assuming intent.
