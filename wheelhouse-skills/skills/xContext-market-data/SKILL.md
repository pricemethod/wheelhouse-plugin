---
name: xContext-market-data
description: Use whenever Wheelhouse market report or neighborhood data, or third-party market data (Key Data, AirDNA, others), is used to benchmark, compare, or derive anything — rate-vs-market checks, high-performer or percentile benchmarks, market ADR/revenue/occupancy comparisons, or setting minimum prices, base prices, or custom rates from market numbers. Explains the fee basis of market data (all-in, normalized to scraped OTA prices), converting between all-in and rental (rent-only) rates, and like-for-like pitfalls. Trigger on "vs market," "neighborhood price," "market ADR," "p75," "high performers," "AirDNA says," "Key Data shows," or any analysis that mixes listing and market numbers, even if fees are never mentioned. Read-only context; writes go through xContext-preferences or xContext-custom-rates.
---

# xContext-market-data

Market numbers and listing numbers are on different bases. Before comparing or deriving anything, know which basis each number is on and convert deliberately.

## The three bases

| Basis | What it includes | Where it comes from |
|---|---|---|
| **All-in (market)** | Nightly rate + fees + markups. Excludes taxes. Cannot be broken into line items. | Market report (`*_w_fees` metrics), neighborhood pricing (p25/p50/p75), Dynamic Set analytics |
| **Rental (rent-only)** | Nightly rate only | Listing `asking_rate`, `adr`, `revenue`, `revpar`; price recommendations; base price; min/max prices; custom rates. Everything the pricing engine reads or writes |
| **Listing all-in** | Listing rent + fees | *Estimated* (unbooked/asking prices only): `asking_rate_fees`, or rent × `fee_multiplier` from `fee_impact_calendar`; both come from the fee setting below. *Actual* (booked nights): `adr_fees`, `revenue_fees`, and reservations (`total_price − taxes`) |

**Why market data is all-in:** most OTAs now show scraped prices only as an all-in rate. Wheelhouse market and neighborhood data is normalized to that scraped basis. Fee and markup breakdowns exist only in direct (PMS) data, which is visible only to someone with direct access. So a user cannot get a fee breakdown of market data, and you should not imply one.

**Reservations are the only source of true fee values for a listing.** Rent = `nightly_subtotal`; rent + fees = `total_price − taxes`; guest-paid = `total_price`. ADR = the chosen revenue ÷ nights.

## Convert in the right direction

1. **Comparing a listing with the market:** convert the listing **up**. Multiply listing rent by the per-date `fee_multiplier` (or use `asking_rate_fees` for a window), then compare all-in to all-in.
2. **Analysis or deriving anything in rental terms:** convert the market **down** to a rental-equivalent. Divide the market all-in value by the listing's `fee_multiplier`. Use this for setting a minimum, base price, or custom rate, for judging what market ADR implies for nightly rate, and for any analysis framed in rent. **Never write a market number directly as a price.**

The down-conversion is an approximation. It assumes comparable listings carry a fee mix like this listing's, and the market's real fee share is unknowable. Say so when it matters, such as short-stay markets where amortized cleaning per night is large, or a listing whose fee structure is unusual.

**The fee setting.** The estimate comes from the listing's **Asking Rate (+Est. Fees)** setting (`fee_adjustments`): a **Total Fee Percentage** (`total_fee_percentage`) that the user enters, or that **Auto-update fee percentage** (`auto_update`) refreshes weekly. Auto-update uses the median fee share (fees ÷ rent) of recent bookings, and bookings with no fees count as 0%. Wheelhouse's estimate (`fallback=estimate`) is derived from reservation history: fees relative to revenue, length of stay, and fee structures. It is generally good, but it breaks down when a listing has little or no reservation history. The estimate is used only to add fees onto asking and recommended prices. Booked-night figures always use actual reservation fees.

**Always flag when the setting is not configured.** `fee_impact_calendar` reports `source`: `setting` (configured), `estimate` (Wheelhouse-derived), or `none` (multiplier 1.0). A real fee share of 0% is rare. A value of `none`, a 0% setting, or a `null` `fee_adjustments` most likely means the user hasn't set it up or turned it on. When you see one, tell the user, explain that market comparisons will be rent vs. all-in until it is set, and suggest setting a value or turning on auto-update. Also mention when an estimate rests on little reservation history. State which source every conversion used.

## Like-for-like checks

- **Asking vs. booked.** Neighborhood and market asking rates are list prices. ADR is what booked. Don't compare listing ADR with market asking rates, or the reverse.
- **Night population.** Listing `asking_rate` averages booked and available nights. Market `asking_rate_w_fees` covers available nights only, so match it with `asking_rate_available`.
- **Taxes.** Taxes are excluded from all market data. Only reservation `total_price` includes them.
- **Lead time.** Forward market occupancy is on-the-books. Compare at the same lead time, and never against last year's final results.
- **Aggregation.** Weight when rolling up days: sum of booked nights ÷ sum of calendar nights, not an average of daily percentages.
- **Currency.** Market and neighborhood data use the market's currency. Listing KPIs use the listing's currency. `GET /listings/kpis` ranks in market currency unless `currency` is passed.
- **Freshness.** Report `updated_at`.
- **MCP behavior (seen in testing).** A multi-value `metric[]` sent through the MCP has kept only the last value. Omit it to get all metrics, or call once per metric.

