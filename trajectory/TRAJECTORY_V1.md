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

## v1.1 addendum (add-only; written 2026-10-23 ~01:40 HKT, before any trajectory result was computed)
### 5. DIVERGENCE: the non-price checklist builds while the price stays put
- **Non-price yes-count.** np_yes(t) = the number of the 796 items answered YES at t, counting only items tagged non-price. The full per-item tag list is in trajectory/item_price_tags.csv: 169 non-price, 627 price.
  - Non-price families: natr, atrtrend, rngcomp, rngexp, sqzexp, insidecnt, bodymean, uwickmean (range/volatility/candle shape, no direction); bigvolday, vdry, volrel, voltrend (volume).
  - Excluded as price-direction: ret, retq, slope, accel, upfrac, upstreak, hhfrac, abv*/blw*, xc20*, disth/distl, dsl, nl20/nl60, maxdd, ddrecfrac, maxup1d/maxdn1d, gap*, clvmean, pctbmean, bbup, upvolfrac, rgvol.
  - No options, short-interest, insider or earnings binary items exist in the computed bank, so none are included.
- **Windows.** k = 3, 5, 10.
  - NPUP_k = np_yes(D) − np_yes(D−k) >= 2.
  - ret_k = close(D−1) / close(D−1−k) − 1.
  - ADR20 = mean over the 20 bars ending D−1 of (high − low) / close.
  - Price: FLAT if |ret_k| < ADR20; UP if ret_k >= ADR20; DOWN if ret_k <= −ADR20.
- **Buckets per k** (entries = run starts, families F5 and F1, as above):
  - DIV{k} = NPUP_k & FLAT.
  - DIV{k}_PDOWN = NPUP_k & DOWN.
  - CTRL{k}_PUP = NPUP_k & UP. This is the control: same score rise, but price up.
  - CTRL{k}_NORISE = np_yes(D) − np_yes(D−k) <= 0 and np_yes(D) >= the median np_yes(D) of 2020–22 DIV{k} trades in that family (frozen). This is the control: same level, no rise.
- **Continuous version (k = 5).** dv = pct(np_yes change over 5) − pct(ret_5). Percentiles are taken against the 2020–22 run-start distribution of that family, then frozen. Bucket DIVC_TOP = top fifth of dv (cutoff = 2020–22 80th percentile). Also reported: DIVC_REST.
- Same dedup, discover 2020–22, check 2023–24, cumulative BH, and both exits.

### 6. Sign source for flips
- LASTFLIP and FLIP5 use only signs in James's FINDINGS_FREEZE_V1 (commit 3502460, csv sha a8819d1f…e66f) with found_on = 2020-22.
- All 1,503 rows have found_on 2020-22. The 796 computed items are a subset, so the definitions above already satisfy this restriction.
- The 311 sheet/master/grid items remain uncomputed, as in SCORE_V1.
