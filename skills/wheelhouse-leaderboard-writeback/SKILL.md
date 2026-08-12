---
name: wheelhouse-leaderboard-writeback
description: "Turns wheelhouse-leaderboard's CSVs into Wheelhouse Tags (all prefixed AI - so they sort together) and one consolidated Note per flagged listing, via the RM API write endpoints (PUT /tags, POST/PUT /notes) using a separate WRITE-ACCESS key. Applies up to 6 tags: Pacing - Behind LY, Expiring Inventory - High Risk, Market Flag - Underperforming, Floor Flag - High, YoY Flag - Declined YoY, Urgent Attention - High. Any listing with at least one tag gets a Base Price/Calendar note dated today with a reminder for tomorrow, summarizing triggered flags and key numbers. Every --apply run also removes any AI tag no longer earned (live fetch-then-merge against Wheelhouse, never a local file) so tags never pile up. Use when the user wants to write back, push, apply, or sync leaderboard flags into Wheelhouse as tags/notes, wants findings visible on listings themselves, or wants to automate tagging at-risk listings after running wheelhouse-leaderboard. Run wheelhouse-leaderboard first if its CSVs aren't on disk."
---

# Wheelhouse Leaderboard Writeback -- Tags + Notes

Piggybacks directly on `wheelhouse-leaderboard`'s output: reads its CSVs,
decides which of 6 fixed tags each listing has earned, and for every listing
that earns at least one, writes both the tags and a single consolidated Note
back onto that listing in Wheelhouse -- so the leaderboard's findings live on
the listing itself (visible to anyone in the Wheelhouse app), not just in a
CSV only this skill's user sees. **On every `--apply` run it also removes any
of its own tags that are no longer earned**, so this never turns into a
one-way ratchet that just accumulates stale flags forever.

**This is a direct-API-key skill, not an MCP-orchestrated one** -- like
`wheelhouse-data-sync-api` / `wheelhouse-notes-export`, all the arithmetic and
every HTTP call happens in a plain Python script, so applying tags/notes
across a large portfolio costs a rounding error of Claude usage rather than
the tokens needed to relay every tag/note payload through the model.

## Prerequisites

1. **`wheelhouse-leaderboard` must have already run** against a data
   directory, producing at minimum `leaderboard_combined.csv` in that
   directory's `leaderboards/` output. If it hasn't, run that skill first --
   this skill never recomputes pacing, risk, market, floor, or YoY numbers
   itself, it only reads what that skill already wrote.
2. `leaderboard_expiring_inventory.csv` and `leaderboard_market_position.csv`
   from the same run are used for two extra detail fields the combined sheet
   doesn't carry (see the tag table below). Both are optional -- if either is
   missing, this skill still tags/notes correctly, it just shows `n/a` for
   the detail fields those specific files would have supplied.

## Setup: a separate WRITE-ACCESS API key

This skill needs to call `PUT`/`POST` endpoints, which a read-only RM API key
cannot do (403 Forbidden). **Do not reuse the read-only key file** the sync
skills (`wheelhouse-data-sync-api`, `wheelhouse-notes-export`, etc.) use --
create a distinct key file for this skill, clearly labeled, so it's obvious
at a glance which key on disk can write and which can only read:

1. In the Wheelhouse dashboard: profile menu -> API Key -> Revenue Management
   API Keys -> Create RM Key. Make sure this key is **not** marked read-only.
2. The user creates the file themselves (their own file manager, never
   through Claude): plain text, one line, just the key, no quotes. Name it
   something unambiguous, e.g. `wheelhouse_api_key_WRITE_ACCESS.txt`, and
   place it in the connected Cowork folder.
3. Never ask the user to paste the key into chat, never type it into a tool
   call, never `Read`/`cat` the file's contents -- pass its path to
   `--api-key-file` and let the script read it directly.

## The 6 tags

Every tag is computed from `leaderboard_combined.csv`'s own flag columns --
nothing here is a new threshold, it's a direct read of what
`wheelhouse-leaderboard` already decided. Every tag name carries a fixed
`AI - ` prefix so they sort together and are instantly recognizable as
this skill's own in the Wheelhouse UI:

| Tag applied | Trigger (from `leaderboard_combined.csv`) | Extra detail pulled from |
|---|---|---|
| `AI - Pacing - Behind LY` | `pace_flag == "Behind LY"` | `pace_delta_pp` (combined) |
| `AI - Expiring Inventory - High Risk` | `expiring_risk_band == "High"` | `available_nights_{smallest window}d`, `pickup_nights_7d`, `rate_delta_pct` (from `leaderboard_expiring_inventory.csv`) |
| `AI - Market Flag - Underperforming` | `market_flag == "Underperforming Market"` | `market_gap_{smallest window}d_pp` (from `leaderboard_market_position.csv`) |
| `AI - Floor Flag - High` | `floor_flag == "High"` | `pct_at_floor` (combined) |
| `AI - YoY Flag - Declined YoY` | `yoy_flag == "Declined YoY"` | `yoy_revpar_delta_pct` (combined) |
| `AI - Urgent Attention - High` | `urgent_band == "High"` | `urgent_score`, `pace_delta_pp`, `market_ratio`, `pct_at_floor`, `yoy_revpar_delta_pct` (all combined) |

**`Expiring Inventory - Medium Risk` was dropped as a trigger (2026-07-29)**
at the user's request -- on a real 47-listing test account it fired on 34 of
47 listings, too broad to be a useful signal. `leaderboard_expiring_inventory.csv`
itself is untouched; this is purely a decision about which `risk_band` values
earn a tag/note here. Easy to re-add if wanted later -- see
`compute_listing_plan` in the bundled script.

### Tag removal, not just addition

Every `--apply` run reconciles **every** listing in the leaderboard (not just
ones flagged today) against its live current tags:

1. `GET /listings/{id}/tags` for the listing.
2. Split the result into tags starting with `AI - ` (owned by this skill,
   safe to touch) vs. everything else (a user's own manual tags -- never
   touched).
3. Compare the `AI - ` tags against today's freshly-computed desired set. If
   they differ at all, `PUT` the reconciled full list
   (`existing_non_ai_tags + desired_ai_tags`, `overwrite: true`) -- this adds
   newly-earned tags **and drops any `AI - ` tag that's no longer earned** in
   the same write. If they already match, no API call is wasted.

