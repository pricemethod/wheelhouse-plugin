---
name: wheelhouse-leaderboard
description: "Builds seven portfolio-wide leaderboards from the local Wheelhouse KPI cache written by wheelhouse-data-sync/wheelhouse-data-sync-api: Pacing (booking pace vs. last year), Expiring Inventory (near-term availability risk), Market Position (occupancy vs. neighborhood), Rate Floor (minimum-price-floor constraint), Recent YoY Performance (actual trailing RevPAR vs. last year), a composite Urgent Attention watchlist, and a Combined one-row-per-listing sheet joining all six. Runs as a local script against cached files only, no live API/MCP calls, so it costs almost no Claude usage regardless of portfolio size. Use whenever the user asks for a \"leaderboard,\" which listings are \"top performing,\" \"worst performing,\" \"falling behind,\" \"at risk,\" \"need attention,\" \"underperforming the market,\" \"expiring soon,\" wants any portfolio-wide ranked/triaged view of listings rather than a single-listing deep dive (for one listing, prefer stly-pacing or future-rate-overpricing instead), or a scheduled nightly digest."
---

# Wheelhouse Leaderboard

Builds seven portfolio-wide leaderboard CSVs from the local Wheelhouse KPI cache that `wheelhouse-data-sync` or `wheelhouse-data-sync-api` already wrote to disk:

1. **Pacing** -- booking pace vs. last year, extrapolated forward from recent pickup.
2. **Expiring Inventory** -- soon-arriving open nights at risk, ranked by a composite risk score.
3. **Market Position** -- listing occupancy vs. its own neighborhood, right now (no last-year comparison needed).
4. **Rate Floor** -- how often a listing's rate is pinned at its minimum-price floor.
5. **Recent YoY Performance** -- actual trailing RevPAR vs. the same period last year (backward-looking, unlike Pacing).
6. **Urgent Attention** -- a composite watchlist blending this skill's own pace calculation with Market Position, Rate Floor, and YoY Performance into one ranked "who needs a look" list.
7. **Combined** -- one row per listing joining all six leaderboards above, for a single at-a-glance scan or a scheduled digest message.

