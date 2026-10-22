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

## Pairs (h=10d primary): symmetric 1:1 winner–loser pairs, same setup and same date, fixed ticker-hash order, no reuse (audit fix; old winner-anchored pairing retracted)

| setup | tradable events | winners | pairs | median items differing | casebook pairs |
|---|---|---|---|---|---|
| chartpass_all6 | 43,517 | 19,810 | 17,128 | 1573 | 27 |
| q5_in_all6 | 14,889 | 7,350 | 4,772 | 1501 | 11 |
| q7_in_all6 | 6,531 | 3,178 | 1,807 | 1452 | 6 |
| q8_in_all6 | 5,194 | 2,403 | 1,421 | 1598 | 9 |

## Honesty split (pair sign test): discover on 2020–22 pairs, confirm on 2023–24 pairs

Tested in discovery (n_differ ≥ 30): 27,682. Discovered (q<0.1 BH, |favour−50| > 5pp): 3,577. **Still hold on 2023–24** (same direction, >5pp, n ≥ 30, q<0.1 BH over discovered set): **1,469**.

| setup | item | source | disc n | disc winner-favour % | conf n | conf winner-favour % | q conf |
|---|---|---|---|---|---|---|---|
| chartpass_all6 | ph2_maxup1d_30_ge0p3 | path bank v2 question | 1527 | 43.5 | 1165 | 37.1 | 1.6e-15 |
| chartpass_all6 | ph2_maxup1d_25_ge0p3 | path bank v2 question | 1505 | 43.4 | 1160 | 37.2 | 1.6e-15 |
| chartpass_all6 | ph2_maxup1d_15_ge0p3 | path bank v2 question | 1258 | 43.6 | 1013 | 36.3 | 1.6e-15 |
| chartpass_all6 | ph2_gapdn5_50_ge5 | path bank v2 question | 962 | 39.3 | 546 | 31.7 | 3.2e-15 |
| chartpass_all6 | ph2_maxup1d_20_ge0p3 | path bank v2 question | 1443 | 43.3 | 1139 | 37.4 | 4.9e-15 |
| chartpass_all6 | ph2_maxup1d_50_ge0p3 | path bank v2 question | 1699 | 44.3 | 1278 | 38.1 | 4.9e-15 |
| chartpass_all6 | ph2_maxup1d_60_ge0p3 | path bank v2 question | 1821 | 45.0 | 1363 | 38.5 | 5.4e-15 |
| chartpass_all6 | ph2_voltrend_50_ge3p0 | path bank v2 question | 1454 | 42.5 | 1202 | 37.9 | 7.4e-15 |
| chartpass_all6 | ph2_maxup1d_40_ge0p3 | path bank v2 question | 1599 | 44.0 | 1213 | 38.3 | 5.1e-14 |
| chartpass_all6 | ph2_gapdn5_60_ge5 | path bank v2 question | 1188 | 40.5 | 677 | 34.7 | 2.6e-13 |
| chartpass_all6 | ph2_voltrend_60_ge3p0 | path bank v2 question | 1420 | 41.8 | 1123 | 38.4 | 1.1e-12 |
| chartpass_all6 | ph2_maxdn1d_20_ge0p05 | path bank v2 question | 4144 | 44.5 | 3798 | 43.9 | 6.3e-12 |
| q5_in_all6 | ph2_volrel_10_ge3p0 | path bank v2 question | 270 | 42.6 | 222 | 31.5 | 3.4e-07 |
| q5_in_all6 | ph2_gapdn5_25_ge2 | path bank v2 question | 476 | 44.5 | 287 | 34.1 | 6.9e-07 |
| q5_in_all6 | ph2_gapup5_10_ge2 | path bank v2 question | 221 | 40.3 | 157 | 29.9 | 3.4e-06 |
| q5_in_all6 | ph2_maxup1d_30_ge0p3 | path bank v2 question | 324 | 42.0 | 247 | 34.4 | 6.1e-06 |
| q5_in_all6 | ph2_maxup1d_25_ge0p3 | path bank v2 question | 324 | 42.3 | 247 | 34.4 | 6.1e-06 |
| q5_in_all6 | ph2_maxdn1d_30_ge0p05 | path bank v2 question | 1132 | 42.8 | 988 | 42.3 | 7.9e-06 |
| q5_in_all6 | ph2_maxdn1d_40_ge0p05 | path bank v2 question | 1038 | 43.4 | 953 | 42.2 | 8e-06 |
| q5_in_all6 | ph2_maxdn1d_50_ge0p05 | path bank v2 question | 971 | 44.4 | 911 | 42.0 | 8.5e-06 |
| q5_in_all6 | ph2_gapdn5_25_ge3 | path bank v2 question | 267 | 37.1 | 123 | 28.5 | 9.2e-06 |
| q5_in_all6 | ph2_gapup5_15_ge2 | path bank v2 question | 347 | 41.5 | 211 | 33.6 | 1.1e-05 |
| q5_in_all6 | ph2_maxdn1d_60_ge0p15 | path bank v2 question | 689 | 44.7 | 462 | 39.0 | 1.1e-05 |
| q5_in_all6 | ph2_maxup1d_20_ge0p3 | path bank v2 question | 311 | 43.1 | 245 | 35.1 | 1.5e-05 |
| q7_in_all6 | ph2_disth_60_le0p15 | path bank v2 question | 465 | 56.8 | 353 | 61.8 | 3.9e-05 |
| q7_in_all6 | ph2_natr_40_ge0p03 | path bank v2 question | 422 | 42.4 | 402 | 39.3 | 6.6e-05 |
| q7_in_all6 | ph2_natr_60_ge0p03 | path bank v2 question | 431 | 42.7 | 396 | 39.4 | 8.7e-05 |
| q7_in_all6 | ph2_natr_50_ge0p03 | path bank v2 question | 424 | 43.6 | 392 | 39.5 | 0.00012 |
| q7_in_all6 | ph2_gapup2_50_ge10 | path bank v2 question | 124 | 38.7 | 78 | 26.9 | 0.00016 |
| q7_in_all6 | ph2_gapup2_20_ge4 | path bank v2 question | 174 | 40.2 | 94 | 29.8 | 0.00029 |
| q7_in_all6 | ph2_natr_30_ge0p03 | path bank v2 question | 408 | 43.6 | 399 | 40.4 | 0.00035 |
| q7_in_all6 | ph2_maxdn1d_50_ge0p075 | path bank v2 question | 460 | 43.7 | 343 | 39.7 | 0.00038 |
| q7_in_all6 | ph2_gapup2_25_ge5 | path bank v2 question | 189 | 38.1 | 88 | 29.5 | 0.00039 |
| q7_in_all6 | ph2_gapdn5_7_ge1 | path bank v2 question | 254 | 39.8 | 214 | 36.9 | 0.00039 |
| q7_in_all6 | TEC-TR-01045-C|10 | sheet:TR (Theme Radar) | 178 | 38.2 | 122 | 32.8 | 0.00044 |
| q7_in_all6 | ph2_natr_5_ge0p07 | path bank v2 question | 308 | 42.5 | 188 | 36.2 | 0.00045 |
| q8_in_all6 | ph2_distl_20_le0p3 | path bank v2 question | 173 | 61.8 | 149 | 69.1 | 1.5e-05 |
| q8_in_all6 | ph2_ret_15_ge0p1 | path bank v2 question | 174 | 38.5 | 146 | 30.8 | 1.7e-05 |
| q8_in_all6 | ph2_retq_15_gt10 | path bank v2 question | 174 | 38.5 | 146 | 30.8 | 1.7e-05 |
| q8_in_all6 | ph2_distl_10_le0p15 | path bank v2 question | 226 | 58.4 | 187 | 66.8 | 1.9e-05 |
| q8_in_all6 | ph2_distl_15_le0p15 | path bank v2 question | 269 | 58.7 | 215 | 65.6 | 2.2e-05 |
| q8_in_all6 | ph2_distl_15_le0p3 | path bank v2 question | 132 | 61.4 | 112 | 71.4 | 2.4e-05 |
| q8_in_all6 | ph2_ret_15_ge0p15 | path bank v2 question | 155 | 40.0 | 118 | 29.7 | 3.9e-05 |
| q8_in_all6 | TEC-TR-01045-C|10 | sheet:TR (Theme Radar) | 291 | 40.9 | 212 | 34.9 | 4.4e-05 |
| q8_in_all6 | ph2_maxdd_30_ge0p3 | path bank v2 question | 189 | 39.2 | 147 | 32.0 | 4.8e-05 |
| q8_in_all6 | ph2_distl_25_le0p3 | path bank v2 question | 201 | 58.7 | 166 | 66.9 | 5.3e-05 |
| q8_in_all6 | ph2_ret_15_ge0p2 | path bank v2 question | 127 | 37.8 | 104 | 28.8 | 6e-05 |
| q8_in_all6 | ph2_slope_20_gt0p01 | path bank v2 question | 141 | 39.7 | 124 | 30.6 | 6.2e-05 |

