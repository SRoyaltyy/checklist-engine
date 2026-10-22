# COMBO_MODEL_V1 — combined checklist model, rules (pre-registered; committed BEFORE any training or outcome join)
Registered 2026-10-23 ~02:40 HKT. Owner: Trading Bot Taskforce. Asked by Cyrus / Manager Bot in War room: one inspectable model that
reads ALL yes/no checklist answers on a buyable stock-day and gives one win chance.
PRACTICE 2020–24 only, survivors-only (win rates read high). No bar after 2024-12-31 is read (filtered on load + asserted).
**2025–26 stays sealed**; the frozen model file is applied to it only at the 23:00 HKT lock, by the lock process, not here.

## Inputs (all answers use only data known before the open of D, i.e. before 09:25 ET)
1. Path bank v2 (map v5.1 price rows): all 5,716 items from checklist_brainstorm/path_bank_v2/path_bank_v2.py, features shifted 1 bar
   (row D uses bars < D). Numeric items -> YES if `feature op cut`; label items (swing/rngposq/retq/seq3) -> YES if label == cut.
2. New Bot nb_tags_v1 (646 map rows, 2-bit packed, bars < D): YES=1; NO or not-ready = 0.
3. Halts (New Bot, 2020–24 only): halt_1d, halt_5d, halt_20d, ludp_5d, news_t123_20d, halt_count_20d binned C1 / C2P. Halts before D only.
   No tag row = 0.
Excluded (stated now): story_q panel columns (r5/r10/r21 are outcome-like; sq/cp rows already in path bank), Theme Radar wire50
(Finviz, no 2020–24 history), history10y yearly fields, trajectory flips, anything blocked/no free 2020–24 data. Yes/no or fixed-label only.
Prices: /workspace/pricehist/universe_2020_survivors.parquet (sha fb9bbe69…ef337, asserted).

## Population and labels (identical to halts/nb193 runs)
Every buyable stock-day in story_q/panel.parquet 2020–2024 minus drop_list_v2, with 21 forward bars <= 2024-12-31. Entry open of D.
Fees 30bp each way (0.6% round trip). Exit A = EXIT_RULE_V1 (+20% target, gap fills at open, no stop, else close day 15).
Exit B = 10-day hold (close of day 10). Excess = return minus same-day mean of all population trades.

## Training (2020–22 ONLY; nothing from 2023–24 used for any choice)
- Training sample: 300,000 stock-days drawn uniformly from 2020–22 population (numpy default_rng(7)).
- Column filter on the training sample only: drop columns with YES share < 0.2% or > 99.8% (never-fires / constant); drop exact
  duplicate columns (keep first in input order).
- Target per exit: y = 1 if net return > 0 (a win after fees). One model pair per exit (A and B).
- Tree: sklearn DecisionTreeClassifier(max_depth=4, min_samples_leaf=300, criterion="gini", random_state=7).
- Weighted score: sklearn LogisticRegression(penalty="l1", C=0.002, solver="saga", max_iter=100, tol=1e-3, random_state=7) on 0/1 answers.
- Hyperparameters above are fixed; no tuning, no re-runs with other settings.

## Trade rules (declared now)
- TREE_BEST: buy stock-days landing in the single tree leaf with the highest training win rate (ties: more training rows).
- LOGIT_TOP1: buy stock-days whose score >= the 99th percentile of training-sample scores (threshold frozen in the model file).
- LOGIT_TOP10: same with the 90th percentile.

## One-shot check on 2023–24 (full buyable population, applied once)
Per exit x rule: n, n_dates, win %, mean, median, excess vs same-day average, date-clustered bootstrap 95% CI of excess (500 draws,
seed 13), p. 2020–22 full-population numbers are reported as in-sample, not a test.
PASS = on 2023–24: n >= 30, win > 55% after fees, excess > 0, and BH q < 0.05.
New tests = 2 exits x 3 rules = 6. BH family cumulative = 10,498 prior (prior p = 1, conservative) + 6 = **10,504**.
If any model uses an earnings/reaction row (ids with ERN-, NB-014, NB-022, NB-023, NB-024, NB-091) among top splits/weights and passes,
it is marked POSSIBLE LOOK-AHEAD (hint only).

## Freeze
Saved model (joblib: column list, tree, logistic, thresholds, leaf id) + sha256 committed to combo/ and copied to Drive
checklist_engine_chunks. Freeze target 20:00 HKT 2026-10-23. Nothing passes as a "keep"; any pass is a hint for the 2025–26 test.