## Definitions

- **Neighborhood data:** same-bedroom-count listings in the listing's local cluster, daily by stay date. *Pricing:* p25/p50/p75 plus `listings_count`. *Occupancy:* occupancy, adjusted occupancy, and `expected_bookings` (model forecast) vs. `observed_bookings`.
- **Market report:** market-wide. `time_series` is daily; `distribution` is monthly histograms with percentiles. Filters: `performance` (low/average/high), `property_type`, and bedroom group. Bedroom groups differ by market, so call `/bedroom_groups` first.
- **High performers vs. 75th percentile:** `performance=high` is a performance tier. p75 is a price percentile. They are different benchmarks, so name the one you used.
- **Dynamic Sets:** a user-curated comp set. Set analytics require a paid set.

## Third-party data (Key Data, AirDNA, others)

These notes summarize each provider's public documentation as read in November 2026. They are not confirmed by Wheelhouse, and providers change definitions and rename metrics. Treat every point below as a caveat: before relying on one, check it against the linked docs (or the export's own metric definitions) and say which source you used.

- **First ask: direct or scraped?** Direct (PMS) data can separate rent from fees. Scraped data is all-in, like Wheelhouse market data. If an export's basis is unclear, ask the user for the metric definitions or export settings rather than assuming.
- **AirDNA (scraped, modeled), per its help center:**
  - Scraped daily from Airbnb, Vrbo, and Booking.com. Reservation data shared by hosts and managers is used only to validate the models.
  - Booked vs. blocked nights are inferred by a model, and listings on several OTAs are de-duplicated.
  - Default channel filter is Airbnb + Vrbo. Booking.com-only listings have data from March 2025 onward, so including them can distort year-over-year comparisons. Ask which channels the export used.
  - ADR and revenue include the cleaning fee spread over the stay; they exclude OTA service fees and taxes. AirDNA's "Price" metric excludes the cleaning fee.
  - Occupancy = reserved days ÷ active listing nights. Blocked nights are excluded, and a listing counts as active only with a reservation in the past 28 days. This is closer to Occupancy (Adjusted), and it reads higher because inactive listings drop out.
  - Data is mostly trailing (last twelve months, or last full month, refreshed monthly). Don't compare it with Wheelhouse forward on-the-books figures without matching periods. Results are in USD by default.
  - Likely closest to Wheelhouse's all-in basis, but it may differ on guest service fees (unconfirmed).
  - Docs: https://help.airdna.co/en/collections/5007594-understanding-airdna-data
- **Key Data (blended sources), per its support docs:**
  - Combines three sources: direct reservation data from PMS and reservation systems (verified, includes line items and forward bookings), Airbnb/Vrbo market data, and hotel data.
  - A Key Data figure can therefore be on either basis. Ask whether it is direct (participating operators only, often professionally managed) or OTA market data before comparing.
  - ADR = accommodation revenue only. ADR (Total) includes fees; it was formerly called TRevPOR, and several KPIs were reportedly renamed in December 2025, so older exports may use older names.
  - Paid Occupancy % = guest nights ÷ total nights, which appears to match Wheelhouse Occupancy. Adj. Paid Occupancy % appears to match Occupancy (Adjusted). Confirm against the export's definitions.
  - Revenue can be nightly or recognized.
  - Direct-data Key Data ADR compares with a listing's rental `adr`, not with Wheelhouse market ADR.
  - Docs: https://support.keydata.co/en/knowledge/kpi-definitions and https://www.keydata.co/how-it-works
- For term mapping, see `${CLAUDE_PLUGIN_ROOT}/references/lexicon-disambiguation.md`.

## Not yet confirmed ⚠️

These are open questions. Don't state an answer as fact; if one matters to a result, say it is unconfirmed (Wheelhouse support can answer it).

- Does Wheelhouse's scraped all-in include OTA guest service fees?
- Do reservations expose a cleaning-fee field, and is `security_deposit` inside `total_price`?
- Are neighborhood percentiles computed over available listings only?

## See also

xContext-preferences and xContext-custom-rates handle writes. The analysis skills that consume this context are MCP-market-overpricing-check, MCP-leaderboard-price-gap-priority-neighborhood, MCP-segment-vs-market-occupancy-graph, MCP-occ-heatmap-segment-market, MCP-market-event-demand-report, MCP-booking-window-diagnosis, MCP-mlos-strat-allbedroom and MCP-mlos-strat-bybedroom.
