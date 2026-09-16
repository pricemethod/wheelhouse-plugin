---
name: Context-Preferences-API
description: Use when a Wheelhouse client wants to change pricing-engine or rule-hierarchy settings via a script calling the RM API directly (X-Integration-Api-Key), outside a live chat turn -- e.g. a scheduled job, or their own backend. Covers the same settings as Context-Preferences (base price, seasonality, day-of-week, min/max price, min stay, demand sensitivity, historical anchoring, check-in/check-out, long-term discounts, occupancy pacing) but for unattended/scripted writes. Always dry-run by default: fetches current state, computes the change, and prints a diff -- an actual write only happens with an explicit --apply flag the client sets themselves after reviewing the diff. Trigger on "write a script to update preferences," "automate a preference change," "set this via the API key," or any preferences write that needs to run without Claude in the loop. Use Context-Preferences instead for an interactive chat-turn change via the connected MCP.
---

# Context-Preferences-API (direct RM API)

Guidance for scripts that write listing preferences directly against the RM API with an `X-Integration-Api-Key`, outside a live chat turn. This is the unattended sibling of Context-Preferences — same settings, same rule-hierarchy and fetch-then-merge facts, different safety model because there's no one to confirm a write in real time. The settings table, rule-array shapes, rule hierarchy, and `supported_settings`/`warnings` behavior are reproduced in full below, not just cross-referenced — a session generating or debugging a script may never open the sibling MCP skill, and getting any of these wrong produces a rule that's silently shadowed, a silently dropped setting, or a silently deleted rule array, none of which a script can catch on its own unless this content is built in.

**Before generating or running any script, check `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** for terminology ambiguity in the client's request — the same risk applies whether the write happens in a chat turn or a script.

## Why this isn't just Context-Preferences with a different auth header

Context-Preferences' safety model is "confirm before every write, in the conversation, right now." A script has no conversation and no "right now" — it runs on a schedule or from the client's own backend, potentially while no one is watching. Silently replicating the MCP skill's write behavior in unattended form would mean live preference changes happening with nobody able to catch a mistake before it posts. That's exactly the risk project instructions §10's confirm-before-write pattern exists to prevent, and a script can't ask a question and wait for an answer.

**The replacement: dry-run by default, explicit `--apply` to write.** Every script this skill produces:

1. Fetches current preferences for the target listing(s).
2. Computes the proposed new state (including the fetch-then-merge rule-array assembly — see below).
3. Prints a clear diff: setting name, current value, proposed value, per listing.
4. **Stops there** unless invoked with `--apply`.
5. Only with `--apply` does it perform the actual `PUT`, and even then it re-prints what it's about to write immediately before the request.

No unattended run of a script built from this skill ever writes without the client themselves having set `--apply` — which means a client wiring this into a scheduled job is explicitly opting into unattended writes for whatever the script's own logic decides to change, and should be told that plainly when the script is handed over.

## Base URL, auth, endpoints (verified against the live RM API docs)

- **Base URL:** `https://api.usewheelhouse.com/ss_api/v1`
- **Auth header:** `X-Integration-Api-Key: <key>`. The key belongs in the client's own environment/config — never ask them to paste it into chat, and never hardcode it in a generated script. Reference it as an environment variable (e.g. `WHEELHOUSE_RM_API_KEY`) in every script.
- **Read-only keys:** allow `GET`/`HEAD`/`OPTIONS` and non-mutating `POST` (preview) only. `PUT`/`DELETE` return `403`. If a script hits `403` on the actual write step, tell the client plainly: their key may be read-only, and point them to Account → API Key in the Wheelhouse app to check or generate a read-write key.
- **Single-listing write:** `PUT /preferences/{listing_id}?channel={channel}`
- **Batch write:** `PUT /preferences?channel={channel}`, body `{"listing_preferences": [{listing_id, ...fields}, ...]}`
- **Preview (non-mutating, safe to call even without `--apply`):** `POST /preferences/{listing_id}/preview?channel={channel}`
- **Read:** `GET /preferences/{listing_id}?channel={channel}` (single), and the batch-read shape mirrors the MCP's `GetPreferencesBatch`.

