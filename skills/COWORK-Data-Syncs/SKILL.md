---
name: COWORK-Data-Syncs
description: "Pulls and caches Wheelhouse RM data (listings + KPIs, reservations, and future price calendars -- either replace-only or with dated history snapshots) to local files via a direct API key and plain scripts, no MCP/Claude in the loop for the actual HTTP calls, so other Wheelhouse skills can read from disk instead of calling the live API through the model. Use this whenever the user wants to \"sync,\" \"cache,\" \"refresh,\" \"archive,\" or \"pull down\" Wheelhouse listings, KPIs, reservations, or calendar/availability data using their own RM API key rather than the connected MCP, wants a nightly/scheduled pull that costs minimal Claude usage, or explicitly asks for the \"API key version\" / \"direct API version\" of a Wheelhouse sync. This is the direct-API-key sibling of the MCP-orchestrated skills -- use one of those instead if the user hasn't set up an API key file or wants Claude to reason over each call. Covers four sync modes in one skill: listings+KPIs (sync_listings_kpis.py), reservations (sync_reservations.py, depends on listings+KPIs having run first), calendar replace-only (sync_calendar.py), and calendar with dated history snapshots (sync_calendar_history.py)."
---

# Wheelhouse Data Syncs -- Direct API Key

Keeps a local cache of Wheelhouse portfolio data on disk -- listings, KPIs,
reservations, and future price calendars -- so other skills (stly-pacing,
future-rate-overpricing, price-change-attribution, portfolio reviews, etc.)
can read from files instead of calling the API live every time.

**This is the direct-API-key sibling of the MCP-orchestrated Wheelhouse
skills.** Those call the Wheelhouse MCP tools directly (Claude reasoning over
every JSON response); this skill runs plain Python scripts against the RM
REST API with a user-supplied key, so the mechanical fetch-and-write work
costs a rounding error of Claude usage instead of the tokens needed to relay
dozens (or thousands) of large API responses through the model. Use whichever
matches what the user has set up -- don't silently switch a user from one to
the other.

This single skill bundles four independent sync modes, each its own script
under `scripts/`, sharing one HTTP client (`scripts/_wh_client.py`):

| Mode | Script | Covers |
|------|--------|--------|
| Listings + KPIs | `sync_listings_kpis.py` | Portfolio listings, rolling KPIs, monthly KPIs |
| Reservations | `sync_reservations.py` | Rolling booking window + historical backfill. **Depends on Listings+KPIs having run first against the same `--out`** (reads its `listings.json`). |
| Calendar (simple) | `sync_calendar.py` | Future price/availability calendar, replace-only, no history |
| Calendar (history) | `sync_calendar_history.py` | Same calendar data, but every night's prior pull is preserved as a dated snapshot |

Pick the mode(s) the user's question needs -- they can all be run against the
same `--out` directory except the two calendar modes, which use different
on-disk layouts and must not share a directory with each other (see
"Calendar modes" below).

## API key setup -- once, never pasted into chat

Needs a Wheelhouse RM API key with read access (Wheelhouse dashboard ->
profile menu -> API Key -> Revenue Management API Keys -> Create RM Key).
**One key file works for all four modes.**

1. The user creates a plain text file themselves (in their own file manager,
   not through Claude) containing just the key, one line, no quotes --
   named `wheelhouse_api_key.txt`, placed alongside where the output data
   directory lives (e.g. directly in the connected workspace folder).
2. Reference that file's path with `--api-key-file` when running any script.
3. Never ask the user to paste the key into a chat message, never type it
   into a tool call, and never `cat`/`Read` the key file's contents -- there
   is no legitimate reason for this skill to need to see the literal value.

## Confirmed API facts shared by all four scripts

Verified directly against the live RM API reference
(api.usewheelhouse.com/wheelhouse_rm_api) and cross-checked against a real
47-listing account (2026-07-28 through 2026-08-04):

- Auth: `X-Integration-Api-Key` header, single key for both integration and
  user context. Confirmed working end-to-end.
- Rate limit: 60 requests/minute, rolling one-minute window, `429` on
  breach. Every script paces at ~1.2s between calls and backs off
  exponentially (capped at 60s) on a 429.
