# Look-alike win/loss mining — PRACTICE 2020–24, **HINT only** (not evidence; 2025–26 sealed until the lock)

Prices `universe_2020_survivors.parquet` sha `fb9bbe69…ef337` (verified). Rows 2020-01-01..2024-12-31 only (asserted). Every feature uses bars < D; entry open D, exit open D+h, net of 30bp/side.
Win = stock net return beats the same-day mean of tradable matched controls (same base filter, rule = NO). Deterministic: no sampling, no seed needed (ties broken by ticker).

See `LOOKBACK_GRID.md` (fixed lookback grid, recorded before computing).

## Tradability filter — Taskforce `buyable_filter_v1/drop_list_v2.csv.gz` (sha 5a6cb756…63239)

Fullscan PREREG §6 liquid gate (avg vol ≥ 500k, vol > 0, SPAC rule) as built by Taskforce. **ETF rule PARTIAL** (only SPY/QQQ/IWM + 11 sector SPDRs). **Market cap ≥ $100M NOT YET APPLIED** (awaits SEC share counts).
Applied to cases AND controls before any scoring, pairing or charting. Drop-list rows dated > 2024 discarded on read. Earlier provisional run with own filter (incl. mcap proxy) superseded.

### Exclusions (stock-days removed; a day can fail several rules)

| setup | n before | n after | removed | fail_taskforce_drop_v2 |
|---|---|---|---|---|
| chartpass_all6 | 147,986 | 44,239 | 103,747 | 103,747 |
| q5_in_all6 | 48,122 | 15,127 | 32,995 | 32,995 |
| q7_in_all6 | 23,191 | 6,610 | 16,581 | 16,581 |
| q8_in_all6 | 17,437 | 5,269 | 12,168 | 12,168 |
| all panel rows (controls pool) | 8,244,720 | 2,459,601 | 5,785,119 | 5,785,119 |

### Re-score of the 4 rules: before vs after the filter (raw = mean net%; exc = mean excess vs same-day all%)

| rule | h | n before | win% before | raw before | exc before | n after | win% after | raw after | exc after |
|---|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 5 | 147,254 | 41.9 | 0.01 | +0.18 | 44,026 | 44.3 | 0.67 | +0.77 |
| chartpass_all6 | 10 | 145,751 | 43.3 | 0.44 | +0.29 | 43,517 | 45.9 | 1.29 | +0.98 |
| chartpass_all6 | 21 | 144,091 | 43.1 | 0.88 | +0.30 | 43,024 | 45.8 | 2.07 | +0.97 |
| q5_in_all6 | 5 | 47,915 | 43.1 | 0.58 | +0.73 | 15,092 | 45.9 | 2.10 | +2.09 |
| q5_in_all6 | 10 | 47,227 | 44.3 | 1.12 | +0.96 | 14,889 | 47.4 | 2.82 | +2.40 |
| q5_in_all6 | 21 | 46,704 | 44.5 | 1.52 | +0.96 | 14,741 | 47.1 | 3.18 | +2.06 |
| q7_in_all6 | 5 | 23,053 | 42.4 | 0.84 | +0.80 | 6,572 | 45.5 | 3.92 | +3.89 |
| q7_in_all6 | 10 | 22,880 | 44.8 | 1.63 | +1.20 | 6,531 | 48.3 | 4.99 | +4.38 |
| q7_in_all6 | 21 | 22,725 | 45.1 | 1.95 | +1.04 | 6,496 | 48.3 | 5.41 | +3.86 |
| q8_in_all6 | 5 | 17,302 | 40.7 | -0.33 | -0.36 | 5,229 | 43.2 | 0.25 | +0.25 |
| q8_in_all6 | 10 | 17,212 | 42.8 | 0.06 | -0.33 | 5,195 | 45.9 | 0.88 | +0.46 |
| q8_in_all6 | 21 | 17,055 | 43.2 | 0.35 | -0.47 | 5,130 | 46.3 | 1.74 | +0.31 |

## Pairs (h=10d primary): symmetric 1:1 winner–loser pairs, same setup and same date, fixed ticker-hash order, no reuse (audit fix; old winner-anchored pairing retracted)

| setup | tradable events | winners | pairs | median items differing | casebook pairs |
|---|---|---|---|---|---|
| chartpass_all6 | 43,517 | 19,810 | 17,128 | 1706 | 27 |
| q5_in_all6 | 14,889 | 7,350 | 4,772 | 1632 | 11 |
| q7_in_all6 | 6,531 | 3,178 | 1,807 | 1582 | 6 |
| q8_in_all6 | 5,194 | 2,403 | 1,421 | 1729 | 9 |

## Per sentence: how often it is YES (top tercile for NEW/grid rows) among winners vs losers (h=10d, tradable setup days; global BH over all items × setups) — `sentence_freq_win_vs_loss.csv.gz`

Tested: 57,490; q<0.1: 21,921. Top 12 per setup (TR `|N` duplicates hidden):

