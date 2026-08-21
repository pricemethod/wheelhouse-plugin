---
name: fast-pickup-priority-list
description: "Builds a live, MCP-only Top 10 of listings selling much faster than the rest of the portfolio -- pickup in the last 14 days as a share of the next 60 days' bookable inventory -- with each listing's neighborhood-occupancy-ratio shown as context, not blended into the score. Trigger on 'which listings are selling fast,' 'who's picking up quickly,' 'fastest-moving listings,' 'outpacing the market,' or any Identify-stage scan about booking velocity. Sibling to occupancy-pickup-priority-list (underperformers) -- this is the opposite signal. Offers two next steps: (1) hand off to price-change-attribution to check if a recent price/rule change, not organic demand, explains the surge; (2) a granular neighborhood-occupancy scan of this listing's unbooked nights ranked by demand -- 'opportunity days' worth a rate push. Not for one named listing's pacing (stly-pacing) or the low-occupancy list (occupancy-pickup-priority-list)."
---

# Fast-Pickup Priority List

The opposite signal from `occupancy-pickup-priority-list`: instead of finding
listings that need rescue, this finds listings that are **already winning**
so a revenue manager can ask "is there more room to push here?" Same
live-MCP-only philosophy -- no cache/sync dependency.

## Step 1 — Build the ranked list

### 1a. Pace metric — deliberately mixed time direction

`pace = pickup(14_0) / nights_bookable(0_60)`

- **Numerator**: `pickup`, window `14_0` (trailing 14 days) -- the only
  option, since `pickup` is a backward-only metric. It counts *nights newly
  booked* in the last 14 days, regardless of how far in the future those
  nights fall (a single 25-night future reservation booked yesterday
  contributes 25 to this number -- pace figures **can and do exceed
  100%**, that's correct, not a bug).
- **Denominator**: `nights_bookable`, window `0_60` (**forward**-looking),
  not `14_0`. This is a deliberate mismatch, confirmed correct by the user:
  pickup's nights are almost always for future dates, so normalizing
  against future bookable capacity ("how much of what's left to sell has
  this listing captured recently") is the more meaningful comparison than
  normalizing against trailing capacity (which would measure something
  closer to "how much of the recent past got consumed," a different and
  less useful question for a forward-looking priority list).
- **Side benefit, confirmed in dry run:** using a forward `nights_bookable`
  also avoids the tenure-truncation problem a trailing version would have
  hit (see `references/edge-cases.md`) -- a brand-new listing still has a
  full 60-day forward window to measure against, rather than a shrunken
  trailing one.
- **Caveat, confirmed in dry run:** if no listings in the portfolio have
  any forward-blocked nights in the next 60 days, `nights_bookable(0_60)`
  is uniformly 60 for everyone and this ranking is mathematically
  identical to ranking by raw `pickup(14_0)`. The normalization only does
  real work once forward-block variation exists across listings -- don't
  be surprised if it doesn't visibly change the order on a given account.

### 1b. Gate

- `automatic_rate_posting_enabled == true` (same rationale as
  `occupancy-pickup-priority-list`).
- `exclude_inactive` defaults to `true` on the bulk KPI calls -- rely on it.
- No availability gate here (unlike the low-performer list) -- a listing
  can be a legitimate fast seller even if it's nearly sold out; that's
  often exactly the listing worth a closer look.

### 1c. Rank and present

Sort descending by `pace`. Take Top 10 (or N). For each, also fetch
`occupancy_neighborhood_ratio` (window `0_60`, **raw**, not adjusted --
confirmed preference) and show it as **separate context, not blended into
the score** -- e.g. "41.7% of forward inventory picked up in the last 14
days; occupancy running 1.45x the neighborhood." A listing can be a fast
seller while merely tracking a hot market (ratio near 1x) or genuinely
outpacing it (ratio well above 1x) -- don't collapse that distinction.

Close with **"Which of these do you want to dig into?"**

## Step 2 — Next steps (per listing, on request)

### 2a. Price-change attribution (pure hand-off)

Point directly to `price-change-attribution` for this listing: was the
pickup surge caused by a recent rate drop or rule change, or does it look
organic? Don't reimplement that correlation here.

### 2b. Opportunity-days scan (granular, new logic)

This is the one genuinely new piece of logic in this skill. **Order
matters -- filter before you rank, not the other way around** (see
`references/edge-cases.md` for why the naive order produces a worse
answer):

1. `wheelhouse_rmGetPriceCalendar` for the listing over the target window
   (default: next 60 days, matching the neighborhood window). Filter to
   nights where `is_available == true` (this already means "not booked and
   not blocked" per the API's own definition -- no need to separately
   check `is_booked`/`block_time`).
2. `wheelhouse_rmGetNeighborhoodOccupancy` for the same listing (fetch
   once, it returns a long daily series regardless -- slice client-side to
   the target window, same convention as `GetNeighborhoodPricing`
   elsewhere in this project).
3. Join on `stay_date`. Among the **unbooked nights only**, sort descending
   by `adjusted_occupancy` (the neighborhood's demand signal for that
   date). Take the top N (5, provisional) as **opportunity days**.
4. Present each: date, neighborhood adjusted occupancy %, and this
   listing's current posted price for that date -- so the user can judge
   at a glance whether the current price already reflects the demand or
   looks low for a hot date.

**Recommendation:** an opportunity day with a posted price well below
other high-demand dates on the same listing's own calendar is worth a
closer look for a custom-rate push (via `custom-rate-intervention`,
confirm before writing) or a marketing nudge -- this step only surfaces
the day, it doesn't write anything.

## Call budget

Step 1: 4 calls regardless of portfolio size up to ~400 listings (pickup,
nights_bookable, occupancy_neighborhood_ratio, plus the listings call for
names/channels/automation status -- reuse the listings call from
`occupancy-pickup-priority-list` if it ran earlier this session). Step 2b:
2 calls per listing (price calendar + neighborhood occupancy).

## Open items / provisional numbers

- Opportunity-days count (top 5) -- a reasonable default, not yet tuned
  against a wider set of listings.
- Whether to eventually add a soft tenure caution for very new listings
  (small-sample `pickup` numerator, even though the forward denominator
  fix already resolved the more serious distortion) -- not implemented
  yet, flagged for a future pass if it turns out to matter in practice.
