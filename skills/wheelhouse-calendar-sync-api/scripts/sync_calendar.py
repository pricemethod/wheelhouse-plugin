#!/usr/bin/env python3
"""
Direct-API sync for Wheelhouse price calendars -- the SIMPLE version.
No Claude/MCP calls in the loop -- see _wh_client.py's docstring for why.

This pulls each listing's FUTURE price calendar (today forward) and fully
REPLACES the on-disk file for that listing every run. It keeps no history of
past pulls -- if you want a dated archive of every night's calendar as it
looked when pulled, use the sibling wheelhouse-calendar-sync-api-history
skill instead (different skill folder, different default --out, so the two
can run side by side without colliding).

Usage:
  python3 sync_calendar.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_calendar_data
  python3 sync_calendar.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_calendar_data --selftest

--selftest fetches one listing (via next() on a per_page=1 paginated
generator -- never materializes a full listings page, so it stays fast
regardless of portfolio size, mirroring the fix already applied to the
sibling wheelhouse-data-sync-api skill) plus one short (7-day) price_calendar
call for it -- 2 calls total. Run this before a full sync the first time, or
after any Wheelhouse API change.

Endpoint: GET /listings/{listing_id}/price_calendar -- confirmed via the
connected Wheelhouse MCP's live tool schema and a real test call on
2026-08-04 (see _wh_client.py's docstring for the full field list). No
pagination on this endpoint -- the whole requested date range comes back in
a single call, which makes this cheaper per listing than the sibling KPI
sync (1 call/listing here vs. 2 there).

Date window: defaults to today through --days days forward (default 365).
The underlying API's own default when start_date/end_date are omitted is
today through 1.5 years out, capped at a 3-year total range -- this script
defaults to a shorter 365-day window instead, mainly to keep each nightly
payload and (for the history-tracking sibling skill) each archived snapshot
a predictable, bounded size. Pass --days 545 (~1.5y) or any value up to the
API's 3-year cap for deeper future coverage, e.g. before a far-future
event/holiday rate review.

Output layout (all under --out):
  listings.json                 -- one JSON object keyed by "{id}_{channel}", full listing record
  calendar/{id}_{channel}.json  -- {"listing_id","channel","synced_at","sync_date",
                                    "start_date","end_date","calendar":[...]}
  index.json                    -- sync metadata

Same-day resume, cross-day always-refresh (same fix already verified
end-to-end on the sibling wheelhouse-data-sync-api skill's KPI sync, applied
here identically): a nightly sync must always pull every listing's current
calendar, never silently skip one just because a same-named file already
exists from a previous night -- but a truncated run shouldn't have to
restart the whole portfolio from scratch either. Each calendar/{key}.json
file carries a "sync_date" (UTC calendar date the run that wrote it was
for). A listing is skipped ONLY if its file already exists AND that file's
sync_date matches today's date (or the date passed via --date):
  - Same day, second invocation (resuming after a timeout): listings already
    written earlier TODAY are skipped instantly.
  - A new day's run: every listing's stored sync_date is from a prior day
    (or the file doesn't exist yet), so nothing is skipped -- every listing
    gets a fresh pull, which is the entire point of running this nightly.
--force ignores sync_date and always re-fetches every listing. --date
overrides what "today" means (UTC, YYYY-MM-DD) for the skip check -- mainly
for testing.

Multi-unit listings: price_calendar returns one row per unit per date for
multi-unit listings (unit_number 0 for single-unit listings). This script
stores the raw returned rows as-is in one file per listing -- it does not
split by unit_number on write. Consuming skills should group by unit_number
when reading, per the project's general multi-unit guidance, rather than
assuming one row per date.
"""
import argparse
import datetime
import json
import os
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


def already_synced_today(cal_file, sync_date):
    """True only if cal_file exists AND its stored sync_date matches
    sync_date. Any read/parse failure or missing sync_date key is treated as
    NOT synced today (safe default: re-fetch rather than trust an
    unverifiable file)."""
    if not os.path.exists(cal_file):
        return False
    try:
        with open(cal_file) as f:
            existing = json.load(f)
        return existing.get("sync_date") == sync_date
    except (json.JSONDecodeError, OSError):
        return False


def extract_rows(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        return resp.get("data", resp.get("result", []))
    return []


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-key-file", required=True)
    ap.add_argument("--out", required=True, help="Output directory (e.g. wheelhouse_calendar_data)")
    ap.add_argument(
        "--days", type=int, default=DEFAULT_DAYS_FORWARD,
        help=f"How many days forward (from today) to pull per listing (default {DEFAULT_DAYS_FORWARD}). "
        "The API itself allows up to a 3-year total range.",
    )
    ap.add_argument("--include-inactive", action="store_true", help="Include inactive listings (default: excluded)")
    ap.add_argument("--owned-only", action="store_true", help="Exclude managed/delegated listings (default: included)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore each listing's stored sync_date and re-fetch every listing regardless of "
        "whether it was already synced today. Not needed for routine nightly runs.",
    )
    ap.add_argument(
        "--date",
        default=None,
        help="Override 'today' (UTC, format YYYY-MM-DD) used for the same-day-skip check and the "
        "start of the forward window. Mainly for testing; defaults to the real current UTC date.",
    )
    args = ap.parse_args()

    include_managed = not args.owned_only
    sync_date = args.date or today_str()

    api_key = load_api_key(args.api_key_file)
    client = WheelhouseClient(api_key, verbose=args.verbose)

    if args.selftest:
        selftest(client, include_managed)
        return

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.join(args.out, "calendar"), exist_ok=True)

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
    cal_count = 0
    skipped = 0
    total_rows = 0
    for key, listing in listings_out.items():
        listing_id = listing.get("id")
        channel = listing.get("channel")

        cal_file = os.path.join(args.out, "calendar", f"{key}.json")
        if not args.force and already_synced_today(cal_file, sync_date):
            cal_count += 1
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

        record = {
            "listing_id": listing_id,
            "channel": channel,
            "synced_at": now_iso(),
            "sync_date": sync_date,
            "start_date": start_date,
            "end_date": end_date,
            "calendar": rows,
        }
        with open(cal_file, "w") as f:
            json.dump(record, f, indent=1)
        cal_count += 1
        total_rows += len(rows)
        if args.verbose:
            print(f"  OK {key}: {len(rows)} row(s), {start_date} to {end_date}")

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
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)

    fresh = cal_count - skipped
    print(
        f"Done. Listings: {len(listings_out)}. Calendars synced: {cal_count} "
        f"({fresh} freshly fetched, {skipped} already up to date for {sync_date}). "
        f"Rows fetched this run: {total_rows}. Errors: {len(errors)}."
    )
    if errors:
        print("Listings that failed:", [e["listing"] for e in errors])
    if not errors and cal_count == len(listings_out) and skipped == 0:
        print(f"All {len(listings_out)} listings freshly synced for {sync_date} -- 0 errors.")
    elif not errors and cal_count == len(listings_out):
        print(
            f"All listings have a calendar file synced for {sync_date} on disk "
            f"({fresh} fetched this run, {skipped} already done earlier today)."
        )


if __name__ == "__main__":
    main()