| setup | sentence | source | YES % winners | YES % losers | n win / n lose | q (global BH) |
|---|---|---|---|---|---|---|
| chartpass_all6 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 39.0 | 26.4 | 19,022.0 / 22,495.0 | 5.5e-159 |
| chartpass_all6 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 35.5 | 26.9 | 19,810.0 / 23,707.0 | 5.5e-79 |
| chartpass_all6 | ph2_gapdn5_20_ge1 | path bank v2 question | 24.3 | 29.7 | 19,810.0 / 23,707.0 | 4.3e-32 |
| chartpass_all6 | ph2_gapdn5_20_ge2 | path bank v2 question | 8.7 | 12.4 | 19,810.0 / 23,707.0 | 5.6e-32 |
| chartpass_all6 | ph2_gapdn5_25_ge2 | path bank v2 question | 10.1 | 14.1 | 19,810.0 / 23,707.0 | 6.1e-32 |
| chartpass_all6 | ph2_gapdn5_15_ge1 | path bank v2 question | 22.3 | 27.5 | 19,810.0 / 23,707.0 | 6.1e-32 |
| chartpass_all6 | ph2_gapdn5_10_ge2 | path bank v2 question | 4.6 | 7.5 | 19,810.0 / 23,707.0 | 2.7e-31 |
| chartpass_all6 | ph2_gapdn5_15_ge2 | path bank v2 question | 7.4 | 10.8 | 19,810.0 / 23,707.0 | 4.4e-31 |
| chartpass_all6 | ph2_natr_40_ge0p07 | path bank v2 question | 25.1 | 30.4 | 19,810.0 / 23,707.0 | 1.1e-30 |
| chartpass_all6 | ph2_maxup1d_30_ge0p3 | path bank v2 question | 7.4 | 10.8 | 19,810.0 / 23,707.0 | 2.8e-30 |
| chartpass_all6 | ph2_gapdn5_30_ge2 | path bank v2 question | 11.8 | 15.8 | 19,810.0 / 23,707.0 | 5.6e-30 |
| chartpass_all6 | ph2_gapdn5_10_ge1 | path bank v2 question | 17.7 | 22.4 | 19,810.0 / 23,707.0 | 1.6e-29 |
| q5_in_all6 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 42.7 | 32.9 | 7,350.0 / 7,539.0 | 4.8e-31 |
| q5_in_all6 | MAC-JA-1897-BUT | sheet:SHARED (market rows) | 12.0 | 6.5 | 7,350.0 / 7,539.0 | 1.7e-28 |
| q5_in_all6 | MKT-JA-335 | sheet:SHARED (market rows) | 18.3 | 26.4 | 7,350.0 / 7,539.0 | 1.8e-28 |
| q5_in_all6 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 43.2 | 33.6 | 7,038.0 / 7,236.0 | 1.9e-28 |
| q5_in_all6 | SEC-JA-663 | sheet:SHARED (market rows) | 4.8 | 9.4 | 7,350.0 / 7,539.0 | 1.3e-25 |
| q5_in_all6 | MKT-JA-1872 | sheet:SHARED (market rows) | 37.3 | 46.0 | 7,350.0 / 7,539.0 | 2.1e-24 |
| q5_in_all6 | MAC-JA-1998 | sheet:SHARED (market rows) | 9.9 | 16.4 | 5,753.0 / 6,057.0 | 1.2e-22 |
| q5_in_all6 | MAC-JA-1998-BUT | sheet:SHARED (market rows) | 9.9 | 16.4 | 5,753.0 / 6,057.0 | 1.2e-22 |
| q5_in_all6 | MAC-JA-286 | sheet:SHARED (market rows) | 37.0 | 45.3 | 7,350.0 / 7,539.0 | 2e-22 |
| q5_in_all6 | MAC-JA-1897 | sheet:SHARED (market rows) | 9.9 | 5.6 | 7,350.0 / 7,539.0 | 7.2e-21 |
| q5_in_all6 | MKT-JA-342 | sheet:SHARED (market rows) | 4.8 | 8.7 | 7,350.0 / 7,539.0 | 1.2e-18 |
| q5_in_all6 | MAC-JA-1012 | sheet:SHARED (market rows) | 2.1 | 0.4 | 7,350.0 / 7,539.0 | 1e-17 |
| q7_in_all6 | MAC-JA-2492 | sheet:SHARED (market rows) | 76.0 | 64.5 | 2,495.0 / 2,713.0 | 1.7e-17 |
| q7_in_all6 | MAC-JA-2486 | sheet:SHARED (market rows) | 76.0 | 64.5 | 2,495.0 / 2,713.0 | 1.7e-17 |
| q7_in_all6 | MKT-JA-767 | sheet:SHARED (market rows) | 22.5 | 13.2 | 2,495.0 / 2,713.0 | 1.9e-16 |
| q7_in_all6 | MKT-JA-767-BUT | sheet:SHARED (market rows) | 22.5 | 13.2 | 2,495.0 / 2,713.0 | 1.9e-16 |
| q7_in_all6 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 37.9 | 27.9 | 3,178.0 / 3,353.0 | 5.5e-16 |
| q7_in_all6 | FV-GB-2346 | sheet:SHARED (market rows) | 18.2 | 10.3 | 2,495.0 / 2,713.0 | 1.6e-14 |
| q7_in_all6 | SEC-JA-663 | sheet:SHARED (market rows) | 2.6 | 7.0 | 3,178.0 / 3,353.0 | 2e-14 |
| q7_in_all6 | MAC-JA-1998-BUT | sheet:SHARED (market rows) | 7.9 | 15.1 | 2,495.0 / 2,713.0 | 8.8e-14 |
| q7_in_all6 | MAC-JA-1998 | sheet:SHARED (market rows) | 7.9 | 15.1 | 2,495.0 / 2,713.0 | 8.8e-14 |
| q7_in_all6 | MAC-JA-2448 | sheet:SHARED (market rows) | 39.9 | 29.5 | 2,495.0 / 2,713.0 | 3.1e-13 |
| q7_in_all6 | MAC-JA-2436 | sheet:SHARED (market rows) | 39.9 | 29.5 | 2,495.0 / 2,713.0 | 3.1e-13 |
| q7_in_all6 | MAC-JA-2442 | sheet:SHARED (market rows) | 39.9 | 29.5 | 2,495.0 / 2,713.0 | 3.1e-13 |
| q8_in_all6 | ph2_distl_20_le0p3 | path bank v2 question | 90.0 | 82.5 | 2,403.0 / 2,791.0 | 6.4e-13 |
| q8_in_all6 | MKT-JA-784 | sheet:SHARED (market rows) | 9.9 | 3.9 | 1,932.0 / 2,275.0 | 7e-13 |
| q8_in_all6 | MKT-JA-784-BUT | sheet:SHARED (market rows) | 9.9 | 3.9 | 1,932.0 / 2,275.0 | 7e-13 |
| q8_in_all6 | MKT-JA-370 | sheet:SHARED (market rows) | 19.1 | 11.6 | 2,403.0 / 2,791.0 | 4.8e-12 |
| q8_in_all6 | ph2_distl_15_le0p3 | path bank v2 question | 93.1 | 86.7 | 2,403.0 / 2,791.0 | 5e-12 |
| q8_in_all6 | ph2_maxdd_25_ge0p3 | path bank v2 question | 9.3 | 16.3 | 2,403.0 / 2,791.0 | 5.9e-12 |
| q8_in_all6 | MAC-JA-1796-BUT | sheet:SHARED (market rows) | 13.9 | 7.6 | 2,403.0 / 2,791.0 | 7.2e-12 |
| q8_in_all6 | ph2_distl_10_le0p15 | path bank v2 question | 85.0 | 76.9 | 2,403.0 / 2,791.0 | 9.8e-12 |
| q8_in_all6 | PRC-TR-01969-C|10 | sheet:TR (Theme Radar) | 15.2 | 23.3 | 2,403.0 / 2,791.0 | 1.3e-11 |
| q8_in_all6 | ph2_voltrend_50_ge3p0 | path bank v2 question | 8.7 | 15.4 | 2,403.0 / 2,791.0 | 1.3e-11 |
| q8_in_all6 | ph2_maxdn1d_20_ge0p15 | path bank v2 question | 11.5 | 18.9 | 2,403.0 / 2,791.0 | 1.6e-11 |
| q8_in_all6 | ph2_distl_25_le0p5 | path bank v2 question | 93.6 | 87.6 | 2,403.0 / 2,791.0 | 1.7e-11 |

## Honesty split (pair sign test): discover on 2020–22 pairs, confirm on 2023–24 pairs

Tested in discovery (n_differ ≥ 30): 28,562. Discovered (q<0.1 BH, |favour−50| > 5pp): 3,670. **Still hold on 2023–24** (same direction, >5pp, n ≥ 30, q<0.1 BH over discovered set): **1,498**.