- Pagination (where it applies): `page` (1-based) or `offset` (0-based) --
  never both -- `per_page` up to 100, stop when a page returns fewer than
  `per_page`.
- `/listings` -- `exclude_inactive` (default true), `include_managed_listings`
  (default false; every script here always passes true unless `--owned-only`).
  Response is a bare array, no wrapper. Real response shape includes `id`,
  `channel`, `title`, `location`, `listing_preferences`, etc.
- `listing_id` in every path is the **channel's** string ID (from `/listings`'
  `id` field), not the internal `wheelhouse_id`.

Endpoint-specific facts (KPIs, reservations, price_calendar) are documented in
`scripts/_wh_client.py`'s module docstring and in each mode's section below.

## Same-day resume, cross-day always-refresh -- shared design across all four scripts

**The requirement every mode is built around: a nightly sync must always pull
every listing's current data. It must never silently skip a listing just
because a same-named file already exists from a previous night.** At the same
time, a single sync attempt can get cut off partway through (a confirmed
failure mode -- large portfolios can exceed a time-boxed shell's timeout), and
naively re-fetching already-completed listings on every retry wastes time and
API calls.

The mechanism (adapted per mode to its own file layout, see each section
below): a freshness marker (`sync_date`, the UTC calendar date the run was
for) is stored either inside each listing's own output file, or in a ledger
inside `index.json` when the output format doesn't have a natural per-record
place to put one (e.g. JSONL reservations). A listing is skipped **only if**
that marker already exists **and** matches today's date:

- **Same day, second invocation** (resuming a run cut off by a timeout):
  already-done listings are skipped instantly -- fast resume, no wasted calls.
- **A new day's run** (the nightly case): every stored marker is from a prior
  day, so **nothing is skipped** -- every listing gets a fresh pull.

This means the plain full-sync command for any mode (no `--force`) is correct
for both manual resume and nightly-scheduled use -- the date comparison
picks the right behavior automatically. `--force` (all four scripts) ignores
the marker and re-fetches everything right now, regardless of when it was
last synced -- not needed for routine nightly runs, only for a deliberate
guaranteed-fresh pull. `--date YYYY-MM-DD` (all four scripts) overrides what
"today" means (UTC) for the skip check -- mainly for testing.

After running any script, read back its printed summary and relay a short
version to the user -- don't just say "done." Name any listings that errored.

---

## Mode: Listings + KPIs

```
python3 scripts/sync_listings_kpis.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --selftest
```

3 calls total (1 listings page, 1 rolling-KPI, 1 monthly-KPI), regardless of
portfolio size -- `--selftest` takes a single item from the listings
generator via `next()` rather than materializing a full page, so it stays
fast even on large portfolios. A 404 names which endpoint path needs a look.

**Full sync (also the nightly/scheduled command -- no extra flags needed):**

```
python3 scripts/sync_listings_kpis.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --verbose
```

Flags:
- `--include-inactive` -- also pull inactive/delisted listings (default:
  excluded, matching the API's own `exclude_inactive` default).
- `--owned-only` -- restrict to listings the account owns, excluding
  managed/delegated listings (default: managed listings **included**,
  confirmed required for portfolios with shared-access listings).
- `--verbose` -- per-listing progress (`OK` / `SKIP`).
- `--force`, `--date` -- see shared resume section above.

**Timing:** ~1.2s pacing, 2 KPI calls per listing -> roughly `N * 2 * 1.2`
seconds (~110s for a 47-listing portfolio) before retries -- can exceed a
time-boxed shell's timeout (confirmed against a 45s cap). If cut off, just
re-run the identical command; already-done listings for today skip instantly.

### Output layout

```
wheelhouse_data/
├── index.json                    # shared sync metadata (also written to by the Reservations mode)
├── listings.json                 # object keyed by "{id}_{channel}" -> full listing record
└── kpis/
    └── {id}_{channel}.json       # {"listing_id","channel","synced_at","sync_date","rolling":{...},"monthly":[...]}
```

One file per listing for KPIs (not one bundled portfolio file) so a
single-listing question only touches one small file, and the filename stays
stable regardless of which day's sync last wrote it. Monthly rows with
`adr: null` are dropped (null-padded future placeholder months). Rolling
top-level keys whose value is a dict where every value is null are dropped
too (typically `comp_set_*` with no matched comp set). `listings.json` is
always fully rewritten; `index.json` is read-modify-written so metadata
accumulates safely across runs and across modes.

### Consumer pattern

Check `index.json`'s `last_sync.listings` / `last_sync.kpis` /
`last_sync.kpis_sync_date` first. For a specific listing, resolve its
`{id}_{channel}` key from `listings.json`, then read `kpis/{id}_{channel}.json`
directly -- don't read every file in `kpis/` unless the question is
genuinely portfolio-wide. Fall back to a live call if the cache is missing
or stale rather than failing the question outright.

### Fix history

- **2026-07-28 (initial bug fixes):** Fixed two bugs found running against a
  real 47-listing account. (1) `--selftest` used
  `list(get_paginated("/listings", ..., per_page=1))`, which with
  `per_page=1` never satisfies the "fewer than per_page" stop condition and
  paginated the entire portfolio before returning anything, hanging past
  most shell timeouts on portfolios above ~15-20 listings. Fixed by taking a
  single item via `next()` instead of exhausting the generator with `list()`.
  (2) No way to skip already-written listings, so a truncated run had to
  restart from scratch. A first fix (bare file-exists skip + `--force`) was
  wrong for nightly use -- it would skip a listing forever once its file
  existed unless `--force` was remembered every scheduled invocation.
- **2026-07-28 (same-day/cross-day redesign):** Replaced the bare
  file-exists check with the `sync_date`-based mechanism described in the
  shared resume section above. Verified end-to-end against the real account:
  (a) a same-day run cut off partway resumed correctly; (b) re-running under
  a later `--date` correctly treated every listing as due for a fresh pull;
  (c) re-running again under that same later date correctly skipped the
  now-current day's completed listings.

---

## Mode: Reservations

**Depends on the Listings + KPIs mode having run first, against the exact
same `--out` directory.** This script reads `--out/listings.json` to get the
`{listing_id, channel}` pairs to iterate rather than re-fetching listings
itself. Don't assume the user will point this at the same folder used for
the listings sync -- confirm the path, or check `listings.json` exists there,
before running. If it's missing, the script exits immediately with a clear
message; the fix is almost always "run (or re-run) `sync_listings_kpis.py`
against this exact `--out` first," not a retry of this script.

```
python3 scripts/sync_reservations.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --selftest
```

Confirms `listings.json` exists and the reservations endpoint responds for
the first listing found -- a single non-paginated request, fast regardless
of portfolio size.

**Nightly rolling sync (also the scheduled command -- no extra flags needed):**

```
python3 scripts/sync_reservations.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --mode rolling --verbose
```

Fetches `stay_date >= today - 30 days` forward, filters cancellations, writes
per-listing rolling files, and ages anything that's fallen out of that
30-day window since the last run into the stable archive.

**Historical backfill (one-time; never run automatically as part of nightly cadence):**

```
python3 scripts/sync_reservations.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_data --mode backfill --years 1 --verbose
```

`--years` defaults to **1, and should stay at 1 for a routine backfill** --
deliberate, not a placeholder. Only raise it if the user explicitly asks for
deeper history. Re-running backfill with a larger `--years` later is safe --
it dedupes against what's already archived and just extends coverage back
further, never duplicating anything.

### Resume mechanics specific to reservations

Unlike the KPI sync's per-listing JSON files, a rolling reservations file is
a plain JSONL array -- no clean place for a per-file freshness marker without
polluting every record. So the ledger lives in `index.json` instead, under
`reservations_rolling_progress: {"{id}_{channel}": {"sync_date", "cutoff",
"synced_at"}}`. Same same-day-skip / cross-day-refresh logic as the shared
design above, applied via this ledger. It's written back **after every
single listing**, not just once at the end, so a truncated run doesn't lose
resume progress for listings it already finished.

**Backfill resume works differently: by date-range coverage, not by day.**
`index.json`'s `reservations_backfill_progress` ledger records, per listing,
the `[start_date, end_date)` range last successfully backfilled. A listing is
skipped if its recorded range already covers the range the current
invocation would request -- so retrying after a timeout skips completed
listings and finishes the rest, while a genuinely wider ask (larger
`--years`, or real time passing) correctly re-fetches instead of trusting
stale coverage. `--force` bypasses this the same way it does for rolling.

**Timing:** reservations can need more than the fixed 2-calls-per-listing the
KPI sync always uses -- a listing with a lot of history in its window needs
extra pages. Confirmed against a real 47-listing account: most listings'
30-day rolling window fit in a single page, but this isn't guaranteed for
every account, and a full-year backfill can run long. If a run gets cut off,
re-run the identical command; already-done listings skip in a fraction of a
second.

### Cancellation handling

Confirmed against a real account: cancelled reservations do **not** vanish
from the endpoint -- they persist with `status: "Canceled"` (single L,
American spelling; `"Cancelled"` also matched). Every record with that status
(case-insensitive) is filtered out before being written to any cache file.
Any other status that isn't `"Accepted"` gets logged to `index.json`'s
`unrecognized_reservation_statuses` so a genuinely new status value surfaces
rather than being silently mishandled.

### Output layout

```
wheelhouse_data/
├── index.json                                # shared metadata, including reservations_rolling_progress
│                                                and reservations_backfill_progress ledgers
└── reservations/
    ├── rolling/{id}_{channel}.jsonl           # rewritten each rolling run
    └── stable/{year}.jsonl                    # append-only; built by backfill and by rolling's aging step
```

One rolling file per listing (not one bundled portfolio file) so a failure on
one listing doesn't risk the rest. `stable/` is pooled by year since it's a
long-term append-only archive most often queried by date range across the
portfolio. Dedup key (aging into `stable/`, and backfilling): `id`, then
`confirmation_code`, then `listing_id:start_date:end_date:channel` as a last
resort. Date math is computed from the real UTC calendar date unless
overridden by `--date`, matching the Listings+KPIs mode's convention.

### Confirmed API facts

`/listings/{listing_id}/reservations` is not directly quoted from the live
docs (a rendering gap during verification, not an ambiguity in the API
itself) but is high-confidence by exact pattern match against every other
listing-scoped endpoint and the connected MCP's generated tool schema.
`--selftest` is the fast, cheap way to confirm or catch it before a full run.
Real per-record field names (confirmed against a live account): `id`,
`confirmation_code`, `status`, `start_date`, `end_date`, `booked_at`,
`created_at`, `updated_at`, `source_name`, `num_guests`, `nightly_subtotal`,
`total_price`, `taxes`, `security_deposit`, `extra_guest`, `extras`,
`comments`, `currency`.

### Consumer pattern

Check `index.json`'s `last_sync.reservations` / `last_sync.reservations_sync_date`
(rolling) and `last_sync.reservations_backfill` (historical) for freshness
and coverage before trusting a date range. For "on the books"/forward-looking
questions, read `reservations/rolling/{id}_{channel}.jsonl`. For
historical/STLY comparisons, read the relevant `reservations/stable/{year}.jsonl`
file(s). Fall back to a live call if the cache doesn't cover the requested
range rather than failing the question outright.

### Fix history

- **2026-07-28:** Rebuilt applying the same-day fixes made to the Listings+KPIs
  mode the same day. Three changes: (1) same-day resume / cross-day
  always-refresh for rolling sync via the `reservations_rolling_progress`
  ledger described above -- previously every rolling invocation re-fetched
  every listing from scratch with no skip mechanism. (2) Coverage-based
  resume for backfill via `reservations_backfill_progress`. (3) UTC-consistent
  date math -- previously used local system time for the rolling cutoff and
  backfill dates, a latent inconsistency with the KPI sync's UTC-based
  stamps that could bite under a scheduled runner in a different timezone.
  Both ledgers flush after every single listing, not just once at the end.
  Verified end-to-end against a real 47-listing account: (a) a same-day
  rolling run cut off partway resumed correctly; (b) a simulated new day
  correctly re-fetched every listing; (c) a 1-year backfill cut off partway
  resumed via the coverage check and completed all 47 listings with 0 errors
  across two invocations.

---

## Calendar modes -- simple vs. history-keeping

Both calendar modes pull each listing's future price calendar (price,
availability, booked/blocked state per date). **Pick one per output
directory -- don't point both at the same `--out`.** Each owns a different
on-disk layout underneath that path (`calendar/` flat files for simple vs.
`current/` + `snapshots/` for history-keeping), and mixing them risks
confusing the two formats. They default to different output folders
(`wheelhouse_calendar_data/` vs. `wheelhouse_calendar_data_history/`)
specifically so both can be run side by side for comparison without one
clobbering the other's files.

- **Simple (`sync_calendar.py`):** every run fully replaces each listing's
  cached calendar with whatever the API returns right now. No history of
  what a previous pull looked like. Use for "what does the calendar look
  like right now" workflows.
- **History-keeping (`sync_calendar_history.py`):** same data, but every
  night's prior pull is preserved as a dated snapshot before being
  overwritten. Use when a workflow needs to look back -- "what was this
  listing showing as available on 2026-07-15," a gap-night audit comparing
  pulls over time, etc.

### API key setup

Same key file as the other modes -- no need for a separate key.

### Mode: Calendar (simple)

```
python3 scripts/sync_calendar.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data --selftest
```

2 calls total (1 listings page via `next()` on a `per_page=1` generator, 1
short 7-day `price_calendar` call) -- stays fast regardless of portfolio
size. A 404 means the endpoint path needs a look before a full sync.

**Full sync (also the nightly/scheduled command):**

```
python3 scripts/sync_calendar.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data --verbose
```

Flags:
- `--days N` -- how many days forward from today to pull per listing
  (default **365**). The API defaults to ~1.5 years and allows up to a
  3-year total range with explicit dates -- raise `--days` (e.g. `--days 545`)
  for far-future event/holiday checks.
- `--include-inactive`, `--owned-only`, `--verbose` -- same meaning as the
  Listings+KPIs mode.
- `--force`, `--date` -- see shared resume section above.

**Timing:** 1 call per listing, no pagination -- cheaper than the KPI sync's
2 calls/listing. At ~1.2s pacing, a 47-listing portfolio takes roughly `47 *
1.2` ≈ 56s from scratch, which can still exceed a ~45s shell cap. Re-run the
identical command if cut off.

#### Output layout

```
wheelhouse_calendar_data/
├── index.json                    # shared sync metadata (merges cleanly if this --out is shared
│                                    with the Listings+KPIs / Reservations modes)
├── listings.json                 # object keyed by "{id}_{channel}" -> full listing record
└── calendar/
    └── {id}_{channel}.json       # {"listing_id","channel","synced_at","sync_date",
                                   #  "start_date","end_date","calendar":[...]}
```

Each `calendar` array entry is a raw row as returned by the API: `stay_date`,
`price`, `currency`, `is_available`, `is_booked`, `block_time`,
`reservation_id`, `created_at`, `unit_number`. Rows are **not** split or
grouped by `unit_number` on write -- a multi-unit listing shows one row per
unit per date in the same array (`unit_number: 0` for single-unit listings).
Group by `unit_number` when *reading*.

#### Consumer pattern

Check `index.json`'s `last_sync.calendar` / `last_sync.calendar_sync_date`
first. Resolve a listing's `{id}_{channel}` key from `listings.json`, then
read `calendar/{id}_{channel}.json` directly. Fall back to a live call if the
cache is missing or stale. This file only ever contains the **latest** pull
-- there's no way to recover an earlier calendar state from this mode's
cache; that's what the history-keeping mode is for.

### Mode: Calendar (history-keeping)

```
python3 scripts/sync_calendar_history.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data_history --selftest
```

Same 2-call selftest as the simple mode.

**Full sync (also the nightly/scheduled command):**

```
python3 scripts/sync_calendar_history.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data_history --verbose
```

Flags identical to the simple mode, plus:
- **`--prune-older-than-days N`** -- delete `snapshots/{date}/` folders
  older than `N` days. **Default: unset, meaning keep every snapshot
  forever** -- retaining history is this mode's entire purpose, nothing is
  deleted unless explicitly asked. Only pass this if snapshots past a
  certain age genuinely aren't needed (e.g. `--prune-older-than-days 180`
  caps growth at roughly six months).
