---
name: MCP-Listing-Map-visual
description: Build an interactive, filterable HTML map of a Wheelhouse listing portfolio pulled live from the connected Wheelhouse MCP — fetching address, tags/amenities, unit name, nickname, and listing IDs directly from the tool rather than from an uploaded file — geocoding the addresses, and producing a self-contained map with bedroom/category chip filters, a multi-select amenities checklist, hover popups, a slide-out filtered/in-view list panel, and CSV export. Use whenever the user asks to "map," "plot," or "visualize" their portfolio/listings/units ("map my properties," "show my listings on a map," "pull my units from Wheelhouse and map them") — trigger even without a file upload, since data should come from the MCP. Also use to add a filter/popup field/export column to a map this skill built before, to refresh a map with the latest MCP data, or to tag the listings selected on the map (writes tags via wheelhouse_rmPutTags after explicit confirmation).
---

# Property Map Builder

Turns a live Wheelhouse listing portfolio — fetched from the Wheelhouse MCP,
not a CSV upload — into a single self-contained HTML page: a Leaflet map
with sidebar filters, hover popups, and a slide-out list panel that exports
to CSV. It was built from a run that mapped about 160 short-term-rental listings,
first from a CSV export and then straight from the Wheelhouse MCP.

## Overview of the pipeline

1. **Find and fetch the portfolio from the MCP** — paginate through every
   active listing, capturing name, nickname, address, unit ID(s), and
   amenities/tags. Inspect the *actual* response shape rather than assuming
   field names in advance.
2. **Geocode every address** with whatever place-search or geocoding tool your
   client has.
3. **Derive amenities from tags/name if there's no explicit amenities
   field** — same conservative heuristic as before, now applied to
   MCP-sourced text instead of CSV columns.
4. **Fill in the bundled HTML template** (`assets/map_template.html`) with
   the fetched, geocoded data.
5. **Validate, save, and present the page.**

Read this whole file before starting.

## Step 1: Pull the portfolio from the MCP

**Identify the tool.** The listings endpoint is `wheelhouse_rmGetListings`.
If the Wheelhouse MCP isn't connected, ask the user to connect it
(`https://mcp.usewheelhouse.com/mcp`) before falling back to a CSV upload —
don't assume a file is coming.

**Don't assume field names — inspect the first response.** Different
PMS/listings tools name things differently, and even within Wheelhouse the
skill only documents the fields relevant to pricing/pacing, not necessarily
every field this map needs. Fetch one small page first and print/inspect the
raw JSON keys before writing any parsing code. You're looking for:
- A **unit name** (Wheelhouse: `title`).
- A **unit nickname**, if the account uses one (Wheelhouse: `nickname`).
- A full **address** (may be one field or split across street/city/state/zip
  — concatenate if split).
- **Unit ID(s)**. The field the user wants as "unit IDs" is **`wheelhouse_id`**
  (the Wheelhouse-internal ID, passed with `channel=wheelhouse` on other
  calls) — always fetch and carry this through as `WheelhouseId`. Wheelhouse
  listings separately expose `id` (the *channel's* listing ID, e.g. the
  Airbnb/VRBO-side ID, paired with that listing's own `channel` value) —
  this is optional extra context, not the primary ask, so include it as
  `ChannelId`/`Channel` when it's easy to carry along but don't hold up the
  map on it, and don't confuse the two: `id` alone is meaningless without
  its matching `channel`, while `wheelhouse_id` is stable and unambiguous on
  its own.
- **Amenities/tags**, if present as a field — could be a list on the listing
  object itself, or require a separate tags call. If nothing amenity-like
  comes back on the listing object, plan to derive it in Step 3 instead.
- A **filterable category field** if the user wants one beyond amenities
  (e.g. bedroom count, property type) — check whether it's on the listing
  object or requires a separate preferences/details call.

**Paginate the full portfolio.** Never build the map from a partial pull.
For Wheelhouse: call `wheelhouse_rmGetListings` with `exclude_inactive=true`
(default, unless the user wants inactive units too) and keep paging until a
page returns fewer items than `per_page` — it returns managed listings
alongside owned ones automatically, so a partial pull silently drops units
the user does have access to. Respect rate limits (batch endpoints where
available; back off with jitter on 429s).

**Write the fetched records to a local JSON file** (where your client can
write files) as a plain list of per-unit objects (`json.dump(records, open('listings.json', 'w'))`) before
moving on — this gives Step 2's script something concrete to work from and
means a slow/rate-limited MCP fetch doesn't have to be repeated if a later
step fails.

**If the Wheelhouse MCP can't be connected**, fall back to asking the
user for a CSV — `scripts/prepare_geodata.py` accepts either input (see
Step 2), so the rest of the pipeline is unaffected either way.

## Step 2: Geocode addresses

Use `scripts/prepare_geodata.py`, which accepts either the JSON file you
just wrote or a CSV, auto-detected by extension:

```bash
python3 scripts/prepare_geodata.py extract-addresses listings.json \
  --address-col address --out addresses_batches.json
```

(Use whatever the address field is actually called in the fetched
records — check what you printed in Step 1.)

This strips unit/suite/floor/building noise so multiple units in the same
building collapse to one geocoding target, and prints the unique base
addresses in batches of 10. The script uses the Python standard library only.

For each batch, geocode one query per address and take the top hit's
latitude/longitude. Build a JSON mapping of
`{base_address_string: [lat, lng]}` as you go — save it to a file
(`geocodes.json`) incrementally so a dropped connection doesn't lose earlier
batches.

**Gotchas:**
- Some addresses won't resolve on the first try (typos, rural roads, resort
  sub-addresses). Retry with a simplified query (drop the unit/building
  suffix, or fall back to "street, town, state zip"). A same-town fallback
  coordinate is acceptable for the rare unresolvable one — better than
  dropping the row.
