# Look-alike win/loss mining — PRACTICE 2020–24, **HINT only** (not evidence; 2025–26 sealed until the lock)

Prices `universe_2020_survivors.parquet` sha `fb9bbe69…ef337` (verified). Rows 2020-01-01..2024-12-31 only (asserted). Every feature uses bars < D; entry open D, exit open D+h, net of 30bp/side.
Win = stock net return beats the same-day mean of tradable matched controls (same base filter, rule = NO). Deterministic: no sampling, no seed needed (ties broken by ticker).

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

## Pairs (h=10d primary): every winner paired with its nearest loser in the same setup (same date first, ±7 days max, then fewest story-question differences, then ticker)

| setup | tradable events | winners | pairs | median items differing | casebook pairs |
|---|---|---|---|---|---|
| chartpass_all6 | 43,517 | 19,810 | 19,831 | 1446 | 42 |
| q5_in_all6 | 14,889 | 7,350 | 7,360 | 1446 | 21 |
| q7_in_all6 | 6,531 | 3,178 | 3,180 | 1404 | 14 |
| q8_in_all6 | 5,194 | 2,403 | 2,410 | 1538 | 25 |

## Honesty split (pair sign test): discover on 2020–22 pairs, confirm on 2023–24 pairs

Tested in discovery (n_differ ≥ 30): 28,662. Discovered (q<0.1 BH, |favour−50| > 5pp): 11,159. **Still hold on 2023–24** (same direction, >5pp, n ≥ 30, q<0.1 BH over discovered set): **6,479**.

