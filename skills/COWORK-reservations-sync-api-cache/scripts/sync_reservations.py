#!/usr/bin/env python3
"""
Direct-API sync for Wheelhouse reservations -- both the nightly rolling sync
and the one-time (or periodic) historical backfill. No Claude/MCP calls in
the loop -- see _wh_client.py's docstring for why that matters here.

Two modes:
  --mode rolling    Nightly incremental sync. Fetches stay_date >= (today -
                    30 days) forward, per listing, filters out cancelled
                    reservations, writes one JSONL file per listing. Also
                    migrates anything that's aged out of a *previous* rolling
                    snapshot into the stable/ archive.
  --mode backfill   One-time (or occasional) historical pull. Fetches
                    stay_date in [today - N years, today - 30 days) per
                    listing, filters cancelled, writes straight into
                    stable/{year}.jsonl. Defaults to 1 year back (--years 1)
                    -- this default is deliberate and should not be increased
                    casually: a routine backfill should cover exactly one
                    year, full stop. Only pass a larger --years if the user
                    explicitly asks for deeper history; re-running backfill
                    with a larger --years later is safe and just extends
                    coverage further back without duplicating anything
                    already archived.

Usage:
  python3 sync_reservations.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_data --mode rolling
  python3 sync_reservations.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_data --mode backfill --years 1
  python3 sync_reservations.py --api-key-file /path/to/key.txt --out /path/to/wheelhouse_data --selftest

Requires listings.json (from the sibling wheelhouse-data-sync-api skill) to
already exist at --out/listings.json, keyed by "{id}_{channel}" -> listing
record with "id" and "channel" fields -- this script reads that to know which
listing/channel pairs to iterate, rather than re-fetching listings itself.
--out here MUST be the exact same directory the data-sync-api skill was run
against -- there is no way to guess this from elsewhere, and a wrong --out
fails loudly and immediately (see load_listings) rather than silently
creating an empty/wrong cache.

Endpoint path: uses /listings/{listing_id}/reservations. This is
high-confidence-but-not-directly-quoted from the live API reference -- see
_wh_client.py's docstring for the full reasoning (the doc's "Reservations"
section didn't render during verification, but every other listing-scoped
endpoint follows this identical path+channel-query-param pattern with zero
exceptions, and the connected Wheelhouse MCP's generated tool schema requires
the same shape). Run --selftest first; a 404 there means this path guess was
wrong for this endpoint specifically.

Output layout (all under --out):
  reservations/rolling/{id}_{channel}.jsonl   -- rewritten each rolling run
  reservations/stable/{year}.jsonl            -- append-only, built by backfill
                                                  and by rolling's aging step
  index.json                                  -- sync metadata (merged, not
                                                  overwritten), including the
                                                  rolling/backfill progress
                                                  ledgers described below

Cancellation handling: confirmed on a real account that cancelled
reservations persist in GetReservations/`/reservations` with
status "Canceled" (single L) rather than disappearing -- every record with
that status (case-insensitive, "Cancelled" also matched) is dropped before
it's ever written to any cache file. Any other status value that isn't
"Accepted" gets logged to index.json's unrecognized_reservation_statuses so a
new status this script hasn't seen yet is surfaced, not silently mishandled.

Same-day resume, cross-day always-refresh for --mode rolling (added
2026-07-28, applying the same fix already verified end-to-end on the sibling
wheelhouse-data-sync-api skill's KPI sync): the requirement is "run nightly
and always pull every listing's current reservation window" -- a scheduled
nightly sync must never silently skip a listing just because a rolling file
with that name already exists from a previous night. At the same time, a
single sync attempt can get cut off partway (reservations can need MORE than
2 calls per listing if a listing has a lot of history in its rolling window,
so this is if anything a bigger risk here than in the KPI sync's fixed
2-calls-per-listing case), and re-doing already-completed listings from
scratch on every retry wastes calls and time for no benefit.

Unlike the KPI sync, a rolling reservations file is a plain JSONL array of
reservation records with no room for a per-file "sync_date" marker without
polluting every record. So the freshness ledger lives in index.json instead,
under "reservations_rolling_progress": {"{id}_{channel}": {"sync_date":
"YYYY-MM-DD", "cutoff": "...", "synced_at": "..."}}. A listing is skipped
ONLY if this ledger has an entry for it AND that entry's sync_date equals
today's date (or the date passed via --date):
  - Same day, second invocation (e.g. resuming after a timeout): listings
    already recorded as synced earlier TODAY are skipped -- fast resume.
  - A new day's run: every listing's recorded sync_date is from a prior day,
    so nothing is skipped -- every listing's rolling window gets refetched,
    which is the whole point of running this nightly (the window itself
    shifts forward one day too, so a stale file would be wrong, not just
    old).
The ledger is written back to index.json after EVERY listing (not just once
at the end), so a run truncated mid-portfolio doesn't lose the resume
progress for listings it already finished before the cutoff.

--force ignores the ledger entirely and re-fetches every listing regardless
of when it was last synced. --date overrides what "today" means (UTC,
format YYYY-MM-DD) for the same-day-skip check -- mainly for testing.

Backfill coverage-based resume (added 2026-07-28): --mode backfill gets the
same problem (a truncated run over many listings shouldn't have to restart
from scratch) but a different fix, since backfill isn't a daily operation --
"already done today" isn't the right question; "already covers the date
range this call would fetch" is. index.json's "reservations_backfill_progress"
ledger records, per listing, the [start_date, end_date) range last
successfully backfilled. A listing is skipped if its recorded range already
covers (is a superset of) the range this invocation would request -- so
retrying the same backfill command after a timeout skips everything already
done and finishes the rest, while asking for a genuinely wider range (a
later --years, or backfill run again after enough time has passed that the
implied dates shifted) correctly re-fetches. --force bypasses this the same
way it does for rolling.

Dates internally are computed from the real UTC calendar date unless
overridden by --date (previously this script used naive
datetime.date.today(), i.e. local system time, which could disagree with
the UTC-based sync_date stamps the sibling KPI sync uses -- now consistent).
"""
import argparse
import datetime
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wh_client import WheelhouseClient, load_api_key  # noqa: E402

