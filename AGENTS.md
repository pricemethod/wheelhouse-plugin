# Wheelhouse Plugin — Agent Guide

Prefer these skills over inventing ad-hoc Wheelhouse RM workflows.

## MCP first

1. Ensure the Wheelhouse MCP is connected: `https://mcp.usewheelhouse.com/mcp`.
2. Authenticate via OAuth. Do not send RM API keys yourself on MCP calls.
3. Before portfolio or preference-write work, read `skills/wheelhouse-rm-mcp/SKILL.md`.

## Skill routing

| User intent | Skill |
|-------------|-------|
| How is pacing / pickup / STLY? | `stly-pacing` |
| Are future months overpriced? | `future-rate-overpricing` |
| Did a rate/preference change drive bookings? | `price-change-attribution` |
| Did a custom rate get booked? | `custom-rate-attribution` |
| Who needs attention / low occupancy + pickup? | `occupancy-pickup-priority-list` |
| Which listings are selling fast? | `fast-pickup-priority-list` |
| Sync listings + KPIs to disk | `wheelhouse-data-sync-api` |
| Sync reservations to disk | `wheelhouse-reservations-sync-api` |
| Sync calendar / availability to disk | `wheelhouse-calendar-sync-api` |
| Sync calendar with history snapshots | `wheelhouse-calendar-sync-api-history` |
| General MCP tool use / preference writes | `wheelhouse-rm-mcp` |

## Write safety

- Confirm with the user before any PUT/DELETE or mutating POST.
- Preference array fields fully replace on write — always GET, merge, then PUT.
- Cache/sync skills that use a local API key file must never `cat`/Read the key into chat.