| setup | item | source | disc n | disc winner-favour % | conf n | conf winner-favour % | q conf |
|---|---|---|---|---|---|---|---|
| chartpass_all6 | sq1_lower_highs3 | sheet:chart-picture v2 story Q | 757 | 80.4 | 608 | 84.2 | 8.5e-66 |
| chartpass_all6 | sq3_shrinking_green3 | sheet:chart-picture v2 story Q | 1064 | 76.0 | 740 | 80.8 | 6.5e-64 |
| chartpass_all6 | sq7_lowerbb_reclaim | sheet:chart-picture v2 story Q | 848 | 77.0 | 698 | 78.8 | 5.8e-52 |
| chartpass_all6 | sq8_above_last_red_high | sheet:chart-picture v2 story Q | 791 | 78.5 | 622 | 79.9 | 2.9e-50 |
| chartpass_all6 | ph2_maxup1d_60_ge0p3 | path bank v2 question | 1923 | 43.6 | 1601 | 34.6 | 2.2e-32 |
| chartpass_all6 | ph2_ret_15_ge0p05 | path bank v2 question | 2527 | 43.3 | 2151 | 37.4 | 8.3e-29 |
| chartpass_all6 | ph2_maxup1d_50_ge0p3 | path bank v2 question | 1801 | 42.8 | 1469 | 34.9 | 1.1e-28 |
| chartpass_all6 | ph2_maxup1d_30_ge0p3 | path bank v2 question | 1575 | 42.8 | 1325 | 34.1 | 1.5e-28 |
| chartpass_all6 | new_rmove60_max [NEW, tercile] | NEW (not on sheet) | 6708 | 44.7 | 5671 | 42.4 | 9.6e-28 |
| chartpass_all6 | sq4_below_mid_5of10 | sheet:chart-picture v2 story Q | 1099 | 64.8 | 798 | 69.9 | 2.1e-27 |
| chartpass_all6 | ph2_abv20frac_10_ge0p6 | path bank v2 question | 1099 | 35.2 | 798 | 30.1 | 2.1e-27 |
| chartpass_all6 | ph2_maxup1d_40_ge0p3 | path bank v2 question | 1678 | 42.8 | 1389 | 34.8 | 2.4e-27 |
| q5_in_all6 | sq7_lowerbb_reclaim | sheet:chart-picture v2 story Q | 431 | 65.0 | 398 | 80.9 | 4.4e-34 |
| q5_in_all6 | ph2_slope_20_gt0p002 | path bank v2 question | 1607 | 34.0 | 1339 | 32.9 | 1.1e-33 |
| q5_in_all6 | ph2_disth_10_le0p075 | path bank v2 question | 1305 | 65.6 | 1317 | 65.6 | 2.1e-27 |
| q5_in_all6 | ph2_slope_20_gt0p001 | path bank v2 question | 1245 | 34.1 | 1039 | 32.8 | 2.1e-26 |
| q5_in_all6 | ph2_disth_25_le0p075 | path bank v2 question | 1130 | 65.8 | 1221 | 65.7 | 8.2e-26 |
| q5_in_all6 | ph2_maxdn1d_30_ge0p05 | path bank v2 question | 1703 | 37.3 | 1544 | 36.2 | 3.5e-25 |
| q5_in_all6 | ph2_disth_20_le0p075 | path bank v2 question | 1141 | 65.6 | 1226 | 65.4 | 4.6e-25 |
| q5_in_all6 | ph2_maxdn1d_50_ge0p05 | path bank v2 question | 1515 | 40.0 | 1445 | 35.8 | 7.5e-25 |
| q5_in_all6 | ph2_disth_7_le0p075 | path bank v2 question | 1524 | 66.9 | 1399 | 64.3 | 1.8e-24 |
| q5_in_all6 | new_bb_width [NEW, tercile] | NEW (not on sheet) | 2510 | 37.8 | 2120 | 38.4 | 1.8e-24 |
| q5_in_all6 | ph2_disth_15_le0p075 | path bank v2 question | 1169 | 65.7 | 1242 | 64.9 | 8.5e-24 |
| q5_in_all6 | ph2_abv20frac_10_ge0p6 | path bank v2 question | 528 | 29.5 | 545 | 27.7 | 8.5e-24 |
| q7_in_all6 | ph2_disth_60_le0p1 | path bank v2 question | 642 | 60.7 | 611 | 66.4 | 5.1e-15 |
| q7_in_all6 | ph2_maxdd_50_ge0p1 | path bank v2 question | 556 | 40.8 | 591 | 33.5 | 1.2e-14 |
| q7_in_all6 | ph2_disth_50_le0p1 | path bank v2 question | 684 | 60.2 | 642 | 65.7 | 1.7e-14 |
| q7_in_all6 | ph2_maxdd_60_ge0p1 | path bank v2 question | 479 | 40.9 | 548 | 33.6 | 1.4e-13 |
| q7_in_all6 | ph2_gapup2_20_ge4 | path bank v2 question | 356 | 30.9 | 179 | 21.8 | 1.7e-13 |
| q7_in_all6 | ph2_gapup2_30_ge5 | path bank v2 question | 420 | 35.5 | 229 | 25.3 | 4.1e-13 |
| q7_in_all6 | ph2_slope_15_gtm0p005 | path bank v2 question | 634 | 60.9 | 530 | 66.0 | 1.2e-12 |
| q7_in_all6 | ph2_disth_40_le0p1 | path bank v2 question | 725 | 59.2 | 667 | 64.2 | 2e-12 |
| q7_in_all6 | ph2_maxdn1d_30_ge0p03 | path bank v2 question | 420 | 40.5 | 441 | 32.7 | 2.2e-12 |
| q7_in_all6 | ph2_gapup2_20_ge3 | path bank v2 question | 474 | 36.7 | 315 | 29.8 | 4.6e-12 |
| q7_in_all6 | ph2_natr_30_ge0p02 | path bank v2 question | 276 | 36.6 | 372 | 31.5 | 5e-12 |
| q7_in_all6 | ph2_gapup2_25_ge5 | path bank v2 question | 354 | 32.2 | 167 | 22.8 | 6.3e-12 |
| q8_in_all6 | new_gmove60_max [NEW, tercile] | NEW (not on sheet) | 813 | 40.5 | 660 | 33.5 | 3.8e-16 |
| q8_in_all6 | ph2_natr_20_ge0p04 | path bank v2 question | 570 | 37.9 | 484 | 31.6 | 6.3e-15 |
| q8_in_all6 | ph2_gapup2_60_ge4 | path bank v2 question | 554 | 42.8 | 507 | 32.3 | 1.9e-14 |
| q8_in_all6 | ph2_maxdn1d_30_ge0p05 | path bank v2 question | 513 | 39.4 | 453 | 31.3 | 1.9e-14 |
| q8_in_all6 | new_bb_width [NEW, tercile] | NEW (not on sheet) | 814 | 39.9 | 658 | 34.5 | 2e-14 |
| q8_in_all6 | ph2_distl_10_le0p03 | path bank v2 question | 248 | 64.5 | 356 | 70.8 | 3.4e-14 |
| q8_in_all6 | ph2_distl_15_le0p15 | path bank v2 question | 470 | 60.9 | 330 | 71.5 | 4e-14 |
| q8_in_all6 | ph2_natr_10_ge0p04 | path bank v2 question | 567 | 37.0 | 476 | 32.1 | 6.1e-14 |
| q8_in_all6 | ph2_maxdd_15_ge0p075 | path bank v2 question | 317 | 40.4 | 381 | 30.2 | 8.2e-14 |
| q8_in_all6 | ph2_natr_25_ge0p03 | path bank v2 question | 399 | 42.6 | 441 | 31.7 | 1.5e-13 |
| q8_in_all6 | ph2_maxdn1d_25_ge0p05 | path bank v2 question | 538 | 39.8 | 462 | 32.3 | 2e-13 |
| q8_in_all6 | ph2_natr_20_ge0p07 | path bank v2 question | 575 | 36.7 | 415 | 31.3 | 2.2e-13 |

## (b) Items that most often differ in the winner's favour (pair sign test, BH across all items × setups)

HINT candidates (winner-favour > 55%, n_differ ≥ 30, q < 0.1): **3836** of 31,290 tested.

