# TRAJECTORY MCAP100 CLEAN results v1 — F1 DIV3_PDOWN, $100M filter, cleaned share counts

Rule: MCAP100_CLEAN_ADDENDUM_V1.md (commit a9a1d2a, committed before these results). 2020–24 only; 2025–26 not opened. Script mcap100_clean_run.py. The trades and returns are identical to MCAP100 v1; only the share counts changed. Fees 0.6% round trip. Exit A. Bar: win >55%, n >=30, excess >0, in both periods.

Cleaning: 787 of 139,348 SEC rows removed (394 tickers). Of these, 304 were <=0, 69 were >1e11, and 724 were >50x off the ticker median (a row can hit more than one test). No trade had an implied market cap above $5T.
Trades affected: 2020–22, 9 counts changed (5 became missing); 2023–24, 2 changed (2 became missing).
No count: 397/1121 (2020–22) and 215/728 (2023–24). Known <$100M: 29 and 49.

| Version | Period | Trades | Win A | Excess A | 95% CI | p | Pass |
|---|---|---|---|---|---|---|---|
| MAIN (keep no-count) | 2020–22 | 1092 | 58.2% | +1.59% | +0.45/+2.66 | 0.008 | yes |
| MAIN (keep no-count) | 2023–24 | 679 | 57.9% | +1.28% | −0.02/+2.47 | 0.039 | yes |
| WARNING (drop no-count) | 2020–22 | 695 | 56.7% | +1.03% | −0.15/+2.37 | 0.10 | yes |
| WARNING (drop no-count) | 2023–24 | 464 | 54.7% | +1.15% | −0.32/+2.59 | 0.14 | **no (win <55%)** |

Note that the p values use a normal approximation on the bootstrap standard error, and the CI is the bootstrap percentile range. For MAIN 2023–24 the two disagree slightly at the edge.
