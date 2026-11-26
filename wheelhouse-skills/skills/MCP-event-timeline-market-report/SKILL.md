---
name: MCP-event-timeline-market-report
description: "Builds a 12-month event timeline for ONE Wheelhouse market: one big annotated chart of daily market occupancy for the next year - last year's demand curve (same weekday, 52 weeks earlier) with this year's on-the-books line over it - and every notable event placed on its next dates as a labeled band, colored by High / Mid / Low demand tier from how its two most recent past editions filled the market. Event tier tables sit below the chart. Live via the Wheelhouse MCP market report, event dates researched on the web, published as a Wheelhouse-styled HTML page. Use whenever the user asks for an event timeline, a year-ahead demand chart, 'show the events on a timeline/graph', 'when are the busy weeks this year', a demand calendar with events annotated, or the timeline version of the market event report - even if they don't say 'timeline'. For tables plus a 6-month outlook instead of a chart, use MCP-market-event-demand-report. Market data only, one market per run."
---

# Market event timeline

One market, one page:

1. **The chart.** Every night from tomorrow to today + 364 days (the market report
   rejects later end dates). Behind everything, last year's adjusted occupancy for
   the same weekday 52 weeks earlier - a soft daily area plus a 7-day average line -
   which is the demand shape the year is likely to follow. Over it, this year's
   on-the-books occupancy (7-day average, magenta). Events sit on their next
   dates as shaded bands, shaded by tier; new events are dashed, TBA events have a
   dashed edge. **Annotations are interactive:** by default one row of labels shows
   the highest-impact events (High, then Mid, in score order, as many as fit on one
   line); clicking any band adds its annotation in a row above, clicking a label
   removes it, and Reset restores the default row. A **Last year’s events** toggle
   (off by default) draws each event’s most recent past edition as a hatched band,
   placed 364 days forward so it sits on the last-year line where its spike
   happened; clicking one adds an italic, dashed "Last year ’26" annotation with that
   edition’s own dates, occupancy, lift and ADR premium. Season-long events
   (stock shows, holiday markets) get a thin context bar along the top. Holidays
   are marked under the axis because they explain last year's spikes. Each month
   label carries last year's final occupancy and today's on-the-books figure.
   Hover or arrow keys give the night-by-night readout; Enter toggles the event
   under the crosshair. No summary text on the page.
2. **The event tables.** High / Mid / Low demand, same columns and scoring as
   `MCP-market-event-demand-report`, plus a "Not rated" list (new and season-long events).

No month tiles and no bedroom filter on this one - it is the whole market. All
money figures include guest fees (market report basis). Needs the Wheelhouse MCP
and at least one **Pro** listing in the market.

## Files

| File | What it is |
|---|---|
| `references/block_timeline.py` | One Wheelhouse `execute` block: one market pull, daily series for the chart, month labels, trailing-12 reference, event scoring. Edit only CONFIG. |
| `scripts/build_timeline.py` | Renders `report.json` into the page. `python3 build_timeline.py report.json out.html` |

Read the block before running it; don't retype it from memory.

## Step 0 - which market

One market per run. If none is named, call `wheelhouse_rmGetMarketReport` with
the user's country (`r["result"]` lists `{market_id, market_name, postal_codes}`)
and ask. Several named: run the first, offer the next at the end.

## Step 1 - research the events

Same rules as the sibling skill; the timeline adds two fields.

