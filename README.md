# Wheelhouse Plugin

Give your AI agent a captain in the Wheelhouse — agent skills and a plugin for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp).

## Prerequisites

1. A Wheelhouse account.
2. **Enable MCP Access** under [API Key](https://app.usewheelhouse.com/u/account/api_token) in account settings.

## Install

Full client-by-client steps: [docs.usewheelhouse.com/rm/wheelhouse-plugin](https://docs.usewheelhouse.com/rm/wheelhouse-plugin).

### Cursor

```bash
cursor-agent plugin marketplace add https://github.com/pricemethod/wheelhouse-plugin
```

Then install **wheelhouse-plugin** from **Customize**. Teams and Enterprise can also import the repo under **Dashboard → Plugins**.

Skills under `skills/` are discovered automatically.

### Claude Code

```text
/plugin marketplace add pricemethod/wheelhouse-plugin
/plugin install wheelhouse-plugin@wheelhouse-plugin
```

### Codex / Agent Plugins

```bash
codex plugin marketplace add pricemethod/wheelhouse-plugin
```

Then install **wheelhouse-plugin** from the Codex plugins list. Manifests: `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`.

### ChatGPT (workspace admin)

Requires a ChatGPT Enterprise/Edu workspace. In **Workspace settings → Plugins → Add → Import marketplace**:

- **Source:** `https://github.com/pricemethod/wheelhouse-plugin`
- **Path:** leave empty — the manifest lives at the repo root (`.agents/plugins/marketplace.json`)

Use a GitHub account with read access to the repo. New imports sync daily; use **Sync now** to pick up changes immediately. See [Importing and syncing plugin marketplaces from GitHub](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github).

### Grok Build

```bash
grok plugin marketplace add pricemethod/wheelhouse-plugin
```

Then install **wheelhouse-plugin** from the `/marketplace` tab, or install directly:

```bash
grok plugin install pricemethod/wheelhouse-plugin --trust
```

`--trust` activates the plugin's skills; without it, the plugin installs but stays inert.

## What you can ask

Once the plugin and MCP are connected, ask your assistant things like:

- How is this listing or portfolio pacing vs same time last year? → `MCP-stly-pacing-calculations`
- Are future months overpriced vs last year’s booked rates? → `MCP-future-rate-overpricing`
- Did a recent rate or preference change drive bookings? → `MCP-price-change-attribution`
- Did that custom rate get booked? → `MCP-custom-rate-attribution`
- Who needs attention / isn’t booking? → `MCP-Leaderboard-Poor-Occ-Pickup`
- Which listings are selling fast? → `MCP-Leaderboard-Fast-Seller`
- Sync listings, KPIs, reservations, or calendars to disk → `COWORK-Listing-data-sync-api-cache`, `COWORK-reservations-sync-api-cache`, `COWORK-calendar-sync-api-cache`

Shared MCP guidance lives in `MCP-wheelhouse-mcp-general-use-guidance`.

## Authentication

MCP clients authenticate with **OAuth**. Sign in with your Wheelhouse account — do not paste an RM API key into chat.

Cache/sync skills (`COWORK-Listing-data-sync-api-cache`, `COWORK-reservations-sync-api-cache`, `COWORK-calendar-sync-api-cache`, `COWORK-calendar-history-sync-api-cache`) use a local API key **file** on disk. Follow those skills’ setup; never paste the key into the conversation.

## Links

- Install: https://docs.usewheelhouse.com/rm/wheelhouse-plugin
- MCP: https://mcp.usewheelhouse.com/mcp
- API reference: https://api.usewheelhouse.com/wheelhouse_rm_api
- License: [Apache License 2.0](LICENSE)

Contributors: see [AGENTS.md](AGENTS.md) and `skills/`.