| setup | item | source | disc n | disc winner-favour % | conf n | conf winner-favour % | q conf |
|---|---|---|---|---|---|---|---|
| chartpass_all6 | ph2_maxup1d_30_ge0p3 | path bank v2 question | 1527 | 43.5 | 1165 | 37.1 | 1.6e-15 |
| chartpass_all6 | ph2_maxup1d_25_ge0p3 | path bank v2 question | 1505 | 43.4 | 1160 | 37.2 | 1.6e-15 |
| chartpass_all6 | ph2_maxup1d_15_ge0p3 | path bank v2 question | 1258 | 43.6 | 1013 | 36.3 | 1.6e-15 |
| chartpass_all6 | ph2_gapdn5_50_ge5 | path bank v2 question | 962 | 39.3 | 546 | 31.7 | 3.2e-15 |
| chartpass_all6 | ph2_maxup1d_20_ge0p3 | path bank v2 question | 1443 | 43.3 | 1139 | 37.4 | 5.1e-15 |
| chartpass_all6 | ph2_maxup1d_50_ge0p3 | path bank v2 question | 1699 | 44.3 | 1278 | 38.1 | 5.1e-15 |
| chartpass_all6 | ph2_maxup1d_60_ge0p3 | path bank v2 question | 1821 | 45.0 | 1363 | 38.5 | 5.5e-15 |
| chartpass_all6 | ph2_voltrend_50_ge3p0 | path bank v2 question | 1454 | 42.5 | 1202 | 37.9 | 7.6e-15 |
| chartpass_all6 | ph2_maxup1d_40_ge0p3 | path bank v2 question | 1599 | 44.0 | 1213 | 38.3 | 5.2e-14 |
| chartpass_all6 | ph2_gapdn5_60_ge5 | path bank v2 question | 1188 | 40.5 | 677 | 34.7 | 2.7e-13 |
| chartpass_all6 | ph2_voltrend_60_ge3p0 | path bank v2 question | 1420 | 41.8 | 1123 | 38.4 | 1.1e-12 |
| chartpass_all6 | ph2_maxdn1d_20_ge0p05 | path bank v2 question | 4144 | 44.5 | 3798 | 43.9 | 6.4e-12 |
| q5_in_all6 | ph2_volrel_10_ge3p0 | path bank v2 question | 270 | 42.6 | 222 | 31.5 | 3.5e-07 |
| q5_in_all6 | ph2_gapdn5_25_ge2 | path bank v2 question | 476 | 44.5 | 287 | 34.1 | 7.1e-07 |
| q5_in_all6 | ph2_gapup5_10_ge2 | path bank v2 question | 221 | 40.3 | 157 | 29.9 | 3.5e-06 |
| q5_in_all6 | ph2_maxup1d_25_ge0p3 | path bank v2 question | 324 | 42.3 | 247 | 34.4 | 6.2e-06 |
| q5_in_all6 | ph2_maxup1d_30_ge0p3 | path bank v2 question | 324 | 42.0 | 247 | 34.4 | 6.2e-06 |
| q5_in_all6 | ph2_maxdn1d_30_ge0p05 | path bank v2 question | 1132 | 42.8 | 988 | 42.3 | 8.1e-06 |
| q5_in_all6 | ph2_maxdn1d_40_ge0p05 | path bank v2 question | 1038 | 43.4 | 953 | 42.2 | 8.2e-06 |
| q5_in_all6 | ph2_maxdn1d_50_ge0p05 | path bank v2 question | 971 | 44.4 | 911 | 42.0 | 8.7e-06 |
| q5_in_all6 | ph2_gapdn5_25_ge3 | path bank v2 question | 267 | 37.1 | 123 | 28.5 | 9.4e-06 |
| q5_in_all6 | ph2_gapup5_15_ge2 | path bank v2 question | 347 | 41.5 | 211 | 33.6 | 1.1e-05 |
| q5_in_all6 | ph2_maxdn1d_60_ge0p15 | path bank v2 question | 689 | 44.7 | 462 | 39.0 | 1.1e-05 |
| q5_in_all6 | ph2_maxup1d_20_ge0p3 | path bank v2 question | 311 | 43.1 | 245 | 35.1 | 1.6e-05 |
| q7_in_all6 | ph2_disth_60_le0p15 | path bank v2 question | 465 | 56.8 | 353 | 61.8 | 4e-05 |
| q7_in_all6 | ph2_natr_40_ge0p03 | path bank v2 question | 422 | 42.4 | 402 | 39.3 | 6.8e-05 |
| q7_in_all6 | ph2_natr_60_ge0p03 | path bank v2 question | 431 | 42.7 | 396 | 39.4 | 8.9e-05 |
| q7_in_all6 | grid_lgE126L21_rchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 605 | 43.6 | 487 | 40.5 | 9.1e-05 |
| q7_in_all6 | ph2_natr_50_ge0p03 | path bank v2 question | 424 | 43.6 | 392 | 39.5 | 0.00012 |
| q7_in_all6 | grid_trL20_gchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 604 | 43.9 | 467 | 40.5 | 0.00013 |
| q7_in_all6 | grid_lgE10L21_gchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 616 | 42.4 | 462 | 40.5 | 0.00014 |
| q7_in_all6 | grid_lgE42L21_rchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 620 | 44.2 | 499 | 40.9 | 0.00015 |
| q7_in_all6 | ph2_gapup2_50_ge10 | path bank v2 question | 124 | 38.7 | 78 | 26.9 | 0.00016 |
| q7_in_all6 | ph2_gapup2_20_ge4 | path bank v2 question | 174 | 40.2 | 94 | 29.8 | 0.0003 |
| q7_in_all6 | ph2_natr_30_ge0p03 | path bank v2 question | 408 | 43.6 | 399 | 40.4 | 0.00036 |
| q7_in_all6 | ph2_maxdn1d_50_ge0p075 | path bank v2 question | 460 | 43.7 | 343 | 39.7 | 0.00039 |
| q8_in_all6 | ph2_distl_20_le0p3 | path bank v2 question | 173 | 61.8 | 149 | 69.1 | 1.5e-05 |
| q8_in_all6 | ph2_ret_15_ge0p1 | path bank v2 question | 174 | 38.5 | 146 | 30.8 | 1.7e-05 |
| q8_in_all6 | ph2_retq_15_gt10 | path bank v2 question | 174 | 38.5 | 146 | 30.8 | 1.7e-05 |
| q8_in_all6 | ph2_distl_10_le0p15 | path bank v2 question | 226 | 58.4 | 187 | 66.8 | 1.9e-05 |
| q8_in_all6 | ph2_distl_15_le0p15 | path bank v2 question | 269 | 58.7 | 215 | 65.6 | 2.2e-05 |
| q8_in_all6 | ph2_distl_15_le0p3 | path bank v2 question | 132 | 61.4 | 112 | 71.4 | 2.5e-05 |
| q8_in_all6 | ph2_ret_15_ge0p15 | path bank v2 question | 155 | 40.0 | 118 | 29.7 | 4e-05 |
| q8_in_all6 | TEC-TR-01045-C|10 | sheet:TR (Theme Radar) | 291 | 40.9 | 212 | 34.9 | 4.5e-05 |
| q8_in_all6 | ph2_maxdd_30_ge0p3 | path bank v2 question | 189 | 39.2 | 147 | 32.0 | 4.9e-05 |
| q8_in_all6 | ph2_distl_25_le0p3 | path bank v2 question | 201 | 58.7 | 166 | 66.9 | 5.5e-05 |
| q8_in_all6 | ph2_ret_15_ge0p2 | path bank v2 question | 127 | 37.8 | 104 | 28.8 | 6.2e-05 |
| q8_in_all6 | ph2_slope_20_gt0p01 | path bank v2 question | 141 | 39.7 | 124 | 30.6 | 6.3e-05 |