KNOWN_GOOD_STATUS = "accepted"
CANCELLED_STATUSES = {"canceled", "cancelled"}


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_today(date_override=None):
    """Returns a datetime.date. Uses --date (YYYY-MM-DD) if given, otherwise
    the real current UTC calendar date (not local system time -- keeps this
    script's date math consistent with the sibling KPI sync's sync_date
    stamps)."""
    if date_override:
        return datetime.datetime.strptime(date_override, "%Y-%m-%d").date()
    return datetime.datetime.now(datetime.timezone.utc).date()


def load_listings(out_dir):
    path = os.path.join(out_dir, "listings.json")
    if not os.path.exists(path):
        sys.exit(
            f"{path} not found. This skill depends on wheelhouse-data-sync-api "
            f"having already been run against this exact --out directory -- "
            f"run its sync_listings_kpis.py first (or re-run it here) so "
            f"listings.json exists at this path. Don't assume --out matches "
            f"whatever directory was used for a previous invocation of either "
            f"skill unless you've confirmed it: a user may point this at a "
            f"different folder than the data-sync-api skill used, in which "
            f"case this file simply won't be here yet."
        )
    with open(path) as f:
        listings = json.load(f)
    pairs = []
    for key, l in listings.items():
        listing_id = l.get("id")
        channel = l.get("channel")
        if listing_id and channel:
            pairs.append((str(listing_id), channel))
    return pairs


def load_jsonl(path):
    records = []
    if path and os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def record_key(r):
    for field in ("id", "confirmation_code"):
        if r.get(field):
            return f"{field}:{r[field]}"
    return f"composite:{r.get('listing_id')}:{r.get('start_date')}:{r.get('end_date')}:{r.get('channel')}"


