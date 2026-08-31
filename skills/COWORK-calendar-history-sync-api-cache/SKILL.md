---
name: COWORK-calendar-history-sync-api-cache
description: "Pulls each listing's future price calendar (price, availability, booked/blocked state per date) from Wheelhouse RM and caches it to local files via a direct API key and script -- no MCP/Claude in the loop for the HTTP calls. HISTORY-KEEPING version: alongside the latest pull, every night's previous pull is preserved as a dated snapshot, so you can answer \"what did this listing's calendar look like as of a past date.\" Use when the user wants to \"sync,\" \"cache,\" \"archive,\" or \"track changes to\" Wheelhouse calendar/availability data over time, wants a nightly/scheduled calendar pull that keeps history, or asks for the \"history\"/\"snapshot\"/\"complex\" calendar sync. Sibling to wheelhouse-calendar-sync-api, the simpler replace-only version with no history -- use that one if the user only needs the current calendar. Also sibling to wheelhouse-data-sync-api (listings+KPIs) and wheelhouse-reservations-sync-api (bookings) -- this one is calendar/availability only."
---

# Wheelhouse Calendar Sync -- Direct API Key (History-Keeping)

Keeps a local cache of each listing's **future price calendar** -- nightly
price, availability, and booked/blocked state per stay date -- on disk, the
same as the sibling `wheelhouse-calendar-sync-api` skill, but this version
additionally **preserves every night's pull as a dated snapshot** instead of
overwriting it in place. Use this when a workflow needs to look back --
"what was this listing showing as available on 2026-07-15," "did this
night's price change between last week's pull and today's," a gap-night
audit that wants to compare pulls over time, etc.

**Uses a different default `--out` than the simple sibling on purpose**
(`wheelhouse_calendar_data_history/` here vs. `wheelhouse_calendar_data/`
there), specifically so **both skills can be run side by side against the
same parent directory at the same time** -- e.g. for testing/comparison --
without one clobbering the other's files. Don't point this skill and its
simple sibling at the *same* `--out` value -- each owns a different on-disk
layout underneath that path (`current/` + `snapshots/` here vs. a flat
`calendar/` there) and mixing them risks confusing the two formats.

**This is the direct-API-key sibling pattern already used by
`wheelhouse-data-sync-api` (listings+KPIs) and `wheelhouse-reservations-sync-api`
(bookings)** -- same mechanics (plain Python script against the RM REST API,
a user-supplied key, same-day resume / cross-day always-refresh), extended
with a rotate-to-history step that those two skills don't need.

## API key setup

Same as the sibling skills: a plain text file, one line, no quotes,
`wheelhouse_api_key.txt`, created by the user themselves, referenced via
`--api-key-file`. Never ask for it in chat, never type it into a tool call,
never read its contents. Reuse the same key file the sibling sync skills
use if the user already set one up -- no need for a separate key.

## Running a sync

**First time, or after any Wheelhouse API change:**

```
python3 scripts/sync_calendar_history.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data_history --selftest
```

2 calls total (1 listings page via `next()` on a `per_page=1` generator, 1
short 7-day `price_calendar` call). A 404 here means the endpoint path needs
a look before running a full sync.

**Full sync (this is also the nightly/scheduled command -- no extra flags needed):**

```
python3 scripts/sync_calendar_history.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data_history --verbose
```

Flags (all identical to the simple sibling except the last one):
- `--days N` -- how many days forward from today to pull per listing
  (default **365**). Every night's snapshot is roughly this size per
  listing, so a larger window directly multiplies disk usage per night --
  keep this in mind before raising it across a large portfolio.
- `--include-inactive` / `--owned-only` -- same meaning as the sibling skill.
- `--verbose` -- per-listing progress, including `ROTATED` lines showing
  what got archived where.
- `--force` -- ignore the same-day skip and re-fetch/rotate every listing
  right now. Safe to use: it still rotates whatever was in `current/`
  before overwriting, so forcing a same-day re-run never silently drops
  data (see below).
- `--date YYYY-MM-DD` -- override "today" for the skip check, the rotation
  folder name, and the start of the forward window. Mainly for testing.
- **`--prune-older-than-days N`** -- delete `snapshots/{date}/` folders
  older than `N` days. **Default: unset, meaning keep every snapshot
  forever** -- retaining history is this skill's entire purpose, so nothing
  is deleted unless you explicitly ask. Only pass this if you've decided
  you genuinely don't need snapshots past a certain age (e.g. `--prune-older-than-days 180`
  to cap growth at roughly six months of nightly history).