## (b) Items that most often differ in the winner's favour (pair sign test, BH across all items × setups)

HINT candidates (winner-favour > 55%, n_differ ≥ 30, q < 0.1): **1048** of 29,436 tested.

### chartpass_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_gapdn5_50_ge5 | path bank v2 question | 1508 | 551 | 957 | 36.5 | 2.74e-21 | False |
| ph2_maxdn1d_20_ge0p05 | path bank v2 question | 7942 | 3510 | 4432 | 44.2 | 6.41e-21 | False |
| ph2_natr_40_ge0p07 | path bank v2 question | 6305 | 2748 | 3557 | 43.6 | 2.16e-20 | False |
| ph2_gapdn2_60_ge10 | path bank v2 question | 4677 | 1995 | 2682 | 42.7 | 5.49e-20 | False |
| ph2_gapdn5_60_ge5 | path bank v2 question | 1865 | 716 | 1149 | 38.4 | 5.49e-20 | False |
| ph2_maxdn1d_15_ge0p05 | path bank v2 question | 7957 | 3536 | 4421 | 44.4 | 1.63e-19 | False |
| ph2_voltrend_50_ge3p0 | path bank v2 question | 2656 | 1073 | 1583 | 40.4 | 1.63e-19 | False |
| ph2_voltrend_60_ge3p0 | path bank v2 question | 2543 | 1024 | 1519 | 40.3 | 3.07e-19 | False |
| new_rmove60_max [NEW, tercile] | NEW (not on sheet) | 11021 | 4995 | 6026 | 45.3 | 3.07e-19 | False |
| ph2_gapdn2_60_ge7 | path bank v2 question | 6351 | 2785 | 3566 | 43.9 | 3.32e-19 | False |
| ph2_upvolfrac_30_ge0p7 | path bank v2 question | 2301 | 917 | 1384 | 39.9 | 5.03e-19 | False |
| ph2_maxup1d_30_ge0p3 | path bank v2 question | 2692 | 1096 | 1596 | 40.7 | 1.19e-18 | False |
| ph2_gapdn2_50_ge10 | path bank v2 question | 3659 | 1538 | 2121 | 42 | 1.19e-18 | False |
| ph2_maxup1d_25_ge0p3 | path bank v2 question | 2665 | 1084 | 1581 | 40.7 | 1.19e-18 | False |
| ph2_distl_20_le0p2 | path bank v2 question | 4182 | 2402 | 1780 | 57.4 | 1.29e-18 | True |

