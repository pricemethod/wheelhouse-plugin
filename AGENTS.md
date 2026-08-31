# Wheelhouse Plugin — Agent Guide

Prefer these skills over inventing ad-hoc Wheelhouse RM workflows.

## MCP first

1. Ensure the Wheelhouse MCP is connected: `https://mcp.usewheelhouse.com/mcp`.
2. Authenticate via OAuth. Do not send RM API keys yourself on MCP calls.
3. Before portfolio or preference-write work, read `skills/MCP-wheelhouse-mcp-general-use-guidance/SKILL.md`.

## Skill routing

| User intent | Skill |
|-------------|-------|
| How is pacing / pickup / STLY? | `MCP-stly-pacing-calculations` |
| Are future months overpriced? | `MCP-future-rate-overpricing` |
| Did a rate/preference change drive bookings? | `MCP-price-change-attribution` |
| Did a custom rate get booked? | `MCP-custom-rate-attribution` |
| Who needs attention / low occupancy + pickup? | `MCP-Leaderboard-Poor-Occ-Pickup` |
| Which listings are selling fast? | `MCP-Leaderboard-Fast-Seller` |
| Sync listings + KPIs to disk | `COWORK-Listing-data-sync-api-cache` |
| Sync reservations to disk | `COWORK-reservations-sync-api-cache` |
| Sync calendar / availability to disk | `COWORK-calendar-sync-api-cache` |
| Sync calendar with history snapshots | `COWORK-calendar-history-sync-api-cache` |
| General MCP tool use / preference writes | `MCP-wheelhouse-mcp-general-use-guidance` |

## Write safety

- Confirm with the user before any PUT/DELETE or mutating POST.
- Preference array fields fully replace on write — always GET, merge, then PUT.
- Cache/sync skills that use a local API key file must never `cat`/Read the key into chat.
