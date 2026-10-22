# FIX2023_V1 — rules (written and pushed BEFORE any compute)
Add-only fix. Frozen files (FINDINGS_FREEZE_V1*, untested_v1/*, untested_v2/*) are NOT rewritten.

## Bug 1 — 2023 SHARED row order
`chunks/2023__SHARED.npz` stores the same 8,176 ids as 2020/21/22/24 but in a different order. `build.py` took the id list from the first year only, so in `A_SHARED.npz` every 2023 SHARED answer was read from the wrong column.
Fix: read each year's id list from that year's file and align by id to one fixed order (the 2020 order).

## Bug 2 — missing data stored as NO
The 265 rows (264 columns) marked in untested_v2 as "every sibling bucket of this indicator is zero-YES while answered NO" are treated as MISSING (NR = 0) on every day. This applies to 243 SHARED, 12 TR, 9 NB and 1 MPV columns. The list is in `missing_as_no_rows.csv`.

## Deliverables, in order
1. FIRST: `shared_answers_2020_24.npz` holds the corrected SHARED answers. It has one row per date, `dates` × `ids` (2020 order), and a uint8 code per cell: 0 = NR, 1 = NO, 2 = YES. Bugs 1 and 2 are both applied.
   - `missing_as_no_rows.csv` lists the affected rows.
   - `fixed_answers.py` is a loader. It returns SHARED answers for any (ticker, date) or date list, and it masks the Bug-2 columns of any kind to NR.
   - Pushed before any re-scoring.
2. Re-score with the SAME method, bar, exits, fees and BH as the originals. The only change is that the SHARED block comes from the per-year-ordered answers.
   - Primary re-score uses the Bug-1 fix only, so the delta can be attributed. Rows hit by Bug 2 are flagged.
   - FINDINGS_FREEZE_V1: rerun `analyze.py` (10-day) and `OUTCOME_FILE=EXIT_RULE_V1` `analyze.py` from copies under fix2023_v1/ with a separate TMP. All non-SHARED inputs are symlinked unchanged. Then the `freeze.py` logic is applied, so the global BH family is the same as the original's.
   - untested_v1: rerun `untested_run.py` from a copy with the corrected SHARED block. Same bar and BH family.
   - Report every SHARED-sourced keep/hold that is gained or lost, plus a CSV giving the corrected status of each SHARED row.
3. PV-TF-110 (untested_v2 PASS) is re-checked for any SHARED input. It is a master price/volume row computed from prices, so it is expected to be unaffected; this is verified, not assumed.
4. Tests added: re-scoring replaces earlier tests and adds no new hypotheses, so the BH family total stays at 13,302. This is stated in the results.

Hard rules: no 2025+ data; price sha fb9bbe69…ef337; qa/redundancy/feats.py excluded; secret scan before every push; SRoyaltyy identity. Copies and SHA256SUMS go on Drive in folder 1FL6sQIYJDAq4xbgLq7YSRseIFC6BqE6I.
