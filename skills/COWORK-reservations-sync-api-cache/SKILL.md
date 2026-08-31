---
name: COWORK-reservations-sync-api-cache
description: "Pulls and caches Wheelhouse RM reservation data (nightly rolling sync + a one-time/periodic historical backfill, default 1 year) to local files via a direct API key and script (no MCP/Claude in the loop for the actual HTTP calls). Use this whenever the user wants to \"sync reservations,\" set up a nightly/scheduled reservations pull using their own RM API key rather than the connected MCP, wants a historical reservation backfill that costs minimal Claude usage, or explicitly asks for the \"API key version\" of the Wheelhouse reservations sync. This is a sibling to wheelhouse-reservations-sync (the MCP-orchestrated version) -- use that one instead if the user hasn't set up an API key file. Listings and KPIs are handled by the separate wheelhouse-data-sync-api skill, not this one -- this skill depends on that one having already run at least once (reads its listings.json)."
---

# Wheelhouse Reservations Sync -- Direct API Key

Keeps a local cache of Wheelhouse reservation history on disk (a rolling
window plus a stable long-term archive) so other skills (stly-pacing,
price-change-attribution, portfolio reviews, etc.) can read booking history
from files instead of calling the API live every time.

**This is the direct-API-key sibling of `wheelhouse-reservations-sync`.**
That other skill calls the Wheelhouse MCP tools directly (Claude reasoning
over every JSON response); this one runs a plain Python script against the
RM REST API with a user-supplied key, so the mechanical fetch-and-write work
costs a rounding error of Claude usage instead of the tokens needed to relay
every reservation payload through the model. Use whichever one matches what
the user has set up.

**Depends on `wheelhouse-data-sync-api` having run first, against the exact
same `--out` directory.** This script reads `--out/listings.json` to get the
`{listing_id, channel}` pairs to iterate, rather than re-fetching listings
itself. **Don't assume the user will point this at the same folder they used
for the data-sync-api skill** -- confirm the path, or check that
`listings.json` actually exists there, before running. If it's missing, the
script exits immediately with a clear message rather than silently doing
nothing useful; if you see that error, the fix is almost always "run (or
re-run) `sync_listings_kpis.py` against this exact `--out` first," not a
retry of this script.

## API key setup

Same key file as the sibling skill: `wheelhouse_api_key.txt`, one line, no
quotes, created by the user themselves, referenced via `--api-key-file`.
Never ask for it in chat, never type it into a tool call, never read its
contents.

## Running a sync

**First time (or after any API change):**

```
python3 scripts/sync_reservations.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --selftest
```

Confirms `listings.json` exists and that the reservations endpoint responds
for the first listing found -- a single non-paginated request, so this stays
fast regardless of portfolio size (this skill never had the pagination-hang
bug the sibling KPI sync had, since selftest here uses a plain `.get()`, not
`.get_paginated()`).

**Nightly rolling sync (this is also the scheduled command -- no extra flags needed):**

```
python3 scripts/sync_reservations.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --mode rolling --verbose
```

Fetches `stay_date >= today - 30 days` forward, filters cancellations,
writes per-listing rolling files, and ages anything that's fallen out of
that 30-day window since the last run into the stable archive.

**Historical backfill (one-time; never run automatically as part of the nightly cadence):**

```
python3 scripts/sync_reservations.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --mode backfill --years 1 --verbose
```

`--years` defaults to **1, and should stay at 1 for a routine backfill** --
this is deliberate, not a placeholder. Only raise it if the user explicitly
asks for deeper history. Re-running backfill with a larger `--years` later
is safe -- it dedupes against what's already archived and just extends
coverage further back, it won't duplicate anything.

`--verbose` shows per-listing progress on either mode.

After running, relay the script's printed summary (listings total/freshly
fetched/skipped, reservations written/archived, any errors, any
unrecognized statuses) to the user rather than just saying "done."

## Same-day resume, cross-day always-refresh for rolling -- same fix as the sibling KPI sync, applied here

**The requirement: a nightly rolling sync must always pull every listing's
current reservation window. It must never silently skip a listing just
because it happens to have a rolling file from a previous night.** At the
same time, a truncated run (a real risk here -- see timing below) shouldn't
have to restart the whole portfolio from scratch on retry.

