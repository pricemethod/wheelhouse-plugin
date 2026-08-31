#!/usr/bin/env python3
"""
Direct-API sync for Wheelhouse listings + KPIs (rolling + monthly).
No Claude/MCP calls in the loop -- see _wh_client.py's docstring for why.

Usage:
  python3 sync_listings_kpis.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_data
  python3 sync_listings_kpis.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_data --selftest

--selftest fetches one listing and, for it, one rolling-KPI call and one
monthly-KPI call -- 3 calls total -- and prints exactly what happened. Run
this before a full sync the first time, or after any Wheelhouse API change.
Fixed 2026-07-28: previously used per_page=1 + list(generator), which on any
portfolio bigger than ~15-20 listings paginated through the ENTIRE portfolio
one listing per call (at ~1.2s/call) before ever checking anything, hanging
well past most shell timeouts with zero output. Now takes a single item via
next() and never materializes more than one page.

Managed listings: always requests include_managed_listings=true by default
(confirmed API param, see _wh_client.py docstring) so listings the account
manages on another Wheelhouse account's behalf (shared/delegated access) are
included alongside owned listings -- not just an account's own listings.
Pass --owned-only to restrict to owned listings only.

Output layout (all under --out):
  listings.json              -- one JSON object keyed by "{id}_{channel}", full listing record
  kpis/{id}_{channel}.json   -- {"listing_id", "channel", "synced_at", "sync_date", "rolling": {...}, "monthly": [...]}
  index.json                 -- sync metadata (see wheelhouse-data-sync-api SKILL.md for schema)

KPI trimming (to cut future read cost for consuming skills, not just this
script's own token cost): monthly rows with adr == null are dropped -- these
are null-padded future placeholder months carrying zero information (confirmed
pattern: every real/actual month has a non-null adr, even at 0% occupancy;
every month with no data at all shows adr: null). Any top-level key in the
rolling-KPI response whose value is a dict where every value is null is
dropped too (typically comp_set_* on listings with no matched comp set).

Same-day resume, cross-day always-refresh (redesigned 2026-07-28):
The requirement this serves is "run nightly and always pull every listing's
current KPIs" -- a scheduled nightly sync must NOT silently skip a listing
just because a file with that name happens to already exist from a previous
night. At the same time, a single sync attempt can get cut off partway
(confirmed: 47 listings x 2 calls x ~1.2s pacing is ~110s+, comfortably over
a 45s time-boxed shell timeout), and re-doing already-completed listings
from scratch on every retry wastes calls and time for no benefit.

The fix: each kpis/{key}.json now carries a "sync_date" field (the UTC
calendar date the sync that wrote it started, e.g. "2026-07-29") alongside
the existing "synced_at" timestamp. A listing is skipped ONLY if its file
already exists AND that file's "sync_date" equals today's date (or the date
passed via --date). Concretely:
  - Same day, second invocation (e.g. resuming after a timeout): listings
    already written earlier TODAY are skipped -- fast resume, no wasted calls.
  - A new day's run: every listing's stored sync_date is from a prior day
    (or the file doesn't exist yet for a new listing), so nothing is skipped
    -- every single listing gets a fresh pull, which is the whole point of
    running this nightly.
This makes the default behavior correct for the common nightly-refresh case
without needing a flag to be remembered/passed correctly every night. Old
kpis/{key}.json files from before this change (no "sync_date" key) are
treated as not-synced-today and will be refreshed on first run after
upgrading, which is the safe/correct behavior for stale-format files.

--force still exists, now meaning "ignore sync_date entirely, always
re-fetch every listing regardless of when it was last synced" -- for a
guaranteed fully-fresh pull (e.g. you suspect a partial/corrupt write, or
you changed --include-inactive/--owned-only and want every listing
re-evaluated under the new flags right now instead of waiting for the
date to roll over).

--date lets you override what "today" means for the skip check (format
YYYY-MM-DD, UTC). Mainly useful for testing the skip/resume logic itself,
or for deliberately treating a sync as "the same logical day" across a
run that crosses midnight UTC.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wh_client import WheelhouseClient, load_api_key  # noqa: E402


def trim_monthly(rows):
    return [r for r in rows if r.get("adr") is not None]


def trim_rolling(kpi):
    trimmed = {}
    for k, v in kpi.items():
        if isinstance(v, dict) and v and all(x is None for x in v.values()):
            continue
        trimmed[k] = v
    return trimmed


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def already_synced_today(kpi_file, sync_date):
    """True only if kpi_file exists AND its stored sync_date matches sync_date.
    Any read/parse failure or missing sync_date key is treated as NOT synced
    today (safe default: re-fetch rather than silently trust a file we can't
    verify the freshness of)."""
    if not os.path.exists(kpi_file):
        return False
    try:
        with open(kpi_file) as f:
            existing = json.load(f)
        return existing.get("sync_date") == sync_date
    except (json.JSONDecodeError, OSError):
        return False


def selftest(client, include_managed):
    print("=== SELF-TEST: 1 listing, 3 calls ===")
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

    for label, path in [
        ("rolling KPIs", f"/listings/{listing_id}/kpis"),
        ("monthly KPIs", f"/listings/{listing_id}/kpis/monthly"),
    ]:
        try:
            result = client.get(path, {"channel": channel})
            keys = list(result.keys()) if isinstance(result, dict) else f"list of {len(result)}"
            print(f"OK {label} -> {path} -- top-level keys/shape: {keys}")
        except RuntimeError as e:
            print(f"FAIL {label} -> {path}: {e}")
            sys.exit(1)
    print("=== SELF-TEST PASSED -- safe to run a full sync ===")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-key-file", required=True)
    ap.add_argument("--out", required=True, help="Output directory (wheelhouse_data)")
    ap.add_argument("--include-inactive", action="store_true", help="Include inactive listings (default: excluded)")
    ap.add_argument("--owned-only", action="store_true", help="Exclude managed/delegated listings (default: included)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore each listing's stored sync_date and re-fetch every listing regardless of "
        "whether it was already synced today. Use for a guaranteed fully-fresh pull; not needed "
        "for routine nightly runs, since a new calendar day already re-fetches everything by default.",
    )
    ap.add_argument(
        "--date",
        default=None,
        help="Override 'today' (UTC, format YYYY-MM-DD) used for the same-day-skip check. "
        "Mainly for testing; defaults to the real current UTC date.",
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
    os.makedirs(os.path.join(args.out, "kpis"), exist_ok=True)

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

    errors = []
    kpi_count = 0
    skipped = 0
    for key, listing in listings_out.items():
        listing_id = listing.get("id")
        channel = listing.get("channel")

        kpi_file = os.path.join(args.out, "kpis", f"{key}.json")
        if not args.force and already_synced_today(kpi_file, sync_date):
            kpi_count += 1
            skipped += 1
            if args.verbose:
                print(f"  SKIP {key} (already synced today, {sync_date} -- use --force to redo anyway)")
            continue

        try:
            rolling = client.get(f"/listings/{listing_id}/kpis", {"channel": channel})
            monthly_resp = client.get(f"/listings/{listing_id}/kpis/monthly", {"channel": channel})
            monthly_rows = monthly_resp.get("data", monthly_resp) if isinstance(monthly_resp, dict) else monthly_resp
        except RuntimeError as e:
            print(f"  ERROR {key}: {e}", file=sys.stderr)
            errors.append({"listing": key, "error": str(e)})
            continue

        record = {
            "listing_id": listing_id,
            "channel": channel,
            "synced_at": now_iso(),
            "sync_date": sync_date,
            "rolling": trim_rolling(rolling) if isinstance(rolling, dict) else rolling,
            "monthly": trim_monthly(monthly_rows) if isinstance(monthly_rows, list) else monthly_rows,
        }
        with open(kpi_file, "w") as f:
            json.dump(record, f, indent=1)
        kpi_count += 1
        if args.verbose:
            print(f"  OK {key}")

    index_path = os.path.join(args.out, "index.json")
    index = {}
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    index.setdefault("last_sync", {})
    index["last_sync"]["listings"] = now_iso()
    index["last_sync"]["kpis"] = now_iso()
    index["last_sync"]["kpis_sync_date"] = sync_date
    index["listing_count"] = len(listings_out)
    index["include_managed_listings"] = include_managed
    index["include_inactive_listings"] = args.include_inactive
    index["kpi_sync_errors"] = errors
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)

    fresh = kpi_count - skipped
    print(
        f"Done. Listings: {len(listings_out)}. KPIs synced: {kpi_count} "
        f"({fresh} freshly fetched, {skipped} already up to date for {sync_date}). "
        f"Errors: {len(errors)}."
    )
    if errors:
        print("Listings that failed:", [e["listing"] for e in errors])
    if not errors and kpi_count == len(listings_out) and skipped == 0:
        print(f"All {len(listings_out)} listings freshly synced for {sync_date} -- 0 errors.")
    elif not errors and kpi_count == len(listings_out):
        print(
            f"All listings have a KPI file synced for {sync_date} on disk "
            f"({fresh} fetched this run, {skipped} already done earlier today)."
        )


if __name__ == "__main__":
    main()
