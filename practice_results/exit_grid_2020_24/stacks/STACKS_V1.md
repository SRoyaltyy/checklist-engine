# STACKS_V1 — pre-registered stacks (written before any stack result was computed)
Practice 2020–24 only (no bar after 2024-12-31 read). Same panel (story_q/panel.parquet, date = D), drop_list_v2, entry open D,
exit mechanics of EXIT_RULE_V1 (stop checked first, same-day touch = stop, gaps fill at open, else close of day H), fees 0.6% round trip.

## Building blocks (all from bars <= t, t = ticker's bar before D)
- Q5 = sq5_big_red_recent; Q7 = sq7_lowerbb_reclaim (panel columns).
- BIGMOVE (James's loser set) = any of:
  1. 20-day close return (C[t]/C[t-20]-1) in the top decile of that day's post-filter panel, or > 20%;
  2. ATR14/C[t] >= 20% (Wilder TR, 14-bar simple mean);
  3. MFI14 > 80;
  4. running ahead of SPY: 20-day return minus SPY 20-day return >= +10 percentage points.
     Sector leg NOT computed (no point-in-time sector history/sector-ETF panel on the box) -> SPY only.
- NO_BIGMOVE = not BIGMOVE (rows with missing inputs count as BIGMOVE = unknown -> excluded).
- NEAR26 = C[t] >= 0.95 x max(High[t-125..t]) (126 bars, needs 126 bars of history).

## Stacks
- S1 = Q5 & NO_BIGMOVE
- S2 = Q7 & NO_BIGMOVE
- S3 = Q5 & NO_BIGMOVE & NEAR26
- S4 = Q7 & NO_BIGMOVE & NEAR26
- S5 = (Q5 | Q7) & NO_BIGMOVE & NEAR26

## Grid
X in {10,15,20}%, stop in {none, X/2}, H = 1..21. Per cell: n, win%, mean, median, excess vs ALL same D same rule, date-clustered bootstrap 95% CI (500).
Also per stack: rate of high >= entry x 1.10 on any of days 1..21, vs ALL.
BH q=0.05 over all stack cells + all 4,536 exit_grid_v1 cells together. Discover 2020–22, confirm 2023–24.
