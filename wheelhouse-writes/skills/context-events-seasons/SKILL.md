---
name: Context-Events&Seasons
description: Use when a Wheelhouse client wants to create, rename, redate, or otherwise change a Season or Event (the named date ranges under the Events & Seasons configuration group) via the connected Wheelhouse MCP, or wants to add/update a seasonal- or event-type pricing rule that references one. Covers the two-layer id-sharing model, when to reuse an existing id vs. mint a new one (the blank-id protocol), and how to migrate rules after a redate. Trigger on "add a holiday season," "create an event for the marathon weekend," "rename my winter season," "change the dates on this event," "add a rule for [named season/event]," or any request touching Events & Seasons. Always read alongside Context-Preferences when the resulting change also involves a seasonal/event rule -- this skill governs the date-range definition and id lifecycle; Context-Preferences governs the rule that references it.
---

# Context-Events&Seasons (MCP)

Guidance for Wheelhouse's Events & Seasons system: the named date-range definitions (`custom_date_ranges`) that `seasonal`- and `event`-type preference rules reference by `id`. This is one of the more error-prone parts of the write surface because the same-looking edit ("just change this season's dates") can mean two very different operations depending on whether you're changing a *value* or a *definition* — and picking wrong either silently detaches a listing from the Event/Season other listings share by id, or silently orphans a rule.

**Before interpreting any request, check `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`.** "Seasonal rate" and "event" are both flagged there — a client using either word may not mean the Wheelhouse-specific feature this skill governs.

## The two-layer model

- **Layer 1 — `custom_date_ranges`:** the named date-range definition itself. Lives inside a listing's preferences (`custom_date_ranges` array on `wheelhouse_rmPutPreferences`/`wheelhouse_rmGetPreferences`). Verified shape (from the live tool schema):

  ```
  {
    id?: string,              // omit only when creating new -- server assigns one
    name: string,             // required
    type: "event" | "seasonal",  // required
    yearly: boolean,          // required
    date_ranges: [            // required, array (supports multiple ranges per entry)
      { start_date: string (ISO date, required), end_date: string (ISO date, required) }
    ]
  }
  ```

  `id` is **not** in the schema's required fields — it's optional on write, but the server **always returns it as a string** on read. The field description is explicit: *"Preserve the existing `id` when updating an entry to keep it linked; omit only when creating a new range (one will be assigned)."* Rule `id` fields accept both string and integer for backward compatibility, but treat `id` as a string throughout — use string comparisons when matching a rule's `id` against a `custom_date_ranges` entry's `id`.

  **Live-tested 2026-09-15** (a `hypothetical`-channel test listing): `wheelhouse_rmPutPreferences` with a new `custom_date_ranges` entry and `id` omitted returned a server-assigned id (a UUID, e.g. `"47df6a70-e720-4634-855b-1afdee427a3b"`) — and critically, **the assigned id came back directly in that same PUT's response body**, which is the full updated preferences object, not a bare ack. A follow-up `wheelhouse_rmGetPreferences` returned the identical entry, confirming persistence, but wasn't needed to learn the id. Confirmed by cleaning up (a second PUT with `custom_date_ranges: []`) and re-reading to verify the listing reverted to its pre-test state.

- **Layer 2 — the referencing rule:** a `seasonal`- or `event`-type entry inside one of the rule locations listed below, shaped `{type: "seasonal"|"event", id, value | day_of_week_values}` — a rule carries `value` **or** `day_of_week_values` (7 entries, index 0 = Sunday), never both. `priority` is read-only and server-assigned (any value submitted is ignored); don't set it on a new rule. The rule's `id` must match a `custom_date_ranges` entry's `id` — the rule is meaningless without it. **Always fetch full preferences before interpreting any `seasonal`/`event` rule** — you cannot tell what dates or name it corresponds to from the rule object alone.

**Where `seasonal`/`event` rules can live (verified against the OpenAPI spec)** — scan **all** of these when enumerating rules that reference an id, so a redate or delete doesn't leave orphaned rules behind:

