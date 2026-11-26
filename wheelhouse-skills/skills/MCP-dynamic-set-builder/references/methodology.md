# Methodology and API notes

Read this when a user asks how a score was calculated, when results look
wrong, or before changing any threshold in `scripts/fetch_and_score.py`.

## Data source

Everything comes from `wheelhouse_rmGetSetCandidates` (market listings near
a point, nearest-first, trailing-year metrics). Confirmed live (Nov 2026):

- **Silent defaults.** The endpoint filters by `min_open_occupancy_365_0 =
  0.35` and `min_bookable_nights_365_0 = 127` unless you override them. The
  script passes `0` for both so the skill sees the whole pool and applies its
  own gates. Never drop those overrides, or weak/new listings vanish without
  being counted.
- **No forward values in rows.** Rows only carry trailing metrics
  (`*_365_0`, `nights_percent_open_90_0`). Forward data exists only as
  filters: `min_bookable_nights_0_365` and `min_open_occupancy_0_365`. The
  script recovers forward signals by re-running the search at several
  thresholds and noting which IDs survive each one (banding). Filters were
  verified to bite: counts fall as thresholds rise.
- **Fixed windows.** Forward = next 365 days only. Trailing = 365 days
  (`nights_bookable_365_0`) or 90 days (`nights_percent_open_90_0`).
- `source`: `A` Airbnb, `V` Vrbo, `B` Booking.com. `url` is the OTA link.
- `room_type` values seen: apartment, house, cabin, room, hotel, bnb, other,
  camping. `property_type` is free-ish text (Condo, Apartment, Entire
  home/apt...). Condo/Apartment property types under room_type `other` are
  treated as apartment.
- `listing_id` is the internal market ID `rmCreateSet` expects.
- Pagination: `per_page` max 100; stop when a page is short. In dense
  markets a 3 mi, all-bedroom search exceeds 500 rows, so keep the bedroom
  filter server-side and the radius tight.

## Translating the user's answers

| User answer | What the script gets |
|---|---|
| Future minimum, e.g. 30 nights in next 90 days | `fwd_min_bookable_365 = ceil(30 * 365 / 90) = 122`. Say this is pro-rated to the API's 365-day window. |
| Window 12 months (or 6-12) | `lookback = "365"` |
| Window ~3 months (or less) | `lookback = "90"` |
| Window between, e.g. 6 months | use `"365"` and say so; no 180-day window exists |
| "N bookable nights in that window" | `lookback_min_nights = N`, a raw count, not a share. For a 90-day window the API only returns a share (`nights_percent_open_90_0`); the script multiplies it back out to a night count to compare. |
| "No minimum" / user skips this | `lookback_min_nights = 0` (gate never fires; scoring still uses the share) |
| Trailing adjusted occupancy floor, e.g. "above 20%" | `min_adjusted_occupancy = 0.2` (strict greater-than; a listing at exactly 20% fails) |
| Radius and all distances | asked and shown in miles; the script converts to meters for the API (x 1609.34) |

## Gates (applied before scoring, counted in `counts`)

Order: exclude list → own listings → OTA channel → type mismatch →
insufficient history → stale → low adjusted occupancy → future bookable
minimum. Known includes (`pinned`) skip all of these except the exclude
list but are still scored and labeled.

- **Own listings:** the numeric ID in the candidate URL matches a value in
  the user's `rmGetListings` `channel_ids`, or `owner_name` matches a host
  name the user gave.
- **Type mismatch:** candidate class differs from the example's class and
  is not `other`. Exception: when the example is an apartment and the title
  names the complex, `hotel` is kept at half type credit. Managed condos on
  Booking.com and some Airbnb listings are typed `hotel` (in one test
  resort, 12 of 164 rows).
- **Insufficient history:** fewer bookable nights within the lookback
  window than `lookback_min_nights` (the user's answer; 0 means no
  minimum, which only filters out listings with literally zero open
  nights). This is a count of nights actually open, not a proxy for how
  long the listing has existed — a listing created 5 years ago with a
  dead calendar fails this exactly like a brand-new one would.
- **Stale:** `updated_at` (last scrape) older than `stale_days` (default
  30) — a separate, purely mechanical freshness check, independent of the
  history gate above.
