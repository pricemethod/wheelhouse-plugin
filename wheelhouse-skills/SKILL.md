---
name: wheelhouse-skills
description: Wheelhouse Revenue Management agent skills for the Wheelhouse MCP (mcp.usewheelhouse.com). STLY pacing, future-rate overpricing, price-change attribution, local data caches, live pickup priority lists, occupancy-vs-market charts, a portfolio map, and confirm-before-write changes to preferences, Events & Seasons and Custom Rates.
metadata:
  version: "0.3.0"
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
3. For offline/cache workflows: load `COWORK-Data-Syncs` and run its Listings + KPIs mode first, then the Reservations and/or Calendar mode(s) as needed.

## Skills

| User intent | Skill | Description |
|---|---|---|
| How is pacing / pickup vs. same time last year? | `MCP-stly-pacing-calculations` | Same-Time-Last-Year pacing analysis |
| Are future months overpriced? | `MCP-future-rate-overpricing` | Flag months priced well above historical booked rates |
| Did a rate or preference change drive bookings? | `MCP-price-change-attribution` | Attribute preference/custom-rate changes to recent bookings |
| Did a custom rate get booked? | `MCP-custom-rate-attribution` | Fast single-listing check of whether recent custom rates booked |
| Who needs attention / isn't booking? | `MCP-Leaderboard-Poor-Occ-Pickup` | Live Top 10 of listings with low occupancy and weak pickup |
| Which listings are selling fast? | `MCP-Leaderboard-Fast-Seller` | Live Top 10 of listings selling faster than the portfolio |
| Which nights are soft vs. the market? | `MCP-Occ-Heatmap-Segment-Market` | Night-by-night occupancy heatmap for a segment vs. the bedroom-matched market |
| How is a segment's occupancy vs. the market by month? | `MCP-segment-vs-market-occupancy-graph` | Month-by-month line chart of a segment vs. market high performers (on the books now) |
| Map my listings | `MCP-Listing-Map-visual` | Filterable map of the portfolio with list panel, CSV export, and optional tagging of selected listings |
| Sync listings, KPIs, reservations or calendars to disk | `COWORK-Data-Syncs` | Cache listings+KPIs, reservations, and future price calendars (replace-only or dated-history) locally via RM API key file |
| Change base price, seasonality, day-of-week, min/max price, min stay, etc. | `Context-Preferences` | Pricing-engine settings and rule hierarchy via the MCP; fetch, merge, confirm, then write |
| Same, from an unattended script | `Context-Preferences-API` | Direct RM API script; dry-run by default, writes only with `--apply` |
| Add, rename or redate a Season or Event, or a rule that uses one | `Context-Events&Seasons` | `custom_date_ranges` id lifecycle and the blank-id protocol via the MCP |
| Same, from an unattended script | `Context-Events&Seasons-API` | Direct RM API script; dry-run prints the id-migration plan before `--apply` |
| Set, combine or remove a Custom Rate | `Context-CustomRates` | Date-range overrides via the MCP: fixed vs. adjustment, overlap/split, combine math |
| Same, from an unattended script | `Context-CustomRates-API` | Direct RM API script; dry-run shows combine math and split impact before `--apply` |
| Recreate a PriceLabs setup / PriceLabs terms | `Context-PriceLabsMigration` | Translates PriceLabs vocabulary to the right Wheelhouse write skill; writes nothing itself |

## Write skills

The `Context-*` skills change data in Wheelhouse. Before interpreting a write request, load `references/lexicon-disambiguation.md` (Wheelhouse terms that don't mean what they sound like). Design notes and verification status for the write skills are in `references/write-skills-notes.md`.

Changes to preferences, Events & Seasons or Custom Rates always go through the matching `Context-*` skill above; when an analysis leads the user to want one, hand off. The only `MCP-*` skill that writes is `MCP-Listing-Map-visual`, which can tag listings selected on the map after explicit confirmation (merge by default).

## Safety

- Skills that use a local API key file (`COWORK-Data-Syncs` and the `-API` write skills) must never read or print the key into the conversation.
- Confirm with the user before any call that changes data in Wheelhouse, such as creating a segment.
- MCP write skills fetch current state, show exactly what will change (including any values replaced, split or removed), and write only after explicit confirmation.
- `-API` write skills are dry-run by default and write only with an explicit `--apply` flag the user sets after reviewing the printed diff.