## (b) Items that most often differ in the winner's favour (pair sign test, BH across all items × setups)

HINT candidates (winner-favour > 55%, n_differ ≥ 30, q < 0.1): **1081** of 30,316 tested.

### chartpass_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 10768 | 6478 | 4290 | 60.2 | 8.54e-95 | True |
| nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 11281 | 6426 | 4855 | 57 | 2.04e-45 | True |
| ph2_gapdn5_50_ge5 | path bank v2 question | 1508 | 551 | 957 | 36.5 | 9.39e-22 | False |
| ph2_maxdn1d_20_ge0p05 | path bank v2 question | 7942 | 3510 | 4432 | 44.2 | 3.3e-21 | False |
| ph2_natr_40_ge0p07 | path bank v2 question | 6305 | 2748 | 3557 | 43.6 | 1.34e-20 | False |
| ph2_gapdn2_60_ge10 | path bank v2 question | 4677 | 1995 | 2682 | 42.7 | 4.04e-20 | False |
| ph2_gapdn5_60_ge5 | path bank v2 question | 1865 | 716 | 1149 | 38.4 | 4.04e-20 | False |
| ph2_maxdn1d_15_ge0p05 | path bank v2 question | 7957 | 3536 | 4421 | 44.4 | 1.29e-19 | False |
| ph2_voltrend_50_ge3p0 | path bank v2 question | 2656 | 1073 | 1583 | 40.4 | 1.31e-19 | False |
| grid_trL60_rchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 10984 | 4976 | 6008 | 45.3 | 2.19e-19 | False |
| ph2_voltrend_60_ge3p0 | path bank v2 question | 2543 | 1024 | 1519 | 40.3 | 2.37e-19 | False |
| new_rmove60_max [NEW, tercile] | NEW (not on sheet) | 11021 | 4995 | 6026 | 45.3 | 2.37e-19 | False |
| ph2_gapdn2_60_ge7 | path bank v2 question | 6351 | 2785 | 3566 | 43.9 | 2.63e-19 | False |
| ph2_upvolfrac_30_ge0p7 | path bank v2 question | 2301 | 917 | 1384 | 39.9 | 4.07e-19 | False |
| grid_lgE10L21_rchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 10853 | 4922 | 5931 | 45.4 | 7.22e-19 | False |

### q5_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_gapdn5_50_ge5 | path bank v2 question | 334 | 100 | 234 | 29.9 | 1.2e-11 | False |
| nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 2884 | 1637 | 1247 | 56.8 | 2.72e-11 | True |
| ph2_maxdn1d_20_ge0p05 | path bank v2 question | 2203 | 934 | 1269 | 42.4 | 6.39e-11 | False |
| ph2_gapdn5_60_ge5 | path bank v2 question | 431 | 142 | 289 | 32.9 | 7.75e-11 | False |
| ph2_gapdn1_20_ge7 | path bank v2 question | 1220 | 487 | 733 | 39.9 | 1.16e-10 | False |
| ph2_maxdn1d_30_ge0p05 | path bank v2 question | 2120 | 903 | 1217 | 42.6 | 5.13e-10 | False |
| ph2_maxdn1d_15_ge0p05 | path bank v2 question | 2217 | 949 | 1268 | 42.8 | 6.91e-10 | False |
| ph2_gapdn2_60_ge10 | path bank v2 question | 1200 | 483 | 717 | 40.2 | 7.78e-10 | False |
| ph2_gapdn5_60_ge3 | path bank v2 question | 840 | 326 | 514 | 38.8 | 4.03e-09 | False |
| ph2_maxdn1d_40_ge0p05 | path bank v2 question | 1991 | 852 | 1139 | 42.8 | 5.72e-09 | False |
| ph2_gapdn2_50_ge7 | path bank v2 question | 1479 | 616 | 863 | 41.6 | 6.06e-09 | False |
| ph2_maxdn1d_5_ge0p05 | path bank v2 question | 2266 | 981 | 1285 | 43.3 | 7.55e-09 | False |
| ph2_gapdn1_15_ge5 | path bank v2 question | 1555 | 652 | 903 | 41.9 | 8.56e-09 | False |
| ph2_gapdn5_30_ge3 | path bank v2 question | 455 | 160 | 295 | 35.2 | 1e-08 | False |
| ph2_maxdn1d_10_ge0p05 | path bank v2 question | 2229 | 965 | 1264 | 43.3 | 1.04e-08 | False |

### q7_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| grid_lgE10L21_gchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 1078 | 448 | 630 | 41.6 | 8.86e-07 | False |
| ph2_maxup1d_5_ge0p05 | path bank v2 question | 472 | 176 | 296 | 37.3 | 9.75e-07 | False |
| ph2_maxdn1d_15_ge0p05 | path bank v2 question | 850 | 345 | 505 | 40.6 | 1.18e-06 | False |
| ph2_maxdn1d_20_ge0p05 | path bank v2 question | 861 | 353 | 508 | 41 | 3.28e-06 | False |
| ph2_distl_5_le0p1 | path bank v2 question | 308 | 200 | 108 | 64.9 | 3.95e-06 | True |
| ph2_natr_40_ge0p03 | path bank v2 question | 824 | 337 | 487 | 40.9 | 4.32e-06 | False |
| grid_lgE126L21_rchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 1092 | 461 | 631 | 42.2 | 6.36e-06 | False |
| ph2_accel_25_gtm0p02 | path bank v2 question | 512 | 314 | 198 | 61.3 | 6.99e-06 | True |
| ph2_natr_60_ge0p03 | path bank v2 question | 827 | 340 | 487 | 41.1 | 7.46e-06 | False |
| ph2_disth_60_le0p15 | path bank v2 question | 818 | 482 | 336 | 58.9 | 7.71e-06 | True |
| ph2_maxdd_15_ge0p15 | path bank v2 question | 607 | 241 | 366 | 39.7 | 9.03e-06 | False |
| ph2_gapup2_30_ge5 | path bank v2 question | 343 | 125 | 218 | 36.4 | 1.16e-05 | False |
| ph2_distl_25_le0p1 | path bank v2 question | 661 | 395 | 266 | 59.8 | 1.18e-05 | True |
| ph2_gapdn5_7_ge1 | path bank v2 question | 468 | 180 | 288 | 38.5 | 1.34e-05 | False |
| grid_trL20_gchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 1071 | 454 | 617 | 42.4 | 1.39e-05 | False |

