# WIRE50 MCAP100 results V1 (2020-24 only, survivors-only universe; 2025-26 not opened)
Rule: ../MCAP100_ADDENDUM_V1.md (017f99b), committed before this run. Cleaning = Taskforce a9a1d2aa rule. Scorer: wire50_mcap100_score.py (copy of frozen wire50_score.py + filter). Frozen V1 files untouched.

Share counts: 139,348 SEC filing rows, 787 removed as impossible. Of 8,768,826 universe stock-days (2020-24), 4,466,966 (51%) have no PIT count and 479,543 have a known mcap < $100M.

Check: variant NONE (no filter) reproduces WIRE50_RESULTS_V1.csv exactly (max win% diff 0.00).

| version | passes | E1 trades 2020-22 | E1 trades 2023-24 | removed vs V1 (E1) |
|---|---|---|---|---|
| V1 unfiltered | 0/110 | 881,681 | 699,588 | – |
| MAIN (keep no-count, drop known <$100M) | **0/110** | 875,363 | 693,852 | 12,054 (0.8%) |
| WARNING (also drop no-count) | **0/110** | 726,474 | 580,083 | 274,712 (17.5%) |
(OWN-TR-00830-BUT-C still never fires: 2 tests fail automatically; CSVs hold the other 108.)

Notable: still the only row with any slice >55% is tr-attn-10-LOUD10K. MAIN E1: 2020-22 52.5% (402, excess -0.07%), 2023-24 60.4% (308, +1.25%). WARNING E1: 51.7% (331, -0.02%) / 63.4% (216, +1.71%); E2 59.3% in 2023-24. Discovery still fails in every version, so no pass. Max win% shift per test vs V1: MAIN 0.5 pt, WARNING 3.4 pt.

Casebook (theme-radar PR #17, F4TR, 2,154 buyable cases): MAIN 2,132 (-22), WARNING 1,499 (-655). Summary in casebook_summary_MCAP100_V1.csv. Win rates stay ~47-50% in every split/exit; no split reaches 55%.
