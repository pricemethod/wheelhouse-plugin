---
name: wheelhouse-calendar-sync-api
description: "Pulls each listing's future price calendar (price, availability, booked/blocked state per date) from Wheelhouse RM and caches it to local files via a direct API key and script -- no MCP/Claude in the loop for the HTTP calls -- so other Wheelhouse skills can read a listing's calendar from disk instead of calling the live API every time. SIMPLE version: each nightly run fully replaces the cached calendar for every listing, no history kept. Use when the user wants to \"sync,\" \"cache,\" \"refresh,\" or \"pull down\" Wheelhouse calendar/availability data with their own RM API key, wants a cheap nightly/scheduled calendar pull, or asks for the \"simple\"/\"replace-only\" calendar sync. Sibling to wheelhouse-calendar-sync-api-history (which snapshots every pull for history -- use that one if the user wants a past date's calendar, not just current). Also sibling to wheelhouse-data-sync-api (listings+KPIs) and wheelhouse-reservations-sync-api (bookings) -- this one is calendar/availability only."
---

# Wheelhouse Calendar Sync -- Direct API Key (Simple / Replace-Only)

Keeps a local cache of each listing's **future price calendar** -- nightly
price, availability, and booked/blocked state per stay date -- on disk, so
other skills (calendar/availability audits, future-rate-overpricing checks,
gap-night reviews, etc.) can read from files instead of calling the API live
every time.

**This is the SIMPLE version.** Every run fully replaces each listing's
cached calendar with whatever the API returns right now -- there is
deliberately no history of what a previous pull looked like. If you want a
dated archive of every night's pull so you can answer "what did this
listing's calendar look like on 2026-07-15," use the sibling
`wheelhouse-calendar-sync-api-history` skill instead. Both skills can be
installed and run at the same time -- they default to different output
folders (`wheelhouse_calendar_data/` here vs.
`wheelhouse_calendar_data_history/` there) specifically so you can compare
them side by side without one clobbering the other's files. Don't run this
skill and its history-keeping sibling against the *same* `--out` directory --
each expects to own its own listings.json/index.json + calendar layout
underneath that path, and pointing both at one folder risks confusing the two
different on-disk formats (`calendar/{key}.json` here vs. `current/{key}.json`
+ `snapshots/` there).

**This is the direct-API-key sibling pattern already used by
`wheelhouse-data-sync-api` (listings+KPIs) and `wheelhouse-reservations-sync-api`
(bookings)** -- same mechanics (plain Python script against the RM REST API,
a user-supplied key, same-day resume / cross-day always-refresh), applied to
calendar/availability data instead. Like those, the point is to keep the
mechanical fetch-and-write work down to a rounding error of Claude usage
instead of the tokens needed to relay a whole portfolio's calendar rows
through the model.

## API key setup -- once, never pasted into chat

Needs a Wheelhouse RM API key with read access (Wheelhouse dashboard ->
profile menu -> API Key -> Revenue Management API Keys -> Create RM Key). If
you already created a key file for the sibling sync skills, this same file
works here too -- no need for a separate key.

1. The user creates a plain text file themselves (in their own file manager,
   not through Claude) containing just the key, one line, no quotes --
   named `wheelhouse_api_key.txt`.
2. Reference that file's path with `--api-key-file` when running the script.
3. Never ask the user to paste the key into a chat message, never type it
   into a tool call, and never `cat`/`Read` the key file's contents.

## Running a sync

**First time, or after any Wheelhouse API change:**

```
python3 scripts/sync_calendar.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data --selftest
```

2 calls total (1 listings page via `next()` on a `per_page=1` generator, 1
short 7-day `price_calendar` call) -- stays fast regardless of portfolio
size. A 404 here means the endpoint path needs a look before running a full
sync.

**Full sync (this is also the nightly/scheduled command -- no extra flags needed):**

```
python3 scripts/sync_calendar.py --api-key-file <path>/wheelhouse_api_key.txt --out <path>/wheelhouse_calendar_data --verbose
```

Flags:
- `--days N` -- how many days forward from today to pull per listing
  (default **365**). The API itself defaults to ~1.5 years and allows up to
  a 3-year total range when you pass explicit dates -- raise `--days` (e.g.
  `--days 545`) if a workflow needs to see further out, such as a
  far-future event/holiday rate check.
- `--include-inactive` -- also pull inactive/delisted listings (default:
  excluded).
- `--owned-only` -- restrict to listings the account owns, excluding
  managed/delegated listings (default: managed listings included).
- `--verbose` -- per-listing progress (`OK` / `SKIP` / `ERROR`).
- `--force` -- ignore each listing's stored sync date and re-fetch every
  listing right now regardless of when it was last synced. Not needed for
  routine nightly runs.
- `--date YYYY-MM-DD` -- override what "today" means (UTC) for the
  same-day-skip check and the start of the forward window. Mainly for
  testing.

## Same-day resume, cross-day always-refresh -- this is what makes nightly runs correct

