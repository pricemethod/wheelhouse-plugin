---
name: Context-Events&Seasons-API
description: Use when a Wheelhouse client wants a script calling the RM API directly (X-Integration-Api-Key) to create, rename, redate, or otherwise change a Season or Event (custom_date_ranges) or a rule referencing one, outside a live chat turn. Covers the same id-sharing model and blank-id protocol as Context-Events&Seasons but for unattended/scripted writes -- dry-run by default, prints the full id-migration plan, only writes with an explicit --apply flag. Trigger on "script a season update," "automate an event redate," or any Events & Seasons write that needs to run without Claude in the loop. Use Context-Events&Seasons instead for an interactive chat-turn change via the connected MCP.
---

# Context-Events&Seasons-API (direct RM API)

Unattended sibling of Context-Events&Seasons. Same `custom_date_ranges` two-layer model, same id-sharing behavior, same blank-id protocol — reproduced in full below (see "The two-layer model" and "Decision quick-reference"), not just cross-referenced, because a session generating or troubleshooting a script may never open the sibling file, and getting the id-lifecycle decision wrong here is worse than a bad value: it can silently fork an id other listings were sharing, or leave a rule pointing at nothing. What differs for a script, beyond that reproduced content, is auth/transport and the confirmation-replacement mechanism below.