All the arithmetic runs in a plain Python script against files already on disk -- **no live Wheelhouse API or MCP calls happen when this skill runs**, so it costs almost no Claude usage regardless of portfolio size. Once the CSVs exist, read them back (they're small) and do the actual analysis/narrative on top of the pre-computed numbers, instead of reasoning listing-by-listing over raw KPI JSON.

**Not for a single listing.** If the user names one specific listing and wants its pacing or rate health checked, `stly-pacing` or `future-rate-overpricing` give a deeper, reservation-level answer for that one listing. This skill is for the portfolio-wide "which listings need my attention," "who's my best/worst performer," or "which properties should I be concerned about" view -- ranking listings against each other, not analyzing one in depth.

**Verified against a real account.** This skill was tested end-to-end against a real 47-listing multi-currency account (USD and AUD listings side by side, monthly history ranging from 3 to 20 months depending on how long each listing has existed). The script doesn't assume anything about portfolio size or shape -- it just iterates over however many entries are in `listings.json`, so it works the same way whether the cache holds 3 listings or 300, and listings with thin history simply show up with `No LY Data` / blank last-year columns instead of breaking the run.

## Prerequisites

This skill reads, and never writes to, the cache directory produced by `wheelhouse-data-sync` (MCP-orchestrated) or `wheelhouse-data-sync-api` (direct API key) -- specifically `listings.json` and `kpis/{id}_{channel}.json`. It does **not** need the reservations cache -- every leaderboard here is built from listings + KPI data alone.

**The path to that cache directory is different on every machine** (e.g. `C:\Users\<name>\Documents\Wheelclaude\Admin Account Data\wheelhouse_data`, or wherever the user pointed the sync skill's `--out`). Ask for it if it isn't already known from earlier in the session, rather than guessing a path. The script itself will check one level down for a `wheelhouse_data` subfolder if `listings.json` isn't directly at the given path -- the sync skills write into a `wheelhouse_data` folder alongside the API key file, so the folder a user thinks of as "the data folder" and the folder this script needs are sometimes one level apart, and the script now handles that automatically rather than erroring. If it still can't find `listings.json` after checking both places, say so plainly and ask the user to re-check the path or run a sync first, rather than silently producing an empty report.

If the KPI cache looks stale (check `index.json`'s `last_sync.kpis` / `last_sync.kpis_sync_date`) or is missing entirely, offer to run `wheelhouse-data-sync`/`wheelhouse-data-sync-api` first rather than building a leaderboard off week-old numbers without saying so.

## Running from a scheduled task

**If this skill is invoked from a scheduled task (a nightly digest, a cron-style automation) rather than an interactive chat, the data directory must be mounted into that run's sandbox before `build_leaderboard.py` can reach it -- on every single run, not just the first.** A scheduled task spins up a fresh, isolated sandbox each time with no memory of any folder mounted in a previous run, interactive or scheduled. A mount that worked for yesterday's run does not carry over to today's -- the mount itself doesn't persist between invocations, only the on-disk cache contents do, and only once the folder is actually reachable in that particular run.

Concretely: as the **first step** of any scheduled task that wraps this skill, call `request_cowork_directory` (load via `ToolSearch` first if it's deferred) with the exact data-directory path -- *before* running `build_leaderboard.py`, and before even a `--selftest` check. Do this unconditionally on every scheduled run. Don't skip it on the theory that "it was already connected yesterday" -- that history doesn't carry into today's sandbox.

Skipping this step doesn't fail loudly. `--data-dir` silently fails to resolve to a real path, which looks identical to the cache never having been synced or the folder never having been connected at all -- e.g. a `listings.json not found` error, or (if the parent path happens to still resolve to something) an empty or stale-looking leaderboard. That failure mode is indistinguishable from a genuine missing/stale-cache problem unless you already know to check for a mount issue first. So on any scheduled run, if the data directory can't be found, check whether `request_cowork_directory` was actually called this run before concluding the cache itself is missing or stale -- don't jump straight to telling the user to re-run the sync.

This mount requirement is specific to **scheduled/automated** invocations. In an interactive chat session the folder is already connected via the user's own session, so this step doesn't apply there.

## Running it

Write the script below to a working file (e.g. `build_leaderboard.py` in your working directory) each time you use this skill -- it's short and cheap to (re)materialize, and doing so means you're never dependent on some other file having survived between sessions.

**First time against a given data directory, or if anything looks off:**
```
python3 build_leaderboard.py --data-dir "<path to the cache folder>" --selftest
```
This just confirms `listings.json` and at least one `kpis/*.json` file are readable and prints the real field names found, without writing anything -- cheap sanity check before trusting a full run.

**Full run:**
```
python3 build_leaderboard.py --data-dir "<path to the cache folder>"
```
Writes all seven CSVs into `<data-dir>/leaderboards/` by default (override with `--out`). Read the script's printed summary and relay it in a sentence or two -- rather than just saying "done" -- naming how many listings were flagged on each leaderboard.

Useful flags (all optional, sensible defaults baked in -- see "Tuning the defaults" below):

| Leaderboard | Flags |
|---|---|
| Pacing | `--pacing-windows 30,60` (1 month, 2 months), `--pace-dead-band-pp 5.0` |
| Expiring Inventory | `--expiring-windows 7,14,30`, `--rate-window 30`, `--low-ly-occupancy-threshold 0.50`, `--risk-weights 0.5,0.3,0.2` (available_nights,pickup,rate_delta), `--risk-bands 66,33` |
| Market Position | `--market-windows 30,60,90`, `--market-dead-band-pct 0.15` |
| Rate Floor | `--floor-windows 30,60,90`, `--floor-high-pct 30.0`, `--floor-medium-pct 15.0` |
| Recent YoY Performance | `--yoy-windows 30,60,90`, `--yoy-dead-band-pct 10.0` |
| Urgent Attention | `--urgent-weights 0.35,0.20,0.10,0.35` (pace,market,floor,yoy -- pace and yoy tied highest), `--urgent-bands 66,33` |

Plus `--date YYYY-MM-DD` to override "today" (mainly for testing against old cache snapshots). All the `*-windows` flags expect smallest-first (e.g. `30,60,90`, not `90,60,30`) -- the smallest window in each list drives that leaderboard's flag and sort order, on the theory that near-term signals matter most.

## After running: read the CSVs, then analyze

Read the CSVs back (one row per listing each, small) and do the interpretation there -- sort/filter further, cross-reference across leaderboards (a listing showing up on Urgent Attention *and* Expiring Inventory is a bigger priority than one showing up on just one), and write the takeaway in plain language. Don't just dump a CSV as a table with no commentary, and don't recompute any of these numbers by hand from raw KPI files -- the whole point of running the script is that the arithmetic is already done and verified.

Before presenting any last-year rate or RevPAR comparison as fact, glance at whether the LY figure looks like an obvious outlier (a demo/sample listing with one aberrant high-priced night can blow out a whole month's blended average). The blending math is correct given the inputs -- but a single bad month in the underlying KPI data can still produce a technically-correct-but-misleading delta, so sanity-check anything that looks extreme (e.g. a multi-hundred-percent delta, or a market ratio in the double digits) before calling it a finding.

### 1. Pacing leaderboard columns

| Column | Meaning |
|---|---|
| `pickup_nights_7d` | Nights newly booked (added to the books) across the whole listing in the trailing 7 days -- the pace signal everything else extrapolates from. |
| `daily_pickup_rate` | `pickup_nights_7d / 7`. |
| `current_occ_{W}d_pct` | Occupancy already on the books today for the next W days. |
| `projected_occ_{W}d_pct` | `current_occ` plus `daily_pickup_rate * W` additional nights, capped at 100%. A deliberately simple extrapolation -- assumes the last week's booking velocity holds steady for the entire W-day window and that all of that new pickup lands within it, not a true lead-time/pickup-curve model. Say so if a user asks how "real" the projection is. |
| `ly_occ_{W}d_pct` | Last year's **actual, final** occupancy for the same calendar days one year ago, blended across whichever calendar months that span. Blank if less than half the window's days have real last-year data. |
| `pace_delta_{W}d_pp` | `projected_occ - ly_occ`, in percentage points. The number to sort/rank on. |
| `pace_flag` | `Behind LY` / `On Pace` / `Ahead of LY` (from the smallest window's delta and `--pace-dead-band-pp`), or `No LY Data`. |

Default sort: ascending by the smallest window's delta -- listings falling furthest behind last year float to the top; `No LY Data` sinks to the bottom.

**How far out are we forecasting?** Default windows are 30 and 60 days (1 month, 2 months) -- both driven by the same trailing-7-day daily pickup rate extrapolated forward. A 90-day window was deliberately dropped from the default: the further out the extrapolation reaches, the more the "pace holds steady" assumption breaks down, and the more likely that new pickup during the run-up is actually for stays beyond the window rather than within it. `--pacing-windows` still accepts any comma-separated list if a longer horizon is wanted for a specific analysis.

### 2. Expiring Inventory leaderboard columns

| Column | Meaning |
|---|---|
| `available_nights_{W}d` | Open (bookable, unbooked) nights in the next W days. |
| `pickup_nights_7d` | Same trailing-7-day pickup as Pacing -- low pickup alongside high near-term availability is the core "nobody is booking this soon" signal. |
| `last_booked_days_next_7d` / `last_booked_days_{W}d` | Simply how many days have passed since the last reservation was booked, scoped to that forward window. **Confirmed against a real account:** Wheelhouse represents "no booking to measure from" as either a real `null` or a sentinel `-1` depending on the window -- both are treated as missing here, never as a literal negative day count. |
| `asking_rate_{rate-window}d` | Current posted average rate for the next `--rate-window` days. |
| `ly_adr_{rate-window}d` | Last year's actual ADR for the same calendar window (blended). There's no monthly *asking rate* in the cache, only actual ADR, so this is deliberately rate-vs-ADR, not rate-vs-rate. |
| `rate_delta_pct` | `(asking_rate - ly_adr) / ly_adr`, as a percent. |
| `ly_occ_{rate-window}d_pct` | Last year's blended occupancy for that window -- context for whether soft demand, not price, is the real story. |
| `low_ly_demand` | `True` if `ly_occ` was below `--low-ly-occupancy-threshold`, **regardless of `rate_delta_pct`** -- a listing priced right in line with last year can still be worth flagging if last year's occupancy for that window was already weak. |
| `risk_score` | 0-100 composite, weighted by priority: **Available Nights** (dominant driver -- a listing with a lot of unbooked near-term inventory is nearly always worth a look), **Pickup Nights** (moderates it -- the same availability is far less urgent if the listing is already picking up fast, more urgent if pickup is low-to-moderate; this is a real but lower weight, not a hard "pickup is really high" override), and **Rate Delta** (amplifies it -- an available, slow-moving listing priced above where it transacted last year is the highest-priority combination). Each input is converted to a percentile rank *within this portfolio* and blended via `--risk-weights` (default `0.5,0.3,0.2` for available_nights,pickup,rate_delta). `last_booked_days` is still shown as an informational column but intentionally is not part of the score. |
| `rate_delta_assumed_high` | `True` when the current asking rate is known but there's no reliable last-year ADR to benchmark it against. In that case the rate-risk component is **not** excluded/renormalized away -- it's assumed to be at maximum risk instead. Rationale: a listing that's available and not booking, with no last-year baseline to say otherwise, is more likely explained by "priced too high" than by "we just lack data" -- so it's treated as a real opportunity signal, not a neutral unknown. Only a truly missing asking rate (not just a missing LY comparison) still gets excluded from the score entirely. |
| `missing_signals` | Which of the three risk inputs (`available_nights`, `pickup`, `rate_delta`) were **entirely** unavailable -- e.g. `rate_delta` only appears here when the asking rate itself is missing, not merely when the last-year ADR is missing (that case is handled by `rate_delta_assumed_high` above and still counts toward the score). |
| `risk_band` | `High` / `Medium` / `Low` from `risk_score` and `--risk-bands`. |

Default sort: descending by `risk_score`.

### 3. Market Position leaderboard columns

Uses Wheelhouse's own neighborhood-comparison metrics -- a live snapshot, not a last-year comparison, so it needs no blending and has no "insufficient history" edge case the way the LY-based leaderboards do. **Confirmed populated for 100% of listings on a real 47-listing account.** This is the leaderboard to reach for when a listing looks like it's underperforming, but you want to know whether that's a listing-specific problem or the whole neighborhood is just soft right now -- Pacing (vs. the listing's *own* last year) can't tell those apart on its own, this can.

| Column | Meaning |
|---|---|
| `occ_adjusted_{W}d_pct` | The listing's own occupancy (adjusted for blocked nights) over the next W days. |
| `neighborhood_occ_adjusted_{W}d_pct` | The neighborhood's occupancy over the same window. |
| `market_ratio_{W}d` | Listing occupancy ÷ neighborhood occupancy. 1.0 = exactly matching the market; below 1.0 = under-booking relative to the neighborhood; above 1.0 = out-booking it. |
| `market_gap_{W}d_pp` | The same comparison as a percentage-point difference instead of a ratio -- useful when the neighborhood occupancy itself is very low, where a ratio can look dramatic (see caveat below) but the pp gap stays readable. |
| `market_flag` | `Underperforming Market` / `On Par With Market` / `Outperforming Market` (from the smallest window's ratio and `--market-dead-band-pct`, default ±15%), or `No Market Data`. |

Default sort: ascending by the smallest window's ratio -- worst market-relative performers float to the top.

**Caveat confirmed on a real account:** when neighborhood occupancy is very low, the ratio can swing to extreme values (a real account showed ratios from 0 to over 10) purely because the denominator is tiny -- this isn't a bug, but it means a ratio in the double digits is a "small-sample" flag as much as a "great performer" flag. Check `market_gap_{W}d_pp` alongside the ratio before calling a listing a huge outperformer on ratio alone.

### 4. Rate Floor leaderboard columns

Flags listings whose rate is frequently pinned at the minimum-price floor -- often a sign the floor is set too high for current demand and is suppressing bookings the pricing engine would otherwise take at a lower rate.

| Column | Meaning |
|---|---|
| `days_at_floor_{W}d` | Raw count of days in the next W days where Asking Rate = Minimum Price. |
| `pct_at_floor_{W}d` | The same, as a percent of the window (`days_at_floor / W * 100`) -- normalized so windows of different lengths are comparable. |
| `floor_flag` | `High` / `Medium` / `Low` from the smallest window's `pct_at_floor` and `--floor-high-pct` / `--floor-medium-pct`, or `No Minimum Price Rule`. |

Default sort: descending by `pct_at_floor` for listings that have a rule; listings with no rule sort to the bottom (not because they're "safe," but because this signal doesn't apply to them at all).

**Confirmed on a real account: absence is not the same as zero.** About a quarter of a real 47-listing portfolio had this field completely missing (no minimum-price rule configured), while most of the rest had a genuine `0` (a rule exists, it's just never been hit) -- these are two different, non-comparable situations, and the leaderboard keeps them distinct rather than treating "no rule" as "0 occurrences of hitting a floor that doesn't exist."

### 5. Recent YoY Performance leaderboard columns

Deliberately backward-looking and un-extrapolated, to complement the Pacing leaderboard's forward-looking projection. Uses the rolling KPI's own trailing windows (`revpar["{W}_0"]`, already computed, no extrapolation) against the same calendar window one year ago (blended from monthly history the same way as the other leaderboards).

| Column | Meaning |
|---|---|
| `revpar_last_{W}d` | Actual RevPAR over the trailing W days, settled/actual data only. |
| `ly_revpar_{W}d` | Actual RevPAR for the same calendar window one year ago (blended across months). |
| `yoy_delta_{W}d_pct` | Percent change, `(recent - ly) / ly`. |
| `yoy_flag` | `Declined YoY` / `Flat YoY` / `Improved YoY` (from the smallest window's delta and `--yoy-dead-band-pct`), or `No LY Data`. |

Default sort: ascending by the smallest window's delta -- the steepest actual declines float to the top.

Revenue basis is rent-only (`revpar`, not the fee-inclusive `revpar_fees`) for consistency with the rest of this skill's occupancy/ADR figures, which are also rent-basis by default.

### 6. Urgent Attention leaderboard (composite watchlist)

Built by joining the four leaderboards above on listing, not by recomputing anything -- the values shown here always match what's in each individual leaderboard, so there's one consistent story across every CSV this skill produces. **Uses this project's own pace projection (from the Pacing leaderboard), not Wheelhouse's `revenue_score`** -- deliberately, so the composite is built entirely from signals this skill computes and can explain, rather than an opaque third-party score.

| Column | Meaning |
|---|---|
| `pace_delta_pp` | The Pacing leaderboard's primary-window delta for this listing. |
| `market_ratio` | The Market Position leaderboard's primary-window ratio. |
| `pct_at_floor` | The Rate Floor leaderboard's primary-window percent. |
| `yoy_revpar_delta_pct` | The Recent YoY Performance leaderboard's primary-window delta. |
| `urgent_score` | 0-100 composite: each of the four raw values above is converted to a percentile-rank "urgency" (worse pace/market/YoY, or higher floor-constraint, all push the percentile toward 100) and blended via `--urgent-weights` (default `0.35,0.20,0.10,0.35` for pace,market,floor,yoy). Pace and YoY RevPAR are weighted equally highest -- one forward-looking, one backward-looking, both listing-specific trend signals -- Market Position is next (useful, but a low ratio can also just mean a soft neighborhood), and Rate Floor is weighted lowest (a narrower, more mechanical signal). Listings missing a given signal (e.g. no minimum-price rule, or `No LY Data`) get that component dropped and the remaining weights renormalized, same missing-tolerant pattern as the Expiring Inventory risk score. |
| `missing_signals` | Which of `pace` / `market_position` / `rate_floor` / `yoy_revpar` were unavailable for this listing. |
| `urgent_band` | `High` / `Medium` / `Low` from `urgent_score` and `--urgent-bands`. |

Default sort: descending by `urgent_score`. This is the single leaderboard to reach for when the user asks "which properties should I be concerned about" without specifying which signal they mean -- lead with this, then point to whichever of the four underlying leaderboards explains *why* a listing landed where it did.

### 7. Combined leaderboard columns

One row per listing, joining the six leaderboards above on `(listing_id, channel)` -- nothing recomputed, every value here matches its source leaderboard exactly. This is the sheet to reach for when a user wants a single scan across the whole portfolio (or a scheduled digest message) rather than reading six separate CSVs.

| Column | Meaning |
|---|---|
| `pace_delta_pp` / `pace_flag` | From the Pacing leaderboard's primary window. |
| `expiring_risk_score` / `expiring_risk_band` | From the Expiring Inventory leaderboard. |
| `market_ratio` / `market_flag` | From the Market Position leaderboard's primary window. |
| `pct_at_floor` / `floor_flag` | From the Rate Floor leaderboard's primary window. |
| `yoy_revpar_delta_pct` / `yoy_flag` | From the Recent YoY Performance leaderboard's primary window. |
| `urgent_score` / `urgent_band` | From the Urgent Attention leaderboard. |

Default sort: descending by `urgent_score`, same as Urgent Attention itself.

**When presenting this as a chat message (e.g. a scheduled digest):** don't just dump the raw CSV. Render it as a readable table (title, currency, then the six flag/score pairs), and call out the handful of listings in the `High` urgent band by name before the table -- that's the actionable summary; the full table is the supporting detail.

## Tuning the defaults

Every threshold above is a starting point calibrated to be reasonable, not a fixed constant -- the way any dead-band or confidence threshold works elsewhere in this project. If a user says a leaderboard is flagging too much or too little, or that a particular signal should count for more in Urgent Attention, adjust the relevant flag rather than re-deriving the whole approach -- and mention in your reply which default you changed and why.

## Edge cases

- **Listing has no cached KPI file yet**: skipped from every leaderboard, counted in the run summary rather than silently dropped with no trace.
- **New listing, no monthly history**: Pacing and Recent YoY Performance show `No LY Data`; Market Position and Rate Floor still compute fully since neither needs last-year data.
- **`last_booked_days` sentinel values**: confirmed on a real account that this field comes back as either `null` or `-1` when there's no qualifying booking to measure from -- both treated as missing, never as a literal negative day count.
- **No minimum-price rule configured**: `Rate Floor` shows `No Minimum Price Rule`, distinct from a real `0` (a rule exists and is simply never hit) -- confirmed both cases occur on a real account, roughly a quarter of listings had no rule at all.
- **Extreme Market Position ratios**: a very low neighborhood occupancy can push `market_ratio` into double digits purely from a small denominator -- check the pp-gap column alongside it before treating an extreme ratio as a straightforward "great performer" signal.
- **Portfolio of 1-2 listings**: every percentile-rank-based score (Expiring Inventory's `risk_score`, Urgent Attention's `urgent_score`) is less meaningful with a tiny population -- say so if asked to interpret a very small portfolio's scores, since the ranking is relative, not absolute.
- **Varying portfolio size**: the script places no assumptions on how many listings exist -- it reads whatever `listings.json` contains, so it works unchanged whether the account has a handful of listings or hundreds.
- **Currency**: every CSV carries each listing's own `currency` field; never assume USD when reporting rate/RevPAR figures, especially for a multi-currency portfolio (confirmed: a real account mixed USD and AUD with no issue, since nothing here sums rate figures across listings -- every composite score is unit-less/percentage-based for exactly this reason).

## Script

```python
#!/usr/bin/env python3
"""
Builds seven leaderboard CSVs from the local Wheelhouse KPI cache written by
wheelhouse-data-sync / wheelhouse-data-sync-api. No API/MCP calls -- this is
pure arithmetic over files already on disk, so it costs no Claude usage
beyond reading the small output CSVs back.

Reads (all read-only, never written to):
  <data-dir>/listings.json
  <data-dir>/kpis/{id}_{channel}.json

Writes (all under <out>, default <data-dir>/leaderboards):
  leaderboard_pacing.csv
  leaderboard_expiring_inventory.csv
  leaderboard_market_position.csv
  leaderboard_rate_floor.csv
  leaderboard_yoy_performance.csv
  leaderboard_urgent_attention.csv
  leaderboard_combined.csv (one row per listing, joining all six above)

Usage:
  python3 build_leaderboard.py --data-dir /path/to/wheelhouse_data --selftest
  python3 build_leaderboard.py --data-dir /path/to/wheelhouse_data --out /path/to/wheelhouse_data/leaderboards

See this skill's SKILL.md for what every field means and why each default
threshold was chosen -- this docstring only covers how to run it.
"""
import argparse
import csv
import datetime
import json
import os
import sys


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def parse_date(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


def one_year_before(d):
    """Same calendar day one year earlier. Feb 29 -> Feb 28 (no Feb 29 last year)."""
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def daterange(start, days):
    for i in range(days):
        yield start + datetime.timedelta(days=i)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def blended_ly_value(monthly_by_key, field, ly_start, window_days):
    """Weighted average of `field` across the monthly KPI rows overlapped by
    the window [ly_start, ly_start + window_days), weight = number of days
    of that window falling in each calendar month. Returns
    (blended_value_or_None, coverage_fraction) -- coverage_fraction is the
    share of days in the window for which a monthly row with a non-null
    value for `field` was actually found. A low coverage fraction should
    suppress the comparison rather than silently average over fewer days
    than the window implies (see each caller's 0.5 coverage guard)."""
    total_weight = 0.0
    weighted_sum = 0.0
    covered_days = 0
    for day in daterange(ly_start, window_days):
        month_key = day.strftime("%Y-%m")
        row = monthly_by_key.get(month_key)
        total_weight += 1
        if row is not None and row.get(field) is not None:
            weighted_sum += row[field]
            covered_days += 1
    coverage = covered_days / total_weight if total_weight else 0.0
    if covered_days == 0:
        return None, coverage
    # Average using only the covered days as the denominator -- each covered
    # day contributes its month's value once, so this is exactly the
    # day-weighted mean over the days we actually have data for.
    return weighted_sum / covered_days, coverage


def pct(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return numerator / denominator


def percentile_rank(values, value):
    """Fraction of `values` that are <= value, as 0-100. None-safe: None
    values in the input population are ignored; if `value` itself is None,
    returns None (caller should substitute a neutral score)."""
    pool = [v for v in values if v is not None]
    if value is None or not pool:
        return None
    rank = sum(1 for v in pool if v <= value)
    return 100.0 * rank / len(pool)


def get_metric(rolling, name, key):
    return (rolling.get(name) or {}).get(key)


def get_last_booked_days(rolling, key):
    """last_booked_days is just 'days since the most recent reservation was
    booked' for the reservations relevant to this window -- but Wheelhouse's
    API represents 'no booking to measure from' two different ways depending
    on the window: sometimes a real JSON null, sometimes a sentinel -1
    (confirmed against a real 47-listing account -- -1 shows up on roughly a
    fifth of listings, on whichever windows have no qualifying booking, and
    is never a real day-count). Both mean the same thing: no data for this
    window, not '1 day in the future.' Treat both as missing."""
    value = get_metric(rolling, "last_booked_days", key)
    if value is None or value < 0:
        return None
    return value


def primary_window(windows):
    """The windows lists are expected smallest-first (e.g. [30, 60, 90]) --
    the smallest window is treated as the 'primary' one that drives each
    leaderboard's flag and sort order, on the theory that near-term signals
    matter most for a revenue manager's attention. min() rather than
    windows[0] so this is correct even if a caller passes them out of order."""
    return min(windows)


# ---------------------------------------------------------------------------
# Loading the cache
# ---------------------------------------------------------------------------

def load_portfolio(data_dir, verbose=False):
    listings_path = os.path.join(data_dir, "listings.json")
    if not os.path.exists(listings_path):
        # The sync skills write into a wheelhouse_data/ subfolder alongside
        # the API key file -- if the user pointed us at the parent folder,
        # check one level down before giving up.
        nested = os.path.join(data_dir, "wheelhouse_data", "listings.json")
        if os.path.exists(nested):
            data_dir = os.path.join(data_dir, "wheelhouse_data")
            listings_path = nested
        else:
            sys.exit(
                f"{listings_path} not found (also checked {nested}). This script reads "
                f"the cache written by wheelhouse-data-sync / wheelhouse-data-sync-api -- "
                f"run one of those skills against this --data-dir first."
            )
    listings = load_json(listings_path)

    portfolio = []
    skipped = []
    for key, listing in listings.items():
        kpi_path = os.path.join(data_dir, "kpis", f"{key}.json")
        if not os.path.exists(kpi_path):
            skipped.append({"listing": key, "reason": "no KPI file cached yet"})
            continue
        try:
            kpi = load_json(kpi_path)
        except (json.JSONDecodeError, OSError) as e:
            skipped.append({"listing": key, "reason": f"unreadable KPI file: {e}"})
            continue

        rolling = kpi.get("rolling") or {}
        monthly_rows = kpi.get("monthly") or []
        monthly_by_key = {r["month"][:7]: r for r in monthly_rows if r.get("month")}

        portfolio.append(
            {
                "key": key,
                "listing_id": listing.get("id"),
                "channel": listing.get("channel"),
                "title": listing.get("title") or listing.get("nickname") or key,
                "currency": rolling.get("currency") or listing.get("currency"),
                "rolling": rolling,
                "monthly_by_key": monthly_by_key,
                "kpi_sync_date": kpi.get("sync_date"),
            }
        )
        if verbose:
            print(f"  loaded {key}")
    return portfolio, skipped, data_dir


# ---------------------------------------------------------------------------
# 1. Pacing leaderboard (forward-looking: projected occupancy vs LY actual)
# ---------------------------------------------------------------------------
# How far out are we extrapolating? For each requested window W (default 30
# and 60 days -- 1 month and 2 months), the daily pickup rate from the
# trailing 7 days is multiplied by W and added on top of nights already on
# the books for that same W-day window, then capped at 100% occupancy. So
# "60-day pace" assumes the last week's booking velocity holds steady for
# the *entire* 60 days and that all of that new pickup lands within the
# window -- a deliberately simple, single-rate extrapolation, not a
# lead-time/pickup-curve model. Accuracy degrades the larger W gets (more
# time for the assumption "pace holds steady" to break down, and more
# chance new pickup is actually for stays beyond the window), which is why
# the default stops at 60 days rather than reaching further out to 90.

def compute_pacing_row(listing, today, ly_start, windows, dead_band_pp):
    rolling = listing["rolling"]
    monthly_by_key = listing["monthly_by_key"]
    pickup_7 = get_metric(rolling, "pickup", "7_0")
    daily_pickup_rate = pickup_7 / 7 if pickup_7 is not None else None

    row = {
        "listing_id": listing["listing_id"],
        "channel": listing["channel"],
        "title": listing["title"],
        "currency": listing["currency"],
        "pickup_nights_7d": pickup_7,
        "daily_pickup_rate": round(daily_pickup_rate, 3) if daily_pickup_rate is not None else None,
    }

    primary_delta = None
    any_ly_data = False
    for w in windows:
        key = f"0_{w}"
        nights_calendar = get_metric(rolling, "nights_calendar", key)
        nights_booked = get_metric(rolling, "nights_booked", key)
        current_occ = pct(nights_booked, nights_calendar)

        projected_occ = current_occ
        if daily_pickup_rate is not None and nights_calendar and nights_booked is not None:
            projected_total = min(nights_booked + daily_pickup_rate * w, nights_calendar)
            projected_occ = projected_total / nights_calendar

        ly_occ, coverage = blended_ly_value(monthly_by_key, "occupancy", ly_start, w)
        if coverage < 0.5:
            ly_occ = None

        delta_pp = None
        if projected_occ is not None and ly_occ is not None:
            delta_pp = round((projected_occ - ly_occ) * 100, 1)
            any_ly_data = True

        row[f"current_occ_{w}d_pct"] = round(current_occ * 100, 1) if current_occ is not None else None
        row[f"projected_occ_{w}d_pct"] = round(projected_occ * 100, 1) if projected_occ is not None else None
        row[f"ly_occ_{w}d_pct"] = round(ly_occ * 100, 1) if ly_occ is not None else None
        row[f"pace_delta_{w}d_pp"] = delta_pp
        if w == primary_window(windows):
            primary_delta = delta_pp

    if not any_ly_data:
        row["pace_flag"] = "No LY Data"
        row["sort_key"] = 999
    elif primary_delta is not None and primary_delta <= -dead_band_pp:
        row["pace_flag"] = "Behind LY"
        row["sort_key"] = primary_delta
    elif primary_delta is not None and primary_delta >= dead_band_pp:
        row["pace_flag"] = "Ahead of LY"
        row["sort_key"] = primary_delta
    else:
        row["pace_flag"] = "On Pace"
        row["sort_key"] = primary_delta if primary_delta is not None else 0
    return row


def build_pacing_leaderboard(portfolio, today, windows, dead_band_pp):
    ly_start = one_year_before(today)
    rows = [compute_pacing_row(l, today, ly_start, windows, dead_band_pp) for l in portfolio]
    rows.sort(key=lambda r: r["sort_key"])
    for r in rows:
        del r["sort_key"]
    return rows


# ---------------------------------------------------------------------------
# 2. Expiring inventory leaderboard (near-term availability + rate risk)
# ---------------------------------------------------------------------------
# risk_score priority order, by design: (1) Available Nights is the dominant
# driver -- a listing with a lot of unbooked near-term inventory is nearly
# always worth a look. (2) Pickup Nights moderates that: the same available-
# nights count is far less urgent if the listing is already picking up
# fast, and more urgent if pickup is low-to-moderate. This is why pickup
# enters the blend as (100 - pickup_percentile) at a real but lower weight
# than availability -- high pickup pulls the blended score down without
# needing a separate hard-coded "pickup is really high" override. (3) Rate
# Delta -- whether this year's asking rate is priced above last year's ADR
# for the same window -- amplifies the other two: an available, slow-moving
# listing that's also priced above where it transacted last year is the
# highest-priority combination. last_booked_days is still computed and
# shown as an informational column, but is intentionally not part of the
# score itself (see SKILL.md for why).
#
# Missing last-year ADR is treated as a risk signal, not a neutral unknown:
# if we know the current asking rate but have no last-year ADR to compare
# it against, and the listing is still showing up here (near-term available,
# not booking), the working assumption is that price is the more likely
# explanation than "we simply lack data" -- so this case gets the maximum
# rate-risk percentile rather than being excluded and renormalized away.
# True unknowns (no asking rate at all) are still excluded, not assumed.

def compute_expiring_raw(listing, ly_start, windows, rate_window):
    rolling = listing["rolling"]
    monthly_by_key = listing["monthly_by_key"]

    pickup_7 = get_metric(rolling, "pickup", "7_0")
    last_booked_7 = get_last_booked_days(rolling, "0_7")

    rate_key = f"0_{rate_window}"
    asking_rate = get_metric(rolling, "asking_rate", rate_key)
    ly_adr, adr_coverage = blended_ly_value(monthly_by_key, "adr", ly_start, rate_window)
    if adr_coverage < 0.5:
        ly_adr = None
    ly_occ, occ_coverage = blended_ly_value(monthly_by_key, "occupancy", ly_start, rate_window)
    if occ_coverage < 0.5:
        ly_occ = None

    rate_delta_pct = None
    if asking_rate is not None and ly_adr:
        rate_delta_pct = round((asking_rate - ly_adr) / ly_adr * 100, 1)

    raw = {
        "listing_id": listing["listing_id"],
        "channel": listing["channel"],
        "title": listing["title"],
        "currency": listing["currency"],
        "pickup_nights_7d": pickup_7,
        "last_booked_days_next_7d": last_booked_7,
        f"asking_rate_{rate_window}d": round(asking_rate, 2) if asking_rate is not None else None,
        f"ly_adr_{rate_window}d": round(ly_adr, 2) if ly_adr is not None else None,
        "rate_delta_pct": rate_delta_pct,
        f"ly_occ_{rate_window}d_pct": round(ly_occ * 100, 1) if ly_occ is not None else None,
        "low_ly_demand": None,
        "_ly_occ_raw": ly_occ,
    }
    for w in windows:
        raw[f"available_nights_{w}d"] = get_metric(rolling, "nights_available", f"0_{w}")
        raw[f"last_booked_days_{w}d"] = get_last_booked_days(rolling, f"0_{w}")
    raw["_available_7d"] = get_metric(rolling, "nights_available", "0_7")
    return raw


def build_expiring_leaderboard(portfolio, today, windows, rate_window, low_ly_threshold,
                                weights, risk_bands):
    ly_start = one_year_before(today)
    raws = [compute_expiring_raw(l, ly_start, windows, rate_window) for l in portfolio]

    for r in raws:
        r["low_ly_demand"] = (
            r["_ly_occ_raw"] is not None and r["_ly_occ_raw"] < low_ly_threshold
        )

    available_pool = [r["_available_7d"] for r in raws]
    pickup_pool = [r["pickup_nights_7d"] for r in raws]
    rate_delta_pool = [r["rate_delta_pct"] for r in raws]
    w_avail, w_pickup, w_rate = weights

    for r in raws:
        pct_avail = percentile_rank(available_pool, r["_available_7d"])
        pct_low_pickup = percentile_rank(pickup_pool, r["pickup_nights_7d"])
        # Higher rate_delta_pct = this year's asking rate is further above
        # last year's ADR for the same window = more risk (priced above
        # where it actually transacted last year, while sitting available).
        rate_delta_val = r["rate_delta_pct"]
        asking_rate_val = r.get(f"asking_rate_{rate_window}d")
        rate_delta_assumed_high = False
        if rate_delta_val is not None:
            pct_rate = percentile_rank(rate_delta_pool, rate_delta_val)
        elif asking_rate_val is not None:
            # We know the current asking rate but have no last-year ADR to
            # benchmark it against. Rather than treat this as a neutral
            # unknown, assume the listing is priced too high -- it's still
            # available and not booking, so "no baseline" is read as a
            # signal worth acting on (an opportunity to test a lower rate),
            # not excluded from the score.
            pct_rate = 100.0
            rate_delta_assumed_high = True
        else:
            pct_rate = None
        r["rate_delta_assumed_high"] = rate_delta_assumed_high

        components = []
        if pct_avail is not None:
            components.append((w_avail, pct_avail))
        if pct_low_pickup is not None:
            components.append((w_pickup, 100 - pct_low_pickup))
        if pct_rate is not None:
            components.append((w_rate, pct_rate))

        if components:
            weight_sum = sum(w for w, _ in components)
            r["risk_score"] = round(sum(w * v for w, v in components) / weight_sum, 1)
        else:
            r["risk_score"] = None

        missing = []
        if pct_avail is None:
            missing.append("available_nights")
        if pct_low_pickup is None:
            missing.append("pickup")
        if pct_rate is None:
            missing.append("rate_delta")
        r["missing_signals"] = ";".join(missing) if missing else ""

        high, medium = risk_bands
        if r["risk_score"] is None:
            r["risk_band"] = "Unknown"
        elif r["risk_score"] >= high:
            r["risk_band"] = "High"
        elif r["risk_score"] >= medium:
            r["risk_band"] = "Medium"
        else:
            r["risk_band"] = "Low"

        del r["_ly_occ_raw"]
        del r["_available_7d"]

    raws.sort(key=lambda r: (r["risk_score"] is None, -(r["risk_score"] or 0)))
    return raws


# ---------------------------------------------------------------------------
# 3. Market Position leaderboard (listing occupancy vs. its own neighborhood)
# ---------------------------------------------------------------------------
# Isolates listing-specific under/over-performance from market-wide swings --
# a listing can be "behind last year" purely because the whole neighborhood
# is soft this year (see the Pacing leaderboard's caveat about that). This
# leaderboard uses Wheelhouse's own occupancy_neighborhood_adjusted_ratio
# (confirmed populated for 100% of a real 47-listing test account), so it
# needs no last-year blending at all -- it's a live snapshot comparison.

def compute_market_position_row(listing, windows):
    rolling = listing["rolling"]
    row = {
        "listing_id": listing["listing_id"],
        "channel": listing["channel"],
        "title": listing["title"],
        "currency": listing["currency"],
    }
    primary_ratio = None
    for w in windows:
        key = f"0_{w}"
        occ_adj = get_metric(rolling, "occupancy_adjusted", key)
        nbhd_occ_adj = get_metric(rolling, "occupancy_neighborhood_adjusted", key)
        ratio = get_metric(rolling, "occupancy_neighborhood_adjusted_ratio", key)
        gap_pp = get_metric(rolling, "occupancy_neighborhood_adjusted_pp", key)

        row[f"occ_adjusted_{w}d_pct"] = round(occ_adj * 100, 1) if occ_adj is not None else None
        row[f"neighborhood_occ_adjusted_{w}d_pct"] = round(nbhd_occ_adj * 100, 1) if nbhd_occ_adj is not None else None
        row[f"market_ratio_{w}d"] = round(ratio, 2) if ratio is not None else None
        row[f"market_gap_{w}d_pp"] = round(gap_pp, 1) if gap_pp is not None else None
        if w == primary_window(windows):
            primary_ratio = ratio

    row["_primary_ratio"] = primary_ratio
    return row


def build_market_position_leaderboard(portfolio, windows, dead_band_pct):
    rows = [compute_market_position_row(l, windows) for l in portfolio]
    for r in rows:
        ratio = r["_primary_ratio"]
        if ratio is None:
            r["market_flag"] = "No Market Data"
        elif ratio <= 1 - dead_band_pct:
            r["market_flag"] = "Underperforming Market"
        elif ratio >= 1 + dead_band_pct:
            r["market_flag"] = "Outperforming Market"
        else:
            r["market_flag"] = "On Par With Market"
    rows.sort(key=lambda r: (r["_primary_ratio"] is None, r["_primary_ratio"] if r["_primary_ratio"] is not None else 0))
    for r in rows:
        del r["_primary_ratio"]
    return rows


# ---------------------------------------------------------------------------
# 4. Rate-Floor Constraint leaderboard (min_price_occurrence)
# ---------------------------------------------------------------------------
# Flags listings whose posted rate is frequently pinned at the minimum-price
# floor -- often a sign the floor is set too high for current demand and is
# suppressing bookings the pricing engine would otherwise take at a lower
# rate. Confirmed against a real account: this field is genuinely absent
# (not zero) for listings with no minimum-price rule configured at all --
# that's a different, non-comparable case from a listing that *has* a rule
# and simply never hits it (a real, meaningful 0), so the two are kept
# distinct rather than treating "no rule" as "0 occurrences."

def compute_floor_row(listing, windows):
    rolling = listing["rolling"]
    row = {
        "listing_id": listing["listing_id"],
        "channel": listing["channel"],
        "title": listing["title"],
        "currency": listing["currency"],
    }
    primary_pct = None
    any_data = False
    for w in windows:
        days_at_floor = get_metric(rolling, "min_price_occurrence", f"0_{w}")
        pct_at_floor = round(days_at_floor / w * 100, 1) if days_at_floor is not None else None
        row[f"days_at_floor_{w}d"] = days_at_floor
        row[f"pct_at_floor_{w}d"] = pct_at_floor
        if pct_at_floor is not None:
            any_data = True
        if w == primary_window(windows):
            primary_pct = pct_at_floor
    row["_any_data"] = any_data
    row["_primary_pct"] = primary_pct
    return row


def build_floor_leaderboard(portfolio, windows, high_pct, medium_pct):
    rows = [compute_floor_row(l, windows) for l in portfolio]
    for r in rows:
        if not r["_any_data"]:
            r["floor_flag"] = "No Minimum Price Rule"
        elif r["_primary_pct"] is None:
            r["floor_flag"] = "Unknown"
        elif r["_primary_pct"] >= high_pct:
            r["floor_flag"] = "High"
        elif r["_primary_pct"] >= medium_pct:
            r["floor_flag"] = "Medium"
        else:
            r["floor_flag"] = "Low"
    # Listings with no rule at all aren't "low risk" on this signal, they're
    # not applicable -- sort them to the bottom rather than implying safety.
    rows.sort(key=lambda r: (not r["_any_data"], -(r["_primary_pct"] or 0)))
    for r in rows:
        del r["_any_data"]
        del r["_primary_pct"]
    return rows


# ---------------------------------------------------------------------------
# 5. Recent YoY Performance leaderboard (actual trailing RevPAR vs last year)
# ---------------------------------------------------------------------------
# Distinct from the Pacing leaderboard on purpose: Pacing is forward-looking
# and projected (where is this listing headed based on recent pickup).
# This one is entirely backward-looking and uses only settled actuals --
# "how has this listing really been performing lately" -- via the rolling
# KPI's own trailing windows (no extrapolation at all) compared to the same
# calendar window one year ago (blended across months the same way as the
# other leaderboards' LY comparisons).

def compute_yoy_performance_row(listing, today, windows, dead_band_pct):
    rolling = listing["rolling"]
    monthly_by_key = listing["monthly_by_key"]
    row = {
        "listing_id": listing["listing_id"],
        "channel": listing["channel"],
        "title": listing["title"],
        "currency": listing["currency"],
    }
    primary_delta = None
    any_ly_data = False
    for w in windows:
        recent_revpar = get_metric(rolling, "revpar", f"{w}_0")
        ly_window_start = one_year_before(today - datetime.timedelta(days=w))
        ly_revpar, coverage = blended_ly_value(monthly_by_key, "revpar", ly_window_start, w)
        if coverage < 0.5:
            ly_revpar = None

        delta_pct = None
        if recent_revpar is not None and ly_revpar:
            delta_pct = round((recent_revpar - ly_revpar) / ly_revpar * 100, 1)
            any_ly_data = True

        row[f"revpar_last_{w}d"] = round(recent_revpar, 2) if recent_revpar is not None else None
        row[f"ly_revpar_{w}d"] = round(ly_revpar, 2) if ly_revpar is not None else None
        row[f"yoy_delta_{w}d_pct"] = delta_pct
        if w == primary_window(windows):
            primary_delta = delta_pct

    row["_any_ly_data"] = any_ly_data
    row["_primary_delta"] = primary_delta
    row["_dead_band_pct"] = dead_band_pct
    return row


def build_yoy_performance_leaderboard(portfolio, today, windows, dead_band_pct):
    rows = [compute_yoy_performance_row(l, today, windows, dead_band_pct) for l in portfolio]
    for r in rows:
        if not r["_any_ly_data"]:
            r["yoy_flag"] = "No LY Data"
        elif r["_primary_delta"] <= -dead_band_pct:
            r["yoy_flag"] = "Declined YoY"
        elif r["_primary_delta"] >= dead_band_pct:
            r["yoy_flag"] = "Improved YoY"
        else:
            r["yoy_flag"] = "Flat YoY"
    rows.sort(key=lambda r: (not r["_any_ly_data"], r["_primary_delta"] if r["_primary_delta"] is not None else 0))
    for r in rows:
        del r["_any_ly_data"]
        del r["_primary_delta"]
        del r["_dead_band_pct"]
    return rows


# ---------------------------------------------------------------------------
# 6. Urgent Attention leaderboard (composite watchlist)
# ---------------------------------------------------------------------------
# Blends four independently-computed signals -- this project's own pace
# projection (not Wheelhouse's revenue_score), market position, rate-floor
# constraint, and YoY RevPAR trend -- into one ranked "who needs a look"
# list. Built by joining the four leaderboards above on listing rather than
# recomputing anything, so the numbers shown here always match what's in
# each individual leaderboard.
#
# Default weighting tier: pace and yoy_revpar (0.35 each) are the two most
# trusted signals -- one forward-looking, one backward-looking, both
# listing-specific trend measures -- so they're weighted equally highest.
# market_position (0.20) is next: useful context, but a low ratio can also
# just mean a soft neighborhood rather than a listing-specific problem.
# rate_floor (0.10) is weighted lowest since being pinned at a floor is a
# narrower, more mechanical signal than the other three.

def build_urgent_attention_leaderboard(pacing_rows, market_rows, floor_rows, yoy_rows,
                                        pacing_windows, market_windows, floor_windows, yoy_windows,
                                        weights, bands):
    pace_field = f"pace_delta_{primary_window(pacing_windows)}d_pp"
    market_field = f"market_ratio_{primary_window(market_windows)}d"
    floor_field = f"pct_at_floor_{primary_window(floor_windows)}d"
    yoy_field = f"yoy_delta_{primary_window(yoy_windows)}d_pct"

    def index_by_listing(rows):
        return {(r["listing_id"], r["channel"]): r for r in rows}

    pacing_by_key = index_by_listing(pacing_rows)
    market_by_key = index_by_listing(market_rows)
    floor_by_key = index_by_listing(floor_rows)
    yoy_by_key = index_by_listing(yoy_rows)

    pace_pool = [r.get(pace_field) for r in pacing_rows]
    market_pool = [r.get(market_field) for r in market_rows]
    floor_pool = [r.get(floor_field) for r in floor_rows]
    yoy_pool = [r.get(yoy_field) for r in yoy_rows]

    w_pace, w_market, w_floor, w_yoy = weights
    out = []
    all_keys = set(pacing_by_key) | set(market_by_key) | set(floor_by_key) | set(yoy_by_key)
    for key in all_keys:
        p = pacing_by_key.get(key, {})
        m = market_by_key.get(key, {})
        f = floor_by_key.get(key, {})
        y = yoy_by_key.get(key, {})
        title = p.get("title") or m.get("title") or f.get("title") or y.get("title")
        currency = p.get("currency") or m.get("currency") or f.get("currency") or y.get("currency")

        pace_value = p.get(pace_field)
        market_value = m.get(market_field)
        floor_value = f.get(floor_field)
        yoy_value = y.get(yoy_field)

        urgency_pace = 100 - percentile_rank(pace_pool, pace_value) if pace_value is not None else None
        urgency_market = 100 - percentile_rank(market_pool, market_value) if market_value is not None else None
        urgency_floor = percentile_rank(floor_pool, floor_value) if floor_value is not None else None
        urgency_yoy = 100 - percentile_rank(yoy_pool, yoy_value) if yoy_value is not None else None

        components = []
        if urgency_pace is not None:
            components.append((w_pace, urgency_pace))
        if urgency_market is not None:
            components.append((w_market, urgency_market))
        if urgency_floor is not None:
            components.append((w_floor, urgency_floor))
        if urgency_yoy is not None:
            components.append((w_yoy, urgency_yoy))

        if components:
            weight_sum = sum(w for w, _ in components)
            urgent_score = round(sum(w * v for w, v in components) / weight_sum, 1)
        else:
            urgent_score = None

        missing = []
        if urgency_pace is None:
            missing.append("pace")
        if urgency_market is None:
            missing.append("market_position")
        if urgency_floor is None:
            missing.append("rate_floor")
        if urgency_yoy is None:
            missing.append("yoy_revpar")

        high, medium = bands
        if urgent_score is None:
            band = "Unknown"
        elif urgent_score >= high:
            band = "High"
        elif urgent_score >= medium:
            band = "Medium"
        else:
            band = "Low"

        out.append(
            {
                "listing_id": key[0],
                "channel": key[1],
                "title": title,
                "currency": currency,
                "pace_delta_pp": pace_value,
                "market_ratio": market_value,
                "pct_at_floor": floor_value,
                "yoy_revpar_delta_pct": yoy_value,
                "urgent_score": urgent_score,
                "missing_signals": ";".join(missing) if missing else "",
                "urgent_band": band,
            }
        )

    out.sort(key=lambda r: (r["urgent_score"] is None, -(r["urgent_score"] or 0)))
    return out


# ---------------------------------------------------------------------------
# 7. Combined leaderboard (one row per listing, all six joined together)
# ---------------------------------------------------------------------------
# A single at-a-glance sheet -- every other leaderboard is easiest to read
# leaderboard-by-leaderboard, but a quick portfolio scan or a scheduled
# digest wants one row per listing with every flag side by side. Joined on
# (listing_id, channel) from the already-computed rows, so the numbers here
# always match the individual CSVs -- nothing is recomputed.

def build_combined_leaderboard(pacing_rows, expiring_rows, market_rows, floor_rows, yoy_rows, urgent_rows,
                                pacing_windows, market_windows, floor_windows, yoy_windows):
    pace_field = f"pace_delta_{primary_window(pacing_windows)}d_pp"
    market_field = f"market_ratio_{primary_window(market_windows)}d"
    floor_field = f"pct_at_floor_{primary_window(floor_windows)}d"
    yoy_field = f"yoy_delta_{primary_window(yoy_windows)}d_pct"

    def index_by_listing(rows):
        return {(r["listing_id"], r["channel"]): r for r in rows}

    pacing_by_key = index_by_listing(pacing_rows)
    expiring_by_key = index_by_listing(expiring_rows)
    market_by_key = index_by_listing(market_rows)
    floor_by_key = index_by_listing(floor_rows)
    yoy_by_key = index_by_listing(yoy_rows)
    urgent_by_key = index_by_listing(urgent_rows)

    all_keys = set(pacing_by_key) | set(expiring_by_key) | set(market_by_key) | set(floor_by_key) | set(yoy_by_key) | set(urgent_by_key)
    out = []
    for key in all_keys:
        p = pacing_by_key.get(key, {})
        e = expiring_by_key.get(key, {})
        m = market_by_key.get(key, {})
        f = floor_by_key.get(key, {})
        y = yoy_by_key.get(key, {})
        u = urgent_by_key.get(key, {})
        title = p.get("title") or e.get("title") or m.get("title") or f.get("title") or y.get("title") or u.get("title")
        currency = p.get("currency") or e.get("currency") or m.get("currency") or f.get("currency") or y.get("currency") or u.get("currency")

        out.append(
            {
                "listing_id": key[0],
                "channel": key[1],
                "title": title,
                "currency": currency,
                "pace_delta_pp": p.get(pace_field),
                "pace_flag": p.get("pace_flag"),
                "expiring_risk_score": e.get("risk_score"),
                "expiring_risk_band": e.get("risk_band"),
                "market_ratio": m.get(market_field),
                "market_flag": m.get("market_flag"),
                "pct_at_floor": f.get(floor_field),
                "floor_flag": f.get("floor_flag"),
                "yoy_revpar_delta_pct": y.get(yoy_field),
                "yoy_flag": y.get("yoy_flag"),
                "urgent_score": u.get("urgent_score"),
                "urgent_band": u.get("urgent_band"),
            }
        )

    out.sort(key=lambda r: (r["urgent_score"] is None, -(r["urgent_score"] or 0)))
    return out


# ---------------------------------------------------------------------------
# CSV writing
# ---------------------------------------------------------------------------

def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def selftest(data_dir):
    print("=== SELF-TEST: checking cache is readable ===")
    portfolio, skipped, resolved_dir = load_portfolio(data_dir, verbose=False)
    if resolved_dir != data_dir:
        print(f"Note: listings.json wasn't at --data-dir directly, found it under {resolved_dir} instead.")
    print(f"Listings with a cached KPI file: {len(portfolio)}")
    print(f"Listings skipped (no/unreadable KPI file): {len(skipped)}")
    if skipped[:5]:
        print("First few skipped:", skipped[:5])
    if not portfolio:
        print("FAIL: no usable listings found -- run wheelhouse-data-sync(-api) against this --data-dir first.")
        sys.exit(1)
    sample = portfolio[0]
    print(f"Sample listing: {sample['key']} ({sample['title']})")
    print(f"  rolling KPI top-level keys: {sorted(sample['rolling'].keys())}")
    print(f"  monthly rows available: {len(sample['monthly_by_key'])}")
    print("=== SELF-TEST PASSED -- safe to run a full build ===")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True, help="wheelhouse_data cache directory (the sync skills' --out)")
    ap.add_argument("--out", default=None, help="Output directory for the CSVs (default: <data-dir>/leaderboards)")

    ap.add_argument("--pacing-windows", default="30,60", help="Comma-separated forward windows in days, smallest first (default: 1 month, 2 months)")
    ap.add_argument("--pace-dead-band-pp", type=float, default=5.0,
                     help="Percentage-point band around 0 treated as 'On Pace' rather than ahead/behind")

    ap.add_argument("--expiring-windows", default="7,14,30", help="Comma-separated forward windows in days, smallest first")
    ap.add_argument("--rate-window", type=int, default=30, help="Window (days) for the asking-rate-vs-LY-ADR comparison")
    ap.add_argument("--low-ly-occupancy-threshold", type=float, default=0.50,
                     help="LY occupancy below this (0-1) sets the low_ly_demand flag")
    ap.add_argument("--risk-weights", default="0.5,0.3,0.2",
                     help="Weights for available_nights,pickup,rate_delta in the expiring-inventory risk score "
                          "(priority order: available nights dominant, pickup moderates it, rate delta amplifies it)")
    ap.add_argument("--risk-bands", default="66,33", help="High,Medium risk-score cutoffs (0-100 scale)")

    ap.add_argument("--market-windows", default="30,60,90", help="Comma-separated forward windows in days, smallest first")
    ap.add_argument("--market-dead-band-pct", type=float, default=0.15,
                     help="Fractional band around a 1.0 ratio treated as 'On Par With Market' (default 0.15 = 85%-115%)")

    ap.add_argument("--floor-windows", default="30,60,90", help="Comma-separated forward windows in days, smallest first")
    ap.add_argument("--floor-high-pct", type=float, default=30.0,
                     help="Percent of days at the minimum-price floor that counts as 'High' concern")
    ap.add_argument("--floor-medium-pct", type=float, default=15.0,
                     help="Percent of days at the minimum-price floor that counts as 'Medium' concern")

    ap.add_argument("--yoy-windows", default="30,60,90", help="Comma-separated trailing windows in days, smallest first")
    ap.add_argument("--yoy-dead-band-pct", type=float, default=10.0,
                     help="Percent band around 0 treated as 'Flat YoY' rather than improved/declined")

    ap.add_argument("--urgent-weights", default="0.35,0.20,0.10,0.35",
                     help="Weights for pace,market_position,rate_floor,yoy_revpar in the Urgent Attention score "
                          "(priority order: pace and yoy_revpar tied highest, market_position next, rate_floor lowest)")
    ap.add_argument("--urgent-bands", default="66,33", help="High,Medium urgent-score cutoffs (0-100 scale)")

    ap.add_argument("--date", default=None, help="Override 'today' (YYYY-MM-DD), mainly for testing")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest(args.data_dir)
        return

    today = parse_date(args.date) if args.date else datetime.date.today()

    pacing_windows = [int(x) for x in args.pacing_windows.split(",")]
    expiring_windows = [int(x) for x in args.expiring_windows.split(",")]
    market_windows = [int(x) for x in args.market_windows.split(",")]
    floor_windows = [int(x) for x in args.floor_windows.split(",")]
    yoy_windows = [int(x) for x in args.yoy_windows.split(",")]

    risk_weights = tuple(float(x) for x in args.risk_weights.split(","))
    risk_bands = tuple(float(x) for x in args.risk_bands.split(","))
    urgent_weights = tuple(float(x) for x in args.urgent_weights.split(","))
    urgent_bands = tuple(float(x) for x in args.urgent_bands.split(","))

    portfolio, skipped, data_dir = load_portfolio(args.data_dir, verbose=args.verbose)
    if not portfolio:
        sys.exit("No listings with cached KPI data found -- run wheelhouse-data-sync(-api) first.")
    out_dir = args.out or os.path.join(data_dir, "leaderboards")

    pacing_rows = build_pacing_leaderboard(portfolio, today, pacing_windows, args.pace_dead_band_pp)
    expiring_rows = build_expiring_leaderboard(
        portfolio, today, expiring_windows, args.rate_window,
        args.low_ly_occupancy_threshold, risk_weights, risk_bands,
    )
    market_rows = build_market_position_leaderboard(portfolio, market_windows, args.market_dead_band_pct)
    floor_rows = build_floor_leaderboard(portfolio, floor_windows, args.floor_high_pct, args.floor_medium_pct)
    yoy_rows = build_yoy_performance_leaderboard(portfolio, today, yoy_windows, args.yoy_dead_band_pct)
    urgent_rows = build_urgent_attention_leaderboard(
        pacing_rows, market_rows, floor_rows, yoy_rows,
        pacing_windows, market_windows, floor_windows, yoy_windows,
        urgent_weights, urgent_bands,
    )
    combined_rows = build_combined_leaderboard(
        pacing_rows, expiring_rows, market_rows, floor_rows, yoy_rows, urgent_rows,
        pacing_windows, market_windows, floor_windows, yoy_windows,
    )

    outputs = [
        ("leaderboard_pacing.csv", pacing_rows),
        ("leaderboard_expiring_inventory.csv", expiring_rows),
        ("leaderboard_market_position.csv", market_rows),
        ("leaderboard_rate_floor.csv", floor_rows),
        ("leaderboard_yoy_performance.csv", yoy_rows),
        ("leaderboard_urgent_attention.csv", urgent_rows),
        ("leaderboard_combined.csv", combined_rows),
    ]
    for filename, rows in outputs:
        write_csv(os.path.join(out_dir, filename), rows)
        print(f"Built {filename}: {len(rows)} listings")

    print(f"All leaderboards written to: {out_dir}")
    print(f"Listings skipped (no cached KPI file yet): {len(skipped)}")
    if skipped and args.verbose:
        print("Skipped:", skipped)

    behind = sum(1 for r in pacing_rows if r["pace_flag"] == "Behind LY")
    high_risk = sum(1 for r in expiring_rows if r["risk_band"] == "High")
    underperforming = sum(1 for r in market_rows if r["market_flag"] == "Underperforming Market")
    floor_high = sum(1 for r in floor_rows if r["floor_flag"] == "High")
    declined = sum(1 for r in yoy_rows if r["yoy_flag"] == "Declined YoY")
    urgent_high = sum(1 for r in urgent_rows if r["urgent_band"] == "High")
    print(f"Pacing: {behind} listing(s) flagged 'Behind LY'.")
    print(f"Expiring inventory: {high_risk} listing(s) flagged 'High' risk.")
    print(f"Market position: {underperforming} listing(s) 'Underperforming Market'.")
    print(f"Rate floor: {floor_high} listing(s) 'High' floor-constraint.")
    print(f"YoY performance: {declined} listing(s) 'Declined YoY'.")
    print(f"Urgent attention: {urgent_high} listing(s) flagged 'High'.")


if __name__ == "__main__":
    main()
```

