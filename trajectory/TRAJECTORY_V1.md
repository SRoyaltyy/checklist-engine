# TRAJECTORY_V1 — "setup over time" test (pre-registered before any trajectory result was computed)
Practice data 2020–24 only. No bar after 2024-12-31 is read. 2025–26 stays sealed.
Inputs:
- The daily checklist score from SCORE_V1 (score/SCORE_V1.md sha 098399e8…c113; score_raw.parquet).
- The same 796 path-bank-v2 items. Every item answer at day D uses only bars before D, because path_bank_v2 shifts features by 1 bar.
- Panel story_q/panel.parquet, survivors-only, minus buyable filter drop_list_v2.
- Exits from EXIT_RULE_V1.

## "Passing"
- PASS(t) = score(t) > 78. That is the SCORE_V1 top-fifth (F5) cutoff, fixed from 2020–22.
- Secondary family, pre-registered because SCORE_V1 ran backwards: FAIL1(t) = score(t) <= -84, the SCORE_V1 bottom-fifth (F1) cutoff. All features and buckets below are repeated for F1 "runs".
- A run is an unbroken sequence of a ticker's trading days with PASS true. Runs are counted on the ticker's own day series.

## Dedup and entry
- Each run gives at most one trade per bucket family. The entry is the open of the first day of the run (D = run day 1).
- Exception, feature (1): the trade enters on the first day the run reaches the bucket's day count (day 1, day 2, or day 5). So a run gives at most one trade per run-length bucket.
- A trade is kept only if D is in the buyable panel and bars D..D+20 exist on or before 2024-12-31.
- No last-day-of-run variant is tested. It is not pre-registered.

## Features at D (all use scores and item answers dated <= D, which are built only from bars before D)
1. RUNLEN, the number of consecutive PASS days counting D. Buckets: R1 = first day; R2 = 2nd day; R5 = 5th day (only runs that reach 5).
2. SLOPE5 = score(D) − score(D−5) and SLOPE10 = score(D) − score(D−10), in ticker trading days. Buckets: terciles (UP / FLAT / DOWN) with cutoffs taken from 2020–22 run-start trades of that family, then frozen for 2023–24.
3. FLIP5, the count of the 796 items that are YES at D and NO at D−5. Buckets: terciles (HI / MID / LO), cut on 2020–22 as above.
   LASTFLIP, from items that flipped NO→YES between D−1 and D: wf1 = winner-leaning flips, lf1 = loser-leaning flips. Buckets: W_LAST (wf1 > lf1), L_LAST (lf1 > wf1), NONE_TIE (equal, including both 0).
4. REPASS: was there any PASS day in the 20 ticker trading days before the run started? (The day just before the run is a non-pass day by definition.) Buckets: REPASS = yes; FRESH = no.

## Stats per bucket and period (discover 2020–22, check 2023–24)
- Exit A (EXIT_RULE_V1): buy at the open of D. Sell at +20% (a gap past the level fills at that day's open). No stop. Otherwise sell at the close of day 15 (day 1 = D).
- Exit B: sell at the close of day 10.
- Fees: 0.6% round trip.
- Reported: n, win%, mean, median, and excess vs ALL. ALL is every buyable stock-day with the same D, the same as SCORE_V1. The excess has a date-clustered bootstrap 95% CI (500 resamples, seed 13).
- Also reported: the baseline row for each family (all run-starts, unbucketed).
- BH q = 0.05, cumulative. The family is every bucket × exit × period p-value here, plus all earlier p-values (exit grid + stacks + score = 6,446 tests).
- What "held" means: excess is significant (q < 0.05) on 2020–22 AND has the same sign with q < 0.05 on 2023–24.

## Caveat (stated in advance)
The data is survivors-only. This flatters near-low and jumpy stocks: a stock that fell apart and was delisted is missing. Any F1-type win is suspect until live post-lock days are in.
