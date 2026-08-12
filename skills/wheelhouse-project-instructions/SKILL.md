---
name: wheelhouse-project-instructions
description: Shared Wheelhouse RM domain context for MCP-orchestration and direct-API skills — terminology, API conventions, Active Revenue Management workflows, rate limiting, rule hierarchy, and write-safety. Use when building or interpreting Wheelhouse skills, or when a workflow skill defers to project instructions for shared conventions.
---

# Wheelhouse Revenue Management — Project Instructions

> **Purpose:** Shared context for building **skills** (SKILL.md files and supporting references) that let Claude work with Wheelhouse — through the connected **Wheelhouse MCP**, and through the **RM API directly** where that's the better fit. Individual tool-building conversations in this project should treat this document as their shared starting context, the way project instructions normally work.
>
> **Sources, and how to resolve conflicts between them:**
> 1. **Live RM API docs** — `https://api.usewheelhouse.com/wheelhouse_rm_api`. This is the API itself and is treated as ground truth. It's in active beta and ships changes roughly weekly (check its `#tag/Changelog` section before building or editing a tool).
> 2. **Live Wheelhouse Lexicon** — `https://www.usewheelhouse.com/research-metrics` — canonical metric names/definitions.
> 3. **Live Active Revenue Management Guide** — the Foundation / Identify / Intervene / Communicate / Process chapters at `https://www.usewheelhouse.com/research/*-final` — domain workflow framing.
> 4. Prior notes and examples from earlier MCP tool-building and API troubleshooting on this project.
>
> Where sources conflict, the live API docs win for anything API-shaped (auth, parameters, schemas, rule behavior); the live lexicon wins for terminology; the live guide wins for workflow/process framing. A few open questions where even the live docs are ambiguous are flagged **⚠️ needs verification** below rather than resolved by guessing.

---

## 1. How this project is organized

Skills built here fall into two families:

- **MCP-orchestration skills** (the common case): the connected **Wheelhouse MCP** exposes roughly 70 tools that mirror the RM API's operations directly (see §4 for the name mapping). Most skills here are about *sequencing and judgment* around those existing tools — terminology mapping, rate-limit-aware batching, confirmation flows, rule-hierarchy conflict checks — not about defining new tools from scratch.
- **Direct-API skills**: for automations that run outside a chat turn (scheduled jobs, webhooks, a user's own backend), or for the rare endpoint the connected MCP doesn't expose, a skill instead documents calling the RM API directly with an `X-Integration-Api-Key`. Make the distinction explicit in each skill's description so Claude picks the right mode.

**These project instructions** hold everything that should be true across every skill: terminology, API conventions, RM workflow patterns, rate-limiting strategy, rule-hierarchy rules, write-safety rules. Individual skills shouldn't restate this — they should reference it and focus on the specific workflow.

**Individual skills** are one coherent workflow or tool family each (e.g., "daily booking review," "custom rate intervention," "portfolio segment review"). Keep each SKILL.md under ~500 lines; push large reference material (a full JSON schema, a long filter-key table) into a `references/` file and point to it from the SKILL.md body.

---

## 2. Domain Context: Active Revenue Management (5 stages)

The live guide frames RM work in five stages:

**Foundation** — Portfolio segmentation (basic bedroom-count segments up through hierarchical, multi-dimensional, and performance-driven segments), demand-pattern literacy (seasonal, day-of-week, event, booking-window), and benchmarking setup (market benchmarks vs. CompSets). It also gives an explicit **"source of truth" chain** for troubleshooting bad data across a tech stack:
- Rates & minimum length of stay → source of truth is the **RMS** (e.g., Wheelhouse)
- Availability, fees, taxes → source of truth is the **PMS**
- Reservations → source of truth is the **channel** (OTA)

When a rate looks wrong, trace RMS → PMS → Channel Manager → Channel in that order and find the first hop where values diverge. When a *reservation* looks wrong, trace the reverse direction (channel → PMS/RMS) and check fee/tax breakouts plus both the rental total and gross total.

**Identify** — Daily booking-table review; expiring/at-risk inventory monitoring; pick-up analysis and its recognizable chart **shapes** (peaks & valleys, cliffs/drop-offs, steady decline, steady incline, bookending, and combinations — each has a distinct typical cause and action); Same-Time-Last-Year (STLY) comparison; pacing charts (segment-vs-segment, YoY, and using pacing to A/B test policy changes like minimum-stay length); benchmarking (pricing-specific and performance-specific); calendar/availability review (posted rates, gap nights, blocked nights, opening more nights for sale); and periodic retrospectives.

**Intervene** — Start from written **strategic guidelines** ("mantras") per scenario (discount windows, ADR positioning, next-year risk posture, peak season, lead-time-based rules, large events, shoulder season, weekday/weekend spread, length-of-stay minimums, gap-night discounting). Apply an **Intervention Matrix**: cross Occupancy (higher/lower) against ADR (higher/lower) vs. a trusted benchmark (STLY or market/CompSet) to get a default action, then expand by lead time, portfolio composition changes, recent pacing, and events. Rate-adjustment methodology ranges from simple incremental changes (±5–10%, reassessed weekly) to listing-level or group-level pacing tables, up to point-driven scoring systems for automation candidates. The intervention toolkit isn't only rate: minimum length of stay, CTA/CTD restrictions, length-of-stay discounts, OTA markups/promotions, marketing discounts, and fees are all levers — distinguish **demand-capturing** moves (loosen restrictions/fees when the market is booking but you aren't) from **demand-generating** moves (discount/market when nobody is booking). Track every intervention: date, action, rationale, channels affected, and a short-term outcome check.

