# PATH_BANK v2 — "how it got here" question bank at snapshot scale (FROZEN, built Thu 2026-10-22 HKT, before Fri 21:00 HKT deadline)
Spec + code only. **Nothing scored.** No 2025-26 data read: `assert_practice` refuses any row dated >= 2025-01-01; the loader filters date < 2025-01-01.
v1 (`../path_bank/`, path_bank.py sha 985e4469…, PATH_BANK.csv 5b09a9e6…) is untouched and stays locked as the fallback.

## Size
- **5,716 questions = 5,683 yes/no + 33 fixed-label**, 76 families, lookbacks **3,5,7,10,15,20,25,30,40,50,60** trading days (max 60).
- IDs `ph2_<family>_<lb>_<op><cut>` (op = ge/gt/le/eq; `p`=decimal point, `m`=minus) or `ph2_<family>_<lb>_<label>` / `_label`.
- Per-family counts: see `PATH_BANK_V2.csv` (`family` column) or the report in test_log notes below.

## Rules
- Timing: every feature computed on bar t, then `shift(1)` -> day D sees only bars < D.
- All cutoffs hard-coded in `path_bank_v2.py` (shared grids FR / RATIO / CNT / RET / SLP + per-family lists), written before any outcome look. Never tuned.
  Only structural pruning: count cuts > lb dropped; dsh/dsl cuts >= (lb-1)/lb and recovspd cuts >= lb-1 dropped (always-yes by construction). No data-driven pruning.
- Scoring later: horizons 5/10/20 trading days only; 2020-24 practice/HINT, 2025-26 exam after lock. More questions does NOT loosen the bar: the same
  false-discovery correction covers the whole bank (v1 + v2 + everything else), and the many correlated cuts of one feature count as one family of evidence.
- Many questions are rare by design (e.g. 5 gap-downs >5% in 5 bars). On the 5 test names 2020-24 ~546 yes/no questions never fired and ~990 fired <1% or >99%
  of the time; they are kept (no pruning on data) and will fall out at scoring under the minimum-support rule.

## Families
v1 families, wider grids: upstreak, dnstreak, ddrun, bbup, bbdn, voltrend, rgvol, slope, accel, slopeflip, recov, recovspd, gapup/gapdn at 1/2/5%,
rngexp, dsh, dsl, disth (+ new distl), dipatr, pctbmean, swing (label).
New: hlfrac/hhfrac (share higher lows/highs), hlrun/lhrun (consecutive higher lows / lower highs), abv10/20/50frac, abv20run, abv20now/blw20now
(current streak vs SMA20), MA-cross recency gx/dx 5_20, 10_50, 20_50 and close-vs-SMA20 xc20up/dn (cross happened within lb), nh20/nl20/nh60/nl60
(new-high/low counts), clvmean/clvtrend (close-location value level & slope), volrel, vdry (volume dry-up), vdrymove/vdryup (dry-up then move),
rngcomp/sqzexp (range compression then expansion), nr7cnt, insidecnt, maxdd, ddrecfrac (drawdown recovery fraction), grnfrac, upfrac, seq3
(red/green sequence label, lb=3), upvolfrac, atrtrend, natr, ret, retq (label), rngpos, rngposq (label), maxup1d, maxdn1d, bigvolday,
bodymean, uwickmean, lwickmean. Exact formula of every question is in the `formula` column.

## Test (`python3 path_bank_v2.py --test`, log in test_log.txt) — PASS
AAPL, ALDX, NVDA, CELH, F, 2020-24, 10 random dates each (seed 20261022): history truncated at D, and again with D's own bar poisoned
(O,H x3, L x0.1, C x5, V x50) -> all 5,716 answers identical to the full-history run, 0 mismatches. 2025-01-02 row correctly refused.
NaN after 140-bar warm-up: overall 0.06%; 25 questions >5%, 8 >20% — all ddrecfrac (NaN by design when the window had no >=1% drawdown; worst
ddrecfrac_5 at 20%) plus rgvol_3/5 (no red or no green day in window).

## Overlaps (correlated evidence, not independent)
- cp_*: ph2_ddrun_*_ge0p5 ~ cp_dd_vs_run_ge_0p5; ph2_dipatr_* ~ cp_dip_atr_le_4p2 (cp uses 20d high); ph2_dsh_20_* ~ cp_days_since_h20_in_5_18;
  ph2_rgvol_10_* ~ cp_redgreen_vol10_gt_1; ph2_slope_20_* / abv20frac ~ cp_mid_slope_up; ph2_pctbmean_* ~ cp_pctB_ge_0p12 (cp is point %B);
  ph2_bodymean_20_* ~ cp_gr_body20_ge_0p9 (loosely).
- v1: every v1 family is reproduced in v2 with a superset grid (same definitions; v2 ids use prefix ph2_ and lb 5/10/20/60 overlap v1 directly).
  Small v1 differences: v1 dsh/dsl/disth/dipatr/pctbmean were bins; v2 uses fixed thresholds (same edges included). Treat v1 ∩ v2 as duplicates.
- Taskforce story Qs (STORY_QUESTIONS_V1.md): sq2_higher_lows3 ~ hlrun/hlfrac/swing; sq1_lower_highs3 ~ lhrun/swing LH_*; sq4_below_mid_5of10 ~
  ph2_abv20frac_10_* (sq4 = abv20frac_10 <= 0.5); sq7_lowerbb_reclaim ~ bbdn_10 + xc20up (partial); sq9_breakdown_vol ~ nl20 + bigvolday;
  sq8_above_last_red_high, sq3 (shrinking green bodies), sq5 (big red recent), sq6 (dip volume lower) ~ partly grnfrac/maxdn1d/vdry; no exact duplicate.
