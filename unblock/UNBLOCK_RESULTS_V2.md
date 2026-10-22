# UNBLOCK_RESULTS_V2 — wave 2 (2020-24 only; 2025-26 not opened)
Pre-registration: UNBLOCK_V2.md (24e45c9), UNBLOCK_V2_ADDENDUM.md (7c7b49e), UNBLOCK_V2_ADDENDUM2.md (3854ca6), all committed before results.

## Headline
**0 of 52 features pass** (48 buildable minus 12 still open = 36, + 3 market-cap insider versions, + PV-TF-159, + 12 v1.2 rewritten timing ideas).
Luck-correction family: 13,851 prior + 208 wave-2 p-values (52 x 2 exits x 2 periods) = **14,059**.
Population: story_q 2020-24 minus drop_list_v2, 21 forward bars = 2,408,833; minus 39,459 stock-days with known mcap < $100M = **2,369,374** (mcap known on 66.8%; unknown kept). Benchmark (same-date mean) uses the filtered population.
None of the 40 ideas v1.2 moved to BLOCKED is in scope.

## Closest misses
- **GAPD1_UP8 (PV-TF-082..089 family, D-1 gap up >= 8%), Exit A**: win 58.2% / 54.6%, excess +0.26 / +0.21 pts, but q = 1.0 (not significant). Fails on 2023-24 win and q.
- **MICROCAP (FND-NB-001, $100-300M), Exit A**: excess +1.56 / +1.08 pts with q ~ 0 in both periods, but win 54.5% / 51.8% (< 55). Exit B win 48.6 / 46.6. Size effect is real in mean, not in hit rate.
- **DE2 (FND-TR-014)**: excess +0.32 / +0.26 (q ~ 0), win 51.8 / 50.9.