### q5_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_gapdn5_50_ge5 | path bank v2 question | 334 | 100 | 234 | 29.9 | 1.24e-11 | False |
| ph2_maxdn1d_20_ge0p05 | path bank v2 question | 2203 | 934 | 1269 | 42.4 | 6.6e-11 | False |
| ph2_gapdn5_60_ge5 | path bank v2 question | 431 | 142 | 289 | 32.9 | 8.01e-11 | False |
| ph2_gapdn1_20_ge7 | path bank v2 question | 1220 | 487 | 733 | 39.9 | 1.2e-10 | False |
| ph2_maxdn1d_30_ge0p05 | path bank v2 question | 2120 | 903 | 1217 | 42.6 | 5.32e-10 | False |
| ph2_maxdn1d_15_ge0p05 | path bank v2 question | 2217 | 949 | 1268 | 42.8 | 7.18e-10 | False |
| ph2_gapdn2_60_ge10 | path bank v2 question | 1200 | 483 | 717 | 40.2 | 8.08e-10 | False |
| ph2_gapdn5_60_ge3 | path bank v2 question | 840 | 326 | 514 | 38.8 | 4.17e-09 | False |
| ph2_maxdn1d_40_ge0p05 | path bank v2 question | 1991 | 852 | 1139 | 42.8 | 5.91e-09 | False |
| ph2_gapdn2_50_ge7 | path bank v2 question | 1479 | 616 | 863 | 41.6 | 6.25e-09 | False |
| ph2_maxdn1d_5_ge0p05 | path bank v2 question | 2266 | 981 | 1285 | 43.3 | 7.8e-09 | False |
| ph2_gapdn1_15_ge5 | path bank v2 question | 1555 | 652 | 903 | 41.9 | 8.83e-09 | False |
| ph2_gapdn5_30_ge3 | path bank v2 question | 455 | 160 | 295 | 35.2 | 1.03e-08 | False |
| ph2_maxdn1d_10_ge0p05 | path bank v2 question | 2229 | 965 | 1264 | 43.3 | 1.07e-08 | False |
| ph2_maxdn1d_25_ge0p05 | path bank v2 question | 2175 | 941 | 1234 | 43.3 | 1.46e-08 | False |