- Once you think you have full coverage, run the merge step — it will tell
  you exactly which base addresses are still missing:

```bash
python3 scripts/prepare_geodata.py merge listings.json geocodes.json \
  --address-col address \
  --out-json final_properties.json --out-csv final_properties.csv
```

This also **jitters coincident coordinates** (multiple units in one
building) in a small spiral so overlapping pins are still clickable/visible,
and carries through every original field plus the new `lat`/`lng` — list-
valued fields like an `amenities` array survive intact in the JSON output
(the CSV output stringifies them, which is fine since the map template
consumes the JSON, not the CSV).

## Step 3: Derive amenities if there's no explicit field

**Don't assume an empty `amenities` array means no amenity-like data
exists anywhere.** In a live run against Wheelhouse, every listing's own
`amenities` field came back `[]`, but a separate per-listing endpoint
(`wheelhouse_rmGetTags`) returned real tags for a subset of listings (e.g.
"Ski", "Beach Access", "Oceanfront", plus non-amenity tags like pricing-
strategy labels or test markers). Fetching tags requires one call per
listing — watch the rate limit (read the `X-RateLimit-*` headers where
visible, wait `Retry-After` seconds on a 429) and warn the user before a
portfolio-wide tag pull.

Whether to use that tag data as the map's amenities filter is a judgment
call, not an automatic substitution: **ask the user** ("your listings'
`amenities` field is empty, but I found per-listing tags like X/Y/Z via a
separate endpoint — want me to use those as the amenities filter, or leave
amenities empty?") rather than silently picking one. In one run the account
turned out to be intentionally-empty sample/demo data, and the user asked
to keep amenities empty rather than substitute tags. Don't re-litigate this
choice on a later refresh of the same map without being asked — carry
forward whatever the user decided the first time.

If the MCP didn't return a ready-made amenities/tags list, derive one from
whatever free text you do have (unit name/title, and any tags field),
exactly as with a CSV. Example (waterfront, from the original reference
run):

```python
import re
WATER = re.compile(r'lakefront|riverfront|waterfront|lakeside|riverside|\bdock\b|water access|shoreline', re.I)
for r in records:
    tagged = any('_Water_' in t for t in (r.get('tags') or []))
    named = bool(WATER.search(r.get('title') or ''))
    r['Amenities'] = ['Waterfront'] if (tagged or named) else []
```

Generalize this per amenity you're deriving (pet-friendly, pool, hot tub,
etc.), then combine into one list-valued `Amenities` column
(`[['Waterfront','Pet Friendly'], ['Pool'], [], ...]`) — the template's
amenities filter expects a list per row, not a single Yes/No flag, so it can
show multiple amenities per unit and let the user check several at once.

**Be conservative about false positives**: a listing calling itself "lake
view," "walk to the lake," or "near the lake" is describing proximity, not
direct access — don't match on those. Cross-check your regex against a few
category-adjacent listings before finalizing, and tell the user the
heuristic you used and its limits.

