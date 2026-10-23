# checklist dials v2.7.2 = v2.7.1 + cutoff grid

Cyrus's ruling: every fixed cutoff gets tested as a dial ("try all definitions to see which give an edge under what conditions").
Question IDs and the v2.7.1 files are unchanged: 15,093 questions = 6,654 base + 8,439 history.

## New files
- `CUTOFF_GRID_v2.7.2.csv`: one row per hard-coded number found in the DIAL_TABLE dial rows (definition, answer_set, formula and notes) and in the HISTORY_BUCKETS rules, plus the history conventions. Columns: cutoff_id, scope, where_used, unit, current_default, grid_values, grid_size, bull_bear_mirror, context.
  - Grid rules:
    - ATR, %, multiple and sigma: default x {0.5, 0.75, 1, 1.5, 2}, with % capped at 100.
    - Bar counts or integers up to 5: {d-1 .. d+2}; larger: x {0.5, 0.75, 1, 1.5, 2}.
    - Fractions: x {0.5, 0.75, 1, 1.25, 1.5}.
    - Oscillator levels (RSI, MFI, Stoch, ADX, VIX zones): default ±5 and ±10.
  - Directional cutoffs are applied as ±value, so bull and bear are mirrored and one grid serves both sides.
- `QUESTION_CUTOFFS_v2.7.2.csv`: for each question_id, its default tags (`cutoff_id=value;...`) and its version counts under one-at-a-time and under the full cross.
- `cutoff_counts_v2.7.2.json`: summary counts.
- `build_cutoff_grid_v2.7.2.py`: rebuilds the three files above from the v2.7.1 outputs.

## Not counted as cutoffs (by design)
- Indicator periods such as RSI6/12/24 and SMA10/80 (those are variants).
- Calendar years in data notes.
- Fibonacci level names (61.8, 127, 161.8).
- The round-number level list ($1/5/10/50/100).
- The 1y/2y/3y horizons (part of the facet's identity).
- Publication lags in business days (leak rules).
- Structural 0 and 1 values.

Numbers were extracted by regex. Most grids are generic multipliers that should be reviewed per cutoff.

## Size
- 441 cutoffs: {'dial': 412, 'history': 26, 'history_convention': 3}. Grid sizes: {'3': 4, '4': 138, '5': 299}. 12,168 of 15,093 questions use at least one cutoff.
- One-at-a-time (recommended: vary one cutoff, keep the others at default): 208,837 question versions, x13.837 the base count.
- Full cross per question: 419,856,708 versions (x10^4.44); the worst single question has 16,000,000. Crossing all cutoffs globally gives 10^294.0.

## sha256
```
dfee714ec956673987b02df3b34ac671dd66f0e16f264bf07b05d4ac617b1dd0  build_cutoff_grid_v2.7.2.py
6f3e498da4a923f2c0c16710baa4f3c489b5d706c25695598a232aa9563aacd2  build_question_tree_v2.7.1.py
d53ca18651aa5bc128765fbf37fead299826bab2e036d76106ba7fd3af60827a  gen4_v2.7.1.py
31f587415f7e3c24873f544871c1fdd2627f9b2501175ffb76a744c019f06a24  CUTOFF_GRID_v2.7.2.csv
41bad6b6313591b04988ab44b376078e86d1c8f81812caef5805aef6ed851e30  DIAL_TABLE_v2.7.1.csv
d8adbb466dfc809e8084dd47fcea7c59b6ab2749c7f23e7e7d9f74b590e49f69  HISTORY_BUCKETS_v2.7.1.csv
10d096f53eb870b75bee338eecafd24e179199ae43650b876b1022f8f17c8ac3  HISTORY_LEVER_v2.7.1.csv
50afbb2e5ec31277dcc7bed4d72f7fbcaf96c0c188dd795549a24001fddf3c65  QUESTION_CUTOFFS_v2.7.2.csv
ac0a2e5ded7771e4515be6c1b789eb6bd2a953841963c59a7c78d81e5cd85e77  VARIANT_SERIES_v2.7.1.csv
df5efe175c082121beab558d8da0eec3eae1ce31c55cedb0fd9df484e2943dff  counts_v2.7.1.json
896827f7d0fd105e2d7418ca9f4c1858cdeffc4db5242ed7e7ef70592032159a  cutoff_counts_v2.7.2.json
85b4ae99645eee7d75bf353ac4468ecf7231670b2af72b104d757a82e2c1a292  tree/QUESTION_TREE_v2.7.1.csv
f5019a2bdfcdfe0a3cc3b062b68c7270af28ecc4cdbffe220269fbcc8eb4f3bf  tree/QUESTION_TREE_v2.7.1.html
2ece27af7d13414103ae66210c1afb7dd7bc70ebb81afc732952050f32cfd557  tree/QUESTION_TREE_v2.7.1.md
```
