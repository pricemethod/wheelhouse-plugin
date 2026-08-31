---
name: COWORK-Listing-data-sync-api-cache
description: "Pulls and caches Wheelhouse RM listings and KPIs (rolling + monthly) to local files via a direct API key and script (no MCP/Claude in the loop for the actual HTTP calls), so other Wheelhouse skills can read from disk instead of calling the live API through the model. Use this whenever the user wants to \"sync,\" \"cache,\" \"refresh,\" or \"pull down\" Wheelhouse listings/KPIs using their own RM API key rather than the connected MCP, wants a nightly/scheduled listings+KPI pull that costs minimal Claude usage, or explicitly asks for the \"API key version\" / \"direct API version\" of the Wheelhouse sync. This is a sibling to wheelhouse-data-sync (the MCP-orchestrated version) -- use that one instead if the user hasn't set up an API key file or wants Claude to reason over each call. Reservations are handled by the separate wheelhouse-reservations-sync-api skill, not this one."
---


# Wheelhouse Data Sync -- Direct API Key (Listings + KPIs)

Keeps a local cache of Wheelhouse listings and KPIs (rolling + monthly) on
disk so other skills (stly-pacing, future-rate-overpricing,
price-change-attribution, portfolio reviews, etc.) can read from files
instead of calling the API live every time.

**This is the direct-API-key sibling of `wheelhouse-data-sync`.** That other
skill calls the Wheelhouse MCP tools directly (Claude reasoning over every
JSON response); this one runs a plain Python script against the RM REST API
with a user-supplied key, so the mechanical fetch-and-write work costs a
rounding error of Claude usage instead of the tokens needed to relay dozens
of large API responses through the model. Use whichever one matches what the
user has set up -- don't silently switch a user from one to the other.

**This skill covers listings and KPIs only.** Reservations (rolling sync and
historical backfill) live in the sibling `wheelhouse-reservations-sync-api`
skill.

## API key setup -- once, never pasted into chat

Needs a Wheelhouse RM API key with read access (Wheelhouse dashboard ->
profile menu -> API Key -> Revenue Management API Keys -> Create RM Key).

1. The user creates a plain text file themselves (in their own file manager,
   not through Claude) containing just the key, one line, no quotes --
   named `wheelhouse_api_key.txt`, placed alongside where `wheelhouse_data/`
   lives (e.g. directly in the connected workspace folder).
2. Reference that file's path with `--api-key-file` when running the script.
3. Never ask the user to paste the key into a chat message, never type it
   into a tool call, and never `cat`/`Read` the key file's contents -- there
   is no legitimate reason for this skill to need to see the literal value.

## Running a sync

**First time, or after any Wheelhouse API change:**

```
python3 scripts/sync_listings_kpis.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --selftest
```

3 calls total (1 listings page, 1 rolling-KPI, 1 monthly-KPI), regardless of
portfolio size -- `--selftest` takes a single item from the listings
generator via `next()` rather than materializing a full page, so it stays
fast even on large portfolios. If it fails with a 404, the printed error
names which endpoint path needs a look -- cheap to catch here versus
partway through a full run.

**Full sync (this is also the nightly/scheduled command -- no extra flags needed):**

```
python3 scripts/sync_listings_kpis.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --verbose
```

