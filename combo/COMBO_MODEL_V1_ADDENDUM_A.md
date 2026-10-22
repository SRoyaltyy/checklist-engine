# COMBO_MODEL_V1 — Addendum A (War room steering; committed BEFORE any training or outcome join). Overrides V1 where they differ.
Registered 2026-10-23 ~02:30 HKT. Nothing has been trained; only the population keys and feature answers are being built.

1. **Engine answers added + 2023 SHARED order bug guarded.** Inputs now also include the stored engine answers for every map row in
   checklist_brainstorm/engine/universe/chunks, kinds JG (sector npz), NB (parquet+json), TR (npz), SHARED (npz) — the same four kinds
   as the look-alike build (~13,076 ids). Each year's file is read with ITS OWN id list and its own (ticker,date) keys, joined to the
   population explicitly on (ticker,date); per year we assert keys are unique and that the column list is mapped by id name (never
   by position from another year). The 2023 SHARED file (different id order) is therefore read by name. Path bank, nb_tags_v1 and
   halts inputs stay as in V1; the same row in more than one source is collapsed by the exact-duplicate filter.
   Other chunk families (ATTN, BUCKETS7_*, COUNTS*, EARN, NBX, OPT, SI, F4TR, JA_F4*, FRESH, SECADD) are NOT read in V1 (no
   validated reader; listed as not included, not as tested).
2. **No pre-filter to "working" questions.** Every row is kept except broken ones: never YES on the training sample; YES on >= 99% of
   answered training days; no 2020–24 answer; or in James's untested_v2 BUG list (904 never-answered + 265 missing-stored-as-NO).
   (Replaces V1's 0.2%/99.8% share filter.) Missing is missing, never NO: each row enters the model only as a YES indicator
   (YES=1; NO and NOT_READY/missing = 0), so a stored "NO" is never used as evidence; the 265 bug rows are dropped outright.
3. **Not a plain count.** Weighted score = L1/L2 (elastic-net) penalised logistic, fit by sklearn SGDClassifier(loss="log_loss",
   penalty="elasticnet", random_state=7, 5 epochs over the training sample in fixed-order chunks); tree = DecisionTreeClassifier
   (criterion gini, random_state=7). **All settings chosen by time-split CV inside 2020–22 only**: fit on 2020–21 sample rows, score
   2022 sample rows, pick by 2022 log-loss (logistic) / 2022 AUC (tree). Grids fixed now:
   logistic alpha in {1e-5, 1e-4, 1e-3}, l1_ratio in {0.15, 0.5, 0.9}; tree max_depth in {3, 4}, min_samples_leaf in {300, 1000, 3000}.
   Then refit the chosen settings on all 300,000 2020–22 sample rows; freeze. 2023–24 is not touched until the frozen file + sha exist.
   Trade rules (TREE_BEST, LOGIT_TOP1, LOGIT_TOP10) unchanged; thresholds/leaf from the refit on the training sample.
4. **Cumulative test count base = 13,302** (untested_v2 family). New tests 6 -> BH family **13,308** (prior p = 1, conservative).
