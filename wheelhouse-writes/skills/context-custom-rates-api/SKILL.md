---
name: Context-CustomRates-API
description: Use when a Wheelhouse client wants a script calling the RM API directly (X-Integration-Api-Key) to set, replace, combine, or remove a Custom Rate, outside a live chat turn. Covers the same fixed-vs-adjustment semantics, overlap/split behavior, and compounding math as Context-CustomRates but for unattended/scripted writes -- dry-run by default, prints the computed combined value and overlap impact, only writes with an explicit --apply flag. Trigger on "script a custom rate update," "automate rate overrides," or any Custom Rate write that needs to run without Claude in the loop. Use Context-CustomRates instead for an interactive chat-turn change via the connected MCP.
---

# Context-CustomRates-API (direct RM API)

Unattended sibling of Context-CustomRates. Same `fixed`/`adjustment` semantics, same overlap/split behavior, same compounding formulas. This skill covers what differs for a script — but the combine-vs-replace protocol and the compounding math are reproduced in full below (see "Combining values" further down), not just cross-referenced, because a session generating or troubleshooting a script may never open the sibling file, and this is exactly the piece a client expects to work the same regardless of which interface they used.

**Before generating any script, check `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** for terminology ambiguity in the client's request — confirm this is genuinely a Custom Rate, not a preference rule, before writing anything.

## Why this needs its own dry-run discipline, specifically

Custom Rates carry a risk the interactive skill's per-call confirmation exists specifically to catch: **overlap behavior is silent and automatic.** Writing a new rate over an existing one's date range shortens, splits, or replaces it with no separate confirmation from the API — the MCP skill's mandatory "state the plan and get explicit confirmation of the specific values" step is the only thing standing between a client's intent and an unreviewed change to what was already there. An unattended script has no equivalent unless it's built in explicitly, which is what dry-run mode is for.

**Dry-run by default, explicit `--apply` to write:**

1. Fetch current custom rates for the target listing(s) (`GET /listings/{listing_id}/custom_rates`).
2. Detect any overlap between the requested date range(s) and existing rates.
3. If overlap exists, determine adjust-vs-replace from the script's config (never assume — this must be an explicit input the client set, not inferred; see "Combining values" below for how that input should have been captured in the first place and the exact formula to apply).
4. Print the full plan: listing, exact date range(s), rate type, existing value (if any), computed new value, mode used, and — critically — **exactly which existing rate period(s) will be shortened, split, or replaced**, with their resulting before/after date ranges shown explicitly (a mid-period deletion or overlap splits one period into two; show both resulting periods, not just "modified").
5. Stop there without `--apply`.
6. With `--apply`: re-fetch (rates may have changed since the dry-run — especially likely if this runs on any kind of regular schedule), recompute, print again, then write.

## Combining values — inlined here in full, not just cross-referenced

This is the one piece of Context-CustomRates most likely to matter for a script, and the least safe to leave behind a "read that skill first" pointer — a fresh session invoked to generate or run a script may never open the sibling file, and a client expects the compounding behavior to work the same whether they're going through the MCP or a script hitting the API directly. Nothing below should depend on that cross-reference having been followed.

**Capture the choice at config-authoring time, not as a silent default.** If a script's config is being written or edited to change a rate for a listing/date range that could plausibly overlap an existing one, ask the client directly — "adjust the existing rate on top of what's already there, or replace it outright?" — before finalizing `on_overlap`, the same moment the interactive skill asks it. Don't default `on_overlap` to `replace` for convenience, and don't leave the field for the client to discover unprompted and hope they realize it matters; offering the choice explicitly at this point is what makes the distinction "stick" independent of whether anyone reads the sibling skill.

**The math itself is interface-independent — the API never compounds on its own, whether called through the MCP or directly:**
- **`adjustment`-type rates combine additively on percentage points.** Existing rate is 110 (+10%). Client requests +10% more. Submit **120** (+20% total) — not 110 × 1.10 = 121. Formula: `new_value = existing_value + requested_delta_points`.
- **`fixed`-type rates combine multiplicatively on the dollar value.** Existing rate is $100. Client requests +10%. Submit **$110** (100 × 1.10). Formula: `new_value = round(existing_value × (1 + requested_delta_pct / 100))`.

These are opposite operations — confirm `rate_type` before computing, and never apply one formula to the other type.

**At runtime, if overlap is detected and the config never captured a choice**, the script must stop and report that a decision is needed — never guess adjust-vs-replace and never silently fall back to one. Treat this as a hard stop equivalent to a missing `currency` on a `fixed`-type write, not a warning to log past.

## Endpoints (verified against the live RM API docs)

- **Base URL:** `https://api.usewheelhouse.com/ss_api/v1`
- **Auth header:** `X-Integration-Api-Key`
- **Get current rates:** `GET /listings/{listing_id}/custom_rates?channel={channel}`
- **Single rate create/replace:** `PUT /listings/{listing_id}/custom_rates?channel={channel}`
- **Bulk create/replace:** `PUT /listings/{listing_id}/custom_rates/bulk?channel={channel}` — **a distinct path from the single-rate endpoint**, not the same URL with an array body. Verify this path against current API docs before shipping a script, since it was confirmed via live docs fetch rather than the MCP schema dump during this skill's own verification and beta endpoints can shift.
- **Single deletion:** `DELETE /listings/{listing_id}/custom_rates?channel={channel}`, body or params `start_date`/`end_date`.
- **Bulk deletion:** `DELETE /listings/{listing_id}/custom_rates/bulk?channel={channel}`, body `delete_ranges[]`.
- **Custom rate history** (not current state): `GET /preferences/{listing_id}/changelog?channel={channel}`, filter `event` for `Custom rates` entries — the Custom Rates endpoints themselves report only currently-active, future-affecting rates.

