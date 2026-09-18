---
name: MCP-wheelhouse-mcp-general-use-guidance
description: Guides agents using the Wheelhouse Revenue Management MCP server. Use when answering portfolio pricing, pacing, occupancy, comp-set, preference, or base-rate questions via wheelhouse_rm_* tools — especially multi-listing analysis, preference writes, and rule configuration.
---

# Wheelhouse RM MCP Agent Guide

Read this before answering portfolio-level or preference-write questions. Tool schemas document individual endpoints; this guide documents **how tools combine**, **portfolio-wide patterns**, and **write safety**.

## Authentication

- MCP clients authenticate with **OAuth**. The server exchanges the token for the user's RM API key (read/write); do not send an API key yourself.

## Tool access

- The stable `/mcp` endpoint exposes `wheelhouse_*` tools directly.
- The beta `/mcp/beta` endpoint uses FastMCP Code Mode. Discover tools with `search`, inspect parameters with `get_schema`, then compose calls in `execute` via `await call_tool("wheelhouse_rm…", {…})`. Prefer paginating and aggregating inside one `execute` block so intermediate pages do not flood context.

## Portfolio-first rules

1. **Fetch the full active portfolio** — call `wheelhouse_rmGetListings` with `exclude_inactive=true` (default) and paginate until a page returns fewer items than `per_page`. Never answer portfolio questions from the first page alone.
2. **Respect rate limits** — 60 requests/minute (default). Batch when possible (`wheelhouse_rmGetPreferencesBatch`, `wheelhouse_rmPutPreferencesBatch`). On **429**, exponential backoff with jitter. On **immediate, repeatable schema/validation errors**, that is not rate limiting — do not retry blindly.
3. **Identify listings by `id` + `channel`** from `wheelhouse_rmGetListings`. Match user names against `title`, `nickname`, and `address` fields; confirm ambiguous matches. `wheelhouse_rmGetListings` returns managed listings (shared with the user by another account) alongside owned ones by default — there is no extra step or parameter needed to reach them, so never tell a user a listing is missing without having paginated the full list.
4. **Two kinds of listing ID exist — never guess between them.** `id` is the **channel's** listing ID and requires the matching `channel`; `wheelhouse_id` is the **Wheelhouse** listing ID and is passed with the literal `channel=wheelhouse`. Mixing them 404s. When a user supplies a bare ID that you cannot trace to a `wheelhouse_rmGetListings` result, resolve it rather than guessing:
    - A purely numeric ID that matches a `wheelhouse_id` in the portfolio → use it with `channel=wheelhouse`.
    - A value that matches an `id` → use it with that listing's `channel`.
    - It matches **both** an `id` and a different listing's `wheelhouse_id`, or neither → **ask the user which they mean**, naming the candidate listings by `title`/`nickname`. Do not try one form and fall back to the other on a 404; a 404 here is ambiguous and retrying hides which listing you actually touched — this matters most before a write.

    Under `channel=wheelhouse`, a 404 means "not in your portfolio" and does **not** mean the listing does not exist — inaccessible listings are deliberately indistinguishable from absent ones there. So never tell a user their listing "doesn't exist" on a 404; say it is not in the portfolio you can see, and check you paginated the full `wheelhouse_rmGetListings` result first.
5. **Multi-unit listings** (`number_of_active_units` is not null): per-date endpoints return one row per unit per date (`unit_number` ≥ 1). Metrics like `min_price_occurrence` count **unit-nights**, so multi-unit listings rank higher in raw counts — normalize by dividing by active units when ranking or comparing across listings.

## Question → tool routing

