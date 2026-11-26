---
name: MCP-dynamic-set-builder
description: "Builds a Wheelhouse Dynamic Set (comp set) from one example listing or complex, live through the connected Wheelhouse MCP. Interviews the user (example address, complex name, radius, bedrooms, OTA channels, future bookable minimum, lookback, own-listing exclusion, known includes/excludes, views), pulls candidates with wheelhouse_rmGetSetCandidates, scores each on Same complex, Openness and Performance (weighted 40/25/35 by default (same/open/perf) — overall score adjustable), and shows a sortable picker with checkboxes, OTA links and a Create set button that sends the selection back. Writes one thing: after the user picks, it restates the set name and every selected listing and creates the set with wheelhouse_rmCreateSet only after the user explicitly confirms. Use whenever someone wants to build, create, generate or suggest a Dynamic Set, comp set, competitive set or SETS for a listing, complex, condo building or resort, find comparable listings in the same complex, or asks which competitors to track, even if they don't say 'Dynamic Set'."
---

# Dynamic Set builder

Turns one example listing (or complex) into a scored, hand-picked Dynamic
Set. Everything is live from the Wheelhouse MCP; nothing is cached.

The user picks the final members. The skill's job is to surface the right
candidates, explain why each scored as it did, and create the set only when
the user has picked members and explicitly confirmed the exact set to be
created (Step 5).

## Step 1: Ask the questions, one at a time

Run this as a real back-and-forth: ask one question, stop and wait for the
reply, then ask the next. Never bundle these into one message, a list, or
a single long paragraph — each one is its own turn, the way this skill
itself was interviewed into existence. Write each prompt conversationally,
not as a form label, and fold the default into the sentence in brackets
so the user can just say "default" and move on.

For the two questions that are really a choice from a short fixed set
(OTA channels, own-listing exclusion), use your client's multiple-choice
question tool if it has one (for example `ask_user_input_v0` in Claude
chat) — tappable options are faster than typing. If there is no such tool,
ask in plain text and list the options. Everything else is a plain
conversational question expecting free text; don't force those into
buttons.

Ask in this order, one per turn:

1. "Which listing should we use as the example? Give me one of your
   listings — name, nickname or ID — or just its address; it doesn't need
   to be a listing in your Wheelhouse account." (free text)
2. "What complex or development is it in, and what's its exact name? Toss
   in the complex's address too if you have it." (free text; address is
   optional, say so)
3. "Radius to search, in miles? [0.6 mi] — this just limits the search,
   it's never part of the score." (free text)
4. "Bedroom count?" (free text)
5. "Limit this to specific OTA channels, or search all of them?"
   (choice question, single or multi select: All, Airbnb, Vrbo,
   Booking.com)
6. "What's the minimum number of bookable nights in the future, and over
   what window? [30 nights in the next 90 days]" (free text)
7. "How many nights does a listing need to have actually been bookable,
   and over what trailing window? [150 bookable nights over the last 12
   months]" This is a count of nights actually open within the window,
   not just how long the listing has existed — e.g. "180 bookable nights
   in the trailing 365 days" or "20 in the last 90." The API only has
   90-day or 365-day windows; if the user names something else, ask them
   to pick the closer of the two and say which you're using.
8. "Should we exclude your own listings from the set?"
   (choice question, single select: Yes, No)
9. "Any competitor complexes or listings you already know you want
   included or excluded? Names, OTA links or IDs are all fine. [None]"
   (free text)
10. "Any views worth weighting — ocean view, lake view, anything like
    that? Totally optional." (free text)