### q7_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_maxup1d_5_ge0p05 | path bank v2 question | 472 | 176 | 296 | 37.3 | 9.99e-07 | False |
| ph2_maxdn1d_15_ge0p05 | path bank v2 question | 850 | 345 | 505 | 40.6 | 1.21e-06 | False |
| ph2_maxdn1d_20_ge0p05 | path bank v2 question | 861 | 353 | 508 | 41 | 3.35e-06 | False |
| ph2_distl_5_le0p1 | path bank v2 question | 308 | 200 | 108 | 64.9 | 4.04e-06 | True |
| ph2_natr_40_ge0p03 | path bank v2 question | 824 | 337 | 487 | 40.9 | 4.42e-06 | False |
| ph2_accel_25_gtm0p02 | path bank v2 question | 512 | 314 | 198 | 61.3 | 7.16e-06 | True |
| ph2_natr_60_ge0p03 | path bank v2 question | 827 | 340 | 487 | 41.1 | 7.63e-06 | False |
| ph2_disth_60_le0p15 | path bank v2 question | 818 | 482 | 336 | 58.9 | 7.89e-06 | True |
| ph2_maxdd_15_ge0p15 | path bank v2 question | 607 | 241 | 366 | 39.7 | 9.24e-06 | False |
| ph2_gapup2_30_ge5 | path bank v2 question | 343 | 125 | 218 | 36.4 | 1.19e-05 | False |
| ph2_distl_25_le0p1 | path bank v2 question | 661 | 395 | 266 | 59.8 | 1.21e-05 | True |
| ph2_gapdn5_7_ge1 | path bank v2 question | 468 | 180 | 288 | 38.5 | 1.37e-05 | False |
| ph2_natr_60_ge0p07 | path bank v2 question | 419 | 159 | 260 | 37.9 | 1.8e-05 | False |
| ph2_maxdd_40_ge0p2 | path bank v2 question | 565 | 224 | 341 | 39.6 | 1.88e-05 | False |
| ph2_maxdd_20_ge0p15 | path bank v2 question | 649 | 262 | 387 | 40.4 | 2.01e-05 | False |

### q8_in_all6

| item | source | n differ | W yes/L no | W no/L yes | winner favour % | q (BH) | HINT |
|---|---|---|---|---|---|---|---|
| ph2_accel_50_gt0p02 | path bank v2 question | 255 | 83 | 172 | 32.5 | 7.26e-07 | False |
| ph2_distl_20_le0p3 | path bank v2 question | 322 | 210 | 112 | 65.2 | 1.36e-06 | True |
| ph2_ret_15_ge0p1 | path bank v2 question | 320 | 112 | 208 | 35 | 2.16e-06 | False |
| ph2_retq_15_gt10 | path bank v2 question | 320 | 112 | 208 | 35 | 2.16e-06 | False |
| TEC-TR-01045-C|10 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.61e-06 | False |
| TEC-TR-01045-C|20 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.61e-06 | False |
| TEC-TR-01045-C|3 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.61e-06 | False |
| TEC-TR-01045-C|5 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.61e-06 | False |
| TEC-TR-01045-C|60 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.61e-06 | False |
| TEC-TR-01045-C|1 | sheet:TR (Theme Radar) | 503 | 193 | 310 | 38.4 | 4.61e-06 | False |
| ph2_distl_15_le0p15 | path bank v2 question | 484 | 299 | 185 | 61.8 | 5.5e-06 | True |
| ph2_maxdd_30_ge0p3 | path bank v2 question | 336 | 121 | 215 | 36 | 7.12e-06 | False |
| TEC-TR-00121-C|20 | sheet:TR (Theme Radar) | 275 | 95 | 180 | 34.5 | 7.12e-06 | False |
| TEC-TR-00121-C|60 | sheet:TR (Theme Radar) | 275 | 95 | 180 | 34.5 | 7.12e-06 | False |
| TEC-TR-00121-C|1 | sheet:TR (Theme Radar) | 275 | 95 | 180 | 34.5 | 7.12e-06 | False |