Unlike the KPI sync's JSON files, a rolling reservations file is a plain
JSONL array of reservation records -- there's no clean place to stash a
per-file freshness marker without polluting every record written to disk.
So the freshness ledger lives in `index.json` instead, under
`reservations_rolling_progress: {"{id}_{channel}": {"sync_date", "cutoff",
"synced_at"}}`. A listing is skipped only if this ledger has an entry for it
**and** that entry's `sync_date` equals today's UTC date (or the date passed
via `--date`):

- **Same day, second invocation** (resuming after a timeout): listings
  already recorded as synced earlier *today* are skipped instantly.
- **A new day's run**: every listing's recorded `sync_date` is from a prior
  day, so nothing is skipped -- every listing's rolling window gets
  refetched. This is correct behavior, not just refresh-for-its-own-sake:
  the 30-day window itself shifts forward one day too, so a stale file
  would actually be wrong, not merely old.

This ledger is written back to `index.json` **after every single listing**,
not just once at the end, so a run cut off mid-portfolio doesn't lose resume
progress for listings it already finished.

`--force` ignores the ledger and re-fetches every listing regardless of
when it was last synced -- not needed for routine nightly runs. `--date`
overrides what "today" means (UTC, `YYYY-MM-DD`) for the same-day check --
mainly for testing.

## Backfill resume works differently: by date-range coverage, not by day

Backfill isn't a daily operation, so "already done today" isn't the right
question for it -- "does what's already archived cover the range this call
would fetch" is. `index.json`'s `reservations_backfill_progress` ledger
records, per listing, the `[start_date, end_date)` range last successfully
backfilled. A listing is skipped if its recorded range already covers (is a
superset of) the range the current invocation would request -- so retrying
the same backfill command after a timeout skips everything already done and
finishes the rest, while a genuinely wider ask (a larger `--years`, or
enough real time passing that the implied dates shifted) correctly
re-fetches instead of trusting stale coverage. `--force` bypasses this the
same way it does for rolling.

## Timing to plan around

Reservations can need **more than the fixed 2 calls-per-listing** the KPI
sync always uses -- a listing with a lot of history in its requested window
needs additional pages. Confirmed against a real 47-listing account
(2026-07-28): most listings' rolling (30-day) window fit in a single page
(1 call/listing), but this isn't guaranteed for every account, and a
full-year backfill in particular can run long. Expect a full rolling sync or
backfill on a large portfolio to potentially exceed a time-boxed shell's
~45s cap -- if a run gets cut off, just re-run the identical command;
already-done listings skip in a fraction of a second (same-day for rolling,
covered-range for backfill) and the run finishes what's left. Confirmed
end-to-end on the real account: a rolling run needed 2 invocations to
finish all 47 listings, and a 1-year backfill also needed 2 invocations,
both completing with 0 errors after resuming.

## Cancellation handling

Confirmed against a real account (a Rentals United-channel managed listing
with live booking history): cancelled reservations do **not** vanish from
the reservations endpoint -- they persist with `status: "Canceled"` (single
L, American spelling; `"Cancelled"` is also matched). Every record with
that status (case-insensitive) is filtered out before it's ever written to
any cache file. Any other status that isn't `"Accepted"` gets logged to
`index.json`'s `unrecognized_reservation_statuses` so a genuinely new status
value surfaces rather than being silently mishandled.

## Output layout

```
wheelhouse_data/
├── index.json                                # shared metadata (also written to by wheelhouse-data-sync-api),
│                                                including reservations_rolling_progress and
│                                                reservations_backfill_progress ledgers
└── reservations/
    ├── rolling/{id}_{channel}.jsonl           # rewritten each rolling run
    └── stable/{year}.jsonl                    # append-only; built by backfill and by rolling's aging step
```

Reservations are one rolling file per listing (not one bundled file for the
whole portfolio) so a failure on one listing doesn't risk the rest, and a
consuming skill asking about one listing only touches one small file.
`stable/` is pooled by year since it's a long-term append-only archive most
often queried by date range across the portfolio, not per-listing.

Dedup key (used both when aging rolling records into `stable/` and when
backfilling) checks, in order: `id`, then `confirmation_code`, then a
composite of `listing_id:start_date:end_date:channel` as a last resort.

Date math (the rolling cutoff, and the backfill start/end dates) is computed
from the real UTC calendar date unless overridden by `--date` -- this
matches the sibling KPI sync's UTC-based `sync_date` convention. (This
script previously used naive local-system time for its date math, which
could silently disagree with the KPI sync's UTC-based stamps depending on
what timezone a scheduled runner's container happened to be in; now both
scripts agree.)