Flags:
- `--include-inactive` -- also pull inactive/delisted listings (default:
  excluded, matching the API's own `exclude_inactive` default).
- `--owned-only` -- restrict to listings the account owns, excluding
  managed/delegated listings (default: managed listings are **included**,
  via `include_managed_listings=true` -- confirmed required for portfolios
  with shared-access listings from another Wheelhouse account).
- `--verbose` -- per-listing progress (`OK` for freshly-fetched listings,
  `SKIP` for ones already synced earlier the same day -- see below).
- `--force` -- ignore each listing's stored sync date entirely and re-fetch
  every listing regardless of when it was last synced. Not needed for
  routine nightly runs (a new calendar day already re-fetches everything by
  default, see below) -- reserve this for a deliberate guaranteed-fresh pull,
  e.g. right after changing `--include-inactive`/`--owned-only` and wanting
  every listing re-evaluated under the new flags immediately.
- `--date YYYY-MM-DD` -- override what "today" means (UTC) for the
  same-day-skip check. Mainly for testing; defaults to the real current UTC
  date and should be left alone for normal use.

## Same-day resume, cross-day always-refresh -- this is what makes nightly runs correct

**The requirement this is built around: a nightly sync must always pull
every single listing's current KPIs. It must never silently skip a listing
just because a same-named file happens to already exist from a previous
night.** At the same time, a single sync attempt can get cut off partway
through (a real, confirmed failure mode -- see the timing note below), and
naively re-fetching already-completed listings from scratch on every retry
wastes time and API calls for no benefit.

The mechanism: each `kpis/{id}_{channel}.json` file stores a `sync_date`
field -- the UTC calendar date the sync run that wrote it was for -- next to
the existing `synced_at` timestamp. A listing is skipped **only if its file
already exists and that file's `sync_date` matches today's date**:

- **Same day, second invocation** (e.g. resuming a run that got cut off by a
  timeout): listings already written earlier *today* are skipped instantly
  -- fast resume, no wasted calls, and the run finishes the remaining
  listings.
- **A new day's run** (i.e. the actual nightly case): every listing's stored
  `sync_date` is from a prior day, so **nothing is skipped** -- every single
  listing gets a fresh pull. This is what "always do every listing nightly"
  actually requires, and it happens automatically with no flag to remember.

This means the plain command above (no `--force`) is correct for both the
manual-resume case and the nightly-scheduled case -- you don't need to
choose between them or remember a flag; the date comparison picks the right
behavior on its own. `--force` is only for the rarer case where you want a
fresh pull *right now*, same-day, ignoring what's already cached.

**Timing to plan around:** at ~1.2s pacing between calls and 2 KPI calls per
listing, a full from-scratch sync of N listings takes roughly `N * 2 * 1.2`
seconds (~110s for a 47-listing portfolio) before any retries -- which can
exceed a time-boxed shell's timeout (confirmed against a 45s cap). If a run
gets cut off, just re-run the identical command; already-done listings for
today skip in a fraction of a second and the run picks up where it left
off. Expect to need 2-3 invocations to finish a from-scratch (or new-day)
sync on a portfolio of this size within a 45s-per-call constraint.

After running, read back the script's printed summary (listings count, KPIs
synced/freshly-fetched/already-done, any errors) and relay a short version
to the user -- don't just say "done." Name any listings that errored. The
summary explicitly states when every listing has been freshly synced for
today with 0 errors, versus when some were already done earlier today.

## Output layout

```
wheelhouse_data/
├── index.json                    # shared sync metadata (also written to by wheelhouse-reservations-sync-api)
├── listings.json                 # object keyed by "{id}_{channel}" -> full listing record
└── kpis/
    └── {id}_{channel}.json       # {"listing_id","channel","synced_at","sync_date","rolling":{...},"monthly":[...]}
```

KPIs are one file per listing (not one bundled file for the whole
portfolio, and **not** date-stamped in the filename), so a single-listing
question only ever touches one small file instead of the entire portfolio's
KPI data, and consumer skills always read the same stable filename
regardless of which day's sync last wrote it. The freshness signal lives
*inside* the file (`sync_date`/`synced_at`), not in the filename.

Monthly KPI rows with `adr: null` are dropped before writing (null-padded
future placeholder months with zero real data). Rolling KPI top-level keys
whose value is a dict where every value is null are dropped too (typically
`comp_set_*` on a listing with no matched comp set).

`listings.json` is always fully rewritten on every run (`open(..., "w")` +
full re-dump) -- it's small and cheap, so it doesn't need the same
same-day/cross-day logic as KPIs. `index.json` is read-modify-written
(loads existing content, updates `last_sync.*` fields including
`last_sync.kpis_sync_date`) rather than overwritten outright, so metadata
accumulates safely across runs.

## Confirmed API facts this script relies on

Verified directly against the live RM API reference
(api.usewheelhouse.com/wheelhouse_rm_api), and cross-checked against a real
47-listing account on 2026-07-28:
- Auth: `X-Integration-Api-Key` header, single key for both integration and
  user context. Confirmed working end-to-end.
- Rate limit: 60 requests/minute, rolling one-minute window, `429` on
  breach. Script paces at ~1.2s between calls and backs off exponentially
  (capped at 60s) on a 429. At this pacing, a full sync of N listings takes
  roughly `N * 2 * 1.2` seconds just for KPI calls (~110s for 47 listings),
  before any retries -- factor this into how much wall-clock time to allow
  a scheduled run, or rely on the same-day resume behavior across
  invocations.
- Pagination: `page` (1-based) or `offset` (0-based) -- never both --
  `per_page` up to 100, stop when a page returns fewer than `per_page`.
  Confirmed working correctly both for the default full-sync `per_page=100`
  and for `--selftest`'s single-item `next()` pull.