## (a2) Item win-rate ranking across all tradable setup days (YES vs NO; NEW rows: top vs bottom tercile), BH across all items × setups × horizons

HINT candidates (>55% win in the better bucket, n ≥ 30, q < 0.1): **8942** of 165,893 tests.

| setup | h | item | source | n YES/top | win% YES/top | n NO/bottom | win% NO/bottom | base win% | effect h | q | HINT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 21 | ph2_maxup1d_40_ge0p1 | path bank v2 question | 16206 | 38.2 | 26818 | 48.4 | 44.6 | -0.207 | 8.21e-90 | False |
| chartpass_all6 | 21 | ph2_maxup1d_30_ge0p1 | path bank v2 question | 15332 | 38 | 27692 | 48.2 | 44.6 | -0.207 | 4.88e-88 | False |
| chartpass_all6 | 21 | ph2_maxup1d_25_ge0p1 | path bank v2 question | 14977 | 37.9 | 28047 | 48.1 | 44.6 | -0.208 | 1.05e-87 | False |
| chartpass_all6 | 21 | ph2_maxup1d_20_ge0p1 | path bank v2 question | 14471 | 37.7 | 28553 | 48 | 44.6 | -0.209 | 3.05e-87 | False |
| chartpass_all6 | 21 | ph2_maxup1d_50_ge0p1 | path bank v2 question | 17418 | 38.7 | 25606 | 48.5 | 44.6 | -0.199 | 4.79e-86 | False |
| chartpass_all6 | 21 | ph2_natr_25_ge0p07 | path bank v2 question | 12345 | 37 | 30679 | 47.6 | 44.6 | -0.216 | 1.02e-85 | False |
| chartpass_all6 | 21 | ph2_natr_20_ge0p07 | path bank v2 question | 12517 | 37 | 30507 | 47.6 | 44.6 | -0.215 | 1.02e-85 | False |
| chartpass_all6 | 21 | ph2_natr_30_ge0p07 | path bank v2 question | 12189 | 36.9 | 30835 | 47.6 | 44.6 | -0.216 | 1.63e-84 | False |
| chartpass_all6 | 21 | ph2_maxup1d_15_ge0p075 | path bank v2 question | 16341 | 38.6 | 26683 | 48.2 | 44.6 | -0.195 | 1.06e-80 | False |
| chartpass_all6 | 21 | ph2_natr_40_ge0p07 | path bank v2 question | 12058 | 37.1 | 30966 | 47.5 | 44.6 | -0.21 | 9.82e-80 | False |
| chartpass_all6 | 21 | ph2_distl_25_le0p15 | path bank v2 question | 30794 | 47.5 | 12230 | 37.2 | 44.6 | 0.208 | 3.44e-79 | False |
| chartpass_all6 | 21 | ph2_disth_15_le0p15 | path bank v2 question | 27080 | 48.1 | 15944 | 38.5 | 44.6 | 0.193 | 9.03e-79 | False |
| chartpass_all6 | 21 | ph2_maxup1d_15_ge0p1 | path bank v2 question | 11862 | 37.1 | 31162 | 47.4 | 44.6 | -0.21 | 1.33e-78 | False |
| chartpass_all6 | 21 | ph2_maxup1d_50_ge0p15 | path bank v2 question | 10825 | 36.6 | 32199 | 47.2 | 44.6 | -0.215 | 5.32e-78 | False |
| chartpass_all6 | 21 | ph2_natr_60_ge0p07 | path bank v2 question | 12004 | 37.2 | 31020 | 47.4 | 44.6 | -0.208 | 8.64e-78 | False |
| chartpass_all6 | 21 | ph2_disth_20_le0p15 | path bank v2 question | 26526 | 48.2 | 16498 | 38.7 | 44.6 | 0.191 | 8.64e-78 | False |
| chartpass_all6 | 21 | ph2_disth_25_le0p15 | path bank v2 question | 26455 | 48.2 | 16569 | 38.8 | 44.6 | 0.191 | 8.64e-78 | False |
| chartpass_all6 | 21 | ph2_natr_7_ge0p05 | path bank v2 question | 18995 | 39.4 | 24029 | 48.6 | 44.6 | -0.186 | 1.04e-77 | False |
| chartpass_all6 | 21 | ph2_maxup1d_20_ge0p075 | path bank v2 question | 19472 | 39.5 | 23552 | 48.7 | 44.6 | -0.186 | 1.32e-77 | False |
| chartpass_all6 | 21 | ph2_distl_40_le0p2 | path bank v2 question | 32166 | 47.2 | 10858 | 36.7 | 44.6 | 0.214 | 2.22e-77 | False |
| chartpass_all6 | 21 | PV-TF-279 | master.csv price/volume row (ported formula) | 19514 | 39.4 | 22854 | 48.7 | 44.6 | -0.186 | 2.51e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|5 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.51e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|10 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.51e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|1 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.51e-77 | False |
| chartpass_all6 | 21 | PRC-TR-01969-C|20 | sheet:TR (Theme Radar) | 6704 | 33.9 | 36320 | 46.5 | 44.6 | -0.258 | 2.51e-77 | False |

