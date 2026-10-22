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
| chartpass_all6 | 5 | 145,002 | 47.0 | 0.46 | +0.17 | 43,288 | 48.8 | 0.92 | +0.54 |
| chartpass_all6 | 10 | 145,002 | 47.0 | 0.46 | +0.17 | 43,288 | 48.8 | 0.92 | +0.54 |
| chartpass_all6 | 21 | 145,002 | 47.0 | 0.46 | +0.17 | 43,288 | 48.8 | 0.92 | +0.54 |
| q5_in_all6 | 5 | 46,948 | 48.0 | 0.98 | +0.65 | 14,820 | 50.1 | 2.34 | +1.83 |
| q5_in_all6 | 10 | 46,948 | 48.0 | 0.98 | +0.65 | 14,820 | 50.1 | 2.34 | +1.83 |
| q5_in_all6 | 21 | 46,948 | 48.0 | 0.98 | +0.65 | 14,820 | 50.1 | 2.34 | +1.83 |
| q7_in_all6 | 5 | 22,833 | 48.4 | 1.63 | +0.94 | 6,526 | 50.7 | 4.16 | +3.26 |
| q7_in_all6 | 10 | 22,833 | 48.4 | 1.63 | +0.94 | 6,526 | 50.7 | 4.16 | +3.26 |
| q7_in_all6 | 21 | 22,833 | 48.4 | 1.63 | +0.94 | 6,526 | 50.7 | 4.16 | +3.26 |
| q8_in_all6 | 5 | 17,162 | 47.2 | 0.45 | -0.02 | 5,167 | 49.2 | 0.66 | +0.17 |
| q8_in_all6 | 10 | 17,162 | 47.2 | 0.45 | -0.02 | 5,167 | 49.2 | 0.66 | +0.17 |
| q8_in_all6 | 21 | 17,162 | 47.2 | 0.45 | -0.02 | 5,167 | 49.2 | 0.66 | +0.17 |

## Pairs (h=10d primary): symmetric 1:1 winner–loser pairs, same setup and same date, fixed ticker-hash order, no reuse (audit fix; old winner-anchored pairing retracted)

| setup | tradable events | winners | pairs | median items differing | casebook pairs |
|---|---|---|---|---|---|
| chartpass_all6 | 43,288 | 21,067 | 17,179 | 1704 | 32 |
| q5_in_all6 | 14,820 | 7,690 | 5,076 | 1638 | 11 |
| q7_in_all6 | 6,526 | 3,278 | 1,955 | 1571 | 8 |
| q8_in_all6 | 5,166 | 2,604 | 1,535 | 1719 | 10 |

## Per sentence: how often it is YES (top tercile for NEW/grid rows) among winners vs losers (h=10d, tradable setup days; global BH over all items × setups) — `sentence_freq_win_vs_loss.csv.gz`

Tested: 57,470; q<0.1: 9,217. Top 12 per setup (TR `|N` duplicates hidden):

