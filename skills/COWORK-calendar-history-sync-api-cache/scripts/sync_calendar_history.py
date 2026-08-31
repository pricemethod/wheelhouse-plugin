#!/usr/bin/env python3
"""
Direct-API sync for Wheelhouse price calendars -- the HISTORY-KEEPING
version. No Claude/MCP calls in the loop -- see _wh_client.py's docstring
for why.

This is the sibling of the simple wheelhouse-calendar-sync-api skill. Both
pull each listing's FUTURE price calendar (today forward), but this version
additionally preserves every past pull as a dated snapshot instead of just
overwriting it:

  - current/{id}_{channel}.json always holds the MOST RECENT pull for that
    listing -- a stable, referenceable path other skills can read without
    needing to know which date's pull is "latest."
  - Before a fresh pull replaces it, whatever was previously in current/ gets
    MOVED (not copied) into snapshots/{the date IT was pulled}/{id}_{channel}.json
    -- so history accumulates as one dated folder per calendar sync date,
    each holding exactly the listings whose current pull was superseded that
    day. Nothing is ever duplicated between current/ and snapshots/: a given
    pull lives in exactly one of the two places at any moment.

**Uses a different default --out than the sibling simple skill on purpose**
(wheelhouse_calendar_data_history/ vs. wheelhouse_calendar_data/), so you can
run both against the same parent directory at the same time -- e.g. for
side-by-side testing -- without one overwriting the other's files.

Usage:
  python3 sync_calendar_history.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_calendar_data_history
  python3 sync_calendar_history.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_calendar_data_history --selftest

--selftest fetches one listing (via next() on a per_page=1 paginated
generator -- never materializes a full listings page) plus one short (7-day)
price_calendar call for it -- 2 calls total, same as the sibling skill.

Endpoint: GET /listings/{listing_id}/price_calendar -- see _wh_client.py's
docstring for the confirmed field list and behavior. No pagination on this
endpoint; the whole requested range comes back in one call.

Date window: same --days convention as the sibling skill, default 365 days
forward from today. Every night's snapshot for a listing is roughly this
size, so a longer window directly multiplies disk usage per night -- see
--prune-older-than-days below if that matters to you.

Output layout (all under --out):
  listings.json                          -- one JSON object keyed by "{id}_{channel}"
  current/{id}_{channel}.json             -- {"listing_id","channel","synced_at","sync_date",
                                               "start_date","end_date","calendar":[...]} -- latest pull only
  snapshots/{YYYY-MM-DD}/{id}_{channel}.json
                                          -- the calendar exactly as it stood in current/ before being
                                             superseded, filed under the date IT was originally pulled
  index.json                             -- sync metadata

Same-day resume, cross-day always-refresh -- checked against current/'s own
sync_date, same fix already verified end-to-end on the sibling KPI sync: a
listing is skipped ONLY if current/{key}.json exists AND its sync_date
matches today's date (or --date). A new day means every listing's recorded
sync_date is from before today, so nothing is skipped and every listing gets
rotated-then-refetched -- the entire point of running this nightly. --force
ignores the skip check (but still safely rotates whatever's currently in
current/ into today's snapshot folder before overwriting, so forcing a
same-day re-run never silently drops the pull that was there before it).

Rotation only happens AFTER a fresh fetch succeeds, never before -- so a
failed API call for a listing leaves that listing's current/ (and its
history) completely untouched rather than losing data to a fetch that never
landed.

--prune-older-than-days N (optional, default: none -- keep every snapshot
forever): after a sync, deletes any snapshots/{date}/ folder older than N
days relative to this run's sync_date. This is the only place disk usage is
actively bounded; the whole point of this skill is to keep history, so the
default is to never delete anything unless you ask for it.

Multi-unit listings: same as the sibling skill -- price_calendar returns one
row per unit per date (unit_number 0 for single-unit listings), stored
as-is; consuming skills should group by unit_number when reading rather than
assuming one row per date.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wh_client import WheelhouseClient, load_api_key  # noqa: E402

DEFAULT_DAYS_FORWARD = 365


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def window(sync_date, days):
    start = datetime.datetime.strptime(sync_date, "%Y-%m-%d").date()
    end = start + datetime.timedelta(days=days)
    return start.isoformat(), end.isoformat()


def extract_rows(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        return resp.get("data", resp.get("result", []))
    return []


def load_current(current_file):
    """Returns the existing current/{key}.json record, or None if missing or
    unreadable. A read/parse failure is treated as 'nothing there' (safe
    default: proceed to fetch fresh rather than trust or rotate a file we
    can't verify)."""
    if not os.path.exists(current_file):
        return None
    try:
        with open(current_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def selftest(client, include_managed):
    print("=== SELF-TEST: 1 listing, 2 calls ===")
    try:
        gen = client.get_paginated(
            "/listings",
            {"exclude_inactive": "true", "include_managed_listings": str(include_managed).lower()},
            per_page=1,
        )
        listing = next(gen, None)
    except RuntimeError as e:
        print(f"FAIL on /listings: {e}")
        sys.exit(1)
    if not listing:
        print("No listings returned -- check the account has active listings, or try --include-inactive.")
        sys.exit(1)
    listing_id = listing.get("id")
    channel = listing.get("channel")
    print(f"OK /listings -> got listing_id={listing_id} channel={channel} title={listing.get('title')}")

    today = today_str()
    end = (datetime.datetime.strptime(today, "%Y-%m-%d").date() + datetime.timedelta(days=7)).isoformat()
    try:
        result = client.get(
            f"/listings/{listing_id}/price_calendar",
            {"channel": channel, "start_date": today, "end_date": end},
        )
        rows = extract_rows(result)
        print(f"OK price_calendar -> {len(rows)} row(s) for a 7-day window")
        if rows:
            print(f"Sample row keys: {sorted(rows[0].keys())}")
    except RuntimeError as e:
        print(f"FAIL price_calendar: {e}")
        sys.exit(1)
    print("=== SELF-TEST PASSED -- safe to run a full sync ===")


def prune_snapshots(snapshots_dir, sync_date, retain_days, verbose=False):
    if retain_days is None or not os.path.isdir(snapshots_dir):
        return []
    cutoff = datetime.datetime.strptime(sync_date, "%Y-%m-%d").date() - datetime.timedelta(days=retain_days)
    removed = []
    for name in sorted(os.listdir(snapshots_dir)):
        path = os.path.join(snapshots_dir, name)
        if not os.path.isdir(path):
            continue
        try:
            folder_date = datetime.datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            continue  # not a date-named folder -- leave it alone
        if folder_date < cutoff:
            shutil.rmtree(path)
            removed.append(name)
            if verbose:
                print(f"  PRUNED snapshots/{name} (older than {retain_days} days)")
    return removed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-key-file", required=True)
    ap.add_argument("--out", required=True, help="Output directory (e.g. wheelhouse_calendar_data_history)")
    ap.add_argument(
        "--days", type=int, default=DEFAULT_DAYS_FORWARD,
        help=f"How many days forward (from today) to pull per listing (default {DEFAULT_DAYS_FORWARD}). "
        "The API itself allows up to a 3-year total range. Larger windows mean larger snapshots every night.",
    )
    ap.add_argument("--include-inactive", action="store_true", help="Include inactive listings (default: excluded)")
    ap.add_argument("--owned-only", action="store_true", help="Exclude managed/delegated listings (default: included)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore each listing's stored sync_date and re-fetch/rotate every listing regardless of "
        "whether it was already synced today. Not needed for routine nightly runs.",
    )
    ap.add_argument(
        "--date",
        default=None,
        help="Override 'today' (UTC, format YYYY-MM-DD) used for the same-day-skip check, the rotation "
        "folder name, and the start of the forward window. Mainly for testing.",
    )
    ap.add_argument(
        "--prune-older-than-days",
        type=int,
        default=None,
        help="Delete snapshots/{date}/ folders older than this many days (relative to the sync date). "
        "Default: unset -- keep every snapshot forever, since retaining history is this skill's purpose. "
        "Only pass this if you've deliberately decided you don't need snapshots past a certain age.",
    )
    args = ap.parse_args()

    include_managed = not args.owned_only
    sync_date = args.date or today_str()

    api_key = load_api_key(args.api_key_file)
    client = WheelhouseClient(api_key, verbose=args.verbose)

    if args.selftest:
        selftest(client, include_managed)
        return

    current_dir = os.path.join(args.out, "current")
    snapshots_dir = os.path.join(args.out, "snapshots")
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(current_dir, exist_ok=True)

    print("Fetching listings...")
    listings = list(
        client.get_paginated(
            "/listings",
            {
                "exclude_inactive": str(not args.include_inactive).lower(),
                "include_managed_listings": str(include_managed).lower(),
            },
        )
    )
    listings_out = {}
    for l in listings:
        key = f"{l.get('id')}_{l.get('channel')}"
        listings_out[key] = l
    with open(os.path.join(args.out, "listings.json"), "w") as f:
        json.dump(listings_out, f, indent=1)
    print(f"Wrote listings.json: {len(listings_out)} listings (include_managed_listings={include_managed})")

    start_date, end_date = window(sync_date, args.days)

    errors = []
    fresh = 0
    skipped = 0
    rotated = 0
    total_rows = 0
    for key, listing in listings_out.items():
        listing_id = listing.get("id")
        channel = listing.get("channel")
        current_file = os.path.join(current_dir, f"{key}.json")

        existing = load_current(current_file)
        if not args.force and existing is not None and existing.get("sync_date") == sync_date:
            skipped += 1
            if args.verbose:
                print(f"  SKIP {key} (already synced today, {sync_date} -- use --force to redo anyway)")
            continue

        try:
            resp = client.get(
                f"/listings/{listing_id}/price_calendar",
                {"channel": channel, "start_date": start_date, "end_date": end_date},
            )
            rows = extract_rows(resp)
        except RuntimeError as e:
            print(f"  ERROR {key}: {e}", file=sys.stderr)
            errors.append({"listing": key, "error": str(e)})
            continue

        # Rotate the previous pull (if any) into its own dated snapshot
        # folder ONLY after the fresh fetch has already succeeded, so a
        # failed call never costs us the data that was already there.
        if existing is not None:
            old_date = existing.get("sync_date") or "unknown-date"
            snap_dir = os.path.join(snapshots_dir, old_date)
            os.makedirs(snap_dir, exist_ok=True)
            snap_path = os.path.join(snap_dir, f"{key}.json")
            os.replace(current_file, snap_path)
            rotated += 1
            if args.verbose:
                print(f"  ROTATED {key}: previous pull ({old_date}) -> snapshots/{old_date}/{key}.json")

        record = {
            "listing_id": listing_id,
            "channel": channel,
            "synced_at": now_iso(),
            "sync_date": sync_date,
            "start_date": start_date,
            "end_date": end_date,
            "calendar": rows,
        }
        with open(current_file, "w") as f:
            json.dump(record, f, indent=1)
        fresh += 1
        total_rows += len(rows)
        if args.verbose:
            print(f"  OK {key}: {len(rows)} row(s), {start_date} to {end_date}")

    pruned = prune_snapshots(snapshots_dir, sync_date, args.prune_older_than_days, verbose=args.verbose)

    index_path = os.path.join(args.out, "index.json")
    index = {}
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    index.setdefault("last_sync", {})
    index["last_sync"]["listings"] = now_iso()
    index["last_sync"]["calendar"] = now_iso()
    index["last_sync"]["calendar_sync_date"] = sync_date
    index["listing_count"] = len(listings_out)
    index["include_managed_listings"] = include_managed
    index["include_inactive_listings"] = args.include_inactive
    index["calendar_window_days"] = args.days
    index["calendar_sync_errors"] = errors
    index["prune_older_than_days"] = args.prune_older_than_days
    index["last_prune_removed"] = pruned
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)

    total = fresh + skipped
    print(
        f"Done. Listings: {len(listings_out)}. Calendars processed: {total} "
        f"({fresh} freshly fetched, {skipped} already up to date for {sync_date}, "
        f"{rotated} previous pulls rotated into snapshots/). "
        f"Rows fetched this run: {total_rows}. Errors: {len(errors)}."
    )
    if pruned:
        print(f"Pruned {len(pruned)} snapshot date folder(s) older than {args.prune_older_than_days} days: {pruned}")
    if errors:
        print("Listings that failed:", [e["listing"] for e in errors])
    if not errors and total == len(listings_out) and skipped == 0:
        print(f"All {len(listings_out)} listings freshly synced for {sync_date} -- 0 errors.")
    elif not errors and total == len(listings_out):
        print(
            f"All listings have a current/ calendar synced for {sync_date} on disk "
            f"({fresh} fetched this run, {skipped} already done earlier today)."
        )


if __name__ == "__main__":
    main()