- `/listings` -- confirmed path and params: `exclude_inactive` (default
  true), `include_managed_listings` (default false, this script always
  passes true unless `--owned-only`). Response is a bare array, no wrapper.
  Confirmed real response shape includes `id`, `channel`, `title`,
  `location`, `listing_preferences`, etc.
- `/listings/{listing_id}/kpis` and `/listings/{listing_id}/kpis/monthly`
  -- confirmed paths, `channel` required as a query param alongside
  `listing_id` as a path param. Confirmed real rolling-KPI response includes
  `currency`, `model_date`, `comp_set_count`, `adr`, `adr_fees`, etc.; real
  monthly response is a list of per-month rows.
- `/listings/{listing_id}/reservations` (used by the sibling skill) --
  **not directly confirmed** (a rendering gap in the fetched docs, not an
  ambiguity in the API), but high-confidence by pattern-matching every
  other listing-scoped endpoint plus the connected MCP's generated tool
  schema. The reservations skill's `--selftest` is the safety net if this
  turns out wrong.

## Consumer pattern (for other skills reading this cache)

Check `wheelhouse_data/index.json` first for `last_sync.listings` /
`last_sync.kpis` / `last_sync.kpis_sync_date` freshness. For a specific
listing, resolve its `{id}_{channel}` key from `listings.json`, then read
`kpis/{id}_{channel}.json` directly -- don't read every file in `kpis/`
unless the question is genuinely portfolio-wide. A consuming skill that
cares whether a listing's KPIs are from today specifically (rather than
just "present") should check that file's own `sync_date` field, not assume
freshness from the file's mere existence. If the cache is missing or stale
for the question, fall back to a live call (via this script or the MCP)
rather than failing the user's question outright.

## Cadence and scheduling

Listings change slowly; KPIs move daily. Both are bundled into one script
run here for simplicity -- the whole run is cheap since it's script-driven.
Use the `schedule` skill to set up a nightly scheduled task that runs the
plain full-sync command above (no `--force` needed -- the cross-day
always-refresh behavior described above already guarantees every listing
gets re-pulled each night). Claude's role in a scheduled run is just to
invoke the script and report its summary, not to process each listing
itself. For portfolios large enough to risk exceeding the scheduled
runner's execution-time limit, either allow more wall-clock time or accept
that a single scheduled invocation may only get partway -- the same-day
resume behavior means a follow-up invocation (still no flags needed) will
finish the rest before the next night's run rolls the date over again.

## Fix history

- **2026-07-28 (initial bug fixes):** Fixed two bugs found while running
  this against a real 47-listing account. (1) `--selftest` used to call
  `list(get_paginated("/listings", ..., per_page=1))`, which with
  `per_page=1` never satisfies the "fewer than per_page" stop condition --
  it paginated through the *entire* portfolio one listing per call before
  ever checking anything, hanging well past most shell timeouts with zero
  output on portfolios above roughly 15-20 listings. Fixed by taking a
  single item via `next()` instead of exhausting the generator with
  `list()`. (2) The full sync had no way to skip listings already written,
  so a run truncated by a timeout had to restart completely from scratch.
  First fix attempt added a bare "skip if file exists" check plus a
  `--force` flag -- functionally a resume mechanism, but wrong for nightly
  use, since it would skip a listing forever once its file existed unless
  `--force` was remembered on every scheduled invocation.
- **2026-07-28 (same-day/cross-day redesign):** Replaced the bare
  file-exists skip check with a `sync_date`-based one: each KPI file now
  stores the UTC calendar date it was synced for, and a listing is skipped
  only if that stored date matches the current run's date. This makes the
  default (no-flag) behavior correct for both manual same-day resume
  (skip, fast) and nightly scheduled runs (a new day means nothing matches,
  so everything gets refreshed automatically). `--force` was narrowed to
  mean "ignore sync_date, always redo," and a `--date` override was added
  for testing the logic without waiting for a real day to roll over.
  Verified end-to-end with three scenarios against the real account: (a)
  a same-day run cut off partway through resumed correctly and skipped only
  the already-done listings; (b) re-running under a later `--date` value
  correctly treated every previously-synced listing as due for a fresh
  pull rather than skipping any of them; (c) re-running again under that
  same later date correctly skipped the now-current day's completed
  listings. All three matched the intended nightly-refresh behavior.
