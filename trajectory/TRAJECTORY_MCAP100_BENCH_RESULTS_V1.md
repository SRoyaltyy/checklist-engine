# TRAJECTORY MCAP100 BENCH results v1 — F1 DIV3_PDOWN, $100M filter on trades AND benchmark

Rule: MCAP100_BENCH_ADDENDUM_V1.md (commit b399463, committed before these results). 2020–24 only; 2025–26 not opened. Script mcap100_bench_run.py. Trades, returns and cleaned share counts identical to MCAP100 CLEAN v1; only the same-day average-stock benchmark changed. Fees 0.6% round trip. Bar: win >55%, n >=30, excess >0, both periods.

Reproduction check: with the benchmark filter OFF the script reproduces trajectory_mcap100_clean_results_v1.csv (672d437e) byte-for-byte (sha256 8087dd7c…5c26); max |excess diff| 2e-16.
Benchmark rows (2020–24 universe): OFF 2,408,833; MAIN 2,371,498; WARNING 1,569,869.

| Version | Period | Trades | Win A | Avg ret A | Bench filt / old | Excess A (old) | 95% CI | p | Pass |
|---|---|---|---|---|---|---|---|---|---|
| MAIN | 2020–22 | 1092 | 58.2% | +3.52% | +1.82% / +1.94% | +1.71% (+1.59%) | +0.56/+2.75 | 0.004 | yes |
| MAIN | 2023–24 | 679 | 57.9% | +2.89% | +1.56% / +1.61% | +1.33% (+1.28%) | +0.03/+2.52 | 0.032 | yes |
| WARNING | 2020–22 | 695 | 56.7% | +2.98% | +2.01% / +1.94% | +0.97% (+1.03%) | −0.19/+2.26 | 0.12 | yes |
| WARNING | 2023–24 | 464 | 54.7% | +2.68% | +1.44% / +1.53% | +1.24% (+1.15%) | −0.20/+2.70 | 0.11 | **no (win <55%)** |

10-day hold (B), win / avg / excess: MAIN 54.2% / +2.44% / +1.29% and 52.0% / +2.76% / +1.81%; WARNING 52.8% / +1.99% / +0.74% and 50.9% / +2.49% / +1.73%. All below 55% win.

BH: re-score adds 0 tests (count ~13,851). Not passed: a BH q <= 0.05 at N=13,851 would need p <= 0.05·k/N; MAIN 2023–24 p=0.032 would need rank k >= ~8,860, MAIN 2020–22 p=0.004 needs k >= ~1,140. Treated as a hint, not a BH pass.