Same design already verified end-to-end on the sibling `wheelhouse-data-sync-api`
skill's KPI sync, applied identically here: **a nightly sync must always
pull every listing's current calendar.** It must never silently skip a
listing just because a same-named file already exists from a previous
night -- but a single sync attempt that gets cut off partway through
shouldn't have to restart the whole portfolio from scratch on retry either.

Each `calendar/{id}_{channel}.json` file stores a `sync_date` field (the UTC
calendar date the run that wrote it was for) next to `synced_at`. A listing
is skipped **only if its file already exists and that file's `sync_date`
matches today's date**:

- **Same day, second invocation** (resuming a run cut off by a timeout):
  listings already written earlier *today* are skipped instantly.
- **A new day's run** (the actual nightly case): every listing's stored
  `sync_date` is from a prior day, so **nothing is skipped** -- every
  listing gets a fresh pull.

The plain command above (no `--force`) is correct for both the manual-resume
case and the nightly-scheduled case -- the date comparison picks the right
behavior on its own.

**Timing:** this endpoint needs only **1 call per listing** (no pagination,
the whole requested range comes back in one response) -- cheaper than the
sibling KPI sync's 2 calls/listing. At ~1.2s pacing, a 47-listing portfolio
takes roughly `47 * 1.2` ≈ 56s from scratch, which can still exceed a
time-boxed shell's ~45s cap. If a run gets cut off, just re-run the
identical command; already-done listings for today skip in a fraction of a
second.

After running, read back the script's printed summary (listings count,
calendars synced/freshly-fetched/already-done, rows fetched, any errors) and
relay a short version to the user. Name any listings that errored.

## Output layout

```
wheelhouse_calendar_data/
├── index.json                    # shared sync metadata (merges cleanly if this --out is shared
│                                    with wheelhouse-data-sync-api / wheelhouse-reservations-sync-api)
├── listings.json                 # object keyed by "{id}_{channel}" -> full listing record
└── calendar/
    └── {id}_{channel}.json       # {"listing_id","channel","synced_at","sync_date",
                                   #  "start_date","end_date","calendar":[...]}
```

Calendar data is one file per listing (not one bundled portfolio file), same
reasoning as the KPI/reservations siblings: a single-listing question only
touches one small file, and the filename stays stable regardless of which
night's sync last wrote it -- freshness lives in the `sync_date`/`synced_at`
fields inside the file, not in the filename. `listings.json` is always fully
rewritten (small, cheap). `index.json` is read-modify-written, so it's safe
to point this at the same `--out` already used by the sibling data/reservations
sync skills -- the calendar-specific keys (`last_sync.calendar`,
`calendar_sync_errors`, `calendar_window_days`) merge in alongside theirs
rather than clobbering them.

Each `calendar` array entry is a raw row as returned by the API:
`stay_date`, `price`, `currency`, `is_available`, `is_booked`, `block_time`,
`reservation_id`, `created_at`, `unit_number`. Rows are **not** split or
grouped by `unit_number` on write -- for a multi-unit listing you'll see one
row per unit per date in the same array (`unit_number: 0` for single-unit
listings). Group by `unit_number` when *reading*, per the project's general
multi-unit guidance, rather than assuming one row per date.

## Confirmed API facts this script relies on

Verified directly against the connected Wheelhouse MCP's live tool schema
and a real test call against a real account on 2026-08-04:
- `GET /listings/{listing_id}/price_calendar` -- path param `listing_id`,
  required query param `channel`, optional `start_date`/`end_date`
  (YYYY-MM-DD). When omitted, the API defaults to today through its maximum
  calendar horizon (1.5 years); the total requested range may not exceed 3
  years.
- **No pagination** on this endpoint -- confirmed the whole requested range
  comes back as a single response, unlike the paginated `/listings` list
  endpoint.
- Confirmed real response fields per row: `stay_date`, `price`, `currency`,
  `is_available`, `is_booked`, `block_time`, `reservation_id`, `created_at`,
  `unit_number`. Past dates reflect what actually happened (booked/blocked/
  available and the price in effect at the time); future dates reflect the
  current state as of the request.
- Auth, rate limit (60/min), and `/listings` pagination/params are identical
  to the sibling `wheelhouse-data-sync-api` skill -- see that skill's
  SKILL.md for the fuller writeup; not re-derived here.

## Consumer pattern (for other skills reading this cache)

Check `wheelhouse_calendar_data/index.json`'s `last_sync.calendar` /
`last_sync.calendar_sync_date` for freshness first. For a specific listing,
resolve its `{id}_{channel}` key from `listings.json`, then read
`calendar/{id}_{channel}.json` directly -- don't read every file in
`calendar/` unless the question is genuinely portfolio-wide. A consuming
skill that cares whether a listing's calendar is from today specifically
(not just "present") should check that file's own `sync_date`, not assume
freshness from the file's mere existence. If the cache is missing or stale
for the question, fall back to a live call (via this script or the MCP)
rather than failing the user's question outright. Remember this file only
ever contains the **latest** pull -- there is no way to recover what the
calendar looked like on an earlier date from this skill's cache; that's what
the history-keeping sibling is for.

## Cadence and scheduling