def filter_and_tag(records, listing_id, channel, unrecognized_statuses):
    kept = []
    for r in records:
        status = (r.get("status") or "").strip().lower()
        if status in CANCELLED_STATUSES:
            continue
        if status and status != KNOWN_GOOD_STATUS:
            unrecognized_statuses.add(r.get("status"))
        r["listing_id"] = listing_id
        r["channel"] = channel
        kept.append(r)
    return kept


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def append_stable(stable_dir, records, existing_keys_cache):
    """Appends records into stable/{year}.jsonl, deduped by record_key."""
    by_year = defaultdict(list)
    for r in records:
        year = (r.get("start_date") or "")[:4] or "unknown"
        by_year[year].append(r)

    written = {}
    for year, recs in by_year.items():
        path = os.path.join(stable_dir, f"{year}.jsonl")
        if year not in existing_keys_cache:
            existing_keys_cache[year] = {record_key(r) for r in load_jsonl(path)}
        existing_keys = existing_keys_cache[year]
        new_recs = [r for r in recs if record_key(r) not in existing_keys]
        if not new_recs:
            continue
        os.makedirs(stable_dir, exist_ok=True)
        with open(path, "a") as f:
            for r in new_recs:
                f.write(json.dumps(r) + "\n")
                existing_keys.add(record_key(r))
        written[year] = written.get(year, 0) + len(new_recs)
    return written


