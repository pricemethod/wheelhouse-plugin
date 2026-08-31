# Pace Signal Guide

Full reference for `stly-pacing`'s pace signal and interpretation text. This is the Matrix Pacing framework (ADR × Occupancy vs. a trusted benchmark) applied specifically to STLY as the benchmark, at the period level.

---

## Which occupancy drives the signal

This skill computes both Occupancy (unadjusted) and Occupancy (Adjusted). **The signal is driven by ADR (Rent) × Occupancy (Adjusted)** — adjusted occupancy is the more meaningful pricing-strategy metric because it excludes blocked nights an owner has taken out of the rental pool, so it isn't diluted by inventory that was never available to sell. Both occupancy flavors are still shown in the output table; only Adjusted feeds `pace_signal`.

If a listing/segment's use case calls for matching external tools that report raw calendar occupancy (Keydata, AirDNA-style "Calendar Occupancy %"), swap the driver to Occupancy (unadjusted) — the rest of the framework is unaffected either way.

Revenue (Rent) and Revenue (+ Fees) variance are always present in the output as read context. They never drive the signal.

---

## Dead-band and signal derivation

A metric is "neutral" on its axis when its variance % is within ±2.0% (inclusive).

**Evaluation order:** check for `null` first (either `adr_rent_pct` or `occupancy_adj_pct` missing → `no_stly`), then apply the dead-band.

| `adr_rent_pct` | `occupancy_adj_pct` | `pace_signal` |
|---|---|---|
| Either is `null` | — | `no_stly` |
| Within ±2% | Within ±2% | `neutral` |
| Within ±2% | Above +2% | `adr_neutral_occ_up` |
| Within ±2% | Below −2% | `adr_neutral_occ_down` |
| Above +2% | Within ±2% | `adr_up_occ_neutral` |
| Below −2% | Within ±2% | `adr_down_occ_neutral` |
| Above +2% | Above +2% | `adr_up_occ_up` |
| Above +2% | Below −2% | `adr_up_occ_down` |
| Below −2% | Above +2% | `adr_down_occ_up` |
| Below −2% | Below −2% | `adr_down_occ_down` |

**Icons:**
🟢 `adr_up_occ_up` · 🔴 `adr_down_occ_down` · 🟡 any mixed signal · ⚪ `neutral` · ❓ `no_stly`
⚡ `immediate` · 🔶 `short` · 🔷 `medium` · 🔵 `long` · 🌐 `far`

Only periods with a non-`neutral`, non-`no_stly` signal get an interpretation line in the output — neutral periods are omitted from the interpretation block to keep it focused (they still appear in the table).

---

## Interpretation text by signal × booking window

**`adr_up_occ_up` — rate and occupancy both ahead**

| Window | Interpretation |
|---|---|
| immediate | Strong close-out — both metrics ahead with little time left. Hold position and watch for late cancellations. |
| short | Good momentum. Keep holding rate; watch pick-up velocity so the rate gain isn't throttling demand as the period fills. |
| medium | Strong pace in the primary booking window. Look for a compression date driving the signal; consider incremental rate increases while watching for stalling. |
| long | Early strength. Check whether one date is driving it or the whole period is up. Raise rates and set a milestone to re-check velocity. |
| far | Early positive signal — raise rates and watch for stalling as you push rate position. |

**`adr_down_occ_down` — rate and occupancy both behind**

| Window | Interpretation |
|---|---|
| immediate | Urgent — low demand with almost no time left. Prioritize occupancy: undercut market if needed, check distribution. |
| short | Low-demand signal. Undercut market, check distribution, focus on occupancy — limited window to recover. |
| medium | Check market trends and distribution; decide hold vs. adjust based on booking-window behavior. |
| long | Same check, but more room to course-correct if the trend shifts. |
| far | Early warning — check market trends and listing performance, reforecast. Not urgent yet. |

**`adr_up_occ_down` — rate ahead, occupancy behind**