### chartpass_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| sq1_lower_highs3 | sheet:chart-picture v2 story Q | 1365 | 1121 | 244 | 82.1 | 5.91e-130 | True |
| sq3_shrinking_green3 | sheet:chart-picture v2 story Q | 1804 | 1407 | 397 | 78 | 6.57e-128 | True |
| sq8_above_last_red_high | sheet:chart-picture v2 story Q | 1413 | 1118 | 295 | 79.1 | 8.11e-109 | True |
| sq7_lowerbb_reclaim | sheet:chart-picture v2 story Q | 1546 | 1203 | 343 | 77.8 | 4.87e-108 | True |
| sq5_big_red_recent | sheet:chart-picture v2 story Q | 1898 | 1310 | 588 | 69 | 2.18e-59 | True |
| ph2_slope_20_gt0p001 | path bank v2 question | 5514 | 2200 | 3314 | 39.9 | 6.61e-48 | False |
| ph2_abv20frac_10_ge0p6 | path bank v2 question | 1897 | 627 | 1270 | 33.1 | 6.03e-47 | False |
| sq4_below_mid_5of10 | sheet:chart-picture v2 story Q | 1897 | 1270 | 627 | 66.9 | 6.03e-47 | True |
| ph2_slope_20_gt0p002 | path bank v2 question | 6461 | 2635 | 3826 | 40.8 | 1.04e-46 | False |
| sq2_higher_lows3 | sheet:chart-picture v2 story Q | 1837 | 1232 | 605 | 67.1 | 3.86e-46 | True |
| new_rmove60_max [NEW, tercile] | NEW (not on sheet) | 12379 | 5400 | 6979 | 43.6 | 7.95e-43 | False |
| ph2_maxup1d_20_ge0p1 | path bank v2 question | 7758 | 3263 | 4495 | 42.1 | 1.05e-41 | False |
| ph2_maxup1d_25_ge0p1 | path bank v2 question | 7915 | 3336 | 4579 | 42.1 | 1.29e-41 | False |
| ph2_pctbmean_7_ge0p5 | path bank v2 question | 5250 | 2128 | 3122 | 40.5 | 3.01e-40 | False |
| ph2_maxup1d_30_ge0p02 | path bank v2 question | 2097 | 739 | 1358 | 35.2 | 2.14e-39 | False |

### q5_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_slope_20_gt0p002 | path bank v2 question | 2946 | 986 | 1960 | 33.5 | 2.15e-69 | False |
| ph2_disth_7_le0p075 | path bank v2 question | 2923 | 1918 | 1005 | 65.6 | 3.61e-61 | True |
| new_bb_width [NEW, tercile] | NEW (not on sheet) | 4630 | 1762 | 2868 | 38.1 | 2.88e-56 | False |
| ph2_disth_10_le0p075 | path bank v2 question | 2622 | 1720 | 902 | 65.6 | 1.07e-54 | True |
| ph2_maxdd_7_ge0p075 | path bank v2 question | 3185 | 1145 | 2040 | 35.9 | 9.26e-54 | False |
| ph2_slope_20_gt0p001 | path bank v2 question | 2284 | 766 | 1518 | 33.5 | 3.36e-53 | False |
| ph2_natr_15_ge0p03 | path bank v2 question | 2798 | 992 | 1806 | 35.5 | 1.22e-50 | False |
| ph2_disth_25_le0p075 | path bank v2 question | 2351 | 1545 | 806 | 65.7 | 8.57e-50 | True |
| ph2_natr_20_ge0p03 | path bank v2 question | 2817 | 1006 | 1811 | 35.7 | 3.47e-49 | False |
| ph2_disth_5_le0p075 | path bank v2 question | 3262 | 2063 | 1199 | 63.2 | 7.36e-49 | True |
| ph2_disth_20_le0p075 | path bank v2 question | 2367 | 1550 | 817 | 65.5 | 1.1e-48 | True |
| ph2_maxdn1d_30_ge0p05 | path bank v2 question | 3247 | 1195 | 2052 | 36.8 | 2.45e-48 | False |
| ph2_disth_15_le0p075 | path bank v2 question | 2411 | 1574 | 837 | 65.3 | 2.45e-48 | True |
| ph2_disth_30_le0p1 | path bank v2 question | 3250 | 2044 | 1206 | 62.9 | 3.37e-46 | True |
| ph2_maxdd_10_ge0p075 | path bank v2 question | 2875 | 1047 | 1828 | 36.4 | 2e-45 | False |

