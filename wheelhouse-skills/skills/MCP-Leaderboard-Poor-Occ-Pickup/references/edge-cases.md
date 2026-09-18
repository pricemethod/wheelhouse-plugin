# Edge Cases & Exclusions (confirmed via live dry runs)

## ID mapping: `listing_id` (bulk KPI) vs. `wheelhouse_id` (GetListings)

`wheelhouse_rmGetBulkListingKpis` rows carry only `listing_id`,
`partner_listing_id`, `value`, `currency`, `updated_at` -- no `channel`, no
name. Naming alone suggested `listing_id` = Wheelhouse-internal ID and
`partner_listing_id` = channel-scoped ID, but a single-channel sandbox
account can't prove it (many listings there have identical values in both
ID spaces by coincidence).

**Confirmed live** against The Luzianne (a real `rentalsunited`-channel
listing, `channel`-scoped id `3995218`, `wheelhouse_id` `56573612`): the
bulk KPI row for this listing was `{"listing_id": 56573612,
"partner_listing_id": "3995218", ...}`. A second listing
(`63721665`/`4816578`) confirmed the same pattern. **Always join bulk KPI
results to `GetListings` on `wheelhouse_id`, never on `partner_listing_id`
unless you've separately confirmed a single-channel account.**

## Pagination has no total-count field

Both `GetBulkListingKpis` and `GetListings` paginate without returning a
total row count. Stop paging when a page returns fewer rows than the
requested `per_page` -- the general convention used elsewhere in this
project, confirmed necessary here too.

## Missing-from-one-metric handling

Per `GetBulkListingKpis` docs, "listings for which no stats have been
generated at all are absent" from that call's results -- meaning the three
KPI calls (`nights_available`, `occupancy_adjusted`, `pickup`) don't
necessarily share the same membership. In the one real dry run so far, all
48 listings appeared in all three sets (no gap to handle) -- but the join
logic still needs to drop any listing missing from one or more sets and
report the count, since this will eventually happen on a portfolio with
newer or less-active listings.

## Automation-off listings distort the list if not gated out

Live dry run flagged the (then) #1 listing, Vatican House, as the most
urgent by occupancy+pickup alone -- but its `automatic_rate_posting_enabled`
was `false` and `base_price` was `null`. Its flat, unchanging $87 asking
rate was a manually-set number entirely outside Wheelhouse's pricing
engine, not a pricing problem to diagnose. Gating the list itself on
`automatic_rate_posting_enabled == true` (rather than just flagging it
during the deep dive) removed 10 of 48 listings in the real account --
mostly obvious "Example"/"Test" sandbox listings, but also this one real
listing that would otherwise have topped the list for the wrong reason.

## Neighborhood pricing: currency and confidence gaps

`GetNeighborhoodPricing` takes no `currency` parameter (unlike
`GetBasePriceRecommendation` / `GetPriceRecommendations`, which do). Live
dry run against Vatican House (an Italy-market listing priced in USD)
returned neighborhood data in **EUR** -- a literal $-vs-€ comparison would
have been meaningless, and there's no in-tool way to convert it. Skip the
numeric comparison and say so when currencies differ.

Separately, a live dry run against a Steamboat Springs, CO listing showed
the risk of a thin comp cluster: `listings_count` was only 6-8 in the near
term (shrinking to 2-3 further out), and prices in the far-future portion
of the same response were obviously corrupted sandbox data -- repeated
identical values of exactly `$9999` across dozens of consecutive dates.
Nothing in the response flags this as unreliable; it has to be inferred
from `listings_count` and from sanity-checking for implausible repeated
values.

## `anchor_credibility` separates real signal from noise

Two real `GetBasePriceRecommendation` calls in this session landed at
opposite ends of `anchor_credibility`:
- Vatican House (0 reviews, 1 lifetime booking): recommendation $222 vs.
  null base price, but `anchor_credibility: 0.0` -- not a usable signal.
- A Steamboat Springs listing with real booking history: recommendation
  $244 vs. an active $278 base price (above even the $268 aggressive
  band), at `anchor_credibility: 90.0` -- a real, actionable finding.

This is why Step 4 of the deep dive explicitly weights the gap by
`anchor_credibility` rather than treating any recommendation-vs-actual gap
as equally meaningful.

## Contradictory signals are informative, not noise to average away

In the same Steamboat Springs dry run, Step 1 (market) suggested the
listing was priced at less than half the neighborhood median (looks
underpriced), while Step 4 (base rate vs. recommendation, high confidence)
showed the base rate above even the aggressive recommendation (looks
overpriced). Both findings are real; they just answer different questions
at different confidence levels. Surface both explicitly rather than
resolving the contradiction silently.
