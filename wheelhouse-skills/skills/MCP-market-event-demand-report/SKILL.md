---
name: MCP-market-event-demand-report
description: "Builds a one-page market report for ONE Wheelhouse market: a 6-month outlook (month-by-month market occupancy on the books, ADR and asking rate vs. last year, with a bedroom-group filter) followed by every notable event in the next 12 months, rated High / Mid / Low demand by how its two most recent past editions filled the market against the same weekdays around them. Live through the connected Wheelhouse MCP market report, with event dates researched on the web, published as a hosted HTML page in Wheelhouse brand style. Use whenever the user asks for a market report, an event demand report, an event calendar or event impact analysis for a market, 'which events actually move demand in [market]', 'how did [event] fill the market last year', a market outlook for the coming months - even if they don't say 'report'. Market data only, no portfolio data. One market per run. For one year-ahead chart with events annotated on it instead of tables, use MCP-event-timeline-market-report."
---

# Market event demand report

One market, one page, two parts:

1. **Next six months.** For each of the next six calendar months: market adjusted
   occupancy on the books, ADR (booked nights), asking rate (open nights) and
   listings bookable per night, each against last year. A row of chips switches
   the six months between bedroom groups. A 2-3 sentence summary sits above, plus
   a one-line trailing-12-month reference (average occupancy, peak and softest
   month, listings per night).
2. **Events, next 12 months.** Every notable event in the market, measured on its
   two most recent past editions: event-night occupancy, lift vs. the same
   weekdays in the 4 weeks either side, market ADR and ADR premium. Sorted into
   High / Mid / Low demand tables in date order, plus a "Not rated" list for
   events with no past edition.

**Market data only.** No portfolio units, segments or listing data anywhere on the
page. All market money figures include guest fees (that is the market report
basis); say so, never mix them with rent-only listing numbers.

Needs the Wheelhouse MCP connected and at least one **Pro** listing in the market
(the market report is Pro-gated). No API key, no files.

## Files

| File | What it is |
|---|---|
| `references/block_a_market.py` | One Wheelhouse `execute` block: market pull, 6-month overview (whole market), trailing-12 reference, event scoring. Edit only its CONFIG section. |
| `references/block_b_bedrooms.py` | One `execute` block per batch of up to 5 bedroom groups: the 6-month overview per group, for the page's filter. |
| `scripts/build_report.py` | Renders `report.json` into the self-contained HTML page. `python3 build_report.py report.json out.html` |

Read the two blocks before running them; don't retype them from memory. They do all
the arithmetic inside the sandbox and return a few KB of JSON, so the ~1,000 daily
rows never enter the conversation.

## Step 0 - which market (ask first)

One market per run. If the user hasn't named one, call
`wheelhouse_rmGetMarketReport` with their country (result is wrapped:
`r["result"]` is a list of `{market_id, market_name, postal_codes}`) and ask which.
If they name several, run the first and offer the next one at the end. Use the
market's own name on the page (e.g. "Denver, CO"), never "your market".

Nothing else needs asking. Bedroom groups all go into the filter automatically.

## Step 1 - research the events (most of the work)

Build a list of events whose **next edition starts between today and today + 12
months**, in the market's footprint. Aim for 10-25. For each one you need:

- `name`, `dates_label` (as shown, e.g. "Mar 19-21, 2027", or "Jun 2027 (TBA)"),
  `next_start` (ISO date, used only for sort order - for TBA use the usual date),
  and an optional short `note`.