This is deliberately a **live** fetch-then-merge, not something driven off a
local file -- the local writeback log described below is an audit trail and a
dry-run preview aid, never the thing an actual write is computed from. That
matters: if a user manually added or removed a Wheelhouse tag by hand between
runs, this skill's next `--apply` still sees the real current state and
reconciles against that, rather than clobbering a manual change based on a
possibly-stale local record.

**Confirmed live** against a real account's tags while building this: `GET
/tags` returns a list of tag *objects* (`{"id", "name", "description",
"type"}`), not bare strings -- while `PUT /tags`'s `names` field wants plain
strings. Merge-add (`overwrite: false`) does not create a duplicate when a
tag name is re-sent that's already present; `overwrite: true` with a
recomputed full list is what performs an actual removal.

`leaderboard_expiring_inventory.csv` and `leaderboard_market_position.csv`
use whatever forward windows `wheelhouse-leaderboard` was run with (default
7/14/30 and 30/60/90 respectively, but user-configurable) -- this script
doesn't hardcode a window number, it discovers the *smallest* available
`available_nights_{W}d` / `market_gap_{W}d_pp` column from each file's own
header row and uses that, matching wheelhouse-leaderboard's own "smallest
window is primary" convention.

## The writeback log (`leaderboard_writeback_log.json`)

A small JSON file this skill maintains at `<data-dir>/leaderboard_writeback_log.json`
(default; override with `--log`), one entry per listing keyed by
`{listing_id}_{channel}`, storing the `AI - ` tags last applied and the date
last checked. Two things it's for:

- **Dry-run removal preview.** Since a plain dry run makes zero API calls, it
  can't live-check current tags -- instead it diffs today's freshly-computed
  desired tags against this log's last-known state, so the plan CSV can show
  "N listings will have a stale tag removed" before you ever call the API.
  On the very first run ever (no log file yet), removal preview isn't
  available -- only additions are previewable, and the summary says so
  explicitly rather than silently implying zero removals.
- **Audit trail.** A persisted record of what this skill has applied to each
  listing and when, independent of Wheelhouse's own note/tag history.

**This log is never the source of truth for an actual write** -- `--apply`
always re-fetches live tags per listing (see above) precisely so a stale or
missing log file can never cause a wrong removal or a clobbered manual tag.
Treat the log as "best current guess for a preview," not as authoritative.

## The consolidated Note

Any listing that earns **at least one** of the 6 tags gets exactly **one**
Note (not one note per tag). A listing whose tags are all being *removed*
this run (nothing currently earned) does **not** get its note touched --
tag removal and note management are independent; only a currently-earning
listing gets a note write.

- **Category:** `["base_price", "calendar"]` on every note -- matching the
  user's ask for a "Base Rate and Calendar" categorized note. **Confirmed
  live** while building this skill: posted a real test note with this exact
  category pair to a sample listing via `POST /listings/{id}/notes` and the
  response echoed `"category":["base_price","calendar"]` back unchanged (no
  422). The same test also confirmed the `PUT /listings/{id}/notes/{note_id}`
  update path (used for same-day re-runs, see below) round-trips correctly,
  and that `GET /notes?start_date=...&end_date=...` reliably finds a note by
  its exact date range -- the mechanism this skill's idempotency check
  depends on.
- **Dates:** `start_date` = `end_date` = today (the day the script ran).
- **Status:** every write (create or update) explicitly sends `"status": "active"`. **Confirmed live and fixed during testing:** `PUT /notes/{id}` only changes fields you send -- if a marker-matching note was ever archived (by a person, or by an earlier interrupted test run) and a same-day update omitted `status`, the note's content would refresh but it would stay archived forever, invisible in Wheelhouse's default note view. Always forcing `status: active` on write means a note about a currently-live flag never gets stuck hidden.
- **Reminder:** `remind_by` = tomorrow, `repeat_by: does_not_repeat`.
- **Description:** one line per tag that actually triggered (in the table
  order above), each with its key number(s) -- *except* `Urgent Attention`,
  whose line is **always included** regardless of whether that specific
  listing's `urgent_band` was `High` -- so every note that gets created shows
  the full composite-score context, not just whichever flag(s) triggered it.
  A short header line (`[Wheelhouse Leaderboard Flags] <date>`) starts every
  description -- this is also the marker this skill uses to find and update
  its own note on a same-day re-run (see below) rather than creating a
  duplicate. Note text itself is not tag-prefixed (`AI - ` is only for the
  Wheelhouse tag list) -- these are plain descriptive lines inside the note
  body.

Example description for a listing that triggered Pacing, Expiring (High), and
Urgent Attention, run on 2026-07-29:

```
[Wheelhouse Leaderboard Flags] 2026-07-29
Pacing - Behind LY: Pace Delta -12.3pp
Expiring Inventory - High Risk: Available Nights 5 (7d) - Pickup Nights 7d 1.0 - Rate Delta Pct 18.2%
Urgent Attention - High: Urgent Score 81.2 - Pace Delta PP -12.3 - Market Ratio 0.62 - Pct at Floor 46.7 - YoY RevPAR Delta Pct -15.4
```

And for a listing that only triggered Market Flag -- Urgent Attention's line
still appears, showing this listing's own (non-High) band for context:

```
[Wheelhouse Leaderboard Flags] 2026-07-29
Market Flag - Underperforming: Market Gap -6.9pp (30d)
Urgent Attention - Medium: Urgent Score 55.2 - Pace Delta PP 1.1 - Market Ratio 0.71 - Pct at Floor 0.0 - YoY RevPAR Delta Pct -4.0
```

**Same-day re-run is idempotent.** Before creating a note, the script checks
today's notes on that listing (`GET /notes?start_date=today&end_date=today`)
for one whose description already starts with the `[Wheelhouse Leaderboard
Flags]` marker, and if found, `PUT`s (updates) that note instead of `POST`ing
a new one. Running this twice in the same day updates the same note in
place; running it on a new day creates that day's fresh note (so over time
you get one dated note per day this ran and found something to flag --
functioning as a running log, not a single note that gets silently
overwritten forever).

## Running it -- dry run first, always

Materialize `_wh_write_client.py` and `apply_leaderboard_tags_notes.py`
(embedded verbatim below) into your working directory if they aren't already
there from earlier this session.

**Step 1 -- dry run (default, zero API calls, always safe):**

```
python3 apply_leaderboard_tags_notes.py --data-dir <path to wheelhouse-leaderboard's output dir>
```

This reads the CSVs (and the writeback log, if one already exists), computes
the full plan, and writes a brand-new, date-stamped file,
`<data-dir>/tag_note_writeback_plan_<YYYY-MM-DD>.csv` -- one row per listing
that has an active tag this run **or** a tag the log shows will be removed --
with columns `listing_id`, `channel`, `title`, `currency`, `desired_tags`,
`tags_to_add`, `tags_to_remove`, `note_description`. **No network calls
happen in this mode.** Read this plan back and relay a short summary to the
user (how many listings evaluated, how many gain a tag, how many lose one,
which tags are most common) before ever running `--apply`. Per this
project's own write-safety convention, a bulk write across a portfolio
always needs the user's confirmation first -- the dry-run plan *is* that
confirmation step, so don't skip straight to `--apply` even if the user
seems in a hurry.

**This plan file (and the log file) are always separate from anything
`wheelhouse-leaderboard` produced.** This script only ever *reads*
`leaderboard_combined.csv` / `leaderboard_expiring_inventory.csv` /
`leaderboard_market_position.csv` -- it never writes to, appends to, or adds
columns onto any of them. Because the plan filename is date-stamped, running
this once a day (e.g. on a schedule) never overwrites a previous day's plan
either -- each day gets its own plan file, so you end up with a running
history of what was evaluated each day, not one file that keeps getting
clobbered. The actual tags and notes themselves aren't local files at all --
`--apply` writes them straight into Wheelhouse over the API, where they
become part of the listing's own record (visible in the Wheelhouse app to
anyone with access), not something that lives in this skill's output folder.

**Step 2 -- selftest (1-2 calls, confirms the write-access key works):**

```
python3 apply_leaderboard_tags_notes.py --data-dir <path> --api-key-file <path>/wheelhouse_api_key_WRITE_ACCESS.txt --selftest
```

Reads one listing's current tags and re-applies that exact same set with
`overwrite: true` -- a real write, but a no-op in effect (nothing changes).
Confirms the key has write access and the `/tags` endpoint is reachable
before trusting a full `--apply` run. Run this once per new key/account.

**Step 3 -- apply for real, after the user has reviewed the plan:**

```
python3 apply_leaderboard_tags_notes.py --data-dir <path> --api-key-file <path>/wheelhouse_api_key_WRITE_ACCESS.txt --apply --verbose
```

**Every** listing in the leaderboard gets a live tags GET (and a PUT only if
its `AI - ` tags need to change), plus up to 2 more calls for any listing
with an active note -- paced at ~1.2s between calls with exponential backoff
on 429. For more than ~50 listings the script prints an estimated call
volume and expected time before it starts. After it finishes, read back the
printed summary (tag sets changed, tags added/removed, notes created vs.
updated, any errors) and relay it plainly -- name any listings that failed,
don't just say "done."

Flags:
- `--data-dir` (required) -- wheelhouse-leaderboard's output directory.
- `--api-key-file` -- required for `--selftest`/`--apply`, not needed for a
  plain dry run.
- `--out` -- plan CSV path (default: `<data-dir>/tag_note_writeback_plan_<date>.csv` -- a new dated file every day, never overwritten).
- `--log` -- writeback log JSON path (default: `<data-dir>/leaderboard_writeback_log.json`).
- `--apply` -- actually write/remove. Omit for the zero-API-call dry run.
- `--selftest` -- see Step 2.
- `--date YYYY-MM-DD` -- override "today", mainly for testing.
- `--verbose` -- per-listing progress.
- `--offset` / `--limit` -- only affect `--apply`: process a slice of the **full per-listing list** (e.g. `--offset 0 --limit 8`, then `--offset 8 --limit 8`, ...) instead of the whole portfolio in one run. Every listing is in this list now, not just currently-flagged ones, since tag removal requires checking every listing's live tags. Useful for batching a large portfolio across multiple invocations to stay under a shell/tool time limit -- **confirmed necessary in practice**: a real 47-listing run took well over a minute, longer than a single command's execution window in some environments. Batches are safe to re-run or overlap: reconciliation is idempotent (a listing whose tags already match its desired set makes no PUT call at all), so a listing processed twice by an overlapping batch boundary just gets re-confirmed, never double-written.

## Running from a scheduled task

**A scheduled run gets a fresh, isolated sandbox every single time it fires,
with no memory of anything mounted in a previous run.** This matters here in
a way it doesn't for a live chat session: in an interactive session the data
directory (and the WRITE-ACCESS key file's directory -- usually the same
folder) is already mounted from earlier in the conversation, so it's easy to
forget this is a step at all. On a schedule there is no "earlier in the
conversation" -- every firing starts cold, so **the mount step must be the
first thing the scheduled task does, every time it runs, not just the first
time it's set up.**

Concretely, before materializing or running `apply_leaderboard_tags_notes.py`
(or `cleanup_legacy_tags.py`), a scheduled invocation of this skill must call
`request_cowork_directory` (load via `ToolSearch` first if it's deferred)
with the exact data-directory path -- the same folder that holds
`leaderboard_combined.csv` and the WRITE-ACCESS key file. Do this
unconditionally at the start of every run; there's no reliable way to detect
in advance whether this particular firing already has the mount (and no
harm in asking again if it does).

**Skipping this step doesn't produce a loud failure** -- `--data-dir` and
`--api-key-file` just silently fail to resolve, since the path the script is
given doesn't exist yet in that sandbox. Since `--apply` mode makes real
writes to Wheelhouse, a run that can't find its data should stop and say so
plainly (missing data directory / missing key file) rather than doing
anything unexpected -- never fall back to a different directory, a cached
copy, or skip the mount check because "it worked last time."

When setting up the schedule itself, make the scheduled task's own prompt
state the data-directory path explicitly (not "the usual folder" or "same as
before") so the mount step has something concrete to request every time.

## Edge cases

- **A listing triggers nothing, and never has:** no tag, no note, no plan
  CSV row -- silence here is correct, not a bug.
- **A listing triggers nothing anymore, but used to:** no note action, but
  `--apply` still removes its stale `AI - ` tag(s) via the live reconcile
  step above; the dry-run plan surfaces this in advance if a prior log
  exists (`tags_to_remove` column).
- **`leaderboard_expiring_inventory.csv` / `leaderboard_market_position.csv`
  missing:** the corresponding tag(s) still apply correctly from
  `leaderboard_combined.csv` alone (it carries `expiring_risk_band` and
  `market_flag`), but the note's detail numbers for that line show `n/a`
  instead of the real figures. Say so if this happens rather than silently
  showing a blank.
- **`expiring_risk_band` is anything other than `High`** (including
  `Medium`, `Low`, `Unknown`, or `No Minimum Price Rule`-style non-applicable
  states) **or `floor_flag` is not `High`:** no tag triggers -- see the
  Medium-risk removal note above.
- **Multiple flags on one listing:** exactly one note, one line per
  triggered flag (in the fixed table order), plus the always-present Urgent
  Attention line -- never multiple notes.
- **Currency:** irrelevant here -- tags and notes carry no money figures
  that need currency context; the numbers this skill writes (pp, %, ratios,
  scores) are all unit-less/percentage-based already.
- **Rate limit (429):** same backoff as the sibling sync/export skills --
  1s, 2s, 4s... capped at 60s, with jitter.
- **Read-only key used by mistake:** the script's error message calls this
  out explicitly (403 on the first PUT/POST) rather than surfacing a bare
  status code.
- **Running daily/weekly on a schedule -- does it pile up duplicate or stale
  tags?** No, **confirmed live**: re-sending a tag name Wheelhouse already
  has does not create a second copy, and every `--apply` run also actively
  drops any `AI - ` tag that's no longer earned. A listing's `AI - ` tags
  always reflect exactly what's currently flagged, nothing more.
- **A user manually adds/removes a Wheelhouse tag between runs:** since
  reconciliation is always a live `GET /tags` fetch-then-merge (never based
  on the local log), the next `--apply` sees the real current state. Manual
  non-`AI - ` tags are never touched; a manually-added `AI - `-prefixed tag
  would be treated as this skill's own on the next run, since the prefix is
  the only signal used to decide ownership -- worth knowing if a user ever
  wants to hand-add a tag that happens to start with `AI - `.
- **Migrating from an older, unprefixed version of this skill:** if tags
  were ever applied before the `AI - ` prefix existed, those old tag names
  won't be recognized as `AI - `-owned and won't be auto-removed by the
  reconciliation step -- they'll just sit there as ordinary (now-orphaned)
  tags. Clean these up as a one-time manual pass (or a short one-off script
  against the known old tag names) if that matters to you; this skill has no
  way to know a differently-named tag used to be its own.

## Bundled script: `_wh_write_client.py`

Materialize this file verbatim as `_wh_write_client.py` alongside the main
script (same directory) before running anything above.

```python
#!/usr/bin/env python3
"""
Minimal shared HTTP client for the Wheelhouse RM API, WRITE-CAPABLE variant.

This is a sibling of the read-only `_wh_client.py` used by
wheelhouse-data-sync-api / wheelhouse-reservations-sync-api /
wheelhouse-notes-export -- same auth, base URL, pacing, and backoff -- but
adds put()/post() alongside get(), because this skill needs to write tags
and notes, not just read them.

Deliberately a separate file (not an import of the read-only client) so a
read-only key file can never accidentally be pointed at a script capable of
writes -- the WRITE ACCESS key file this script needs is a distinct file the
user creates on purpose (see SKILL.md).

Auth: reads the API key from a file path (never accept it as a literal
argument or environment value typed in a chat message -- the user creates
the key file themselves in their own file manager). Sent as the
X-Integration-Api-Key header.

Base URL, rate limit (60 req/min, rolling one-minute window, 429 on
breach), and pagination (page 1-based or offset 0-based -- never both --
per_page up to 100, stop when a page returns fewer than per_page) match the
live RM API reference at api.usewheelhouse.com/wheelhouse_rm_api.
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.usewheelhouse.com/ss_api/v1"

SECONDS_BETWEEN_CALLS = 1.2
MAX_BACKOFF_SECONDS = 60


def load_api_key(key_file_path):
    if not os.path.exists(key_file_path):
        sys.exit(
            f"API key file not found at {key_file_path}. Create it yourself "
            f"(one line, just the key, no quotes) -- this script will never "
            f"print its contents, and you should never paste the key into a "
            f"chat message. This must be a WRITE-ACCESS RM API key (not the "
            f"read-only key some other Wheelhouse skills use) -- PUT/POST "
            f"calls made with a read-only key fail with 403."
        )
    with open(key_file_path, "r") as f:
        key = f.read().strip()
    if not key:
        sys.exit(f"API key file at {key_file_path} is empty.")
    return key


class WheelhouseWriteClient:
    def __init__(self, api_key, verbose=False):
        self.api_key = api_key
        self.verbose = verbose
        self._last_call = 0.0

    def _pace(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < SECONDS_BETWEEN_CALLS:
            time.sleep(SECONDS_BETWEEN_CALLS - elapsed)
        self._last_call = time.monotonic()

    def _request(self, method, path, params=None, json_body=None):
        params = params or {}
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{BASE_URL}{path}"
        if query:
            url += f"?{query}"

        data = None
        headers = {"X-Integration-Api-Key": self.api_key, "Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        backoff = 1.0
        attempt = 0
        while True:
            attempt += 1
            self._pace()
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read()
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as e:
                body_text = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    if self.verbose:
                        print(f"  429 rate-limited on {method} {path}, backing off {backoff:.1f}s", file=sys.stderr)
                    time.sleep(min(backoff, MAX_BACKOFF_SECONDS) + random.uniform(0, 0.5))
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    if attempt <= 6:
                        continue
                    raise RuntimeError(f"429 persisted after {attempt} attempts on {method} {url}: {body_text}")
                if e.code == 401:
                    raise RuntimeError(
                        f"401 Unauthorized on {method} {url} -- API key missing/invalid. "
                        f"Check the key file has no extra spaces/newlines and hasn't been revoked."
                    )
                if e.code == 403:
                    raise RuntimeError(
                        f"403 Forbidden on {method} {url} -- either this key is read-only "
                        f"(PUT/POST require a write-access RM API key) or it isn't scoped to "
                        f"this listing. Body: {body_text}"
                    )
                if e.code == 404:
                    raise RuntimeError(f"404 Not Found on {method} {url}: {body_text}")
                if e.code == 409:
                    raise RuntimeError(f"409 Conflict on {method} {url} -- concurrent update in progress, retry shortly: {body_text}")
                if e.code == 422:
                    raise RuntimeError(f"422 Unprocessable Entity on {method} {url}: {body_text}")
                if e.code == 423:
                    raise RuntimeError(f"423 Locked on {method} {url} -- resource not ready, retry shortly: {body_text}")
                raise RuntimeError(f"HTTP {e.code} on {method} {url}: {body_text}")
            except urllib.error.URLError as e:
                if attempt <= 3:
                    time.sleep(2 * attempt)
                    continue
                raise RuntimeError(f"Network error calling {method} {url}: {e}")

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def put(self, path, params=None, json_body=None):
        return self._request("PUT", path, params=params, json_body=json_body)

    def post(self, path, params=None, json_body=None):
        return self._request("POST", path, params=params, json_body=json_body)

    def get_paginated(self, path, params=None, per_page=100):
        params = dict(params or {})
        params["per_page"] = per_page
        page = 1
        while True:
            params["page"] = page
            batch = self.get(path, params)
            items = batch if isinstance(batch, list) else batch.get("data", batch.get("result", []))
            if not items:
                return
            for item in items:
                yield item
            if len(items) < per_page:
                return
            page += 1
```

## Bundled script: `apply_leaderboard_tags_notes.py`

Materialize this file verbatim as `apply_leaderboard_tags_notes.py`, in the
same directory as `_wh_write_client.py` above, each time you use this skill.

```python
#!/usr/bin/env python3
"""
Turns wheelhouse-leaderboard's output CSVs into Wheelhouse Tags + a single
consolidated Note per flagged listing, via the RM API's write endpoints --
and, on every --apply run, also REMOVES any "AI - " tag this skill previously
added that no longer applies (tag reconciliation, not just tag addition).

