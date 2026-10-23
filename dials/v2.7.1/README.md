# checklist dials v2.7.1 — history answer buckets LOCKED

v2.7.1 = v2.7 + locked answer buckets for every kept history_value. **Questions, names and counts are unchanged: 14,643 = 6,654 base + 7,989 history** (`counts_v2.7.1.json` is identical to v2.7 `counts.json`; `DIAL_TABLE_v2.7.1.csv` is byte-identical to `DIAL_TABLE_v2.7.csv`; `HISTORY_LEVER_v2.7.1.csv` = v2.7 columns unchanged + `answer_set`). Frozen v2.7 files are untouched.

## Changelog (v2.7 -> v2.7.1)
- Added `HISTORY_BUCKETS_v2.7.1.csv`: 14 history_values x locked buckets, one deterministic one-line rule per bucket (shape stays lookalike_input, not a question).
- Added `VARIANT_SERIES_v2.7.1.csv`: for each of 54 variants, the primary series X, paired series Y, bench, and unit (ATR14 for price series, else sX = std of 1-bar changes over the 250 bars before the window).
- `gen4_v2.7.1.py`: v2.7 generator unchanged in question logic; output names -> v2.7.1; appends bucket emission.
- Conventions: all bars < D; window W = last B bars of U-day candles ending D-1; k = max(1,N//10); thirds of W; n_a checked first, then rules top to bottom, first match wins (mutually exclusive + exhaustive). Directional values mirror bull/bear (up_/down_, support/resistance, high_first/low_first).
- Tree regenerated (`tree/`), "proposed:" removed.

Rebuild: `cd <dir> && python3 gen4_v2.7.1.py && python3 build_question_tree_v2.7.1.py` (the build script has box paths at the top).

## sha256
```
98445deea9c0c3b8780c03e4c416de86f72d5fd426d29dc7302c611f91e81c4e  gen4_v2.7.1.py
7a89f672973cda6543ecf60a6f607682fb3470efc810ab80571b0d387dccf903  build_question_tree_v2.7.1.py
41bad6b6313591b04988ab44b376078e86d1c8f81812caef5805aef6ed851e30  DIAL_TABLE_v2.7.1.csv
fb0ebab7646f4c4dd1542865594e896b4f7bb4a1d9f0839cdc3faa2715593c53  HISTORY_BUCKETS_v2.7.1.csv
727ac15836352c4ca3953438693f6fea297625cc6987b10f77c4c38e172205e2  HISTORY_LEVER_v2.7.1.csv
ac0a2e5ded7771e4515be6c1b789eb6bd2a953841963c59a7c78d81e5cd85e77  VARIANT_SERIES_v2.7.1.csv
c0bd4fcd7dea28117d12d339d9dc7978cab827f45075add17a43394004bf8be2  counts_v2.7.1.json
9f864a003e481a5c71805a33fc60b2da31d05bb81c7a840e4deee286940c3a35  tree/QUESTION_TREE_v2.7.1.csv
05347c0df6ccf78b9e27186397f0fac63db6cf984e8ef8d8b7b9ef40726eaa1f  tree/QUESTION_TREE_v2.7.1.html
3c27b3f945e06709f18879bf4221379f65cd80be500336da8444457c9dd5238e  tree/QUESTION_TREE_v2.7.1.md
c5d15d6a118bbf84f4d9c1bfe511a951518204eee3b5ddca732b9867d7ba3f24  ../v2.7 gen4_v2.7.py (parent, unchanged)
```