## All results (2020-22 / 2023-24; q = max across periods)
| id | feature | min n | A win | A excess | A q | B win | B excess | B q | no-data share |
|---|---|---|---|---|---|---|---|---|---|
| PV-TF-159 | SMA20_SLOPE_UP | 558410 | 49.4/48.3 | -0.06/+0.01 | 1.000 | 47.0/46.4 | -0.02/-0.02 | 1.000 | 0.00 |
| PV-TF-082 | GAPD1_UP1 | 146813 | 54.3/50.0 | +0.15/+0.07 | 1.000 | 50.6/48.2 | +0.08/+0.16 | 1.000 | 0.00 |
| PV-TF-083 | GAPD1_DN1 | 124310 | 53.6/50.5 | +0.12/+0.17 | 1.000 | 50.7/48.1 | +0.11/+0.13 | 1.000 | 0.00 |
| PV-TF-084 | GAPD1_UP2 | 51888 | 56.1/50.7 | +0.24/+0.10 | 1.000 | 50.1/47.6 | +0.13/+0.29 | 1.000 | 0.00 |
| PV-TF-085 | GAPD1_DN2 | 42236 | 54.6/52.2 | +0.35/+0.19 | 1.000 | 51.2/48.3 | +0.34/+0.10 | 1.000 | 0.00 |
| PV-TF-086 | GAPD1_UP4 | 14349 | 57.2/52.5 | +0.20/+0.35 | 1.000 | 47.6/47.1 | -0.19/+0.49 | 1.000 | 0.00 |
| PV-TF-087 | GAPD1_DN4 | 11374 | 53.9/54.8 | +0.34/+0.07 | 1.000 | 49.5/49.8 | +0.62/-0.16 | 1.000 | 0.00 |
| PV-TF-088 | GAPD1_UP8 | 3785 | 58.2/54.6 | +0.26/+0.21 | 1.000 | 46.8/47.6 | -0.50/+0.41 | 1.000 | 0.00 |
| PV-TF-089 | GAPD1_DN8 | 3070 | 50.6/53.8 | -0.69/+0.08 | 1.000 | 42.6/48.5 | -0.17/+0.16 | 1.000 | 0.00 |
| PV-TF-430 | SVR1_HI | 252395 | 49.5/48.6 | -0.08/-0.05 | 1.000 | 47.3/47.2 | -0.05/-0.02 | 1.000 | 0.04 |
| PV-TF-431 | SVR1_LO | 105521 | 50.1/48.2 | +0.03/+0.08 | 1.000 | 47.5/46.7 | -0.02/+0.04 | 1.000 | 0.04 |
| PV-TF-432 | SVR1_JUMP | 234079 | 50.6/48.6 | -0.02/+0.02 | 1.000 | 48.3/47.1 | -0.04/+0.00 | 1.000 | 0.04 |
| PV-TF-433 | SVR5_HI | 176911 | 48.8/48.5 | -0.12/-0.08 | 0.764 | 46.6/47.1 | -0.11/-0.05 | 1.000 | 0.04 |
| PV-TF-434 | SVR5_LO | 68841 | 50.3/48.3 | +0.06/+0.09 | 1.000 | 47.5/46.6 | -0.00/+0.08 | 1.000 | 0.04 |
| PV-TF-435 | SVR5_JUMP | 144415 | 50.1/48.3 | -0.10/+0.03 | 1.000 | 48.0/47.0 | -0.11/+0.02 | 1.000 | 0.04 |
| PV-TF-436 | SVR20_HI | 121378 | 48.2/48.0 | -0.17/-0.12 | 0.020 | 45.8/46.5 | -0.16/-0.12 | 0.044 | 0.04 |
| PV-TF-437 | SVR20_LO | 42631 | 51.0/47.8 | +0.07/+0.12 | 1.000 | 48.2/46.2 | -0.01/+0.07 | 1.000 | 0.04 |
| PV-TF-438 | SVR20_JUMP | 47106 | 50.1/47.0 | -0.12/+0.12 | 1.000 | 47.7/45.7 | -0.11/+0.10 | 1.000 | 0.04 |
| PV-TF-439 | SVR5_TOPDEC | 119827 | 50.3/48.4 | +0.01/+0.02 | 1.000 | 48.2/47.2 | -0.04/+0.01 | 1.000 | 0.05 |
| PV-TF-440 | PRICEUP_SVRUP | 89757 | 49.0/47.7 | -0.19/-0.14 | 0.253 | 46.6/46.5 | -0.25/-0.11 | 1.000 | 0.04 |
| FND-NB-001 | MICROCAP | 30785 | 54.5/51.8 | +1.55/+1.08 | 0.000 | 48.6/46.6 | +2.28/+1.53 | 0.000 | 0.34 |
| SUP-NB-004 | SHARES_UP20 | 46970 | 49.2/47.9 | -0.13/-0.32 | 1.000 | 45.9/44.9 | +0.10/-0.05 | 1.000 | 0.38 |
| PV-TF-452 | INS_SELL_1PCT_5 | 1320 | 47.6/56.0 | +0.29/+1.38 | 1.000 | 46.1/55.2 | +0.20/+1.50 | 1.000 | 0.34 |
| PV-TF-455 | INS_SELL_1PCT_30 | 8250 | 49.4/51.6 | +0.34/+0.60 | 0.590 | 47.1/49.8 | +0.16/+0.68 | 1.000 | 0.34 |
| PV-TF-458 | INS_SELL_1PCT_90 | 22256 | 50.9/51.0 | +0.02/+0.39 | 1.000 | 48.7/49.5 | +0.10/+0.44 | 1.000 | 0.34 |
| PV-TF-446 | FTD_01 | 78816 | 51.5/48.6 | +0.17/-0.08 | 1.000 | 47.7/45.7 | +0.47/+0.05 | 1.000 | 0.34 |
| PV-TF-447 | FTD_05 | 18455 | 52.2/49.0 | +0.17/-0.13 | 1.000 | 46.8/44.0 | +1.17/-0.20 | 1.000 | 0.34 |
| PV-TF-448 | FTD_SPIKE | 291073 | 50.8/48.8 | +0.06/-0.04 | 1.000 | 48.6/47.0 | +0.06/-0.07 | 0.294 | 0.07 |
| PV-TF-449 | FTD_T35 | 275236 | 50.7/49.0 | +0.02/+0.06 | 1.000 | 48.5/47.2 | +0.05/+0.02 | 1.000 | 0.00 |
| EVT-NB-004 | CASH_RUNWAY4Q | 79536 | 51.2/49.1 | +0.30/+0.01 | 1.000 | 47.6/45.8 | +0.54/+0.17 | 1.000 | 0.29 |
| FND-NB-004 | UNPROFITABLE | 251829 | 49.8/49.8 | +0.13/+0.33 | 1.000 | 46.9/47.3 | +0.30/+0.39 | 1.000 | 0.32 |
| FND-NB-005 | REV_YOY30 | 96497 | 49.6/49.4 | +0.15/+0.32 | 1.000 | 47.7/47.7 | +0.20/+0.35 | 1.000 | 0.39 |
| FND-TR-009 | SALES_QQ20 | 49955 | 53.6/48.3 | +0.59/-0.02 | 1.000 | 50.8/46.5 | +0.55/+0.07 | 1.000 | 0.51 |
| FND-TR-003 | EY3 | 293343 | 53.3/49.8 | +0.37/-0.07 | 1.000 | 51.1/48.8 | +0.16/-0.10 | 1.000 | 0.44 |
| FND-TR-004 | PS_TOP5 | 4939 | 48.5/48.3 | -1.00/-0.20 | 1.000 | 43.5/43.5 | -0.09/-0.16 | 1.000 | 0.47 |
| FND-TR-006 | PFCF_BAD | 190182 | 49.5/49.1 | -0.18/+0.11 | 1.000 | 46.7/46.6 | +0.08/+0.22 | 1.000 | 0.42 |
| FND-TR-012 | OPM_NEG | 184337 | 49.4/49.8 | +0.11/+0.41 | 1.000 | 46.7/47.3 | +0.33/+0.49 | 1.000 | 0.44 |
| FND-TR-013 | ROE20 | 151815 | 52.1/50.1 | +0.24/+0.02 | 1.000 | 50.4/49.0 | +0.08/-0.06 | 1.000 | 0.38 |
| FND-TR-014 | DE2 | 247973 | 51.8/50.9 | +0.32/+0.26 | 0.000 | 49.5/49.2 | +0.26/+0.23 | 0.000 | 0.42 |
| FND-TR-015 | CR_LT1 | 111055 | 52.3/50.0 | +0.36/+0.05 | 1.000 | 49.7/48.0 | +0.37/+0.04 | 1.000 | 0.41 |
| EVT-NB-009 | EVT_502 | 32328 | 51.8/48.9 | +0.15/-0.12 | 1.000 | 49.1/47.3 | +0.27/-0.05 | 1.000 | 0.28 |
| EVT-NB-010 | EVT_NT_401 | 1216 | 55.8/48.6 | +0.90/+0.44 | 1.000 | 52.0/41.7 | +1.93/+0.15 | 1.000 | 0.28 |
| EVT-NB-011 | EVT_301 | 552 | 60.5/51.8 | +2.46/+0.87 | 1.000 | 51.9/48.2 | +0.78/+0.44 | 1.000 | 0.28 |
| SEC-JA-021 | SECT_TOP3 | 196174 | 51.1/50.4 | +0.04/+0.17 | 1.000 | 49.0/48.3 | +0.10/+0.11 | 1.000 | 0.32 |
| SEC-JA-022 | SECT_BOT3 | 180752 | 51.2/47.8 | +0.18/-0.27 | 1.000 | 48.9/46.7 | +0.06/-0.23 | 1.000 | 0.32 |
| SEC-JA-023 | SECT_RANK_UP5 | 116811 | 49.4/49.3 | +0.01/+0.14 | 1.000 | 47.0/46.5 | +0.15/-0.04 | 1.000 | 0.32 |
| SEC-JA-024 | CYC_DEF_UP | 84469 | 50.5/55.4 | +0.34/+0.65 | 1.000 | 49.8/54.7 | +0.26/+0.58 | 1.000 | 0.32 |
| SEC-JA-033 | SECT_LOWCORR | 161643 | 48.2/47.4 | -0.14/-0.16 | 1.000 | 45.3/45.2 | +0.05/-0.11 | 1.000 | 0.32 |
| PRC-TR-003 | YTD_VS_SECT20 | 109858 | 46.6/50.3 | -0.20/+0.39 | 1.000 | 44.6/48.0 | -0.16/+0.30 | 1.000 | 0.42 |
| CAL-JA-004 | CPI_DAY | 49724 | 47.0/47.2 | +0.00/+0.00 | 1.000 | 42.5/43.7 | +0.00/+0.00 | 1.000 | 0.00 |
| CAL-JA-005 | NFP_DAY | 47187 | 48.1/50.3 | +0.00/+0.00 | 1.000 | 44.9/51.7 | +0.00/+0.00 | 1.000 | 0.00 |
| MKT-JA-060 | CFTC_ES_LEVSHORT | 138997 | 50.6/50.1 | +0.00/+0.00 | 1.000 | 47.8/47.5 | +0.00/+0.00 | 1.000 | 0.00 |

Date-level features (CPI_DAY, NFP_DAY, CFTC_ES_LEVSHORT): excess 0 by construction, p set to 1 (cannot pass), as in wave 1.

## Still open (12)
CAL-JA-038 (Treasury refunding dates not sourced), MKT-JA-059 (NAAIM: no downloadable history), CAP-NB-001/003 (no dated split / split-announcement source <=2024), SUP-NB-009 (no de-SPAC list), BRW-NB-005 (Reg SHO threshold archives not pulled), REL-NB-007/008 (fixed name lists + overnight BTC/futures at 09:25), PV-TF-462..465 (13F holdings not built).

## Caveats (pre-registered)
Market cap uses split-adjusted closes x as-filed share counts (understates names that split later). SIC is current, not point-in-time; sector map covers 49% of rows. Annual figures are last fiscal year, not TTM. 8-K 5.02 includes planned changes. FTD scaled by shares outstanding (no float). 10b5-1 flag not available for insider sells.

## Data and code
FINRA CNMSshvol 2019-09..2024-12; SEC companyfacts and submissions (filed <= 2024-12-31); New Bot SEC shares (Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4); SEC FTD 2019-2024 (144 files); BLS release archives; CFTC TFF 2016-2024. Scripts: unblock/w2/*.py.
