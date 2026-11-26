---
name: MCP-airbnb-new-listing-discount-uplift
description: "Recurring (e.g. daily scheduled) job for Wheelhouse listings that carry a 'new listing' tag: raises a fixed base price and all minimum prices by 25% to offset Airbnb's 20% new-listing discount, then restores the original values after 3 Airbnb reservations, live through the connected Wheelhouse MCP. Use when the user wants to offset Airbnb's new-listing promotion, 'uplift new listings,' 'compensate for the Airbnb new listing discount,' or set up / run / check that job. WRITES base price, minimum price rules, notes and tags: dry run by default, writes only when the run is explicitly in APPLY mode after the user has reviewed a dry run, and creates the tag or segment only after explicit confirmation. Not for general base-price or minimum-price changes (use xContext-preferences) or one-off date overrides (use xContext-custom-rates)."
---

# New Listing Discount Uplift (Airbnb)

Airbnb can give new listings a 20% new-listing discount. While it is live, this job raises the base price and minimum prices by 25% (1 / 0.8 offsets a 20% discount exactly). After 3 Airbnb reservations it restores the originals and removes the tag. It uses only the connected Wheelhouse MCP and can run unattended as a scheduled task once the user has reviewed a dry run.

Check Airbnb's current terms before relying on the 20% figure and the 3-booking threshold; Airbnb can change its new-listing promotion. Both are settings below.

## Settings (confirm with the user on first run)

| Setting | Default | Notes |
|---|---|---|
| Tag name | `Listing-New` | The user tags new listings with it. |
| Segment name | `Listing-New (Uplift Tracking)` | Segment whose filter is that tag. |
| UPLIFT | 1.25 | Offsets a 20% discount. |
| THRESHOLD | 3 Airbnb reservations | When to revert. |

- Scaling: scaled = int(value x UPLIFT + 0.5) (round half up to whole currency units).
- Airbnb match: `source_name` contains "airbnb", case-insensitive. This is an expected value, not confirmed against the API docs: check it against the distinct `source_name` values the report lists (step 3) before the first APPLY run. Cancelled reservations COUNT toward the threshold (Airbnb's promotion is generally tied to bookings received; confirm against Airbnb's current terms). Count every reservation returned for the listing, all pages (per_page 100, increment page until fewer than 100 come back).
- Note categories: every note this job writes uses category ["base_price","minimum_price"]. No start/end dates.
- NOTES ARE NEVER ARCHIVED OR DELETED by this job. They stay active and visible in Wheelhouse as a permanent record.
- Two kinds of notes are written on each listing:
  1. LEDGER note (machine state): description is `NLU-LEDGER ` (prefix with a trailing space) followed by JSON. While a note starts with exactly `NLU-LEDGER ` the uplift is LIVE. On revert its prefix is changed in place to `NLU-LEDGER-REVERTED ` (see Revert) - same JSON, status still active. This is what the job reads.
  2. ACTIVITY notes (human readable): description starts with `New listing uplift` - see below. The job never reads these.
  Ignore all other notes (listings often have many).

## Setup: find the tag and segment (first run)

1. Find the segment by name with `wheelhouse_rmGetSegments`. If found, read its `id` and `filter_backend` and confirm it filters on the tag. Store nothing account-specific in this file; look the ids up on every run.
2. If the segment is missing: look up the tag's id from a tagged listing (`wheelhouse_rmGetTags` on a listing the user names). If no listing carries the tag yet, ask the user to tag one first (or to confirm tagging one with `wheelhouse_rmPutTags`, merge mode, `overwrite=false`).
3. Show the user exactly what will be created (segment name and `filter_backend` {"tags.id":[<tag id>]}) and create it with `wheelhouse_rmPostSegments` only after explicit confirmation. Never create it in an unattended run; report "segment missing" and stop instead.

## Mode
- DRY RUN (default): read only. Report exactly what would be applied/reverted, including the activity note text that would be posted. Make no PUT/POST/note/tag changes.
- APPLY: only if the task prompt contains the word APPLY, and only after the user has reviewed at least one dry run. Then perform writes.

## Constraints
- RM API rate limit is 60 requests/minute; honour `Retry-After` on a 429 (else wait about 60 seconds) and retry that step; never skip silently.
- If the Wheelhouse MCP runs code in an execute sandbox (the tool may be named `execute` or similar, with a per-block call cap and a short time limit), process ONE listing per block for writes (about 10 calls) and a few per block for read-only dry runs. If there is no execute tool, call the `wheelhouse_rm*` tools directly, one listing at a time.
- Some MCP clients have been seen to keep only the last element of an array parameter. Loop one call per item rather than relying on array parameters.
- PUT preferences replaces whole arrays: always send the COMPLETE minimum_price_rules_v3 array (fetched fresh, then scaled), keeping every field on each rule exactly as fetched (echoing `priority` back is harmless; the server ignores it). Send only the fields being changed (base_price, minimum_price_rules_v3).
- Never touch listings outside the segment. Never change max price, min stay, or other rules.

## Base price handling: ALWAYS FIXED
The base rate is managed as a FIXED base_price both when applying and when reverting.
- `wheelhouse_rmGetPreferences` returns base_price = null when a listing uses the recommended base (with base_price_adjustment as a multiplier). The effective base is returned by `wheelhouse_rmGetPriceRecommendations` (field `base_price`, already includes any adjustment).
- Original effective base E = preferences.base_price if not null, else price_recommendations.base_price.
- Uplifted base U = scaled(E), written as a FIXED base_price. Do not send base_price_adjustment: it only applies when base_price is not set, so a fixed base_price takes over. Confirm after the write that recommendations moved by about the uplift (step (c) below).
- Revert writes E back as a FIXED base_price, even if the recommended base has moved since apply. The listing stays on a fixed base after revert; tell the user this on the first run, and offer to return it to the recommended base (base_price = null) by hand if they prefer.

