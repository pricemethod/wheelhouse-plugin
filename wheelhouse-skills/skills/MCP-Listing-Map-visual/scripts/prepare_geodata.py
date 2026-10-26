#!/usr/bin/env python3
"""
prepare_geodata.py — address dedup / geocode-batch prep / merge+jitter for
the MCP-Listing-Map-visual skill. Python standard library only.

Input can be EITHER:
  - a CSV file (e.g. a spreadsheet export), or
  - a JSON file containing a list of record objects (e.g. dumped straight
    from an MCP tool's listings response — `json.dump(listings, open(...))`)
The two subcommands auto-detect which one you passed by file extension.

Workflow:
  1) extract-addresses:  read the listings, strip unit/suite/floor noise
     from each address to get a smaller set of "base addresses" (one per
     building), and print them in batches of 10.
  2) merge:               after you've geocoded each base address into a
     {base_address: [lat, lng]} JSON mapping, merge that back onto every
     original record, add small jitter so units in the same building don't
     perfectly overlap on the map, and write the final records (all original
     fields + lat + lng) as JSON + CSV.

Usage:
  python prepare_geodata.py extract-addresses listings.json \
      --address-col address --out addresses_batches.json

  python prepare_geodata.py merge listings.json geocodes.json \
      --address-col address --out-json final.json --out-csv final.csv
"""
import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict

LIST_KEYS = ('listings', 'results', 'data', 'records')


def _unwrap(data):
    """Tolerate a top-level {"listings": [...]} / {"data": [...]} wrapper."""
    if isinstance(data, dict):
        for key in LIST_KEYS:
            if isinstance(data.get(key), list):
                return data[key]
    return data


def load_records(path: str, skiprows: int = 0) -> list:
    """Load either a CSV file or a JSON file (list of record dicts) into a
    list of dicts. Detected by extension; falls back to sniffing content."""
    lower = path.lower()
    if not lower.endswith('.csv'):
        with open(path, encoding='utf-8') as f:
            head = f.read(1024).lstrip()
        if lower.endswith('.json') or head.startswith(('[', '{')):
            with open(path, encoding='utf-8') as f:
                return list(_unwrap(json.load(f)))
    with open(path, encoding='utf-8-sig', newline='') as f:
        for _ in range(skiprows):
            next(f, None)
        return list(csv.DictReader(f))


def require_column(records: list, col: str):
    if not records:
        sys.exit("No records found in input.")
    if col not in records[0]:
        sys.exit(f"Column '{col}' not found. Columns: {list(records[0].keys())}")


def strip_unit(address: str) -> str:
    """Remove unit/suite/apt/floor/building noise so multiple units in the
    same building collapse to one geocoding target."""
    a = address
    a = re.sub(r',?\s*(Unit|Suite|Apt|#)\.?\s*[\w-]+', '', a, flags=re.I)
    a = re.sub(r',\s*\d+(st|nd|rd|th)\s+Floor', '', a, flags=re.I)
    a = re.sub(r',\s*(Building|Bldg)\.?\s*\d+', '', a, flags=re.I)
    a = re.sub(r',?\s*cabins?\s+\d+\s+and\s+\d+', '', a, flags=re.I)
    a = re.sub(r'\s+,', ',', a)
    a = re.sub(r',\s*,', ',', a)
    return a.strip()


def normalize_key(address: str) -> str:
    """A looser key for dedup, so trivial formatting differences (Rd vs
    Road, extra 'Unit' text that strip_unit missed, etc.) still collapse."""
    k = address.lower()
    k = re.sub(r'[.,]', '', k)
    for a, b in [('road', 'rd'), ('street', 'st'), ('drive', 'dr'),
                 ('lane', 'ln'), ('avenue', 'ave')]:
        k = k.replace(a, b)
    k = re.sub(r'\s+', ' ', k).strip()
    return k


def cmd_extract_addresses(args):
    records = load_records(args.input_path, args.skiprows)
    require_column(records, args.address_col)

    seen, addresses = set(), []
    for r in records:
        base = strip_unit(str(r.get(args.address_col) or ''))
        key = normalize_key(base)
        if key not in seen:
            seen.add(key)
            addresses.append(base)

    batches = [addresses[i:i + 10] for i in range(0, len(addresses), 10)]
    out = {"total_rows": len(records), "unique_addresses": len(addresses), "batches": batches}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print(f"{len(records)} rows -> {len(addresses)} unique base addresses -> {len(batches)} batches of <=10")
    print(f"Wrote {args.out}")
    print("\nNext: geocode each base address (one query per address, top hit only),")
    print("then build a JSON object mapping each base address string to its [lat, lng], e.g.:")
    print('  {"100 Example Rd, Springfield, ST 00000, United States": [40.0, -75.0], ...}')


def cmd_merge(args):
    records = load_records(args.input_path, args.skiprows)
    require_column(records, args.address_col)

    with open(args.geocodes_json, encoding='utf-8') as f:
        geocodes = json.load(f)

    bases = [strip_unit(str(r.get(args.address_col) or '')) for r in records]

    missing = sorted(set(bases) - set(geocodes.keys()))
    if missing:
        print(f"WARNING: {len(missing)} base addresses have no geocode entry:", file=sys.stderr)
        for m in missing[:20]:
            print(f"  {m!r}", file=sys.stderr)
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more", file=sys.stderr)
        print("Add these to the geocodes JSON (or fix the address text) and re-run merge.", file=sys.stderr)

    # jitter duplicate coords (multi-unit buildings) so pins don't fully overlap
    seen = defaultdict(int)
    out = []
    for r, base in zip(records, bases):
        coord = geocodes.get(base)
        if not coord:
            continue
        lat, lng = float(coord[0]), float(coord[1])
        key = (round(lat, 6), round(lng, 6))
        n = seen[key]
        seen[key] += 1
        if n:
            angle = n * 2.399963  # golden angle -> even spiral spread
            rad = 0.00015 * (n ** 0.5)  # ~15-20m per step, grows with count
            lat += rad * math.cos(angle)
            lng += rad * math.sin(angle)
        out.append({**r, 'lat': lat, 'lng': lng})

    if args.out_json:
        with open(args.out_json, 'w', encoding='utf-8') as f:
            json.dump(out, f)
        print(f"Wrote {args.out_json} ({len(out)} records)")
    if args.out_csv and out:
        cols = list(dict.fromkeys(k for r in out for k in r))
        with open(args.out_csv, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in out:
                # list-valued fields (e.g. amenities) are stringified for CSV only
                w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v
                            for k, v in r.items()})
        print(f"Wrote {args.out_csv} ({len(out)} records)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)

    p1 = sub.add_parser('extract-addresses', help='Dedup + batch addresses for geocoding')
    p1.add_argument('input_path')
    p1.add_argument('--address-col', default='Address')
    p1.add_argument('--skiprows', type=int, default=0)
    p1.add_argument('--out', default='addresses_batches.json')
    p1.set_defaults(func=cmd_extract_addresses)

    p2 = sub.add_parser('merge', help='Merge geocodes back onto the records, jitter, write final data')
    p2.add_argument('input_path')
    p2.add_argument('geocodes_json', help='JSON: {base_address: [lat, lng], ...}')
    p2.add_argument('--address-col', default='Address')
    p2.add_argument('--skiprows', type=int, default=0)
    p2.add_argument('--out-json', default='final_properties.json')
    p2.add_argument('--out-csv', default='final_properties.csv')
    p2.set_defaults(func=cmd_merge)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
