# UNBLOCK_RESULTS_BRW005 — Reg SHO threshold list (Nasdaq), 2020-24
Pre-reg: UNBLOCK_V2_ADDENDUM3.md (33c3d57). Input sha256 d5032717...3045 verified. No 2025-26 data opened.

**Result: FAIL (0 of 1). Wave-2 total stays 0 of 53.** BH family n = 14,063.

| period | trades | dates | A win % | A mean % | A excess pts | A q | B win % | B mean % | B excess pts | B q |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020-22 | 1,381 | 582 | 53.4 | -0.32 | -0.98 | 1.0 | 42.9 | +1.66 | +1.15 | 1.0 |
| 2023-24 | 1,147 | 385 | 43.8 | -4.59 | -5.12 | <0.001 | 30.3 | -6.80 | -6.97 | <0.001 |

Population 2,369,374 stock-days after the $100M filter; REGSHO_TH known (Nasdaq) on 33% of rows: YES 2,528, NO 779,814, unknown 1,587,032.
Being on the D-1 threshold list is not a long signal; in 2023-24 it is a strongly significant negative (as a long entry). Shorting is out of scope.

Caveats: Nasdaq membership uses SEC's current exchange file plus earlier list appearances (not point-in-time); NYSE/other names are unknown, not NO. Survivors universe only.
Code: unblock/w2/w2_brw005.py. Coverage: unblock_coverage_v4.csv = v3 plus one appended BRW-NB-005 row (the v3 row is kept unchanged).