## How the history mechanism works

Two locations under `--out`:
- **`current/{id}_{channel}.json`** -- always the most recent pull for that
  listing. A stable path other skills can read without needing to know
  which date's pull is "latest."
- **`snapshots/{YYYY-MM-DD}/{id}_{channel}.json`** -- the calendar exactly
  as it stood in `current/` right before being superseded, filed under the
  date **it was originally pulled** (not the date it got moved out).

Each run, per listing: if `current/{key}.json` exists and its own
`sync_date` doesn't already match today (or `--force` is set), the script
(1) fetches the fresh calendar, and only once that succeeds, (2) **moves**
(not copies) the existing `current/{key}.json` into
`snapshots/{its own sync_date}/{key}.json`, then (3) writes the fresh pull
into `current/{key}.json`. A given pull always lives in exactly one of the
two places -- nothing is ever duplicated. **Rotation only happens after a
successful fetch, never before** -- a failed API call for a listing leaves
that listing's `current/` (and all its history) completely untouched rather
than risking data loss to a call that never landed.

## Same-day resume, cross-day always-refresh

Same requirement and design as the simple sibling and the KPI sync it's
modeled on: a nightly run must always pull every listing's current
calendar, never silently skip one just because `current/{key}.json` already
exists -- but a truncated run shouldn't have to restart the whole portfolio
from scratch. A listing is skipped only if `current/{key}.json` exists
**and** its `sync_date` matches today's date (or `--date`):
- **Same day, second invocation:** listings already rotated+refreshed
  earlier today are skipped instantly, with no rotation and no new fetch.
- **A new day's run:** every listing's recorded `sync_date` predates today,
  so nothing is skipped -- every listing gets rotated then refreshed.
- **`--force` on the same day:** bypasses the skip. Whatever was already in
  `current/` (even if it's today's own earlier pull) gets rotated into
  `snapshots/{today}/` before being overwritten, so a forced same-day re-run
  still can't silently lose data -- it just means `snapshots/{today}/` ends
  up holding the pre-force version instead of a prior day's.

**Timing:** 1 call per listing (no pagination). At ~1.2s pacing, a
47-listing portfolio takes roughly `47 * 1.2` ≈ 56s from scratch, which can
exceed a time-boxed shell's ~45s cap. If a run gets cut off, re-run the
identical command -- already-rotated-and-refreshed listings for today skip
in a fraction of a second.

After running, relay the script's printed summary (listings total,
freshly-fetched/skipped/rotated counts, rows fetched, any pruning, any
errors) to the user rather than just saying "done."

## Output layout

```
wheelhouse_calendar_data_history/
├── index.json                          # shared sync metadata
├── listings.json                       # object keyed by "{id}_{channel}" -> full listing record
├── current/
│   └── {id}_{channel}.json             # latest pull only -- {"listing_id","channel","synced_at",
│                                        #  "sync_date","start_date","end_date","calendar":[...]}
└── snapshots/
    └── {YYYY-MM-DD}/                   # one folder per date a pull was superseded FROM
        └── {id}_{channel}.json         # same shape as current/, frozen at that pull
```

Same per-row calendar fields as the simple sibling: `stay_date`, `price`,
`currency`, `is_available`, `is_booked`, `block_time`, `reservation_id`,
`created_at`, `unit_number` -- raw as returned, not split by unit. Group by
`unit_number` when reading a multi-unit listing's rows.

## Confirmed API facts this script relies on

Identical to the simple sibling skill -- see its SKILL.md for the full
writeup of `GET /listings/{listing_id}/price_calendar`'s params, defaults
(today through 1.5y, 3y max range), lack of pagination, and confirmed
response fields, all verified against the connected Wheelhouse MCP's live
tool schema and a real test call on 2026-08-04. Not re-derived here to avoid
drift between the two skills' docs -- if one is updated after an API
change, update both.

## Consumer pattern (for other skills reading this cache)

For "what does this listing's calendar look like right now," read
`current/{id}_{channel}.json` exactly like the simple sibling's
`calendar/{id}_{channel}.json`. For "what did it look like as of a specific
past date," look for the closest snapshot **at or before** that date under
`snapshots/`. A snapshot is created every time a new day's sync runs
(regardless of whether the underlying data actually changed since the last
pull), so `snapshots/{date}/{key}.json` reliably represents "the calendar as
pulled on `{date}`" for every date the sync ran successfully -- not only
dates where something changed. List the `snapshots/` directory to discover
which dates have coverage rather than assuming every calendar date has one
(a date the sync was skipped, errored on, or wasn't running yet won't have a
snapshot). If the cache is missing or stale for the question, fall back to a
live call rather than failing the question outright.