| setup | sentence | source | YES % winners | YES % losers | n win / n lose | q (global BH) |
|---|---|---|---|---|---|---|
| chartpass_all6 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 37.3 | 25.7 | 20,101.0 / 21,190.0 | 7.7e-139 |
| chartpass_all6 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 35.1 | 25.3 | 21,067.0 / 22,221.0 | 2.5e-106 |
| chartpass_all6 | MKT-JA-945 | sheet:SHARED (market rows) | 0.9 | 2.2 | 16,703.0 / 17,705.0 | 1.6e-18 |
| chartpass_all6 | MKT-JA-945-BUT | sheet:SHARED (market rows) | 0.9 | 2.2 | 16,703.0 / 17,705.0 | 1.6e-18 |
| chartpass_all6 | MKT-JA-1145 | sheet:SHARED (market rows) | 0.7 | 1.9 | 16,703.0 / 17,705.0 | 3.8e-18 |
| chartpass_all6 | MKT-JA-1145-BUT | sheet:SHARED (market rows) | 0.8 | 1.8 | 21,067.0 / 22,221.0 | 2.9e-16 |
| chartpass_all6 | FV-GB-2136 | sheet:SHARED (market rows) | 10.7 | 7.9 | 16,703.0 / 17,705.0 | 3.4e-15 |
| chartpass_all6 | MKT-JA-738-BUT | sheet:SHARED (market rows) | 0.1 | 0.7 | 16,703.0 / 17,705.0 | 2.9e-13 |
| chartpass_all6 | MKT-JA-738 | sheet:SHARED (market rows) | 0.1 | 0.7 | 16,703.0 / 17,705.0 | 2.9e-13 |
| chartpass_all6 | MKT-JA-1012 | sheet:SHARED (market rows) | 7.5 | 5.6 | 21,067.0 / 22,221.0 | 5.6e-13 |
| chartpass_all6 | MKT-JA-1105 | sheet:SHARED (market rows) | 6.1 | 8.1 | 21,067.0 / 22,221.0 | 5.6e-13 |
| chartpass_all6 | FV-GB-2430 | sheet:SHARED (market rows) | 7.5 | 9.7 | 21,067.0 / 22,221.0 | 1.3e-12 |
| q5_in_all6 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 42.3 | 31.5 | 7,343.0 / 6,862.0 | 2e-36 |
| q5_in_all6 | MAC-JA-675-BUT | sheet:SHARED (market rows) | 7.1 | 11.8 | 7,690.0 / 7,130.0 | 1.2e-18 |
| q5_in_all6 | MAC-JA-675 | sheet:SHARED (market rows) | 7.1 | 11.8 | 7,690.0 / 7,130.0 | 1.2e-18 |
| q5_in_all6 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 39.5 | 32.1 | 7,690.0 / 7,130.0 | 3.6e-17 |
| q5_in_all6 | MAC-JA-875-BUT | sheet:SHARED (market rows) | 7.5 | 11.8 | 7,690.0 / 7,130.0 | 4e-15 |
| q5_in_all6 | MAC-JA-875 | sheet:SHARED (market rows) | 7.5 | 11.8 | 7,690.0 / 7,130.0 | 4e-15 |
| q5_in_all6 | MAC-JA-1897-BUT | sheet:SHARED (market rows) | 11.1 | 7.3 | 7,690.0 / 7,130.0 | 2.3e-12 |
| q5_in_all6 | MKT-JA-1027-BUT | sheet:SHARED (market rows) | 11.5 | 7.7 | 7,690.0 / 7,130.0 | 1.1e-11 |
| q5_in_all6 | MAC-JA-855 | sheet:SHARED (market rows) | 17.8 | 22.9 | 7,690.0 / 7,130.0 | 1.8e-11 |
| q5_in_all6 | MAC-JA-855-BUT | sheet:SHARED (market rows) | 17.8 | 22.9 | 7,690.0 / 7,130.0 | 1.8e-11 |
| q5_in_all6 | MKT-JA-399 | sheet:SHARED (market rows) | 17.2 | 21.9 | 7,690.0 / 7,130.0 | 5.3e-10 |
| q5_in_all6 | MKT-JA-316 | sheet:SHARED (market rows) | 46.0 | 51.9 | 7,690.0 / 7,130.0 | 9.6e-10 |
| q7_in_all6 | MAC-JA-2492 | sheet:SHARED (market rows) | 74.8 | 65.4 | 2,586.0 / 2,617.0 | 1.6e-10 |
| q7_in_all6 | MAC-JA-2486 | sheet:SHARED (market rows) | 74.8 | 65.4 | 2,586.0 / 2,617.0 | 1.6e-10 |
| q7_in_all6 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 31.8 | 23.9 | 3,278.0 / 3,248.0 | 1.5e-09 |
| q7_in_all6 | MKT-JA-007 | sheet:SHARED (market rows) | 12.6 | 7.5 | 3,278.0 / 3,248.0 | 3.1e-09 |
| q7_in_all6 | MKT-JA-1668 | sheet:SHARED (market rows) | 24.3 | 17.6 | 3,278.0 / 3,248.0 | 1.6e-08 |
| q7_in_all6 | MAC-JA-2098 | sheet:SHARED (market rows) | 4.7 | 9.4 | 2,586.0 / 2,617.0 | 2e-08 |
| q7_in_all6 | MAC-JA-2098-BUT | sheet:SHARED (market rows) | 4.7 | 9.4 | 2,586.0 / 2,617.0 | 2e-08 |
| q7_in_all6 | ph2_gapdn2_5_ge1 | path bank v2 question | 49.3 | 41.3 | 3,278.0 / 3,248.0 | 3.8e-08 |
| q7_in_all6 | FV-GB-2194 | sheet:SHARED (market rows) | 9.4 | 4.9 | 2,586.0 / 2,617.0 | 1.2e-07 |
| q7_in_all6 | MKT-JA-1681 | sheet:SHARED (market rows) | 18.4 | 12.7 | 3,278.0 / 3,248.0 | 1.2e-07 |
| q7_in_all6 | MAC-JA-2356 | sheet:SHARED (market rows) | 5.6 | 10.4 | 2,586.0 / 2,617.0 | 1.2e-07 |
| q7_in_all6 | MKT-JA-368 | sheet:SHARED (market rows) | 26.5 | 20.0 | 3,278.0 / 3,248.0 | 2.3e-07 |
| q8_in_all6 | MAC-JA-917 | sheet:SHARED (market rows) | 7.8 | 4.0 | 2,604.0 / 2,562.0 | 2.1e-06 |
| q8_in_all6 | MAC-JA-917-BUT | sheet:SHARED (market rows) | 7.8 | 4.0 | 2,604.0 / 2,562.0 | 2.1e-06 |
| q8_in_all6 | CAL-JA-100 | sheet:SHARED (market rows) | 6.0 | 2.8 | 2,604.0 / 2,562.0 | 6.6e-06 |
| q8_in_all6 | MAC-JA-292 | sheet:SHARED (market rows) | 7.6 | 4.0 | 2,604.0 / 2,562.0 | 8.6e-06 |
| q8_in_all6 | MAC-JA-1094 | sheet:SHARED (market rows) | 8.8 | 5.0 | 2,604.0 / 2,562.0 | 1.1e-05 |
| q8_in_all6 | MAC-JA-1094-BUT | sheet:SHARED (market rows) | 8.8 | 5.0 | 2,604.0 / 2,562.0 | 1.1e-05 |
| q8_in_all6 | MAC-JA-1901 | sheet:SHARED (market rows) | 3.9 | 1.6 | 2,604.0 / 2,562.0 | 3.7e-05 |
| q8_in_all6 | MAC-JA-1901-BUT | sheet:SHARED (market rows) | 3.9 | 1.6 | 2,604.0 / 2,562.0 | 3.7e-05 |
| q8_in_all6 | MKT-JA-784 | sheet:SHARED (market rows) | 8.7 | 4.7 | 2,102.0 / 2,077.0 | 4e-05 |
| q8_in_all6 | MKT-JA-784-BUT | sheet:SHARED (market rows) | 8.7 | 4.7 | 2,102.0 / 2,077.0 | 4e-05 |
| q8_in_all6 | MAC-JA-1797-BUT | sheet:SHARED (market rows) | 9.5 | 5.9 | 2,604.0 / 2,562.0 | 8.7e-05 |
| q8_in_all6 | ph2_hhfrac_25_ge0p3 | path bank v2 question | 99.3 | 97.6 | 2,604.0 / 2,562.0 | 9e-05 |

