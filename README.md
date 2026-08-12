# Brig

Give your AI agent a captain in the Wheelhouse — agent skills and plugins for the [Wheelhouse Revenue Management MCP](https://mcp.usewheelhouse.com/mcp).

A distributable skills + plugin directory that AI coding assistants can install, plus an MCP connection to live Wheelhouse tools.

## What is Brig?

**Brig** packages Wheelhouse RM workflows as Agent Skills (`SKILL.md`) and plugin manifests for Cursor, Claude Code, Codex, and other assistants that speak the Agent Plugins / Cursor plugin formats.

Skills cover:

- **Identify** — STLY pacing, future-rate overpricing, price-change attribution, portfolio leaderboards
- **Intervene** — custom-rate writes (with confirmation)
- **Cache / Cowork** — local listings+KPI sync, leaderboard writeback to Tags/Notes
- **Shared context** — project instructions + MCP agent guide

Live tools come from the MCP at `https://mcp.usewheelhouse.com/mcp` (OAuth via WorkOS AuthKit). Full API reference: https://api.usewheelhouse.com/wheelhouse_rm_api

## Repository layout

```text
brig/
├── .cursor-plugin/plugin.json      # Cursor plugin manifest
├── .claude-plugin/                 # Claude Code plugin + marketplace
├── .codex-plugin/plugin.json       # Codex plugin manifest
├── .agents/plugins/marketplace.json
├── mcp.json                        # Wheelhouse MCP server entry
├── SKILL.md                        # Root skill index
├── AGENTS.md                       # Agent-oriented overview
└── skills/                         # One directory per skill (SKILL.md + refs/scripts)
```

## Install

### Cursor

1. Add this repository as a local or marketplace plugin (manifest: `.cursor-plugin/plugin.json`).
2. Confirm `mcp.json` registers `https://mcp.usewheelhouse.com/mcp`.
3. Sign in with your Wheelhouse account when the MCP OAuth flow prompts.

Skills under `skills/*/SKILL.md` are discovered automatically.

### Claude Code

```text
/plugin marketplace add pricemethod/brig
```

### Codex / Agent Plugins

Use `.codex-plugin/plugin.json` or `.agents/plugins/marketplace.json`.

## Skills

| Skill | Description |
|-------|-------------|
| `wheelhouse-rm-mcp` | Core MCP portfolio / write-safety guide |
| `wheelhouse-project-instructions` | Shared skill-authoring + RM context |
| `stly-pacing` | STLY pacing |
| `future-rate-overpricing` | Overpriced future dates |
| `price-change-attribution` | Price change → booking attribution |
| `custom-rate-intervention` | Custom rate writes |
| `wheelhouse-data-sync-api` | Listings + KPI local cache |
| `wheelhouse-leaderboard` | Leaderboards off cache |
| `wheelhouse-leaderboard-writeback` | Tags/Notes writeback |

## Authentication

MCP clients authenticate with **OAuth** (WorkOS AuthKit). The server resolves your user RM API key; do not paste API keys into chat.

Direct-API cache skills (`wheelhouse-data-sync-api`, writeback) expect a local `wheelhouse_api_key.txt` (or write-access key file) on disk — never paste the key into the conversation.

## Development

Skills are plain markdown. To add one:

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
2. Optional: `references/`, `scripts/`.
3. Keep `SKILL.md` under ~500 lines; push long arithmetic into references.
4. Bump `version` in the plugin manifests when shipping.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