| Window | Interpretation |
|---|---|
| immediate | High risk — rate held too high, occupancy dragging, no time left. Cut rate (possibly below LY) and prioritize catching up on occupancy. |
| short | Likely price resistance. Cut rate, check comp set. Could still beat YoY revenue if the occupancy gain is large enough. |
| medium | May mean rate growth outran the market. Reforecast and check whether the projected ADR growth is realistic. |
| long | Low risk — may just be too early in the window for occupancy to have built yet. Recheck once the primary booking window opens. |
| far | Low risk, too early for occupancy to reflect demand. Check market trends and whether the rate plan is reasonable. |

**`adr_down_occ_up` — rate behind, occupancy ahead**

| Window | Interpretation |
|---|---|
| immediate | Undersold but largely committed. May still beat YoY RevPAR if the occupancy gain is big enough — calculate the ADR needed at current occupancy to beat LY revenue. |
| short | Low risk — an occupancy-led approach may still beat LY revenue. Keep driving occupancy; consider measured rate raises. |
| medium | High-risk early signal — underselling a period that's booking fast. Check rate vs. LY ADR and look for compression dates where rate can be raised. |
| long | High risk if it continues — early sign of underselling. Check rate vs. LY ADR and monitor for compression. |
| far | High risk if the trend holds — early base of business building at a low rate. Consider raising rate before the window compresses. |

**`adr_neutral_occ_up` — rate flat, occupancy ahead**

| Window | Interpretation |
|---|---|
| immediate | Strong occupancy close-out with rate holding — good position, maintain. |
| short | Solid occupancy pace, stable rate — consider a modest rate test given the demand strength. |
| medium | Occupancy building ahead of pace with rate flat — look for room to push rate into the demand. |
| long | Early occupancy lead, rate holding — monitor whether rate can move up into the signal. |
| far | Occupancy building early, rate stable — watch for a rate-raise opportunity as the window approaches. |

**`adr_neutral_occ_down` — rate flat, occupancy behind**

| Window | Interpretation |
|---|---|
| immediate | Occupancy lagging, rate flat, no time left — consider a last-minute discount to move remaining nights. |
| short | Occupancy behind, rate holding — evaluate whether a modest rate cut would accelerate pick-up. |
| medium | Occupancy soft, rate flat — check whether this is market-wide or listing-specific. |
| long | Early occupancy lag, rate neutral — monitor before adjusting; may be too early to act on. |
| far | Too early to act — keep monitoring as the window approaches. |

**`adr_up_occ_neutral` — rate ahead, occupancy flat**

| Window | Interpretation |
|---|---|
| immediate | Strong rate with occupancy on pace — good close-out position, maintain. |
| short | Rate ahead, occupancy tracking — watch pick-up velocity for signs the rate gain is throttling demand. |
| medium | Rate gains holding with flat occupancy — watch for price resistance as the window progresses. |
| long | Early rate strength, occupancy neutral — good early signal; watch whether occupancy builds into it. |
| far | Rate running ahead early, occupancy not yet developed — too early to conclude much. |

**`adr_down_occ_neutral` — rate behind, occupancy flat**

| Window | Interpretation |
|---|---|
| immediate | Rate below LY, occupancy flat, limited time — weigh whether a rate cut to drive final nights is worth it. |
| short | Rate lagging, occupancy on pace — check comp set; may be room to recover rate if occupancy holds. |
| medium | Rate soft, occupancy flat — check market trends; may be underselling if occupancy holds into peak. |
| long | Rate below LY, occupancy flat — review market direction and reforecast. |
| far | Early rate softness — check market trends; too early for occupancy to reflect demand yet. |

**`neutral` — both metrics within the dead-band**

| Window | Interpretation |
|---|---|
| immediate | Tracking closely to last year — monitor for late movement. |
| short | On pace with LY — keep watching pick-up velocity. |
| medium | On pace — no action needed, keep monitoring. |
| long | Early pace matching LY — continue monitoring as the window develops. |
| far | Too early to conclude anything — currently in line with last year. |

**`no_stly` — insufficient prior-year data**

| Window | Interpretation |
|---|---|
| all | No STLY data for this period — pace signal can't be calculated. Review absolute metrics and current asking rates instead. |