Rate-limit headers, `Retry-After` handling, and read-only-key behavior are identical to Context-Preferences-API — see that skill rather than duplicating here.

## Script structure (recommended shape)

```
usage: custom_rates_update.py [--apply] [--listing LISTING_ID] [--channel CHANNEL] [--config path/to/change.json]
```

- `--config` should declare: listing(s), date range(s), `rate_type`, per-weekday values or a single flat value applied to all seven days, `currency` (required for `fixed`), optional `expires_at`, and — when overlap is possible — an explicit `on_overlap: adjust|replace` field. This field should be filled in by *asking the client which they want* while helping set up the config (see "Combining values" above), not left as a default or an unexplained option in a template. Never default it silently; if `--config` omits it and the dry-run detects overlap, the script should stop and report that a decision is needed rather than guessing either direction.
- The dry-run output must show computed values with the formula used spelled out (e.g. `"existing 110 + requested +10pts = 120 (additive, adjustment-type)"`), not just the final number — a client reviewing this before `--apply` needs to be able to check the math, not just trust it.
- Exit non-zero and explain plainly on: `403` (read-only key), a missing `currency` on a `fixed`-type write, or a `207`/`424` from a bulk call — report exactly which date ranges/listings succeeded vs. failed, never a blanket "some failed."
- Log every applied write (listing, date range, rate type, previous value if any, new value, mode used, expires_at if set) to a file, including a record of any existing rate period that was shortened or split as a side effect.

## Running from a scheduled/unattended task

Same requirement as every scheduled skill in this plugin: re-mount any dependent local directory (`--config`, API-key file, log location) via `request_cowork_directory` as the first step of every scheduled firing, per project instructions §14 — a prior run's mount does not carry over. Because this script can silently split or replace a client's existing rate periods, treat a failed mount as a hard stop, never a silent skip, and consider whether a scheduled Custom Rates script should even run unattended at all vs. always requiring a human to review the dry-run output and re-run with `--apply` manually — flag this tradeoff to the client when helping them set up the schedule rather than defaulting to full automation without discussion.

## See also

- **Context-CustomRates** — the interactive MCP sibling; same fixed/adjustment semantics and combine-vs-replace protocol, reproduced above for the scripted case, with the full interactive walkthrough and rationale there.
- **Context-Preferences-API** — for changing what the engine recommends going forward instead of overriding it for specific dates.
- **`${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** — terminology ambiguity, load before generating any script from a client request.
