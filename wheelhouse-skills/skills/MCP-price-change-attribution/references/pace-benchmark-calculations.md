# Pace Benchmark Calculations

Used for **General**-bucket changes (Step 5 of SKILL.md), where there's no bounded date range to join bookings against, so the change is evaluated against a pace trend instead.

## Windows

Given `lookback_days` (7 or 30, whatever the user specified) and today's date:

- **Check window**: `today - lookback_days` through `today` — the period being examined for changes (matches the changelog query window from Step 1).
- **Baseline window**: `today - lookback_days - 30` through `today - lookback_days` — a fixed 30 days immediately preceding the check window. Always 30 days regardless of the check window's length; this is what makes a 7-day check window comparable to the baseline without a raw-total mismatch.

Both windows are pulled from the single Step 3 reservations fetch (`booked_at`-filtered) — no separate calls.

## Per-day rate calculation

For each window, using reservations with `booked_at` in that window:

```
nights_per_day   = sum(nights across reservations in window) / window_length_days
bookings_per_day = count(reservations in window) / window_length_days
revenue_per_day   = sum(revenue, per revenue_basis) / window_length_days
ADR               = sum(revenue) / sum(nights)   [not divided by days — ADR is already a rate]
```

`window_length_days` is 30 for the baseline, and `lookback_days` (7 or 30) for the check window.

## Comparison

```
pct_change = (check_window_rate - baseline_rate) / baseline_rate * 100
```

Suggested interpretation bands (consistent in spirit with the ±2% dead-band used in `stly-pacing`, widened slightly since this is a noisier daily-rate comparison rather than a longer aggregate):

| `pct_change` | Read |
|---|---|
| > +10% | Pace increased since the change |
| −10% to +10% | No material change in pace |
| < −10% | Pace decreased since the change |

These bands are a starting default, not a fixed rule — flag them as adjustable if the user wants tighter or looser thresholds.

## Worked example

Baseline window: 40 nights over 30 days → 1.33 nights/day.
Check window (7 days, since a base-price change): 14 nights over 7 days → 2.0 nights/day.

```
pct_change = (2.0 - 1.33) / 1.33 * 100 ≈ +50%
```

Read: pace increased materially since the change. Report this alongside the ADR comparison (did the extra pace come at a lower rate, i.e. a discount-driven pickup, or hold ADR steady?) so the RM can see the full picture, not just nights booked.

## Caveats to always state in output

- This is a **correlation**, not a causal claim — other factors (seasonality, market demand, other simultaneous changes) can move pace independent of this specific change.
- The baseline window may itself contain other pricing changes. That's expected — it's a "normal pace" reference point, not a controlled/isolated comparison.
- If the listing has less than ~30 days of booking history, the baseline will be noisy or built on too little data — flag rather than present as reliable.
