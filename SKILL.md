---
name: brig
description: Wheelhouse Revenue Management agent skills for the Wheelhouse MCP (mcp.usewheelhouse.com). STLY pacing, future-rate overpricing, price-change attribution, local KPI cache, portfolio leaderboards, and custom-rate interventions.
metadata:
  version: "0.1.0"
  author:
    name: Wheelhouse
    email: support@usewheelhouse.com
  tags: wheelhouse,mcp,revenue-management,pricing,hospitality
---

# Brig — Wheelhouse Agent Skills

Agent skills and plugin packaging for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp).

## Install

### Cursor

Add this repo as a local or marketplace plugin, then enable the Wheelhouse MCP from `mcp.json` (`https://mcp.usewheelhouse.com/mcp`). Authenticate via OAuth when prompted.

Cursor reads `.cursor-plugin/plugin.json` and discovers skills under `skills/`.

### Claude Code

```text
/plugin marketplace add pricemethod/brig
```

### Codex

Reads `.codex-plugin/plugin.json` (or `.agents/plugins/marketplace.json`).

## MCP

- **Stable tools:** `https://mcp.usewheelhouse.com/mcp` — direct `wheelhouse_*` tools
- **Beta (Code Mode):** `https://mcp.usewheelhouse.com/mcp/beta` — `search` / `get_schema` / `execute`
- **API docs:** https://api.usewheelhouse.com/wheelhouse_rm_api

Skills are also exposed as `skill://` resources from the MCP server itself.

## Skills

| Skill | Description |
|-------|-------------|
| **wheelhouse-rm-mcp** | Core MCP agent guide — portfolio patterns, write safety, tool routing |
| **wheelhouse-project-instructions** | Shared RM domain context, lexicon, rule hierarchy |
| **stly-pacing** | Same-Time-Last-Year pacing analysis |
| **future-rate-overpricing** | Flag months priced well above historicals |
| **price-change-attribution** | Attribute preference/custom-rate changes to recent bookings |
| **custom-rate-intervention** | Write custom rates (Intervene stage) |
| **wheelhouse-data-sync-api** | Cache listings + KPIs locally via RM API key |
| **wheelhouse-leaderboard** | Portfolio leaderboards from local KPI cache |
| **wheelhouse-leaderboard-writeback** | Write leaderboard flags as Tags/Notes |

## Quick Start

1. Connect the Wheelhouse MCP (`mcp.usewheelhouse.com/mcp`) and complete OAuth.
2. Load `wheelhouse-rm-mcp` before portfolio or preference-write work.
3. For offline/cache workflows, run `wheelhouse-data-sync-api` first, then `wheelhouse-leaderboard`.
