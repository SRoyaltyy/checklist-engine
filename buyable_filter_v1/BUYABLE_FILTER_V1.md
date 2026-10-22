# BUYABLE_FILTER_V1 (2020-01-01 .. 2024-12-31)
Built: 2026-10-22 ~22:05 HKT by Trading Bot Taskforce. Prices: universe_2020_survivors.parquet (fb9bbe69), bars before D only. No 2025-26 data.
Sources: fullscan research/hot_n4_clean_v4/PREREG.md §6; src/gainer_asof.py _liquid_tape; SPAC rule set by Manager Bot in War room.

Drop stock-day (ticker, D) if any:
1. 20-day mean volume over D-20..D-1 < 500,000 shares (or <20 bars of history)
2. volume on D-1 is 0 or missing
3. ticker ends -U, -WS or -R
4. close in [$9.50, $10.50] on >= 90% of the 60 bars before D
5. Market cap >= $100M: NOT YET APPLIED (waiting on James's SEC share-count file)
6. ETF exclusion: NOT YET APPLIED (the price file has no ETF flag; to be added with an ETF list)

Counts (of 8,768,826 stock-days): rule1 6,204,629; rule2 162,303; rule3 0 (no such tickers in survivors file); rule4 48,472; total dropped 6,206,955.
DCGO 2021-09-27: dropped (rules 1 and 4).
sha256 buyable_filter.py ffec7c4aeee5f0629bbde0173ad950ba6b634e727121f800c4ade4ff38465057
sha256 drop_list.csv 3c1ed970286e7998574748391604033c65d330efcfd9a82a49d47788b745a5a2