Auth, transport, and the confirmation-replacement mechanism (dry-run/`--apply`) are the only things that actually differ from Context-Preferences. Everything else below — listing identification, the settings table, rule-array shapes, the rule hierarchy, and `supported_settings`/`warnings` — is identical to that skill and reproduced here in full rather than cross-referenced.

## Listing identification (identical to Context-Preferences, reproduced here)

Every call needs `listing_id` **and** `channel` together, sourced from a prior `GET /listings` call — never accept a bare ID without its channel. Two valid pairings: the channel listing ID with its actual `channel` value, or the Wheelhouse ID with `channel=wheelhouse` literally. Don't mix the two forms in one call — a Wheelhouse ID sent without `channel=wheelhouse`, or a channel listing ID sent with it, returns `404`.

## Settings this skill covers (identical to Context-Preferences, reproduced here)

| UI Group | Setting | API field(s) |
|---|---|---|
| Pricing Engine | Base price | `base_price`, `base_price_adjustment` |
| Pricing Engine | Seasonality | `seasonality_adjustment` |
| Pricing Engine | Day of week | `day_of_week` |
| Pricing Engine | Last minute | `last_minute_discount` |
| Pricing Engine | Far future | `far_future_premium` |
| Pricing Engine | Gaps & Adjacencies (pricing) | `gap_night` — pricing-only, distinct from the `gap`/`adjacency` rule *types* under Minimum Stays |
| Model Weights | Demand sensitivity | `demand_sensitivity_rules` |
| Model Weights | Historical anchoring | `historical_anchoring_rules` |
| Limits | Maximum prices | `maximum_price_rules_v3` |
| Limits | Minimum prices | `minimum_price_rules_v3`, `min_min_price` (absolute floor) |
| Operations | Minimum stays | `minimum_stay_rules_v3`, `min_min_stay` (absolute floor), `min_stays_enabled` |
| Operations | Length of stay pricing | `long_term_discounts`, `weekly_discount`, `monthly_discount` |
| Calendar Pacing | Occupancy pacing | `occupancy_pacing` |
| Configuration | Events & Seasons | `custom_date_ranges` — see Context-Events&Seasons-API before writing here |
| (top-level) | Check-in/check-out | `checkin_checkout` (`check_in_rules`, `check_out_rules`) |
| (top-level) | Automatic rate posting | `automatic_rate_posting_enabled` |
| (top-level) | Price model | `price_model` — pass through explicitly, never switch a listing's active model unless the client asks |

## Rule-array shapes (identical to Context-Preferences, reproduced here)

Every rule-array field uses one polymorphic rule shape keyed by `type`. Two type families:

- **7-type family** (`minimum_price_rules_v3`, `maximum_price_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`, `checkin_checkout` rules, `day_of_week.rules`): `global`, `time_based`, `seasonal`, `event`, `monthly`, `day_of_week`, `custom`.
- **9-type family** (`minimum_stay_rules_v3` and `long_term_discounts` rules only): all 7 above, plus `adjacency` (alias `one_sided_gap`) and `gap`.
- **Narrower sets** — check before generating a rule of a type the field doesn't support: `last_minute_discount.rules`/`far_future_premium.rules` allow 6 types (no `global`); `seasonality_adjustment.rules` allows **only** `seasonal`, `event`, `monthly`.

Per-type shape a script must build correctly:

- `global`: `{type: "global", value}`. At most one per rule set.
- `day_of_week`: `{type: "day_of_week", months?: [1-12], day_of_week_values: [7]}` (index 0 = Sunday).
- `monthly`: `{type: "monthly", months: [1-12] (required), value?}` or `day_of_week_values?` (not both). Inside `seasonality_adjustment` only, also takes `step: boolean`, `start_value`, `end_value` — `step: false` interpolation is honored **only** here, despite being schema-legal on other rule-array fields too.
- `time_based`: `{type: "time_based", days_before?, days_after?, months?, value?}` — at least one of `days_before`/`days_after` required. `days_before` alone = last-minute; `days_after` alone = far-future; both = a band.
- `seasonal`/`event`: `{type: "seasonal"|"event", id (required), value?}` — `id` references a `custom_date_ranges` entry; get this from Context-Events&Seasons-API before generating either.
- `custom`: `{type: "custom", start_date (required), end_date (required), yearly?: boolean, value (required)}` — unrelated to `custom_date_ranges` despite the similar name.
- `adjacency`/`one_sided_gap` (minimum-stay/long-term-discount only): `{type, days_adjacent (required), adjustment?, day_of_week_adjustments?}`. Negative = prior side, positive = subsequent side; negative wins a same-date collision.
- `gap` (minimum-stay/long-term-discount only): `{type, gap_enabled: true (required literal), days_before?, days_after?, gap_flexibility?, value?}`. Orphan gap nights only.

