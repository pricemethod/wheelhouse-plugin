# Wheelhouse Plugin

Give your AI agent a captain in the Wheelhouse — agent skills and plugins for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp).

This marketplace publishes two companion plugins, kept separate deliberately so a client's decision to let Claude *read* their Wheelhouse data and their decision to let Claude *write* to it stay two distinct choices:

| Plugin | Source | What it covers |
|---|---|---|
| **wheelhouse-skills** | `./wheelhouse-skills` | Read-only: portfolio pacing, pricing diagnostics, leaderboards, and local data-sync/caches |
| **wheelhouse-writes** | `./wheelhouse-writes` | Write-capable: preferences/rule hierarchy, Events & Seasons, Custom Rates — each as an interactive MCP skill and a dry-run/`--apply` direct-API sibling, plus a PriceLabs migration reference |

Install either or both independently — installing one does not require or imply the other.

> **Renamed:** the read-only plugin was previously published as `wheelhouse-plugin` — the same name as this marketplace, which was ambiguous and caused install confusion for some clients. It's now `wheelhouse-skills`. If you already installed it under the old name, reinstall: remove `wheelhouse-plugin@wheelhouse-plugin` and install `wheelhouse-skills@wheelhouse-plugin` (or your client's equivalent).

## Prerequisites

1. A Wheelhouse account.
2. **Enable MCP Access** under [API Key](https://app.usewheelhouse.com/u/account/api_token) in account settings.

## Install

Full client-by-client steps: [docs.usewheelhouse.com/rm/wheelhouse-plugin](https://docs.usewheelhouse.com/rm/wheelhouse-plugin).

### Cursor

```bash
cursor-agent plugin marketplace add https://github.com/pricemethod/wheelhouse-plugin
```

Then install **wheelhouse-skills** and/or **wheelhouse-writes** from **Customize**. Teams and Enterprise can also import the repo under **Dashboard → Plugins**.

Skills under each plugin's own `skills/` directory are discovered automatically.

### Claude Code

```text
/plugin marketplace add pricemethod/wheelhouse-plugin
/plugin install wheelhouse-skills@wheelhouse-plugin
/plugin install wheelhouse-writes@wheelhouse-plugin
```

### Codex / Agent Plugins

```bash
codex plugin marketplace add pricemethod/wheelhouse-plugin
```

Then install **wheelhouse-skills** and/or **wheelhouse-writes** from the Codex plugins list. Manifests: `wheelhouse-skills/.codex-plugin/plugin.json` (and `wheelhouse-writes/.codex-plugin/plugin.json`), `.agents/plugins/marketplace.json`.

### ChatGPT (workspace admin)

Requires a ChatGPT Enterprise/Edu workspace. In **Workspace settings → Plugins → Add → Import marketplace**:

- **Source:** `https://github.com/pricemethod/wheelhouse-plugin`
- **Path:** leave empty — the manifest lives at the repo root (`.agents/plugins/marketplace.json`)

Use a GitHub account with read access to the repo. New imports sync daily; use **Sync now** to pick up changes immediately. See [Importing and syncing plugin marketplaces from GitHub](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github).

### Grok Build

```bash
grok plugin marketplace add pricemethod/wheelhouse-plugin
```

Then install **wheelhouse-skills** and/or **wheelhouse-writes** from the `/marketplace` tab, or install directly:

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
- Sync listings, KPIs, reservations, or calendars to disk → `COWORK-Data-Syncs`

Shared MCP guidance lives in `MCP-wheelhouse-mcp-general-use-guidance`.

With **wheelhouse-writes** installed, you can also ask things like:

- Change my base price / seasonality / minimum stay → `Context-Preferences` (or `Context-Preferences-API` for an unattended script)
- Add a holiday season or event rule → `Context-Events&Seasons` (or `Context-Events&Seasons-API`)
- Set or combine a custom rate for specific dates → `Context-CustomRates` (or `Context-CustomRates-API`)
- Recreate my PriceLabs setup in Wheelhouse → `Context-PriceLabsMigration`

## Authentication

MCP clients authenticate with **OAuth**. Sign in with your Wheelhouse account — do not paste an RM API key into chat. This applies to both plugins' MCP-orchestrated skills.

The `COWORK-Data-Syncs` skill (in **wheelhouse-skills**) and the `-API` skills (in **wheelhouse-writes**) use a local API key **file** on disk instead of OAuth for unattended/scripted runs. Follow each skill's own setup; never paste the key into the conversation. The `-API` write skills are dry-run by default — they only write with an explicit `--apply` flag after you review the printed diff.

## Links

- Install: https://docs.usewheelhouse.com/rm/wheelhouse-plugin
- MCP: https://mcp.usewheelhouse.com/mcp
- API reference: https://api.usewheelhouse.com/wheelhouse_rm_api
- License: [Apache License 2.0](LICENSE)

Contributors: see [AGENTS.md](AGENTS.md), `wheelhouse-skills/skills/` (wheelhouse-skills), and `wheelhouse-writes/skills/` (wheelhouse-writes).