## Step 4: Fill in the HTML template

Copy `assets/map_template.html` — don't build a map from scratch. It's a
complete, tested Leaflet map styled to the **Wheelhouse design system**
(magenta brand accent, sky-blue secondary, Hanken Grotesk headlines, Inter
body/UI, Space Mono eyebrows/labels, 8px-radius cards, pill-shaped chips
and badges, light-gray page with white cards — see "Design system" below)
with:
- A **chip filter** (`CHIP_FIELD`, defaults to `Bedrooms`) — multi-select
  buttons for a numeric/small-cardinality categorical field.
- An **amenities filter** (`AMENITY_FIELD`, defaults to `Amenities`) — a
  checklist built from the union of every listing's amenity list, with
  OR-matching (a listing matches if it has *any* checked amenity; nothing
  checked shows everyone). This is the piece that replaced the old
  single-boolean waterfront toggle from the CSV-based version — use it for
  any list-valued attribute, not just amenities.
- Hover-triggered Leaflet popups showing name, nickname, address, unit
  ID(s) (WheelhouseId always, ChannelId/Channel when present), bedroom-style
  tag, and amenity tags.
- A slide-out list panel with a "limit to current map view" checkbox
  (filters against `map.getBounds()`) and a CSV export button (builds a
  `Blob`, no server needed) — the export already includes Nickname,
  WheelhouseId, ChannelId, Channel, and the joined Amenities list.

**Adapt these pieces for the new dataset:**
1. `<title>` and the header `<h1>`/`.tagline` text.
2. `CHIP_FIELD` and `AMENITY_FIELD` constants near the top of the
   `<script>` — set them to whatever your final JSON actually calls those
   fields (they default to `'Bedrooms'` and `'Amenities'`).
3. If the user wants more identifying fields in the popup/list/CSV beyond
   Name/Nickname/WheelhouseId/ChannelId/Channel/Address (e.g. a channel
   URL, a market name), add them alongside the existing ones in the popup
   template, the list table, and the CSV header/row-builder — all three
   live in the same `<script>` block.
4. Replace the `const PROPERTIES = __DATA__` line with the new data. Load
   `final_properties.json`, minify it (`json.dump(..., separators=(',',
   ':'))`), and substitute it in with a script — don't hand-edit a
   150-row JSON literal into the file.

After editing, **validate before shipping**:
- Extract the `<script>...</script>` body and run `node --check` on it to
  catch syntax errors from the templating.
- Re-parse the embedded `PROPERTIES` array with `json.loads` to confirm the
  injected data is valid JSON, has the expected row count, and that
  `Amenities` (or whatever you renamed it to) is a list on every row, not a
  bare string.

### Design system

`map_template.html` is styled to Wheelhouse's brand, defined as CSS custom
properties on `:root` — change the design by editing those variables, not
by hunting through individual rules:

- **Colors**: `--brand` `#E80EDF` (primary — used sparingly, as an accent:
  the "View list" button, active chip, brand-tinted bed-count tag, marker
  highlight for listings that have an amenity — never as a page-wide fill),
  `--brand-deep` `#BD08B6` (hover state, small text links), `--sky`
  `#57B0E0` / `--sky-tint` `#E1F1FA` (secondary accent — Export CSV/Copy IDs
  buttons, amenity badges), `--green`/`--green-tint` (success, e.g. the
  copy-succeeded note), `--amber`/`--amber-tint` (caution, e.g. the
  no-results note), `--red`/`--red-tint` (reserved, not currently used —
  wire up if a future field needs a negative/flagged state), `--ink`
  `#1A1A1A`, `--body-text` `#2B2B2B`, `--muted` `#878787`, `--border`
  `#DCDBDB`, `--page` `#F5F5F4`, `--card` `#FFFFFF`.
- **Type**: `--font-headline` (Hanken Grotesk 700/800, tight tracking) for
  `h1`/`h3`/popup property names; `--font-body` (Inter) for everything
  else; `--font-mono` (Space Mono 700, uppercase, letter-spaced) for
  eyebrows/labels — sidebar section headings, the tagline, table headers,
  nickname/ID lines. Fonts load from Google Fonts in `<head>`; if a future
  environment can't reach that host, fall back to Arial/Courier New per
  the brand guide rather than leaving `font-family` unset.
