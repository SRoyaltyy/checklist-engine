# UNTESTED_V1 — rules (pre-registered; committed BEFORE any result was computed)
PRACTICE 2020–24 only, **HINT, survivors-only**. No bar after 2024-12-31 is read (filtered on load + asserted). 2025–26 stays sealed.
Price file: /workspace/pricehist/universe_2020_survivors.parquet, sha fb9bbe69…ef337 (asserted). qa/redundancy/feats.py not used.

## Scope
Grok Bot coverage audit (Drive 1wGJORBF… master_coverage.csv, 1fVTW-AG… map_coverage.csv), status = BUILT_NOT_TESTED:
87 master.csv ideas + 1,581 map v5.1 rows. Answers are the existing engine answers already stored for the look-alike
build (tmp_laf A_JG/NB/TR/SHARED/MPV.npz on the 147,986 ledger cells, code 2 = YES, 1 = NO, 0 = NR; every answer at D uses bars before D).
Each answer column is one test. A row id matches its column by exact id, else by base id (text before "|").
A row with no answer column, or with < 30 YES trades in 2020–22 after filters, is reported NOT COMPUTABLE / TOO FEW with the reason.
Master ideas also present in map v5.1 share the same column and are counted once.

## Trades and controls
- Trade = (ticker, D) ledger cell with answer YES, entry at open D.
- Untradeable removed from BOTH trades and controls: Taskforce buyable filter drop_list_v2 (liquidity, zero volume, SPAC rules).
  Minimum market cap ($100M) is NOT applied: no point-in-time share-count file exists on the box (same gap as BUYABLE_FILTER_V1 rule 5). Flagged.
- Control = mean return of all buyable stock-days in story_q/panel.parquet on the same date (the "average buyable stock").
- Labels, 30bp/side (0.6% round trip): (B) 10-day: open D → close D+9 (10 sessions); (A) EXIT_RULE_V1: +20% take-profit
  (gap fills at open), no stop, else close of day 15. Same code as trajectory/traj_run.py. Needs bars D..D+20 ≤ 2024-12-31.

## Pass bar (per label; a row passes if it passes under either label, both reported)
Discover 2020–22 AND confirm 2023–24, each: n ≥ 30 trades, win rate (net return > 0) > 55%, mean excess vs control > 0.
Plus discover-period BH q < 0.10 on the excess (date-clustered bootstrap, 500 draws, seed 13) over the GLOBAL family:
6,802 prior tests + 2 × (tests here). Prior p-values not all on box → treated as p = 1 (conservative).
Nothing passes as a "keep"; any pass is a live-day HINT only.