- **Low adjusted occupancy:** `occupancy_adjusted_365_0` at or below
  `min_adjusted_occupancy` (default 0.2, strict greater-than to pass).
  This is a trailing performance floor, not forward-looking — it catches
  listings with plenty of open/bookable nights (so they'd clear the
  history and stale gates) that simply aren't converting into stays. A
  listing exactly at the threshold fails, by design.
- **Future bookable:** not in the `min_bookable_nights_0_365` result set.

## Scores (each 0-100)

**Same complex** = 50% name + 35% proximity + 15% type.
- Name: 1.0 if the exact complex name is in the title, 0.75 for a
  variation, else 0. Titles and names are lowercased with punctuation
  stripped.
- Proximity: 1.0 within `prox_full_mi` (default 0.12 mi; OTAs blur pins,
  Airbnb by up to a few hundred feet), then linear to 0 at `prox_zero_mi`
  (default 0.6 mi). Radius never affects score.
- Type: 1.0 same class, 0.5 `other`.

**Openness** = 50% lookback open share (full marks at `open_full`, default
80% open) + 50% forward bookable band (≥ upper `fwd_bookable_bands` value
1.0, ≥ lower value 0.75, ≥ the user's future minimum 0.5; defaults 270 and
180 nights in the next 365).

**Performance** = 60% forward open-occupancy band (highest band the listing
passes; bands step up 5 points at a time from `fwd_occ_band_floor`,
default 40%, to `fwd_occ_full`, default 75%, which earns full marks) +
40% trailing adjusted occupancy (`occupancy_adjusted_365_0`; full marks at
`trail_occ_full`, default 80%). Forward is weighted higher because the goal
is listings that actually book going forward; trailing steadies thin
forward data.

A wide gap between the floor and the full-credit point (40-75 by default)
means more bands get tested — 8 at the 5-point step — so more MCP calls
per run, still well inside the 48-call cap. One consequence worth knowing:
in a market where no candidate clears the floor (seen in one test resort
whose whole pool topped out near 30%), every listing scores 0 on the forward half of performance, and
ranking there falls entirely to trailing occupancy; raising the full-credit
point further doesn't change that, only the floor does.

**Overall** = `weight_same * same + weight_open * openness + weight_perf *
perf`, with the three weights summing to 1.0. Defaults are `weight_same=0.40,
weight_open=0.25, weight_perf=0.35`. These are asked and set in question
11 like every other threshold, so a run can still use an even split or
any other mix the user wants.

**Cross-listings** are flagged, not scored: rows whose normalized titles
match exactly get an "Also on ..." label. The same unit often appears on
Airbnb, Vrbo and Booking.com; picking all copies weights that unit 2-3x.
Titles that differ slightly ("Beautiful Lakeview Condo ... 1027" vs
"Lakeview Condo ... 1027") are not caught; unit numbers in titles are the
best manual tell.

All cut-offs are asked of the user every run (SKILL.md question 11) and
passed in CONFIG. The defaults are starting points from one test market.

## Call budget

About 12 searches (1 base + 3 forward-bookable + 8 occupancy bands between
the default 40% floor and 75% full-credit point, stepping 5 points at a
time; fewer or more if those are moved closer together or farther apart),
each paginated up to `max_pages` (default 4). The script stops at 48 calls
and sets `truncated`, staying under the
sandbox's 50 per execute and the API's 60/minute. If `truncated` is true,
tighten the radius rather than raising `max_pages`.

## Test notes

Patterns from live read-only tests (Nov 2026) in two resort complexes:

- A 2BR, 0.6 mi, all-OTA run with 30/90 pro-rated to 122/365 and a
  12-month lookback pulled 164 candidates in 14 calls: 20 type mismatches,
  26 failed the future minimum, 118 scored. The top 25 were all units in
  the target complex.
- In a pool where forward occupancy topped out near 30%, no candidate
  reached the 40% band floor, so the forward half of performance was 0 for
  everyone and ranking fell to trailing occupancy.
- With the default 40-75% bands a run used about 12 searches, inside the
  48-call cap.
- The adjusted-occupancy floor (0.2) fires independently of the history
  and stale gates: a listing can have plenty of bookable nights and still
  fail on occupancy.