## Honesty split (pair sign test): discover on 2020–22 pairs, confirm on 2023–24 pairs

Tested in discovery (n_differ ≥ 30): 28,779. Discovered (q<0.1 BH, |favour−50| > 5pp): 509. **Still hold on 2023–24** (same direction, >5pp, n ≥ 30, q<0.1 BH over discovered set): **5**.

| setup | item | source | disc n | disc winner-favour % | conf n | conf winner-favour % | q conf |
|---|---|---|---|---|---|---|---|
| chartpass_all6 | ph2_pctbmean_20_ge0p8 | path bank v2 question | 1038 | 55.2 | 763 | 55.7 | 0.067 |
| q5_in_all6 | ph2_xc20up_20_eq1 | path bank v2 question | 597 | 43.6 | 478 | 42.1 | 0.044 |
| q5_in_all6 | ph2_abv20run_20_ge20 | path bank v2 question | 513 | 56.9 | 415 | 58.3 | 0.044 |
| q5_in_all6 | ph2_abv10frac_25_ge0p7 | path bank v2 question | 634 | 56.0 | 470 | 57.7 | 0.044 |
| q8_in_all6 | ph2_pctbmean_25_ge0p7 | path bank v2 question | 185 | 63.2 | 114 | 65.8 | 0.044 |