### q7_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| PRC-TR-00662-BUT-C|5 | sheet:TR (Theme Radar) | 1194 | 408 | 786 | 34.2 | 2.17e-26 | False |
| PRC-TR-00662-BUT-C|10 | sheet:TR (Theme Radar) | 1194 | 408 | 786 | 34.2 | 2.17e-26 | False |
| PRC-TR-00662-BUT-C|20 | sheet:TR (Theme Radar) | 1194 | 408 | 786 | 34.2 | 2.17e-26 | False |
| PRC-TR-00662-BUT-C|60 | sheet:TR (Theme Radar) | 1194 | 408 | 786 | 34.2 | 2.17e-26 | False |
| PRC-TR-00662-BUT-C|3 | sheet:TR (Theme Radar) | 1194 | 408 | 786 | 34.2 | 2.17e-26 | False |
| PRC-TR-00662-BUT-C|1 | sheet:TR (Theme Radar) | 1194 | 408 | 786 | 34.2 | 2.17e-26 | False |
| ph2_gapdn5_10_ge1 | path bank v2 question | 1009 | 336 | 673 | 33.3 | 6.04e-25 | False |
| ph2_gapup2_20_ge4 | path bank v2 question | 535 | 149 | 386 | 27.9 | 1.26e-23 | False |
| ph2_gapdn5_7_ge1 | path bank v2 question | 886 | 290 | 596 | 32.7 | 1.67e-23 | False |
| new_bb_width [NEW, tercile] | NEW (not on sheet) | 1805 | 685 | 1120 | 38 | 3.94e-23 | False |
| ph2_gapdn5_20_ge1 | path bank v2 question | 1090 | 377 | 713 | 34.6 | 5.62e-23 | False |
| ph2_gapdn5_15_ge1 | path bank v2 question | 1063 | 366 | 697 | 34.4 | 7.1e-23 | False |
| ph2_accel_25_gtm0p02 | path bank v2 question | 966 | 639 | 327 | 66.1 | 2.09e-22 | True |
| ph2_gapdn5_25_ge1 | path bank v2 question | 1136 | 399 | 737 | 35.1 | 2.58e-22 | False |
| ph2_disth_60_le0p1 | path bank v2 question | 1253 | 796 | 457 | 63.5 | 2.17e-20 | True |

### q8_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_disth_20_le0p15 | path bank v2 question | 1070 | 700 | 370 | 65.4 | 1.36e-22 | True |
| ph2_disth_25_le0p15 | path bank v2 question | 1070 | 699 | 371 | 65.3 | 2.51e-22 | True |
| ph2_natr_10_ge0p04 | path bank v2 question | 1043 | 363 | 680 | 34.8 | 2e-21 | False |
| ph2_disth_50_le0p15 | path bank v2 question | 1113 | 720 | 393 | 64.7 | 2.37e-21 | True |
| ph2_maxdd_50_ge0p2 | path bank v2 question | 1113 | 393 | 720 | 35.3 | 2.37e-21 | False |
| ph2_natr_20_ge0p07 | path bank v2 question | 990 | 341 | 649 | 34.4 | 2.5e-21 | False |
| PRC-TR-01873-C|20 | sheet:TR (Theme Radar) | 1040 | 363 | 677 | 34.9 | 4.3e-21 | False |
| ph2_natr_20_ge0p04 | path bank v2 question | 1054 | 369 | 685 | 35 | 4.48e-21 | False |
| new_gmove60_max [NEW, tercile] | NEW (not on sheet) | 1473 | 550 | 923 | 37.3 | 6.05e-21 | False |
| ph2_distl_25_le0p1 | path bank v2 question | 1099 | 710 | 389 | 64.6 | 7.48e-21 | True |
| ph2_maxdd_30_ge0p2 | path bank v2 question | 1042 | 365 | 677 | 35 | 8.62e-21 | False |
| PRC-TR-01718-BUT-C|5 | sheet:TR (Theme Radar) | 1103 | 391 | 712 | 35.4 | 8.85e-21 | False |
| PRC-TR-01718-BUT-C|20 | sheet:TR (Theme Radar) | 1103 | 391 | 712 | 35.4 | 8.85e-21 | False |
| PRC-TR-01718-BUT-C|10 | sheet:TR (Theme Radar) | 1103 | 391 | 712 | 35.4 | 8.85e-21 | False |
| PRC-TR-01718-BUT-C|60 | sheet:TR (Theme Radar) | 1103 | 391 | 712 | 35.4 | 8.85e-21 | False |

## (a2) Item win-rate ranking across all tradable setup days (YES vs NO; NEW rows: top vs bottom tercile), BH across all items × setups × horizons

HINT candidates (>55% win in the better bucket, n ≥ 30, q < 0.1): **8888** of 162,230 tests.