## Confirmed API facts this script relies on

See the sibling `wheelhouse-data-sync-api` skill's SKILL.md for the full
list (auth header, rate limit, pagination, confirmed `/listings` and KPI
paths). The one path specific to this skill,
`/listings/{listing_id}/reservations`, is not directly quoted from the live
docs (a rendering gap during verification, not an ambiguity in the API
itself) but is high-confidence by exact pattern match against every other
listing-scoped endpoint and the connected MCP's generated tool schema.
`--selftest` is the fast, cheap way to confirm or catch it before a full run,
and it returns real per-record field names (confirmed against a live
account): `id`, `confirmation_code`, `status`, `start_date`, `end_date`,
`booked_at`, `created_at`, `updated_at`, `source_name`, `num_guests`,
`nightly_subtotal`, `total_price`, `taxes`, `security_deposit`,
`extra_guest`, `extras`, `comments`, `currency`.

## Consumer pattern (for other skills reading this cache)

Check `index.json`'s `last_sync.reservations` / `last_sync.reservations_sync_date`
(rolling) and `last_sync.reservations_backfill` (historical) for freshness
and coverage before trusting a date range. For "on the books" or
forward-looking questions, read `reservations/rolling/{id}_{channel}.jsonl`.
For historical/STLY comparisons, read the relevant
`reservations/stable/{year}.jsonl` file(s). A consuming skill that cares
whether a specific listing's rolling data is from today specifically (not
just "present") can check `reservations_rolling_progress[key].sync_date`
directly rather than assuming freshness from the file's mere existence. If
the cache doesn't cover the requested range, fall back to a live call rather
than failing the question outright.

## Cadence and scheduling

Rolling sync should run nightly (use the `schedule` skill) with the plain
command above -- no `--force` needed, since the cross-day always-refresh
behavior already guarantees every listing's window gets re-pulled each
night. Backfill is a one-time or occasional manual operation at `--years 1`
-- never wire it into the nightly schedule; a fresh backfill re-run to
extend history further back should be a deliberate ask, not automatic. For
portfolios large enough to risk exceeding a scheduled runner's execution
time limit, either allow more wall-clock time or accept that a single
scheduled invocation may only get partway -- the same-day resume behavior
means a follow-up invocation (still no flags needed) finishes the rest
before the next night's run rolls the date over again.

## Fix history

- **2026-07-28:** Rebuilt this skill applying the learnings from fixing the
  sibling `wheelhouse-data-sync-api` skill's KPI sync the same day. Three
  changes:
  1. **Same-day resume / cross-day always-refresh for rolling sync.**
     Previously, every rolling invocation re-fetched every listing from
     scratch with no way to skip ones already done, so a run truncated by a
     shell timeout had to restart completely. Added a `reservations_rolling_progress`
     ledger in `index.json` (keyed by listing, storing `sync_date`) that
     mirrors the sibling skill's per-file `sync_date` design, adapted for
     JSONL output where per-record metadata isn't practical. Skips a
     listing only if it was already synced *today*; a new calendar day
     re-fetches everything automatically, satisfying "this should always do
     every single one nightly" without needing a flag remembered on every
     scheduled run.
  2. **Coverage-based resume for backfill.** Same underlying problem
     (truncated runs over many listings), different fix, since backfill
     isn't date-keyed the same way: added a `reservations_backfill_progress`
     ledger recording each listing's already-covered `[start_date, end_date)`
     range, skipping a listing only when its recorded range is a superset of
     what the current invocation would request.
  3. **UTC-consistent date math.** This script previously used
     `datetime.date.today()` (local system time) for its rolling cutoff and
     backfill start/end dates, while the sibling KPI sync's `sync_date`
     stamps are UTC-based -- a latent inconsistency that could bite under a
     scheduled runner in a different timezone. Both scripts now compute
     "today" the same way (UTC, overridable via `--date`).
  Both new ledgers are flushed to `index.json` after every single listing
  (not just once at the end), so a truncated run never loses resume progress
  for listings it already finished. All three changes verified end-to-end
  against a real 47-listing account: (a) a same-day rolling run cut off
  partway resumed correctly and skipped only already-done listings; (b) a
  simulated new day correctly re-fetched every listing rather than skipping
  any; (c) a 1-year backfill cut off partway resumed correctly via the
  coverage check and completed all 47 listings with 0 errors across two
  invocations.
