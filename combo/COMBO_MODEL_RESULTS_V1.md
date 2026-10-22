# COMBO_MODEL_V1 — Results (one-shot 2023–24 check)
Run 2026-10-23 (HKT). Rules: COMBO_MODEL_V1.md (2e37e12) + Addenda A (1270def), B (7d3c635), C (ac5d53a), D (c011f17), all committed before any training/outcome.
Frozen model: combo/COMBO_MODEL_V1_frozen.joblib, sha256 21d16f36e2639e23460177c877fd682e20c0fc1ea23a244485cf84f6c93edd6d (commit 9377368), committed before the check was run.
2025–26 never opened (all reads asserted <= 2024-12-31).

## Data
- Survivors-only panel minus drop_list_v2; $100M filter (latest SEC shares filed before D x prior close). Train: 295,054 of the 300,000 draw (4,946 dropped <$100M; 101,049 cap-unknown kept).
  Check: 1,042,483 rows (16,981 dropped; 343,722 cap-unknown kept). Benchmark (excess) = same-day mean of the FILTERED population.
- Inputs: 11,345 YES indicators after removing broken rows (path bank 5,111; NB tags v2 incl. CAC/DIL rows 338; halts 7; engine JG/NB/TR/SHARED 5,889).
  SHARED from James fix2023_v1 npz (853312d4…c283); 264 missing-as-NO cols excluded; untested_v2 BUG rows excluded; DIL-NB-051 blocked.
- Implementation note: the box ran out of memory on a sparse build, so the elastic-net logistic was fit with SGD partial_fit (6 epochs, 20k batches) and the tree with an
  exact greedy Gini splitter on 0/1 inputs (same as CART). Grids, CV split and selection rules unchanged.

## CV picks (fit 2020–21, validate 2022)
- EXIT_RULE_V1: logistic alpha 1e-3, l1_ratio 0.9 (val log-loss 0.696); tree depth 3, min_leaf 3000 (val AUC 0.547).
- HOLD_10D: logistic alpha 1e-3, l1_ratio 0.9 (log-loss 0.797); tree depth 4, min_leaf 3000 (AUC 0.550). Both are weak: barely better than a coin on 2022.
- ~3,200 non-zero weights per model. Top weights (both exits): PB maxdd_60>=2% (+), FV-GB-2410 (+), FV-GB-2261 (−), FV-GB-2346 (−), MAC-JA-2305 (−), FV-GB-2210 (+).
- Top tree splits: MAC-JA-191, MKT-JA-353, PB natr_60/20>=1%, MKT-JA-152 / MKT-JA-666, MAC-JA-2509, FV-GB-2350. These are mostly MARKET-WIDE (per-date) questions,
  so the "best leaf" is really a choice of market days, not stocks.
- Look-ahead flags: no earnings/reaction or CAC dividend rows among top splits/weights (none flagged). 35 used inputs never say YES in 2023–24.

## 2023–24 (once). Pass = n>=30, win>55%, after 30bp each way, excess>0, BH q<0.05 (family 13,857 = 13,851 + 6)
| exit | rule | n | days | win% | mean% | excess% | 95% CI (date-clustered) | p | BH q | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| EXIT_RULE_V1 | TREE_BEST | 197499 | 98 | 53.0 | 0.89 | 0.07 | 0.04 to 0.10 | 0.0000 | 0.36 | FAIL |
| EXIT_RULE_V1 | LOGIT_TOP1 | 11947 | 76 | 59.1 | 1.05 | 0.36 | -0.01 to 0.85 | 0.0946 | 1.00 | FAIL |
| EXIT_RULE_V1 | LOGIT_TOP10 | 76158 | 254 | 55.7 | 0.67 | 0.19 | 0.10 to 0.28 | 0.0001 | 0.36 | FAIL |
| HOLD_10D | TREE_BEST | 124211 | 59 | 57.0 | 1.16 | 0.07 | 0.03 to 0.11 | 0.0002 | 0.91 | FAIL |
| HOLD_10D | LOGIT_TOP1 | 578 | 25 | 62.1 | 1.02 | -1.61 | -3.79 to 0.10 | 0.1349 | 1.00 | FAIL |
| HOLD_10D | LOGIT_TOP10 | 55309 | 142 | 58.3 | 1.14 | 0.05 | -0.08 to 0.17 | 0.4809 | 1.00 | FAIL |

Average stock in 2023–24: win 48.8% (EXIT_RULE_V1), 47.1% (10-day).

## Verdict: FAIL (0 of 6). Several rules clear 55% wins, but excess over the average stock is tiny (+0.05 to +0.36%) and
nothing survives the luck correction. The wins come from picking market days (only 25–254 distinct days), not from picking stocks.
Cumulative test count now 13,857.
