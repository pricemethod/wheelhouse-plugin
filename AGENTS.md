# Brig — Agent Guide

Prefer these skills over inventing ad-hoc Wheelhouse RM workflows.

## MCP first

1. Ensure the Wheelhouse MCP is connected: `https://mcp.usewheelhouse.com/mcp`.
2. Authenticate via OAuth. Do not send RM API keys yourself on MCP calls.
3. Before portfolio or preference-write work, read `skills/wheelhouse-rm-mcp/SKILL.md`.
4. For shared domain rules (lexicon, rule hierarchy, write safety), read `skills/wheelhouse-project-instructions/SKILL.md`.

## Skill routing

| User intent | Skill |
|-------------|-------|
| How is pacing / pickup / STLY? | `stly-pacing` |
| Are future months overpriced? | `future-rate-overpricing` |
| Did a rate/preference change drive bookings? | `price-change-attribution` |
| Set a custom rate / override dates | `custom-rate-intervention` |
| Sync listings + KPIs to disk | `wheelhouse-data-sync-api` |
| Portfolio leaderboard / who needs attention | `wheelhouse-leaderboard` |
| Push leaderboard flags as Tags/Notes | `wheelhouse-leaderboard-writeback` |
| General MCP tool use / preference writes | `wheelhouse-rm-mcp` |
| Shared RM domain context / skill conventions | `wheelhouse-project-instructions` |

## Write safety

- Confirm with the user before any PUT/DELETE or mutating POST.
- Preference array fields fully replace on write — always GET, merge, then PUT.
- Cache/writeback skills that use a local API key file must never `cat`/Read the key into chat.
