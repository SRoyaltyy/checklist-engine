# checklist dials v2.7.2.1: reviewed cutoff grid

This version reviews `dials/v2.7.2/CUTOFF_GRID_v2.7.2.csv`. Question IDs are unchanged, and so are the v2.7.1 dial and history files, which stay in `dials/v2.7.1/`.

- 441 cutoffs went in.
- 55 were dropped as structural or noise. Each one has a reason in `CUTOFF_DROPPED_v2.7.2.1.csv`.
- 189 rows were merged into 34 shared cutoffs (prefix `S_`).
- 197 were kept as facet-specific cutoffs.
- **That leaves 231 cutoffs.** Grid sizes: {'3': 2, '4': 72, '5': 157}.

- One-at-a-time (recommended): **151,879** question-versions, x10.063. v2.7.2 had 208,837.
- Full cross per question: 30,779,060 versions; the worst single question has 800,000.
- 11,812 of 15,093 questions use at least one cutoff.

## Drop reasons
- pattern size = facet identity: 3
- thirds split = structural: 2
- pole length as share of window = structural split: 1
- facet identity (top-3 days): 1
- count of start->end pairs (descriptive): 1
- two pivots = minimum to define a swing (structural): 2
- thirds index (structural): 1
- derived bin edge (= previous edge + 1): 16
- MA set membership (identity): 5
- Fibonacci level identities: 4
- data-availability requirement, not a cutoff: 6
- Ichimoku displacement = indicator identity: 2
- restates leg_atr (merged): 6
- seq length = facet identity: 1
- interior-extreme guard (structural): 1
- touch separation 1 bar = structural: 1
- MA length tied to window = structural: 2

## Shared cutoffs (default | grid | dial or history rows using it)
- `S_pivot_k_min`: 2 | 1|2|3|4 | 8
- `S_pivot_k_divisor`: 10 | 5|8|10|15|20 | 6
- `S_leg_atr`: 3 | 1.5|2.25|3|4.5|6 | 11
- `S_ratio_band_1p5`: 1.5 | 0.75|1.125|1.5|2.25|3 | 17
- `S_ratio_band_1p25`: 1.25 | 0.625|0.938|1.25|1.875|2.5 | 4
- `S_long_history_bars`: 500 | 250|375|500|750|1000 | 3
- `S_vol_spike_mult`: 3 | 1.5|2.25|3|4.5|6 | 5
- `S_baseline_bars`: 250 | 125|188|250|375|500 | 41
- `S_age_recent_bars`: 5 | 4|5|6|7 | 12
- `S_age_old_bars`: 20 | 10|15|20|30|40 | 12
- `S_base_range_atr`: 3 | 1.5|2.25|3|4.5|6 | 2
- `S_leg_min_bars`: 5 | 4|5|6|7 | 9
- `S_ratio_band_1p3`: 1.3 | 0.65|0.975|1.3|1.95|2.6 | 5
- `S_trend_t_stat`: 2 | 1|2|3|4 | 12
- `S_osc_zone_high`: 80 | 70|75|80|85|90 | 33
- `S_osc_zone_low`: 20 | 10|15|20|25|30 | 34
- `S_majority_share_pct`: 60 | 30|45|60|90|100 | 14
- `S_rsi_extreme_low`: 30 | 20|25|30|35|40 | 10
- `S_flat_atr`: 1 | 0.5|0.75|1|1.5|2 | 3
- `S_base_min_bars_10`: 10 | 5|8|10|15|20 | 12
- `S_rsi_extreme_high`: 70 | 60|65|70|75|80 | 9
- `S_shock_atr`: 3 | 1.5|2.25|3|4.5|6 | 2
- `S_flat_base_atr`: 2 | 1|1.5|2|3|4 | 3
- `S_break_atr_2`: 2 | 1|1.5|2|3|4 | 1
- `S_retest_tol_atr`: 0.5 | 0.25|0.375|0.5|0.75|1 | 12
- `S_break_atr_1`: 1 | 0.5|0.75|1|1.5|2 | 9
- `S_base_min_bars_15`: 15 | 8|11|15|22|30 | 1
- `S_count_many`: 2 | 1|2|3|4 | 2
- `S_cluster_window_bars`: 5 | 4|5|6|7 | 3
- `S_shock_max_bars`: 3 | 2|3|4|5 | 8
- `S_squeeze_release_atr`: 0.5 | 0.25|0.375|0.5|0.75|1 | 1
- `S_stage_slope_atr`: 0.05 | 0.025|0.038|0.05|0.075|0.1 | 1
- `S_partial_low_share`: 0.25 | 0.125|0.188|0.25|0.312|0.375 | 1
- `S_partial_high_share`: 0.75 | 0.375|0.562|0.75|0.938|0.99 | 1

On ratio bands (for example 1.5 and 0.67), the lower side is the mirror, 1/hi, so it folds into the same cutoff. A merged cutoff moves in every row that uses it at the same time.

## sha256
```
bc276749807cc29af72526b682715508647950e23e47fc6a550c6091c85f4046  review_cutoffs_v2.7.2.1.py
57e224af97f19564f3f880fe2eecaef9c8c70c8aec0be924529d100ed5e8d395  CUTOFF_DROPPED_v2.7.2.1.csv
7b9a406b65192e45a7fc9e8d025c59a9ca716e9770619d2c640add284395e989  CUTOFF_GRID_v2.7.2.1.csv
331f9554766d160cc069715c156d05a1c41224b0c2f5975b7832bc3337b9a619  QUESTION_CUTOFFS_v2.7.2.1.csv
0df9c034862ff6ce4bfc8c5a30778297819d4df26e5a6899aa5c11797d795ec7  cutoff_counts_v2.7.2.1.json
```
