# PATH_BANK v1 — "how it got here" question bank (FROZEN before Fri 2026-10-23 23:00 HKT)
Spec + code only. Nothing scored. No 2025-26 data read (`assert_practice` guards; test uses date<2025-01-01).

- 264 questions = 240 yes/no + 24 fixed-label, 21 families x lookbacks 5/10/20/60 trading days. IDs `ph_<family>_<lb>_<cut>`.
- Timing: features computed on bar t then `shift(1)` -> day D sees only bars < D (same as NB chunks / cp_* build).
- Threshold grid is hard-coded in `path_bank.py` (THRESH, LABEL_BINS, SWING), set before any outcome look. No tuning.
- Scoring later: horizons 5, 10, 20 trading days only (Cyrus max hold 1 month), 30bp/side fee bar, 2020-24 = practice/HINT, 2025-26 = exam after lock.
- Families: swing (HH/HL/LH/LL from half-window max/min), upstreak/dnstreak, ddrun (pullback/run), recov + recovspd, dipatr (ATR14 bins),
  bbup/bbdn touches, pctbmean bins, voltrend, rgvol (green/red-day volume), slope, accel, slopeflip, gapup/gapdn (>2%), rngexp (TR ratio vs prior lb),
  dsh/dsl (days since lb high/low as fraction of lb), disth (distance below lb high bins).
- Test: `python3 path_bank.py --test` on AAPL & ALDX 2020-24: 10 random dates each, history truncated at D AND with D's own bar poisoned
  -> all 264 answers identical to full run. PASS (test_log.txt). Warm-up: first ~130 bars NaN by design; residual NaN max 7% (rgvol_5 when no red/green day in window).
- Overlaps with cp_* (not duplicates, different grid/window defs): ph_ddrun_*_ge0p5 ~ cp_dd_vs_run_ge_0p5; ph_dipatr_* ~ cp_dip_atr_le_4p2 (cp uses 20d high, bins differ);
  ph_dsh_20_* ~ cp_days_since_h20_in_5_18; ph_rgvol_10_ge1p0 ~ cp_redgreen_vol10_gt_1 (cp uses red/green by close-vs-prev? check; here C vs O);
  ph_slope_20_gt0 ~ cp_mid_slope_up (cp: SMA20 slope); ph_pctbmean_* ~ cp_pctB_ge_0p12 (cp: point %B, here lb-mean). Treat as correlated, not independent evidence.
- Taskforce's 9 story questions: file not located on the box; overlap check pending.
