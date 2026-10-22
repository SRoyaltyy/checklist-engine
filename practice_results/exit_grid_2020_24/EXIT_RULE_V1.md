# EXIT_RULE_V1 — exit-grid test, 2020–24 practice data only (HINT)
Built Fri 2026-10-23 HKT. No price bar after 2024-12-31 was read (parquet filter date<=2024-12-31). 2025–26 sealed.

## Frozen rule (fixed before any result was viewed; X grid per Manager steering)
- Entries: panel `story_q/panel.parquet` rows (date = D), minus every (ticker,date) in `buyable_filter/drop_list_v2.csv`.
  Groups: ALL (control), CHART6 (all 6 hard chart checks = 2), Q5/Q7/Q8 YES (sq5_big_red_recent, sq7_lowerbb_reclaim, sq8_above_last_red_high).
  Signal kept only if the ticker has 21 bars D..D+20 all <= 2024-12-31.
- Entry = open of D. Day 1 = D. Fees 0.6% round trip (30bp each way), subtracted from gross return.
- Grid: X in {3,5,8,10,15,20}%; stop S in {none, X/2, X}; max hold H = 1..21 trading days. 6x3x21 = 378 rules x 4 groups x 3 periods.
- Each day: if stop set and low <= entry(1-S) -> exit at min(open, stop) [checked FIRST, so same-day touch of both = stop];
  else if high >= entry(1+X) -> exit at max(open, target) [gap fills at open]; if neither by day H -> close of day H.
- Win = net return > 0. Excess = row net minus the ALL-control mean on the same D under the same rule.
- CI: date-clustered bootstrap (500 resamples of D), 95%. p from bootstrap z. Benjamini–Hochberg q=0.05 over ALL non-control cells together (4,536 tests: 378 rules x 4 groups x 3 periods).
- Selection: best cell chosen on 2020–22 only; reported on 2023–24.

## Results (n after filter: ALL 2,408,833; CHART6 43,060; Q5 592,075; Q7 857,912; Q8 873,547)
- Best 2020–22 cell by excess: X=20, no stop, H=17, CHART6: win 49.5%, excess +1.09% [-0.14,+3.08], BH q=0.32 -> FAILS BH. 2023–24: win 49.3%, mean +0.33%, excess -0.17% [-0.42,+0.08] -> does not hold.
- Best 2020–22 cell that passes BH: X=20, no stop, H=15, Q5: win 50.7%, mean +1.24%, excess +0.40% [+0.21,+0.66], q=0.009. 2023–24: win 49.2%, mean +0.38%, excess +0.09% [+0.01,+0.17], q=0.072 -> same sign, smaller, misses BH.
- 145 rule×group cells pass BH in BOTH halves with the same sign: Q5 85 (+), Q7 15 (+), CHART6 42 (−), Q8 3 (−).
  Strongest positive in 2023–24: X=15, no stop, H=14, Q7: win 51.3%, mean +0.53%, excess +0.12% [+0.05,+0.19], q=0.010.
- Win rates: small X gives high win rates for everything (X=3, H=21, no stop: CHART6 79%, Q7 77%) but mean net is ~0 or negative — the win rate measures X, not edge. No cell reaches a 55% win rate with a positive excess that survives both halves.

## sha256
```
9a1aacf4331b71338cd1f2b5486f1d719977e06def616fb3bf1704cab3d7f4b8  exit_grid.py
6d05f56fa7b1ad001a51c94708477e9a9dbec849f30f4c00403c43837c1b0220  exit_grid_results_v1.csv
0249a8e75fb780944321e9b309b6df30c8a04f05083fc3639105b37f909297d9  ../story_q/panel.parquet
5a6cb756b7b71c1658b89524a6c2349136ad6132c642a88d8e91be4566963239  ../buyable_filter/drop_list_v2.csv
fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337  /workspace/pricehist/universe_2020_survivors.parquet
3828cfb7cfb019c4da0195c3f66c70b766aab54eee63282e5b5d5cfaf0bfbca9  ../story_q/story_q.py
```
