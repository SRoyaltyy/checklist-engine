# SCORE_V1 — count-the-signs score (pre-registered before any score result was computed)
Practice 2020–24 only; no bar after 2024-12-31 read.
Input: FINDINGS_FREEZE_V1.csv @ SRoyaltyy/checklist-engine commit 3502460, sha256 a8819d1f8925e8b59567871f9b523276f33c92c57beb8c1fd98dc2f79187e66f (verified). All 1,503 rows have found_on = 2020-22.

## Signs
- Rows deduplicated by item (1,107 items). An item's sign = its direction (all items have one direction across setups; none conflicting).
- Used: the 796 path-bank-v2 items (`ph2_*`, 165 winner-leaning, 631 loser-leaning), answered with frozen path_bank_v2.py (sha d0910085…79cc), whose features are shifted 1 bar (only bars before D).
- Skipped (listed in items_used_skipped.csv): 311 sheet:TR / sheet:NB / master.csv / lookback-grid items — not recomputed for the full panel in this run.
- score = (# winner-leaning items YES) − (# loser-leaning items YES). Missing answer = not true.

## Cases and fifths
- Panel story_q/panel.parquet (date = D) minus drop_list_v2; signal kept only if 21 bars D..D+20 exist <= 2024-12-31 (same as EXIT_RULE_V1).
- Fifths F1 (lowest) .. F5 (highest): cutoffs = 20/40/60/80th percentiles of score over all 2020–22 cases; same cutoffs applied to 2023–24. Ties at a cutoff go to the lower fifth (score <= cutoff), so fifths may be unequal.

## Per fifth, per period (2020–22, 2023–24), vs ALL
- Hit rates: intraday high >= entry x (1.10 / 1.15 / 1.20) on any of days 1–21.
- View A (EXIT_RULE_V1): +20% take-profit, no stop, else sell close of day 15. Win%, mean, median net (0.6% round trip), excess vs ALL same D, date-clustered bootstrap 95% CI (500).
- View B: plain hold, sell at close of day 10 (entry open D). Same stats.
- BH q=0.05 over the excess tests here (5 fifths x 2 views x 2 periods = 20) plus the previous 6,426 together (6,446).
