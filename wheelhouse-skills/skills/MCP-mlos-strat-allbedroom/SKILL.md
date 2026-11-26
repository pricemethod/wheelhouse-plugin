---
name: MCP-mlos-strat-allbedroom
description: Market-wide version. Recommends a Minimum Length of Stay (MLOS / min stay / minimum nights) rule strategy for EVERY bedroom count the user manages in ONE Wheelhouse market, by season (High, Shoulder, Low), using market LOS and booking-window distributions live through the connected Wheelhouse MCP. Aims to beat the market rather than copy it - holds longer minimums only where high performers' bookings prove it pays, steps down ahead of the booking window, splits weekend vs weekday, and stays open in low season. Delivers a Wheelhouse-style HTML report (min-stay chart plus the rules laid out like the Minimum stays panel) for review; producing the Wheelhouse write-back is a separate opt-in step after the user approves or edits the rules. Trigger on "MLOS strategy for [market]," "min stay strategy across my listings in [market]," "recommend minimum stay rules for [market]," or any request covering several bedroom counts. For a single bedroom count (faster), use MCP-mlos-strat-bybedroom.
---

# MCP MLOS Strategy

Recommends a minimum-stay rule structure for every bedroom count the user manages in one market, built from Wheelhouse market data. For one bedroom count at a time (about 30 calls per run), use `MCP-mlos-strat-bybedroom`. Serves the **Identify → Intervene** handoff of Active Revenue Management: this skill proposes rules for review; writing them to Wheelhouse is a separate, opt-in step.

**Design principles (keep them):**
- **Beat the market, don't follow it.** Hold a longer minimum only when most high-performer bookings already meet it. Compare high vs average performers: if winners take shorter stays, go shorter.
- **All bedroom groups, one skeleton.** Every group gets the same rule structure; values and break points vary. Cost is ~24–28 calls per group, so with more than 4 groups suggest starting with the ones holding most of the user's listings, or the by-bedroom skill.
- **Simplicity over permutations.** The structure lives in `global`, `monthly` (season months, with weekend/weekday values), `time_based` step-downs, one `gap` rule, and the absolute minimum stay. Season rules, Event rules, date-specific overrides and Adjacency rules are left alone for the user's own exceptions.
- **1-night stays are opt-in.** Never recommend them unless the user opts in; do flag where they could work.

## Run order

1. **Scope** (ask once, with defaults)
2. **Market data** — Blocks A, B, C (+ C2 if the scorer asks)
3. **Score + render** — deliver the HTML report
4. **Offer** (only if relevant): refine with the user's own bookings
5. **Write-back** — only after the user reviews/edits and asks for it

Post a one-line progress note after every block ("Pass 1: 9/12 months · 0 failed · next: last 3 months"). Long silent stretches look like a hang.

## Step 1 — Scope

Confirm in one message, with defaults the user can accept:
1. **Market** — resolve from the user's listings (`market_name`), not by guessing.
2. **Bedroom groups** — default: every group where the user has listings in that market. State the cost (~24–28 calls and 2 blocks per group).
3. **Floor / absolute minimum stay** — default 2.
4. **1-night stays** — "Do you accept 1-night stays? If yes, in which seasons and how close to arrival?" Default no; if yes, default window is within 7 days.
5. **Threshold profile** — default `balanced`; the report always shows all three.

## Step 2 — Market data (`references/sandbox-blocks.md`)

