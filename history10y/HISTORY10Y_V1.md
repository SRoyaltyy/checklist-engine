# HISTORY10Y_V1 — pre-registration (written before any results)
Registered 2026-10-23 HKT, before running. Owner: Trading Bot Taskforce. Master-list row: "10-year history".

## Data
- Look-back source: Stooq free daily file d_us_txt.zip (stocks folders only, ETFs excluded), close only, rows dated <= 2024-12-31 read; 2025-26 never loaded. Stooq closes are split+dividend adjusted, so all features use Stooq alone (one convention; ratios within a series are unaffected by constant rescaling).
- Features at decision day D use only Stooq closes strictly before D (last close = D-1). Pre-2020 rows feed look-backs only.
- Outcomes: universe_2020_survivors.parquet (split-only), entry at open of D, exactly as trajectory/traj_run.py.
- Population: every buyable stock-day in story_q panel 2020-01-01..2024-12-31 after drop_list_v2, with 21 forward bars. SURVIVORS ONLY (delisted names absent) -> win rates read high.
- Ticker coverage = universe tickers found in Stooq; names with no Stooq file fall in NO_DATA and are not tested.

## Features (yes/no or fixed labels only; 10y window = last 2520 trading closes before D)
| id | labels |
|---|---|
| H10_NEAR_HIGH | YES if close(D-1) >= 0.95 x max(10y window); NO; SHORT (<2520 closes) |
| H10_NEAR_LOW | YES if close(D-1) <= 1.10 x min(10y window); NO; SHORT |
| H10_DD | drawdown from 10y high: DD0_5, DD5_20, DD20_50, DD50_80, DD80P; SHORT |
| H10_YRS_SINCE_HIGH | Y_LT1, Y1_3, Y3P (trading days/252 since 10y max); SHORT |
| H10_ABOVE_5YAVG | YES/NO close(D-1) > mean of last 1260 closes; SHORT (<1260) |
| H10_ABOVE_10YAVG | YES/NO vs mean of last 2520 closes; SHORT |
| H10_AGE | AGE_LT5, AGE5_10, AGE10P (years since first Stooq close, 252-day years) |
SHORT buckets are reported but are themselves tests.

## Exits / fees / stats (same as traj_run.py)
- Exit A = EXIT_RULE_V1: +20% target, no stop, else close day 15. Exit B: 10-day hold (close day 10).
- Fees 0.30% each way (0.6% round trip). Excess = return minus same-day mean of all population trades.
- Periods: discover 2020-22, check 2023-24. Date-clustered bootstrap (500 draws, seed 13) 95% CI and p.
- BH-FDR cumulative: continues from 6,702 prior tests (all earlier p-values pooled with these).
- PASS (per bucket per exit) requires on BOTH periods: win > 55% after fees, n >= 30, BH q < 0.05, excess > 0.
