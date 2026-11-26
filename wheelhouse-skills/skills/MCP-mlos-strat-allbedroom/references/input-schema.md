# Scorer input (`input.json`)

```json
{
  "market": {"id": 123, "name": "Example City, ST"},
  "params": {
    "profile": "balanced",
    "floor": 2,
    "one_night": {"opt_in": false, "months": [1, 2], "days_before": 7},
    "season_override": null
  },
  "season_index": {"2025-11": {"revpar": 150.0}},
  "weekday_occ": {"2025-11": [0.40, 0.40, 0.45, 0.50, 0.70, 0.70, 0.40]},
  "groups": {
    "2": {
      "market_listings": 5000,
      "user_listings": 1,
      "months": {
        "2025-11": {
          "los_high": [0.0, 0.01, 0.30, 0.50, 0.15, 0.03, 0.01],
          "los_avg":  [0.0, 0.03, 0.35, 0.45, 0.13, 0.03, 0.01],
          "lead_high_within": {"7": 0.01, "14": 0.05, "30": 0.30, "60": 0.80, "90": 0.95, "120": 0.99}
        }
      }
    }
  }
}
```

- `season_index` and `weekday_occ` come from Block B; `weekday_occ` lists Mon…Sun. `season_index` entries may also be `{"occ", "adr"}` (the scorer multiplies them).
- Pass 1 gives every month `los_high`; High/Shoulder months add `lead_high_within`; Low months add `los_avg`. Pass 2 adds `lead_high_within` to Low months the scorer names.
- `los_high` / `los_avg` are probabilities indexed by nights (index 1 = 1-night stays); trailing zeros may be trimmed.
- `lead_high_within` is the cumulative share booked within each rung.
- `season_override`, if set, is `{"high": ["2026-06", ...], "shoulder": [...], "low": [...]}`.
- Months missing for a group (failed pulls) are skipped; the report should say which months are missing.
- Optional `portfolio_eligibility` (from Block A): `{"3": {"listings": 3, "bookings": 120}}` — real (non-hypothetical) listings and trailing-year bookings per group. Lets the report state whether refinement is available and its estimated cost.
- Optional `portfolio` (from Block D, only after opt-in): `{"rows": [[group, "YYYY-MM" stay month, nights, lead_days], ...]}`. Applied only to cells the scorer flagged.
- Optional `T` overrides the profile's threshold.
