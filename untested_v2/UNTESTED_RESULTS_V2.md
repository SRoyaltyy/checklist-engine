# UNTESTED_RESULTS_V2 (frozen 2026-10-23 HKT)
Rules: UNTESTED_V2_RULES.md (commit 915eead). Universe: 2,408,833 buyable stock-days 2020-03-31..2024-12-02 (4,205 tickers, after drop_list_v2). Price sha fb9bbe69...ef337. No 2025+ data. qa/redundancy/feats.py excluded.
Rows: 1,660 (v1 TOO_RARE). Distinct columns tested: 1,621. BH family = 10,060 + 2x1,621 = **13,302** (conservative: every column counted, including non-firing ones).

## Counts
| status           |   map |   master |   All |
|:-----------------|------:|---------:|------:|
| BUG              |  1129 |       40 |  1169 |
| FAIL             |   328 |       43 |   371 |
| GENUINELY_RARE   |    36 |        0 |    36 |
| PASS             |     0 |        1 |     1 |
| TOO_RARE_TO_TEST |    81 |        2 |    83 |
| All              |  1574 |       86 |  1660 |

Summary: PASS 1, FAIL 371, TOO_RARE_TO_TEST 83, BUG 1,169 (904 NR everywhere -> should be BLOCKED; 265 all-sibling-zero-YES while answered NO -> missing data coded as NO), GENUINELY_RARE 36.

## Passing row (HINT; SURVIVORS-ONLY; mcap floor not applied)
PV-TF-110 'Price return: 20d return' (master).
- EXIT_RULE_V1: discovery 2020-22 n=13,879 win 57.45% mean +2.06% excess +0.80pp p=0.0002 q=0.034; confirm 2023-24 n=8,007 win 56.76% mean +1.79% excess +0.24pp p=0.35.
- 10-day: discovery win 55.41% excess +0.92pp q=0.0007; confirm win 55.94% excess +0.64pp p=0.022.
- Caveat: confirm excess under EXIT_RULE_V1 is small and not significant on its own.

## Bug findings
1. **SHARED id-order bug (affects earlier frozen results):** the 2023 SHARED chunk stores its 8,176 ids in a different order than 2020/21/22/24 (all 8,176 positions differ; same set). The look-alike build (tmp_laf/A_SHARED.npz, build.py attaches SHARED ids from the first year without an equality check) therefore read 2023 SHARED answers from the wrong columns. This is why 866 SHARED rows looked 'answered on 31,212 cells' in v1 yet are NR on every day when read per-file. Every SHARED-sourced result in FINDINGS_FREEZE_V1 and UNTESTED_V1 has misaligned 2023 (confirm-period) answers. Frozen files not rewritten; needs a re-run decision. v2 reads ids per file and is not affected.
2. 904 rows NR on every buyable day -> definitions never computed by engine; should be BLOCKED.
3. 265 rows: all sibling buckets of the same indicator zero-YES while NO is stored -> missing input coded as NO.
4. MPV rows use the current Finviz sector map (not point-in-time).
