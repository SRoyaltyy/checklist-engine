# TRAJECTORY MCAP100 results v1 — F1 DIV3_PDOWN with $100M market-cap filter

Rule: MCAP100_ADDENDUM_V1.md (commit 4c7f216, written before these results). Data 2020–24 only; 2025–26 not opened. Script mcap100_run.py (copy of frozen traj_run.py plus an appended filter block). Locked numbers reproduce exactly. Fees 0.6% round trip (30bp per side). Exit A = +20% take-profit or day-15 close. Bar: exit A, win >55%, n >=30, excess >0, in both periods.

Trades with no SEC share count filed before entry: 392 of 1121 (2020–22), 213 of 728 (2023–24). Trades with a count and mcap < $100M dropped: 37 (2020–22), 51 (2023–24).

| Variant | Period | Trades | Win A | Excess A | 95% CI | p | Pass |
|---|---|---|---|---|---|---|---|
| Locked v1 | 2020–22 | 1121 | 58.4% | +1.76% | +0.55/+2.90 | 0.004 | yes |
| Locked v1 | 2023–24 | 728 | 58.1% | +1.41% | +0.27/+2.49 | 0.017 | yes |
| MCAP100, no-count dropped | 2020–22 | 692 | 56.8% | +1.10% | −0.15/+2.26 | 0.069 | yes |
| MCAP100, no-count dropped | 2023–24 | 464 | 54.7% | +1.15% | −0.22/+2.64 | 0.14 | **no (win <55%)** |
| MCAP100, no-count kept | 2020–22 | 1084 | 58.4% | +1.67% | +0.38/+2.80 | 0.005 | yes |
| MCAP100, no-count kept | 2023–24 | 677 | 58.1% | +1.36% | +0.13/+2.43 | 0.016 | yes |

Verdict: passes if trades with no share count are kept; fails 2023–24 (54.7% wins) if they are dropped, and excess is no longer significant in either period. Exit B in trajectory_mcap100_results_v1.csv. Per-trade data: trajectory_mcap100_trades_v1.csv.
