---
name: wheelhouse-skills
description: Wheelhouse Revenue Management agent skills for the Wheelhouse MCP (mcp.usewheelhouse.com). STLY pacing, future-rate overpricing, price-change attribution, local data caches, and live pickup priority lists.
metadata:
  version: "0.2.1"
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
| Sync listings, KPIs, reservations or calendars to disk | `COWORK-Data-Syncs` | Cache listings+KPIs, reservations, and future price calendars (replace-only or dated-history) locally via RM API key file |

## Writes are out of scope here

This plugin is read-only. A request to change preferences, rules, Events & Seasons or Custom Rates belongs to the separate **wheelhouse-writes** plugin, if it is installed (`Context-Preferences`, `Context-Events&Seasons`, `Context-CustomRates` and their `-API` siblings). Don't improvise a write from this plugin. If wheelhouse-writes isn't installed, tell the user it is needed.

## Safety

- Skills that use a local API key file (`COWORK-Data-Syncs`) must never read or print the key into the conversation.
- Confirm with the user before any call that changes data in Wheelhouse, such as creating a segment.