- `--verbose` here also prints `ROTATED` lines showing what got archived
  where.
- `--force` here is safe to use: it still rotates whatever was in
  `current/` before overwriting, so a forced same-day re-run never silently
  drops data -- it just means `snapshots/{today}/` ends up holding the
  pre-force version instead of a prior day's.

#### How the history mechanism works

Two locations under `--out`:
- **`current/{id}_{channel}.json`** -- always the most recent pull for that
  listing. A stable path other skills can read without knowing which date's
  pull is "latest."
- **`snapshots/{YYYY-MM-DD}/{id}_{channel}.json`** -- the calendar exactly as
  it stood in `current/` right before being superseded, filed under the date
  **it was originally pulled** (not the date it got moved out).

Each run, per listing: if `current/{key}.json` exists and its own
`sync_date` doesn't already match today (or `--force` is set), the script
(1) fetches the fresh calendar, and only once that succeeds, (2) **moves**
(not copies) the existing `current/{key}.json` into
`snapshots/{its own sync_date}/{key}.json`, then (3) writes the fresh pull
into `current/{key}.json`. A given pull always lives in exactly one of the
two places. **Rotation only happens after a successful fetch, never
before** -- a failed API call for a listing leaves that listing's `current/`
(and all its history) completely untouched.

**Timing:** 1 call per listing, no pagination -- same as the simple mode.
~56s from scratch for 47 listings, can exceed a ~45s shell cap; re-run if
cut off.

