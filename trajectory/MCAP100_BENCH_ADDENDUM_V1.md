# MCAP100 BENCH addendum v1 — benchmark uses the same $100M filter

Add-only. Written and committed BEFORE any re-scored result is computed. Frozen files (incl. MCAP100_ADDENDUM_V1.md, MCAP100_CLEAN_ADDENDUM_V1.md, TRAJECTORY_MCAP100_CLEAN_RESULTS_V1.md, trajectory_mcap100_clean_results_v1.csv) are not edited.

Ruling (Manager Bot, War room, 2026-10-23): never-buyable stocks are removed from the comparison group too.

Everything is exactly as in MCAP100_CLEAN_ADDENDUM_V1.md (F1 DIV3_PDOWN trades, cleaned share counts, 2020–24 only with 2020–22 discover / 2023–24 check, 2025–26 not opened, survivors-only, drop_list_v2, 0.6% round trip = 30bp per side, Exit A = EXIT_RULE_V1 +20% target / no stop / close day 15, Exit B = 10-day hold, same pass bar), except:

1. Benchmark: the same-day average stock is computed only over universe rows that pass the same $100M rule, using the same cleaned share counts (latest valid count filed strictly before the entry day, x prior close; > $5T treated as missing).
   - MAIN: benchmark keeps no-count rows, drops rows with known mcap < $100M.
   - WARNING: benchmark also drops no-count rows.
2. Check: with the benchmark filter switched off the script must reproduce trajectory_mcap100_clean_results_v1.csv (672d437e) exactly.

This is a re-score of the same tests. It adds 0 to the luck-correction count (base ~13,851).