11. Once 1-10 are answered, ask about the scoring thresholds as their own
    turn: "Last thing — want to touch any of the scoring thresholds, or
    keep the defaults? Full proximity credit within 0.12 mi, fading to
    zero by 0.6 mi; a listing counts as stale past 30 days unscraped; a
    listing must have trailing adjusted occupancy above 20% to be
    considered at all; full openness credit at 80% of nights open or 270
    future bookable nights (180 for partial credit); full performance
    credit at 75% future occupancy (tested in steps from a 40% floor) or
    80% trailing occupancy; and the overall score weights Same complex
    40%, Openness 25%, Performance 35%." If the user says keep defaults
    (or doesn't raise it again), use the defaults. If they want to adjust
    one or more, ask for just those values, one at a time, the same way.
    If they adjust the weights, confirm the three numbers sum to 100%
    before using them.

If the user volunteers several answers in one message (they often will,
especially once they know the flow), accept all of them and skip straight
to the next unanswered question — don't re-ask something they already
gave you just to keep the one-at-a-time shape.

Use miles for every distance you ask about or show. The API works in
meters; the script converts.

Don't start pulling data until the example listing, the complex name and
the bedroom count are answered, and the user has responded to the
thresholds question in 11.

## Step 2: Resolve the example

1. Call `wheelhouse_rmGetListings` (paginate until a short page). Match
   what the user gave against `id`/`wheelhouse_id`, `title`, `nickname` and
   `location.address`. Addresses are often blank, so also try the complex
   name. If one listing matches, use its `location.latitude/longitude`,
   `num_bedrooms` and `room_type`. If several match, ask which one.
2. If nothing matches, geocode with your client's place or map search
   tool (for example `places_search` in Claude chat; if there is none, ask
   the user for the coordinates) in this order: the
   example address, then the complex address, then the complex name. Take
   the coordinates of the matching result. Ask the user for the listing
   type (apartment/condo vs home) if you can't tell.
3. Center the search on the example (matched listing or its geocoded
   address). If a complex address was also given and it geocodes more than
   0.2 mi from the example, say so and ask which point to search from,
   since one of them is probably wrong. If only the complex address or
   name resolves, center on the complex.
4. Keep every value in each own listing's `channel_ids` as
   `own_channel_ids` (for own-listing exclusion).
5. Example class: `apartment` for apartment/condo/townhome-in-complex,
   `house` for homes and cabins, `room`, or `hotel`.
6. Write 3-6 lowercase variations of the complex name that hosts actually
   put in titles: drop "The", "Resort", "Condominiums", "Villas"; common
   abbreviations ("LR" for Lakeside Resort); split or joined words. List them
   for the user in one line so they can correct them, but don't block on
   it.

## Step 3: Fetch and score

1. Read `scripts/fetch_and_score.py`. Fill in `CONFIG` from the answers
   (see `references/methodology.md` → "Translating the user's answers" for
   the pro-rating and window rules). Pass the whole file, CONFIG filled,
   as the `code` of one call to the Wheelhouse MCP's `execute` tool (its
   full name carries your client's prefix, e.g. `mcp__wheelhouse__execute`).
2. The result is compact JSON: `rows`, `counts` (how many were dropped at
   each gate), `calls`, `truncated`.
3. If `truncated` is true, the radius pulled more than the page budget.
   Tell the user and suggest a tighter radius rather than silently scoring
   a partial pool.
4. If a known include didn't come back at all (it's outside the radius or
   not in Wheelhouse's market data), say so and offer to widen the radius.

Exclusions and the include/exclude lists are applied inside the script
before any scoring, as the user asked. Includes are labeled "Known include"
and skip the gates but are still scored.

## Step 4: Show the picker

1. Read `assets/picker_template.html`. Replace `__DATA__` with the execute
   result JSON exactly as returned and `__META__` with
   `{"example": "<example title or address> · <N>BR · <complex name>", "views": true|false}`.
2. If your client has an inline widget tool (in Claude chat: load the
   Visualizer `interactive` module with `mcp__visualize__read_me` once,
   then render with `mcp__visualize__show_widget`), use it. The inline
   widget is what makes the Create set button send its message: it calls
   `sendPrompt` with the set name and selected IDs. Nothing is pre-checked.
   If there is no inline widget tool, use the standalone file in step 5.
3. Branding: the template already uses Wheelhouse magenta (#e80edf) for the
   primary action and host CSS variables for everything else so it reads
   in light and dark mode. Keep that if you change the visual design.
4. Above the widget, in 2-4 sentences of chat text: how many candidates
   were pulled and scored, the gate counts that matter (own, type
   mismatch, insufficient history, stale, future bookable), and any
   translation you made (e.g.
   "30 nights in 90 days was pro-rated to 122 in the next 365, the only
   forward window the API has"). Mention view matches only if views were
   given.
5. If a standalone file is wanted (sharing, or no inline widget tool),
   save the filled template wrapped in a basic HTML page to the user's
   output or working folder (or publish it as an artifact) and say where
   it is. Outside the inline widget `sendPrompt` doesn't exist, so the
   button shows a copyable message instead; the user pastes it back into
   the chat.

## Step 5: Create the set

When a message arrives like `Create the Dynamic Set "<name>" with these
listing IDs: 1, 2, 3`, that is the user's selection, not yet the go-ahead
to write. Creating a set changes the user's Wheelhouse account, so:

1. Show exactly what will be created: the set name, the member count, and
   every selected listing (ID, title, OTA). Flag any "Also on ..." copies
   of the same unit and any known includes. Ask the user to confirm.
2. Only after an explicit yes, call `wheelhouse_rmCreateSet` with `name`
   and `listing_ids` (integers). Add the example listing's currency if
   known. If the user edits the list instead, restate the new list and
   ask again.
3. Reply with the set name, member count and set ID from the response.
   The set is created on the free plan; KPIs need an upgrade
   (`wheelhouse_rmUpgradeSet`), so mention it once.
4. Offer, don't do: associate the example listing with the set
   (`wheelhouse_rmPutSetAssociatedListings` with its channel listing ID and
   channel). That's a separate change the user didn't ask for; if they
   want it, show exactly what will change and confirm first.

If creation fails because some IDs aren't eligible, report which, and offer
to create the set without them (restate the reduced list and confirm
before writing).

## Things to keep straight

- Radius is a filter only. Proximity scoring uses distance with its own
  full-credit distance (question 11) to allow for blurred OTA pins.
- The API's forward window is fixed at 365 days and trailing at 365 or 90.
  Translate the user's windows and say you did; never claim a precision the
  data doesn't have.
- The same unit is often listed on several OTAs. The picker labels exact
  title matches "Also on ...". Point this out when the user selects
  several copies of one unit.
- Views are a flag column, not part of the score — the three category
  scores (Same complex, Openness, Performance) combine by the weights in
  question 11, not a plain average. Default is 40/25/35
  (same/open/perf); confirm any custom weights the user gives sum to
  100%.
- Every threshold comes from the user's answer to question 11 and goes
  into CONFIG. If the user disagrees with a ranking, change the threshold
  with them and rerun rather than hand-editing scores.
