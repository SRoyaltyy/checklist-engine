# Master list coverage v1.4 (819 ideas; 2020-24 practice only, 2025-26 not read)

Add-only successor to v1.3 (06490a8, coverage_v1_3/, unchanged). Built by `build_master_coverage_v1_4.py` from the v1.3 csv.
No row changes status. Only additions: combo v2 FAIL record and luck-correction count 14,075.

## Totals by status (unchanged from v1.3)

| status         | v1.3 | v1.4 | change |
|:---------------|-----:|-----:|-------:|
| TESTED         |  590 |  590 |      0 |
| TOO_FEW_TRADES |    3 |    3 |      0 |
| STILL_OPEN     |   11 |   11 |      0 |
| BLOCKED        |  215 |  215 |      0 |
| All            |  819 |  819 |      0 |

Single PASS on the list is still PV-TF-110 (20d return), HINT only (found on 2020-24).
Still-open 11 and their missing data: see coverage_v1_3 summary (unchanged).

## Combo models ("thousands of yes/no questions") - both FAIL; models over many answers, not master ids

| model | commits | result |
|:--|:--|:--|
| Combo V1 | 2e37e12 / af4b70f (md) / 4f67edc (csv) | FAIL: 6 rules, 0 pass; mostly market-wide questions = picks days, not stocks |
| Combo v2 | rules 3fa5c75 (sha 015ab011...), frozen model 39c0cd6, results 02310d9 (md) / dadf83c (csv) | FAIL: 0 of 6 pass |

Combo v2 changes vs V1: dropped 3,768 market-wide questions (7,577 stock-level remain); each stock judged only against other stocks on the same day.
Rules committed first; model frozen before the 2023-24 check.
- No rule reached 55% wins in 2023-24. Best: 51.3% on 10,645 trades, -0.02% vs the average stock.
- Tree: 84.6% in 2020-22 fell to 49.2% in 2023-24 (overfit).
- All BH q = 1.0. 2025-26 never opened.
- Drive: md 1P4vANhlXXo6bsi1MqvnJogfjQqIa77Ex, csv 1pDI28TJ1U-fxVF6Jwf4Aka9v33wIEKic.

Plainly: once the model can't win by picking good market days, nothing is left.

## Luck-correction count
**14,075** = 14,069 (v1.3) + 6 combo v2 rules.