**Communicate** — Documentation habits (running daily notes, logging inbound owner/teammate requests, a periodic strategy journal), alerts/reminders for outstanding requests and interventions awaiting review, internal reporting cadences (weekly revenue report to leadership, weekly pick-up/pacing report to the RM team, monthly/quarterly market-trend report), internal meeting cadences (tactical weekly vs. strategic monthly/quarterly), and external owner communication (personalization, "simple vs. complex" report tiers, proactive check-ins on blocked dates, soliciting owner input on priority dates), plus prospective-owner/business-development support.

**Process** — A concrete cadence for the above, useful as a checklist skill in its own right:
- **Daily (mandatory):** review bookings (15–30 min) for low ADRs, far-future stays, short LOS; scan the 30–60 day calendar for gaps, stale blocks, off-market rates.
- **Weekly (2x/week, mandatory):** pace/occupancy analysis (peaks & valleys, STLY, WoW pacing); expiring-inventory management (1–4 week horizon); team tactical meeting; generate/distribute the weekly report.
- **Monthly:** market/CompSet analysis; review & update strategy documentation; longer-term (12–18 month) trend review, with special attention to far-future rates and MLOS over known events/holidays/high season; monthly strategic report.
- **Quarterly/Annual:** post-mortem after major events/seasons; review & update segmentation; annual strategy planning.

A "process checklist" or "daily RM digest" skill maps naturally onto this cadence.

---

## 3. Terminology & Lexicon

Canonical names come from the live Metrics Lexicon. Always accept user input in any common alias; always render output using the Wheelhouse canonical name, and only call out a terminology mapping explicitly when the distinction changes the answer (e.g., adjusted vs. unadjusted occupancy) — otherwise just use the right term silently.

> One term to watch closely: **"channel."** Everywhere in this document outside of API parameter names, "channel" means the OTA/booking channel (Airbnb, Vrbo, Booking.com) — the standard RM sense. The RM API's `channel` *parameter*, used for identifying listings, means something different (the PMS/integration connection) — see §4.

### Core metrics

| Canonical Name | Formula | Common aliases |
|---|---|---|
| Asking Rate | Σ Nights (Bookable) price ÷ nights | Listed price, Display rate, Nightly rate, Published rate, Rack rate |
| Asking Rate (+ Fees) | Σ (nightly price + fees) ÷ nights | Gross nightly rate, All-in price, OTA rate, Guest-facing price |
| Asking Rate (+ Estimated Fees) | Σ (nightly price + estimated fees) ÷ nights | Estimated total rate, Display rate with fees |
| Asking Rate (Available) | Σ Nights (Available) price ÷ nights | Available nightly rate, Open night rate |
| Asking Rate (Highest / Lowest) | Max / Min nightly price in a window | Peak/floor rate, Ceiling/base rate |
| Average Daily Rate (ADR) | Σ Revenue ÷ Nights (Booked) | ANR, Average booking rate |
| ADR (+ Fees) | Σ Revenue(+Fees) ÷ Nights (Booked) | Gross ADR, All-in ADR |
| Bookings | Count of unique reservations in window | Reservation count |
| Last Booked (Days) | Days since most recent booking | Booking gap |
| Lead Time | Stay start date − booked date | Booking window, Days to arrival |
| Lead Time (Average) | Mean lead time across bookings | Avg. booking window |
| Length of Stay (LOS) | Stay end − stay start | Trip length, Stay duration |
| LOS (Average / ALOS) | Mean LOS across bookings | Avg. trip length |
| Minimum Price Occurrence | Days where Asking Rate = Minimum Price | Floor hits |
| Nights (Calendar / Available / Blocked / Bookable / Booked) | See lexicon | Total/open/owner-hold/net-available/occupied nights |
| Nights (Bookable %) | Nights(Bookable) ÷ Nights(Calendar) × 100 | — |
| Occupancy | Nights(Booked) ÷ Nights(Calendar) | Occ%, Fill rate |
| Occupancy (Adjusted) | Nights(Booked) ÷ Nights(Bookable) | Net/Adjusted occupancy — excludes blocked nights |
| Occupancy (Neighborhood / Neighborhood Adjusted) | Same formulas, at neighborhood level | Comp set occ |
| Occupancy (Neighborhood % Diff) | Listing Occ − Neighborhood Occ, in pp | Occ gap vs. market |
| Occupancy (Neighborhood Ratio) | Listing Occ ÷ Neighborhood Occ | Occ index |
| Pickup (Booked Nights) | Σ new Nights(Booked) in a window | Nights sold |
| Revenue / Revenue (+Fees) / Revenue (+Fees, Taxes) | Rent-only / +fees / all-in Σ for Nights(Booked) | Net/gross/all-in revenue |
| Revenue (Available / Blocked) | Σ Asking Rate over available/blocked nights | Potential/lost revenue |
| Revenue Score | Wheelhouse system score vs. market | — |
| RevPAR | ADR × Occupancy (Revenue ÷ Nights(Calendar)) | Revenue per available night |
| RevPAR (+Fees) | ADR(+Fees) × Occupancy | Gross RevPAR |
| RevPAR (Adjusted Occupancy) | Revenue ÷ Nights(Bookable) | RevPAB, Net RevPAR |
| RevPAR (Adjusted Occupancy +Fees) | Revenue(+Fees) ÷ Nights(Bookable) | Gross RevPAB |

**Non-metric fields** in listing objects: Star Rating, Room Type, Property Type, Booking Source (channel), Cleaning Fee, Security Deposit — dimensions/filters, not computed metrics.

