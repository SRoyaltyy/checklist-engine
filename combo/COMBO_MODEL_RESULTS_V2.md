# COMBO_MODEL_V2 — Results (one-shot 2023–24 check)
Run 2026-10-23 (HKT). Rules: combo/COMBO_MODEL_V2.md (3fa5c75), committed before any V2 training. Otherwise identical to V1 (2e37e12 + Addenda A–D).
Frozen model: combo/COMBO_MODEL_V2_frozen.joblib, sha256 c9649aa133f3c4c360108f96906e396f453c3b595c7f92f280a677ae2c1d2d37 (commit 39c0cd6),
committed (and the GitHub copy's sha256 verified) before the 2023–24 check ran. 2025–26 never opened (all reads asserted <= 2024-12-31).

## The two changes vs V1
1. Market-wide questions removed: 3,768 of 11,345 inputs (MAC-/MKT- ids and the SHARED file). Zero-within-date-variance rule removed 0 more. 7,577 inputs kept.
2. Label = beat the same-day mean of filtered stocks (after 30bp each way); LOGIT picks = top 1% / 10% of scores within each date.

## CV picks (fit 2020–21, validate 2022)
- EXIT_RULE_V1: logistic alpha 1e-3, l1_ratio 0.9 (val log-loss 0.747); tree depth 4, min_leaf 300 (val AUC 0.509, i.e. a coin).
  Best leaf: maxdd_60>=0.5% YES, volrel_50>=0.3 NO, natr_50>=0.1 YES, ret_60>=-30% NO (3,124 training rows, 79% beat the day).
- HOLD_10D: logistic alpha 1e-3, l1_ratio 0.9 (log-loss 0.729); tree depth 4, min_leaf 3000 (AUC 0.527).
  Best leaf: BRW-NB-057 YES, natr_40>=4% NO, OPX-NB-073 NO, maxdd_10>=2% NO (5,651 rows, 65% beat the day).
- Logistic 2022 log-loss was worse than a constant guess (0.693) for every setting; the models did not generalise even inside 2020–22.

## Results (after 30bp each way; excess = vs same-day mean of $100M-filtered stocks; BH family 14,075 = 14,069 + 6)
| exit | rule | 2020–22 n | 2020–22 win% | 2020–22 excess% | 2023–24 n | days | 2023–24 win% | beat day% | excess% | 95% CI | p | BH q | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXIT_RULE_V1 | TREE_BEST | 3124 | 84.6 | 6.80 | 181 | 147 | 49.2 | 48.6 | -1.82 | -5.18 to 1.56 | 0.30 | 1.00 | FAIL |
| EXIT_RULE_V1 | LOGIT_TOP1 | 3287 | 57.7 | 2.23 | 10645 | 482 | 51.3 | 49.1 | -0.02 | -0.30 to 0.22 | 0.87 | 1.00 | FAIL |
| EXIT_RULE_V1 | LOGIT_TOP10 | 29818 | 56.7 | 1.68 | 104448 | 482 | 50.5 | 48.8 | -0.07 | -0.20 to 0.08 | 0.32 | 1.00 | FAIL |
| HOLD_10D | TREE_BEST | 5651 | 52.8 | 1.68 | 43364 | 151 | 46.5 | 47.5 | -0.27 | -0.54 to -0.01 | 0.05 | 1.00 | FAIL |
| HOLD_10D | LOGIT_TOP1 | 3287 | 54.2 | 1.92 | 10645 | 482 | 48.6 | 47.5 | -0.00 | -0.22 to 0.22 | 0.97 | 1.00 | FAIL |
| HOLD_10D | LOGIT_TOP10 | 29818 | 53.1 | 1.33 | 104448 | 482 | 48.0 | 47.5 | -0.00 | -0.16 to 0.06 | 0.36 | 1.00 | FAIL |

2020–22 numbers are in-sample (the 295,054 training rows the model was fit on), not a test. Average stock 2023–24: win 48.8% (EXIT_RULE_V1), 47.1% (10-day).
Check population: 1,042,483 rows (16,981 dropped <$100M; 343,722 cap-unknown kept, counted per rule in the csv).

## Verdict: FAIL (0 of 6). With market-day picking removed, nothing is left: every 2023–24 rule is at or below the same-day average stock,
no rule clears 55% wins, and none survives the luck correction. The strong 2020–22 tree leaves were overfit. Cumulative test count now 14,075.
