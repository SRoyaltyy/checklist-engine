# MCAP100 addendum v1 — $100M market-cap buyable filter for DIV3_PDOWN (F1)

Written and committed BEFORE any filtered result is computed. Frozen files (TRAJECTORY_V1.md, TRAJECTORY_RESULTS_V1.md, trajectory_results_v1.csv, traj_run.py) are not edited.

Scope: only the locked pattern F1 / DIV3 / DIV3_PDOWN, exactly as in traj_run.py (same universe, drop_list_v2 buyable filter, entry at the run-start day's open, same exits A (+20% take-profit or day-15 close) and B (day-10 close), same 0.6% round-trip fee = 30bp per side, same excess vs the same-day mean of all buyable stocks). Data 2020-01-01..2024-12-31 only. 2025-26 is not opened.

Market-cap rule: for a trade entered on day D, mcap = close on the stock's prior trading bar (D-1) x the most recent SEC dei:EntityCommonStockSharesOutstanding value whose `filed` date is strictly before D (ties on filed date: latest `end`, then last row). Source: sec_shares_out_filed_le_2024.parquet in New Bot's nb_tags_v2.tar.gz (Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4, sha256 573fcea379b9525005d007ed1dd6d255b1dfcc6493039b4284aec1278a86ffb3). Matched by ticker. No value cleaning.

Trade kept if mcap >= $100,000,000. Trades with no share count filed before D are counted and reported; results are shown twice: (EXCL) no-share-count trades dropped, (KEEP) no-share-count trades kept.

The excess benchmark ("avg stock") stays the unfiltered same-day buyable mean, as locked.

Pass bar (unchanged), exit A, required in BOTH 2020-22 and 2023-24: win rate > 55%, trades >= 30, mean excess > 0. Exit B reported for information.