**Budget & STLY metrics** (Rev/Occ/ADR Budget, Rev/Occ STLY) don't appear on the live lexicon and aren't available from the API today. For budget metrics, there's no API path — point the user to the Wheelhouse UI Budgets module. For STLY, derive it manually: query `reservations` for both the current window and the equivalent prior-year window and compare directly (see §9).

### Cross-platform aliasing

Worth keeping as supplementary reference for accepting user phrasing from other tools — re-verify periodically, since this table isn't itself published anywhere live:

| External term | Source | Wheelhouse equivalent |
|---|---|---|
| Paid Occupancy % | Keydata | Occupancy (Adjusted) |
| Calendar Occupancy % | Keydata | Occupancy |
| Average Booking Window | Keydata | Lead Time (Average) |
| ALOS | Keydata/General | LOS (Average) |
| Owner Nights + Holds | Keydata | Nights (Blocked) |
| Guest Booked Revenue | Keydata | Revenue (+ Fees, Taxes) |
| Owner Lost Opportunity | Keydata | Revenue (Blocked) |
| Market/Revenue Score | AirDNA | Revenue Score |
| Dynamic Pricing Recommendation | PriceLabs/AirDNA | `price_recommendations` |
| Base Price | PriceLabs/General | `base_price` preference |
| Custom Rates / Date Override | PriceLabs/General | Custom Rates system |
| Comp Set | AirDNA/General | No direct equivalent; Neighborhood metrics or a paid **Dynamic Set** are the closest proxies |
| Cancellation Rate | Keydata | No direct equivalent — derive from `reservations` |
| RevPAB | Keydata | No direct equivalent — requires bedroom count, not exposed as a formula |

---

## 4. Connecting to Wheelhouse: MCP vs. Direct API

### Which mode to use
- **Default to the connected Wheelhouse MCP.** It's OAuth-authenticated (WorkOS AuthKit — the user signs in with their Wheelhouse account, and the MCP server resolves the RM API key server-side; the caller never sees or sends it), and mirrors the RM API operation-for-operation.
- **Use direct API** (HTTP with an `X-Integration-Api-Key` header) when: the workflow needs to run outside a live chat turn (scheduled job, webhook), the MCP doesn't expose a needed endpoint (confirm via `tool_search` — don't assume), or the user explicitly wants a code sample for their own stack.
- Never ask the user to paste an API key into chat. For direct-API skills, the key belongs in the user's own environment/config; reference it as `X-Integration-Api-Key` in code samples without requesting its value.

### MCP tool name mapping
The connected MCP's tool names mirror the RM API's OpenAPI `operationId`s (camelCase, `wheelhouse_rm` prefix) rather than a hand-designed snake_case convention. Confirm exact names/parameters via `tool_search` before use rather than guessing from the pattern — as of this writing:

| Workflow area | Representative MCP tool names |
|---|---|
| Listings | `wheelhouse_rmGetListings`, `wheelhouse_rmGetListing`, `wheelhouse_rmGetListingPricingTier`, `wheelhouse_rmGetListingRecentChanges`, `wheelhouse_rmPostListingSync` |
| KPIs | `wheelhouse_rmGetListingKpis`, `…KpisMonthly`, `…KpisQuarterly`, `…KpisYearly` |
| Recommendations | `wheelhouse_rmGetPriceRecommendations`, `wheelhouse_rmPreviewPreferences`, `wheelhouse_rmGetBasePriceRecommendation`, `wheelhouse_rmGetBasePriceHistory`, `wheelhouse_rmGetCheckinCheckout`, `wheelhouse_rmGetMinMaxPrices`, `wheelhouse_rmGetMonthlySeasonality` |
| Preferences | `wheelhouse_rmGetPreferences(Batch)`, `wheelhouse_rmPutPreferenceSetting`, `wheelhouse_rmCopyPreferences`, `wheelhouse_rmGetLongTermDiscounts`, `wheelhouse_rmGetPreferencesChangelog` |
| Custom Rates | `wheelhouse_rmGetCustomRates`, `wheelhouse_rmPutCustomRate`, `wheelhouse_rmDeleteCustomRate`, `wheelhouse_rmBulkPutCustomRates`, `wheelhouse_rmBulkDeleteCustomRates` |
| Reservations | `wheelhouse_rmGetReservations` |
| Tags/Flags | `wheelhouse_rmGetTags`, `wheelhouse_rmPutTags`, `wheelhouse_rmGetFlags` |
| Notes | `wheelhouse_rmGetNotes`, `wheelhouse_rmPostNote`, `wheelhouse_rmPutNote`, `wheelhouse_rmDeleteNote` |
| Calendar | `wheelhouse_rmGetPriceCalendar`, `wheelhouse_rmGetLastPostedPrices`, `wheelhouse_rmGetCalendarDayHistory`, `wheelhouse_rmGetFeeImpactCalendar`, `wheelhouse_rmGetMinStayCalendar` |
| Segments | `wheelhouse_rmGetSegments`, `wheelhouse_rmPostSegments`, `wheelhouse_rmPutSegment`, `wheelhouse_rmGetSegmentListings`, `wheelhouse_rmGetSegmentAggregatedMetrics` |
| Market Reports | `wheelhouse_rmGetMarketReport`, `wheelhouse_rmGetMarketTimeSeries`, `wheelhouse_rmGetMarketDistribution` |
| Neighborhood | `wheelhouse_rmGetNeighborhoodPricing`, `wheelhouse_rmGetNeighborhoodOccupancy` |
| Dynamic Sets | `wheelhouse_rmGetSets`, `wheelhouse_rmGetSet`, `wheelhouse_rmGetSetAggregatedMetrics`, `wheelhouse_rmGetSetListings`, `wheelhouse_rmGetSetAssociatedListings`, `wheelhouse_rmPutSetAssociatedListings`, `wheelhouse_rmDeleteSetAssociatedListings`, `wheelhouse_rmGetSetChangelog`, `wheelhouse_rmGetSetTimeSeries`, `wheelhouse_rmGetSetDistribution` |
| Notifications | `wheelhouse_rmGetNotifications`, `wheelhouse_rmDismissNotifications`, `wheelhouse_rmGetNotificationSettings`, `wheelhouse_rmUpdateNotificationSettings` |
| Teams | `wheelhouse_rmGetTeamMembers`, `wheelhouse_rmPostTeamMemberInvite`, `wheelhouse_rmDeleteTeamMember`, `wheelhouse_rmPostTeamMemberAutoManagedListingLevel`, `wheelhouse_rmPostTeamMemberAssignedSegments`, `wheelhouse_rmPostTeamMemberRefreshAutoManagedListings`, `wheelhouse_rmGetTeamMemberships`, `wheelhouse_rmPostTeamMembership`, `wheelhouse_rmDeleteTeamMembership` |

