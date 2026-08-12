# Changelog Parsing Rules

`wheelhouse_rmGetPreferencesChangelog` returns `events`, each shaped like:

```json
{"time": "2026-07-09T13:42:22.253-07:00", "source": "User John deRoulet", "event": "Settings changed", "status": "success", "msg": "Global minimum prices modified: 99 $<br>Monthly minimum prices modified: [Jan, Feb, Mar, Jun, Jul] 150 $<br>Date-specific minimum prices modified: From Aug 01, 26 to Aug 31, 26, 70 $"}
```

There are no structured old/new-value fields. Everything actionable is in `msg`, an HTML string. Parsing is line-by-line, not event-by-event.

## Step 0 — Drop noise events

Discard any event where `source == "Wheelhouse"` (these are `event: "Prices posted"` sync confirmations — no preference content, just confirm a sync ran).

## Step 1 — Split into lines

Split `msg` on `<br>`. Each resulting line is independently classified. One event routinely contains 2-3 unrelated lines (different settings, different scopes) — treat each as its own change.

## Step 2 — Classify each line

| Line prefix pattern | Bucket | Extraction |
|---|---|---|
| `Global <setting> modified: <value>` | General | setting name, new value |
| `Default <setting> modified: <value>` | General | setting name, new value (per-day-of-week values may follow, e.g. "Sun 0 % Mon 0 % ...") |
| `Monthly <setting> modified: [<months>] <value>` | Month-scoped | setting name, month list, new value |
| `Time-based <setting> modified: After <N> day(s), <value>` | General (lead-time flavor — label as such in output) | setting name, day threshold, new value |
| `Date-specific <setting> modified: From <date1> to <date2>, <value>` | Date-scoped | setting name, date range, new value |
| `Base price changed to $<amount>` | General | dollar value directly available |
| `Base price changed to recommended` | General | dollar value NOT given — resolve via `GetBasePriceHistory` only if needed for output completeness |
| `Monthly Seasonality modified: [Jan] X%; [Feb] Y%; ...` | Month-scoped | one change per bracketed month, or treat as a single month-scoped change covering all listed months if the user wants an aggregate view |
| Custom Rates lines — see Step 3 | — | — |

Anything not matching a known pattern: surface it in output as an unclassified/raw line rather than silently dropping it, and note it may need a pattern-table update.

## Step 3 — Custom Rates event lines

Custom Rates events (`event: "Custom rates"`) log cascading edits as the system reshapes overlapping date ranges — a single logical edit often produces several lines:

```
Automated rate removed for Aug 22, 26 - Aug 22, 26 with Saturdays at 10.0%
Automated rate removed for Aug 16, 26 - Aug 21, 26 with Sundays at 10.0%, ...
Automated rate added for Aug 18, 26 - Aug 21, 26 with Tuesdays at -1.0%, ...
Automated rate added for Aug 16, 26 - Aug 17, 26 with Sundays at 10.0%, ...
Automated rate split off for Aug 22, 26 - Aug 22, 26 with Saturdays at -1.0% (Originally created by John deRoulet)
```

**Rule: only lines starting with "Automated rate added" or "Fixed rate added" are actionable changes.** Ignore "removed" and "split off" lines entirely — they're bookkeeping byproducts of the same edit, not separate decisions.

**Latest-wins**: if the same (or overlapping) date range gets an "added" line more than once within the lookback window, use the most recent one as the effective change; use its timestamp as the booking cutoff. Track how many times that range was touched and surface the count as context (e.g. "edited 3× in the last 7 days") without trying to reconstruct the full history. **This same rule applies to any date-scoped `Settings changed` line too** (e.g. a "Date-specific minimum stays" range edited twice within minutes) — not just Custom Rates.

**Rate type**: "Fixed rate added" → `fixed` (absolute $ per day, bypasses `minimum_price_rules_v3`, only floored by `min_min_price`). "Automated rate added" → `adjustment` (percentage multiplier on the Wheelhouse recommendation, also constrained by `minimum_price_rules_v3`). Carry this distinction into output since it affects how the value should be read.

**Display merge**: when one event yields several "added" lines with the same value (same rate type, same adjustment/fixed amount, same day-of-week pattern), report them as a single change spanning the union of their date ranges rather than as separate rows. Keep the underlying reservation join per sub-range — the merge is a reporting convenience, not a change to the matching logic.

## Step 4 — Date parsing

Dates appear as `"Aug 01, 26"` (short month name, 2-digit day, 2-digit year). Normalize to ISO 8601 (`2026-08-01`) before using in any `GetReservations` filter. Month lists in Monthly lines use the same 3-letter abbreviations (`[Jan, Feb, Mar, Jun, Jul]`) — map to month numbers 1-12 for the month-membership filter.

## Worked example

Given the sample event above, decomposed:

1. `Global minimum prices modified: 99 $` → **General** — global minimum price now $99.
2. `Monthly minimum prices modified: [Jan, Feb, Mar, Jun, Jul] 150 $` → **Month-scoped** — minimum price $150 for stays in those months, any year.
3. `Date-specific minimum prices modified: From Aug 01, 26 to Aug 31, 26, 70 $` → **Date-scoped** — minimum price $70 for 2026-08-01 through 2026-08-31.

Three separate changes from one event, three different attribution paths.