- Window: next edition starts between today and today + 364 days, in the market's
  footprint (check a neighbouring city's ZIP against `postal_codes`). Aim for 10-25.
- Per event: `name`, `dates_label`, `next_start`, **`next_end`** (needed to draw the
  band; for a single day use the same date), optional `note`, and **`tba: True`**
  when the next dates are a best guess from the usual pattern (draw it on the usual
  dates, say "Usually the last weekend of June" in the note).
- `editions`: the two most recent past editions with **actual** dates, finished
  before today, within ~3 years. Dates move; never copy this year's onto last year.
- Season-long events (longer than ~10 days): add them with `"context": True`, their
  next dates, and no editions. They draw as a thin bar and are listed as not rated.
- New events: `"editions": []` - dashed band, "No past edition" label.
- Notes for format/venue changes, shared nights between two events, holiday
  coincidence, single past edition.

Cheapest sources first: the tourism board's annual events guide in one
fetch, then organizer sites and local
press for past dates. Use whatever web fetch or search tool your client provides;
if there is none, ask the user for the event list and past dates. In the chat reply, list any past dates you could not confirm.

## Step 2 - the block

Fill CONFIG in `block_timeline.py` (`MARKET_ID`, `TODAY`, `EVENTS`) and run it as
one call to the Wheelhouse MCP's `execute` tool (its name carries your client's
prefix, e.g. `mcp__wheelhouse__execute`; `call_tool` is already in scope inside it). One pull of about 3 years of daily rows (~6-8 s); it returns ~10 KB:
`series` (364-day arrays: `occ`, `occ_ly`, `adr_ly`, `bookable`), `months`,
`reference`, `events` (each edition carries its own `start`, `end`, `occ`,
`base_occ`, `lift_pts`, `adr`, `adr_prem` for the last-year annotations), `unrated`,
`context`. Last year here is final data for the date 364 days earlier, so it never
depends on early-access STLY.

## Step 3 - assemble report.json

The block's result plus:

| Key | What to write |
|---|---|
| `market_name` | "Denver, CO" |
| `sources_events` | One line: where event dates came from |
| `caveats` | Short strings: holiday overlaps, shared nights, format changes |

There is no summary on the page; the reading of the chart goes in the chat reply
(see below). Last-year editions only appear on the chart when their dates + 364 days
fall inside the window, which in practice means editions from the past 12 months.

## Step 4 - render and publish

`python3 scripts/build_timeline.py report.json <output-folder>/<market>-event-timeline.html`.
Where the client can publish hosted pages (for example claude.ai's Artifact tool),
publish it there (title "<Market> event timeline"). Everywhere else (Claude Code,
Cowork, Cursor, Codex), save the HTML file to the workspace and give the user its
path.

The chart draws itself in the browser at the real width (it scrolls sideways
under ~980 px, so labels never shrink). It stops the on-the-books line where
bookable inventory falls below 30% of normal - in the last weeks of the window
calendars aren't open yet - and marks the cutoff. Change the layout in
`build_timeline.py`, never by hand-editing the HTML.

## Scoring

Identical to `MCP-market-event-demand-report`: per past edition, lift = event-night
occupancy − same-weekday baseline (4 weeks either side, leaving out listed events,
holiday weekends and dates on or after today); ADR premium = event ADR ÷ baseline
ADR − 1; level = event-night occupancy − trailing-12-month average.
`score = lift + 0.4 × premium% + 0.3 × level`; High ≥ 20, Mid ≥ 8. Event nights run
from the night before day one to the night before the last day, and the bands on
the chart cover those nights. Keep the two skills' constants in step if one changes.

## Read it out in the chat

Short: the shape of the year in one sentence, which High events land where - on
top of an already busy stretch, or lifting a soft one (the second is the bigger
pricing opportunity) - any well-known event that barely moves the market, which
default-row events were left off for space (one click away), unconfirmed past
dates, and an offer of the next market or the table-and-outlook version. The
on-the-books gap to last year is mostly bookings still to come: never call it
"behind pace".

## When it comes back wrong

- **400 "Invalid end_date"** - an end date past today + 364. The block never sends one.
- **400 "end_date should always be greater than start_date"** - single-day ranges
  are rejected; check any hand-made call.
- **Market occupancy missing, only `nights_bookable` in rows** - the `metric`
  parameter was passed. Don't.
- **Magenta line ends early** - expected: inventory fell below 30% of normal there.
- **A band is missing** - `next_end` before `next_start`, or dates outside the window.
- **A High event is missing from the default row** - its dates are crowded by
  higher-scoring events; it stays one click away. Widen `MAXS_DEFAULT` in
  `build_timeline.py` only if labels can still sit near their bands.
- **No hatched bands after toggling last year** - the events' past editions lack
  `start`/`end` (old block output) or fall outside the past 12 months.
- **Empty data / 404** - no Pro listing in the market.