⚠️ **Needs verification each session:** whether the MCP exposes the two broadest write endpoints, `PUT /preferences/{listing_id}` (full preference replace) and `PUT /preferences` (batch), under some tool name — they weren't confidently identified in the current tool list (only `wheelhouse_rmPutPreferenceSetting`, which is limited to the presets `base_price_adjustment`, `seasonality_adjustment`, `last_minute_discount`, `far_future_premium`, `automatic_rate_posting`). If a skill needs to write a *new* rule into `minimum_price_rules_v3`/`minimum_stay_rules_v3`/etc., confirm via `tool_search` first; if it's genuinely unavailable via MCP, fall back to a direct-API code sample for that specific write and say so plainly.

### Cross-cutting API facts every skill needs
- **Base URL** (direct API): `https://api.usewheelhouse.com/ss_api/v1`
- **Auth:** MCP → OAuth, resolved server-side. Direct → `X-Integration-Api-Key` header.
- **Read-only keys:** allow `GET`, `HEAD`, `OPTIONS`, and non-mutating `POST` (e.g., `preview`) only; `PUT`/`DELETE`/mutating `POST` return `403`.
- **`listing_id` and `channel` are required together** for virtually every listing-scoped call — both come from `GET /listings`. Cache them as a pair, not just the ID; build this map once per session before making other listing-specific calls.
- **"Channel" means something different in the API than in RM conversation.** In the Wheelhouse API/MCP, `channel` identifies the **PMS/integration connection** a listing syncs through — it's a plumbing identifier, not a distribution channel. In everyday RM usage (and in this document's own workflow sections), "channel" almost always means the **OTA/booking channel** — Airbnb, Vrbo, Booking.com. These are genuinely different things and easy to conflate. If a user asks to "filter by channel," "see channel mix," or "compare OTA performance," that's the OTA sense — look at a listing's `channel_ids` object, a reservation's `source_name`, or the segment filter's `source` key (`"A"`/`"V"`/`"B"` for Airbnb/Vrbo/Booking.com), **not** the API's `channel` parameter. Keep this distinction explicit in tool descriptions and confirmations rather than using the bare word "channel" and letting the two senses blur.
- **Multi-unit listings:** a listing can represent multiple independently bookable units (`number_of_active_units` non-null). Per-date endpoints (`price_calendar`, `last_posted_prices`) return **one row per unit per date**, keyed by `unit_number` (single-unit listings always report `unit_number: 0`). Group by `unit_number` when aggregating, or risk double-counting or miscomputing.
- **Pagination:** `page` (1-based) or `offset` (0-based) — never both; `per_page` up to 100; stop paging when a page returns fewer than `per_page` items.
- **Rate limit:** 20 requests/min, rolling window, `429` on breach. Exponential backoff: 1s → 2s → 4s → 8s… capped at 60s, ±10–20% jitter.
- **Beta API:** response shapes may change; code defensively against unexpected/missing fields.

---

## 5. Rate Limiting & API Usage Strategy

**Portfolio scan mode** (e.g., "how's my portfolio doing?"): use paginated list/segment endpoints for an overview first; only pull per-listing detail for listings that need attention.

**Targeted mode** (a specific listing or small set named by the user): fetch exactly those.

**Scope parameter:** every tool that can operate on `listing_id` / `segment_id` / "all" should let the user pick scope explicitly, and should warn about call volume before running against a large segment or the full portfolio.

**Backoff on 429:** wait → retry → double the wait (±jitter) → cap at 60s → if still failing, tell the user plainly: *"Wheelhouse API rate limit reached. Try again shortly, or narrow the scope."*