### Cyrus's NEW rows (chains, 40-bar trend/drawdown, 2-month trend, red:green ratio, last green vs red body, RSI, MACD, RVOL, BB, SMA distance) — best horizon per setup

| setup | h | item | n top | win% top | n bottom | win% bottom | effect h | q |
|---|---|---|---|---|---|---|---|---|
| chartpass_all6 | 21 | new_gmove60_max [NEW, tercile] | 15319 | 38.4 | 13374 | 49.5 | -0.226 | 3.11e-77 |
| chartpass_all6 | 21 | new_rmove60_max [NEW, tercile] | 15032 | 38.9 | 13641 | 49.9 | -0.223 | 1.1e-75 |
| chartpass_all6 | 21 | new_bb_width [NEW, tercile] | 15254 | 38.9 | 13583 | 49.6 | -0.216 | 1.7e-71 |
| chartpass_all6 | 21 | new_maxdd40 [NEW, tercile] | 13673 | 49 | 15090 | 39.3 | 0.196 | 6.16e-59 |
| chartpass_all6 | 21 | new_gr250_moveratio [NEW, tercile] | 12545 | 40.2 | 11840 | 49.6 | -0.189 | 1.16e-46 |
| chartpass_all6 | 21 | new_gr60_moveratio [NEW, tercile] | 15149 | 40.8 | 13598 | 47.6 | -0.137 | 1.15e-28 |
| q5_in_all6 | 21 | new_rmove60_max [NEW, tercile] | 4470 | 41.5 | 5070 | 53.2 | -0.234 | 8.49e-28 |
| q5_in_all6 | 21 | new_gmove60_max [NEW, tercile] | 4591 | 42.6 | 5011 | 53.2 | -0.213 | 3.1e-23 |
| chartpass_all6 | 21 | new_slope40 [NEW, tercile] | 15048 | 40.7 | 14102 | 46.7 | -0.121 | 5.31e-23 |
| q5_in_all6 | 21 | new_maxdd40 [NEW, tercile] | 5116 | 52.8 | 4446 | 42.3 | 0.211 | 1.3e-22 |
| q5_in_all6 | 21 | new_bb_width [NEW, tercile] | 4904 | 42.6 | 4634 | 53 | -0.209 | 2.18e-22 |
| chartpass_all6 | 21 | new_rsi14 [NEW, tercile] | 14607 | 41.6 | 14041 | 47 | -0.108 | 4.28e-18 |
| q8_in_all6 | 21 | new_gmove60_max [NEW, tercile] | 1991 | 37.5 | 1590 | 52.4 | -0.301 | 2.87e-17 |
| chartpass_all6 | 21 | new_rvol20 [NEW, tercile] | 13044 | 46.4 | 15629 | 41.2 | 0.105 | 6.35e-17 |
| q8_in_all6 | 21 | new_rmove60_max [NEW, tercile] | 2082 | 38.8 | 1506 | 53.1 | -0.288 | 1.06e-15 |
| chartpass_all6 | 21 | new_dist_sma10 [NEW, tercile] | 13624 | 46.1 | 15066 | 41.6 | 0.0896 | 1.44e-12 |
| q8_in_all6 | 21 | new_bb_width [NEW, tercile] | 2060 | 38.5 | 1471 | 51.3 | -0.256 | 2.37e-12 |
| q8_in_all6 | 21 | new_gr250_moveratio [NEW, tercile] | 1474 | 39.2 | 1446 | 52.5 | -0.267 | 2.04e-11 |
| chartpass_all6 | 5 | new_dist_sma50 [NEW, tercile] | 15255 | 43.1 | 14651 | 47.2 | -0.0831 | 2.35e-11 |
| q8_in_all6 | 21 | new_maxdd40 [NEW, tercile] | 1507 | 50.8 | 2102 | 39 | 0.238 | 5.9e-11 |
| q8_in_all6 | 21 | new_gr60_moveratio [NEW, tercile] | 1705 | 40.1 | 1720 | 50.6 | -0.211 | 1.67e-08 |
| chartpass_all6 | 21 | new_bb_pctb [NEW, tercile] | 14741 | 42.1 | 13554 | 45.6 | -0.0715 | 3.81e-08 |
| chartpass_all6 | 21 | new_red_green_ratio20 [NEW, tercile] | 13963 | 42.7 | 18798 | 46.1 | -0.0669 | 4.32e-08 |
| chartpass_all6 | 5 | new_ret40 [NEW, tercile] | 15210 | 43.8 | 14674 | 47.2 | -0.0683 | 6.95e-08 |
| chartpass_all6 | 5 | new_macd_hist_pct [NEW, tercile] | 14892 | 47.3 | 14657 | 44 | 0.0671 | 1.45e-07 |
| chartpass_all6 | 21 | new_r60_mean [NEW, tercile] | 14458 | 43.2 | 14939 | 46.5 | -0.0667 | 1.94e-07 |
| chartpass_all6 | 5 | new_trend42_ret [NEW, tercile] | 15201 | 43.9 | 14657 | 47.1 | -0.0644 | 4.3e-07 |
| q5_in_all6 | 21 | new_gr250_moveratio [NEW, tercile] | 4088 | 46.2 | 4272 | 52.2 | -0.119 | 7.48e-07 |
| q5_in_all6 | 21 | new_rsi14 [NEW, tercile] | 3681 | 44.5 | 6053 | 50.1 | -0.111 | 1.66e-06 |
| q7_in_all6 | 21 | new_gmove60_max [NEW, tercile] | 1169 | 41.4 | 3040 | 50.3 | -0.179 | 2.77e-06 |

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