| setup | h | item | source | n YES/top | win% YES/top | n NO/bottom | win% NO/bottom | base win% | effect h | q | HINT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 21 | ph2_maxup1d_40_ge0p1 | path bank v2 question | 16206 | 38.2 | 26818 | 48.4 | 44.6 | -0.207 | 8.03e-90 | False |
| chartpass_all6 | 21 | ph2_maxup1d_30_ge0p1 | path bank v2 question | 15332 | 38 | 27692 | 48.2 | 44.6 | -0.207 | 4.77e-88 | False |
| chartpass_all6 | 21 | ph2_maxup1d_25_ge0p1 | path bank v2 question | 14977 | 37.9 | 28047 | 48.1 | 44.6 | -0.208 | 1.02e-87 | False |
| chartpass_all6 | 21 | ph2_maxup1d_20_ge0p1 | path bank v2 question | 14471 | 37.7 | 28553 | 48 | 44.6 | -0.209 | 2.99e-87 | False |
| chartpass_all6 | 21 | ph2_maxup1d_50_ge0p1 | path bank v2 question | 17418 | 38.7 | 25606 | 48.5 | 44.6 | -0.199 | 4.68e-86 | False |
| chartpass_all6 | 21 | ph2_natr_25_ge0p07 | path bank v2 question | 12345 | 37 | 30679 | 47.6 | 44.6 | -0.216 | 9.99e-86 | False |
| chartpass_all6 | 21 | ph2_natr_20_ge0p07 | path bank v2 question | 12517 | 37 | 30507 | 47.6 | 44.6 | -0.215 | 9.99e-86 | False |
| chartpass_all6 | 21 | ph2_natr_30_ge0p07 | path bank v2 question | 12189 | 36.9 | 30835 | 47.6 | 44.6 | -0.216 | 1.59e-84 | False |
| chartpass_all6 | 21 | ph2_maxup1d_15_ge0p075 | path bank v2 question | 16341 | 38.6 | 26683 | 48.2 | 44.6 | -0.195 | 1.04e-80 | False |
| chartpass_all6 | 21 | ph2_natr_40_ge0p07 | path bank v2 question | 12058 | 37.1 | 30966 | 47.5 | 44.6 | -0.21 | 9.61e-80 | False |
| chartpass_all6 | 21 | ph2_distl_25_le0p15 | path bank v2 question | 30794 | 47.5 | 12230 | 37.2 | 44.6 | 0.208 | 3.37e-79 | False |
| chartpass_all6 | 21 | ph2_disth_15_le0p15 | path bank v2 question | 27080 | 48.1 | 15944 | 38.5 | 44.6 | 0.193 | 8.83e-79 | False |
| chartpass_all6 | 21 | ph2_maxup1d_15_ge0p1 | path bank v2 question | 11862 | 37.1 | 31162 | 47.4 | 44.6 | -0.21 | 1.3e-78 | False |
| chartpass_all6 | 21 | ph2_maxup1d_50_ge0p15 | path bank v2 question | 10825 | 36.6 | 32199 | 47.2 | 44.6 | -0.215 | 5.2e-78 | False |
| chartpass_all6 | 21 | ph2_natr_60_ge0p07 | path bank v2 question | 12004 | 37.2 | 31020 | 47.4 | 44.6 | -0.208 | 8.45e-78 | False |
| chartpass_all6 | 21 | ph2_disth_20_le0p15 | path bank v2 question | 26526 | 48.2 | 16498 | 38.7 | 44.6 | 0.191 | 8.45e-78 | False |
| chartpass_all6 | 21 | ph2_disth_25_le0p15 | path bank v2 question | 26455 | 48.2 | 16569 | 38.8 | 44.6 | 0.191 | 8.45e-78 | False |
| chartpass_all6 | 21 | ph2_natr_7_ge0p05 | path bank v2 question | 18995 | 39.4 | 24029 | 48.6 | 44.6 | -0.186 | 1.01e-77 | False |
| chartpass_all6 | 21 | ph2_maxup1d_20_ge0p075 | path bank v2 question | 19472 | 39.5 | 23552 | 48.7 | 44.6 | -0.186 | 1.29e-77 | False |
| chartpass_all6 | 21 | ph2_distl_40_le0p2 | path bank v2 question | 32166 | 47.2 | 10858 | 36.7 | 44.6 | 0.214 | 2.17e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|1 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.55e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|10 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.55e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|20 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.55e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|60 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.55e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|3 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.55e-77 | False |

### Cyrus's NEW rows (chains, 40-bar trend/drawdown, 2-month trend, red:green ratio, last green vs red body, RSI, MACD, RVOL, BB, SMA distance) — best horizon per setup

