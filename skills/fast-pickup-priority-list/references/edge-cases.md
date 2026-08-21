# Edge Cases & Design Decisions (confirmed via live dry runs)

## Why the pace metric deliberately mixes time direction

First design pass used `pickup(14_0) / nights_bookable(14_0)` (both
trailing) -- symmetric, but wrong for this purpose. The user corrected
this: `pickup`'s nights are for future stay dates almost by construction
(you can't "newly book" a night that's already passed in a way that
matters for pricing), so the more useful comparison is against how much
*forward* inventory exists to capture, not how much *trailing* calendar
existed. Final formula: `pickup(14_0) / nights_bookable(0_60)`.

## Forward-looking denominator resolves the tenure-truncation problem

The original trailing-window version (`nights_bookable(14_0)`) returned
`2.0` instead of `14.0` for a listing created 4 days before the dry run
(Vatican House) -- a brand-new listing simply hasn't had 14 days of
calendar history to be "bookable" in yet, so the trailing count shrinks
with tenure. Dividing a real `pickup` number by a tiny trailing denominator
could make a 4-day-old listing with one lucky early booking look like the
fastest mover in the portfolio.

Switching to `nights_bookable(0_60)` (forward-looking) sidesteps this
specific failure mode entirely -- a listing's *future* 60-day calendar
exists in full regardless of how recently it was created. This wasn't the
original motivation for the forward-looking choice (that was about
matching pickup's future-dated nights), but it's a confirmed side benefit.

**Residual caution, not yet built as a hard gate:** the numerator
(`pickup(14_0)`) can still be noisy for a very new listing on small sample
size alone -- one booking on a listing with almost no history is a bigger
swing than one booking on an established listing. This is a softer,
statistical-noise concern rather than the harder structural distortion the
denominator fix solved, and hasn't been implemented as an exclusion here.

## Confirmed in this account: the denominator can be a constant

Live dry run: `nights_bookable(0_60)` returned exactly `60.0` for **every
one of the 48 listings** in the real account -- meaning no listing had any
forward-blocked nights in the next 60 days at the time of the check. In
that situation, dividing by a portfolio-wide constant is a no-op for
ranking purposes: the Top 10 order was byte-for-byte identical whether
ranked by `pace` or by raw `pickup(14_0)` alone. This doesn't mean the
normalization is wrong -- a portfolio with real variation in forward-blocked
nights (owner holds, etc.) would see the ranking actually change -- it's
just worth knowing this dry run couldn't demonstrate that effect, so don't
be surprised if a given account's ranking looks identical to a raw-pickup
sort.

## Considered and rejected: `nights_available` as the denominator

Before settling on `nights_bookable(0_60)`, `nights_available(0_60)` (nights
neither blocked nor already booked -- i.e. what's *currently still open*,
as opposed to total addressable capacity) was tried as the denominator.
Live dry run showed why this is the wrong choice for this skill's purpose:
it systematically pushes **near-sold-out** listings to the top. DC - Thomas
Circle had only 17 nights available in the next 60 days; dividing its
pickup count by that small remaining-inventory number produced the
*highest* pace score in the portfolio (94.1%), ahead of Ceros (the far
larger, more broadly-selling listing that led every other version of this
ranking). A listing with almost nothing left to sell isn't a great fit for
a "where's there room to push further" list, and it also starves Step 2b's
opportunity-days scan of candidate days (DC - Thomas Circle would only
have 17 unbooked nights total to search across).

`nights_bookable` doesn't have this problem because it counts total
addressable capacity regardless of current booking status -- a listing
that sold out fast still shows its full capacity in the denominator, so
the ranking reflects capture rate against total opportunity rather than
being amplified by how little is left. The trade-off, per the caveat
above, is that `nights_bookable` won't vary at all in a portfolio with no
blocked nights -- but that's a much safer failure mode (ranking collapses
to raw pickup) than the alternative (ranking gets dominated by
low-remaining-inventory listings for the wrong reason).

## Opportunity-days: filter-then-rank, not rank-then-filter

First design pass: rank all 60 days in the neighborhood window by demand,
take the top 10, then check which of those happened to be unbooked for
this listing. Live dry run against Ceros (the #1 fast-seller) showed why
this is the wrong order: 6 of the top-10-demand days were already booked
(this listing had captured its own hottest nights), leaving only 4
apparent "opportunities" -- and Sep 19 (30.6% neighborhood adjusted
occupancy, $203 posted) never appeared in that list at all, because
several *already-booked* August days ranked higher overall and crowded it
out of the top 10.

**Corrected order:** filter to this listing's unbooked nights first (via
`GetPriceCalendar`, `is_available == true`), *then* rank only those by
neighborhood `adjusted_occupancy`. Re-run with the corrected order
surfaced Sep 19 immediately as a legitimate top-5 opportunity. Rank-then-
filter systematically undercounts opportunities whenever a listing has
already captured some of its own highest-demand nights -- which is
exactly the common case for a listing that made this Top 10 in the first
place (it's here *because* it's selling fast).

## ID mapping and pagination

Same conventions as `occupancy-pickup-priority-list` -- join bulk KPI
results to `GetListings` on `wheelhouse_id`, not `partner_listing_id`; page
until a page returns fewer rows than requested. Confirmed again in this
dry run against the same account (Ceros: `listing_id: 63721665` /
`partner_listing_id: "4816578"`, and per-listing endpoint calls for a
non-`hypothetical` channel need the channel-scoped ID, not `wheelhouse_id`
-- caught live when a first attempt at `GetNeighborhoodOccupancy` using
`wheelhouse_id` 404'd).