## (b) Items that most often differ in the winner's favour (pair sign test, BH across all items × setups)

HINT candidates (winner-favour > 55%, n_differ ≥ 30, q < 0.1): **89** of 30,544 tested.

### chartpass_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 10823 | 6642 | 4181 | 61.4 | 3.38e-120 | True |
| nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 11331 | 6664 | 4667 | 58.8 | 1.15e-74 | True |
| ph2_atrtrend_20_ge0p9 | path bank v2 question | 4804 | 2187 | 2617 | 45.5 | 3.73e-06 | False |
| ph2_atrtrend_20_ge1p0 | path bank v2 question | 6125 | 2820 | 3305 | 46 | 3.73e-06 | False |
| ph2_rngexp_20_ge1p0 | path bank v2 question | 6274 | 2909 | 3365 | 46.4 | 2.6e-05 | False |
| TEC-TR-00410-BUT-C|60 | sheet:TR (Theme Radar) | 5565 | 2996 | 2569 | 53.8 | 2.6e-05 | False |
| TEC-TR-00410-BUT-C|20 | sheet:TR (Theme Radar) | 5565 | 2996 | 2569 | 53.8 | 2.6e-05 | False |
| TEC-TR-00410-BUT-C|10 | sheet:TR (Theme Radar) | 5565 | 2996 | 2569 | 53.8 | 2.6e-05 | False |
| TEC-TR-00410-BUT-C|5 | sheet:TR (Theme Radar) | 5565 | 2996 | 2569 | 53.8 | 2.6e-05 | False |
| TEC-TR-00410-BUT-C|1 | sheet:TR (Theme Radar) | 5565 | 2996 | 2569 | 53.8 | 2.6e-05 | False |
| TEC-TR-00410-BUT-C|3 | sheet:TR (Theme Radar) | 5565 | 2996 | 2569 | 53.8 | 2.6e-05 | False |
| ph2_dipatr_40_ge5 | path bank v2 question | 6125 | 3274 | 2851 | 53.5 | 0.000146 | False |
| TEC-TR-00457-C|60 | sheet:TR (Theme Radar) | 3373 | 1530 | 1843 | 45.4 | 0.000146 | False |
| ph2_disth_50_le0p5 | path bank v2 question | 1151 | 484 | 667 | 42.1 | 0.000146 | False |
| ph2_atrtrend_25_ge1p0 | path bank v2 question | 6410 | 2990 | 3420 | 46.6 | 0.000149 | False |

### q5_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 3119 | 1835 | 1284 | 58.8 | 5.51e-19 | True |
| nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 3371 | 1853 | 1518 | 55 | 2.6e-05 | False |
| ph2_hlrun_40_ge6 | path bank v2 question | 2350 | 1292 | 1058 | 55 | 0.00144 | False |
| ph2_abv10frac_30_ge0p7 | path bank v2 question | 913 | 528 | 385 | 57.8 | 0.002 | True |
| ph2_xc20up_20_eq1 | path bank v2 question | 1075 | 461 | 614 | 42.9 | 0.00255 | False |
| TEC-TR-00421-C|3 | sheet:TR (Theme Radar) | 219 | 144 | 75 | 65.8 | 0.00264 | True |
| ph2_hlrun_50_ge6 | path bank v2 question | 2445 | 1336 | 1109 | 54.6 | 0.00285 | False |
| ph2_abv20run_20_ge20 | path bank v2 question | 928 | 534 | 394 | 57.5 | 0.00285 | True |
| ph2_slope_30_gt0p02 | path bank v2 question | 355 | 220 | 135 | 62 | 0.00418 | True |
| ph2_nr7cnt_30_ge5 | path bank v2 question | 2449 | 1114 | 1335 | 45.5 | 0.00448 | False |
| ph2_abv10frac_25_ge0p7 | path bank v2 question | 1104 | 626 | 478 | 56.7 | 0.00456 | True |
| ph2_xc20up_25_eq1 | path bank v2 question | 511 | 207 | 304 | 40.5 | 0.00804 | False |
| ph2_insidecnt_30_ge2 | path bank v2 question | 822 | 350 | 472 | 42.6 | 0.00869 | False |
| ph2_nr7cnt_25_ge4 | path bank v2 question | 2454 | 1122 | 1332 | 45.7 | 0.00883 | False |
| ph2_uwickmean_15_ge0p2 | path bank v2 question | 903 | 515 | 388 | 57 | 0.0095 | True |

