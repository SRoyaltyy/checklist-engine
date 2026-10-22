# Master list coverage v1.2 (819 ideas; 2020-24 practice only, 2025-26 not read)

Add-only successor to v1.1 (Drive 1MX9qVHF3Jj6YtMyfzwvoGScT02TDg36L / 1vZWdjHceo_XUhD9u9sy6eFlyFg5SCam-, frozen, not rewritten).
Built by `build_master_coverage_v1_2.py` from: v1.1 csv; `unblock/unblock_coverage_v2.csv` (d2b3dda); `untested_v2/untested_results_v2.csv` (6a791b2, master rows).
nb32_v1 (c7049a4/8ac0ad6; 32 rows, 0 pass: 28 FAIL, 4 too few trades) and nb193_v1 (193 rows: 165 FAIL, 18 too few, 10 never YES) are **map-v5.1 rows, none carries a master id**, so they change no master status (they count toward map/luck-correction totals only).

## Totals by status (v1.1: TESTED 398 / BUILT_NOT_TESTED 87 / BLOCKED 334)

| status                   |   count |
|:-------------------------|--------:|
| TESTED                   |     540 |
| TOO_FEW_TRADES           |       3 |
| NEVER_FIRED              |       0 |
| BUILT_NOT_TESTED         |       1 |
| BUILDABLE_FROM_FREE_DATA |      60 |
| BLOCKED                  |     215 |

TESTED 540 = 398 (v1.1) + 99 unblock wave-1 (all FAIL) + 43 FAIL + 1 PASS from untested_v2. Single PASS: PV-TF-110 (20d return) - HINT only, 2020-24.
NEVER_FIRED: 0 on the master list (the never-YES cases in untested_v2 were missing answers, classed BLOCKED, not never-fired).

## Change matrix (rows v1.1 status, cols v1.2)

| status_v1_1      |   BLOCKED |   BUILDABLE_FROM_FREE_DATA |   BUILT_NOT_TESTED |   TESTED |   TOO_FEW_TRADES |   All |
|:-----------------|----------:|---------------------------:|-------------------:|---------:|-----------------:|------:|
| BLOCKED          |       175 |                         60 |                  0 |       98 |                1 |   334 |
| BUILT_NOT_TESTED |        40 |                          0 |                  1 |       44 |                2 |    87 |
| TESTED           |         0 |                          0 |                  0 |      398 |                0 |   398 |
| All              |       215 |                         60 |                  1 |      540 |                3 |   819 |

- 98 BLOCKED -> TESTED (unblock wave 1, 0 pass; HST-NB-004 was already TESTED via history10y, also re-tested in this wave).
- 1 BLOCKED -> TOO_FEW_TRADES (CAL-JA-032: 0 YES rows under the pre-registered >=1500/week rule).
- 60 BLOCKED -> BUILDABLE_FROM_FREE_DATA: 48 buildable-not-built + 12 timing-rule ideas redefined to pre-09:25 info (not built yet).
- 1 BLOCKED stays BLOCKED but dropped (EVT-NB-005: no dated conference history).
- 87 BUILT_NOT_TESTED: 44 TESTED (43 FAIL, 1 PASS), 2 TOO_FEW_TRADES (PV-TF-230, PV-TF-324), 40 -> BLOCKED (38 no stored answer on any buyable day; 2 missing data coded as NO), 1 still BUILT_NOT_TESTED (PV-TF-159 SMA20 slope; not in untested_v2).

## BUILDABLE_NOW flag (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4)

| id         | data_type    | variant            | status                   | flag                                                                                                                                    |
|:-----------|:-------------|:-------------------|:-------------------------|:----------------------------------------------------------------------------------------------------------------------------------------|
| SUP-NB-004 | Share supply | Share count growth | BUILDABLE_FROM_FREE_DATA | BUILDABLE_NOW (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4)                                                       |
| FND-NB-001 | Size bucket  | Market cap bucket  | BUILDABLE_FROM_FREE_DATA | BUILDABLE_NOW (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4)                                                       |
| PV-TF-452  | Insider      | Net sell value 5d  | TESTED                   | BUILDABLE_NOW (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4); %-of-mktcap version not built (proxy version tested) |
| PV-TF-455  | Insider      | Net sell value 30d | TESTED                   | BUILDABLE_NOW (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4); %-of-mktcap version not built (proxy version tested) |
| PV-TF-458  | Insider      | Net sell value 90d | TESTED                   | BUILDABLE_NOW (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4); %-of-mktcap version not built (proxy version tested) |

## Blocked reasons (215)

| reason                                                                                     |   count |
|:-------------------------------------------------------------------------------------------|--------:|
| no stored answer on any buyable day (answers missing, not a NO)                            |      38 |
| needs analyst estimates/ratings history; no free PIT archive                               |      19 |
| needs Options data not on box point-in-time for 2020-24                                    |      19 |
| needs consensus forecasts; no free dated consensus archive 2020-24                         |      17 |
| no free 2020-24 history (CBOE P/C free series ended 2019; CNN F&G/AAII/GEX/0DTE/stock IV n |      16 |
| needs prose filings or paid index/ETF data; no fixed-label free history                    |      15 |
| needs pre-market quotes; no free 2020-24 pre-market archive                                |      13 |
| engine row present but NR on every 2020-24 setup cell (source has no 2020-24 history)      |      12 |
| free FRED ICE OAS history only from 2023-10-23 (licence cut); no 2020-22 period            |      10 |
| Theme Radar/Finviz snapshots start Aug 2026; live only                                     |       9 |
| short interest history: FINRA SI owned by New Bot/Theme Radar rows; not duplicated         |       8 |
| needs float/holdings history; no free PIT float series                                     |       7 |
| no free dated index-change/lockup announcement archive                                     |       5 |
| no free borrow-fee/utilisation history                                                     |       4 |
| needs After-hours data not on box point-in-time for 2020-24                                |       3 |
| no free fed funds futures / Fedspeak dated history                                         |       2 |
| data bug: all sibling buckets zero-YES while answered NO (missing coded as NO)             |       2 |
| no free dated PDUFA/AdCom archive                                                          |       2 |
| no free dated 2020-24 source found                                                         |       1 |
| needs after-hours prints of industry peers                                                 |       1 |
| needs pre-market quotes (fails 09:25 data)                                                 |       1 |
| needs intraday last-hour bars                                                              |       1 |
| needs intraday VWAP                                                                        |       1 |
| needs LULD halt records                                                                    |       1 |
| all 2020-24 Nasdaq rows are time-not-supplied; AMC unknowable                              |       1 |
| Nasdaq calendar has no revenue/consensus fields                                            |       1 |
| no fixed-label guidance source (Nasdaq has none; prose banned)                             |       1 |
| same as ERN-NB-006                                                                         |       1 |
| DROP: no free dated conference-schedule history; partial knowledge only                    |       1 |
| 'no news' clause needs news text                                                           |       1 |
| needs home-market ADR mapping + intraday FX                                                |       1 |
| all 2020-24 rows time-not-supplied                                                         |       1 |