## Cadence and scheduling

Set this up as a nightly scheduled task (via the product's scheduled-task
feature) running the plain full-sync command above -- no `--force` needed.
For portfolios large enough to risk exceeding the scheduled runner's
execution-time limit, either allow more wall-clock time or accept that a
single scheduled invocation may only get partway -- the same-day resume
behavior means a follow-up invocation finishes the rest before the next
night's run rolls the date over again.

### Running this from a scheduled/unattended task

A scheduled/unattended firing gets a fresh, isolated sandbox with **no
memory of any folder mounted in a previous run.** If `--out`'s parent
directory lives in a folder connected from the user's own device, **the
first action inside every scheduled firing of this skill must be to request
access to that exact folder again** (e.g. via this session's
device-folder-access tool, such as `device_request_folder_access` -- check
the current tool list rather than assuming a name) **before** running
`sync_calendar_history.py`. If the mount step fails, stop and report that
plainly rather than guessing at a path or letting the script run against the
wrong (empty) location. Requesting access is necessary but **not
sufficient** by itself here -- see the next section for the additional step
this skill specifically needs beyond what the simple sibling requires.

### Writing output to (and reading state from) a folder reached via a device bridge

**This section matters much more for this skill than for the simple
sibling, and getting it wrong doesn't fail loudly -- it silently defeats the
entire point of running this skill.**

The script needs live network access to call the Wheelhouse API, so it has
to run wherever a real Python interpreter *with network access* is
available (this session's cloud container) -- never via a device-side shell
tool, since those typically have no network access at all. That means the
script's `--out` during a run is necessarily a *local* scratch directory in
the cloud container, not the user's actual device folder directly. The
device folder only enters the picture at the beginning (reading prior
state) and the end (writing fresh output back).

**The critical part: before running the script, stage down the ENTIRE
existing `current/` directory from the device -- not just `index.json`.**
The rotation logic (see "How the history mechanism works" above) decides
whether to rotate a listing's previous pull into `snapshots/{date}/` by
checking whether `current/{key}.json` already exists **in the directory the
script is actually running against**. If the local scratch directory is
only seeded with `index.json` (which is all the *simple* sibling skill
needs, since it only cares about merging shared metadata, not deciding what
to archive), every listing looks like it's being synced for the very first
time -- no rotation happens, and when the freshly-fetched output gets
shipped back to the device, it silently **overwrites the real
`current/{key}.json` on the device without ever archiving what was there**.
The previous night's pull is gone, not because the script has a bug, but
because it was never shown the data it needed to protect. This is exactly
the mistake to avoid: staging just `index.json` is correct for the simple
skill's needs and wrong for this one.

Concretely, before every run against a device-mounted `--out`:
1. Stage the **whole `current/` directory** (every `{id}_{channel}.json`
   file in it, not a sample) plus `index.json` down into the local scratch
   directory that will serve as `--out`, preserving the same relative paths
   (`current/{key}.json`, not just `{key}.json`). `snapshots/` does **not**
   need to be staged -- the script only ever reads from `current/`, never
   from `snapshots/`, so omitting it doesn't affect correctness (it just
   means this run's `snapshots/` output will only contain what got rotated
   *this* run, which is fine to ship back additively). A portfolio with more
   than the staging tool's per-call file cap needs more than one staging
   call to cover every listing -- don't silently stage a partial set and
   proceed. **Confirmed live (2026-08-04): a single batch staging call can
   silently drop a small number of files with a transient error even when
   the overall call "succeeds"** -- after staging, always compare the count
   of files that actually landed locally against the count of listings
   expected (from `listings.json` or the prior `index.json`'s
   `listing_count`), and re-stage any specific missing paths individually
   before running the script. Don't treat a batch stage call's lack of a
   top-level error as proof every file arrived.
2. Run the script normally against that seeded local directory.
3. Ship the changed output back using the same pattern as the simple
   sibling: zip `current/`, any newly-written `snapshots/{today}/` (and any
   other `snapshots/` subfolders produced this run), `index.json`, and
   `listings.json`; send/commit that zip to **one fixed, reused filename**
   on the device (e.g. `.calendar_sync_scratch.zip`); then unpack it **with
   Python's `zipfile` module**, not the shell `unzip` command:
   ```python
   import zipfile
   with zipfile.ZipFile('.calendar_sync_scratch.zip') as z:
       z.extractall('wheelhouse_calendar_data_history')  # or wherever --out lives on the device
   ```
   `zipfile` extraction opens each target with `open(path, "wb")`
   (truncate-and-write) and never calls `unlink`/`remove`, so it overwrites
   `current/{key}.json` and `index.json`/`listings.json` in place, and
   creates new `snapshots/{date}/` subfolders cleanly, without hitting the
   device bridge's restriction on deleting mounted files (confirmed on the
   simple sibling skill: shelling out to `unzip -o` fails there, since it
   deletes-then-recreates existing targets before writing).