## Run steps
1. `wheelhouse_rmGetSegmentListings(segment_id=<id found in Setup>, exclude_inactive=false)`. If empty, report "no listings tagged" and stop.
2. For each listing: `wheelhouse_rmGetNotes`, `wheelhouse_rmGetPreferences`, `wheelhouse_rmGetPriceRecommendations` (effective base), `wheelhouse_rmGetReservations` (all pages). Classify using ledger notes:
   - A note whose description starts with `NLU-LEDGER ` AND status active -> LIVE uplift
   - Otherwise, any note starting `NLU-LEDGER-REVERTED ` or an archived note starting `NLU-LEDGER` -> previously reverted
   - No ledger note of either kind -> APPLY candidate
   Then: no ledger -> APPLY candidate; previously reverted and no LIVE note (tag has come back) -> FLAG for the user, do not apply; LIVE with Airbnb count < THRESHOLD -> WAITING (report n of THRESHOLD); LIVE with Airbnb count >= THRESHOLD -> REVERT candidate.
3. Report the distinct source_name values seen across the listing's reservations (so the Airbnb string can be verified).

## Apply (listing has no ledger note)
Minimums: for every rule in minimum_price_rules_v3, scale `value` when not null, and scale every non-null entry of `day_of_week_values` (leave nulls as null). Keep all other rule fields as fetched.
Steps (APPLY mode):
(a) `wheelhouse_rmPostNote` the LEDGER note FIRST, category ["base_price","minimum_price"]: `NLU-LEDGER ` + JSON {"v":1,"listing_id","channel","uplift":UPLIFT,"applied_at":ISO date,"original":{"base_price_raw":<null or number as fetched>,"effective_base":E,"base_price_adjustment":<as fetched>,"minimum_price_rules_v3":<as fetched>},"uplifted":{"base_price":U,"minimum_price_rules_v3":<scaled>}}
(b) `wheelhouse_rmPutPreferences` with base_price=U and the full scaled minimum_price_rules_v3. Read `warnings` in the response and report any.
(c) GET preferences again and verify base_price == U and the rules equal the scaled rules; GET price recommendations and confirm prices rose about 25%.
(d) Only after (c) passes, `wheelhouse_rmPostNote` the ACTIVITY note, category ["base_price","minimum_price"], plain text in this form:
   `New listing uplift APPLIED <YYYY-MM-DD> (automated). Airbnb's 20% new-listing discount is offset with a 25% uplift. BEFORE: base price $<E> (<fixed|recommended base>), minimums <describe each rule, e.g. global $79; Fri/Sat $150; within 30 days $80>. AFTER: base price $<U> (fixed), minimums <scaled values>. This reverts automatically after 3 Airbnb reservations; original values are stored in the NLU-LEDGER note.`
If a step fails after the ledger note was written, mark that note reverted in place (prefix change, see Revert) so state stays consistent, and report. Never delete it.

## Revert (LIVE ledger note and Airbnb count >= THRESHOLD)
1. Parse the ledger JSON from the LIVE note. GET live preferences.
2. Guard: live base_price must equal ledger.uplifted.base_price and live minimum_price_rules_v3 must equal ledger.uplifted.minimum_price_rules_v3. If anything differs, someone edited it: do NOT write. FLAG for the user with both sets of values. Leave the tag and note in place.
3. Otherwise (APPLY mode): PUT base_price = ledger.original.effective_base (fixed) and the full ledger.original.minimum_price_rules_v3; GET to verify both match; then `wheelhouse_rmGetTags` and `wheelhouse_rmPutTags` with overwrite=true and every remaining tag name (all except the uplift tag) to remove the tag; `wheelhouse_rmGetTags` again to verify the other tags are intact.
4. Mark the ledger note reverted IN PLACE (do not archive): `wheelhouse_rmPutNote` with the same note_id and description = `NLU-LEDGER-REVERTED ` + the original JSON with "reverted_at":ISO date added. Status stays active.
5. Post a REVERT activity note, category ["base_price","minimum_price"]:
   `New listing uplift REVERTED <YYYY-MM-DD> (automated) after <n> Airbnb reservations. Restored base price $<E> (fixed) and minimums <original values>. Previous (uplifted) values were base $<U>, minimums <uplifted values>. <tag name> tag removed.`
   Do not start this note with NLU-LEDGER.

## Report (always, concise table)
Per listing: title, id, action (APPLIED / WAITING n of 3 / REVERTED / FLAGGED / WOULD APPLY / WOULD REVERT), old -> new base (effective values, fixed) and minimums, Airbnb count, distinct source_name values, and whether the notes were posted. End with counts and any errors or flags needing the user's attention. Say clearly whether the run was DRY RUN or APPLY.

## Known limits
- If someone removes the tag by hand while the uplift is live, the listing leaves the segment and the uplift will not auto-revert. Remind the user in reports to revert by hand or re-tag in that case.
- While the fixed base is in place the listing does not follow Wheelhouse's recommended base; this is intended, and it stays fixed after revert.
- The Airbnb source_name string is an assumption until confirmed from a report on a real Airbnb listing.
- Do not edit or delete a LIVE ledger note by hand: the job cannot undo that listing's uplift without it.
