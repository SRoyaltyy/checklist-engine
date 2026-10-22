# FIX2023_RESULTS_V1 — 2023 SHARED row-order fix + missing-as-NO fix (frozen 2026-10-23 HKT, add-only)
Rules: FIX2023_V1_RULES.md (commit b119328, pushed before compute). Frozen files untouched. No 2025+ data. Price sha fb9bbe69…ef337. feats.py excluded.

## Corrected answers file (for Taskforce combined model and re-runs)
- `fix2023_v1/shared_answers_2020_24.npz`: A uint8 [1,258 dates x 8,176 SHARED ids], `dates` 2020-01-02..2024-12-31, `ids` in the 2020 order, codes 0=NR/1=NO/2=YES. Per-year id order fixed. The 242 SHARED missing-as-NO columns are set to NR.
- `fix2023_v1/fixed_answers.py`: loader. `shared()`, `shared_for(ticker/date df)`, and `mask_missing(A, ids)`, which sets the 264 missing-as-NO columns of any kind (242 SHARED, 12 TR, 9 NB, 1 MPV) to NR.
- `fix2023_v1/missing_as_no_rows.csv`: the 265 affected rows.
- Check: the old and fixed A_SHARED are identical for 2020/21/22/24 (0 differing cells) and differ on 118,998,711 cells in 2023.

## What changed
- **FINDINGS_FREEZE_V1: nothing changed. No keep or hold was gained or lost.** Look-alike pairs are same-date (25,128 10-day pairs and 25,745 exit-v1 pairs, all with date gap 0). A market-wide SHARED answer is therefore identical for the winner and the loser, so SHARED items never differ, never reach n>=30, and are not in the honesty split or the freeze (0 SHARED rows in FINDINGS_FREEZE_V1.csv and in both honesty_split files). Verified with both the old and the corrected A_SHARED: 0 differing winner/loser cells. Discovery (2020-22) is untouched by a 2023-only bug, so the BH family is unchanged. The full analyze.py re-run was OOM-killed by other jobs on the box; it is not needed, because the verification above is exact.
- **untested_v1:** re-run with the corrected block (`rescore/untested_results_v1_fix2023.csv`). PASS stays 0 and the same 8 rows FAIL with identical numbers (none of them are SHARED). 904 SHARED rows move from TOO_FEW to NOT_COMPUTABLE: their only "answers" were misaligned 2023 values, and read correctly they are NR on every cell. 353 SHARED rows stay TOO_FEW.
- **untested_v2:** already read ids per file, so it is unaffected (the 904 rows already carried the label "BUG: NR everywhere").
- **PV-TF-110** (untested_v2 PASS): a master price/volume row ("20d return is lowest of trailing 252 days") computed from prices only by master_pv, with no SHARED input. Unaffected, so the PASS stands. Note that it is a near-low item, so survivor-bias risk applies.

## Per-row status
`shared_rows_corrected_status.csv`: 1,257 SHARED rows from untested_v1, with the v1 status, fixed status, changed flag, Bug-2 flag, fixed trade counts and the freeze note.

## Tests added
0. Re-scoring replaces earlier tests and adds no new hypotheses. The BH running total stays at 13,302.