## AUDIT 2026-10-22 (Manager Bot request) — leakage + direction check, and a RETRACTION

**RETRACTED:** the earlier claim that chart-picture story questions (Q1 lower highs, Q3 shrinking green, Q7 lower-band reclaim, Q8 above last red high) "differ in the winner's favour in ~78–84% of pairs" (and the 6,479 "holds on 2023–24" count built on that pairing) is withdrawn. It was a **pairing artifact**, not an edge.
- Cause: pairs were winner-anchored (each winner → nearest loser, losers reused) with a tie-break on story-question Hamming distance. A rare YES trait on the winner usually cannot be matched, a common NO usually can, so "winner YES / loser NO" dominates regardless of outcome.
- Proof: shuffling the win labels within setup × date (seed 20261022) reproduced it — Q1 83.9%, Q3 79.4%, Q7 78.6%, Q8 77.9% under the null, and 2,183 false "HINT candidates".
- Fix: symmetric 1:1 pairs — same setup, same date, winners and losers each in a fixed ticker-hash order, zipped without reuse; no tested item is used for matching. Under shuffled labels the fixed design gives **0** HINT candidates and 1 item at q<0.1 out of 29,384 (null file `pair_item_aggregate_NULL.csv.gz`). With real labels the story questions now sit at 49.8–51.9% (Q1 50.4%, Q3 49.9%, Q7 50.5%, Q8 49.8%) — **no separation**.