### q8_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_accel_50_gt0p02 | path bank v2 question | 255 | 83 | 172 | 32.5 | 7.1e-07 | False |
| ph2_distl_20_le0p3 | path bank v2 question | 322 | 210 | 112 | 65.2 | 1.33e-06 | True |
| ph2_ret_15_ge0p1 | path bank v2 question | 320 | 112 | 208 | 35 | 2.11e-06 | False |
| ph2_retq_15_gt10 | path bank v2 question | 320 | 112 | 208 | 35 | 2.11e-06 | False |
| TEC-TR-01045-C|3 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.51e-06 | False |
| TEC-TR-01045-C|10 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.51e-06 | False |
| TEC-TR-01045-C|60 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.51e-06 | False |
| TEC-TR-01045-C|5 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.51e-06 | False |
| TEC-TR-01045-C|20 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.51e-06 | False |
| TEC-TR-01045-C|1 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.51e-06 | False |
| ph2_distl_15_le0p15 | path bank v2 question | 484 | 299 | 185 | 61.8 | 5.37e-06 | True |
| ph2_maxdd_30_ge0p3 | path bank v2 question | 336 | 121 | 215 | 36 | 6.96e-06 | False |
| TEC-TR-00121-C|1 | sheet:TR (Theme Radar) | 275 | 95 | 180 | 34.5 | 6.96e-06 | False |
| TEC-TR-00121-C|20 | sheet:TR (Theme Radar) | 275 | 95 | 180 | 34.5 | 6.96e-06 | False |
| TEC-TR-00121-C|60 | sheet:TR (Theme Radar) | 275 | 95 | 180 | 34.5 | 6.96e-06 | False |

## (a2) Item win-rate ranking across all tradable setup days (YES vs NO; NEW rows: top vs bottom tercile), BH across all items × setups × horizons

HINT candidates (>55% win in the better bucket, n ≥ 30, q < 0.1): **8963** of 168,533 tests.

