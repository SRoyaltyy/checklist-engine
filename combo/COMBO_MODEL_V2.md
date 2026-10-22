# COMBO_MODEL_V2 — pre-registered rules (second and final try; committed before any V2 training)
Registered 2026-10-23 ~04:15 HKT. Everything is as COMBO_MODEL_V1 + Addenda A–D (same population, $100M filter on population and benchmark,
drop_list_v2, survivors-only, fix2023_v1 answers with the 264 missing-as-NO columns excluded, broken rows dropped, DIL-NB-051 blocked,
YES indicators only, 300k 2020–22 draw then filtered (295,054 rows), 30bp each way, exits EXIT_RULE_V1 and HOLD_10D, settings grids and
2020–21 -> 2022 CV, 2025–26 never opened), EXCEPT the two changes below.

1. **No market-wide questions.** An input is removed if (a) its id starts with MAC- or MKT-, or comes from the SHARED (market-wide) answers file,
   or (b) it has zero within-date variance in the 2020–22 training rows: on every training date with >=2 rows, all rows give the same answer.
   Rule applied mechanically before any fitting; the removed count is reported.
2. **Stocks judged only against same-day stocks.** Label = 1 if the stock's after-fee return minus the same-date mean of the filtered rows
   (training: same-date mean of the 295,054 filtered training rows; check: same-date mean of all filtered 2023–24 rows) is > 0.
   Trade rules: LOGIT_TOP1 / LOGIT_TOP10 = the top 1% / 10% of logistic scores WITHIN EACH DATE (ceil, at least 1 per date);
   TREE_BEST = the leaf with the highest training share of label 1.
   Pass (unchanged bar): n >= 30, win > 55% after fees, within-date excess > 0, BH q < 0.05 (date-clustered bootstrap, 500 draws, seed 13).
   Also reported: share of picks beating their same-day mean.
3. **Fitting (pre-registered this time):** elastic-net logistic by SGD partial_fit (6 epochs, 20k-row batches, seed 7), grid alpha {1e-5,1e-4,1e-3}
   x l1_ratio {0.15,0.5,0.9}, picked by 2022 log-loss; exact greedy Gini tree on 0/1 inputs, depth {3,4} x min_leaf {300,1000,3000}, picked by 2022 AUC;
   refit on all training rows; model frozen and committed with sha256 before the single 2023–24 check.
4. Tests: 6 (2 exits x 3 rules). Luck-correction base 14,069 -> family 14,075.
