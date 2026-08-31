---
name: MCP-custom-rate-attribution
description: Fast, single-listing check of whether Custom Rates set in the last 30 days actually got booked — the simple, custom-rates-only sibling to price-change-attribution. Trigger for "did that custom rate get booked," "check if my custom rate led to bookings," "did the rate I set on [listing] work," "did Zachary's rate change book," or any quick post-hoc check specifically about Custom Rates (not base price, seasonality, monthly, day-of-week, or global rules — those go through price-change-attribution instead). Fixed 30-day lookback, one listing at a time, reports hits only — no no-impact table, no pace-trend bucket. Use price-change-attribution instead when the user wants broader rule-type coverage, a configurable 7-/30-day window, or wants to see the misses too. Serves the Identify stage of Active Revenue Management.
---

# Custom Rate Attribution (Simple)

Checks whether Custom Rates added on a single listing in the last 30 days correlate with bookings that followed. This is the narrow, custom-rates-only sibling of `price-change-attribution` — see the project instructions for shared conventions (terminology, `listing_id`+`channel` pairing, rate limiting, revenue basis). Read that skill's own SKILL.md if the user's request turns out to need the broader rule-type coverage, a configurable lookback, or a no-impact breakdown — this skill deliberately doesn't do those things.

## When to use this skill

- "Did the custom rate I set on the Luzianne get booked?"
- "Check if Zachary's rate change on [listing] actually worked"
- "Any bookings against the custom rates I set last week?"

Not for: base price / seasonality / monthly / day-of-week / global rule changes (use `price-change-attribution`), making a new rate decision (Custom Rate Intervention workflow), or portfolio-wide scans (this is single-listing only).

## Inputs

| Param | Value | Notes |
|---|---|---|
| `listing_id` + `channel` | — | Required pair, resolved via `GetListings` if not already known this session |
| `revenue_basis` | `rent` (default) | Per project convention — state the default in output |

Lookback is fixed at 30 days — not configurable. If the user wants 7 days or a different rule type, hand off to `price-change-attribution`.

## Workflow

### Step 1 — Resolve the listing

Confirm `listing_id`+`channel` via `GetListings` if not already cached this session.

### Step 2 — Pull the changelog

Call `wheelhouse_rmGetPreferencesChangelog` with no date params — its defaults (30 days back, tomorrow forward) are exactly the fixed window this skill uses.

Keep only events where `event == "Custom rates"`. Drop everything else (`Settings changed`, `Prices posted`, `Calendar synced`) — this skill doesn't look at other rule types. `source == "Wheelhouse"` never appears on a `Custom rates` event in practice, but drop it too if seen, for consistency with the parent skill's convention.

### Step 3 — Parse each event into per-range actions

Each event's `msg` is HTML, `<br>`-separated. Split on `<br>`. Each line matches one of:

- `Fixed rate added for {start} - {end} with {values}` — type `fixed`, dollar values
- `Automated rate added for {start} - {end} with {values}` — type `adjustment`, percentage values (the changelog calls it "Automated rate"; the API field is `adjustment` — same reconcile-terminology caveat as elsewhere in this project)
- `Fixed rate removed for {start} - {end} with {values}` / `Automated rate removed for ...`
- `Automated rate split off for {start} - {end} with {values} (Originally created by {name})` — treat identically to "removed" for this skill's purposes

Dates are `MMM DD, YY` (e.g. `Aug 14, 26` → `2026-08-14`). Keep the `{values}` clause as-is for display — no need to parse it down to individual weekdays, since only the date range matters for the join.

**Group by exact `(start, end)` pair.** Within one event, if both a `removed` and an `added` line share the same exact `(start, end)`, that event's **net action** for that range is `SET` (to the added line's value), timestamped at the event's time. If a range has only a `removed`/`split off` line in that event with no matching `added` line in the same event, the net action is `CLEARED`.

A single event commonly reshapes one range into several narrower ones (e.g. a 10-day block split into three sub-ranges with different values) — each resulting `(start, end)` is its own independent range going forward, not a continuation of the original.

### Step 4 — Resolve each range's effective state across the window

For each distinct `(start, end)` pair touched anywhere in the window, sort its net actions chronologically and take the **last** one:

- **Last action is `SET`** → this is an effective change. `added_at` = that action's timestamp, `value` = its value, `edits_in_window` = count of `SET` actions for this range in the window, `deleted_at` = none (attribution window stays open through now).
- **Last action is `CLEARED`**, and there is an earlier `SET` for this same range within the window → still an effective change, but now **bounded**: `added_at` = the last `SET`'s timestamp, `value` = that `SET`'s value, `deleted_at` = the clearing timestamp. The attribution window becomes `[added_at, deleted_at)` instead of open-ended.
- **Last action is `CLEARED`** with no `SET` for this range anywhere in the window (i.e. the range existed before the 30-day lookback and was only removed within it) → drop it. Nothing was actually *added* in-window, so there's no change to check bookings against.

This is what correctly handles a rate that gets added and then fully deleted within the window (confirmed against real data — see the design note at the bottom of this file if curious): the bounded window naturally produces zero qualifying bookings in the near-universal case where the rate was live only briefly, and the "hits only" rule in Step 6 quietly drops it. No separate "too recent" or "deleted" list is needed.

### Step 5 — One reservations pull

Single call: `wheelhouse_rmGetReservations`, `date_filter_type=booked_at`, `start_date = today - 30`, `end_date = today + 1`, `per_page=100`, paginate until a page returns fewer than 100. Filter to `status == "Accepted"` — canceled reservations aren't evidence of anything.

This keeps the whole skill to about 3 calls total (`GetListings` if needed, `GetPreferencesChangelog`, one paginated `GetReservations` pull), regardless of how many custom rate edits are found.

### Step 6 — Join and filter to hits

For each effective change from Step 4: from the Step 5 result set, take reservations whose stay overlaps `[start, end]` AND whose `booked_at` falls in `[added_at, deleted_at)` (or `[added_at, now)` if never deleted). **Only keep changes with at least one qualifying reservation** — this skill reports hits only, not misses. If literally nothing qualifies across the whole listing, say so in one line rather than an empty table.

For each surviving change, report: booking count, nights, revenue, and ADR, using `revenue_basis` (default `rent`, stated once in the output).

### Step 7 — Output

One table, one line per change with ≥1 qualifying booking, sorted by `added_at` descending:

| Change | Date Range | Made At | Edits in Window | Active Until | Bookings | Nights | Revenue | ADR |
|---|---|---|---|---|---|---|---|---|

- **Change**: plain language, e.g. "Fixed rate $71–$89 (Mon–Thu)" or "Automated rate +5.0% (Fri/Sat)".
- **Edits in Window**: only show if >1.
- **Active Until**: only show if the change was later deleted (Step 4's bounded case); otherwise leave blank.

Close with 1–2 sentences: state the `revenue_basis` default if not already obvious from the table, and note this is correlation (a booking after a rate change is consistent with the change working, not proof it caused the booking) — same caveat `price-change-attribution` uses.

## Edge cases

- **No Custom Rates events in the window at all** — say so, skip the reservations pull entirely (no point).
- **A range reshaped into narrower sub-ranges with the same value** — each sub-range is still independently joined; merge them for *display* only if they're contiguous and share the same value, exactly as `price-change-attribution` does.
- **Fixed vs. Automated (adjustment) type** — display both the same way; don't imply one is "more real" than the other. Note in passing if relevant that fixed rates bypass `minimum_price_rules_v3` while adjustment rates don't (per project instructions §6) — only if the user asks why a fixed-rate custom rate posted below what they expected.