def load_index(out_dir):
    index_path = os.path.join(out_dir, "index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return json.load(f)
    return {}


def save_index(out_dir, index):
    index_path = os.path.join(out_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)


def selftest(client, out_dir, date_override):
    print("=== SELF-TEST: 1 listing, reservations endpoint ===")
    pairs = load_listings(out_dir)
    if not pairs:
        print("No listing pairs found in listings.json.")
        sys.exit(1)
    listing_id, channel = pairs[0]
    today = utc_today(date_override)
    cutoff = (today - datetime.timedelta(days=30)).isoformat()
    try:
        result = client.get(
            f"/listings/{listing_id}/reservations",
            {"channel": channel, "date_filter_type": "stay_date", "start_date": cutoff, "per_page": 5},
        )
        items = result if isinstance(result, list) else result.get("data", result.get("result", []))
        print(f"OK /listings/{listing_id}/reservations -> {len(items)} record(s) on first page")
        if items:
            print(f"Sample record keys: {sorted(items[0].keys())}")
    except RuntimeError as e:
        print(f"FAIL: {e}")
        print(
            "If this is a 404, the path is wrong -- edit the "
            "'/listings/{listing_id}/reservations' string in this script "
            "(selftest, sync_rolling, and sync_backfill) and retry --selftest."
        )
        sys.exit(1)
    print("=== SELF-TEST PASSED ===")


def sync_rolling(client, out_dir, sync_date, force=False, verbose=False):
    pairs = load_listings(out_dir)
    rolling_dir = os.path.join(out_dir, "reservations", "rolling")
    stable_dir = os.path.join(out_dir, "reservations", "stable")
    today = utc_today(sync_date)
    cutoff = (today - datetime.timedelta(days=30)).isoformat()

    index = load_index(out_dir)
    index.setdefault("last_sync", {})
    progress = index.setdefault("reservations_rolling_progress", {})

    unrecognized = set(index.get("unrecognized_reservation_statuses", []))
    errors = []
    existing_keys_cache = {}
    total_written = 0
    total_aged_out = 0
    fresh_count = 0
    skipped_count = 0

    for listing_id, channel in pairs:
        key = f"{listing_id}_{channel}"
        rolling_path = os.path.join(rolling_dir, f"{key}.jsonl")

        entry = progress.get(key)
        if not force and entry and entry.get("sync_date") == sync_date:
            skipped_count += 1
            if verbose:
                print(f"  SKIP {key} (already synced today, {sync_date} -- use --force to redo anyway)")
            continue

        previous = load_jsonl(rolling_path)
        try:
            fetched = list(
                client.get_paginated(
                    f"/listings/{listing_id}/reservations",
                    {"channel": channel, "date_filter_type": "stay_date", "start_date": cutoff},
                )
            )
        except RuntimeError as e:
            print(f"  ERROR {key}: {e}", file=sys.stderr)
            errors.append({"listing": key, "error": str(e)})
            continue

        current = filter_and_tag(fetched, listing_id, channel, unrecognized)
        write_jsonl(rolling_path, current)
        total_written += len(current)
        fresh_count += 1

        current_keys = {record_key(r) for r in current}
        aged_out = [
            r for r in previous
            if record_key(r) not in current_keys and (r.get("end_date") or "") < cutoff
        ]
        if aged_out:
            written = append_stable(stable_dir, aged_out, existing_keys_cache)
            total_aged_out += sum(written.values())
        if verbose:
            print(f"  OK {key}: {len(current)} rolling, {len(aged_out)} aged out")

        # Persist progress after every listing, not just at the end -- a run
        # truncated by a timeout must not lose resume state for listings it
        # already finished before the cutoff.
        progress[key] = {"sync_date": sync_date, "cutoff": cutoff, "synced_at": now_iso()}
        index["unrecognized_reservation_statuses"] = sorted(unrecognized)
        index["last_sync"]["reservations"] = now_iso()
        index["last_sync"]["reservations_sync_date"] = sync_date
        index["reservations_stable_cutoff"] = cutoff
        index["reservations_rolling_errors"] = errors
        save_index(out_dir, index)

    return {
        "cutoff": cutoff,
        "sync_date": sync_date,
        "listings_total": len(pairs),
        "listings_fresh": fresh_count,
        "listings_skipped": skipped_count,
        "errors": errors,
        "reservations_written": total_written,
        "aged_out_to_stable": total_aged_out,
        "unrecognized_statuses": sorted(unrecognized),
    }


def sync_backfill(client, out_dir, years, sync_date, force=False, verbose=False):
    pairs = load_listings(out_dir)
    stable_dir = os.path.join(out_dir, "reservations", "stable")
    today = utc_today(sync_date)
    cutoff = (today - datetime.timedelta(days=30)).isoformat()
    start_date = (today - datetime.timedelta(days=365 * years)).isoformat()

    index = load_index(out_dir)
    index.setdefault("last_sync", {})
    progress = index.setdefault("reservations_backfill_progress", {})

    unrecognized = set(index.get("unrecognized_reservation_statuses", []))
    errors = []
    existing_keys_cache = {}
    total_written = 0
    fresh_count = 0
    skipped_count = 0

    for listing_id, channel in pairs:
        key = f"{listing_id}_{channel}"

        entry = progress.get(key)
        already_covered = (
            entry
            and not force
            and entry.get("start_date", "9999-99-99") <= start_date
            and entry.get("end_date", "0000-00-00") >= cutoff
        )
        if already_covered:
            skipped_count += 1
            if verbose:
                print(
                    f"  SKIP {key} (already backfilled {entry['start_date']} to {entry['end_date']}, "
                    f"covers requested {start_date} to {cutoff} -- use --force to redo anyway)"
                )
            continue

        try:
            fetched = list(
                client.get_paginated(
                    f"/listings/{listing_id}/reservations",
                    {
                        "channel": channel,
                        "date_filter_type": "stay_date",
                        "start_date": start_date,
                        "end_date": cutoff,
                    },
                )
            )
        except RuntimeError as e:
            print(f"  ERROR {key}: {e}", file=sys.stderr)
            errors.append({"listing": key, "error": str(e)})
            continue

        tagged = filter_and_tag(fetched, listing_id, channel, unrecognized)
        written = append_stable(stable_dir, tagged, existing_keys_cache)
        total_written += sum(written.values())
        fresh_count += 1
        if verbose:
            print(f"  OK {key}: {sum(written.values())} backfilled ({written})")

        # Persist progress after every listing so a truncated backfill can
        # resume instead of restarting the whole portfolio.
        progress[key] = {"start_date": start_date, "end_date": cutoff, "completed_at": now_iso()}
        index["unrecognized_reservation_statuses"] = sorted(unrecognized)
        index["last_sync"]["reservations_backfill"] = now_iso()
        index["reservations_backfill_years"] = years
        index["reservations_backfill_errors"] = errors
        save_index(out_dir, index)

    return {
        "start_date": start_date,
        "end_date": cutoff,
        "years": years,
        "listings_total": len(pairs),
        "listings_fresh": fresh_count,
        "listings_skipped": skipped_count,
        "errors": errors,
        "reservations_written": total_written,
        "unrecognized_statuses": sorted(unrecognized),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-key-file", required=True)
    ap.add_argument("--out", required=True, help="Output directory (wheelhouse_data) -- must match wheelhouse-data-sync-api's --out")
    ap.add_argument("--mode", choices=["rolling", "backfill"])
    ap.add_argument(
        "--years", type=int, default=1,
        help="Backfill lookback in years (default: 1 -- a routine backfill should stay at 1; "
        "only raise this if the user explicitly asks for deeper history)",
    )
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore the resume ledger and re-fetch every listing regardless of what's already "
        "recorded as synced/backfilled. Not needed for routine nightly rolling runs (a new "
        "calendar day already re-fetches everything); mainly for a guaranteed fully-fresh pull.",
    )
    ap.add_argument(
        "--date",
        default=None,
        help="Override 'today' (UTC, format YYYY-MM-DD) used for date math and the rolling "
        "same-day-skip check. Mainly for testing; defaults to the real current UTC date.",
    )
    args = ap.parse_args()

    api_key = load_api_key(args.api_key_file)
    client = WheelhouseClient(api_key, verbose=args.verbose)

    if args.selftest:
        selftest(client, args.out, args.date)
        return

    if not args.mode:
        sys.exit("--mode rolling or --mode backfill is required (or use --selftest)")

    sync_date = args.date or utc_today().isoformat()

    if args.mode == "rolling":
        result = sync_rolling(client, args.out, sync_date, force=args.force, verbose=args.verbose)
        print(
            f"Rolling sync done for {result['sync_date']} (cutoff {result['cutoff']}). "
            f"Listings: {result['listings_total']} total, {result['listings_fresh']} freshly fetched, "
            f"{result['listings_skipped']} already up to date for today. "
            f"Reservations cached: {result['reservations_written']}. "
            f"Aged into stable/: {result['aged_out_to_stable']}. "
            f"Errors: {len(result['errors'])}."
        )
        if not result["errors"] and result["listings_fresh"] + result["listings_skipped"] == result["listings_total"]:
            if result["listings_skipped"] == 0:
                print(f"All {result['listings_total']} listings freshly synced for {result['sync_date']} -- 0 errors.")
            else:
                print(
                    f"All listings covered for {result['sync_date']} "
                    f"({result['listings_fresh']} fetched this run, {result['listings_skipped']} already done earlier today)."
                )
    else:
        result = sync_backfill(client, args.out, args.years, sync_date, force=args.force, verbose=args.verbose)
        print(
            f"Backfill done ({result['years']}yr, {result['start_date']} to {result['end_date']}). "
            f"Listings: {result['listings_total']} total, {result['listings_fresh']} freshly fetched, "
            f"{result['listings_skipped']} already covered from a prior backfill. "
            f"Reservations archived: {result['reservations_written']}. "
            f"Errors: {len(result['errors'])}."
        )
        if not result["errors"] and result["listings_fresh"] + result["listings_skipped"] == result["listings_total"]:
            print(
                f"All {result['listings_total']} listings have backfill coverage for "
                f"{result['start_date']} to {result['end_date']} -- 0 errors."
            )

    if result["unrecognized_statuses"]:
        print(f"Unrecognized reservation statuses seen: {result['unrecognized_statuses']}")
    if result["errors"]:
        print("Listings that failed:", [e["listing"] for e in result["errors"]])


if __name__ == "__main__":
    main()
