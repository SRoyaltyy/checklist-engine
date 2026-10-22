# HALTS_V1 — pre-registration (written before any results)
Registered 2026-10-23 ~02:10 HKT, before any returns were joined. Owner: Trading Bot Taskforce. Master-list row: "trading halts".

## Data
- Tags: New Bot nb_halts_v1.tar.gz (Drive 12wDfBWSEmZqYL_1_XbEs1Jxz37J9rnNo, sha256 b5c7a836fb3694b81c706e1285d17bb72a56b27d537fe7732b113ea37b38afa1, verified), manifest Drive 1z057K44pwwlDhwzjxu8JSVppoPGtK85l. Only nb_halt_tags_2020_2024.csv.gz is used (sha256 041ed6d9…a90b, matches manifest). The sealed/ 2025-26 files were excluded at extraction and never opened.
- Source: Nasdaq Trader daily halt feed (all US exchanges). Leak rule (New Bot): tag for day D counts only halts dated strictly before D.
- Outcomes: universe_2020_survivors.parquet, entry at open of D, exactly as history10y/h10_run.py and trajectory/traj_run.py.
- Population: every buyable stock-day in story_q panel 2020-01-31..2024-12-31 (tags start 2020-01-31 after 20-session warm-up) after drop_list_v2, with 21 forward bars, joined to a tag row on (ticker, date). Stock-days with no tag row are dropped (not tested). SURVIVORS ONLY -> win rates read high.

## Tags (yes/no or fixed bins only)
| id | buckets |
|---|---|
| halt_1d | YES / NO |
| halt_5d | YES / NO |
| halt_20d | YES / NO |
| ludp_5d (volatility pause, last 5 sessions) | YES / NO |
| news_t123_20d (news halt T1/T2/T3, last 20 sessions) | YES / NO |
| halt_count_20d | C0 (0), C1 (1), C2P (2 or more) — bins fixed now |
t1_20d is NOT tested (feed relabels news halts as T3; ~always 0). SEC suspensions are not in the feed (row stays blocked). Every bucket, including NO and C0, is a test.

## Exits / fees / stats (same as h10_run.py)
- Exit A = EXIT_RULE_V1: +20% target, no stop, else close day 15. Exit B: 10-day hold (close day 10).
- Fees 0.30% each way (0.6% round trip). Excess = return minus same-day mean of all population trades.
- Periods: discover 2020-22, check 2023-24. Date-clustered bootstrap (500 draws, seed 13) 95% CI and p.
- New tests: 13 buckets x 2 periods x 2 exits = 52 p-values.
- BH-FDR cumulative: prior family = 10,060 tests (James's latest count). All prior p-values available on the box (score/stacks/exit_grid/trajectory/history10y files) are pooled; the rest of the 10,060 not on the box are entered as p=1 (conservative). Family = 10,060 + 52 = 10,112.
- PASS (per bucket per exit) requires on BOTH periods: win > 55% after fees, n >= 30, BH q < 0.05, excess > 0.