- Top-level rule arrays: `minimum_price_rules_v3`, `maximum_price_rules_v3`, `minimum_stay_rules_v3`, `demand_sensitivity_rules`, `historical_anchoring_rules`
- `checkin_checkout.check_in_rules`, `checkin_checkout.check_out_rules`
- `long_term_discounts.rules` (an object keyed by length-of-stay threshold, e.g. `"7"`, `"28"` — scan every key's array), plus the deprecated `long_term_discounts.weekly_rules` / `long_term_discounts.monthly_rules`
- Nested `.rules` arrays under `last_minute_discount`, `far_future_premium`, `seasonality_adjustment`, and `day_of_week` (these are used when that object's `type` is `"CUS"`)

**id sharing:** each listing stores its own copy of every Event or Season it belongs to, and entries for the same event/season **share the same `id` across listings — that shared `id` is what links them as one Event/Season and enables bulk adjustments in the Wheelhouse UI** (confirmed in the API spec). If a listing's entry is written with a new or changed `id` (including a blank-id rewrite, which mints a new one), that listing's entry is **no longer linked** to the others and will not be included in future UI bulk edits of the original Event or Season. Rules referencing an id are always listing-scoped, even when the `custom_date_ranges` id is shared.

## Deciding which operation you need

**Rule-value-only change** (same dates, same name, client just wants a different price/stay value for an existing season/event): resubmit the `custom_date_ranges` entry with its **existing `id` unchanged**, and separately update the value on the rule that references it. This affects only the listing being written — no other listing sharing that id is touched.

**Definition change** (dates, name, or the `yearly` flag are changing): first establish whether the change is for **this listing only** or for **every listing sharing the id**.

- **This listing only (default, verified path):** use the blank-id approach. The spec documents omitting `id` as the safe way to change a definition on one listing without affecting others — the server assigns a new independent id scoped to that listing. The consequence: **this listing is detached from the shared Event/Season** and will no longer be included in future UI bulk edits of it. That detachment must be stated to the client as part of the confirmation for every blank-id redate/rename (see the write protocol), even when the id doesn't currently appear shared — if it is shared, the link is lost.
- **Every listing sharing the id (unverified option):** keep the existing `id` and write the new definition to **each** listing sharing it (`wheelhouse_rmPutPreferencesBatch`), so the link is preserved. **This path is not yet verified** — the spec confirms the shared-id linkage but does not document what happens when an existing id is resubmitted with new dates/name. Before relying on it, it needs a test (e.g. two `hypothetical` listings sharing an id: write new dates with the same id to both, confirm via `wheelhouse_rmGetPreferencesBatch`, then check the UI still groups them). Until verified, offer it to the client only as an option that carries this caveat, never as the default.

Blank-id steps:

1. `PUT` the listing's `custom_date_ranges` array with the modified entry's `id` field **omitted** (the server assigns a new one), and every other entry retained with its **current** `id` values unchanged (fetch-then-merge applies to this array exactly like any other rule array — see Context-Preferences).
2. Read the newly-assigned `id` for the modified entry **directly off that same PUT's response body** — live-tested and confirmed: `wheelhouse_rmPutPreferences` returns the full updated preferences object, including the new id, so no separate `GetPreferences` call is needed to learn it (though re-fetching afterward is still a reasonable way to double-check persistence if you want the extra certainty).
3. Migrate any rules that referenced the old id to the new id — a second `PUT` if the first one didn't also carry the rule update. (A new entry and its referencing rule *can* go in the same `PUT` if you assign the entry a client-side `id` yourself rather than omitting it — but then you're responsible for that id being unique and not colliding with an existing one; the safer default is two sequential PUTs with the server assigning the id.)
4. **Enumerate every affected rule for the client before writing anything** — scanning every rule location listed under "Where `seasonal`/`event` rules can live," not just the top-level rule arrays — and let them choose which rules should follow the redate vs. which should keep referencing the old (now-orphaned, but not deleted) date-range definition. Some clients may want the old id's rule left alone deliberately (e.g. it's actually about to be reused for a different, unrelated purpose).

Other listings sharing the old id keep their own unchanged copy of that `custom_date_ranges` entry (old dates/name, old id) and stay linked to each other — but **the listing you wrote is now detached** from that shared Event/Season, so future UI bulk edits of it will skip this listing.

**Creating a new event/season + a rule for it in one motion:** the server hasn't seen the new id yet at the start of the request, so you cannot reference an id that doesn't exist within the same rule set it's being created in unless you assign the id client-side. Default to two sequential PUTs: first create the `custom_date_ranges` entry (omit `id`), read the server-assigned id straight off that PUT's response (no extra `GetPreferences` call needed — see the live-tested note above), then write the rule referencing it.

