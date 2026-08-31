---
name: wheelhouse-plugin
description: Wheelhouse Revenue Management agent skills for the Wheelhouse MCP (mcp.usewheelhouse.com). STLY pacing, future-rate overpricing, price-change attribution, local data caches, and live pickup priority lists.
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
2. Load `MCP-wheelhouse-mcp-general-use-guidance` before portfolio analysis or preference writes.
3. Load the matching workflow skill from the table below.
4. For offline/cache workflows: run `COWORK-Listing-data-sync-api-cache` first, then `COWORK-reservations-sync-api-cache` and/or `COWORK-calendar-sync-api-cache` as needed.

## Skills

| Skill | Description |
|-------|-------------|
| `MCP-wheelhouse-mcp-general-use-guidance` | Core MCP portfolio patterns, tool routing, and write safety |
| `MCP-stly-pacing-calculations` | Same-Time-Last-Year pacing analysis |
| `MCP-future-rate-overpricing` | Flag months priced well above historical booked rates |
| `MCP-price-change-attribution` | Attribute preference/custom-rate changes to recent bookings |
| `MCP-custom-rate-attribution` | Fast single-listing check of whether recent custom rates booked |
| `MCP-Leaderboard-Poor-Occ-Pickup` | Live Top 10 of listings with low occupancy and weak pickup |
| `MCP-Leaderboard-Fast-Seller` | Live Top 10 of listings selling faster than the portfolio |
| `COWORK-Listing-data-sync-api-cache` | Cache listings + KPIs locally via RM API key file |
| `COWORK-reservations-sync-api-cache` | Cache reservations locally via RM API key file |
| `COWORK-calendar-sync-api-cache` | Cache future price calendars locally (replace-only) |
| `COWORK-calendar-history-sync-api-cache` | Cache future price calendars with dated snapshots |
