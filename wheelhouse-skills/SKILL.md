---
name: wheelhouse-skills
description: Wheelhouse Revenue Management agent skills for the Wheelhouse MCP (mcp.usewheelhouse.com). STLY pacing, overpricing checks, price-change attribution, booking-window diagnosis, live priority leaderboards, occupancy-vs-market charts, market and event demand reports, MLOS strategy, Dynamic Set building, a portfolio map, and confirm-before-write changes to preferences, Events & Seasons and Custom Rates.
metadata:
  version: "0.4.0"
  author:
    name: Wheelhouse
    email: support@usewheelhouse.com
  tags: wheelhouse,mcp,revenue-management,pricing,hospitality
---

# Wheelhouse Skills — Agent Skills

Skill pack for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp). Prefer these skills over inventing ad-hoc RM workflows.

## Load order

1. Confirm the Wheelhouse MCP is connected (`https://mcp.usewheelhouse.com/mcp`) and authenticated via OAuth. On MCP calls, never send an RM API key yourself. The MCP attaches the user's key.
2. Load the matching workflow skill from the table below.
3. When an analysis compares listing numbers with market or neighborhood numbers, also load `xContext-market-data` (fee basis and conversions).

## Skills

| User intent | Skill | Description |
|---|---|---|
| How is pacing / pickup vs. same time last year? | `MCP-stly-pacing-calculations` | Same-Time-Last-Year pacing analysis |
| Are future months overpriced vs. last year? | `MCP-future-rate-overpricing` | Flag months priced well above historical booked rates |
| Is this listing overpriced vs. the neighborhood? | `MCP-market-overpricing-check` | One listing's next 60 days vs. the neighborhood median or p75, with weekly table and heatmap |
| Did a rate or preference change drive bookings? | `MCP-price-change-attribution` | Attribute preference/custom-rate changes to recent bookings |
| Did a custom rate get booked? | `MCP-custom-rate-attribution` | Fast single-listing check of whether recent custom rates booked |
| Why is my 30–59 day booking window slow? | `MCP-booking-window-diagnosis` | One listing's booking-window mix vs. the market and a segment, with a verdict |
| Who needs attention / isn't booking? | `MCP-leaderboard-poor-occ-pickup` | Live Top 10 of listings with low occupancy and weak pickup |
| Which listings trail the neighborhood and are overpriced? | `MCP-leaderboard-price-gap-priority-neighborhood` | Priority list combining neighborhood occupancy gap, recent pickup and price vs. neighborhood |
| Which listings are selling fast? | `MCP-leaderboard-fast-seller` | Live Top 10 of listings selling faster than the portfolio |
| Which nights are soft vs. the market? | `MCP-occ-heatmap-segment-market` | Night-by-night occupancy heatmap for a segment vs. the bedroom-matched market |
| How is a segment's occupancy vs. the market by month? | `MCP-segment-vs-market-occupancy-graph` | Month-by-month line chart of a segment vs. market high performers (on the books now) |
| Market outlook / which events move demand? | `MCP-market-event-demand-report` | One-market report: 6-month outlook plus next-12-month events rated by past demand |
| Year-ahead event timeline chart | `MCP-event-timeline-market-report` | One-market chart of next year's daily occupancy vs. last year with events annotated by demand tier |
| Min stay strategy for every bedroom count in a market | `MCP-mlos-strat-allbedroom` | Season-by-season MLOS rule recommendation for all bedroom groups; write-back is opt-in |
| Min stay strategy for one bedroom count | `MCP-mlos-strat-bybedroom` | Faster single-bedroom-count version of the MLOS strategy |
| Build a comp set / Dynamic Set | `MCP-dynamic-set-builder` | Scores set candidates around an example listing and creates the set after confirmation |
| Offset Airbnb's new-listing discount | `MCP-airbnb-new-listing-discount-uplift` | Scheduled job: raises base and minimum prices for tagged new listings, reverts after 3 Airbnb bookings; dry-run by default |
| Map my listings | `MCP-listing-map-visual` | Filterable map of the portfolio with list panel, CSV export, and optional tagging of selected listings |
| Change base price, seasonality, day-of-week, min/max price, min stay, etc. | `xContext-preferences` | Pricing-engine settings and rule hierarchy via the MCP; fetch, merge, confirm, then write |
| Same, from an unattended script | `xContext-preferences-api` | Direct RM API script; dry-run by default, writes only with `--apply` |
| Add, rename or redate a Season or Event, or a rule that uses one | `xContext-events-seasons` | `custom_date_ranges` id lifecycle and the blank-id protocol via the MCP |
| Same, from an unattended script | `xContext-events-seasons-api` | Direct RM API script; dry-run prints the id-migration plan before `--apply` |
| Set, combine or remove a Custom Rate | `xContext-custom-rates` | Date-range overrides via the MCP: fixed vs. adjustment, overlap/split, combine math |
| Same, from an unattended script | `xContext-custom-rates-api` | Direct RM API script; dry-run shows combine math and split impact before `--apply` |
| Compare listing numbers with market data | `xContext-market-data` | Fee basis of market, neighborhood and third-party data, and how to convert; writes nothing |
| Recreate a PriceLabs setup / PriceLabs terms | `xContext-pricelabs-migration` | Translates PriceLabs vocabulary to the right Wheelhouse write skill; writes nothing itself |

## Write skills

The `xContext-*` skills hold the write procedures and the reference context they depend on. `xContext-preferences`, `xContext-events-seasons` and `xContext-custom-rates` (and their `-api` siblings) change data in Wheelhouse; `xContext-market-data` and `xContext-pricelabs-migration` write nothing. Before interpreting a write request, load `references/lexicon-disambiguation.md` (Wheelhouse terms that don't mean what they sound like). Design notes and verification status for the write skills are in `references/write-skills-notes.md`.

Changes to preferences, Events & Seasons or Custom Rates always go through the matching `xContext-*` skill above; when an analysis leads the user to want one, hand off. A few `MCP-*` skills offer a small, self-contained write of their own, always after showing exactly what will change and getting explicit confirmation: `MCP-listing-map-visual` (tags listings selected on the map, merge by default), `MCP-dynamic-set-builder` (creates the Dynamic Set the user picked) and `MCP-airbnb-new-listing-discount-uplift` (base and minimum price changes plus notes and tags, dry-run unless the user says APPLY).

## Safety

- Skills that use a local API key file (the `-api` write skills) must never read or print the key into the conversation.
- Confirm with the user before any call that changes data in Wheelhouse, such as creating a segment.
- MCP write skills fetch current state, show exactly what will change (including any values replaced, split or removed), and write only after explicit confirmation.
- `-api` write skills are dry-run by default and write only with an explicit `--apply` flag the user sets after reviewing the printed diff.