**Batching:**
- Segment-level: fetch listing IDs via the segment endpoint first, then batch per-listing calls in groups of ~5 with short pauses.
- Bulk preference changes: use the batch endpoint, not a loop of single-listing PUTs (confirm the batch endpoint is actually exposed via MCP per §4's caveat).
- Bulk custom rates: use `bulk_custom_rates`, not a loop of single-date-range PUTs.
- Before running more than ~20 calls, tell the user: *"This will make approximately X API calls against a 20/min limit. Proceed, or narrow the scope?"*

---

## 6. Listing Settings Structure

### Two separate systems
- **Listing Settings** (Pricing Engine, Model Weights, Limits, Operations, Calendar Pacing, Configuration) drive the ongoing recommendation engine via rules that can be global, day-of-week, monthly, time-based, seasonal, event, or date-specific.
- **Custom Rates** sit on top of the recommendation for a specific date range; they don't participate in the rule hierarchy — they just override the final output for those dates. A custom rate on a holiday weekend doesn't remove a seasonal/event rule covering it, it just overrides the price shown for those dates. **Minimum price rules still apply to `adjustment`-type custom rates** (not `fixed`-type — those bypass everything except `min_min_price`).

### UI Settings Panel groups

| UI Group | UI Setting Name | API Field(s) |
|---|---|---|
| Pricing Engine | Base price | `base_price`, `base_price_adjustment` |
| Pricing Engine | Seasonality | `seasonality_adjustment` |
| Pricing Engine | Day of week | `day_of_week` |
| Pricing Engine | Last minute | `last_minute_discount` |
| Pricing Engine | Far future | `far_future_premium` |
| Pricing Engine | Gaps & Adjacencies | `gap_night` (pricing-only — distinct from the `gap`/`adjacency` **rule types** under Minimum Stays, see §7) |
| Model Weights | Demand sensitivity | `demand_sensitivity_rules` |
| Model Weights | Historical anchoring | `historical_anchoring_rules` |
| Limits | Maximum prices | `maximum_price_rules_v3` |
| Limits | Minimum prices | `minimum_price_rules_v3`, `min_min_price` (absolute floor) |
| Operations | Minimum stays | `minimum_stay_rules_v3`, `min_min_stay` (absolute floor) |
| Operations | Length of stay pricing | `long_term_discounts`, `weekly_discount`, `monthly_discount` |
| Calendar Pacing | Occupancy pacing | `occupancy_pacing` |
| Configuration | Events & Seasons | `custom_date_ranges` |

Also present at the top level: `automatic_rate_posting_enabled`, `checkin_checkout` (its own `check_in_rules`/`check_out_rules`, each following the general rule hierarchy), `apply_gap_night_rules_to_overrides`, `price_model` (`current`/`opt_in` — pass this through explicitly when reading or writing recommendations/preferences rather than assuming one model; never switch a listing's active model version without being asked to).

---

## 7. Rule Types, Hierarchy, and Placement Guidance

### Priority table

| Priority | Rule type(s) | Scope |
|---|---|---|
| 1 (lowest) | `global` | Whole calendar, at most one per rule set |
| 2 | `day_of_week`, `monthly` | Weekday pattern or specific month(s) — same level; ties broken by specificity |
| 3 | `time_based` | Booking-window relative rule (`days_before`/`days_after`); narrower window wins ties |
| 4 | `seasonal` | References a `custom_date_ranges` entry |
| 5 | `event` | References a `custom_date_ranges` entry |
| 6 | `adjacency` / `one_sided_gap` | Minimum-stay-only; adjacent blocked-night handling |
| 7 | `gap` | Minimum-stay-only; orphan-gap-night handling |
| 8 (highest, default) | `custom` | Fixed date range; one-time (`yearly:false`) beats recurring (`yearly:true`) on tied dates |

⚠️ A preference field, `apply_gap_night_rules_to_overrides` (default `false`), inverts levels 6–7 vs. 8 for **Minimum Stays specifically**: `false` (default) means `custom` beats `gap`/`adjacency` per the table above; `true` means `gap`/`adjacency` beats `custom`. Any tool writing or explaining minimum-stay precedence must check this field rather than assuming the default ordering.

There is **no `priority` field** to set — the server assigns it automatically from `type`; any submitted value is ignored. Don't read or write `priority` on any calendar rule.

**Per-day values:** a rule can carry a scalar `value` or a 7-element `day_of_week_values` (index 0 = Sunday). A `null` entry means "doesn't apply that weekday" — the engine falls through to the next-lower-precedence applicable rule for that day, not to $0.

### Which rule types apply to each setting

| Setting | Supported rule types |
|---|---|
| `last_minute_discount` / `far_future_premium` | `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom` |
| `seasonality_adjustment` | `seasonal`, `event`, `monthly` **only** |
| `day_of_week` | `global`, `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom` |
| `minimum_stay_rules_v3` | full 8-level table incl. `gap`, `adjacency` |
| `minimum_price_rules_v3` / `maximum_price_rules_v3` | `global`, `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom` (no gap/adjacency) |
| `checkin_checkout.check_in_rules` / `check_out_rules` | `global`, `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom` |
| `demand_sensitivity_rules` / `historical_anchoring_rules` | `global`, `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom` |

Before writing a rule, confirm the target setting actually supports that rule type — e.g., don't propose a `day_of_week` rule for `seasonality_adjustment`.

### Placement decision logic
- Single recurring month → `monthly`, not `custom`.
- Multiple months, shared pattern → one `monthly` rule with a `months` array.
- Recurring annual period (season) → `seasonal`, tied to an Events & Seasons entry — prefer this over a recurring `custom` with `yearly:true`.
- Named one-off or recurring event → `event`, reusing an existing Events & Seasons entry if the dates match one.
- Truly one-off date range → `custom` with `yearly:false`.
- Booking-window behavior → `time_based`, choosing `days_before` (last-minute), `days_after` (far-future), or both (a band). Stay consistent with whichever direction a listing's existing rules already use.
- No date variation → `global`.
- **Always fetch the current rule set first** and check for an existing higher- or equal-precedence rule covering the same dates before writing a new one; surface conflicts to the user rather than silently layering a rule that will be shadowed or that shadows something already relied upon.

---

## 8. Event & Season ID Resolution Protocol

**Two-layer model:** `custom_date_ranges` (Layer 1: the named date-range definition — dates, name, `yearly` flag, `id`) is per-listing; entries for the "same" event/season across listings **share an `id`** only until one of them is rewritten with a different or blank ID. Rules referencing an event/season by `id` (Layer 2, e.g., in `minimum_price_rules_v3`) are always listing-scoped.

**Rule-value-only change** (same dates/name, just a different price/stay value): resubmit the `custom_date_ranges` entry with its **existing `id` unchanged**, and update the referencing rule's value. This affects only the listing being written.

**Definition change** (dates, name, or yearly flag): **always use the blank-ID approach**, regardless of whether the ID is currently shared:
1. PUT the listing's `custom_date_ranges` array with the modified entry's `id` field **omitted** (server assigns a new one) and all other entries retained with their current IDs. A new entry and its referencing rule can be submitted in the same PUT if you manually assign an `id` to the new entry client-side — or across two PUTs, letting the server assign the ID and reading it back before the second PUT.
2. Migrate any rules that referenced the old ID to the new one, in a second PUT if needed.
3. Enumerate affected rules for the user before writing, and let them choose which to migrate.

Other listings sharing the old ID are unaffected — they keep their own copy.

**Creating a new event/season + a rule for it:** two sequential PUTs (or one, with a client-assigned `id` on the new entry) — you cannot reference an ID that doesn't exist yet in the same rule set the server hasn't seen.

**Reading:** always fetch full preferences (`GET /preferences/{listing_id}`) before interpreting any `event`/`seasonal` rule — the rule is opaque without its `custom_date_ranges` entry.

---

## 9. Revenue Management Workflow Patterns (skill catalog)

Each of these is a natural unit for its own SKILL.md. Endpoints/tools referenced use the MCP names from §4 (verify via `tool_search`).

1. **Daily Booking Review** — `GetReservations` with `date_filter_type=booked_at`, sorted by booked date, most recent first. Flag low ADR, far-future stays, short LOS on high-demand dates. Clarify revenue basis (§10) before displaying ADR.
2. **Calendar & Availability Audit** — `GetPriceCalendar` (remember `unit_number` grouping for multi-unit listings) over a target range. Surface nights at minimum price, low-asking-rate available nights, and blocked nights. Cross-reference `GetMinStayCalendar` for effective minimum stay per date.
3. **Pick-Up Analysis & STLY Pacing** — Forward-looking: `GetReservations` filtered by `booked_at` combined with `GetListingKpis`' `pickup` metric (periods 7/14/30) to establish pace; watch for the canonical **pickup shapes** (peaks & valleys, cliff/drop-off, steady decline, steady incline, bookending, or a combination) and match each to its typical cause/action per §2. STLY: since Wheelhouse's own STLY metrics aren't API-available, derive by querying `reservations` for the current window and the equivalent prior-year window and comparing booked-nights/ADR directly.
4. **Market vs. Listing Performance Analysis** — Combine `GetListingKpis` (ADR/Occ/RevPAR) with `GetNeighborhoodPricing` (median/p25/p75, bedroom-count-adjusted) and `GetNeighborhoodOccupancy` (realized + model forecast + std dev), plus `GetMarketTimeSeries`/`GetMarketDistribution` filtered by performance tier/bedroom count/property type, and — for portfolios with a paid comp set — `GetSetAggregatedMetrics`/`GetSetTimeSeries`/`GetSetDistribution`. Frame output as gaps/opportunities ("12 points above neighborhood adjusted occupancy — room to raise rates"; "currently priced at the 60th percentile of comparable listings"), not raw tables.
5. **Base Price Health Check** — `GetBasePriceRecommendation` (includes `anchor_credibility`, full attribution breakdown) vs. current `base_price`; optionally `GetBasePriceHistory` to see how the recommendation and effective price have tracked over the last 30 days. Flag significant, sustained divergence.
6. **Custom Rate Intervention (manual)** — `PutCustomRate` / `BulkPutCustomRates` for a specific listing/date range. Always: (a) resolve `listing_id`+`channel`; (b) check for existing overlapping custom rates — a new rate **replaces/splits** the old one, it doesn't stack; if the user's intent is really to combine with an existing adjustment rather than overwrite it, follow the combine-vs-replace guidance in §10 before computing what to submit; (c) pick `fixed` vs `adjustment` deliberately (fixed bypasses `minimum_price_rules_v3`, adjustment doesn't); (d) confirm before writing; (e) offer an expiring rate (`expires_at`) for anything speculative; (f) offer to log a `Note`.
7. **Data-Triggered Custom Rate Automation** — Accept a qualifying condition (metric+operator+threshold) and a target window; scan listings/segment/portfolio for matches (mind rate limits, §5); show the qualifying set and proposed action; on confirmation, apply via `BulkPutCustomRates`; log what changed.
8. **Preference Audit & Copy** — `GetPreferences`/`GetPreferencesBatch` to review; `CopyPreferences` to propagate a winning strategy (this is destructive to the target — confirm explicitly, and remember event/season IDs may need remapping post-copy since they're listing-scoped).
9. **Segment-Level Portfolio Review** — `GetSegments` → `GetSegmentListings` (or build/update a segment via `PostSegments`/`PutSegment` and its `filter_backend` query language) → `GetSegmentAggregatedMetrics` for a fast monthly rollup before drilling into per-listing detail. Mind rate limits on large segments (§5).
10. **Performance Communication / Owner Reporting** — Combine KPIs, reservations, recommendations, and neighborhood/market context into plain-language summaries ("earned $4,200 in February at 68% adjusted occupancy vs. 61% for the neighborhood"). Offer both a "simple" and a "complex" tier per the Communicate chapter's guidance, and always state the revenue basis used.
11. **Decision Logging & Notes** — After any preference/rate change, offer to `PostNote` capturing reasoning, especially for owner-requested changes, speculative event rates, or anything the user wants flagged for future review (`remind_by`/`repeat_by`). Good default categories: the preference group the change touched (e.g. `base_price`, `minimum_stays`).
12. **Rate/Reservation Discrepancy Troubleshooting** — For a wrong-looking **rate**: trace RMS (Wheelhouse) → PMS → Channel Manager → Channel in order, comparing values at each hop, and report the first hop where they diverge. For a wrong-looking **reservation**: trace the reverse direction (channel → PMS/RMS), specifically comparing fee/tax breakouts and both the rental total and gross total, since fees are the most common source of cross-system drift.
13. **Intervention Matrix / Strategic Guidelines Tool** — Given a listing/segment's Occupancy and ADR vs. a chosen benchmark (STLY or market/CompSet), return the standard quadrant read (Occ↑ADR↓ → increase rate; Occ↑ADR↑ → increase rate, likely event-driven; Occ↓ADR↑ → decrease rate; Occ↓ADR↓ → decrease rate + investigate non-price factors), then let the user layer lead-time, portfolio-composition, recent-pacing, or event-specific overrides on top before recommending an action.
14. **RM Cadence / Daily Digest** — A checklist-style skill that walks the Process-chapter cadence (§2) and, for whichever cadence the user asks about, runs the corresponding checks from items 1–11 above and reports findings against that checklist.

---

## 10. Tool Design Guidelines

### Input design
- Treat `listing_id` **and** `channel` as a pair, always sourced from a prior `GetListings` call — never accept a bare ID without a channel unless the tool itself is `GetListings`.
- ISO 8601 dates (`YYYY-MM-DD`); validate `start_date < end_date`; respect each endpoint's max window (3 years for calendar-family endpoints; 1 year forward / 3 years back for market/set time-series; 180 days for `calendar_day_history`).
- Bulk operations take an array of listing IDs (with their channels).
- Expose `page`/`per_page`/`offset` on list endpoints; default `per_page: 50`.
- **Reservation queries:** always surface `date_filter_type` (`stay_date` vs. `booked_at`) — a daily booking review needs `booked_at`; a forward occupancy view needs `stay_date`.
- **Revenue basis:** any tool touching revenue/ADR/RevPAR needs an explicit `revenue_basis` of `rent` / `rent_and_fees` / `all_in` (mapping to Revenue / Revenue(+Fees) / Revenue(+Fees,Taxes)). Default to `rent` and state the default in output; ask or state the assumption whenever the user says "revenue" unqualified.
- **`price_model`:** when reading or writing recommendations/preferences, pass `price_model` through explicitly rather than silently defaulting.

### Output design
- Surface the most relevant fields; don't just dump raw JSON.
- Always render money with the response's own `currency` field — never assume USD; segment/set aggregates without a natural currency default to the most common market currency (falling back to USD).
- Sort calendar/reservation output chronologically by stay date.
- When returning base-price recommendations, always include the attribution breakdown and `anchor_credibility` so the user understands *why*, not just *what*.
- On `401/403/404/409/422/423/429`, translate to a clear human message (see §11) — don't just surface the raw status code.
- Group multi-unit-listing per-date output by `unit_number`.

### Write operations
- **Confirm before every write**, single-listing or bulk, unless the user has explicitly opted out for the session — and even then, log the action afterward.
- **Fetch-then-merge, always**, for any endpoint that replaces a rule array wholesale. Every rule-array preference field (`minimum_price_rules_v3`, `maximum_price_rules_v3`, `minimum_stay_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`, `custom_date_ranges`, etc.) is fully replaced, not merged, on a PUT — omitting an existing rule from the array permanently deletes it. Always fetch current preferences first and include every rule you want to keep.
- **Combining vs. replacing an adjustment value is a judgment call — ask, don't assume.** The API itself never compounds: a new custom `adjustment`-type rate, or a new value for `base_price_adjustment`/`seasonality_adjustment`/`last_minute_discount`/`far_future_premium`, simply replaces whatever was there. So "bump the existing +10% up by another 10%" isn't something a single write does automatically — it has to be computed and submitted as one combined value. Most RMs, most of the time, want the new instruction to combine with what's already there rather than wipe it out, but that's not universal — some genuinely want a clean replace. Before writing: fetch the current value, tell the user what it is, and confirm whether they want to (a) **replace** it outright, or (b) **combine** it with the new instruction — and if combining, confirm whether they mean additive stacking (10% + 10% = 20%) or multiplicative/compounding stacking (1.10 × 1.10 = 1.21, i.e. +21%), since these give different answers. Show the resulting combined value before writing it.
- **Decompose multi-step intents before executing anything.** A single user request ("open up availability for the long weekend") often implies changes across multiple settings (Minimum Stay + Check-in/Check-out, say) — surface the complete plan, including current values, and get one confirmation for the whole set before the first API call.
- **Use preview** (`PreviewPreferences`) before committing preference changes with non-obvious downstream effects (seasonality, day-of-week, min-stay rules).
- **Log what changed** after every write: listing(s), setting/dates, new value, and previous value where retrievable.
- **Respect read-only keys / OAuth scopes** — a clean 403 message beats a stack trace: *"Your Wheelhouse connection is read-only (or lacks write access). To make changes, [reconnect with write access / use a read-write API key from Account → API Key]."*

---

## 11. Error Handling Reference

| Status | Meaning | Response |
|---|---|---|
| 401 | Auth failed | "Authentication failed — check your Wheelhouse connection/API key." |
| 402 | Feature not on plan (e.g. `calendar_day_history` needs Historical Price Changes) | "This feature isn't available on the current plan." |
| 403 | Not authorized for this listing, read-only key, or read-only OAuth scope | "Access denied — either this listing isn't in your portfolio, or your access is read-only." |
| 404 | Not found | "Not found — verify the listing/segment/set/note ID." |
| 409 | Concurrent update in progress | "A conflicting update is already in progress for this resource — retry shortly." |
| 422 | Validation failure (e.g., listing not covered by a Wheelhouse market, missing required param) | Surface the specific validation issue. |
| 423 | Resource locked / not yet ready (e.g., recommendations still generating, preferences not yet initialized, sync debounce window) | "Still processing — retry in a moment." |
| 424 | All items in a bulk operation failed | Surface per-item errors from the response body. |
| 207 | Partial success in a bulk operation | Report which succeeded and which failed. |
| 429 | Rate limit | Apply exponential backoff (§5); if exhausted, tell the user plainly. |
| 5xx | Server error | "Wheelhouse returned a server error — try again shortly." |

---

## 12. Important Caveats to Surface to Users

- **Beta API** — schemas may change; code defensively.
- **Currency** — always use the response's `currency`; never hardcode USD.
- **Pricing is probabilistic** — recommendations are model output, not guarantees; `anchor_credibility` reflects data-quality confidence.
- **Adjusted occupancy is usually the more meaningful metric** for evaluating pricing strategy (excludes blocked nights) — be explicit about which occupancy flavor you're presenting.
- **No `priority` field** — don't read or write it; hierarchy is type-driven only (§7).
- **Minimum-price monthly rules don't support interpolation** — `step:false` (`start_value`/`end_value`) is accepted by the schema but not honored by the pricing engine for minimum price rules; always use `step:true`.
- **`min_min_price` is integer-only** despite being typed `number` in the schema.
- **Rule-array PUTs fully replace, never merge** — always fetch-then-merge.
- **Custom rates don't stack** — a new rate on overlapping dates replaces/splits the old one; combining with an existing adjustment requires fetching it, confirming with the user whether they mean additive or multiplicative stacking, computing the combined multiplier, and submitting that single value (§10).
- **`adjustment` (write) vs. `adjusted` (read)** — the custom-rate type name changes tense between write and read paths; reconcile explicitly when comparing.
- **Multi-unit listings** return one calendar row per unit per date — group by `unit_number`.
- **`apply_gap_night_rules_to_overrides`** flips minimum-stay rule precedence between `custom` and `gap`/`adjacency` — check it before asserting which rule wins (§7).
- **Manual sync (`PostListingSync`)** is Pro-plan only, rate-limited per day, and debounced 60 seconds between requests for the same listing.

---

## 13. Key Learnings & Verified Constraints

- Terminology mapping lives in project instructions, resolved silently — never a standalone tool call.
- Keep skills separate at human-judgment boundaries (e.g., pacing analysis vs. rate posting); combine tools/steps only when data is always interpreted together.
- Read-only tools/workflows first; introduce writes only with the confirm/fetch-merge/log pattern established above.
- Every write requires confirmation; multi-step writes need the full plan surfaced before any call executes.
- The rule-priority table in §7 has one nuance to verify with Wheelhouse before shipping a Minimum-Stay-rule-writing tool: the interaction with `apply_gap_night_rules_to_overrides`.
- Event/season `custom_date_ranges` IDs are shared across listings only until rewritten with a blank/new ID; deletions and rule-value updates are listing-scoped.
- `listing_id` alone is never sufficient — pair with `channel` from `GetListings`.
- Every rule-array preference field is fully replaced on PUT — fetch-then-merge universally, not just for `custom_date_ranges`.
- Segments are writable (`POST`/`PUT`) with a documented `filter_backend` query language, not read-only.
- KPIs are split across four endpoints by time grain (rolling/monthly/quarterly/yearly) — there's no single "the KPI endpoint."
- `price_model` (`current`/`opt_in`) is a first-class field on recommendations and preferences.

---

## 14. Building Skills From This Document

When a follow-on conversation in this project builds an actual skill:

1. Reference §4's endpoint↔MCP-tool mapping to confirm the correct tool and its live parameters via `tool_search` — this document gives direction, not a frozen contract.
2. Pull the relevant terminology aliases from §3 into the skill's parameter docs/descriptions.
3. If the skill touches Pricing Engine/Limits/Operations/Calendar Pacing/Configuration settings, use the UI group and setting names from §6 consistently in all output and confirmations.
4. If the skill reads or writes `event`/`seasonal` rule types, or accepts date ranges that might intersect existing rules, follow §7–§8 exactly, including the hierarchy-conflict check and the blank-ID protocol.
5. If the skill touches revenue/ADR/RevPAR, implement the `revenue_basis` convention from §10.
6. Follow the Write Operations rules in §10 without exception: confirm, fetch-then-merge, decompose multi-step intents, preview where available, log afterward.
7. Follow §5 for any workflow that could touch more than a handful of listings.
8. Check §12–§13 for any confirmed constraint relevant to the endpoints in play — especially the PUT-replace semantics, the gap/custom precedence toggle, and multi-unit `unit_number` grouping.
9. Keep the SKILL.md itself under ~500 lines; push large reference material (a full JSON schema, a long filter-key table) into a `references/` file and point to it from the SKILL.md body.
10. Write the skill's `description` to name the RM workflow context plainly (which stage of Foundation/Identify/Intervene/Communicate/Process it serves, and when a revenue manager would reach for it) so it triggers reliably.
11. Before finalizing, re-check the live RM API docs changelog (`#tag/Changelog`) for anything newer than this document — the API has shipped new endpoints roughly weekly recently.
