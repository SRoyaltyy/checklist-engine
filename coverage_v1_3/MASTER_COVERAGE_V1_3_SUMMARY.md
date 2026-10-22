# Master list coverage v1.3 (819 ideas; 2020-24 practice only, 2025-26 not read)

Add-only successor to v1.2 (227223e, coverage_v1_2/, unchanged). Built by `build_master_coverage_v1_3.py` from v1.2 csv +
unblock wave 2 (results 57e7676 md / 5b79b21 csv; coverage v3 1232fca; coverage v4 5662076 incl. BRW-NB-005 Reg SHO 8bdeb3c/e942e2f).
Combo model V1 (combo/ af4b70f md, 4f67edc csv) is a model over many answers, not a master id: recorded below, changes no row.

## Totals by status

| status                   |   v1.2 |   v1.3 |   change |
|:-------------------------|-------:|-------:|---------:|
| TESTED                   |    540 |    590 |       50 |
| TOO_FEW_TRADES           |      3 |      3 |        0 |
| NEVER_FIRED              |      0 |      0 |        0 |
| BUILT_NOT_TESTED         |      1 |      0 |       -1 |
| BUILDABLE_FROM_FREE_DATA |     60 |      0 |      -60 |
| STILL_OPEN               |      0 |     11 |       11 |
| BLOCKED                  |    215 |    215 |        0 |

TESTED 590 = 540 (v1.2) + 49 BUILDABLE -> TESTED + PV-TF-159 (BUILT_NOT_TESTED -> TESTED). Wave 2 tested 53 ids, 0 pass
(the other 3 are PV-TF-452/455/458, already TESTED in v1.2, re-tested with the %-of-market-cap version, still FAIL).
Single PASS on the list is still PV-TF-110 (20d return), HINT only (found on 2020-24).
STILL_OPEN 11 = buildable-from-free-data ideas wave 2 did not build; missing data named below. BRW-NB-005 was open in v3 and is TESTED FAIL in v4.

## Change matrix (rows v1.2 status, cols v1.3)

| status_v1_2              |   BLOCKED |   STILL_OPEN |   TESTED |   TOO_FEW_TRADES |   All |
|:-------------------------|----------:|-------------:|---------:|-----------------:|------:|
| BLOCKED                  |       215 |            0 |        0 |                0 |   215 |
| BUILDABLE_FROM_FREE_DATA |         0 |           11 |       49 |                0 |    60 |
| BUILT_NOT_TESTED         |         0 |            0 |        1 |                0 |     1 |
| TESTED                   |         0 |            0 |      540 |                0 |   540 |
| TOO_FEW_TRADES           |         0 |            0 |        0 |                3 |     3 |
| All                      |       215 |           11 |      590 |                3 |   819 |

## Still open (11) - missing data

| id         | data_type        | variant                           | reason                                                                 |
|:-----------|:-----------------|:----------------------------------|:-----------------------------------------------------------------------|
| CAL-JA-038 | Calendar         | Treasury refunding                | missing data: no Treasury refunding-date source pulled (not attempted) |
| MKT-JA-059 | Market-wide      | NAAIM exposure                    | missing data: NAAIM page has no downloadable history                   |
| CAP-NB-001 | Corporate action | Reverse split recent              | missing data: no dated split history source <=2024                     |
| CAP-NB-003 | Corporate action | Forward split announced           | missing data: no split announcement dates                              |
| SUP-NB-009 | Share supply     | De-SPAC age                       | missing data: no de-SPAC completion list                               |
| REL-NB-007 | Crypto proxy     | BTC overnight for crypto equities | missing data: needs fixed crypto-name list + overnight BTC at 09:25    |
| REL-NB-008 | Commodity proxy  | Commodity overnight for producers | missing data: needs producer list + overnight futures at 09:25         |
| PV-TF-462  | 13F              | Holder count change               | missing data: 13F holdings not built                                   |
| PV-TF-463  | 13F              | Inst % of float                   | missing data: 13F holdings not built                                   |
| PV-TF-464  | 13F              | New positions by top-50 filers    | missing data: 13F holdings not built                                   |
| PV-TF-465  | 13F              | Concentration                     | missing data: 13F holdings not built                                   |

## Combo model V1 ("thousands of yes/no questions") - FAIL
11,345 yes/no answers; logistic + small tree; settings picked on 2020-22, frozen before 2023-24. 6 rules, 0 pass
(2023-24 excess +0.05 to +0.36 pts after fees vs same-day average; best BH q 0.36). Mostly market-wide questions = picks days, not stocks.
Combo v2 (no market-wide questions, same-day stock-vs-stock) is pending, not in this version.

## Luck-correction count
**14,069** = 13,851 + 208 wave-2 p-values (14,059) + 4 BRW-NB-005 (14,063) + 6 combo rules (14,069).