| setup | h | item | n top | win% top | n bottom | win% bottom | effect h | q |
|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 21 | new_gmove60_max [NEW, tercile] | 15319 | 38.4 | 13374 | 49.5 | -0.226 | 3.15e-77 |
| chartpass_all6 | 21 | new_rmove60_max [NEW, tercile] | 15032 | 38.9 | 13641 | 49.9 | -0.223 | 1.1e-75 |
| chartpass_all6 | 21 | new_bb_width [NEW, tercile] | 15254 | 38.9 | 13583 | 49.6 | -0.216 | 1.68e-71 |
| chartpass_all6 | 21 | new_maxdd40 [NEW, tercile] | 13673 | 49 | 15090 | 39.3 | 0.196 | 6.13e-59 |
| chartpass_all6 | 21 | new_gr250_moveratio [NEW, tercile] | 12545 | 40.2 | 11840 | 49.6 | -0.189 | 1.17e-46 |
| chartpass_all6 | 21 | new_gr60_moveratio [NEW, tercile] | 15149 | 40.8 | 13598 | 47.6 | -0.137 | 1.14e-28 |
| q5_in_all6 | 21 | new_rmove60_max [NEW, tercile] | 4470 | 41.5 | 5070 | 53.2 | -0.234 | 8.48e-28 |
| q5_in_all6 | 21 | new_gmove60_max [NEW, tercile] | 4591 | 42.6 | 5011 | 53.2 | -0.213 | 3.11e-23 |
| chartpass_all6 | 21 | new_slope40 [NEW, tercile] | 15048 | 40.7 | 14102 | 46.7 | -0.121 | 5.32e-23 |
| q5_in_all6 | 21 | new_maxdd40 [NEW, tercile] | 5116 | 52.8 | 4446 | 42.3 | 0.211 | 1.3e-22 |
| q5_in_all6 | 21 | new_bb_width [NEW, tercile] | 4904 | 42.6 | 4634 | 53 | -0.209 | 2.19e-22 |
| chartpass_all6 | 21 | new_rsi14 [NEW, tercile] | 14607 | 41.6 | 14041 | 47 | -0.108 | 4.29e-18 |
| q8_in_all6 | 21 | new_gmove60_max [NEW, tercile] | 1991 | 37.5 | 1590 | 52.4 | -0.301 | 2.88e-17 |
| chartpass_all6 | 21 | new_rvol20 [NEW, tercile] | 13044 | 46.4 | 15629 | 41.2 | 0.105 | 6.36e-17 |
| q8_in_all6 | 21 | new_rmove60_max [NEW, tercile] | 2082 | 38.8 | 1506 | 53.1 | -0.288 | 1.06e-15 |
| chartpass_all6 | 21 | new_dist_sma10 [NEW, tercile] | 13624 | 46.1 | 15066 | 41.6 | 0.0896 | 1.44e-12 |
| q8_in_all6 | 21 | new_bb_width [NEW, tercile] | 2060 | 38.5 | 1471 | 51.3 | -0.256 | 2.37e-12 |
| q8_in_all6 | 21 | new_gr250_moveratio [NEW, tercile] | 1474 | 39.2 | 1446 | 52.5 | -0.267 | 2.04e-11 |
| chartpass_all6 | 5 | new_dist_sma50 [NEW, tercile] | 15255 | 43.1 | 14651 | 47.2 | -0.0831 | 2.35e-11 |
| q8_in_all6 | 21 | new_maxdd40 [NEW, tercile] | 1507 | 50.8 | 2102 | 39 | 0.238 | 5.89e-11 |
| q8_in_all6 | 21 | new_gr60_moveratio [NEW, tercile] | 1705 | 40.1 | 1720 | 50.6 | -0.211 | 1.66e-08 |
| chartpass_all6 | 21 | new_bb_pctb [NEW, tercile] | 14741 | 42.1 | 13554 | 45.6 | -0.0715 | 3.79e-08 |
| chartpass_all6 | 21 | new_red_green_ratio20 [NEW, tercile] | 13963 | 42.7 | 18798 | 46.1 | -0.0669 | 4.3e-08 |
| chartpass_all6 | 5 | new_ret40 [NEW, tercile] | 15210 | 43.8 | 14674 | 47.2 | -0.0683 | 6.93e-08 |
| chartpass_all6 | 5 | new_macd_hist_pct [NEW, tercile] | 14892 | 47.3 | 14657 | 44 | 0.0671 | 1.45e-07 |
| chartpass_all6 | 21 | new_r60_mean [NEW, tercile] | 14458 | 43.2 | 14939 | 46.5 | -0.0667 | 1.94e-07 |
| chartpass_all6 | 5 | new_trend42_ret [NEW, tercile] | 15201 | 43.9 | 14657 | 47.1 | -0.0644 | 4.29e-07 |
| q5_in_all6 | 21 | new_gr250_moveratio [NEW, tercile] | 4088 | 46.2 | 4272 | 52.2 | -0.119 | 7.46e-07 |
| q5_in_all6 | 21 | new_rsi14 [NEW, tercile] | 3681 | 44.5 | 6053 | 50.1 | -0.111 | 1.66e-06 |
| q7_in_all6 | 21 | new_gmove60_max [NEW, tercile] | 1169 | 41.4 | 3040 | 50.3 | -0.179 | 2.76e-06 |