**Leakage (bars ≥ D):** none found. Story answers (`/workspace/state_test/story_q/story_q.py`) are computed on bar t = D−1 using bars ≤ t (swing points confirmed 2 bars later, so no look-ahead); the cp_* gate and every story flag show no relation to day-D's own open→close move (yes vs no differ by ≤0.03pp on a 10% ticker sample). Win label = open D → open D+h, net of 30bp/side, versus same-day controls — no bar before D's open enters it. Pairing uses only setup and date.

**Direction:** no question's YES/bullish sense was flipped in code — the pair test and win-rate tests are direction-free (they report which side wins); `yes_means` is not used anywhere. Q8 is pre-registered as a **warning/fade**; the Q8 setup's re-score above simply reports its win rate (45.9% at 10d after the filter, i.e. it does still lag). The earlier wording "Q8 flips to slightly positive" referred only to the mean excess return (+0.46%), not to a reversed definition.

## Plain-language findings (HINT only; re-test on sealed 2025–26 after Fri 23:00 HKT)

Filter: Taskforce drop_list_v2 on cases and controls first; **ETF rule partial, market cap not applied**.

1. **The 4 rules alone:** after the filter win rates are 43–48% vs matched controls; none passes the >55% bar.
2. **Honest split, fixed pairing:** 3,577 item × setup differences discovered on 2020–22; **1,469 still hold on 2023–24** (same direction, >5pp, n ≥ 30, BH q<0.1). Correlated cuts of one feature count as one family.
3. **Families that hold — all point the same way: big recent moves / high volatility mark the LOSER.**
   - Path bank: a ≥30% one-day jump in the last 15–60 bars (chart pass winner-favour 43–45% → 36–39% in 2023–24); ≥5 gap-downs >5% in 50 bars (39% → 32%); volume trend ≥3× (42% → 38%); big one-day drops; high NATR (Q7 42–44% → 39–40%); repeated ≥2% gap-ups (Q7 38–40% → 27–30%); in Q8, a ≥10–20% 15-day run-up (38% → 29–31%).
   - Winners: in Q8, close within 15–30% of the 10–25-day low (58–62% → 66–71%); in Q7, within 15% of the 60-day high (57% → 62%).
4. **New master.csv price/volume families that hold (391 rows ported):** 32 row × setup results hold, all in the "too hot = loser" family: ret20 in the top decile of the universe (chart pass 44.4% → 42.4%), ATR14/C ≥ 20% (38.7% → 35.1%) and ≥ 10%, up-day volume share ≥ 65% (43% → 40%), 20-day return ≥ 20% (43.8% → 40.8%), MFI > 80, 5/10-day return ≥ 5–10%, ret5/ret20 ≥ 5% ahead of SPY/IWM/sector (Q7 28–34%, Q8 40–43%). The few winner-side ones: close within 2% of the 52-week low (chart pass 69.6% → 58.8%), within 2% of the 26-week high (60.6% → 57.1%), within 5% of the 13-week low in Q7 (61% → 57%).
5. **Story questions:** no separation once pairing is fixed (see audit).
6. **Caveats:** sector/industry rows use today's Finviz sector map (not point-in-time); long-lookback rows are NA before 2021-01-05 because the price file starts 2020-01-02; market-wide rows hit few dates; TR `|N` variants duplicate each other.

## Visuals

- One PNG per fixed pair (25,128) in `pairs/<setup>/` (sample in repo; full set on Drive `checklist_engine_chunks`, see `pairs/README.md`). The earlier Drive tar parts (`lookalike_pairs_pngs_2020_24_HINT.tar.part00–15`) show the **retracted** pairing.
- Reproduce: `build.py` → `new2.py` → `pb2.py` → `master_pv.py` → `mpv_mask.py` → `TASKFORCE_DROP=… analyze.py` (`PERMUTE_NULL=1` for the null) → `charts.py` → `coverage.py`.