| setup | h | item | source | n YES/top | win% YES/top | n NO/bottom | win% NO/bottom | base win% | effect h | q | HINT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 10 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 13363 | 55.5 | 16534 | 38.3 | 45.5 | 0.347 | 7.02e-189 | True |
| chartpass_all6 | 10 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 13425 | 52.4 | 15715 | 39.1 | 45.5 | 0.269 | 8.66e-111 | False |
| chartpass_all6 | 21 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 13224 | 52.1 | 16351 | 39.1 | 44.6 | 0.261 | 7.84e-105 | False |
| chartpass_all6 | 21 | ph2_maxup1d_40_ge0p1 | path bank v2 question | 16206 | 38.2 | 26818 | 48.4 | 44.6 | -0.207 | 2.09e-90 | False |
| chartpass_all6 | 21 | ph2_maxup1d_30_ge0p1 | path bank v2 question | 15332 | 38 | 27692 | 48.2 | 44.6 | -0.207 | 1.98e-88 | False |
| chartpass_all6 | 21 | ph2_maxup1d_25_ge0p1 | path bank v2 question | 14977 | 37.9 | 28047 | 48.1 | 44.6 | -0.208 | 5.31e-88 | False |
| chartpass_all6 | 21 | ph2_maxup1d_20_ge0p1 | path bank v2 question | 14471 | 37.7 | 28553 | 48 | 44.6 | -0.209 | 1.77e-87 | False |
| chartpass_all6 | 21 | ph2_maxup1d_50_ge0p1 | path bank v2 question | 17418 | 38.7 | 25606 | 48.5 | 44.6 | -0.199 | 3.04e-86 | False |
| chartpass_all6 | 21 | ph2_natr_25_ge0p07 | path bank v2 question | 12345 | 37 | 30679 | 47.6 | 44.6 | -0.216 | 7.26e-86 | False |
| chartpass_all6 | 21 | ph2_natr_20_ge0p07 | path bank v2 question | 12517 | 37 | 30507 | 47.6 | 44.6 | -0.215 | 7.26e-86 | False |
| chartpass_all6 | 21 | ph2_natr_30_ge0p07 | path bank v2 question | 12189 | 36.9 | 30835 | 47.6 | 44.6 | -0.216 | 1.2e-84 | False |
| chartpass_all6 | 21 | ph2_maxup1d_15_ge0p075 | path bank v2 question | 16341 | 38.6 | 26683 | 48.2 | 44.6 | -0.195 | 8.07e-81 | False |
| chartpass_all6 | 21 | ph2_natr_40_ge0p07 | path bank v2 question | 12058 | 37.1 | 30966 | 47.5 | 44.6 | -0.21 | 7.68e-80 | False |
| chartpass_all6 | 21 | grid_trL20_rchain_move [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 14998 | 38.5 | 13763 | 49.9 | 44.6 | -0.229 | 2.21e-79 | False |
| chartpass_all6 | 21 | ph2_distl_25_le0p15 | path bank v2 question | 30794 | 47.5 | 12230 | 37.2 | 44.6 | 0.208 | 2.56e-79 | False |
| chartpass_all6 | 21 | ph2_disth_15_le0p15 | path bank v2 question | 27080 | 48.1 | 15944 | 38.5 | 44.6 | 0.193 | 6.88e-79 | False |
| chartpass_all6 | 21 | ph2_maxup1d_15_ge0p1 | path bank v2 question | 11862 | 37.1 | 31162 | 47.4 | 44.6 | -0.21 | 1.03e-78 | False |
| chartpass_all6 | 21 | grid_trL20_dist_high [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 13536 | 49.8 | 15360 | 38.5 | 44.6 | 0.227 | 1.56e-78 | False |
| chartpass_all6 | 21 | ph2_maxup1d_50_ge0p15 | path bank v2 question | 10825 | 36.6 | 32199 | 47.2 | 44.6 | -0.215 | 3.98e-78 | False |
| chartpass_all6 | 21 | ph2_natr_60_ge0p07 | path bank v2 question | 12004 | 37.2 | 31020 | 47.4 | 44.6 | -0.208 | 6.74e-78 | False |
| chartpass_all6 | 21 | ph2_disth_20_le0p15 | path bank v2 question | 26526 | 48.2 | 16498 | 38.7 | 44.6 | 0.191 | 6.74e-78 | False |
| chartpass_all6 | 21 | ph2_disth_25_le0p15 | path bank v2 question | 26455 | 48.2 | 16569 | 38.8 | 44.6 | 0.191 | 6.78e-78 | False |
| chartpass_all6 | 21 | ph2_natr_7_ge0p05 | path bank v2 question | 18995 | 39.4 | 24029 | 48.6 | 44.6 | -0.186 | 8.25e-78 | False |
| chartpass_all6 | 21 | ph2_maxup1d_20_ge0p075 | path bank v2 question | 19472 | 39.5 | 23552 | 48.7 | 44.6 | -0.186 | 1.06e-77 | False |
| chartpass_all6 | 21 | ph2_distl_40_le0p2 | path bank v2 question | 32166 | 47.2 | 10858 | 36.7 | 44.6 | 0.214 | 1.8e-77 | False |

### Cyrus's NEW rows (chains, 40-bar trend/drawdown, 2-month trend, red:green ratio, last green vs red body, RSI, MACD, RVOL, BB, SMA distance) — best horizon per setup

| setup | h | item | n top | win% top | n bottom | win% bottom | effect h | q |
|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 10 | nn_win126 [NEW, tercile] | 13363 | 55.5 | 16534 | 38.3 | 0.347 | 7.02e-189 |
| chartpass_all6 | 10 | nn_win60 [NEW, tercile] | 13425 | 52.4 | 15715 | 39.1 | 0.269 | 8.66e-111 |
| chartpass_all6 | 21 | grid_trL20_rchain_move [NEW, tercile] | 14998 | 38.5 | 13763 | 49.9 | -0.229 | 2.21e-79 |
| chartpass_all6 | 21 | grid_trL20_dist_high [NEW, tercile] | 13536 | 49.8 | 15360 | 38.5 | 0.227 | 1.56e-78 |
| chartpass_all6 | 21 | new_gmove60_max [NEW, tercile] | 15319 | 38.4 | 13374 | 49.5 | -0.226 | 2.68e-77 |
| chartpass_all6 | 21 | grid_trL60_gchain_move [NEW, tercile] | 15330 | 38.3 | 13378 | 49.5 | -0.225 | 4.5e-77 |
| chartpass_all6 | 21 | new_rmove60_max [NEW, tercile] | 15032 | 38.9 | 13641 | 49.9 | -0.223 | 9.95e-76 |
| chartpass_all6 | 21 | grid_trL60_rchain_move [NEW, tercile] | 15059 | 38.8 | 13648 | 49.8 | -0.222 | 3.99e-75 |
| chartpass_all6 | 21 | grid_lgE5L21_rchain_move [NEW, tercile] | 15550 | 38.9 | 13158 | 49.8 | -0.22 | 1.48e-73 |
| chartpass_all6 | 21 | new_bb_width [NEW, tercile] | 15254 | 38.9 | 13583 | 49.6 | -0.216 | 1.56e-71 |
| chartpass_all6 | 21 | grid_trL10_rchain_move [NEW, tercile] | 14654 | 38.8 | 14198 | 49.5 | -0.216 | 2.12e-71 |
| chartpass_all6 | 21 | grid_trL40_gchain_move [NEW, tercile] | 15404 | 38.4 | 13357 | 49 | -0.215 | 1.96e-70 |
| chartpass_all6 | 21 | grid_trL40_rchain_move [NEW, tercile] | 15044 | 38.9 | 13725 | 49.5 | -0.214 | 7.09e-70 |
| chartpass_all6 | 21 | grid_trL40_dist_high [NEW, tercile] | 13556 | 49.3 | 15307 | 38.7 | 0.212 | 4.11e-69 |
| chartpass_all6 | 21 | grid_trL120_gchain_move [NEW, tercile] | 14677 | 39.4 | 12984 | 50.1 | -0.216 | 1.51e-68 |
| chartpass_all6 | 21 | grid_lgE5L10_rchain_move [NEW, tercile] | 15539 | 39.1 | 13269 | 49.5 | -0.21 | 1.23e-67 |
| chartpass_all6 | 21 | grid_lgE10L21_rchain_move [NEW, tercile] | 15269 | 39 | 13408 | 49.4 | -0.209 | 9.29e-67 |
| chartpass_all6 | 21 | grid_lgE126L21_rchain_move [NEW, tercile] | 14125 | 40.3 | 12904 | 50.8 | -0.212 | 8.78e-65 |
| chartpass_all6 | 21 | grid_trL10_dist_high [NEW, tercile] | 13712 | 49 | 15183 | 38.9 | 0.204 | 6.79e-64 |
| chartpass_all6 | 21 | grid_trL20_gchain_move [NEW, tercile] | 15502 | 38.8 | 13285 | 48.9 | -0.204 | 8.74e-64 |
| chartpass_all6 | 21 | grid_lgE5L10_dist_high [NEW, tercile] | 13509 | 49 | 15391 | 38.9 | 0.203 | 2.47e-63 |
| chartpass_all6 | 21 | grid_lgE5L21_dist_high [NEW, tercile] | 13430 | 49.1 | 15397 | 39 | 0.203 | 7.39e-63 |
| chartpass_all6 | 21 | grid_trL60_dist_high [NEW, tercile] | 13488 | 49.5 | 15255 | 39.4 | 0.202 | 3.45e-62 |
| chartpass_all6 | 21 | grid_lgE5L21_gchain_move [NEW, tercile] | 15490 | 38.5 | 13302 | 48.5 | -0.202 | 3.79e-62 |
| chartpass_all6 | 21 | grid_lgE5L5_rchain_move [NEW, tercile] | 15267 | 39 | 13554 | 48.7 | -0.197 | 1.23e-59 |
| chartpass_all6 | 21 | new_maxdd40 [NEW, tercile] | 13673 | 49 | 15090 | 39.3 | 0.196 | 5.49e-59 |
| chartpass_all6 | 21 | grid_lgE5L10_gchain_move [NEW, tercile] | 15385 | 39.3 | 13327 | 49 | -0.196 | 1.43e-58 |
| chartpass_all6 | 21 | grid_trL10_gchain_move [NEW, tercile] | 14613 | 39.2 | 14111 | 48.7 | -0.193 | 8.15e-57 |
| chartpass_all6 | 21 | grid_lgE21L21_rchain_move [NEW, tercile] | 14893 | 40 | 13756 | 49.6 | -0.193 | 1.4e-56 |
| chartpass_all6 | 21 | grid_trL120_dist_high [NEW, tercile] | 12927 | 49.5 | 14521 | 39.7 | 0.196 | 2.68e-56 |

Files: `item_ranking.csv.gz` (every item × setup × h), `pair_item_aggregate.csv.gz`, `pair_diffs.csv.gz` (one row per pair; `top_items_differing` lists that setup's top-40 aggregate items where W and L differ: YES/NO, or T1–T3 terciles for NEW rows).
Coverage: sheet items = every row answered by the universe engine for 2020–24 (JG 1,478 ticker rows incl. BUT variants, NB 614, TR 2,808 row|N keys, SHARED 8,176 market rows) + 9 chart-picture story questions; the 6 chart-pass checks are the setup itself. NR answers are skipped, never guessed. SHARED rows rarely differ within a pair because pairs share the date.


## Coverage ledger (every row of six_bucket_map_v5_1 ∪ master.csv ∪ path bank v2 ∪ chart-picture v2) — `coverage_ledger.csv.gz`

| list | NOT_READY | SETUP | TESTED |
|---|---|---|---|
| chart_picture_v2 | 0 | 6 | 9 |
| master.csv | 323 | 0 | 391 |
| path_bank_v2 | 33 | 0 | 5,683 |
| six_bucket_map_v5_1 | 1,600 | 0 | 11,569 |

NOT_READY reasons:

- six_bucket_map_v5_1: engine row present but NR on every 2020-24 setup cell (source has no 2020-24 history) — 1,475
- six_bucket_map_v5_1: no 2020-24 answer: SI chunks — 48
- six_bucket_map_v5_1: no 2020-24 answer: no (no reader port) — 36
- master.csv: needs Calendar data not on box point-in-time for 2020-24 — 34
- path_bank_v2: multi-class label (not YES/NO); its yes/no cuts are tested — 33
- master.csv: needs Options data not on box point-in-time for 2020-24 — 19
- master.csv: needs Market-wide data not on box point-in-time for 2020-24 — 19
- six_bucket_map_v5_1: no 2020-24 answer: NBX chunks — 18
- master.csv: needs Macro surprise data not on box point-in-time for 2020-24 — 17
- master.csv: needs Analyst data not on box point-in-time for 2020-24 — 12
- master.csv: needs Insider data not on box point-in-time for 2020-24 — 12
- master.csv: needs Cross-asset data not on box point-in-time for 2020-24 — 12
- master.csv: needs Short volume data not on box point-in-time for 2020-24 — 11
- master.csv: needs Credit data not on box point-in-time for 2020-24 — 11
- master.csv: needs Share supply data not on box point-in-time for 2020-24 — 10
- six_bucket_map_v5_1: no 2020-24 answer: ATTN chunks — 10
- master.csv: needs Earnings data not on box point-in-time for 2020-24 — 10
- master.csv: needs Pre-market data not on box point-in-time for 2020-24 — 9
- master.csv: needs Rates data not on box point-in-time for 2020-24 — 8
- master.csv: needs Yield curve data not on box point-in-time for 2020-24 — 8
- master.csv: not known before 09:25 ET on D (Pre-open: only via 09:25 premarket print; true O is NOT known) — 8
- master.csv: needs Short interest data not on box point-in-time for 2020-24 — 8
- six_bucket_map_v5_1: listed in engine but no reader output in universe chunks — 7
- master.csv: needs Corporate action data not on box point-in-time for 2020-24 — 7
- master.csv: needs Valuation data not on box point-in-time for 2020-24 — 6
- master.csv: needs Theme data not on box point-in-time for 2020-24 — 6
- six_bucket_map_v5_1: no 2020-24 answer: pending (DoltHub IV build) — 6
- master.csv: needs Securities lending data not on box point-in-time for 2020-24 — 5
- master.csv: needs Growth data not on box point-in-time for 2020-24 — 5
- master.csv: needs Market sentiment data not on box point-in-time for 2020-24 — 5
- master.csv: needs Corporate event data not on box point-in-time for 2020-24 — 5
- master.csv: needs Rotation data not on box point-in-time for 2020-24 — 4
- master.csv: needs 13F data not on box point-in-time for 2020-24 — 4
- master.csv: needs Biotech catalyst data not on box point-in-time for 2020-24 — 3
- master.csv: needs Index membership data not on box point-in-time for 2020-24 — 3
- master.csv: needs Volatility data not on box point-in-time for 2020-24 — 3
- master.csv: needs Performance data not on box point-in-time for 2020-24 — 3
- master.csv: needs Profitability data not on box point-in-time for 2020-24 — 3
- master.csv: needs Fed data not on box point-in-time for 2020-24 — 3
- master.csv: needs After-hours data not on box point-in-time for 2020-24 — 3
- master.csv: needs Ownership data not on box point-in-time for 2020-24 — 3
- master.csv: needs Balance sheet data not on box point-in-time for 2020-24 — 2
- master.csv: needs Financial conditions data not on box point-in-time for 2020-24 — 2
- master.csv: needs ETF flows data not on box point-in-time for 2020-24 — 2
- master.csv: needs Correlation data not on box point-in-time for 2020-24 — 2
- master.csv: needs 52w range data not on box point-in-time for 2020-24 — 2
- master.csv: needs Sector gap data not on box point-in-time for 2020-24 — 2
- master.csv: needs Liquidity data not on box point-in-time for 2020-24 — 2
- master.csv: not known before 09:25 ET on D (Lagged only: use rows published before D (~2wk lag)) — 2
- master.csv: not known before 09:25 ET on D (Lagged only) — 2
- master.csv: needs Oscillator data not on box point-in-time for 2020-24 — 2
- master.csv: needs Price bucket data not on box point-in-time for 2020-24 — 2
- master.csv: needs 10 years of same-month history; price file starts 2020-01-02 — 1
- master.csv: needs ADR / dual listing data not on box point-in-time for 2020-24 — 1
- master.csv: needs Change from open data not on box point-in-time for 2020-24 — 1
- master.csv: needs ETF ownership data not on box point-in-time for 2020-24 — 1
- master.csv: needs Float data not on box point-in-time for 2020-24 — 1
- master.csv: needs Industry data not on box point-in-time for 2020-24 — 1
- master.csv: needs Pattern data not on box point-in-time for 2020-24 — 1
- master.csv: needs Inflation expectations data not on box point-in-time for 2020-24 — 1
- master.csv: needs LULD halt records — 1
- master.csv: needs Commodity proxy data not on box point-in-time for 2020-24 — 1
- master.csv: needs Crypto proxy data not on box point-in-time for 2020-24 — 1
- master.csv: needs Sector correlation data not on box point-in-time for 2020-24 — 1
- master.csv: needs Sector data not on box point-in-time for 2020-24 — 1
- master.csv: needs Sector flows data not on box point-in-time for 2020-24 — 1
- master.csv: needs Trend strength data not on box point-in-time for 2020-24 — 1
- master.csv: needs Size bucket data not on box point-in-time for 2020-24 — 1
- master.csv: needs Revenue data not on box point-in-time for 2020-24 — 1
- master.csv: not known before 09:25 ET on D (Partial) — 1
- master.csv: needs after-hours prints of industry peers — 1
- master.csv: needs earnings dates (AVWAP anchor) not on box point-in-time — 1
- master.csv: needs intraday VWAP — 1
- master.csv: needs intraday last-hour bars — 1

## SURVIVOR-BIAS RISK (applies to every near-low / deep-drawdown / 'bought the dip' winner-side result, and near-high results)
The price file `universe_2020_survivors.parquet` holds only names still listed. Stocks that fell to their lows and then delisted are missing, which flatters any 'near the low → winner' or 'deeper drawdown → winner' read (e.g. near 52-week low, near 13-week low in Q7, near 10–25-day low in Q8, deeper 40-bar drawdown). Treat all of these as UNCONFIRMED. The sealed 2025–26 data is ALSO survivors-only, so it cannot clear this doubt; only live trading days after the lock (or a delisting-inclusive price file) can. 'Too hot → loser' results are less exposed but not immune.

## AUDIT 2026-10-22 (Manager Bot request) — leakage + direction check, and a RETRACTION

**RETRACTED:** the earlier claim that chart-picture story questions (Q1 lower highs, Q3 shrinking green, Q7 lower-band reclaim, Q8 above last red high) "differ in the winner's favour in ~78–84% of pairs" (and the 6,479 "holds on 2023–24" count built on that pairing) is withdrawn. It was a **pairing artifact**, not an edge.
- Cause: pairs were winner-anchored (each winner → nearest loser, losers reused) with a tie-break on story-question Hamming distance. A rare YES trait on the winner usually cannot be matched, a common NO usually can, so "winner YES / loser NO" dominates regardless of outcome.
- Proof: shuffling the win labels within setup × date (seed 20261022) reproduced it — Q1 83.9%, Q3 79.4%, Q7 78.6%, Q8 77.9% under the null, and 2,183 false "HINT candidates".
- Fix: symmetric 1:1 pairs — same setup, same date, winners and losers each in a fixed ticker-hash order, zipped without reuse; no tested item is used for matching. Under shuffled labels the fixed design gives **0** HINT candidates and 1 item at q<0.1 out of 30,264 (re-run with every row incl. grid/path/shape) (null file `pair_item_aggregate_NULL.csv.gz`). With real labels the story questions now sit at 49.8–51.9% (Q1 50.4%, Q3 49.9%, Q7 50.5%, Q8 49.8%) — **no separation**.

**Leakage (bars ≥ D):** none found. Story answers (`/workspace/state_test/story_q/story_q.py`) are computed on bar t = D−1 using bars ≤ t (swing points confirmed 2 bars later, so no look-ahead); the cp_* gate and every story flag show no relation to day-D's own open→close move (yes vs no differ by ≤0.03pp on a 10% ticker sample). Win label = open D → open D+h, net of 30bp/side, versus same-day controls — no bar before D's open enters it. Pairing uses only setup and date.

**Direction:** no question's YES/bullish sense was flipped in code — the pair test and win-rate tests are direction-free (they report which side wins); `yes_means` is not used anywhere. Q8 is pre-registered as a **warning/fade**; the Q8 setup's re-score above simply reports its win rate (45.9% at 10d after the filter, i.e. it does still lag). The earlier wording "Q8 flips to slightly positive" referred only to the mean excess return (+0.46%), not to a reversed definition.

## Plain-language findings (HINT only; re-test on sealed 2025–26 after Fri 23:00 HKT)

Filter: Taskforce drop_list_v2 on cases and controls first; **ETF rule partial, market cap not applied**.

1. **The 4 rules alone:** after the filter win rates are 43–48% vs matched controls; none passes the >55% bar.
2. **Honest split, fixed pairing:** 3,670 item × setup differences discovered on 2020–22; **1,498 still hold on 2023–24** (same direction, >5pp, n ≥ 30, BH q<0.1). Correlated cuts of one feature count as one family.
3. **Families that hold — all point the same way: big recent moves / high volatility mark the LOSER.**
   - Path bank: a ≥30% one-day jump in the last 15–60 bars (chart pass winner-favour 43–45% → 36–39% in 2023–24); ≥5 gap-downs >5% in 50 bars (39% → 32%); volume trend ≥3× (42% → 38%); big one-day drops; high NATR (Q7 42–44% → 39–40%); repeated ≥2% gap-ups (Q7 38–40% → 27–30%); in Q8, a ≥10–20% 15-day run-up (38% → 29–31%).
   - Winners: in Q8, close within 15–30% of the 10–25-day low (58–62% → 66–71%) ⚠️ **SURVIVOR-BIAS RISK** (price file is survivors-only: names that delisted near their lows are missing, so near-low / deep-drawdown → winner can be an artifact; unconfirmed: 2025–26 is also survivors-only, so only live trading days after the lock can clear this); in Q7, within 15% of the 60-day high (57% → 62%).
4. **New master.csv price/volume families that hold (391 rows ported):** 32 row × setup results hold, all in the "too hot = loser" family: ret20 in the top decile of the universe (chart pass 44.4% → 42.4%), ATR14/C ≥ 20% (38.7% → 35.1%) and ≥ 10%, up-day volume share ≥ 65% (43% → 40%), 20-day return ≥ 20% (43.8% → 40.8%), MFI > 80, 5/10-day return ≥ 5–10%, ret5/ret20 ≥ 5% ahead of SPY/IWM/sector (Q7 28–34%, Q8 40–43%). The few winner-side ones: close within 2% of the 52-week low (chart pass 69.6% → 58.8%) ⚠️ **SURVIVOR-BIAS RISK** (price file is survivors-only: names that delisted near their lows are missing, so near-low / deep-drawdown → winner can be an artifact; unconfirmed: 2025–26 is also survivors-only, so only live trading days after the lock can clear this), within 2% of the 26-week high (60.6% → 57.1%), within 5% of the 13-week low in Q7 (61% → 57%). ⚠️ **SURVIVOR-BIAS RISK** (price file is survivors-only: names that delisted near their lows are missing, so near-low / deep-drawdown → winner can be an artifact; unconfirmed: 2025–26 is also survivors-only, so only live trading days after the lock can clear this)
5. **Fixed lookback grid + path-level v2 (recorded before computing):** 200 grid rows + 16 path rows + 4 shape rows tested. 20 grid row × setup results hold, all in **Q7**: a bigger biggest green/red chain move in old windows (126 bars back, 21 long; trailing 20/120) marks losers (42–44% → 40–42%), and being nearer the window high 5–126 bars back marks winners (55–58% → 56–58%). Only one path-level row holds: longer base (Q5: 55.5% both periods). Drawdown/recovery, swing counts, trend straightness (R²), ceiling tests, range shrink, up/down volume, spike share: no confirmed separation.
   **Shape look-alike: no edge.** Correlation to the 2020–22 winners' average 60/126-bar shape: ~50% in every setup. Nearest-neighbour win share looked strong in-sample (2020–22 leave-one-out: 59–68% winner-favour) but fell to 46–52% on 2023–24 (none holds) — the in-sample number is neighbours sharing the same dates/regime, not shape.
6. **Story questions:** no separation once pairing is fixed (see audit).
7. **Per-sentence YES frequency, winners vs losers** (`sentence_freq_win_vs_loss.csv.gz`): 57,490 tests, 21,921 at global q<0.1 — far too many to be real: stock-days on the same date are not independent, so this event-level test is anti-conservative. Use the pair test + 2023–24 confirmation above as the evidence; the frequency table is descriptive.
8. **Caveats:** sector/industry rows use today's Finviz sector map (not point-in-time); long-lookback rows are NA before 2021-01-05 because the price file starts 2020-01-02; market-wide rows hit few dates; TR `|N` variants duplicate each other.

## Outcome is pluggable
Taskforce owns the exit-rule grid. To regrade every pair with their rule: `OUTCOME_FILE=<parquet/csv: ticker,date,r5,r10,r21 net returns, entry at D> TASKFORCE_DROP=… analyze.py`. Pairing, tests, BH and honesty split rerun unchanged.

## Visuals

- One PNG per fixed pair (25,128) in `pairs/<setup>/` (sample in repo; full set on Drive `checklist_engine_chunks`, see `pairs/README.md`). The earlier Drive tar parts (`lookalike_pairs_pngs_2020_24_HINT.tar.part00–15`) show the **retracted** pairing.
- Reproduce: `build.py` → `new2.py` → `pb2.py` → `master_pv.py` → `mpv_mask.py` → `grid.py` → `path2.py` → `TASKFORCE_DROP=… analyze.py` (`PERMUTE_NULL=1` for the null) → `charts.py` → `coverage.py`.