Set this up as a nightly scheduled task (via the product's scheduled-task
feature) running the plain full-sync command above -- no `--force` needed,
since the cross-day always-refresh behavior already guarantees every
listing gets re-pulled each night. Claude's role in a scheduled run is just
to invoke the script and report its summary, not to process each listing
itself. For portfolios large enough to risk exceeding the scheduled
runner's execution-time limit, either allow more wall-clock time or accept
that a single scheduled invocation may only get partway -- the same-day
resume behavior means a follow-up invocation (still no flags needed) will
finish the rest before the next night's run rolls the date over again.

### Running this from a scheduled/unattended task

A scheduled/unattended firing gets a fresh, isolated sandbox with **no
memory of any folder mounted in a previous run** -- even if that folder
mounted successfully every night for months. If `--out`'s parent directory
lives in a folder connected from the user's own device (rather than
somewhere already durable inside this environment), **the first action
inside every scheduled firing of this skill must be to request access to
that exact folder again** (e.g. via this session's device-folder-access
tool, such as `device_request_folder_access` -- check the current tool list
rather than assuming a name, since it can vary) **before** running
`sync_calendar.py`. Skipping this doesn't fail loudly: the script just can't
find `--out` and behaves exactly like the cache never existed, which looks
identical to "there's genuinely no data here yet." Rule this out explicitly
before concluding the cache is stale or corrupt. If the mount step fails,
stop and report that plainly rather than guessing at a path.

### Writing output to a folder reached via a device bridge

If `--out` lives inside a folder on the user's own computer rather than
somewhere already durable inside this environment, the script still has to
run wherever a real Python interpreter is available (e.g. this session's
cloud container) and its output then has to be written back to that device
folder over a bridge. That bridge typically **cannot delete files**
(`rm`/`unlink` on a mounted path fails with "Operation not permitted") --
this matters a lot for a skill like this one that overwrites the same
filenames every single run.

**Do not shell out to `unzip -o` (or any tool that deletes-then-recreates a
target) against a path reached this way.** Confirmed failure mode
(2026-08-04): `unzip -o` tries to remove each already-existing file before
writing the new one, which the bridge blocks, aborting the whole extraction
partway through.

**Correct pattern, verified end-to-end against a real 47-listing account:**
1. Run the script locally, producing `calendar/`, `listings.json`, and
   `index.json` under a local `--out`.
2. Zip just that output and send/commit it to **one fixed, reused filename**
   on the device (e.g. `.calendar_sync_scratch.zip`) -- reusing the name
   every run means nothing accumulates, unlike a fresh temp filename each
   time.
3. Unpack it **with Python's `zipfile` module** (via whatever shell access
   reaches the device), not the `unzip` command:
   ```python
   import zipfile
   with zipfile.ZipFile('.calendar_sync_scratch.zip') as z:
       z.extractall('wheelhouse_data')  # or wherever --out lives on the device
   ```
   `zipfile` extraction opens each target with `open(path, "wb")`
   (truncate-and-write) and never calls `unlink`/`remove`, so it overwrites
   `index.json`, `listings.json`, and every `calendar/{key}.json` in place
   without hitting the delete restriction -- and it creates any new
   subdirectory (like `calendar/` on a first-ever run) without issue too.

A first attempt at this (shipped 2026-08-04, before the pattern above was
worked out) used shell `unzip -o` into a temp folder, then `cp` each file
over the real target, then moved the leftover temp zip/folder into a
`_to_delete/` folder since they couldn't be removed outright. That version
worked but left growing clutter behind after every run -- avoid it now that
the reused-scratch-file + `zipfile.extractall()` approach above is known to
work with zero leftover artifacts.

## Fix history

- **2026-08-04 (initial build):** Modeled directly on the already-verified
  same-day-resume / cross-day-refresh design from `wheelhouse-data-sync-api`'s
  KPI sync. Confirmed the `price_calendar` endpoint's parameters and real
  response shape against the connected Wheelhouse MCP and one live test call
  before writing the script (rather than guessing from docs alone -- the
  live API reference's Calendar section didn't fully render during
  research). Verified end-to-end with a monkeypatched fake client across
  simulated days: same-day resume skips with zero extra calls, a new day
  refreshes every listing, and a failed fetch for one listing never touches
  its existing file.
- **2026-08-04 (live account verification + device-write fix):** Ran the
  script for real against a 47-listing account: `--selftest` passed first
  (confirmed the direct REST endpoint's fields match the MCP tool's exactly),
  then a full sync (47/47 listings, 0 errors, 17,192 rows, ~59s) and a
  `--force` re-pull, both confirming `index.json` merges cleanly alongside
  the sibling skills' existing metadata and that each listing's calendar
  file genuinely gets replaced in place with a fresh `synced_at`. Along the
  way, discovered that shipping output to a device-bridge-mounted `--out`
  via shell `unzip -o` fails (the bridge blocks the delete calls `unzip -o`
  makes) and leaves cleanup clutter behind as a workaround; replaced with
  the reused-scratch-file + `zipfile.extractall()` pattern documented above,
  which leaves no leftover artifacts. This section was added directly in
  response to a real user flagging the clutter as unwanted friction.
