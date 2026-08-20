---
name: wheelhouse-plugin
description: Wheelhouse Revenue Management agent skills for the Wheelhouse MCP (mcp.usewheelhouse.com). STLY pacing, future-rate overpricing, price-change attribution, local KPI cache, portfolio leaderboards, and custom-rate interventions.
metadata:
  version: "0.1.0"
  author:
    name: Wheelhouse
    email: support@usewheelhouse.com
  tags: wheelhouse,mcp,revenue-management,pricing,hospitality
---

# Wheelhouse Plugin — Agent Skills

Skill pack for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp). Prefer these skills over inventing ad-hoc RM workflows.

## Load order

1. Confirm the Wheelhouse MCP is connected (`https://mcp.usewheelhouse.com/mcp`) and authenticated via OAuth.
2. Load `wheelhouse-rm-mcp` before portfolio analysis or preference writes.
3. Load the matching workflow skill from the table below.
4. For offline/cache workflows: run `wheelhouse-data-sync-api` first, then `wheelhouse-leaderboard` (optionally `wheelhouse-leaderboard-writeback`).

Shared domain rules live in `wheelhouse-project-instructions`.

## Skills

| Skill | Description |
|-------|-------------|
| `wheelhouse-rm-mcp` | Core MCP portfolio patterns, tool routing, and write safety |
| `wheelhouse-project-instructions` | Shared RM domain context, lexicon, and rule hierarchy |
| `stly-pacing` | Same-Time-Last-Year pacing analysis |
| `future-rate-overpricing` | Flag months priced well above historical booked rates |
| `price-change-attribution` | Attribute preference/custom-rate changes to recent bookings |
| `custom-rate-intervention` | Write custom rates with confirmation |
| `wheelhouse-data-sync-api` | Cache listings + KPIs locally via RM API key file |
| `wheelhouse-leaderboard` | Portfolio leaderboards from local KPI cache |
| `wheelhouse-leaderboard-writeback` | Write leaderboard flags as Tags/Notes |
