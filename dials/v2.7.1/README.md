# checklist dials v2.7.1 — history answer buckets LOCKED (+ retest_count)

**Totals: 15,093 questions = 6,654 base + 8,439 history (v2.7: 14,643 = 6,654 + 7,989; delta +450, all from the new history question `retest_count`).**
All 14,643 v2.7 questions keep their names/ids. `DIAL_TABLE_v2.7.1.csv` is byte-identical to v2.7. `HISTORY_LEVER_v2.7.1.csv` = v2.7 rows unchanged + 28 `retest_count` keep rows (+ its drop/lookalike rows) + `answer_set` column. Frozen v2.7 files untouched.

## Changelog (v2.7 -> v2.7.1), per Manager's final calls
- Locked buckets for all 15 question-bearing history_values in `HISTORY_BUCKETS_v2.7.1.csv` (one-line rule per bucket, plus `engine_label -> locked_label` map for renaming in Taskforce's engine `facets_v26.HLAB`).
- Labels for speed/time_since/character_change/stage/change_of_state/vs_own_past/lead_lag use New Bot wording; engine labels mapped.
- divergence_sync: in_sync dropped (folds into none). order_of_events: high_first/low_first/none. route: 27 H/M/L routes dropped -> up_down/down_up/straight_up/straight_down/flat (flat = net move < 1 unit). retests: held/failed/none. NEW history_value retest_count {0,1,2+} on the same variants/timeframes as retests (+450 questions). squeeze_release: released_up/released_down/still_squeezed/none. shock_recovery: engine's 5 + partial. timeframe_agreement unchanged.
- Missing data = engine -1 ("n_a"), not an answer bucket. All rules bars < D; sizes in ATR14 for price series, else sX (std of 1-bar changes, 250 bars before window). First match wins.
- `VARIANT_SERIES_v2.7.1.csv`: primary series X, paired Y, bench and unit per variant.
- Tree regenerated in `tree/`.

## sha256
```
d53ca18651aa5bc128765fbf37fead299826bab2e036d76106ba7fd3af60827a  gen4_v2.7.1.py
6f3e498da4a923f2c0c16710baa4f3c489b5d706c25695598a232aa9563aacd2  build_question_tree_v2.7.1.py
41bad6b6313591b04988ab44b376078e86d1c8f81812caef5805aef6ed851e30  DIAL_TABLE_v2.7.1.csv
d8adbb466dfc809e8084dd47fcea7c59b6ab2749c7f23e7e7d9f74b590e49f69  HISTORY_BUCKETS_v2.7.1.csv
10d096f53eb870b75bee338eecafd24e179199ae43650b876b1022f8f17c8ac3  HISTORY_LEVER_v2.7.1.csv
ac0a2e5ded7771e4515be6c1b789eb6bd2a953841963c59a7c78d81e5cd85e77  VARIANT_SERIES_v2.7.1.csv
df5efe175c082121beab558d8da0eec3eae1ce31c55cedb0fd9df484e2943dff  counts_v2.7.1.json
85b4ae99645eee7d75bf353ac4468ecf7231670b2af72b104d757a82e2c1a292  tree/QUESTION_TREE_v2.7.1.csv
f5019a2bdfcdfe0a3cc3b062b68c7270af28ecc4cdbffe220269fbcc8eb4f3bf  tree/QUESTION_TREE_v2.7.1.html
2ece27af7d13414103ae66210c1afb7dd7bc70ebb81afc732952050f32cfd557  tree/QUESTION_TREE_v2.7.1.md
```
