# Methodology: Ranking Math

## Percentile urgency score

For a gated pool of listings and a metric where **lower = more urgent**
(both `occupancy_adjusted` and `pickup` qualify -- low occupancy and low
pickup are both bad):

1. Sort the pool ascending by the metric value.
2. Walk the sorted list; for any run of tied values, assign every tied
   listing the **average rank position** across the tied block (not the
   first or last position in the block) -- this is the standard
   tied-rank-averaging convention and avoids an arbitrary ordering among
   ties.
3. Convert rank position to a 0-1 score: `score = 1 - (avg_rank_position /
   (n - 1))`, so the single lowest value scores 1.0 (max urgency) and the
   highest scores 0.0.

```python
def percentile_rank_ascending_urgency(ids, values):
    sorted_ids = sorted(ids, key=lambda i: values[i])
    n = len(sorted_ids)
    scores = {}
    i = 0
    while i < n:
        j = i
        while j < n and values[sorted_ids[j]] == values[sorted_ids[i]]:
            j += 1
        avg_rank = (i + j - 1) / 2.0
        score = 1.0 - (avg_rank / (n - 1)) if n > 1 else 1.0
        for k in range(i, j):
            scores[sorted_ids[k]] = score
        i = j
    return scores
```

## Composite score

`composite = (occupancy_urgency_score + pickup_urgency_score) / 2`

Sort descending by composite for the final ranking.

## Tie-break rule (confirmed against real dry-run data)

Exact composite ties happen -- in the validation run against the real
48-listing portfolio, three listings tied at a 0.763 composite after the
availability gate alone (before the automation gate was added), and two
tied at 0.758 after both gates were in place. Without an explicit rule,
Python's default set/dict iteration order decides the winner, which is
**not deterministic run-to-run**.

**Rule:** break ties by `nights_available (0_60)` descending (more room to
act wins the tiebreak), then by `wheelhouse_id` ascending as a final
deterministic fallback if `nights_available` also ties.

```python
ranked = sorted(gated, key=lambda i: (-composite[i], -nights_available[i], i))
```

This is what separated the two 0.758-composite listings in the real run
(51 vs. 46 available nights).