`day_of_week_values`/`day_of_week_adjustments` are always length 7; a `null` entry falls through to the next-lower-precedence rule for that day, not zero. **`priority` is read-only everywhere** — never generate or set it; the server assigns it from `type` and ignores any submitted value.

## Rule hierarchy (identical to Context-Preferences, reproduced here — get this wrong and a script writes a rule that's silently shadowed or silently shadows something the client relies on)

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

**`apply_gap_night_rules_to_overrides`** (default `false`) inverts levels 6-7 vs. 8 for **minimum stays specifically**: `false` means `custom` beats `gap`/`adjacency`; `true` means the reverse. A script must read this field off the fetched listing before asserting which rule wins in a dry-run diff — never assume the default table order for minimum-stay precedence.

**Before generating any write, fetch the current rule set and check for an existing higher- or equal-precedence rule covering the same dates.** Surface conflicts in the dry-run diff rather than silently emitting a rule that will be shadowed or that shadows something already in place.

## `supported_settings` and `warnings` (identical to Context-Preferences, reproduced here)

Not every channel (PMS/integration connection) supports every setting. A setting the channel can't act on is **silently discarded on write — the request still returns success.**

- **Before generating a write:** check `supported_settings` (`{checkin_checkout, min_stays, long_term_discounts, long_term_discount_type}`) on the fetched listing/preferences object. A `false` value means the write would be dropped even though it succeeds — the dry-run diff must flag this explicitly for any in-scope setting rather than proceeding silently.
- **After any real write:** check the response's `warnings` array (present, possibly empty, on every response — no null check needed). Each entry names the setting that wasn't applied and why (`not_supported_by_channel` or `partially_supported_by_channel`). Print this and treat a non-empty result as a partial-failure condition worth a non-zero exit or an explicit log flag, not something a `200` status silently absorbs.

## Rate limiting (script-specific concerns) — read the ceiling live, never hardcode it

The request-rate ceiling has already changed once (an earlier 20/min raised to the current 60/min), and Wheelhouse is evaluating adding a **token-level** limit alongside or instead of the request-count one. This section is deliberately written so the *mechanism* stays correct regardless of what the number is or how many dimensions it has — a script (or this skill) that bakes in "60/min" as a fact keeps working right up until Wheelhouse changes it again, and then fails silently: under-throttling with no error, or over-cautiously backing off for no reason.

- **Never hardcode a specific requests-per-minute number** into a script's pacing logic or its printed warnings. Read `X-RateLimit-Limit` off the most recent response and use *that* live value for both pacing decisions and any user-facing message ("this would make approximately N calls against a current limit of **M**/min") — never print a fixed number a script author typed in once.
- **Read whichever rate-limit-shaped headers are actually present, not just the three named here.** As of this writing, every response — not just `429`s — carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (Unix timestamp); a `429` additionally carries `Retry-After`. A script iterating over many listings should check `X-RateLimit-Remaining` and pace itself proactively rather than waiting for a `429`. If a token-level dimension ships, expect it as *additional* headers (an unconfirmed but plausible shape: something like `X-RateLimit-Tokens-Limit`/`X-RateLimit-Tokens-Remaining`), not a replacement for the request-count ones — parse known header names defensively (a missing header just skips that check, never a crash), and log any `X-RateLimit-*`-shaped header the script doesn't recognize, so a new dimension shows up as a visible log line the next time this skill or its scripts get revisited, instead of a silent gap.
- **On `429`:** prefer the `Retry-After` header (the server's actual reset time) over a computed backoff delay whenever it's present. Fall back to exponential backoff (1s → 2s → 4s → ... capped at 60s, ±10-20% jitter — this 60-second cap is an unrelated, arbitrary backoff convention, not the same "60" as the request-per-minute ceiling above) only when `Retry-After` is absent.
- **Batching:** for more than a handful of listings, use the batch endpoint (`PUT /preferences`) rather than looping single-listing PUTs. Before a large batch's *projected* apply step, read the current `X-RateLimit-Limit` (already available from a prior `GET` made during the dry-run's fetch step) and warn the user in terms of that live number, never a string baked into the script: "this would make approximately N API calls against a current limit of M/min."
- **If a token-level limit ships**, treat it as an additional constraint to satisfy, not a reason to stop watching the request-count one — a script may need to pace against both at once. There's nothing to build against it yet; the actionable step today is simply not hardcoding today's numbers anywhere in a script or its output.

