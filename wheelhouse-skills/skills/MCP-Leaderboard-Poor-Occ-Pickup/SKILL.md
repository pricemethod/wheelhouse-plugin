---
name: MCP-Leaderboard-Poor-Occ-Pickup
description: "Builds a live, MCP-only Top 10 (or N) list of listings most worth attention today, ranked by low near-term occupancy and low recent pickup, gated to listings that are actionable (automated pricing on, enough available nights). No cache/sync skill required -- pulls straight from the connected Wheelhouse MCP via wheelhouse_rmGetBulkListingKpis and wheelhouse_rmGetListings. Trigger on 'which listings need attention,' 'what should I prioritize today,' 'low occupancy report,' 'who's not booking,' or any Identify-stage scan wanting a live read over a cache. Then offers a one-listing live deep dive: overpriced vs. market, overpriced vs. own history (hands off to MCP-future-rate-overpricing), minimum price binding, and base rate vs. recommendation. Not for a single named listing's pacing/overpricing check (use MCP-stly-pacing-calculations / MCP-future-rate-overpricing directly)."
---

# Occupancy + Pickup Priority List

A live-MCP-only Top 10, and a scoped one-listing deep dive, for the Identify
stage of Active Revenue Management. Everything here is a fresh API call --
there is no local cache and no dependency on `COWORK-Data-Syncs`. That's
the whole point of this skill: a quick, always-current read without
needing a sync pipeline set up first.

The deep dive is deliberately limited to the four checks below.

## Step 1 — Build the ranked list

### 1a. Resolve the portfolio (for names + automation status)

Call `wheelhouse_rmGetListings` (paginate: keep requesting `page+1` until a
page returns fewer than `per_page` rows -- there's no total-count field to
key off of). From each row keep `wheelhouse_id`, `title`, `channel`,
`is_active`, and `listing_preferences.automatic_rate_posting_enabled`.

### 1b. Pull the three ranking signals

Three separate `wheelhouse_rmGetBulkListingKpis` calls, each paginated the
same way (`per_page: 100`, stop when a page is short):

| Call | metric | window |
|---|---|---|
| Availability gate | `nights_available` | `0_60` |
| Occupancy signal | `occupancy_adjusted` | `0_30` |
| Pickup signal | `pickup` | `7_0` |

None of these are monetary metrics, so `currency` is irrelevant here --
don't pass it.