### q7_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 1239 | 698 | 541 | 56.3 | 0.00456 | True |
| TEC-TR-01082-BUT-C|60 | sheet:TR (Theme Radar) | 106 | 30 | 76 | 28.3 | 0.00456 | False |
| ph2_vdry_30_le0p8 | path bank v2 question | 300 | 112 | 188 | 37.3 | 0.00634 | False |
| grid_lgE42L5_voltrend [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 1119 | 630 | 489 | 56.3 | 0.00957 | True |
| PRC-TR-00685-C|10 | sheet:TR (Theme Radar) | 191 | 67 | 124 | 35.1 | 0.0137 | False |
| ph2_atrtrend_60_ge1p25 | path bank v2 question | 628 | 364 | 264 | 58 | 0.0193 | True |
| nb4-REL-NB-025-DUR90-ZTQ | sheet:NB (New Bot) | 69 | 18 | 51 | 26.1 | 0.0201 | False |
| ph2_rngexp_40_ge0p9 | path bank v2 question | 765 | 437 | 328 | 57.1 | 0.0205 | True |
| ph2_rngcomp_20_le0p6 | path bank v2 question | 808 | 348 | 460 | 43.1 | 0.0205 | False |
| ph2_nr7cnt_15_ge2 | path bank v2 question | 732 | 313 | 419 | 42.8 | 0.0218 | False |
| ph2_hlrun_50_ge6 | path bank v2 question | 863 | 489 | 374 | 56.7 | 0.0218 | True |
| grid_trL120_voltrend [NEW, tercile] | lookback grid (LOOKBACK_GRID.md) | 1171 | 519 | 652 | 44.3 | 0.0231 | False |
| PRC-TR-00673-C|5 | sheet:TR (Theme Radar) | 96 | 29 | 67 | 30.2 | 0.0256 | False |
| PRC-TR-00673-C|1 | sheet:TR (Theme Radar) | 96 | 29 | 67 | 30.2 | 0.0256 | False |
| PRC-TR-00673-C|20 | sheet:TR (Theme Radar) | 96 | 29 | 67 | 30.2 | 0.0256 | False |

### q8_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_pctbmean_25_ge0p7 | path bank v2 question | 299 | 192 | 107 | 64.2 | 0.00107 | True |
| ph2_pctbmean_20_ge0p8 | path bank v2 question | 120 | 84 | 36 | 70 | 0.00643 | True |
| ph2_abv20frac_60_ge0p4 | path bank v2 question | 566 | 334 | 232 | 59 | 0.00804 | True |
| ph2_abv10frac_30_ge0p6 | path bank v2 question | 444 | 267 | 177 | 60.1 | 0.00853 | True |
| ph2_dsl_60_le0p4 | path bank v2 question | 618 | 257 | 361 | 41.6 | 0.0105 | False |
| OUT-TR-01201-C|60 | sheet:TR (Theme Radar) | 97 | 69 | 28 | 71.1 | 0.0117 | True |
| TEC-TR-00554-BUT-C|60 | sheet:TR (Theme Radar) | 505 | 207 | 298 | 41 | 0.0162 | False |
| ph2_dsl_60_le0p2 | path bank v2 question | 235 | 87 | 148 | 37 | 0.0198 | False |
| ph2_abv10frac_25_ge0p7 | path bank v2 question | 165 | 108 | 57 | 65.5 | 0.0201 | True |
| PRC-TR-01346-BUT-C|20 | sheet:TR (Theme Radar) | 443 | 180 | 263 | 40.6 | 0.0206 | False |
| ph2_pctbmean_20_ge0p7 | path bank v2 question | 409 | 244 | 165 | 59.7 | 0.023 | True |
| PRC-TR-01382-BUT-C|20 | sheet:TR (Theme Radar) | 461 | 189 | 272 | 41 | 0.0256 | False |
| ph2_dsl_60_le0p3 | path bank v2 question | 372 | 149 | 223 | 40.1 | 0.0271 | False |
| ph2_dsl_50_le0p3 | path bank v2 question | 318 | 125 | 193 | 39.3 | 0.0292 | False |
| ph2_nl20_50_ge5 | path bank v2 question | 616 | 261 | 355 | 42.4 | 0.0304 | False |

## (a2) Item win-rate ranking across all tradable setup days (YES vs NO; NEW rows: top vs bottom tercile), BH across all items × setups × horizons

HINT candidates (>55% win in the better bucket, n ≥ 30, q < 0.1): **7740** of 168,459 tests.

| setup | h | item | source | n YES/top | win% YES/top | n NO/bottom | win% NO/bottom | base win% | effect h | q | HINT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 10 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 12943 | 58 | 17028 | 40.4 | 48.7 | 0.353 | 8.12e-195 | True |
| chartpass_all6 | 21 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 12943 | 58 | 17028 | 40.4 | 48.7 | 0.353 | 8.12e-195 | True |
| chartpass_all6 | 5 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 12943 | 58 | 17028 | 40.4 | 48.7 | 0.353 | 8.12e-195 | True |
| chartpass_all6 | 10 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 13018 | 56.9 | 16113 | 41.9 | 48.7 | 0.301 | 3.89e-138 | True |
| chartpass_all6 | 5 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 13018 | 56.9 | 16113 | 41.9 | 48.7 | 0.301 | 3.89e-138 | True |
| chartpass_all6 | 21 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 13018 | 56.9 | 16113 | 41.9 | 48.7 | 0.301 | 3.89e-138 | True |
| q5_in_all6 | 10 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 5267 | 59 | 4768 | 43.9 | 51.9 | 0.303 | 2.57e-47 | True |
| q5_in_all6 | 21 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 5267 | 59 | 4768 | 43.9 | 51.9 | 0.303 | 2.57e-47 | True |
| q5_in_all6 | 5 | nn_win126 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 5267 | 59 | 4768 | 43.9 | 51.9 | 0.303 | 2.57e-47 | True |
| q5_in_all6 | 5 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 5330 | 57 | 4127 | 46.4 | 51.9 | 0.213 | 1.37e-20 | True |
| q5_in_all6 | 10 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 5330 | 57 | 4127 | 46.4 | 51.9 | 0.213 | 1.37e-20 | True |
| q5_in_all6 | 21 | nn_win60 [NEW, tercile] | path-level v2 / shape (LOOKBACK_GRID.md) | 5330 | 57 | 4127 | 46.4 | 51.9 | 0.213 | 1.37e-20 | True |
| q5_in_all6 | 10 | MAC-JA-675 | sheet:SHARED (market rows) | 1385 | 39.4 | 13435 | 53.2 | 51.9 | -0.278 | 9.61e-19 | False |
| q5_in_all6 | 5 | MAC-JA-675 | sheet:SHARED (market rows) | 1385 | 39.4 | 13435 | 53.2 | 51.9 | -0.278 | 9.61e-19 | False |
| q5_in_all6 | 21 | MAC-JA-675 | sheet:SHARED (market rows) | 1385 | 39.4 | 13435 | 53.2 | 51.9 | -0.278 | 9.61e-19 | False |
| q5_in_all6 | 21 | MAC-JA-675-BUT | sheet:SHARED (market rows) | 1385 | 39.4 | 13435 | 53.2 | 51.9 | -0.278 | 9.61e-19 | False |
| q5_in_all6 | 10 | MAC-JA-675-BUT | sheet:SHARED (market rows) | 1385 | 39.4 | 13435 | 53.2 | 51.9 | -0.278 | 9.61e-19 | False |
| q5_in_all6 | 5 | MAC-JA-675-BUT | sheet:SHARED (market rows) | 1385 | 39.4 | 13435 | 53.2 | 51.9 | -0.278 | 9.61e-19 | False |
| chartpass_all6 | 21 | MKT-JA-945 | sheet:SHARED (market rows) | 543 | 27.8 | 33865 | 48.9 | 48.7 | -0.437 | 1.36e-18 | False |
| chartpass_all6 | 21 | MKT-JA-945-BUT | sheet:SHARED (market rows) | 543 | 27.8 | 33865 | 48.9 | 48.7 | -0.437 | 1.36e-18 | False |
| chartpass_all6 | 10 | MKT-JA-945-BUT | sheet:SHARED (market rows) | 543 | 27.8 | 33865 | 48.9 | 48.7 | -0.437 | 1.36e-18 | False |
| chartpass_all6 | 10 | MKT-JA-945 | sheet:SHARED (market rows) | 543 | 27.8 | 33865 | 48.9 | 48.7 | -0.437 | 1.36e-18 | False |
| chartpass_all6 | 5 | MKT-JA-945-BUT | sheet:SHARED (market rows) | 543 | 27.8 | 33865 | 48.9 | 48.7 | -0.437 | 1.36e-18 | False |
| chartpass_all6 | 5 | MKT-JA-945 | sheet:SHARED (market rows) | 543 | 27.8 | 33865 | 48.9 | 48.7 | -0.437 | 1.36e-18 | False |
| chartpass_all6 | 10 | MKT-JA-1145 | sheet:SHARED (market rows) | 461 | 26.2 | 33947 | 48.8 | 48.7 | -0.472 | 3.27e-18 | False |

### Cyrus's NEW rows (chains, 40-bar trend/drawdown, 2-month trend, red:green ratio, last green vs red body, RSI, MACD, RVOL, BB, SMA distance) — best horizon per setup

| setup | h | item | n top | win% top | n bottom | win% bottom | effect h | q |
|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 10 | nn_win126 [NEW, tercile] | 12943 | 58 | 17028 | 40.4 | 0.353 | 8.12e-195 |
| chartpass_all6 | 21 | nn_win60 [NEW, tercile] | 13018 | 56.9 | 16113 | 41.9 | 0.301 | 3.89e-138 |
| q5_in_all6 | 5 | nn_win126 [NEW, tercile] | 5267 | 59 | 4768 | 43.9 | 0.303 | 2.57e-47 |
| q5_in_all6 | 21 | nn_win60 [NEW, tercile] | 5330 | 57 | 4127 | 46.4 | 0.213 | 1.37e-20 |
| q7_in_all6 | 5 | nn_win60 [NEW, tercile] | 1817 | 57.3 | 2285 | 44.2 | 0.263 | 2.85e-13 |
| chartpass_all6 | 10 | grid_lgE63L21_voltrend [NEW, tercile] | 14453 | 46.6 | 14036 | 50.1 | -0.0704 | 8.8e-07 |
| q8_in_all6 | 21 | nn_win126 [NEW, tercile] | 1367 | 55.4 | 1821 | 44.9 | 0.21 | 1.33e-06 |
| chartpass_all6 | 21 | grid_lgE126L21_rchain_len [NEW, tercile] | 11024 | 46.1 | 20456 | 49.5 | -0.0689 | 1.46e-06 |
| chartpass_all6 | 21 | grid_lgE63L10_voltrend [NEW, tercile] | 14075 | 46.7 | 14505 | 49.9 | -0.0647 | 7.66e-06 |
| chartpass_all6 | 10 | grid_lgE126L5_gchain_move [NEW, tercile] | 14240 | 46.7 | 13321 | 50 | -0.0657 | 8.39e-06 |
| q7_in_all6 | 5 | nn_win126 [NEW, tercile] | 1375 | 55.6 | 2970 | 46.8 | 0.178 | 8.69e-06 |
| chartpass_all6 | 5 | grid_lgE21L21_voltrend [NEW, tercile] | 14352 | 50.8 | 14664 | 47.7 | 0.0612 | 2.42e-05 |
| chartpass_all6 | 10 | grid_lgE5L10_rchain_move [NEW, tercile] | 15633 | 47.2 | 13376 | 50.3 | -0.0612 | 2.57e-05 |
| q8_in_all6 | 5 | nn_win60 [NEW, tercile] | 1761 | 53.2 | 1555 | 44.2 | 0.18 | 3.07e-05 |
| chartpass_all6 | 21 | new_rmove60_max [NEW, tercile] | 15115 | 47.5 | 13765 | 50.3 | -0.0565 | 0.000126 |
| q8_in_all6 | 10 | grid_lgE42L5_voltrend [NEW, tercile] | 1763 | 54.5 | 1728 | 46.4 | 0.162 | 0.000131 |
| chartpass_all6 | 5 | grid_lgE126L10_gchain_move [NEW, tercile] | 14184 | 47.4 | 13271 | 50.3 | -0.0571 | 0.000164 |
| chartpass_all6 | 5 | grid_trL60_rchain_move [NEW, tercile] | 15142 | 47.5 | 13772 | 50.2 | -0.0551 | 0.000199 |
| chartpass_all6 | 21 | grid_lgE5L21_rchain_move [NEW, tercile] | 15653 | 47.4 | 13249 | 50.2 | -0.0552 | 0.000206 |
| chartpass_all6 | 5 | grid_lgE42L21_rchain_move [NEW, tercile] | 15170 | 47.3 | 13659 | 50 | -0.0542 | 0.000273 |
| chartpass_all6 | 21 | grid_lgE63L10_gchain_move [NEW, tercile] | 14836 | 47.1 | 14015 | 49.8 | -0.0538 | 0.000309 |
| chartpass_all6 | 10 | grid_lgE10L21_rchain_move [NEW, tercile] | 15374 | 47.3 | 13494 | 50 | -0.0538 | 0.000314 |
| chartpass_all6 | 5 | grid_lgE126L21_rchain_move [NEW, tercile] | 14190 | 47.6 | 12994 | 50.4 | -0.0551 | 0.000342 |
| chartpass_all6 | 21 | grid_lgE42L5_voltrend [NEW, tercile] | 14652 | 49.7 | 14250 | 47 | 0.0527 | 0.000417 |
| chartpass_all6 | 10 | new_gr250_moveratio [NEW, tercile] | 12633 | 47.4 | 11938 | 50.2 | -0.0566 | 0.000491 |
| q5_in_all6 | 5 | grid_lgE126L5_gchain_move [NEW, tercile] | 4618 | 48.9 | 4710 | 53.5 | -0.0918 | 0.000491 |
| q7_in_all6 | 21 | path2_base_shrink [NEW, tercile] | 1847 | 52.2 | 1269 | 44.2 | 0.161 | 0.000531 |
| chartpass_all6 | 21 | grid_lgE10L5_voltrend [NEW, tercile] | 15381 | 47.5 | 13867 | 50 | -0.0506 | 0.000738 |
| chartpass_all6 | 21 | grid_lgE126L10_voltrend [NEW, tercile] | 13541 | 49.7 | 13652 | 47 | 0.0524 | 0.000747 |
| chartpass_all6 | 21 | grid_lgE10L10_rchain_move [NEW, tercile] | 15710 | 47.3 | 13353 | 49.9 | -0.0506 | 0.000787 |

Files: `item_ranking.csv.gz` (every item × setup × h), `pair_item_aggregate.csv.gz`, `pair_diffs.csv.gz` (one row per pair; `top_items_differing` lists that setup's top-40 aggregate items where W and L differ: YES/NO, or T1–T3 terciles for NEW rows).
Coverage: sheet items = every row answered by the universe engine for 2020–24 (JG 1,478 ticker rows incl. BUT variants, NB 614, TR 2,808 row|N keys, SHARED 8,176 market rows) + 9 chart-picture story questions; the 6 chart-pass checks are the setup itself. NR answers are skipped, never guessed. SHARED rows rarely differ within a pair because pairs share the date.