## Fetch-then-merge in script form

Same rule as Context-Preferences: any rule-array field (`minimum_price_rules_v3`, `maximum_price_rules_v3`, `minimum_stay_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`, `custom_date_ranges`, and the arrays nested in `checkin_checkout`/`day_of_week`/`last_minute_discount`/`far_future_premium`/`seasonality_adjustment`/`long_term_discounts`) is **fully replaced** on `PUT`, never merged server-side. A script must:

1. `GET` current preferences.
2. Build the new array in memory: existing rules the client wants to keep, plus the new/changed rule(s), minus any the client explicitly wants removed.
3. Diff *that assembled array* against the current one when printing the dry-run output — a client reviewing the diff needs to see "rule X unchanged, rule Y added, rule Z would be dropped if you don't keep it," not just "array replaced."
4. Never assemble a rule-array write from only the new rule — this is the single most common way an unattended script silently deletes a client's existing rules, and it's worse here than in the interactive skill because there's no confirmation step to catch it before it posts.

## Custom_date_ranges / seasonal / event rules

If the script's change touches a `seasonal`/`event`-type rule or the `custom_date_ranges` array itself, defer to Context-Events&Seasons-API for the ID-resolution protocol (blank-ID-on-definition-change vs. reuse-ID-on-value-only-change) before generating the write. Getting this wrong in an unattended script is worse than in a chat turn — there's no one to catch a newly-forked ID silently orphaning a rule that used to be shared across listings.

## Script structure (recommended shape)

```
usage: preferences_update.py [--apply] [--listing LISTING_ID] [--channel CHANNEL] [--config path/to/change.json]
```

- `--config` (or equivalent) describes the intended change declaratively — which listing(s), which setting(s), which rule(s) to add/modify/remove — rather than hardcoding the change in the script body. This keeps the dry-run diff meaningful across repeated runs and makes the change auditable/reviewable before `--apply` as a file, not just console output.
- Default (no `--apply`): fetch, compute, print diff, exit 0. Never touch the network with a mutating call.
- `--apply`: repeat the fetch (state may have changed since an earlier dry-run — never reuse a stale fetch across a dry-run/apply pair run at different times), recompute the diff, print it, then perform the write(s).
- Exit non-zero and print the specific problem on: `403` (read-only key), a `supported_settings: false` for a setting in scope, or a `warnings` array entry after write — don't silently succeed while a setting was actually dropped by the channel.
- Log every applied write (listing, setting, previous value, new value, timestamp) to a file beside the script's output, not just stdout, so there's a record for a scheduled/unattended run nobody watched live.

## Running from a scheduled/unattended task

If this script is wired into a scheduled task and depends on a mounted local directory (a `--config` file, an API-key file, an output/log location), the mount does not carry over between scheduled runs — each fresh run needs to re-mount that directory as its first step via `request_cowork_directory` before touching anything in it, per project instructions §14. Because this skill is write-capable: **if the mount step fails or the expected file isn't found, the script must stop and report that plainly rather than proceed** — a failed mount is not a safe condition to guess past when the run is about to make real writes to Wheelhouse. Never let a missing `--config` silently fall through to some default "change nothing" behavior that looks like success; fail loudly.

## See also

- **Context-Preferences** — the interactive MCP sibling; same settings table, rule shapes, and hierarchy table, reproduced above for the scripted case, with the full interactive write protocol and rationale there.
- **Context-Events&Seasons-API** — required before writing any `seasonal`/`event` rule type from a script.
- **Context-CustomRates-API** — for one-off date-range overrides instead of engine-level rules.
- **`${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** — terminology ambiguity, load before generating any script from a client request.