## Decision quick-reference

| Client wants... | Reuse existing `id`? | Notes |
|---|---|---|
| Different price/stay value, same season/event | Yes | Rule-value-only change |
| Rename only, dates unchanged (this listing only) | No — blank-id protocol | Name is part of the definition. Detaches this listing from the shared Event/Season — include that in the confirmation |
| Redate (dates or `yearly` flag change) (this listing only) | No — blank-id protocol | Even if not currently shared. Detaches this listing from the shared Event/Season — include that in the confirmation |
| Redate/rename the event for **every** listing sharing the id | Yes — keep the id and write the new definition to each sharing listing (`wheelhouse_rmPutPreferencesBatch`), preserving the link | **Unverified** — needs a test before relying on it (see "Definition change" above); offer only with that caveat |
| New season/event from scratch | N/A — omit `id` on creation | Two sequential PUTs (create, then reference) unless client-assigning the id |
| Delete a season/event | Omit the entry from `custom_date_ranges` on next write | Fetch-then-merge: the array write drops anything not included. Check first whether any rule (in any of the rule locations listed above) still references its id — a dangling reference to a deleted `custom_date_ranges` entry should be flagged and removed from the rule set too, not left pointing at nothing. |

## Placement: is this actually a `seasonal`/`event` rule, or something else?

Not every date-bound request should become an Events & Seasons entry. Decision logic (shared with Context-Preferences):

- Single recurring month → `monthly` rule, not a Season.
- Multiple months sharing a pattern → one `monthly` rule with a `months` array.
- Recurring annual period with its own identity (a "season") → `seasonal`, tied to a Season entry — prefer this over a recurring `custom` rule with `yearly: true`.
- Named one-off or recurring specific event → `event`, reusing an existing Events & Seasons entry if the dates already match one rather than creating a duplicate.
- Truly one-off date range with no recurring identity → `custom` rule with `yearly: false` — doesn't touch this skill at all.
- No date variation → `global`.

Before creating a new Season/Event entry, check whether an existing one already covers the same or overlapping dates — creating a near-duplicate entry (e.g. two separate "Winter Holidays" entries with slightly different date ranges) is a common source of confusing, hard-to-audit rule sets. Surface any overlap to the client rather than silently creating a duplicate.

## Write protocol

1. Resolve ambiguity against the shared lexicon reference — confirm the client actually means the Events & Seasons feature.
2. Fetch full current preferences (`wheelhouse_rmGetPreferences`) — never interpret or write a `seasonal`/`event` rule or a `custom_date_ranges` array from partial information.
3. Determine which operation applies using the decision table above; state it back to the client along with which listings will and won't be affected.
4. For a definition change, enumerate every rule that references the id being changed, across the listing(s) in scope and across every rule location listed under "Where `seasonal`/`event` rules can live," before writing.
5. Confirm with the client before writing — same confirm-before-write default as Context-Preferences, no built-in bypass, session-level opt-out only if the client explicitly asks and every write is still logged afterward. For a blank-id redate/rename, the confirmation must explicitly say **"this listing will be detached from the shared Event/Season [name] and won't be included in future bulk edits of it in the Wheelhouse UI."**
6. Write via `wheelhouse_rmPutPreferences`/`wheelhouse_rmPutPreferencesBatch`, including the full `custom_date_ranges` array (fetch-then-merge) and any rule updates needed to keep references consistent.
7. Check the response `warnings` array and surface any non-empty result.
8. Log what changed, including old and new `id` values for a definition change — this is the one write type in this plugin where the *id itself* is part of what changed, and a client revisiting this later needs that trail.

## See also

- **Context-Preferences** — full settings table, rule-array shapes, rule hierarchy, and fetch-then-merge mechanics that apply to `custom_date_ranges` exactly like any other rule-array field.
- **Context-CustomRates** — a Custom Rate set "for the holiday weekend" is a different, non-hierarchy-participating override; don't conflate a Custom Rate covering an event's dates with an `event`-type preference rule.
- **`${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`** — terminology ambiguity, load before interpreting any request.
- **Context-PriceLabsMigration** — if the client describes a "Pricing Profile" or "Seasonal Pricing Customization," that's a PriceLabs bundle of several settings, not a single Wheelhouse object; see that skill for the translation before planning writes here.