#### Output layout

```
wheelhouse_calendar_data_history/
├── index.json                          # shared sync metadata
├── listings.json                       # object keyed by "{id}_{channel}" -> full listing record
├── current/
│   └── {id}_{channel}.json             # latest pull only -- same shape as the simple mode's file
└── snapshots/
    └── {YYYY-MM-DD}/                   # one folder per date a pull was superseded FROM
        └── {id}_{channel}.json         # same shape as current/, frozen at that pull
```

Same per-row calendar fields as the simple mode.

#### Consumer pattern

For "what does this listing's calendar look like right now," read
`current/{id}_{channel}.json`. For "what did it look like as of a specific
past date," look for the closest snapshot **at or before** that date under
`snapshots/`. A snapshot is created every time a new day's sync runs
(regardless of whether the data actually changed), so `snapshots/{date}/{key}.json`
reliably represents "the calendar as pulled on `{date}`" for every date the
sync ran successfully -- not only dates where something changed. List the
`snapshots/` directory to discover which dates have coverage rather than
assuming every date has one. Fall back to a live call if the cache is
missing or stale.

### Confirmed API facts (both calendar modes)

`GET /listings/{listing_id}/price_calendar` -- path param `listing_id`,
required query param `channel`, optional `start_date`/`end_date`
(YYYY-MM-DD). When omitted, defaults to today through the maximum calendar
horizon (1.5 years); total requested range may not exceed 3 years. **No
pagination** on this endpoint -- the whole requested range comes back as a
single response. Confirmed real response fields per row: `stay_date`,
`price`, `currency`, `is_available`, `is_booked`, `block_time`,
`reservation_id`, `created_at`, `unit_number`. Past dates reflect what
actually happened; future dates reflect the current state as of the request.
Verified against the connected Wheelhouse MCP's live tool schema and a real
test call on 2026-08-04.