Reads (never writes to; these are wheelhouse-leaderboard's own outputs):
  <data-dir>/leaderboard_combined.csv
  <data-dir>/leaderboard_expiring_inventory.csv   (optional -- richer detail)
  <data-dir>/leaderboard_market_position.csv      (optional -- richer detail)

Also reads/writes its own small log file (never touched by
wheelhouse-leaderboard): <data-dir>/leaderboard_writeback_log.json -- a
per-listing record of the AI tags this skill last applied, used to preview
upcoming tag removals during a zero-API-call dry run. The log is NOT the
source of truth for what actually gets removed during --apply -- that's
always a live GET of the listing's current tags, fetch-then-merge style, so
a stale or missing log file can never cause a wrong write.

Three modes:
  --selftest   1-2 calls: confirms the write-access key file works and can
               reach the tags/notes endpoints for one listing. Makes no
               lasting change (tags PUT with the listing's own current tags
               re-applied; no note written).
  (default)    DRY RUN. Computes which AI tags/notes *would* be applied or
               removed for every listing, purely from the local CSVs and the
               local log file -- makes zero API calls -- and writes a plan
               file plus a printed summary. Always safe to run and costs
               nothing. Tag-removal preview needs a prior log file to compare
               against; on the very first run ever (no log yet) removals
               can't be previewed, only additions.
  --apply      Actually calls the API. For EVERY listing in the leaderboard
               (not just ones currently flagged): fetches its current tags,
               computes the desired "AI - " tag set for today, and PUTs the
               reconciled set (existing non-AI tags + desired AI tags) only
               if it differs -- this is what performs removal, since a stale
               "AI - " tag that's no longer earned simply isn't in the
               desired set and gets dropped. Also creates/updates the
               consolidated note for any listing with >=1 desired tag (same
               as before). Confirm the dry-run plan with the user before
               ever passing this flag.

Usage:
  python3 apply_leaderboard_tags_notes.py --data-dir <leaderboards dir> --api-key-file <path> --selftest
  python3 apply_leaderboard_tags_notes.py --data-dir <leaderboards dir> --out <plan.csv>
  python3 apply_leaderboard_tags_notes.py --data-dir <leaderboards dir> --api-key-file <path> --apply --verbose

See this skill's SKILL.md for the full tag list, note format, and the
write-access API key setup this script needs.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wh_write_client import WheelhouseWriteClient, load_api_key  # noqa: E402

NOTE_HEADER_PREFIX = "[Wheelhouse Leaderboard Flags]"
NOTE_CATEGORY = ["base_price", "calendar"]

# Every tag this skill ever writes carries this prefix -- both so they sort
# together and are easy to spot in the Wheelhouse UI, and because the prefix
# doubles as a namespace marker: during --apply, any existing tag starting
# with this prefix is treated as "owned" by this skill and is a candidate for
# removal if it's no longer earned. Tags without this prefix (a user's own
# manual tags) are never touched.
TAG_PREFIX = "AI - "


def key_for(listing_id, channel):
    return f"{listing_id}_{channel}"


# ---------------------------------------------------------------------------
# Loading wheelhouse-leaderboard's CSVs
# ---------------------------------------------------------------------------


def read_csv_rows(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def index_by_listing(rows):
    return {(r["listing_id"], r["channel"]): r for r in rows} if rows else {}


def smallest_window_field(fieldnames, prefix, suffix):
    """Finds the field matching prefix_{W}suffix with the smallest W --
    the leaderboard script's window flags are user-configurable, so this
    script doesn't assume 7/14/30 or 30/60/90, it discovers whatever windows
    were actually used from the CSV's own header row."""
    pattern = re.compile(r"^" + re.escape(prefix) + r"(\d+)" + re.escape(suffix) + r"$")
    matches = []
    for fn in fieldnames:
        m = pattern.match(fn)
        if m:
            matches.append((int(m.group(1)), fn))
    if not matches:
        return None, None
    matches.sort()
    return matches[0][1], matches[0][0]


def to_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def fmt_num(v, suffix="", decimals=1):
    if v is None:
        return "n/a"
    return f"{v:.{decimals}f}{suffix}"


# ---------------------------------------------------------------------------
# Tag + note-line computation for one listing
# ---------------------------------------------------------------------------


def compute_listing_plan(combined_row, expiring_row, market_row, expiring_window, market_window):
    """Returns (desired_ai_tags, note_lines) for one listing. desired_ai_tags
    is a list of fully-prefixed ("AI - ...") tag strings -- may be empty if
    nothing is currently flagged. note_lines has no header/prefix logic of
    its own; the caller assembles the full note description."""
    tags = []
    lines = []

    pace_flag = combined_row.get("pace_flag")
    pace_delta = to_float(combined_row.get("pace_delta_pp"))
    if pace_flag == "Behind LY":
        tags.append(f"{TAG_PREFIX}Pacing - Behind LY")
        lines.append(f"Pacing - Behind LY: Pace Delta {fmt_num(pace_delta, 'pp')}")

    # Expiring Inventory: High Risk only for now -- Medium Risk was dropped
    # as a trigger per user request (2026-07-29) since it was firing too
    # broadly (34 of 47 listings on a real test run) to be a useful signal.
    # The underlying leaderboard_expiring_inventory.csv column is untouched;
    # this is purely a decision about which risk_band values earn a tag/note
    # here, easy to re-expand later if wanted.
    risk_band = combined_row.get("expiring_risk_band")
    if risk_band == "High":
        tags.append(f"{TAG_PREFIX}Expiring Inventory - High Risk")
        avail = to_float(expiring_row.get(f"available_nights_{expiring_window}d")) if expiring_row and expiring_window else None
        pickup = to_float(expiring_row.get("pickup_nights_7d")) if expiring_row else None
        rate_delta = to_float(expiring_row.get("rate_delta_pct")) if expiring_row else None
        lines.append(
            f"Expiring Inventory - High Risk: "
            f"Available Nights {fmt_num(avail, '', 0)}"
            f"{f' ({expiring_window}d)' if expiring_window else ''} - "
            f"Pickup Nights 7d {fmt_num(pickup, '', 1)} - "
            f"Rate Delta Pct {fmt_num(rate_delta, '%')}"
        )

    market_flag = combined_row.get("market_flag")
    if market_flag == "Underperforming Market":
        tags.append(f"{TAG_PREFIX}Market Flag - Underperforming")
        gap = to_float(market_row.get(f"market_gap_{market_window}d_pp")) if market_row and market_window else None
        lines.append(
            f"Market Flag - Underperforming: Market Gap {fmt_num(gap, 'pp')}"
            f"{f' ({market_window}d)' if market_window else ''}"
        )

    floor_flag = combined_row.get("floor_flag")
    pct_at_floor = to_float(combined_row.get("pct_at_floor"))
    if floor_flag == "High":
        tags.append(f"{TAG_PREFIX}Floor Flag - High")
        lines.append(f"Floor Flag - High: Pct at Floor {fmt_num(pct_at_floor, '%')}")

    yoy_flag = combined_row.get("yoy_flag")
    yoy_delta = to_float(combined_row.get("yoy_revpar_delta_pct"))
    if yoy_flag == "Declined YoY":
        tags.append(f"{TAG_PREFIX}YoY Flag - Declined YoY")
        lines.append(f"YoY Flag - Declined YoY: YoY RevPAR Delta Pct {fmt_num(yoy_delta, '%')}")

    urgent_band = combined_row.get("urgent_band")
    urgent_score = to_float(combined_row.get("urgent_score"))
    market_ratio = to_float(combined_row.get("market_ratio"))
    if urgent_band == "High":
        tags.append(f"{TAG_PREFIX}Urgent Attention - High")

    # Urgent Attention context line is ALWAYS included on any note that gets
    # created (per spec) -- even when this listing's own urgent_band isn't
    # High -- so whoever reads the note always sees the composite score
    # alongside whatever specific flag(s) actually triggered it.
    if tags:
        lines.append(
            f"Urgent Attention - {urgent_band or 'Unknown'}: "
            f"Urgent Score {fmt_num(urgent_score, '', 1)} - "
            f"Pace Delta PP {fmt_num(pace_delta, '', 1)} - "
            f"Market Ratio {fmt_num(market_ratio, '', 2)} - "
            f"Pct at Floor {fmt_num(pct_at_floor, '', 1)} - "
            f"YoY RevPAR Delta Pct {fmt_num(yoy_delta, '', 1)}"
        )

    return tags, lines


def build_entries(data_dir, today):
    """Returns (entries, total_listings, has_expiring, has_market). entries
    has ONE item per listing in leaderboard_combined.csv -- including
    listings with an empty desired_tags list -- because tag *removal* needs
    to consider every listing, not just currently-flagged ones (a listing
    that dropped off every flag this week still needs its stale AI tags
    cleared)."""
    combined_rows = read_csv_rows(os.path.join(data_dir, "leaderboard_combined.csv"))
    if not combined_rows:
        sys.exit(
            f"leaderboard_combined.csv not found (or empty) under {data_dir} -- "
            f"run the wheelhouse-leaderboard skill against this directory first."
        )
    expiring_rows = read_csv_rows(os.path.join(data_dir, "leaderboard_expiring_inventory.csv"))
    market_rows = read_csv_rows(os.path.join(data_dir, "leaderboard_market_position.csv"))

    expiring_by_key = index_by_listing(expiring_rows)
    market_by_key = index_by_listing(market_rows)

    expiring_window = None
    if expiring_rows:
        _, expiring_window = smallest_window_field(expiring_rows[0].keys(), "available_nights_", "d")
    market_window = None
    if market_rows:
        _, market_window = smallest_window_field(market_rows[0].keys(), "market_gap_", "d_pp")

    entries = []
    for row in combined_rows:
        key = (row["listing_id"], row["channel"])
        expiring_row = expiring_by_key.get(key)
        market_row = market_by_key.get(key)
        tags, lines = compute_listing_plan(row, expiring_row, market_row, expiring_window, market_window)
        description = None
        if tags:
            description = NOTE_HEADER_PREFIX + f" {today.isoformat()}\n" + "\n".join(lines)
        entries.append(
            {
                "listing_id": row["listing_id"],
                "channel": row["channel"],
                "title": row.get("title"),
                "currency": row.get("currency"),
                "desired_tags": tags,
                "note_description": description,
            }
        )
    return entries, len(combined_rows), bool(expiring_rows), bool(market_rows)


# ---------------------------------------------------------------------------
# The local writeback log (audit trail + dry-run removal preview only --
# never the source of truth for an actual write, see module docstring)
# ---------------------------------------------------------------------------


def load_log(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_log(path, log):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Applying the plan via the API
# ---------------------------------------------------------------------------


def find_existing_todays_note(client, listing_id, channel, today_str):
    """Looks for a note this script already created today (same start_date/
    end_date == today, description starting with our marker prefix), so a
    same-day re-run updates that note instead of creating a duplicate."""
    notes = client.get(
        f"/listings/{listing_id}/notes",
        {"channel": channel, "start_date": today_str, "end_date": today_str},
    )
    items = notes if isinstance(notes, list) else (notes or {}).get("result", (notes or {}).get("data", []))
    for n in items or []:
        if (n.get("description") or "").startswith(NOTE_HEADER_PREFIX):
            return n.get("id")
    return None


def reconcile_tags(client, listing_id, channel, desired_tags, verbose=False):
    """Fetch-then-merge for tag REMOVAL, not just addition: live-reads the
    listing's current tags (never trusts the local log for this), splits
    them into "AI - " (owned by this skill) vs. everything else (a user's
    own manual tags, always left alone), and PUTs the reconciled full set
    with overwrite=true ONLY if it actually differs from today's desired AI
    tag set. Returns (changed: bool, added: set, removed: set)."""
    current = client.get(f"/listings/{listing_id}/tags", {"channel": channel})
    current_items = current if isinstance(current, list) else (current or {}).get("result", (current or {}).get("data", []))
    current_names = [t["name"] if isinstance(t, dict) else t for t in (current_items or [])]

    existing_ai = [n for n in current_names if n.startswith(TAG_PREFIX)]
    existing_non_ai = [n for n in current_names if not n.startswith(TAG_PREFIX)]

    existing_ai_set = set(existing_ai)
    desired_set = set(desired_tags)

    if existing_ai_set == desired_set:
        return False, set(), set()

    added = desired_set - existing_ai_set
    removed = existing_ai_set - desired_set
    new_full_list = existing_non_ai + list(desired_tags)
    client.put(
        f"/listings/{listing_id}/tags",
        params={"channel": channel},
        json_body={"names": new_full_list, "overwrite": True},
    )
    if verbose:
        extra = []
        if added:
            extra.append(f"+{sorted(added)}")
        if removed:
            extra.append(f"-{sorted(removed)}")
        print(f"  OK tags {listing_id}/{channel}: {' '.join(extra)}")
    return True, added, removed


def apply_entries(client, entries, today, log, verbose=False):
    today_str = today.isoformat()
    remind_by = (today + datetime.timedelta(days=1)).isoformat()
    errors = []
    tags_changed = 0
    tags_unchanged = 0
    tags_added_total = 0
    tags_removed_total = 0
    notes_created = 0
    notes_updated = 0

    for item in entries:
        listing_id, channel = item["listing_id"], item["channel"]
        k = key_for(listing_id, channel)
        desired_tags = item["desired_tags"]

        try:
            changed, added, removed = reconcile_tags(client, listing_id, channel, desired_tags, verbose=verbose)
            if changed:
                tags_changed += 1
                tags_added_total += len(added)
                tags_removed_total += len(removed)
            else:
                tags_unchanged += 1
        except RuntimeError as e:
            print(f"  ERROR tags {listing_id}/{channel}: {e}", file=sys.stderr)
            errors.append({"listing_id": listing_id, "channel": channel, "step": "tags", "error": str(e)})
            continue

        if item["note_description"]:
            try:
                existing_note_id = find_existing_todays_note(client, listing_id, channel, today_str)
                note_body = {
                    "description": item["note_description"],
                    "category": NOTE_CATEGORY,
                    "start_date": today_str,
                    "end_date": today_str,
                    "remind_by": remind_by,
                    "repeat_by": "does_not_repeat",
                    # Explicit, not incidental: PUT only changes fields you
                    # send, so if a marker-matching note was ever archived
                    # (by a person, or an earlier interrupted run) and this
                    # same-day update omitted status, it would stay archived
                    # forever even though its content just refreshed --
                    # confirmed this exact scenario live while testing.
                    "status": "active",
                }
                if existing_note_id:
                    client.put(
                        f"/listings/{listing_id}/notes/{existing_note_id}",
                        params={"channel": channel},
                        json_body=note_body,
                    )
                    notes_updated += 1
                    if verbose:
                        print(f"  OK note (updated existing #{existing_note_id}) {listing_id}/{channel}")
                else:
                    client.post(
                        f"/listings/{listing_id}/notes",
                        params={"channel": channel},
                        json_body=note_body,
                    )
                    notes_created += 1
                    if verbose:
                        print(f"  OK note (created) {listing_id}/{channel}")
            except RuntimeError as e:
                print(f"  ERROR note {listing_id}/{channel}: {e}", file=sys.stderr)
                errors.append({"listing_id": listing_id, "channel": channel, "step": "note", "error": str(e)})

        log[k] = {
            "title": item["title"],
            "ai_tags": desired_tags,
            "last_checked": today_str,
        }

    return {
        "tags_changed": tags_changed,
        "tags_unchanged": tags_unchanged,
        "tags_added_total": tags_added_total,
        "tags_removed_total": tags_removed_total,
        "notes_created": notes_created,
        "notes_updated": notes_updated,
        "errors": errors,
    }


def selftest(client, entries):
    print("=== SELF-TEST: 1 listing, re-applies its own current tags (no lasting change), no note written ===")
    flagged = [e for e in entries if e["desired_tags"]]
    item = flagged[0] if flagged else (entries[0] if entries else None)
    if not item:
        sys.exit("No listings found in leaderboard_combined.csv -- nothing to test against.")
    listing_id, channel = item["listing_id"], item["channel"]
    try:
        current = client.get(f"/listings/{listing_id}/tags", {"channel": channel})
        current_items = current if isinstance(current, list) else (current or {}).get("result", (current or {}).get("data", []))
        # GetTags returns a list of tag objects ({"id", "name", "description",
        # "type"}, confirmed live against a real account), not bare strings --
        # PutTags' "names" field wants plain strings, so extract .name from
        # each rather than round-tripping the whole object back to the API.
        current_names = [t["name"] if isinstance(t, dict) else t for t in (current_items or [])]
        client.put(
            f"/listings/{listing_id}/tags",
            params={"channel": channel},
            json_body={"names": current_names, "overwrite": True},
        )
        print(f"OK -> tags read + re-applied for listing_id={listing_id} channel={channel}: {current_names}")
    except RuntimeError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    print("=== SELF-TEST PASSED -- write-access key works against /tags. "
          "Notes endpoint is exercised for real only during --apply. ===")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True, help="wheelhouse-leaderboard's output directory (contains leaderboard_combined.csv)")
    ap.add_argument("--api-key-file", default=None, help="Path to the WRITE-ACCESS Wheelhouse RM API key file. Required for --selftest/--apply, not needed for a plain dry run.")
    ap.add_argument("--out", default=None, help="Plan CSV output path (default: <data-dir>/tag_note_writeback_plan_<date>.csv -- one new dated file per day, never overwriting a previous day's plan)")
    ap.add_argument("--log", default=None, help="Writeback log JSON path (default: <data-dir>/leaderboard_writeback_log.json)")
    ap.add_argument("--apply", action="store_true", help="Actually call the API and write/remove tags + write notes. Omit for a zero-API-call dry run.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--date", default=None, help="Override 'today' (YYYY-MM-DD), mainly for testing")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--offset", type=int, default=0,
                     help="Only affects --apply: skip this many listings from the start of the full per-listing list before "
                          "processing. Useful for batching a large portfolio across multiple runs to stay under a shell's "
                          "time limit -- every listing is included in this list (not just currently-flagged ones), since "
                          "tag removal requires checking every listing's live tags, not just the ones flagged today.")
    ap.add_argument("--limit", type=int, default=None,
                     help="Only affects --apply: process at most this many listings (after --offset). Omit to process every listing in one run.")
    args = ap.parse_args()

    today = datetime.date.today()
    if args.date:
        today = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()

    entries, total_listings, has_expiring, has_market = build_entries(args.data_dir, today)
    log_path = args.log or os.path.join(args.data_dir, "leaderboard_writeback_log.json")

    if not has_expiring:
        print("Note: leaderboard_expiring_inventory.csv not found -- Expiring Inventory note detail "
              "(Available Nights / Pickup Nights / Rate Delta Pct) will show as n/a.")
    if not has_market:
        print("Note: leaderboard_market_position.csv not found -- Market Flag note detail "
              "(Market Gap) will show as n/a.")

    if args.selftest:
        if not args.api_key_file:
            sys.exit("--selftest requires --api-key-file (the WRITE-ACCESS key).")
        api_key = load_api_key(args.api_key_file)
        client = WheelhouseWriteClient(api_key, verbose=args.verbose)
        selftest(client, entries)
        return

    if not args.apply:
        # DRY RUN: zero API calls. Tag-removal preview is computed against the
        # local log's last-known "ai_tags" per listing -- a best-effort
        # preview only (the actual --apply run always re-checks live tags,
        # so this can't be wrong in a way that causes a bad write, only in a
        # way that makes the preview slightly stale if tags changed by some
        # other means since the log was last written).
        log = load_log(log_path)
        has_log = bool(log)

        rows_out = []
        tag_freq = {}
        removal_count = 0
        addition_count = 0
        for item in entries:
            k = key_for(item["listing_id"], item["channel"])
            desired = item["desired_tags"]
            for t in desired:
                tag_freq[t] = tag_freq.get(t, 0) + 1
            prev = log.get(k, {}).get("ai_tags", []) if has_log else []
            to_add = [t for t in desired if t not in prev]
            to_remove = [t for t in prev if t not in desired] if has_log else []
            if to_add:
                addition_count += 1
            if to_remove:
                removal_count += 1
            if desired or to_remove:
                rows_out.append(
                    {
                        "listing_id": item["listing_id"],
                        "channel": item["channel"],
                        "title": item["title"],
                        "currency": item["currency"],
                        "desired_tags": "; ".join(desired),
                        "tags_to_add": "; ".join(to_add),
                        "tags_to_remove": "; ".join(to_remove) if has_log else "n/a (no prior log)",
                        "note_description": item["note_description"] or "",
                    }
                )

        out_path = args.out or os.path.join(args.data_dir, f"tag_note_writeback_plan_{today.isoformat()}.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["listing_id", "channel", "title", "currency", "desired_tags", "tags_to_add", "tags_to_remove", "note_description"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_out)

        print(f"Evaluated {total_listings} listing(s) from leaderboard_combined.csv.")
        print(f"{sum(1 for e in entries if e['desired_tags'])} listing(s) have an active AI tag today.")
        print(f"{addition_count} listing(s) will gain at least one new AI tag.")
        if has_log:
            print(f"{removal_count} listing(s) will have at least one stale AI tag removed.")
        else:
            print("No prior writeback log found -- this looks like the first run, so tag-removal preview isn't "
                  "available yet (it will be after the first --apply writes the log).")
        print("Tag frequency this run:")
        for tag, count in sorted(tag_freq.items(), key=lambda kv: -kv[1]):
            print(f"  {tag}: {count}")
        print(f"Plan written to: {out_path}")
        print("DRY RUN -- no API calls made, nothing written to Wheelhouse. "
              "Review the plan file above, then re-run with --apply (and --api-key-file) to write it for real.")
        return

    if not args.api_key_file:
        sys.exit("--apply requires --api-key-file (the WRITE-ACCESS key).")

    apply_targets = entries[args.offset:args.offset + args.limit] if args.limit is not None else entries[args.offset:]
    if args.offset or args.limit is not None:
        print(f"Batch mode: processing listings {args.offset}..{args.offset + len(apply_targets) - 1} "
              f"of {len(entries)} total ({len(apply_targets)} in this run).")
    if len(apply_targets) > 50:
        print(f"About to check ~{len(apply_targets)} listings' current tags (1 GET + up to 1 PUT each, plus up to 2 "
              f"more calls for any listing with an active note) against a 60/min limit. This will take a few minutes.")

    api_key = load_api_key(args.api_key_file)
    client = WheelhouseWriteClient(api_key, verbose=args.verbose)
    log = load_log(log_path)
    stats = apply_entries(client, apply_targets, today, log, verbose=args.verbose)
    save_log(log_path, log)

    print(
        f"Done. Listings checked: {len(apply_targets)}. Tag sets changed: {stats['tags_changed']} "
        f"(+{stats['tags_added_total']} tag(s) added, -{stats['tags_removed_total']} tag(s) removed). "
        f"Unchanged: {stats['tags_unchanged']}. Notes created: {stats['notes_created']}. "
        f"Notes updated (same-day re-run): {stats['notes_updated']}. Errors: {len(stats['errors'])}."
    )
    if stats["errors"]:
        print("Listings that failed:", [f"{e['listing_id']}/{e['channel']} ({e['step']})" for e in stats["errors"]])
    print(f"Writeback log updated: {log_path}")


if __name__ == "__main__":
    main()
```