**ID mapping (confirmed live, not just inferred from docs):** each row's
`listing_id` is the **Wheelhouse-internal ID** (matches `GetListings`'
`wheelhouse_id`), and `partner_listing_id` is the **channel-scoped ID**
(matches `GetListings`' `id`). Join on `wheelhouse_id`, not on
`partner_listing_id`. See `references/edge-cases.md` for how this was
verified.

### 1c. Join and gate

Join all three KPI results plus the listings map on `wheelhouse_id`.

- **Drop any listing missing from any one of the three KPI sets** (data not
  yet generated for that metric/window) rather than treating it as zero or
  worst-case. Report the count dropped this way.
- **Gate 1 -- automation:** keep only `automatic_rate_posting_enabled ==
  true`. A listing Wheelhouse isn't actively pricing isn't something this
  list can act on -- surfacing it just wastes the deep dive later. (This
  also happens to catch most "Example"/"Test" demo listings in a sandbox
  account.)
- **Gate 2 -- availability:** keep only `nights_available (0_60) >= 30`
  (50% of the 60-day window) -- **provisional, tune per portfolio**. Below
  this, there isn't enough open inventory left to meaningfully act on even
  a perfect diagnosis.
- `exclude_inactive` on the bulk KPI calls defaults to `true` -- rely on
  that rather than re-filtering `is_active` yourself.

### 1d. Rank

Within the gated pool, compute a percentile-rank **urgency score** for
`occupancy_adjusted` and `pickup` independently (ascending: lowest value =
highest urgency), average the two into a composite, sort descending.

See `references/methodology.md` for the exact tied-rank-averaging formula
and the confirmed tie-break rule (available nights descending, then
`wheelhouse_id` ascending) -- this isn't cosmetic, it resolved a real
three-way tie in dry-run data.

### 1e. Present

Plain-language Top 10 (or however many requested), not a raw dump: name,
channel, the three underlying numbers, and the composite score. Close with
**"Which of these do you want to dig into?"**

## Step 2 — Deep dive (one listing, on request)

Resolve `listing_id` + `channel` for the chosen listing if not already
known this session (from the Step 1 join). Everything below is read-only
diagnosis -- any resulting write goes through `Context-CustomRates`,
which confirms before writing, never
from here.

### Step 0 — Engine-active safety net

Because Step 1's Gate 1 already filters to automated listings, this should
rarely fire -- but check anyway (`wheelhouse_rmGetPreferences`:
`automatic_rate_posting_enabled`) in case the list being worked from is
stale or the user named a listing outside the Top 10 directly. If
`automatic_rate_posting_enabled == false`, say so as the headline finding
and stop -- the four checks below aren't meaningful for a listing
Wheelhouse isn't pricing.

**Don't treat `base_price: null` as "engine off."** `null` means the listing
uses Wheelhouse's recommended base price rather than a manually set one --
the normal, well-configured state. Note it (it matters for Step 4) and
carry on.

### Step 1 — Market comparison

`wheelhouse_rmGetNeighborhoodPricing` (fetch once for the listing, it
returns the full available horizon regardless -- slice client-side to the
window you care about, don't call it per date range). Compare against the
listing's own `asking_rate` for the same window (from
`wheelhouse_rmGetListingKpis`), **made fee-inclusive first**.

**Fee basis:** neighborhood prices (`median_price`, `low_price`,
`high_price`) include the fees guests pay on top of the nightly rate;
`asking_rate` excludes them. Comparing the two raw biases the read toward
"underpriced vs. market." Call `wheelhouse_rmGetFeeImpactCalendar` once
with `fallback=estimate` (same window) and multiply the listing's price by
`fee_multiplier` before comparing. Report the multiplier and its `source`
in the output: `setting` (the listing's fee adjustment), `estimate`
(estimated from recent reservations), or `none` (no fee data -- the
multiplier is `1.0`, so the comparison is still rent-vs-fee-inclusive and
should be flagged as biased toward "underpriced").

Cleaner, if the extra call is acceptable: compare per date rather than as a
window average -- `wheelhouse_rmGetPriceCalendar` `price` ×
`fee_multiplier` for each open date vs. that date's `median_price` /
`low_price` / `high_price`.

**Confidence gate (added after stress-testing against a real listing --
see `references/edge-cases.md`):**
- If `currency` in the neighborhood response differs from the listing's own
  currency, **skip the numeric comparison** and say so explicitly --
  `GetNeighborhoodPricing` has no `currency` conversion parameter, unlike
  `GetBasePriceRecommendation`, so there's no safe way to compare mismatched
  currencies without an external FX rate.
- If `listings_count` for the relevant dates is small (**below 10,
  provisional**), flag the comparison as low-confidence rather than
  presenting it with the same weight as a well-populated cluster.
- Reject implausible values before using them -- specifically, a run of
  identical extreme prices (e.g. the same capped value repeated across many
  consecutive dates) is a data artifact, not a real signal. Don't average
  it in.

### Step 2 — Own-historicals comparison

**Hand off to `MCP-future-rate-overpricing`** for the full month-by-month,
weekend/weekday breakdown against same-period-last-year transacted ADR.
Don't reimplement that comparison here.

### Step 3 — Minimum-price floor check

`wheelhouse_rmGetPreferences`: is `minimum_price_rules_v3` non-empty, or is
`min_min_price` sitting above the market/historical comparisons from Steps
1-2? (Floors are rent-only: compare them to the Step 1 market figures
divided by `fee_multiplier`, not to the fee-inclusive medians.) Cross-check with `min_price_occurrence` from `GetListingKpis` (share of
near-term nights actually pinned at the floor) when it's populated -- it's
sometimes `null` if that stat hasn't been generated yet for the listing,
which isn't the same as "zero occurrences."

### Step 4 — Base rate vs. recommended

`wheelhouse_rmGetBasePriceRecommendation` returns both sides of the
comparison in one response: compare `base_price_recommended` (and the
`base_price_conservative` / `base_price_aggressive` band) against
`base_price_selected`, the currently active base -- not against
`base_price` from preferences. If `base_price` was `null` in Step 0, the
listing is already on the recommended base, so the gap is zero by
construction -- don't flag it. (Unverified: what `base_price_selected`
itself reports when `base_price` is `null`; if it shows a value that
differs from `base_price_recommended`, treat that as a caveat to mention,
not a finding.) Optionally surface `base_price_attribution` to explain
where a real gap comes from. **Weight this by `anchor_credibility`, not just the raw
gap** -- a large gap at `anchor_credibility: 0` (typically a listing with
near-zero booking history) is not a usable signal; the same-size gap at
`anchor_credibility: 90` is.

### Handling contradictions between Steps 1 and 4

These two checks can legitimately disagree -- a listing can be priced
*below* the neighborhood median while its *base rate* still sits above
Wheelhouse's own recommendation (confirmed in dry-run: a listing at ~$279
against a ~$650 neighborhood median, yet with a $278 base price above a
$268 aggressive recommendation at `anchor_credibility: 90`). That dry run
compared the rent-only `asking_rate` against fee-inclusive neighborhood
prices, so part of that gap is likely fees -- apply the Step 1 fee basis
before reading any such contradiction as real. **Present both
findings explicitly with their confidence levels rather than collapsing
them into one verdict.** All else equal, trust the check with the
higher/explicit confidence score (`anchor_credibility`) over one running
against a thin or currency-mismatched comp cluster -- but say why, don't
just silently pick one.

## Call budget

Step 1 (the list): 4 calls total regardless of portfolio size up to ~400
listings (3 bulk KPI calls + 1 listings call, each paginated only if the
portfolio exceeds 100 listings). Step 2 (one listing's deep dive): 5-6 calls
(preferences, neighborhood pricing, listing KPIs, fee impact calendar, base
price recommendation, plus the optional per-date price calendar, plus
whatever `MCP-future-rate-overpricing` uses internally for Step 2). Running
the deep dive across all 10 listed listings at once is a real, larger call
volume (~50-60 calls) -- tell the user the estimate before doing that rather
than silently running it, since it approaches the API's 60 requests/minute
limit -- let them proceed or narrow to fewer listings.

## Open items / provisional numbers

- Availability gate threshold (30 of 60 nights) -- confirmed by the user for
  this account, revisit if it stops feeling right for a different portfolio
  size or seasonality.
- Neighborhood cluster-size confidence threshold (10 listings) -- a
  reasonable starting point from one dry run, not yet validated against a
  wider set of markets.
