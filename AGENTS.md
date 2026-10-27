# Wheelhouse Plugin Library — Maintainer Guide

Instructions for anyone (human or AI agent) **working on this repository**. They are not instructions for using the skills: customers get usage guidance from the plugin files they install (`wheelhouse-skills/SKILL.md`, each skill's `SKILL.md`, and `wheelhouse-skills/references/`).

## What this repository is

- A **public** plugin marketplace (`github.com/pricemethod/wheelhouse-plugin`) that Wheelhouse customers add to Claude Code, Cursor, Codex, ChatGPT and Grok to use skills built by the Wheelhouse team on the [Wheelhouse RM API](https://api.usewheelhouse.com/wheelhouse_rm_api) and the Wheelhouse MCP (`https://mcp.usewheelhouse.com/mcp`).
- It publishes **one plugin**, `wheelhouse-skills` (source `./wheelhouse-skills`), which holds both kinds of skill:

  | Skills | Scope |
  |---|---|
  | `MCP-*`, `COWORK-Data-Syncs` | **Read-only**: pacing, diagnostics, leaderboards, local data syncs |
  | `Context-*` | **Write-capable**: preferences, Events & Seasons, Custom Rates, PriceLabs migration reference |

- Until version 0.3.0 the write skills shipped as a separate `wheelhouse-writes` plugin. They were merged into `wheelhouse-skills` so customers install one plugin. Keep the read/write line clear inside the plugin: changes to preferences, Events & Seasons or Custom Rates always go through the matching `Context-*` skill. An `MCP-*` read skill may offer a small, self-contained write of its own (for example `MCP-Listing-Map-visual` tagging the listings selected on the map) only if it follows the MCP write-safety rule below: read current state first, show exactly what will change, default to the non-destructive option, and write only after explicit confirmation. Say so in the skill's `description`.
- Only the plugin folder ships to customers. Repo-root files (this guide, `README.md`, `.gitignore`) and the marketplace manifests do not install with a plugin.

## Public-repo rules (apply to every committed file)

1. **No customer or account data.** That covers real listing names, listing/user/segment IDs, addresses, prices or KPIs pulled from a real account, and screenshots of them. Use invented examples ("a 3-bedroom beach listing", `listing_id: "12345678"`). Findings from live dry runs can be recorded as patterns, not as named listings.
2. **No credentials.** No API keys, tokens or key-file contents, not even redacted ones. Skills that use a key file must never read the key into chat.
3. **No internal-only references.** Shipped files must make sense to a customer on their own. Don't point to internal documents ("project instructions §4"), internal tools, Slack threads or unreleased features. If guidance matters, write it into the skill.
4. **No unverified claims stated as fact.** If behavior hasn't been confirmed in the API docs or by a live read-only test, phrase it as a caveat and say how to check it.

## Sources of truth

- **Wheelhouse behavior:** the RM API docs, including their dated **Changelog** section, and the live Wheelhouse MCP tool list. MCP tools are named `wheelhouse_<operationId>` and mirror the API one to one. When the docs and a skill disagree, the docs win, unless a live read-only test shows otherwise. Record that test in the skill.
- **Other tools' behavior (PriceLabs, PMSs, channels):** the Wheelhouse docs are **not** evidence for how another product works. Change only the Wheelhouse side of a mapping based on Wheelhouse docs. A claim about PriceLabs needs PriceLabs' own documentation or confirmation from a Wheelhouse team member. Keep existing "Confirmed (<name>, <date>)" notes unless the person who confirmed them revises them.

## Skill conventions

- **Layout:** one folder per skill under `<plugin>/skills/<skill-name>/`, containing `SKILL.md` (YAML frontmatter with `name` and `description`), optional `references/` for long material, and optional `scripts/` for code.
- **`description` frontmatter drives routing.** Keep it accurate: say what the skill does, when to trigger it, and when to use a sibling instead.
- **Hand-offs** must name skills that exist in this repo, by their exact name (e.g. `MCP-stly-pacing-calculations`, `Context-CustomRates`). Check with a search before committing.
- **Tool names:** use full MCP tool names (`wheelhouse_rmGetReservations`, not `GetReservations`).
- **Write safety, MCP skills:** fetch current state first, show the client exactly what will change (and any existing values it replaces, splits or removes), and write only after explicit confirmation. Preference rule arrays are fully replaced on write, so always fetch, merge, then write.
- **Write safety, direct-API (`-api`) skills:** dry-run by default and print the exact request body and diff. Write only with an explicit `--apply` flag that the customer sets after reviewing the diff.
- **API facts to get right** (common past mistakes; check the docs for current values):
  - Rate limit and `Retry-After` handling
  - Reservation statuses: only `Accepted` is a booking
  - Revenue + Fees = `total_price − taxes`
  - Neighborhood prices are fee-inclusive (use `fee_impact_calendar`)
  - Array query params need brackets (`listing_ids[]=`)
  - `channel=wheelhouse` with a Wheelhouse listing ID
  - Hidden listings (`is_hidden`) are still returned with `exclude_inactive=true`
  - Multi-unit listings return one row per `unit_number`
- **Scripts:**
  - Python standard library unless a dependency is unavoidable.
  - Read the API key from a file path, never from an argument or the chat.
  - Honour `Retry-After`.
  - Test against a real account before release. Use read-only calls, or a `hypothetical` listing for writes.

## Releasing a change

1. **Bump the version**: patch for fixes and doc corrections, minor for new skills or behavior changes. The version appears in all of these places, and they must match:
   - `wheelhouse-skills/.claude-plugin/plugin.json`
   - `wheelhouse-skills/.codex-plugin/plugin.json`
   - `wheelhouse-skills/.cursor-plugin/plugin.json`
   - its entry in `.claude-plugin/marketplace.json`
   - its entry in `.agents/plugins/marketplace.json`
   - its entry in `.cursor-plugin/marketplace.json`
   - `metadata.version` in `wheelhouse-skills/SKILL.md`
2. **Keep the lists in sync.** When adding, removing or renaming a skill, update:
   - the root `README.md` ("What you can ask")
   - the skills table in `wheelhouse-skills/SKILL.md` (and `references/write-skills-notes.md` for a write skill)
   - any skills that hand off to it
3. **Check before committing:**
   - search for references to removed or renamed skills
   - check for customer data and internal references (rules above)
   - confirm the manifests are valid JSON
4. **Commit on a branch and open a PR.** Customers pick up changes when their client syncs the marketplace, so `main` is effectively production.

## Local maintenance workspace

Maintainers can keep a local, gitignored `maintenance/` folder. It holds:
- weekly API snapshots and diffs against the RM API docs
- dated skill-update proposals
- a running change log of skill edits

It is never committed. If it exists, read `maintenance/README.md` before doing API-driven skill updates, and log applied changes in `maintenance/SKILL-CHANGE-LOG.md`.