| User question | Primary tools | Notes |
|---|---|---|
| Pacing vs neighborhood comps | `rmGetListingKpis` | Use `occupancy` vs `occupancy_neighborhood` (or `_adjusted` / `_pp` / `_ratio`) for forward windows `0_7`, `0_30`, `0_60`, `0_90`. One call per listing — no batch KPI endpoint. |
| Min prices too high / owner emails | `rmGetListingKpis` | Rank by `min_price_occurrence` for `0_90`; normalize multi-unit counts. Cross-check `minimum_price_rules_v3` via `rmGetPreferences`. |
| Why were rates lower in May vs last year? | `rmGetListingKpisMonthly` | Only **15 months** of history. Requires `listing_id` + `channel`. Compare same calendar month year-over-year. |
| Overpriced dates / way too high | `rmGetListingPriceCalendar` | No portfolio-wide anomaly endpoint — pull calendars for relevant listings and compare asking price to `rmGetListingKpis` `adr` (past) or neighborhood pricing. |
| Occupancy next 30/60/90 across portfolio | `rmGetListingKpis` | Forward `occupancy` / `occupancy_adjusted` at `0_30`, `0_60`, `0_90`. Aggregate after pulling all listings. |
| Low asking rates still available (next ~2 weeks) | `rmGetListingPriceCalendar` | Filter available nights with low posted/asking price. |
| Priced above/below comp median now | `rmGetListingNeighborhoodPricing` or KPI `occupancy_neighborhood_ratio` | Neighborhood pricing gives daily percentiles; KPI ratio summarizes forward occupancy vs cluster. |
| Under/over-performing listings | `rmGetListingKpis` | Compare listing `occupancy` or `occupancy_adjusted` to `occupancy_neighborhood` or `comp_set_occupancy`. Pull **every** active listing before ranking. |
| Overpriced vs historical bookings | `rmGetListingKpis` | Compare forward `asking_rate` to past `adr` (e.g. `365_0`). Flag large positive gaps. |
| Top/bottom performers | `rmGetListingKpis` | Clarify metric (occupancy, RevPAR, revenue_score, etc.). No sort-by-KPI endpoint — compute client-side after full pull. Do **not** use Segments unless the user named one; segments are user-created, not standardized. |
| Length of stay / booking patterns | `rmGetReservations` | Use real reservation `start_date`/`end_date`. Do **not** estimate LoS from KPI booking counts. Monthly KPI LoS fields exist but reservations are preferred for stay-length analysis. |
| Nights blocked by settings (not channel) | `rmGetListingMinStayCalendar`, `rmGetPreferences` | Distinguish channel blocks from rule-driven min-stay / check-in restrictions. |
| Missing event custom rates | `rmGetListingCustomRates` | Compare festival dates to existing custom rate windows. |
| MLOS exceptions across a market | `rmGetPreferences` or `rmGetPreferencesBatch` | Compare `minimum_stay_rules_v3` and `base_min_night_stay`. Batch endpoint is more efficient for many listings. |
| Base rate recommendation / adjustment | `rmGetBasePriceRecommendation`, `rmPutPreferenceSetting` | See **Base price updates** below. |
| Hypothetical preference impact | `rmPreviewPreferences` | POST with a **request body** of preference overrides. See **Preview before write**. |
| Performance percentile / market position | `wheelhouse_rmGetMarketReport` → `wheelhouse_rmGetMarketDistribution` / `wheelhouse_rmGetMarketTimeSeries`, or `revenue_score` on KPIs | Pass `market_id` from `wheelhouse_rmGetMarketReport` (Pro listings only). Do **not** use a listing object's `market_id` alone — that often 404s. |
| How am I pacing? | `rmGetListingKpis` + `occupancy_pacing` in preferences | KPI forward occupancy plus pacing settings for context. |
| Build / search comps for a dynamic set | `wheelhouse_rmGetSetCandidates` → `wheelhouse_rmCreateSet` | **Required:** `lat`+`long`+`radius` **or** `market_ids`. Never call candidates with neither — that is a guaranteed 400. Derive `market_ids` from the user's listings or ask for a location first. |
| Bulk prefs / tags / copy | `wheelhouse_rmGetPreferencesBatch`, `wheelhouse_rmPutTags`, `wheelhouse_rmCopyPreferences` | See **Common gotchas** below. |

## KPI period keys

Rolling-window metrics use `"PAST_FUTURE"` string keys:

- **Forward-only** (e.g. `min_price_occurrence`, `occupancy_neighborhood`): `0_7`, `0_14`, `0_21`, `0_30`, `0_60`, `0_90`, `0_180`, `0_365`
- **Bidirectional** (e.g. `occupancy`, `adr`, `asking_rate`): also `7_0`, `30_0`, `365_0` for past windows
- **`revenue_score`**: non-overlapping forward windows `0_30`, `31_60`, `61_90` (scores 0–100; >100 outperforms segment)
- **`pickup`**: backward only — `7_0`, `14_0`, `30_0` (by booking creation date)

All monetary values use the response `currency`.

## Common gotchas

- **`wheelhouse_rmGetPreferencesBatch`:** always pass `listing_ids`. Channel alone returns an empty `[]`.
- **`wheelhouse_rmCopyPreferences`:** `copy_preferences_from` must be an object with `listing_id` (never a bare string ID). Include `channel` unless it can be inferred from the current session context. The nested `channel` is resolved independently of the top-level one, so the source and target listing may each be identified their own way (see portfolio-first rule 4).
- **`wheelhouse_rmGetSetAggregatedMetrics` / `wheelhouse_rmGetSegmentAggregatedMetrics` `dates`:** first-of-month calendar dates (`YYYY-MM-DD`, e.g. `2026-05-01`). Do **not** use KPI period keys like `0_30` or `0_90`.
- **Market reports:** call `wheelhouse_rmGetMarketReport` first and use `market_id` from that response. A listing object's `market_id` is not sufficient entitlement for time_series/distribution.
- **`wheelhouse_rmPutTags`:** creates `ImportedTag`s only. Despite OpenAPI saying `overwrite: true` replaces all tags, overwrite only removes other **imported** tags — UI `UserTag`s are left alone. Re-writing names that already exist as `UserTag`s can duplicate them as `ImportedTag`s.
- **`wheelhouse_rmGetSetCandidates`:** requires `lat`+`long`+`radius` **or** `market_ids` — empty calls always 400.

## Base price updates

To adopt Wheelhouse's recommended tier, use **`rmPutPreferenceSetting`** with `setting=base_price_adjustment` and `type` of `REC`, `CON`, or `AGG` — not a raw `base_price` integer write.

