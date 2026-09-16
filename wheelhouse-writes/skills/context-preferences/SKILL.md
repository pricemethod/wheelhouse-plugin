---
name: Context-Preferences
description: Use when a Wheelhouse client asks to change any pricing-engine or rule-hierarchy setting via the connected Wheelhouse MCP -- base price, seasonality, day-of-week, last-minute/far-future, min/max price, min stay, demand sensitivity, historical anchoring, check-in/check-out, long-term discounts, occupancy pacing, or gap-night pricing. Covers the rule-type hierarchy, fetch-then-merge write safety, PreviewPreferences, and per-channel setting support. Trigger on "change my base price," "add a day-of-week rule," "set a minimum price for July," "adjust my seasonality," "turn on X preset," or any request to configure how Wheelhouse prices a listing going forward. Not for one-off date-range overrides that should win regardless of engine rules (see Context-CustomRates) and not for defining the Season/Event date range itself (see Context-Events&Seasons, which this skill defers to for seasonal/event rule types).
---

# Context-Preferences (MCP)

Guidance for using the connected Wheelhouse MCP to read and write a listing's pricing-engine preferences: the rules that drive Wheelhouse's ongoing recommendation engine, as opposed to one-off Custom Rate overrides (Context-CustomRates) or the Season/Event date-range definitions rules can reference (Context-Events&Seasons).

