# HINT_SCAN_2020_24 — BUYABLE_V1 (practice only, HINT, not evidence). 2025–26 sealed until Fri 2026-10-23 23:00 HKT.

Rule (Cyrus via James, 2026-10-22 21:49 HKT): drop every stock-day we'd never buy, meaning it fails fullscan's liquidity filter or minimum market cap as of day D. The drop happens before pairing and scoring, and the controls (ALL, not-A, NO groups and the same-day mean) are filtered too.

## Thresholds
From SRoyaltyy/fullscan `src/stock_book.py` `_keep_liquid()` (`MIN_AVG_VOL_K = 500.0`, `MIN_MARKET_CAP_M = 80.0`, `MIN_ATR_PCT = tl.MIN_ATR_PCT`), with `src/ticker_lookback.py` `MIN_ATR_PCT = 2.5`:
- **Average volume ≥ 500k shares**: the mean of the last 63 bars (about Finviz's 3-month average), using bars ≤ D−1 only, min 40 bars.
- **ATR% ≥ 2.5**: ATR14 (simple mean of true range over bars ≤ D−1) divided by close[D−1]. It is part of the same `_keep_liquid` filter.
- **Market cap ≥ $80M: NOT AVAILABLE point-in-time.** We have no history of shares outstanding or market cap. **STAND-IN** (labelled as such): close[D−1] ≥ $1 and 63-bar average dollar volume ≥ $5M/day. The $5M/day figure is fullscan's own Russell-2000 dollar-volume floor in `docs/HOW_IT_WORKS_SIMPLE.md`. This is not a market-cap test.
- Prices: universe_2020_survivors.parquet sha fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337, read with date ≤ 2024-12-31 (asserted). Survivors-only bias still applies.

## Drops
- Stock-days: 8,244,720 → 1,478,138 (**dropped 6,766,582, 82.1%**). Each test fails on its own: volume 5,729,733, ATR 3,835,442, cap stand-in 4,608,143.
- Tickers with any buyable day: 8,479 → 3,299.
- 6-check pass (A) cases: 147,986 → 29,883 (**dropped 118,103, 79.8%**).
- DCGO 2021-09-27: 63-bar average volume 32,959, ATR% 0.42, close[D−1] $9.96, so it is **dropped**.
- Story-question YES days dropped: sq1 1,569,193/1,935,477, sq2 1,801,406/2,169,724, sq3 951,674/1,182,204, sq4 3,386,973/4,182,044, sq5 1,695,032/2,060,642, sq6 3,373,302/4,122,131, sq7 2,427,221/2,990,188, sq8 2,399,078/2,910,794, sq9 610,708/769,748

## Method
Net = gross − 0.60%. Entry is open[D] and exit is open[D+h] (h = 5, 10, 21), same as the locked score. Excess = net minus the same-day mean of the scored set, so "after" uses the buyable-only mean. The 95% CI is a date-clustered bootstrap (1000 draws, seed 7), and p is two-sided from that bootstrap.
FDR is Benjamini–Hochberg at q = 0.05 over the whole question bank: the 9 questions' YES cells, alone and within A, × 3 horizons = 54 tests per set. **Q5, Q7 and Q8 are also graded as their own small group** (18 tests). The NO cells mirror the YES cells and are not counted separately.
FDR-significant cells: bank before 20, after 18; Q5/7/8 group before 7, after 6.

## 1. Gate: 6-check pass (A) vs controls
| set | group | h | n | dates | mean% | median% | win% | excess% | 95% CI | p | FDR bank | FDR Q5/7/8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | ALL | 5 | 8,202,413 | 1192 | -0.09 | -0.54 | 42.1 | +0.00 | [+0.00, +0.00] | 0.040 |  |  |
| before | ALL | 10 | 8,160,272 | 1187 | 0.20 | -0.48 | 44.9 | -0.00 | [-0.00, +0.00] | 0.868 |  |  |
| before | ALL | 21 | 8,068,001 | 1176 | 0.88 | -0.30 | 47.7 | +0.00 | [+0.00, +0.00] | 0.001 |  |  |
| after | ALL | 5 | 1,470,965 | 1192 | -0.06 | -0.32 | 47.8 | +0.00 | [+0.00, +0.00] | 0.001 |  |  |
| after | ALL | 10 | 1,464,049 | 1187 | 0.37 | -0.09 | 49.5 | +0.00 | [+0.00, +0.00] | 0.001 |  |  |
| after | ALL | 21 | 1,450,341 | 1176 | 1.32 | 0.28 | 50.9 | +0.00 | [+0.00, +0.00] | 0.001 |  |  |
| before | A all6 HARD YES | 5 | 147,254 | 1192 | 0.01 | -0.70 | 41.9 | +0.18 | [-0.16, +0.66] | 0.434 |  |  |
| before | A all6 HARD YES | 10 | 145,751 | 1187 | 0.44 | -0.84 | 43.3 | +0.29 | [-0.09, +0.86] | 0.162 |  |  |
| before | A all6 HARD YES | 21 | 144,091 | 1176 | 0.88 | -1.22 | 43.1 | +0.30 | [-0.19, +0.89] | 0.274 |  |  |
| after | A all6 HARD YES | 5 | 29,742 | 1192 | -0.30 | -0.67 | 46.1 | -0.25 | [-0.43, -0.09] | 0.002 |  |  |
| after | A all6 HARD YES | 10 | 29,439 | 1187 | 0.07 | -0.75 | 47.0 | -0.19 | [-0.45, +0.07] | 0.172 |  |  |
| after | A all6 HARD YES | 21 | 29,191 | 1176 | 0.51 | -1.29 | 46.2 | -0.06 | [-0.46, +0.36] | 0.798 |  |  |
| before | B not A | 5 | 8,055,159 | 1192 | -0.09 | -0.54 | 42.1 | -0.00 | [-0.01, +0.00] | 0.484 |  |  |
| before | B not A | 10 | 8,014,521 | 1187 | 0.20 | -0.48 | 44.9 | -0.01 | [-0.01, +0.00] | 0.146 |  |  |
| before | B not A | 21 | 7,923,910 | 1176 | 0.88 | -0.29 | 47.8 | -0.01 | [-0.02, +0.00] | 0.262 |  |  |
| after | B not A | 5 | 1,441,223 | 1192 | -0.05 | -0.31 | 47.8 | +0.01 | [+0.00, +0.01] | 0.008 |  |  |
| after | B not A | 10 | 1,434,610 | 1187 | 0.37 | -0.08 | 49.6 | +0.00 | [-0.00, +0.01] | 0.176 |  |  |
| after | B not A | 21 | 1,421,150 | 1176 | 1.33 | 0.31 | 51.0 | +0.00 | [-0.01, +0.01] | 0.724 |  |  |

## 2. A per year
| set | group | h | n | dates | mean% | median% | win% | excess% | 95% CI | p | FDR bank | FDR Q5/7/8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | A 2020 | 5 | 17,383 | 192 | 3.41 | -0.26 | 48.5 | +1.67 | [-0.59, +5.58] | 0.304 |  |  |
| before | A 2020 | 10 | 17,383 | 192 | 5.86 | 0.55 | 52.6 | +2.56 | [-0.19, +6.95] | 0.086 |  |  |
| before | A 2020 | 21 | 17,383 | 192 | 10.89 | 2.01 | 56.2 | +3.58 | [+0.62, +8.34] | 0.010 |  |  |
| after | A 2020 | 5 | 3,852 | 192 | 1.71 | 0.79 | 54.4 | +0.51 | [-0.20, +1.16] | 0.132 |  |  |
| after | A 2020 | 10 | 3,852 | 192 | 3.61 | 1.91 | 57.2 | +0.90 | [-0.08, +1.94] | 0.092 |  |  |
| after | A 2020 | 21 | 3,852 | 192 | 7.83 | 3.10 | 57.4 | +1.59 | [+0.20, +3.08] | 0.028 |  |  |
| before | A 2021 | 5 | 28,077 | 252 | 0.25 | -0.60 | 43.4 | +0.19 | [-0.29, +0.73] | 0.512 |  |  |
| before | A 2021 | 10 | 28,077 | 252 | 0.87 | -0.60 | 44.0 | +0.36 | [-0.25, +1.01] | 0.280 |  |  |
| before | A 2021 | 21 | 28,077 | 252 | 0.49 | -1.07 | 42.1 | +0.30 | [-0.57, +1.20] | 0.560 |  |  |
| after | A 2021 | 5 | 5,989 | 252 | -0.31 | -0.60 | 46.3 | -0.71 | [-1.10, -0.36] | 0.001 |  |  |
| after | A 2021 | 10 | 5,989 | 252 | 0.28 | -0.76 | 47.2 | -0.77 | [-1.34, -0.20] | 0.006 |  |  |
| after | A 2021 | 21 | 5,989 | 252 | 0.06 | -1.44 | 46.1 | -0.32 | [-1.31, +0.62] | 0.534 |  |  |
| before | A 2022 | 5 | 32,441 | 251 | -1.09 | -1.30 | 38.5 | -0.03 | [-0.30, +0.29] | 0.796 |  |  |
| before | A 2022 | 10 | 32,441 | 251 | -1.56 | -1.86 | 38.5 | -0.14 | [-0.48, +0.24] | 0.466 |  |  |
| before | A 2022 | 21 | 32,441 | 251 | -2.53 | -2.98 | 38.0 | -0.42 | [-0.99, +0.17] | 0.160 |  |  |
| after | A 2022 | 5 | 8,080 | 251 | -1.15 | -1.25 | 43.0 | -0.40 | [-0.75, -0.04] | 0.020 |  |  |
| after | A 2022 | 10 | 8,080 | 251 | -1.80 | -1.99 | 42.4 | -0.36 | [-0.87, +0.16] | 0.164 |  |  |
| after | A 2022 | 21 | 8,080 | 251 | -1.80 | -2.94 | 42.2 | +0.22 | [-0.67, +1.21] | 0.642 |  |  |
| before | A 2023 | 5 | 31,212 | 250 | -0.54 | -0.89 | 40.3 | -0.10 | [-0.27, +0.10] | 0.298 |  |  |
| before | A 2023 | 10 | 31,212 | 250 | -0.50 | -1.12 | 41.5 | -0.14 | [-0.38, +0.14] | 0.328 |  |  |
| before | A 2023 | 21 | 31,212 | 250 | -1.11 | -1.75 | 40.7 | -0.78 | [-1.14, -0.44] | 0.001 |  |  |
| after | A 2023 | 5 | 5,182 | 250 | -0.65 | -0.88 | 44.6 | -0.32 | [-0.62, -0.02] | 0.034 |  |  |
| after | A 2023 | 10 | 5,182 | 250 | -0.63 | -1.05 | 45.6 | -0.45 | [-0.81, -0.10] | 0.018 |  |  |
| after | A 2023 | 21 | 5,182 | 250 | -1.03 | -1.64 | 44.6 | -0.76 | [-1.27, -0.23] | 0.001 |  |  |
| before | A 2024 | 5 | 38,141 | 247 | -0.32 | -0.60 | 42.1 | -0.10 | [-0.30, +0.12] | 0.346 |  |  |
| before | A 2024 | 10 | 36,638 | 242 | 0.11 | -0.74 | 44.0 | -0.08 | [-0.35, +0.20] | 0.572 |  |  |
| before | A 2024 | 21 | 34,978 | 231 | 1.17 | -0.87 | 44.3 | +0.29 | [-0.19, +0.81] | 0.250 |  |  |
| after | A 2024 | 5 | 6,639 | 247 | -0.13 | -0.66 | 46.1 | -0.05 | [-0.41, +0.33] | 0.820 |  |  |
| after | A 2024 | 10 | 6,336 | 242 | 0.70 | -0.58 | 47.7 | +0.16 | [-0.40, +0.79] | 0.560 |  |  |
| after | A 2024 | 21 | 6,088 | 231 | 0.67 | -1.30 | 46.0 | -0.63 | [-1.19, -0.06] | 0.026 |  |  |

## 3. Q8, Q5, Q7 (alone and within A)
| set | group | h | n | dates | mean% | median% | win% | excess% | 95% CI | p | FDR bank | FDR Q5/7/8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | sq5_big_red_recent YES | 5 | 2,047,395 | 1192 | 0.19 | -0.50 | 43.0 | +0.24 | [-0.04, +0.61] | 0.118 | no | no |
| before | sq5_big_red_recent YES | 10 | 2,024,936 | 1187 | 0.46 | -0.49 | 44.9 | +0.23 | [-0.06, +0.61] | 0.112 | no | no |
| before | sq5_big_red_recent YES | 21 | 2,002,566 | 1176 | 1.13 | -0.28 | 47.9 | +0.19 | [-0.13, +0.59] | 0.250 | no | no |
| after | sq5_big_red_recent YES | 5 | 363,739 | 1192 | 0.26 | -0.10 | 49.3 | +0.15 | [+0.09, +0.20] | 0.001 | yes | yes |
| after | sq5_big_red_recent YES | 10 | 360,525 | 1187 | 0.66 | 0.08 | 50.4 | +0.17 | [+0.08, +0.24] | 0.001 | yes | yes |
| after | sq5_big_red_recent YES | 21 | 357,005 | 1176 | 1.61 | 0.58 | 51.9 | +0.08 | [-0.02, +0.18] | 0.146 | no | no |
| before | sq5_big_red_recent NO | 5 | 6,155,018 | 1192 | -0.18 | -0.55 | 41.8 | -0.08 | [-0.19, +0.01] | 0.106 |  |  |
| before | sq5_big_red_recent NO | 10 | 6,135,336 | 1187 | 0.12 | -0.48 | 44.8 | -0.08 | [-0.19, +0.03] | 0.144 |  |  |
| before | sq5_big_red_recent NO | 21 | 6,065,435 | 1176 | 0.79 | -0.30 | 47.7 | -0.06 | [-0.17, +0.04] | 0.260 |  |  |
| after | sq5_big_red_recent NO | 5 | 1,107,226 | 1192 | -0.16 | -0.39 | 47.3 | -0.05 | [-0.07, -0.03] | 0.001 |  |  |
| after | sq5_big_red_recent NO | 10 | 1,103,524 | 1187 | 0.27 | -0.15 | 49.3 | -0.05 | [-0.08, -0.03] | 0.001 |  |  |
| after | sq5_big_red_recent NO | 21 | 1,093,336 | 1176 | 1.22 | 0.18 | 50.6 | -0.03 | [-0.06, +0.01] | 0.150 |  |  |
| before | A&sq5_big_red_recent YES | 5 | 47,915 | 1192 | 0.58 | -0.60 | 43.1 | +0.73 | [-0.00, +2.03] | 0.052 | no | no |
| before | A&sq5_big_red_recent YES | 10 | 47,227 | 1187 | 1.12 | -0.70 | 44.3 | +0.96 | [+0.10, +2.40] | 0.010 | yes | yes |
| before | A&sq5_big_red_recent YES | 21 | 46,704 | 1176 | 1.52 | -0.90 | 44.5 | +0.96 | [-0.02, +2.60] | 0.068 | no | no |
| after | A&sq5_big_red_recent YES | 5 | 10,301 | 1128 | -0.00 | -0.34 | 47.9 | -0.16 | [-0.40, +0.08] | 0.194 | no | no |
| after | A&sq5_big_red_recent YES | 10 | 10,175 | 1123 | 0.48 | -0.29 | 48.9 | +0.02 | [-0.34, +0.42] | 0.958 | no | no |
| after | A&sq5_big_red_recent YES | 21 | 10,126 | 1113 | 0.60 | -0.78 | 47.4 | -0.08 | [-0.56, +0.45] | 0.774 | no | no |
| before | A&sq5_big_red_recent NO | 5 | 99,339 | 1192 | -0.26 | -0.77 | 41.4 | -0.09 | [-0.30, +0.10] | 0.298 |  |  |
| before | A&sq5_big_red_recent NO | 10 | 98,524 | 1187 | 0.11 | -0.91 | 42.8 | -0.03 | [-0.29, +0.20] | 0.798 |  |  |
| before | A&sq5_big_red_recent NO | 21 | 97,387 | 1176 | 0.58 | -1.36 | 42.5 | -0.02 | [-0.38, +0.35] | 0.900 |  |  |
| after | A&sq5_big_red_recent NO | 5 | 19,441 | 1190 | -0.45 | -0.86 | 45.1 | -0.30 | [-0.52, -0.09] | 0.002 |  |  |
| after | A&sq5_big_red_recent NO | 10 | 19,264 | 1185 | -0.14 | -0.98 | 46.0 | -0.29 | [-0.58, +0.02] | 0.074 |  |  |
| after | A&sq5_big_red_recent NO | 21 | 19,065 | 1174 | 0.46 | -1.49 | 45.6 | -0.05 | [-0.55, +0.48] | 0.830 |  |  |
| before | sq7_lowerbb_reclaim YES | 5 | 2,959,166 | 1192 | 0.25 | -0.48 | 43.8 | +0.16 | [+0.06, +0.28] | 0.001 | yes | yes |
| before | sq7_lowerbb_reclaim YES | 10 | 2,943,191 | 1187 | 0.62 | -0.40 | 46.2 | +0.20 | [+0.10, +0.33] | 0.001 | yes | yes |
| before | sq7_lowerbb_reclaim YES | 21 | 2,926,420 | 1176 | 1.30 | -0.19 | 48.7 | +0.23 | [+0.12, +0.38] | 0.001 | yes | yes |
| after | sq7_lowerbb_reclaim YES | 5 | 558,494 | 1192 | 0.07 | -0.08 | 49.4 | +0.01 | [-0.03, +0.06] | 0.520 | no | no |
| after | sq7_lowerbb_reclaim YES | 10 | 555,576 | 1187 | 0.58 | 0.24 | 51.2 | +0.05 | [-0.01, +0.11] | 0.096 | no | no |
| after | sq7_lowerbb_reclaim YES | 21 | 552,869 | 1176 | 1.53 | 0.68 | 52.3 | +0.14 | [+0.06, +0.23] | 0.001 | yes | yes |
| before | sq7_lowerbb_reclaim NO | 5 | 5,243,247 | 1192 | -0.28 | -0.57 | 41.1 | -0.09 | [-0.15, -0.04] | 0.001 |  |  |
| before | sq7_lowerbb_reclaim NO | 10 | 5,217,081 | 1187 | -0.03 | -0.52 | 44.1 | -0.11 | [-0.18, -0.06] | 0.001 |  |  |
| before | sq7_lowerbb_reclaim NO | 21 | 5,141,581 | 1176 | 0.63 | -0.36 | 47.2 | -0.13 | [-0.22, -0.06] | 0.001 |  |  |
| after | sq7_lowerbb_reclaim NO | 5 | 912,471 | 1192 | -0.14 | -0.48 | 46.8 | -0.01 | [-0.04, +0.02] | 0.550 |  |  |
| after | sq7_lowerbb_reclaim NO | 10 | 908,473 | 1187 | 0.24 | -0.32 | 48.5 | -0.03 | [-0.07, +0.00] | 0.082 |  |  |
| after | sq7_lowerbb_reclaim NO | 21 | 897,472 | 1176 | 1.19 | 0.02 | 50.1 | -0.09 | [-0.14, -0.03] | 0.001 |  |  |
| before | A&sq7_lowerbb_reclaim YES | 5 | 23,053 | 1190 | 0.84 | -0.60 | 42.4 | +0.80 | [-0.60, +3.52] | 0.678 | no | no |
| before | A&sq7_lowerbb_reclaim YES | 10 | 22,880 | 1185 | 1.63 | -0.54 | 44.8 | +1.20 | [-0.43, +4.18] | 0.604 | no | no |
| before | A&sq7_lowerbb_reclaim YES | 21 | 22,725 | 1174 | 1.95 | -0.60 | 45.1 | +1.04 | [-0.65, +4.13] | 0.636 | no | no |
| after | A&sq7_lowerbb_reclaim YES | 5 | 4,523 | 961 | -0.62 | -0.50 | 46.7 | -0.66 | [-0.96, -0.37] | 0.001 | yes | yes |
| after | A&sq7_lowerbb_reclaim YES | 10 | 4,497 | 957 | 0.16 | -0.15 | 49.0 | -0.47 | [-0.87, -0.04] | 0.028 | no | no |
| after | A&sq7_lowerbb_reclaim YES | 21 | 4,481 | 949 | 0.52 | -0.54 | 48.4 | -0.59 | [-1.11, -0.03] | 0.042 | no | no |
| before | A&sq7_lowerbb_reclaim NO | 5 | 124,201 | 1192 | -0.14 | -0.77 | 41.9 | +0.06 | [-0.13, +0.26] | 0.536 |  |  |
| before | A&sq7_lowerbb_reclaim NO | 10 | 122,871 | 1187 | 0.22 | -0.97 | 43.0 | +0.12 | [-0.11, +0.37] | 0.318 |  |  |
| before | A&sq7_lowerbb_reclaim NO | 21 | 121,366 | 1176 | 0.68 | -1.43 | 42.8 | +0.16 | [-0.23, +0.53] | 0.452 |  |  |
| after | A&sq7_lowerbb_reclaim NO | 5 | 25,219 | 1191 | -0.24 | -0.71 | 46.0 | -0.18 | [-0.37, +0.03] | 0.100 |  |  |
| after | A&sq7_lowerbb_reclaim NO | 10 | 24,942 | 1186 | 0.06 | -0.88 | 46.7 | -0.13 | [-0.41, +0.17] | 0.382 |  |  |
| after | A&sq7_lowerbb_reclaim NO | 21 | 24,710 | 1175 | 0.50 | -1.42 | 45.8 | +0.04 | [-0.42, +0.50] | 0.940 |  |  |
| before | sq8_above_last_red_high YES | 5 | 2,895,679 | 1192 | -0.44 | -0.53 | 41.2 | -0.43 | [-0.67, -0.23] | 0.001 | yes | yes |
| before | sq8_above_last_red_high YES | 10 | 2,889,584 | 1187 | -0.17 | -0.44 | 44.7 | -0.49 | [-0.79, -0.27] | 0.001 | yes | yes |
| before | sq8_above_last_red_high YES | 21 | 2,862,079 | 1176 | 0.36 | -0.23 | 48.2 | -0.60 | [-0.92, -0.36] | 0.001 | yes | yes |
| after | sq8_above_last_red_high YES | 5 | 509,497 | 1192 | -0.41 | -0.59 | 46.0 | -0.12 | [-0.18, -0.07] | 0.001 | yes | yes |
| after | sq8_above_last_red_high YES | 10 | 508,392 | 1187 | 0.07 | -0.33 | 48.4 | -0.10 | [-0.18, -0.03] | 0.006 | yes | yes |
| after | sq8_above_last_red_high YES | 21 | 504,608 | 1176 | 0.96 | 0.04 | 50.1 | -0.10 | [-0.20, -0.00] | 0.040 | no | no |
| before | sq8_above_last_red_high NO | 5 | 5,306,734 | 1192 | 0.10 | -0.54 | 42.6 | +0.24 | [+0.13, +0.38] | 0.001 |  |  |
| before | sq8_above_last_red_high NO | 10 | 5,270,688 | 1187 | 0.41 | -0.50 | 44.9 | +0.27 | [+0.15, +0.42] | 0.001 |  |  |
| before | sq8_above_last_red_high NO | 21 | 5,205,922 | 1176 | 1.16 | -0.35 | 47.5 | +0.33 | [+0.19, +0.50] | 0.001 |  |  |
| after | sq8_above_last_red_high NO | 5 | 961,468 | 1192 | 0.12 | -0.18 | 48.8 | +0.06 | [+0.03, +0.09] | 0.001 |  |  |
| after | sq8_above_last_red_high NO | 10 | 955,657 | 1187 | 0.52 | 0.03 | 50.1 | +0.05 | [+0.01, +0.09] | 0.008 |  |  |
| after | sq8_above_last_red_high NO | 21 | 945,733 | 1176 | 1.50 | 0.41 | 51.3 | +0.05 | [-0.00, +0.11] | 0.062 |  |  |
| before | A&sq8_above_last_red_high YES | 5 | 17,302 | 1188 | -0.33 | -0.72 | 40.7 | -0.36 | [-0.76, +0.07] | 0.086 | no | no |
| before | A&sq8_above_last_red_high YES | 10 | 17,212 | 1183 | 0.06 | -0.79 | 42.8 | -0.33 | [-0.74, +0.04] | 0.094 | no | no |
| before | A&sq8_above_last_red_high YES | 21 | 17,055 | 1172 | 0.35 | -1.04 | 43.2 | -0.47 | [-1.09, +0.16] | 0.150 | no | no |
| after | A&sq8_above_last_red_high YES | 5 | 3,391 | 944 | -0.36 | -0.73 | 45.8 | -0.36 | [-0.85, +0.11] | 0.132 | no | no |
| after | A&sq8_above_last_red_high YES | 10 | 3,364 | 939 | 0.01 | -0.60 | 47.7 | -0.30 | [-0.86, +0.29] | 0.330 | no | no |
| after | A&sq8_above_last_red_high YES | 21 | 3,317 | 928 | 0.35 | -1.36 | 46.4 | -0.39 | [-1.40, +0.60] | 0.412 | no | no |
| before | A&sq8_above_last_red_high NO | 5 | 129,952 | 1192 | 0.06 | -0.70 | 42.1 | +0.25 | [-0.12, +0.75] | 0.274 |  |  |
| before | A&sq8_above_last_red_high NO | 10 | 128,539 | 1187 | 0.49 | -0.85 | 43.3 | +0.37 | [-0.02, +1.02] | 0.082 |  |  |
| before | A&sq8_above_last_red_high NO | 21 | 127,036 | 1176 | 0.95 | -1.24 | 43.1 | +0.40 | [-0.08, +1.06] | 0.132 |  |  |
| after | A&sq8_above_last_red_high NO | 5 | 26,351 | 1191 | -0.29 | -0.67 | 46.1 | -0.24 | [-0.41, -0.05] | 0.022 |  |  |
| after | A&sq8_above_last_red_high NO | 10 | 26,075 | 1186 | 0.08 | -0.77 | 46.9 | -0.17 | [-0.44, +0.11] | 0.228 |  |  |
| after | A&sq8_above_last_red_high NO | 21 | 25,874 | 1175 | 0.53 | -1.27 | 46.2 | -0.02 | [-0.41, +0.38] | 0.950 |  |  |

## 4. Other story questions
| set | group | h | n | dates | mean% | median% | win% | excess% | 95% CI | p | FDR bank | FDR Q5/7/8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | sq1_lower_highs3 YES | 5 | 1,924,773 | 1192 | 0.17 | -0.54 | 43.3 | +0.22 | [-0.04, +0.58] | 0.116 | no |  |
| before | sq1_lower_highs3 YES | 10 | 1,916,444 | 1187 | 0.54 | -0.48 | 45.8 | +0.30 | [+0.00, +0.72] | 0.050 | no |  |
| before | sq1_lower_highs3 YES | 21 | 1,900,103 | 1176 | 1.42 | -0.28 | 48.3 | +0.55 | [+0.21, +1.00] | 0.001 | yes |  |
| after | sq1_lower_highs3 YES | 5 | 364,242 | 1192 | 0.16 | -0.12 | 49.2 | +0.08 | [+0.03, +0.14] | 0.004 | yes |  |
| after | sq1_lower_highs3 YES | 10 | 362,656 | 1187 | 0.63 | 0.18 | 50.9 | +0.11 | [+0.04, +0.18] | 0.004 | yes |  |
| after | sq1_lower_highs3 YES | 21 | 360,195 | 1176 | 1.57 | 0.57 | 51.8 | +0.19 | [+0.09, +0.29] | 0.001 | yes |  |
| before | A&sq1_lower_highs3 YES | 5 | 15,941 | 1188 | -0.19 | -0.66 | 42.1 | -0.07 | [-0.33, +0.18] | 0.572 | no |  |
| before | A&sq1_lower_highs3 YES | 10 | 15,808 | 1183 | 0.16 | -0.84 | 43.0 | -0.04 | [-0.41, +0.39] | 0.824 | no |  |
| before | A&sq1_lower_highs3 YES | 21 | 15,636 | 1172 | 1.16 | -0.91 | 44.3 | +0.45 | [-0.26, +1.35] | 0.234 | no |  |
| after | A&sq1_lower_highs3 YES | 5 | 2,940 | 876 | 0.03 | -0.57 | 46.9 | +0.08 | [-0.34, +0.53] | 0.730 | no |  |
| after | A&sq1_lower_highs3 YES | 10 | 2,911 | 871 | 0.61 | -0.54 | 48.2 | +0.37 | [-0.29, +1.02] | 0.276 | no |  |
| after | A&sq1_lower_highs3 YES | 21 | 2,882 | 862 | 1.60 | -0.14 | 49.4 | +0.92 | [-0.07, +2.00] | 0.060 | no |  |
| before | sq2_higher_lows3 YES | 5 | 2,163,793 | 1192 | -0.35 | -0.56 | 40.7 | -0.14 | [-0.22, -0.06] | 0.002 | yes |  |
| before | sq2_higher_lows3 YES | 10 | 2,149,206 | 1187 | -0.18 | -0.53 | 43.4 | -0.20 | [-0.29, -0.11] | 0.001 | yes |  |
| before | sq2_higher_lows3 YES | 21 | 2,119,070 | 1176 | 0.28 | -0.42 | 46.4 | -0.36 | [-0.50, -0.25] | 0.001 | yes |  |
| after | sq2_higher_lows3 YES | 5 | 367,062 | 1192 | -0.16 | -0.49 | 46.7 | -0.04 | [-0.10, +0.01] | 0.102 | no |  |
| after | sq2_higher_lows3 YES | 10 | 364,905 | 1187 | 0.13 | -0.49 | 47.7 | -0.11 | [-0.18, -0.04] | 0.002 | yes |  |
| after | sq2_higher_lows3 YES | 21 | 360,442 | 1176 | 1.07 | -0.10 | 49.7 | -0.22 | [-0.31, -0.12] | 0.001 | yes |  |
| before | A&sq2_higher_lows3 YES | 5 | 46,108 | 1192 | -0.31 | -0.78 | 42.5 | -0.15 | [-0.36, +0.03] | 0.114 | no |  |
| before | A&sq2_higher_lows3 YES | 10 | 45,617 | 1187 | -0.10 | -1.01 | 43.1 | -0.24 | [-0.52, +0.03] | 0.088 | no |  |
| before | A&sq2_higher_lows3 YES | 21 | 45,112 | 1176 | 0.36 | -1.37 | 43.3 | -0.27 | [-0.69, +0.16] | 0.204 | no |  |
| after | A&sq2_higher_lows3 YES | 5 | 9,793 | 1157 | -0.21 | -0.74 | 46.1 | -0.27 | [-0.54, +0.01] | 0.058 | no |  |
| after | A&sq2_higher_lows3 YES | 10 | 9,681 | 1152 | -0.14 | -1.15 | 45.7 | -0.35 | [-0.80, +0.08] | 0.106 | no |  |
| after | A&sq2_higher_lows3 YES | 21 | 9,610 | 1141 | 0.66 | -1.48 | 45.6 | +0.06 | [-0.57, +0.72] | 0.826 | no |  |
| before | sq3_shrinking_green3 YES | 5 | 1,175,448 | 1192 | -0.25 | -0.50 | 43.1 | -0.18 | [-0.31, -0.07] | 0.001 | yes |  |
| before | sq3_shrinking_green3 YES | 10 | 1,171,296 | 1187 | -0.02 | -0.44 | 45.7 | -0.20 | [-0.36, -0.08] | 0.001 | yes |  |
| before | sq3_shrinking_green3 YES | 21 | 1,156,810 | 1176 | 0.66 | -0.20 | 48.6 | -0.20 | [-0.39, -0.01] | 0.030 | no |  |
| after | sq3_shrinking_green3 YES | 5 | 229,225 | 1192 | 0.07 | -0.22 | 48.5 | +0.01 | [-0.03, +0.05] | 0.494 | no |  |
| after | sq3_shrinking_green3 YES | 10 | 228,462 | 1187 | 0.47 | 0.00 | 50.0 | +0.03 | [-0.03, +0.08] | 0.368 | no |  |
| after | sq3_shrinking_green3 YES | 21 | 226,331 | 1176 | 1.40 | 0.41 | 51.3 | +0.04 | [-0.05, +0.11] | 0.388 | no |  |
| before | A&sq3_shrinking_green3 YES | 5 | 25,734 | 1192 | -0.23 | -0.72 | 43.1 | -0.10 | [-0.31, +0.09] | 0.300 | no |  |
| before | A&sq3_shrinking_green3 YES | 10 | 25,480 | 1187 | 0.21 | -0.88 | 44.0 | +0.08 | [-0.25, +0.45] | 0.632 | no |  |
| before | A&sq3_shrinking_green3 YES | 21 | 25,107 | 1176 | 0.47 | -1.14 | 44.2 | -0.14 | [-0.58, +0.34] | 0.548 | no |  |
| after | A&sq3_shrinking_green3 YES | 5 | 5,557 | 1079 | -0.23 | -0.79 | 46.0 | -0.30 | [-0.61, +0.02] | 0.060 | no |  |
| after | A&sq3_shrinking_green3 YES | 10 | 5,515 | 1074 | 0.09 | -0.72 | 47.6 | -0.08 | [-0.51, +0.35] | 0.718 | no |  |
| after | A&sq3_shrinking_green3 YES | 21 | 5,470 | 1065 | 0.46 | -1.12 | 46.3 | -0.09 | [-0.77, +0.58] | 0.804 | no |  |
| before | sq4_below_mid_5of10 YES | 5 | 4,148,385 | 1192 | 0.10 | -0.54 | 43.2 | +0.12 | [+0.05, +0.19] | 0.001 | yes |  |
| before | sq4_below_mid_5of10 YES | 10 | 4,125,497 | 1187 | 0.44 | -0.49 | 45.6 | +0.15 | [+0.07, +0.23] | 0.001 | yes |  |
| before | sq4_below_mid_5of10 YES | 21 | 4,092,672 | 1176 | 1.27 | -0.30 | 48.1 | +0.28 | [+0.19, +0.39] | 0.001 | yes |  |
| after | sq4_below_mid_5of10 YES | 5 | 789,701 | 1192 | 0.01 | -0.22 | 48.5 | +0.01 | [-0.03, +0.05] | 0.780 | no |  |
| after | sq4_below_mid_5of10 YES | 10 | 785,760 | 1187 | 0.44 | 0.05 | 50.2 | +0.02 | [-0.03, +0.07] | 0.434 | no |  |
| after | sq4_below_mid_5of10 YES | 21 | 780,215 | 1176 | 1.49 | 0.50 | 51.6 | +0.12 | [+0.05, +0.19] | 0.001 | yes |  |
| before | A&sq4_below_mid_5of10 YES | 5 | 53,324 | 1192 | -0.31 | -0.64 | 41.7 | -0.19 | [-0.43, +0.04] | 0.100 | no |  |
| before | A&sq4_below_mid_5of10 YES | 10 | 53,039 | 1187 | 0.15 | -0.74 | 43.2 | -0.02 | [-0.29, +0.26] | 0.908 | no |  |
| before | A&sq4_below_mid_5of10 YES | 21 | 52,547 | 1176 | 0.66 | -0.90 | 43.7 | +0.10 | [-0.29, +0.50] | 0.666 | no |  |
| after | A&sq4_below_mid_5of10 YES | 5 | 10,934 | 1154 | -0.48 | -0.63 | 46.1 | -0.33 | [-0.55, -0.09] | 0.006 | yes |  |
| after | A&sq4_below_mid_5of10 YES | 10 | 10,862 | 1149 | -0.04 | -0.72 | 47.0 | -0.23 | [-0.55, +0.06] | 0.116 | no |  |
| after | A&sq4_below_mid_5of10 YES | 21 | 10,775 | 1138 | 0.69 | -0.73 | 47.8 | +0.08 | [-0.37, +0.57] | 0.696 | no |  |
| before | sq6_dip_vol_lower YES | 5 | 4,106,310 | 1192 | -0.23 | -0.55 | 42.0 | -0.10 | [-0.22, -0.01] | 0.016 | yes |  |
| before | sq6_dip_vol_lower YES | 10 | 4,085,957 | 1187 | 0.01 | -0.49 | 44.8 | -0.13 | [-0.25, -0.03] | 0.006 | yes |  |
| before | sq6_dip_vol_lower YES | 21 | 4,039,423 | 1176 | 0.62 | -0.34 | 47.5 | -0.18 | [-0.32, -0.06] | 0.001 | yes |  |
| after | sq6_dip_vol_lower YES | 5 | 746,341 | 1192 | -0.05 | -0.33 | 47.7 | +0.00 | [-0.02, +0.02] | 0.734 | no |  |
| after | sq6_dip_vol_lower YES | 10 | 743,050 | 1187 | 0.32 | -0.13 | 49.4 | -0.00 | [-0.03, +0.02] | 0.780 | no |  |
| after | sq6_dip_vol_lower YES | 21 | 735,764 | 1176 | 1.24 | 0.17 | 50.5 | -0.04 | [-0.08, -0.00] | 0.024 | no |  |
| before | A&sq6_dip_vol_lower YES | 5 | 71,500 | 1192 | 0.24 | -0.71 | 41.8 | +0.44 | [-0.11, +1.40] | 0.248 | no |  |
| before | A&sq6_dip_vol_lower YES | 10 | 70,780 | 1187 | 0.43 | -0.81 | 43.1 | +0.34 | [-0.25, +1.38] | 0.554 | no |  |
| before | A&sq6_dip_vol_lower YES | 21 | 69,925 | 1176 | 0.75 | -1.21 | 43.0 | +0.20 | [-0.46, +1.31] | 0.714 | no |  |
| after | A&sq6_dip_vol_lower YES | 5 | 14,262 | 1179 | -0.12 | -0.60 | 46.7 | -0.06 | [-0.28, +0.18] | 0.572 | no |  |
| after | A&sq6_dip_vol_lower YES | 10 | 14,128 | 1174 | 0.01 | -0.71 | 47.1 | -0.13 | [-0.42, +0.17] | 0.446 | no |  |
| after | A&sq6_dip_vol_lower YES | 21 | 14,015 | 1163 | 0.53 | -1.39 | 46.0 | +0.07 | [-0.47, +0.64] | 0.848 | no |  |
| before | sq9_breakdown_vol YES | 5 | 760,458 | 1192 | 0.07 | -0.42 | 45.4 | -0.06 | [-0.39, +0.20] | 0.714 | no |  |
| before | sq9_breakdown_vol YES | 10 | 753,737 | 1187 | 0.46 | -0.30 | 47.6 | -0.04 | [-0.43, +0.28] | 0.870 | no |  |
| before | sq9_breakdown_vol YES | 21 | 749,299 | 1176 | 1.00 | -0.09 | 49.5 | -0.09 | [-0.46, +0.25] | 0.678 | no |  |
| after | sq9_breakdown_vol YES | 5 | 157,844 | 1192 | 0.24 | -0.04 | 49.7 | +0.13 | [+0.05, +0.21] | 0.004 | yes |  |
| after | sq9_breakdown_vol YES | 10 | 156,889 | 1187 | 0.82 | 0.37 | 51.9 | +0.20 | [+0.10, +0.30] | 0.001 | yes |  |
| after | sq9_breakdown_vol YES | 21 | 156,067 | 1176 | 1.63 | 0.69 | 52.5 | +0.28 | [+0.15, +0.43] | 0.001 | yes |  |
| before | A&sq9_breakdown_vol YES | 5 | 1,641 | 739 | -0.67 | -0.66 | 42.8 | -0.72 | [-1.19, -0.24] | 0.004 | yes |  |
| before | A&sq9_breakdown_vol YES | 10 | 1,637 | 737 | 0.51 | -0.60 | 45.6 | +0.12 | [-1.26, +2.20] | 0.998 | no |  |
| before | A&sq9_breakdown_vol YES | 21 | 1,625 | 730 | -0.63 | -1.22 | 43.6 | -1.23 | [-2.46, +0.25] | 0.096 | no |  |
| after | A&sq9_breakdown_vol YES | 5 | 430 | 294 | -1.10 | -1.23 | 43.3 | -1.07 | [-1.78, -0.51] | 0.002 | yes |  |
| after | A&sq9_breakdown_vol YES | 10 | 428 | 293 | 0.12 | -0.75 | 47.9 | -0.53 | [-1.76, +1.07] | 0.444 | no |  |
| after | A&sq9_breakdown_vol YES | 21 | 424 | 290 | -1.43 | -2.89 | 40.1 | -2.20 | [-3.39, -0.92] | 0.002 | yes |  |

Code: `buyable_v1/run.py` (box `/workspace/state_test/story_q/buyable_v1/`). Locked files were not modified.