- **Block A** (1–3 calls): market id, the user's listings by bedroom count, the market's bedroom groups, and `portfolio_eligibility` (real listings' trailing-year bookings; hypothetical listings excluded). A 404 on bedroom groups means no Pro listing in that market — stop and say market reports need one. Bedroom groups are per market (the top group has a `+`); map each of the user's bedroom counts to its group; groups with fewer than ~150 market listings pool into the nearest larger group (say so). The **base group** (weekday pattern) is the analyzed group with the most market listings.
- **Block B** (2 calls): trailing 12 complete months of market `revpar_w_fees` (seasons) and the base group's `occupancy_adjusted` by weekday (weekend split). Season = month's RevPAR ÷ annual mean: High ≥ 1.20, Low ≤ 0.85, else Shoulder. The user may override months.
- **Block C — pass 1** (24 calls and 2 blocks per group; `JOBS` can mix groups, ~18 calls per block): per month, high-performer LOS (all months); high-performer lead time (High and Shoulder months); average-performer LOS (Low months, for the low-season openness test).
- **Block C2 — pass 2** (0–5 calls per group): only if the scorer exits with `NEEDS_DATA` (a Low season that could rise above the floor needs lead time).

Save each block's output to a working folder (e.g. `<workspace>/mlos/<market>/`) right away and assemble `input.json` (`references/input-schema.md`). No caching between runs — users run this periodically and data should be fresh.

## Step 3 — Score and render

```bash
python scripts/score_mlos.py <dir>/input.json --out-dir <dir>/out          # add --final to stop asking for data
python scripts/render_report.py <dir>/out --group <group> --today <YYYY-MM-DD> --out <dir>/out/mlos_<group>br.html   # once per group
```

Scoring rules (constants at the top of `score_mlos.py`):

| Rule | Logic |
|---|---|
| Far-out MLOS per season | Largest N (floor..floor+4) where the high-performer share of bookings ≥ N nights meets the bar: High T, Shoulder T+5, Low T+10 |
| Low-season openness | Low rises above the floor only if high performers book N+ **more** often than average performers |
| Profiles | protective T=55%, balanced 60%, open 65% |
| Step-downs | Caps: High 4, Shoulder 3, Low 1. Use only what's needed |
| First step rung | Smallest of 7/14/30/60/90/120 days where cumulative bookings reach 35% (High), 50% (Shoulder), 65% (Low); one rung earlier if >40% of bookings fall below N; later steps use closer rungs |
| Weekend split | If Fri/Sat (+Thu when close) occupancy ≥ 1.15× Sun–Wed: weekend = season value, weekday one night less, never below floor |
| 1-night flag | Any month where ≥ 7% of high-performer bookings are 1 night |
| Absolute minimum + gap | `min_min_stay` = lowest allowed (floor, or 1 if opted in); one `gap` rule with that value fills orphans down to it |

**Deliver the reports:** one HTML report per group; publish them as hosted pages where the client supports that (e.g. claude.ai's Artifact tool); otherwise save the HTML files to the workspace and give the user their paths. It looks like Wheelhouse's Minimum stays page, condensed:
- a 12-month min-stay chart evaluated from the proposed rules as of today (gray step line, red absolute-minimum line, season shading), with toggleable market overlays: high performers' average stay by month (dashed line, on by default) and their booking mix by length of stay (1, 2, 3, 4, 5+ nights) as a faint stacked area behind the line on a right-hand 0–100% axis (off by default). The hover tooltip shows the month's market figures;
- the Rules panel in Wheelhouse order — Default, Day of week (unused), Monthly rules (month chips + Sun–Sat boxes), Time-based rules ("Within N days"), Season/Event/date-specific/Adjacency (unchanged), Gap night rules, Absolute minimum stay;
- one card per season: rungs × value table and a one-to-two-sentence reason generated from the evidence;
- side cards: threshold profiles, 1-night stays, refinement offer, next step.

In chat, keep it short: one table per season with bedroom groups as columns (from `mlos_report.md`; cells read weekend / weekday), one line on what's notable, and the offer if there is one. Don't paste the JSON plan.

## Step 4 — Optional refinement with the user's bookings

The scorer flags cells held above the floor that are **borderline** (within 5 points of the bar, or profiles disagree) or in **High season** (timing matters most). It's offered only if the group has real listings with ≥ 40 bookings in the trailing year. If the user opts in: run Block D for those listings, add the rows as `portfolio`, re-score, re-render. It can only lower a borderline far-out value by one night or move the first step one rung earlier, or confirm; thin data leaves the market result. Status: logic tested on synthetic data; reservation pull not yet run on real history.

## Step 5 — Write-back (opt-in, after review)

Don't generate write code or payloads until the user has reviewed the report and asks. Apply any edits they make (values, months, rungs, weekend split) to `mlos_plan.json` first, re-render so the reports match, then hand off to xContext-preferences for the write: per listing, mapped to its group by `num_bedrooms`, check `supported_settings.min_stays`, fetch preferences, replace only `global`, `day_of_week`, `monthly`, `time_based`, `gap` rules and `min_min_stay`, keep everything else (and existing `priority` values), preview, verify with `min_stay_calendar`, confirm, write.

**⚠️ Verify before the first write:** whether `day_of_week_values` on min-stay rules are enforced per night or by arrival day (Wheelhouse notes Airbnb applies day-of-week minimums by check-in day). If per night, a Fri/Sat value of 3 also blocks a Thursday-arrival 2-night stay.

## Reliability (prevents stalls)

- **Deferred retries.** A failed month goes into a retry queue; keep going with the next block. Retry the queue once after pass 1, and once more at most. The credential 401 tends to clear after a block or two.
- **Hard stop after two retry rounds.** Whatever still fails is skipped; never loop on the same items a third time.
- **Circuit breaker.** If two blocks in a row lose half or more of their items, stop pulling and score what's in hand (whole groups with no data are listed as not scored).
- **Always finish.** If the scorer returns `NEEDS_DATA` after one pass-2 attempt, run it with `--final`: missing months are skipped and listed as "Data note" lines; a Low season without lead time holds its far-out value or borrows from the nearest group's data if present; a Low season without average-performer data is held at the floor.
- **Known issues:** intermittent `401` on the MCP's `/mcp/credentials` lookup during call bursts (retry as above; if it persists, contact Wheelhouse support); MCP array bug (one `metric` per call); ~30 s per block, 18 calls per block is safe.
- **Cost per run:** ~5 calls + 24–28 per group. Four groups ≈ 110 calls (6–7 blocks); six groups ≈ 160 calls (9–10 blocks).

## Files

- `scripts/score_mlos.py` — scoring; writes `mlos_report.md`, `mlos_plan.json` (API-shaped rules), `mlos_evidence.json`.
- `scripts/render_report.py` — Wheelhouse-style HTML report from the plan and evidence.
- `references/sandbox-blocks.md` — execute blocks A, B, C, C2, D.
- `references/input-schema.md` — scorer input format.