### Running either calendar mode from a scheduled/unattended task

A scheduled/unattended firing gets a fresh, isolated sandbox with **no
memory of any folder mounted in a previous run** -- even if that folder
mounted successfully every night for months. If `--out`'s parent directory
lives in a folder connected from the user's own device, **the first action
inside every scheduled firing must be to request access to that exact folder
again** (e.g. via this session's device-folder-access tool, such as
`device_request_folder_access` -- check the current tool list rather than
assuming a name) **before** running either calendar script. Skipping this
doesn't fail loudly: the script just can't find `--out` and behaves exactly
like the cache never existed, identical to "there's genuinely no data here
yet." Rule this out explicitly before concluding the cache is stale or
corrupt. If the mount step fails, stop and report that plainly rather than
guessing at a path.

**For the history-keeping mode specifically, mounting isn't enough on its
own** -- getting this wrong doesn't fail loudly, it silently defeats the
entire point of running that mode. The rotation decision depends on seeing
the real `current/{key}.json` already on the device before the script runs.
Before every run against a device-mounted `--out`:

1. Stage the **whole `current/` directory** (every `{id}_{channel}.json`
   file, not a sample) plus `index.json` down into the local scratch
   directory that will serve as `--out`, preserving relative paths
   (`current/{key}.json`, not just `{key}.json`). `snapshots/` does not need
   staging -- the script never reads from it. A portfolio larger than the
   staging tool's per-call file cap needs multiple staging calls -- don't
   silently stage a partial set. **A single batch staging call can silently
   drop a small number of files with a transient error even when the overall
   call "succeeds"** (confirmed live, 2026-08-04) -- always compare the count
   of files that actually landed against the expected listing count (from
   `listings.json` or the prior `index.json`'s `listing_count`), and re-stage
   any specific missing paths individually.
2. Run the script normally against the seeded local directory.
3. Ship the changed output back: zip `current/`, any newly-written
   `snapshots/{today}/` (and any other `snapshots/` subfolders produced this
   run), `index.json`, and `listings.json`; send/commit to **one fixed,
   reused filename** on the device (e.g. `.calendar_sync_scratch.zip`); then
   unpack it **with Python's `zipfile` module**, not the shell `unzip`
   command (the simple mode needs the same zipfile approach for the same
   reason -- see below).

If step 1 is skipped or only partially done (e.g. only staging `index.json`,
which is sufficient for the simple mode but not this one), don't treat a
subsequent "0 rotated" or unexpectedly-empty `snapshots/` result as evidence
nothing needed archiving -- it's the expected symptom of running without
prior state, not a sign the portfolio had nothing to rotate.

### Writing output to a folder reached via a device bridge (both calendar modes)

The script needs live network access, so it runs wherever a real Python
interpreter with network access is available (e.g. this session's cloud
container) -- never via a device-side shell tool, which typically has no
network access. `--out` during a run is necessarily a local scratch
directory; the device folder only enters the picture at the start (reading
prior state) and the end (writing output back).

That bridge typically **cannot delete files** (`rm`/`unlink` on a mounted
path fails with "Operation not permitted"). **Do not shell out to `unzip -o`
(or any tool that deletes-then-recreates a target) against a path reached
this way** -- confirmed failure mode (2026-08-04): `unzip -o` tries to remove
each already-existing file before writing the new one, which the bridge
blocks, aborting the extraction partway through.

**Correct pattern, verified end-to-end against a real 47-listing account:**
run the script locally, zip just the relevant output, send/commit it to one
fixed reused filename on the device, then unpack with:

```python
import zipfile
with zipfile.ZipFile('.calendar_sync_scratch.zip') as z:
    z.extractall('wheelhouse_calendar_data')  # or wherever --out lives on the device
```

`zipfile` extraction opens each target with `open(path, "wb")`
(truncate-and-write) and never calls `unlink`/`remove`, so it overwrites
existing files in place and creates new subdirectories cleanly, without
hitting the device bridge's delete restriction.

### Fix history (calendar modes)

- **2026-08-04 (simple mode, initial build):** Modeled on the already-verified
  same-day-resume / cross-day-refresh design from the Listings+KPIs mode's
  KPI sync. Confirmed `price_calendar`'s parameters and real response shape
  against the connected Wheelhouse MCP and a live test call before writing
  the script. Verified end-to-end with a monkeypatched fake client across
  simulated days: same-day resume skips with zero extra calls, a new day
  refreshes every listing, a failed fetch for one listing never touches its
  existing file.
- **2026-08-04 (simple mode, live account verification + device-write fix):**
  Ran against a 47-listing account: `--selftest` passed, a full sync (47/47,
  0 errors, 17,192 rows, ~59s), and a `--force` re-pull all confirmed
  `index.json` merges cleanly alongside sibling-mode metadata and each
  listing's file genuinely gets replaced with a fresh `synced_at`. Discovered
  shipping to a device-bridge-mounted `--out` via shell `unzip -o` fails
  (bridge blocks the delete calls) and leaves cleanup clutter; replaced with
  the reused-scratch-file + `zipfile.extractall()` pattern above, which
  leaves no leftover artifacts.
- **2026-08-04 (history mode, initial build):** Built as the history-tracking
  counterpart to the simple mode, sharing its same-day-resume /
  cross-day-refresh design and endpoint verification, plus the
  rotate-before-overwrite mechanism for `current/` -> `snapshots/{date}/`.
  Verified end-to-end with a monkeypatched fake client across simulated
  days: day 1 writes `current/` with no snapshots yet; a same-day re-run
  skips with no rotation; a new day rotates the prior pull into
  `snapshots/{that date}/` unchanged and refreshes `current/`; `--force` on
  the same day still rotates the pre-force pull rather than losing it;
  `--prune-older-than-days` removes only date folders older than the
  cutoff; a failed fetch for one listing leaves that listing's `current/`
  and history untouched while others proceed.
- **2026-08-04 (history mode, device-bridge guidance added ahead of a live
  test):** Two things surfaced from live-testing the simple mode that apply
  here too, one more seriously: (1) the same `unzip -o` failure and
  `zipfile.extractall()` fix as the simple mode. (2) **Specific to this
  mode:** since rotation depends on seeing the real `current/{key}.json`
  already on the device, staging only `index.json` (correct for the simple
  mode) would make every listing look like a first-ever sync here, silently
  skipping rotation and overwriting the device's real previous pull with no
  snapshot taken. Documented the fix (stage the whole `current/` directory
  first) based on already-verified rotation logic rather than guessing --
  this mode had not yet been run end-to-end against a real account at this
  point.
- **2026-08-04 (history mode, live-tested end-to-end; staging-flakiness
  quirk discovered):** Ran a full two-day simulation against the same real
  47-listing account used for the simple mode's live test, in a separate
  output folder. Day 1: ran fresh, confirmed `current/` populated for all 47
  listings with no `snapshots/` yet. Staged the full `current/` directory
  plus `index.json` down to a fresh session (simulating a new day with no
  memory of the prior run), then ran Day 2 with `--date` one day later.
  Rotation worked exactly as designed: every listing's Day-1 pull moved
  intact into `snapshots/2026-08-0X/`, `current/` refreshed to Day 2's data,
  and a content-level diff confirmed the archived snapshot genuinely matched
  the original Day-1 pull. This confirms the "stage the full `current/`
  directory" requirement above is correct and necessary. Separately, this
  test surfaced an operational quirk in the staging mechanism itself (not a
  bug in this script): a single batch `device_stage_files` call against the
  47-listing `current/` directory reported success but had silently dropped
  2 of the 47 files (a transient per-file `HTTP 404 adding session file`
  inside an otherwise-successful batch). Only caught by comparing the staged
  file count against the expected listing count before running the script;
  the two missing files were identified by name and re-staged individually.
  Documented as a required verification step above.

---

## Cadence and scheduling (all modes)

Use the `schedule` skill to set up nightly scheduled tasks running the plain
full-sync command for each mode in use (no `--force` needed -- the
cross-day always-refresh behavior already guarantees every listing gets
re-pulled each night). Claude's role in a scheduled run is just to invoke
the script and report its summary, not to process each listing itself.
Backfill (Reservations mode) is a one-time or occasional manual operation --
never wire it into the nightly schedule. For portfolios large enough to risk
exceeding a scheduled runner's execution-time limit, either allow more
wall-clock time or accept that a single scheduled invocation may only get
partway -- the same-day resume behavior means a follow-up invocation (still
no flags needed) finishes the rest before the next night's run rolls the
date over again.