**Before interpreting any request, check `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** for terms that don't mean what they sound like ("seasonal rate," "custom rate," "base rate," "channel," etc.). Getting the wrong Wheelhouse object from a client's plain-language request is the single biggest risk in this workflow — resolve ambiguity before touching any tool.

## The two systems, and where this skill sits

Wheelhouse splits pricing configuration into two systems that don't interact the same way:

- **Preferences** (this skill): rules that drive the ongoing recommendation engine. Can be global, day-of-week, monthly, time-based, seasonal, event, or date-specific (`custom`). This is what you're reading/writing here.
- **Custom Rates** (Context-CustomRates): a value that overrides the engine's output for specific dates. Doesn't participate in the rule hierarchy below — it just wins for its dates. A Custom Rate on a holiday weekend doesn't remove a seasonal/event preference rule covering it, it overrides the *displayed price* only.

If a client's request is really "set a specific price for these dates no matter what the engine says," that's Context-CustomRates, not this skill.

## Settings this skill covers

| UI Group | Setting | API field(s) | MCP write path |
|---|---|---|---|
| Pricing Engine | Base price | `base_price`, `base_price_adjustment` | `wheelhouse_rmPutPreferences` (or `wheelhouse_rmPutPreferenceSetting` for a CON/REC/AGG preset on `base_price_adjustment`) |
| Pricing Engine | Seasonality | `seasonality_adjustment` | `wheelhouse_rmPutPreferences` / `wheelhouse_rmPutPreferenceSetting` |
| Pricing Engine | Day of week | `day_of_week` | `wheelhouse_rmPutPreferences` |
| Pricing Engine | Last minute | `last_minute_discount` | `wheelhouse_rmPutPreferences` / `wheelhouse_rmPutPreferenceSetting` |
| Pricing Engine | Far future | `far_future_premium` | `wheelhouse_rmPutPreferences` / `wheelhouse_rmPutPreferenceSetting` |
| Pricing Engine | Gaps & Adjacencies (pricing) | `gap_night` | `wheelhouse_rmPutPreferences` — **pricing-only**, distinct from the `gap`/`adjacency` rule *types* under Minimum Stays below |
| Model Weights | Demand sensitivity | `demand_sensitivity_rules` | `wheelhouse_rmPutPreferences` |
| Model Weights | Historical anchoring | `historical_anchoring_rules` | `wheelhouse_rmPutPreferences` |
| Limits | Maximum prices | `maximum_price_rules_v3` | `wheelhouse_rmPutPreferences` |
| Limits | Minimum prices | `minimum_price_rules_v3`, `min_min_price` (absolute floor) | `wheelhouse_rmPutPreferences` |
| Operations | Minimum stays | `minimum_stay_rules_v3`, `min_min_stay` (absolute floor), `min_stays_enabled` | `wheelhouse_rmPutPreferences` |
| Operations | Length of stay pricing | `long_term_discounts`, `weekly_discount`, `monthly_discount` | `wheelhouse_rmPutPreferences` |
| Calendar Pacing | Occupancy pacing | `occupancy_pacing` | `wheelhouse_rmPutPreferences` |
| Configuration | Events & Seasons | `custom_date_ranges` | `wheelhouse_rmPutPreferences` — see Context-Events&Seasons for the ID-resolution protocol before writing here |
| (top-level) | Check-in/check-out | `checkin_checkout` (`check_in_rules`, `check_out_rules`) | `wheelhouse_rmPutPreferences` |
| (top-level) | Automatic rate posting | `automatic_rate_posting_enabled` | `wheelhouse_rmPutPreferences` / `wheelhouse_rmPutPreferenceSetting` (`enabled` toggle) |
| (top-level) | Price model | `price_model` | pass through explicitly on read/write recommendation calls; never switch a listing's active model without being asked |

## Confirmed MCP tools (verified live against the connected Wheelhouse MCP)

- `wheelhouse_rmGetPreferences(listing_id, channel)` — read one listing's full preferences.
- `wheelhouse_rmGetPreferencesBatch(channel, listing_ids)` — read several listings at once.
- `wheelhouse_rmPutPreferences(listing_id, channel, ...fields)` — single-listing write. **Top-level partial update, rule-array full replace** (see Fetch-Then-Merge below).
- `wheelhouse_rmPutPreferencesBatch(channel, listing_preferences[])` — multi-listing write, same replace semantics per listing. Returns `207` on partial failure, `424` if all fail.
- `wheelhouse_rmPutPreferenceSetting(listing_id, channel, setting, type|enabled)` — shortcut for setting `base_price_adjustment`, `seasonality_adjustment`, `last_minute_discount`, or `far_future_premium` to a CON/REC/AGG preset, or toggling `automatic_rate_posting`. Carries its own confirmation requirement in the tool description — state listing, setting, current value (fetch first if unknown), and new value before calling.
- `wheelhouse_rmPreviewPreferences(listing_id, channel, price_model?)` — non-mutating; returns recommendations as if the given preferences were applied. Use before committing any change with non-obvious downstream effects (seasonality, day-of-week, min-stay rules).
- `wheelhouse_rmCopyPreferences(listing_id, channel, copy_preferences_from, copy_custom_rates?)` — **destructive**, overwrites the target's entire preference set. Carries its own mandatory-confirmation requirement in the tool description: state source and target listings and whether custom rates are also copied, and do not call until both are explicitly confirmed. Event/season IDs are listing-scoped — after a copy, rules referencing `seasonal`/`event` IDs on the source may need remapping on the target (see Context-Events&Seasons).
- `wheelhouse_rmGetPreferencesChangelog(listing_id, channel, start_date?, end_date?)` — full history of everything recorded against the listing (not just preferences) — use to log/verify what a write actually changed, and to see custom-rate history (not exposed on the Custom Rates read endpoints themselves).

Direct RM API base URL for reference (this skill's own path is the MCP, but the underlying resource is `PUT /preferences/{listing_id}` with `channel` as a query parameter, and `PUT /preferences` with a `listing_preferences` body array for batch — see Context-Preferences-API for the direct variant).

## Rule-array shapes (verified from the live tool schema)

Every rule-array field (`minimum_stay_rules_v3`, `minimum_price_rules_v3`, `maximum_price_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`, `checkin_checkout.check_in_rules`/`check_out_rules`, `day_of_week.rules`, `last_minute_discount.rules`, `far_future_premium.rules`, `seasonality_adjustment.rules`, `long_term_discounts.weekly_rules`/`monthly_rules`/`rules[LOS-key]`) uses one polymorphic rule shape keyed by `type`. Two families:

**7-type family** — `minimum_price_rules_v3`, `maximum_price_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`, `checkin_checkout` rules, `day_of_week.rules`:
`global`, `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom`

**9-type family** — `minimum_stay_rules_v3` and `long_term_discounts` rules only, adds two minimum-stay-specific types:
all 7 above, plus `adjacency` (alias `one_sided_gap`) and `gap`

**Narrower sets** (fewer types allowed — confirm before proposing a type the field doesn't support):
- `last_minute_discount.rules` / `far_future_premium.rules`: 6 types — no `global`.
- `seasonality_adjustment.rules`: **only** `seasonal`, `event`, `monthly`.

Per-type field shape:

- `global`: `{type: "global", value}`. No `day_of_week_values`. At most one per rule set.
- `day_of_week`: `{type: "day_of_week", months?: [1-12], day_of_week_values: [7]}` (required). Index 0 = Sunday.
- `monthly`: `{type: "monthly", months: [1-12] (required), value?}` or `day_of_week_values?` (one or the other, not both). Inside `seasonality_adjustment` only, also takes `step: boolean`, `start_value`, `end_value` — see the interpolation note below.
- `time_based`: `{type: "time_based", days_before?, days_after?, months?, value?}` — at least one of `days_before`/`days_after` required. `days_before` alone = last-minute window; `days_after` alone = far-future window; both = a band (days_before ≥ days_after).
- `seasonal` / `event`: `{type: "seasonal"|"event", id (required), value?}`. `id` references a `custom_date_ranges` entry — see Context-Events&Seasons before writing either of these.
- `custom`: `{type: "custom", start_date (required), end_date (required), yearly?: boolean, value (required)}`. Fixed date range — unrelated to `custom_date_ranges`/Events&Seasons despite the similar name.
- `adjacency`/`one_sided_gap` (minimum-stay/long-term-discount only): `{type, days_adjacent (required), adjustment?, day_of_week_adjustments?}`. Negative `days_adjacent` = prior side, positive = subsequent side; on a same-date collision the negative-side rule wins.
- `gap` (minimum-stay/long-term-discount only): `{type, gap_enabled: true (required literal), days_before?, days_after?, gap_flexibility?, value?}`. Applies only to orphan gap nights; `gap_flexibility` can reduce the effective minimum stay but never below `value`.

**`day_of_week_values`/`day_of_week_adjustments` are always length 7.** A `null` entry means "falls through to the next-lower-precedence applicable rule for that day," not zero — use `0` explicitly for an actual zero value.

**`priority` is read-only everywhere.** The schema marks it explicitly: "assigned automatically by the server based on rule type; any value submitted in a request body is ignored." Never read or write it — precedence is entirely type-driven (see hierarchy table below).

**Interpolation note (verified, matches project instructions §12):** `step: false` linear interpolation (`start_value`/`end_value`) is honored **only** inside `seasonality_adjustment`. The schema description states this explicitly. Don't propose `step: false` interpolation for minimum-price monthly rules or anywhere else — it's accepted by the schema shape but not honored by the pricing engine outside seasonality.

## Rule hierarchy (priority, lowest to highest)

| Priority | Rule type(s) | Notes |
|---|---|---|
| 1 (lowest) | `global` | Whole calendar, at most one |
| 2 | `day_of_week`, `monthly` | Same level; ties broken by specificity |
| 3 | `time_based` | Narrower booking window wins ties |
| 4 | `seasonal` | References a `custom_date_ranges` entry |
| 5 | `event` | References a `custom_date_ranges` entry |
| 6 | `adjacency`/`one_sided_gap` | Minimum-stay only |
| 7 | `gap` | Minimum-stay only |
| 8 (highest, default) | `custom` | One-time (`yearly:false`) beats recurring (`yearly:true`) on tied dates |

**`apply_gap_night_rules_to_overrides`** (default `false`) inverts levels 6-7 vs. 8 for **minimum stays specifically**: `false` (default) means `custom` beats `gap`/`adjacency`; `true` means `gap`/`adjacency` beats `custom`. Check this field on the listing before asserting which rule wins — do not assume the default table order for minimum-stay precedence.

**Before writing any rule**, fetch the current rule set and check for an existing higher- or equal-precedence rule covering the same dates. Surface conflicts to the client rather than silently layering a rule that will be shadowed or that shadows something they rely on.

## Fetch-then-merge — mandatory, no exceptions

`wheelhouse_rmPutPreferences` and `wheelhouse_rmPutPreferencesBatch` are **partial-update at the top level only**. Omitting a field (e.g. not mentioning `minimum_stay_rules_v3`) leaves it unchanged. But any field holding a rule array — `minimum_price_rules_v3`, `maximum_price_rules_v3`, `minimum_stay_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`, `custom_date_ranges`, and the rule arrays nested in `checkin_checkout`/`day_of_week`/`last_minute_discount`/`far_future_premium`/`seasonality_adjustment`/`long_term_discounts` — is **completely replaced** on write. This is confirmed verbatim in the live tool description: "individual rules within an array cannot be merged or patched... any rules omitted from an array will be permanently deleted."

So: **always fetch current preferences (`wheelhouse_rmGetPreferences`) before any write that touches a rule-array field, and include every existing rule you want to keep alongside the new one.** There is no partial-array update path. Never construct a rule-array write from only the new/changed rule.

## Per-channel setting support — check before proposing, verify after writing

Not every channel (PMS/integration connection — see the lexicon reference for the channel-sense distinction) supports every setting. A setting the channel can't act on is **silently discarded, not stored — the write still returns success.**

- **Before proposing a change:** check `supported_settings` (`{checkin_checkout, min_stays, long_term_discounts, long_term_discount_type}`) on the listing object or preferences object. A `false` value means the write will be dropped even though it succeeds. This is per-account rollout too — two listings on the same channel can differ.
- **After any write** (single, batch, preview, or copy): check the response's `warnings` array. It's present (possibly empty) on every response — no null check needed. Each entry names the setting that wasn't applied and why: `not_supported_by_channel` or `partially_supported_by_channel` (only the unsupported excess was dropped). Surface this to the client whenever non-empty — never treat a `200`/`207` as confirmation everything requested actually took effect.

## Write protocol

1. **Resolve ambiguity first** against the shared lexicon reference.
2. **Fetch current preferences** for every listing being written to (`wheelhouse_rmGetPreferences`/`Batch`).
3. **Check `supported_settings`** for the setting(s) being changed.
4. **Check the rule hierarchy** for conflicts with existing rules covering the same dates/scope.
5. **Decompose multi-step intents.** A single request ("open up availability for the long weekend") often implies changes across multiple settings (e.g. minimum stay + check-in/check-out). Surface the complete plan — every setting, current value, and proposed new value — before the first write call.
6. **Use `PreviewPreferences`** before committing changes with non-obvious downstream effects (seasonality, day-of-week, min-stay rules) so the client can see the projected recommendations first.
7. **Confirm with the client** before every write, single or batch — this default has no built-in bypass in this skill. If a client explicitly asks to skip per-write confirmation for the rest of the session, that's a session-level choice the client makes explicitly; still log every action taken afterward regardless.
8. **Write**, including every rule you want to retain per the fetch-then-merge rule above.
9. **Check the `warnings` array** on the response and surface any non-empty result to the client.
10. **Log what changed** — listing(s), setting/dates, new value, previous value where retrievable (use `wheelhouse_rmGetPreferencesChangelog` if a written record is wanted).

## `price_model`

`current`/`opt_in`. Pass this through explicitly on any read or write touching recommendations or preferences rather than silently defaulting. Never switch a listing's active model version unless the client explicitly asks to.

## Listing identification

Every call needs `listing_id` **and** `channel` together, sourced from a prior `wheelhouse_rmGetListings` call — never accept a bare ID without its channel. Two valid pairings exist: the channel listing ID with its actual `channel` value, or the Wheelhouse ID with `channel: "wheelhouse"` literally. Don't mix the two forms in one call.

## See also

- **Context-Events&Seasons** — required reading before writing any `seasonal`/`event`-type rule; covers how `custom_date_ranges` IDs are created, shared across listings, and safely updated.
- **Context-CustomRates** — for one-off overrides that should win regardless of what these preference rules say.
- **`${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** — terminology ambiguity, load before interpreting any request.
- **Context-PriceLabsMigration** — if the client's vocabulary comes from PriceLabs or another pricing tool ("Customization," "Pricing Profile") rather than general RM language, translate there first.
