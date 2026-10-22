# HISTORY10Y_RESULTS_V1 — 10-year history rows (2020-24 only; 2025-26 never opened)
Rules: history10y/HISTORY10Y_V1.md (committed before this run, commit fe69f82). SURVIVORS ONLY: delisted names absent, win rates read high.
- Population: 2,408,833 buyable stock-days (drop_list_v2, 21 forward bars), 2020-01..2024-12. 17.9% had no Stooq file match (NO_DATA, not tested). Stooq rows read only up to 2024-12-31; features use closes before day D only.
- Tests: 25 buckets x 2 periods x 2 exits = 100 new; BH family cumulative 6,802 (6,702 prior + 100).
- Pass bar (both periods, per exit): win > 55% after 0.6% fees, n >= 30, q < 0.05, excess > 0.

## Result: 0 of 25 buckets pass on either exit.
Closest (exit A = +20% target / day-15 close):
| bucket | 2020-22 excess / win / n / q | 2023-24 excess / win / n / q |
|---|---|---|
| H10_NEAR_LOW YES (within 10% of 10y low) | +1.79% / 59.2% / 4,138 / <0.001 | +0.95% / 54.8% / 9,227 / <0.001 |
| H10_DD DD80P (80%+ below 10y high) | +1.63% / 55.7% / 51,073 / <0.001 | +0.54% / 50.3% / 43,107 / 0.005 |
| H10_ABOVE_5YAVG NO | +0.80% / 55.7% / 283,119 / <0.001 | 0.00% / 49.8% / 273,683 / 0.996 |
| H10_ABOVE_10YAVG NO | +0.96% / 55.3% / 181,246 / <0.001 | -0.04% / 49.6% / 160,896 / 0.571 |
Near 10y high, years since high, stock age: no stable edge (sign flips between periods). Exit B (10-day hold) never above 54.6% win.
Pattern: "beaten-down / near 10-year low" beats average in both periods but the win rate falls below 55% in 2023-24, and this is exactly the group survivors-only data flatters most (beaten-down names that went on to delist are missing).
Full table: history10y_results_v1.csv. Code: h10_feats.py, h10_run.py, build_stooq.py.