**Before generating any script, check `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** for terminology ambiguity in the client's request.

## Why this needs its own dry-run discipline, specifically

Events & Seasons writes carry a risk the other two skills in this plugin don't: **the blank-id protocol changes the identifier itself**, not just a value. An unattended script that gets rule-value-only vs. definition-change wrong doesn't just write a bad number — it can silently fork an id that other listings were sharing, or leave a rule pointing at an id that no longer has a matching `custom_date_ranges` entry (an orphaned reference), and nothing about the write itself fails or errors when this happens. This is exactly the kind of mistake that's cheap to catch in a printed diff and expensive to catch after the fact across a client's whole portfolio.

**Dry-run by default, explicit `--apply` to write** — same mechanism as Context-Preferences-API:

1. Fetch full current preferences for every listing in scope.
2. Determine whether the requested change is rule-value-only or a definition change (same decision table as the interactive skill).
3. For a definition change, enumerate **every** rule across every in-scope listing that references the id being changed — this is the step most worth getting right in dry-run output, since it's the part a client can't easily verify by eye afterward.
4. Print the full plan: which `custom_date_ranges` entries change, whether existing ids are reused or a blank-id migration will mint new ones, and which rules will be migrated to the new id vs. left as-is.
5. Stop there without `--apply`.
6. With `--apply`: re-fetch (state may have shifted since the dry-run), re-derive the plan, execute the sequence (definition PUT → read the assigned id straight off that PUT's response body → rule-migration PUT), and print exactly what happened including the actual new id values assigned by the server.

Never let a script guess an id client-side and write it in place of the server-assigned one unless the client explicitly asked for that (see Context-Events&Seasons's note on this) — the default path is always create-then-read-back. **Live-tested 2026-09-15** (real listing, `wheelhouse_id: 64765806`, channel `hypothetical`): the "read-back" step is a single response parse, not a second network call — `PUT /preferences/{listing_id}` returns the full updated preferences object, and a newly-created `custom_date_ranges` entry's server-assigned id (a UUID) is present in that same response body. A script does not need a follow-up `GET` to learn the id, which also means one fewer call against the 60/min rate limit per create-then-reference sequence. A follow-up `GET` is still worth doing if the script wants to confirm persistence independently, but it's a verification step, not a requirement for obtaining the id.

## The two-layer model (identical to Context-Events&Seasons, reproduced here)

- **Layer 1 — `custom_date_ranges`:** the named date-range definition, inside a listing's preferences (`custom_date_ranges` array on `GET`/`PUT /preferences/{listing_id}`). Shape:

  ```
  {
    id?: string,                 // omit only when creating new -- server assigns one
    name: string,                // required
    type: "event" | "seasonal",  // required
    yearly: boolean,              // required
    date_ranges: [                // required, supports multiple ranges per entry
      { start_date: string (ISO date, required), end_date: string (ISO date, required) }
    ]
  }
  ```

  `id` is optional on write but always returned as a string on read. Preserve the existing `id` when updating an entry to keep it linked to what it already means; omit only when creating new. Treat `id` as a string throughout in a script, even though rule `id` fields accept both string and integer for backward compatibility.

  **Live-tested 2026-09-15** (real listing, `wheelhouse_id: 64765806`, channel `hypothetical`): confirmed the assigned id comes back directly in the create PUT's own response body (see the dry-run steps above for the call-count implication) — verified by writing a throwaway test entry, reading its assigned id off the response, then cleaning it up with a second PUT and re-reading to confirm the listing reverted to its pre-test state.

- **Layer 2 — the referencing rule:** a `seasonal`- or `event`-type entry inside a rule-array field (e.g. `minimum_price_rules_v3`), shaped `{type: "seasonal"|"event", id, value}`. The rule's `id` must match a `custom_date_ranges` entry's `id` — a script cannot tell what dates or name an existing rule corresponds to from the rule object alone; always fetch full preferences first.

**id sharing:** entries for the "same" event/season across multiple listings share an `id` only until one of them is rewritten with a different or blank id — there is no cross-listing entity, just a string that happens to match right now. Rules referencing an id are always listing-scoped even when the `custom_date_ranges` id is currently shared. A script iterating over a client's whole portfolio must not assume writing one listing's entry is safe to treat as authoritative for any other listing sharing the same id string.

## Decision quick-reference (identical to Context-Events&Seasons, reproduced here — this is the table a script must encode directly, not just point at)

| Client wants... | Reuse existing `id`? | Notes |
|---|---|---|
| Different price/stay value, same season/event | Yes | Rule-value-only change — affects only the listing being written |
| Rename only, dates unchanged | No — blank-id protocol | Name is part of the definition |
| Redate (dates or `yearly` flag change) | No — blank-id protocol | Even if not currently shared with other listings |
| New season/event from scratch | N/A — omit `id` on creation | Two sequential writes (create, then reference) unless the script assigns the id client-side and accepts responsibility for its uniqueness |
| Delete a season/event | Omit the entry from `custom_date_ranges` on next write | Fetch-then-merge applies — check first whether any rule still references its id; a dangling reference should be flagged in the dry-run output, not left pointing at nothing |

Classify the requested change against this table **before** deciding anything about ids — a rule-value-only change never touches the id, and running a blank-id migration for one anyway is the single most common way this skill's automation goes wrong.

## Placement — is this actually a `seasonal`/`event` entry, or something else? (condensed from Context-Events&Seasons)

- Single recurring month → `monthly` rule, not a Season — doesn't touch this skill.
- Recurring annual period with its own identity → `seasonal`, tied to a Season entry.
- Named one-off or recurring specific event → `event`, reusing an existing entry if the dates already match one rather than creating a duplicate.
- Truly one-off date range with no recurring identity → `custom` rule — doesn't touch this skill at all.
- Before generating a new entry, check whether an existing one already covers the same or overlapping dates; flag an apparent near-duplicate in the dry-run output rather than silently creating one.

## Endpoints

Same as Context-Preferences-API — `custom_date_ranges` is a field within the preferences object, not a separate resource:

- **Read:** `GET /preferences/{listing_id}?channel={channel}`
- **Single-listing write:** `PUT /preferences/{listing_id}?channel={channel}`
- **Batch write:** `PUT /preferences?channel={channel}`, `{"listing_preferences": [...]}`

Base URL, auth header, rate-limit headers, and `Retry-After` handling are identical to Context-Preferences-API — see that skill for the full detail rather than duplicating it here.

## Script structure (recommended shape)

```
usage: events_seasons_update.py [--apply] [--listing LISTING_ID] [--channel CHANNEL] [--config path/to/change.json]
```

- `--config` should describe the change declaratively: which listing(s), the target `custom_date_ranges` entry (matched by current `id` or by name+dates if creating new), what's changing (name/dates/yearly vs. just a referencing rule's value), and — for a definition change — an explicit list of which referencing rules the client wants migrated.
- The dry-run output for a definition change must show the **id migration plan** as its own clearly labeled section, not buried in a generic diff — this is the part most likely to have a consequence the client didn't anticipate (e.g. discovering the id is shared with three other listings they'd forgotten about).
- Exit non-zero and explain plainly on: `403` (read-only key), an orphaned-reference detection (a rule's `id` doesn't match any current `custom_date_ranges` entry — this can indicate a prior run left things inconsistent and is worth surfacing rather than silently working around), or a `warnings` array entry after write.
- Log every applied write, including explicit before/after `id` values for any definition change, to a file — this is the one write type in this plugin where a log entry needs to record an identifier change, not just a value change.

## Running from a scheduled/unattended task

Same requirement as every scheduled skill in this plugin: re-mount any dependent local directory (`--config`, API-key file, log location) via `request_cowork_directory` as the first step of every scheduled firing — a prior run's mount does not carry over, per project instructions §14. Because this skill's writes can change identifiers shared across listings, treat a failed mount as a hard stop, never a silent skip.

## See also

- **Context-Events&Seasons** — the interactive MCP sibling; same two-layer model, decision table, and placement logic, reproduced above for the scripted case, with the full interactive write protocol and rationale there.
- **Context-Preferences-API** — fetch-then-merge mechanics that apply to `custom_date_ranges` exactly like any other rule array.
- **`${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** — terminology ambiguity, load before generating any script from a client request.
