# Brig

Give your AI agent a captain in the Wheelhouse — agent skills and a plugin for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp).

## Prerequisites

1. A Wheelhouse account.
2. **Enable MCP Access** under [API Key](https://app.usewheelhouse.com/u/account/api_token) in account settings.

## Install

### Cursor

1. Add this repository as a local or marketplace plugin (manifest: `.cursor-plugin/plugin.json`).
2. Confirm the Wheelhouse MCP is registered from `mcp.json` (`https://mcp.usewheelhouse.com/mcp`).
3. Sign in with your Wheelhouse account when the MCP OAuth flow prompts.

Skills under `skills/` are discovered automatically.

### Claude Code

```text
/plugin marketplace add pricemethod/brig
```

### Codex / Agent Plugins

Use `.codex-plugin/plugin.json` or `.agents/plugins/marketplace.json`.

## What you can ask

Once the plugin and MCP are connected, ask your assistant things like:

- How is this listing or portfolio pacing vs same time last year? → `stly-pacing`
- Are future months overpriced vs last year’s booked rates? → `future-rate-overpricing`
- Did a recent rate or preference change drive bookings? → `price-change-attribution`
- Set a custom rate on these dates → `custom-rate-intervention`
- Who needs attention across my portfolio? → `wheelhouse-data-sync-api` then `wheelhouse-leaderboard`
- Push leaderboard flags back as Tags/Notes → `wheelhouse-leaderboard-writeback`

Shared MCP and domain guidance lives in `wheelhouse-rm-mcp` and `wheelhouse-project-instructions`.

## Authentication

MCP clients authenticate with **OAuth**. Sign in with your Wheelhouse account — do not paste an RM API key into chat.

Cache and writeback skills (`wheelhouse-data-sync-api`, `wheelhouse-leaderboard-writeback`) use a local API key **file** on disk. Follow those skills’ setup; never paste the key into the conversation.

## Links

- MCP: https://mcp.usewheelhouse.com/mcp
- API reference: https://api.usewheelhouse.com/wheelhouse_rm_api
- License: [Apache License 2.0](LICENSE)

Contributors: see [AGENTS.md](AGENTS.md) and `skills/`.