- `editions`: the **two most recent past editions** with their **actual** dates
  (`label` like "’25", `start`, `end`). They must have finished before today and lie
  within the last ~3 years (the market report's history). Dates move every year -
  never assume last year's dates from this year's.

**Where to look, cheapest first.** The city tourism board's annual events guide
(e.g. Visit Denver's "biggest events" page) lists most next-edition dates in one
fetch - pass `text_content_token_limit` (~9000), the navigation is huge. Then
organizer sites and local press for past-edition dates. One targeted search per
uncertain event; don't search what the guide already gave you.

**Include:** festivals, conventions and expos, marquee sports (championships,
marathons, tournaments), big recurring cultural events, major trade shows.
**Leave out:** events longer than ~10 days (stock shows, film-festival runs,
holiday markets - season-long events can't be measured against "the weeks around
them"; mention big ones in caveats), the holidays themselves (Thanksgiving,
Christmas-New Year, July 4th, Memorial and Labor Day are already excluded from
baselines), one-off concerts and regular-season games.

**Write a `note` when** the event changed format, venue or length between editions
("2026 moved outdoors and shrank to two days"), two events shared nights in a past
edition (both rows get the same numbers - say so on both), an event coincides with
a holiday weekend (its lift includes the holiday), only one past edition exists,
or the next date is TBA ("Usually the last weekend of June"). A brand-new event
goes in with `"editions": []` and lands in "Not rated".

**Footprint.** Market postal codes come back from `rmGetMarketReport`. If a big
event is in a neighbouring city, check its ZIP is in the list before including it.

Tell the user in the chat reply which past-edition dates you could not confirm
from a source.

## Step 2 - Block A

Copy `references/block_a_market.py`, fill CONFIG (`MARKET_ID`, `TODAY`, `EVENTS`),
run it as one call to the Wheelhouse MCP's `execute` tool (its name carries your
client's prefix, e.g. `mcp__wheelhouse__execute`; `call_tool` is already in scope
inside it). It makes one long market pull (~6-8 s), tries
`basis=stly` once, and returns:

- `overview.basis`: `"stly"` (same time last year - early access) or `"ly_final"`
  (fallback: same calendar month last year, final results). Accounts without early
  access get a 403 on `stly`; that is expected, the block falls back by itself.
- `overview.groups.all`: the six months for the whole market.
- `reference`, `events` (each with `tier`, `score`, `editions`), `unrated`.

## Step 3 - bedroom groups (Block B)

Call `wheelhouse_rmGetMarketBedroomGroups(market_id)` (no wrapper; returns
`bedroom_groups: [{bedrooms, listings}]`). Groups differ by market - pass the
`bedrooms` strings exactly ("9+" included). Run `block_b_bedrooms.py` with up to
**5 groups per `execute`** (3 if `BASIS` is `"stly"`). Ten groups = two blocks.
Merge every result into `overview.groups`. Groups under 100 listings are flagged
"thin" on the page automatically; keep them, don't drop them.

## Step 4 - assemble report.json

Block A's result, with `overview.groups` extended by Block B, plus four keys you add:

| Key | What to write |
|---|---|
| `market_name` | "Denver, CO" |
| `overview.summary` | 2-3 plain sentences about the **whole market** (see below) |
| `sources_events` | One line: where event dates came from |
| `caveats` | List of short strings: holiday overlaps, shared nights, format changes, big events left out |

**The summary.** Name the month with the most on the books and how far ahead the
rest are, then the rate direction (ADR and asking rate vs. last year), then the one
thing to watch. Use the numbers on the page. When `basis` is `ly_final`, the
occupancy gap to last year is mostly bookings still to come - never call it
"behind pace" or "down"; describe it as on-the-books vs. last year's final. With
`stly` you may call it pace. No recommendations to the user's listings - this is a
market report.

## Step 5 - render and publish

`python3 scripts/build_report.py report.json <output-folder>/<market>-market-report.html`.
Where the client can publish hosted pages (for example claude.ai's Artifact tool),
publish it there (title "<Market> market report"). Everywhere else (Claude Code,
Cowork, Cursor, Codex), save the HTML file to the workspace and give the user its
path; it opens in any browser. If the user asks for a PDF, present the HTML file
(it prints to one landscape page per section).

The page uses the Wheelhouse look: Wheelhouse magenta palette, Hanken
Grotesk / Inter / Space Mono, light and dark mode, bar = occupancy with a tick for
the comparison (last year in the overview, same weekdays in the event tables).
Don't hand-edit the HTML; change `build_report.py` if the layout needs to change.

## Scoring

Per event, averaged over its past editions:

- **Lift** = event-night occupancy − same-weekday baseline occupancy, in points.
  Event nights run from the night before day one to the night before the last day.
  The baseline uses the same weekdays within 4 weeks either side, leaving out every
  listed event's nights, holiday weekends and dates on or after today.
- **ADR premium** = event-night ADR ÷ baseline ADR − 1.
- **Level** = event-night occupancy − the market's trailing-12-month average.

`score = lift + 0.4 × premium% + 0.3 × level`. **High ≥ 20, Mid ≥ 8, else Low**
(constants at the top of Block A). Occupancy is weighted by bookable nights, ADR by
booked nights. These thresholds are a starting point: if the user disagrees with a
tier, show them the event's lift, premium and level and adjust the constants rather
than moving one event by hand.

## Read it out in the chat

Short. Which events came out High and why (lift and premium), any surprise (a famous
event that barely moves the market, usually because demand stays near the venue),
the six-month headline in one sentence, which past dates were unconfirmed, and the
comparison basis used (STLY or LY final). Offer the next market.

## When it comes back wrong

- **`basis=stly is not enabled`** in `stly_note` - expected without early access;
  the page labels everything "LY final".
- **400 "end_date should always be greater than start_date"** - the API rejects
  single-day ranges; the blocks never send one, so check a hand-made call.
- **Market occupancy fields missing, only `nights_bookable` in rows** - someone
  passed the `metric` parameter. Don't; take all fields.
- **`gather() does not yet support keyword arguments`** - Block B catches errors
  inside `pull()`; don't add `return_exceptions`.
- **Timeout over ~30 s** - too many groups in one Block B call. Drop to 3.
- **Empty market data / 404** - no Pro listing in that market, or dates outside 3
  years back / 1 year forward.
- **An event lands in "Not rated" unexpectedly** - its editions were not fully in
  the past, older than the data window, or dated wrong.
- **Two events show identical numbers** - they share nights. Expected; note it on
  both rows.
- **Event tier feels wrong for a holiday-weekend event** - holiday nights are left
  out of baselines but not out of the event itself, so the lift includes the
  holiday. Note it in `caveats`.