Files: `item_ranking.csv.gz` (every item × setup × h), `pair_item_aggregate.csv.gz`, `pair_diffs.csv.gz` (one row per pair; `top_items_differing` lists that setup's top-40 aggregate items where W and L differ: YES/NO, or T1–T3 terciles for NEW rows).
Coverage: sheet items = every row answered by the universe engine for 2020–24 (JG 1,478 ticker rows incl. BUT variants, NB 614, TR 2,808 row|N keys, SHARED 8,176 market rows) + 9 chart-picture story questions; the 6 chart-pass checks are the setup itself. NR answers are skipped, never guessed. SHARED rows rarely differ within a pair because pairs share the date.


## Coverage ledger (every row of six_bucket_map_v5_1 ∪ master.csv ∪ path bank v2 ∪ chart-picture v2) — `coverage_ledger.csv.gz`

| list | NOT_READY | SETUP | TESTED |
|---|---|---|---|
| chart_picture_v2 | 0 | 6 | 9 |
| master.csv | 714 | 0 | 0 |
| path_bank_v2 | 33 | 0 | 5,683 |
| six_bucket_map_v5_1 | 1,600 | 0 | 11,569 |

NOT_READY reasons:

- six_bucket_map_v5_1: engine row present but NR on every 2020-24 setup cell (source has no 2020-24 history) — 1,475
- master.csv: price/volume computable, but master free-text definition not yet ported to a deterministic formula; covered in spirit by path bank v2 / sheet rows of the same family (not counted as tested) — 397
- six_bucket_map_v5_1: no 2020-24 answer: SI chunks — 48
- six_bucket_map_v5_1: no 2020-24 answer: no (no reader port) — 36
- master.csv: needs Calendar data not on box point-in-time for 2020-24 — 34
- path_bank_v2: multi-class label (not YES/NO); its yes/no cuts are tested — 33
- master.csv: needs Market-wide data not on box point-in-time for 2020-24 — 19
- master.csv: needs Options data not on box point-in-time for 2020-24 — 19
- six_bucket_map_v5_1: no 2020-24 answer: NBX chunks — 18
- master.csv: needs Macro surprise data not on box point-in-time for 2020-24 — 17
- master.csv: needs Analyst data not on box point-in-time for 2020-24 — 12
- master.csv: needs Insider data not on box point-in-time for 2020-24 — 12
- master.csv: needs Cross-asset data not on box point-in-time for 2020-24 — 12
- master.csv: needs Credit data not on box point-in-time for 2020-24 — 11
- master.csv: needs Short volume data not on box point-in-time for 2020-24 — 11
- master.csv: needs Share supply data not on box point-in-time for 2020-24 — 10
- master.csv: needs Earnings data not on box point-in-time for 2020-24 — 10
- six_bucket_map_v5_1: no 2020-24 answer: ATTN chunks — 10
- master.csv: needs Pre-market data not on box point-in-time for 2020-24 — 9
- master.csv: needs Yield curve data not on box point-in-time for 2020-24 — 8
- master.csv: needs Rates data not on box point-in-time for 2020-24 — 8
- master.csv: needs Short interest data not on box point-in-time for 2020-24 — 8
- master.csv: not known before 09:25 ET on D (Pre-open: only via 09:25 premarket print; true O is NOT known) — 8
- six_bucket_map_v5_1: listed in engine but no reader output in universe chunks — 7
- master.csv: needs Corporate action data not on box point-in-time for 2020-24 — 7
- master.csv: needs Valuation data not on box point-in-time for 2020-24 — 6
- master.csv: needs Theme data not on box point-in-time for 2020-24 — 6
- six_bucket_map_v5_1: no 2020-24 answer: pending (DoltHub IV build) — 6
- master.csv: needs Market sentiment data not on box point-in-time for 2020-24 — 5
- master.csv: needs Corporate event data not on box point-in-time for 2020-24 — 5
- master.csv: needs Growth data not on box point-in-time for 2020-24 — 5
- master.csv: needs Securities lending data not on box point-in-time for 2020-24 — 5
- master.csv: needs 13F data not on box point-in-time for 2020-24 — 4
- master.csv: needs Rotation data not on box point-in-time for 2020-24 — 4
- master.csv: needs Biotech catalyst data not on box point-in-time for 2020-24 — 3
- master.csv: needs After-hours data not on box point-in-time for 2020-24 — 3
- master.csv: needs Fed data not on box point-in-time for 2020-24 — 3
- master.csv: needs Volatility data not on box point-in-time for 2020-24 — 3
- master.csv: needs Performance data not on box point-in-time for 2020-24 — 3
- master.csv: needs Index membership data not on box point-in-time for 2020-24 — 3
- master.csv: needs Profitability data not on box point-in-time for 2020-24 — 3
- master.csv: needs Ownership data not on box point-in-time for 2020-24 — 3
- master.csv: needs 52w range data not on box point-in-time for 2020-24 — 2
- master.csv: not known before 09:25 ET on D (Lagged only: use rows published before D (~2wk lag)) — 2
- master.csv: not known before 09:25 ET on D (Lagged only) — 2
- master.csv: needs Financial conditions data not on box point-in-time for 2020-24 — 2
- master.csv: needs ETF flows data not on box point-in-time for 2020-24 — 2
- master.csv: needs Balance sheet data not on box point-in-time for 2020-24 — 2
- master.csv: needs Correlation data not on box point-in-time for 2020-24 — 2
- master.csv: needs Liquidity data not on box point-in-time for 2020-24 — 2
- master.csv: needs Oscillator data not on box point-in-time for 2020-24 — 2
- master.csv: needs Sector gap data not on box point-in-time for 2020-24 — 2
- master.csv: needs Price bucket data not on box point-in-time for 2020-24 — 2
- master.csv: needs ADR / dual listing data not on box point-in-time for 2020-24 — 1
- master.csv: needs Float data not on box point-in-time for 2020-24 — 1
- master.csv: needs Industry data not on box point-in-time for 2020-24 — 1
- master.csv: needs Inflation expectations data not on box point-in-time for 2020-24 — 1
- master.csv: needs Commodity proxy data not on box point-in-time for 2020-24 — 1
- master.csv: needs Change from open data not on box point-in-time for 2020-24 — 1
- master.csv: needs Crypto proxy data not on box point-in-time for 2020-24 — 1
- master.csv: needs ETF ownership data not on box point-in-time for 2020-24 — 1
- master.csv: needs Pattern data not on box point-in-time for 2020-24 — 1
- master.csv: needs Size bucket data not on box point-in-time for 2020-24 — 1
- master.csv: needs Trend strength data not on box point-in-time for 2020-24 — 1
- master.csv: needs Sector flows data not on box point-in-time for 2020-24 — 1
- master.csv: needs Revenue data not on box point-in-time for 2020-24 — 1
- master.csv: needs Sector correlation data not on box point-in-time for 2020-24 — 1
- master.csv: needs Sector data not on box point-in-time for 2020-24 — 1
- master.csv: not known before 09:25 ET on D (Partial) — 1

## Plain-language findings (HINT only — practice 2020–24; re-test on sealed 2025–26 after the Fri 23:00 HKT lock)

Filter: Taskforce drop_list_v2 applied to cases and controls first. **ETF rule partial; market cap ≥ $100M not yet applied** — rerun when the SEC share counts land.

1. **The filter matters.** ~70% of setup days were untradeable (chart pass 103,747 of 147,986 dropped; controls pool 5.79M of 8.24M). After filtering, win rates vs matched controls are 43–48% for all 4 rules — none passes the >55% bar on its own. Raw/excess returns rise (Q7 +4.4% excess at 10d, Q5 +2.4%) because the drop list removes illiquid losers but keeps small caps; expect this to shrink once the mcap rule lands (the earlier provisional run with an mcap proxy showed Q7 turning negative).
2. **Volatility marks the losers.** In every setup, losers more often had: wider Bollinger Bands (top-tercile BB width: chart pass wins 38.9% vs 49.6% bottom tercile at 21d; in Q5 pairs the winner had the narrower bands in 62% of differing pairs), a bigger single green-chain move and red-chain move in the last 60 bars (38–42% vs 49–53%), and Theme Radar's high-volatility / far-below-52w-high rows (TEC-TR-01045/01057, PRC-TR-00662).
3. **Deeper 2-month drawdown → winners**, not losers (maxdd40 shallow tercile vs deep: 39% vs 49% chart pass; in Q8 pairs the winner had the deeper drawdown 61% of the time). The 42-bar trend itself is weak (43.9% vs 47.1%).
4. **Cyrus's other ideas:** red:green ratio (20 bars) weak (42.7% vs 46.1%); bigger last green body vs last red → slightly worse (44.1% vs 46.9%, q 5e-5); RSI high tercile → losers (41.6% vs 47.0%); RVOL high tercile → winners (46.4% vs 41.2%); price above SMA5/10/20 → winners in pairs (Q5: 60% winner-favour on dist-SMA5; Q7: 59% on dist-SMA20); MACD histogram weak (57% in Q7 pairs). Chain *lengths* barely separate; chain *moves* do.
5. **Story questions inside chart pass** differ in the winner's favour in 67–82% of differing pairs (Q1 lower highs 82%, Q8 79%, Q3 78%, Q7 78%), but they need a recent swing so they overlap with point 2.
6. **Honesty split (discover 2020–22 → confirm 2023–24):** 11,159 item×setup differences discovered; 6,479 still hold in 2023–24 (same direction, >5pp, q<0.1). Survivors are dominated by path-bank volatility/extension questions: losers more often had a ≥30% one-day jump in the last 30–60 bars (chart pass: winner-favour 43.6% → 34.6%), a ≥5% 15-day run-up, high NATR, repeated ≥2% gap-ups (Q7: 22–25% winner-favour in 2023–24), big one-day drops; winners more often sat within 7.5–10% of the recent high (Q5 ~66% both periods, Q7 61%→66%) and near the 10–15-day low in Q8 (61–65%→71%). Story Qs Q1/Q3/Q7/Q8 hold at 78–84% inside chart pass. Many survivors are correlated cuts of one feature (and TR `|N` duplicates) — count families, not rows.
7. **Caveats:** market-wide (SHARED) rows hit few dates so their q-values are too optimistic; TR `|N` variants are duplicates; tercile cut-offs are in-sample. Shortlist only.

## Visuals

- `summary_top_items.png`: top items per setup by pair sign test.
- One PNG per winner–loser pair (32,781; candles, SMA 5/10/20/50/100/200, BB(20,2), chain shading, RSI14, MACD, cutoff line, caption with top differing items). Full set on Google Drive `checklist_engine_chunks` (link in `pairs/README.md`); a sample of 25 per setup plus the full `index.md` per setup are in `pairs/`.
- Reproduce: `build.py` → `new2.py` → `pb2.py` → `TASKFORCE_DROP=buyable_filter_v1/drop_list_v2.csv.gz analyze.py` → `charts.py` → `summary_chart.py` → `coverage.py`. Deterministic; charts skip existing PNGs so an interrupted run resumes.