| Goal | Approach |
|---|---|
| Switch to recommended/conservative/aggressive preset | `rmPutPreferenceSetting` → `base_price_adjustment` with `type: REC/CON/AGG` |
| Set a specific custom base price | `rmPutPreferences` with `base_price` integer, or `base_price: null` to revert to model-driven |
| Inspect before changing | `rmGetBasePriceRecommendation` (shows `base_price_recommended`, `base_price_selected`, attribution) |

After writes, verify via `rmGetBasePriceRecommendation` or `rmGetPreferences`. Report changes using listing **title/nickname and `listing_id`**, and show before → after `base_price_selected`.

## Preview before write

`rmPreviewPreferences` accepts a **JSON request body** with hypothetical preference fields (same shape as `rmPutPreferences`). It returns price recommendations as if those preferences were applied, without saving.

Workflow for preference or rule changes:

1. `rmGetPreferences` — capture current state
2. Build the proposed payload (merge mentally; see rule-array warning below)
3. `rmPreviewPreferences` with the proposed body — review impacted dates and `base_price_recommended`
4. **Ask the user to confirm** before any `rmPutPreferences` or `rmPutPreferenceSetting` call
5. Write, then read back to verify

## Preference writes — critical safety

`rmPutPreferences` is a **partial update at the top level only**. Omitting a top-level field leaves it unchanged. But **any array field you include fully replaces that array**:

- `minimum_stay_rules_v3`, `minimum_price_rules_v3`, `maximum_price_rules_v3`, `custom_date_ranges`, etc. — sending a partial array **deletes omitted rules permanently**.

**Always:**

1. `rmGetPreferences` first
2. Start from the **full existing array**, then add/edit/remove the intended rule(s)
3. Preview when pricing impact matters
4. Confirm with the user before writing
5. Read back after write; use `rmGetPreferencesChangelog` if helpful

For adding a single event/season: merge the new `custom_date_ranges` entry and its referencing rule into the existing arrays — never send only the new rule.

### Rule type selection

| Situation | Rule type |
|---|---|
| Default for all dates | `global` (priority 1 — lowest, overridden by everything else) |
| Recurring calendar season | `seasonal` + matching `custom_date_ranges` entry |
| One-off or annual event (e.g. Mother's Day weekend) | `event` + `custom_date_ranges` (`yearly: true` for recurring) |
| Last-minute / booking-window logic | `time_based` (`days_before` / `days_after` relative to today) |
| Specific months | `monthly` |
| Weekday pattern | `day_of_week` |
| Fixed date range | `custom` (highest priority) |

**Priority order** (low → high): `global` (1) → `day_of_week`/`monthly` (2) → `time_based` (3) → `seasonal` (4) → `event` (5) → `adjacency`/`gap` (6–7, MLOS only) → `custom` (8). Higher priority wins on overlapping dates. Within `time_based`, narrower `days_before` wins.

`seasonal` and `event` rules reference `custom_date_ranges` by `id`. New entries and referencing rules can ship in one PUT — assign the `id` on the new range so the rule can reference it.

**Do not confuse** `gap_night` (pricing setting) with `gap`/`adjacency` rule types in `minimum_stay_rules_v3` (minimum-stay behavior).

## Rate limits and errors

| Signal | Meaning | Action |
|---|---|---|
| HTTP 429 | Rate limited | Exponential backoff + jitter; batch future calls |
| HTTP 409 | Concurrent write in progress | Wait and retry the same write |
| HTTP 423 | Data still generating | Brief delay, retry |
| Output validation / schema error on read | Upstream null or shape mismatch | Not retryable via backoff; try another listing to isolate, report deterministically |
| HTTP 403 on PUT | Listing authorization failed | Stop writes; confirm `listing_id` + `channel` and user access |

## Output standards

- **Portfolio assessments**: state total active listings and how many were analyzed. Never present a partial sample as the full portfolio.
- **Rankings**: show listing name, `listing_id`, channel, key metric values, and units (for multi-unit).
- **Writes**: summarize every listing changed, field changed, before/after values, and verification result.
- **Recommendations**: cite the data source (which metric, which period key, which date range).

## Anti-patterns (avoid)

- Answering "which listings underperform?" after only 6 of 46 listings
- Ranking `min_price_occurrence` without normalizing multi-unit listings
- Writing preferences without reading current state first
- Replacing a rule array with only the new rule(s)
- Setting `base_price` to the recommended integer instead of using `base_price_adjustment` preset
- Estimating length-of-stay from `bookings` KPI counts instead of `rmGetReservations`
- Using Segments as a default portfolio filter
- Retrying schema validation errors with backoff
- Skipping user confirmation before destructive preference writes
- Guessing rule precedence instead of following the priority table above
- Using a listing `market_id` for market report tools without checking `wheelhouse_rmGetMarketReport`
- Calling `wheelhouse_rmGetPreferencesBatch` without `listing_ids`
- Passing KPI window keys (`0_30`) as `dates` on set/segment aggregated metrics
- Treating `wheelhouse_rmPutTags overwrite` as a full wipe of UI `UserTag`s