If step 1 is skipped or only partially done (e.g. only staging `index.json`
the way the simple sibling's process does), don't treat a subsequent
"0 rotated" or unexpectedly-empty `snapshots/` result as evidence that
nothing needed archiving -- it's the expected symptom of running the script
without its prior state, not a sign the portfolio genuinely had nothing to
rotate.

## Fix history

- **2026-08-04 (initial build):** Built as the history-tracking sibling of
  `wheelhouse-calendar-sync-api`, sharing its same-day-resume /
  cross-day-refresh design and endpoint verification, plus a rotate-before-
  overwrite mechanism for `current/` -> `snapshots/{date}/`. Verified
  end-to-end with a monkeypatched fake client across simulated days: day 1
  writes `current/` with no snapshots yet; a same-day re-run skips with no
  rotation; a new day rotates the prior pull into `snapshots/{that date}/`
  unchanged and refreshes `current/`; `--force` on the same day still
  rotates the pre-force pull rather than losing it; `--prune-older-than-days`
  correctly removes only date folders older than the cutoff; and a failed
  fetch for one listing leaves that listing's `current/` and history
  completely untouched while other listings in the same run proceed
  normally.
- **2026-08-04 (device-bridge write/read guidance added, ahead of a live
  account test):** After live-testing the simple sibling skill against a
  real 47-listing account, two things surfaced that apply here too, one of
  them more seriously: (1) shipping output to a device-mounted `--out` via
  shell `unzip -o` fails, because the bridge blocks the delete calls it
  makes -- fixed by using a reused scratch filename plus Python's
  `zipfile.extractall()` instead, which overwrites in place with no
  leftover clutter (same fix as the simple sibling). (2) **Specific to this
  skill:** because the rotation decision depends on seeing the real
  `current/{key}.json` already on the device, staging only `index.json`
  before a run (correct for the simple sibling, which doesn't need to see
  prior per-listing state) would make every listing look like a first-ever
  sync here -- silently skipping rotation and overwriting the device's real
  previous pull with no snapshot taken. Documented the fix (stage the whole
  `current/` directory first, not just `index.json`) based on this script's
  already-verified rotation logic (see the entry above) rather than
  guessing. This skill has not yet been run end-to-end against a real
  Wheelhouse account the way the simple sibling has -- that live test,
  including confirming the staging step works as described here, is still
  outstanding.
- **2026-08-04 (live-tested end-to-end against a real 47-listing account;
  staging-flakiness quirk discovered and documented):** Ran a full two-day
  simulation against the real account used for the simple sibling's live
  test, in a separate output folder
  (`wheelhouse_calendar_data_history/`) so both skills' data could coexist.
  Day 1: staged the API key, ran the script fresh, confirmed `current/`
  populated for all 47 listings with no `snapshots/` yet. Staged the full
  `current/` directory plus `index.json` back down to a fresh session
  (simulating a new day with no memory of the prior run, per the guidance
  above), then ran Day 2 with `--date` one day later. Rotation worked
  exactly as designed: every listing's Day-1 pull moved intact into
  `snapshots/2026-08-0X/`, `current/` refreshed to Day 2's data, and a
  content-level diff (`synced_at`, `sync_date`, and calendar row values)
  confirmed the archived snapshot genuinely matched the original Day-1 pull
  rather than being clobbered or duplicated. This confirms the "stage the
  full `current/` directory, not just `index.json`" requirement above is
  correct and necessary -- a run without it would have shown 0 rotations
  and silently overwritten the device's real history.
  Separately, this test surfaced an operational quirk in the staging
  mechanism itself (not a bug in this script): a single batch
  `device_stage_files` call against the 47-listing `current/` directory
  reported success but had silently dropped 2 of the 47 files (a transient
  per-file `HTTP 404 adding session file` inside an otherwise-successful
  batch). This was only caught by comparing the staged file count against
  the expected listing count before running the script; the two missing
  files were identified by name and re-staged individually. Documented as a
  required verification step in the device-bridge section above -- always
  check staged-file count against expected listing count before trusting a
  batch stage as complete.