- **Shape**: 8px radius on cards/panels/notes; pill (999px) radius on
  chips, buttons, and badges. White cards, 1px `#DCDBDB` border, soft
  shadow — no gradients, no colored left-edge accent bars.
- If the person gives you an updated brand palette or a different design
  system entirely, re-derive these same variables rather than leaving the
  old ones half-changed — search for every remaining hex literal in the
  `<style>` block (marker colors in the `<script>` section use two plain
  JS constants, `amenityColor`/`baseColor`, not CSS variables — update
  those too) and confirm none of the previous palette's hex codes remain.

## Step 5: Save and present

Save it as `<descriptive-name>.html` and present it the way your client
supports (an artifact, or a file path in the user's working folder). Don't add
a lengthy postamble — a couple of sentences on
what was pulled from the MCP (how many listings, which fields), any
classification-heuristic caveat, and what filters were added is enough.

## Step 6: Writing tags back to Wheelhouse from the map (round trip)

The map is a static, self-contained HTML file — once presented, it has no
live connection back to this session or to Wheelhouse, so a button inside
it cannot call the Wheelhouse API directly. `map_template.html` includes a
**"Copy IDs"** button in the list panel (next to Export CSV) that copies
the `WheelhouseId`s of whatever is currently filtered/in view (same set as
the CSV export, respecting the "only homes in current map view" checkbox)
to the clipboard, with a fallback textarea if clipboard access is blocked.
The button's on-screen note tells the user to paste those IDs back into
chat along with the tag(s) they want.

When the user pastes IDs back and asks to tag them:
1. **Confirm before writing**: state the listing count, the exact tag
   name(s), and whether this merges with each listing's existing tags
   (`overwrite: false`, the default and usually what's wanted) or replaces
   them (`overwrite: true`). Wait for explicit confirmation — this is a
   write to the user's live Wheelhouse account.
2. Call `wheelhouse_rmPutTags` once per `listing_id` (channel `wheelhouse`
   for Wheelhouse-internal IDs — see the blank-id/`wheelhouse_id` vs `id`
   distinction in Step 1) with the confirmed `names` and `overwrite` value.
   Batch a handful at a time and back off on `429`s, same as any other
   portfolio-wide Wheelhouse call.
3. **`overwrite: true` is destructive.** Per the RM API docs, it replaces
   the listing's tags and deletes every tag not in `names`. Default to
   `overwrite: false` (merge), and before using `true` show the user which
   existing tags each listing would lose (read them with
   `wheelhouse_rmGetTags`). Users with *restricted editor* access to a
   shared listing can read its tags but not change them; report those as
   failures rather than retrying.
4. Report back which listings were tagged (name/nickname + WheelhouseId),
   and note any that failed with the reason.
5. If the user wants to see the result, a data refresh (Step 1, re-run)
   picks up the new tags on the next map build — mention this rather than
   trying to patch the already-presented static file in place.

## Handling follow-up requests

Users often iterate on a map this skill already built ("add X to the
popup," "also let me filter by Y," "refresh with the latest listings," "a
unit's address changed, re-pull it"). For these:
- **A data refresh** ("pull the latest," "add the new listing I just
  onboarded") means re-running Step 1 (and Step 2 only for addresses that
  changed or are new — reuse `geocodes.json` for addresses already
  resolved) rather than editing the HTML by hand.
- **A display change** (new popup field, new filter, export column) means
  editing `map_template.html`'s `<script>` with `str_replace` — the
  CSS/JS scaffolding rarely needs to change for a new field, just the popup
  template, list columns, CSV header/rows, and possibly `CHIP_FIELD` /
  `AMENITY_FIELD` if the filtered attribute itself is changing.
- **Tagging listings shown on the map** (see Step 6): the user pastes
  Wheelhouse IDs copied from the map's "Copy IDs" button, tells you the
  tag(s) to apply, and you confirm and write via `wheelhouse_rmPutTags`.
- Re-run the same validation (JS syntax check + JSON re-parse, and confirm
  list-valued fields are still lists) before re-presenting.

## Reference files

- `assets/map_template.html` — the working map (theme, chip + amenities
  filters, popups, list panel with CSV export and Copy-IDs-for-tagging,
  round trip described in Step 6). Copy and adapt per Step 4.
- `scripts/prepare_geodata.py` — address dedup/batching
  (`extract-addresses`) and geocode merge + jitter (`merge`); accepts CSV
  or JSON-list input, run with `--help` for all flags.
