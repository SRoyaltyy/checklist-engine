# CHART_PICTURE_V2_FORMULAS.md — NEW (v2) formula addendum, chart-picture gate

**STATUS: NEW (v2). THIS IS NOT THE ORIGINAL LOCKED RECIPE.**
The original code (feats.py 687db55f…, feats2.py d54ce721…, match2.py bea4bf15…) and ARQT.csv were lost and never recovered.
These formulas are a fresh written definition, not a reconstruction claimed to equal the originals. v2 is OUT of the Fri 2026-10-23 23:00 HKT lock;
it may be built only after Friday, with its own fingerprints (this file's sha256 + the future v2 code's sha256).

Written 2026-10-22 HKT by Trading Bot Taskforce. Sources read (not edited): state_test/chart_picture/FROZEN_RECIPE_chart_picture.md,
PRELOCK_ADDENDUM_CHART_PICTURE.md, chart_picture_gate.py. Yes/no cutoffs are copied from the gate's HARD_GATES / WARN_GATES unchanged.
Only price data (OHLCV) used to define anything. No outcomes / returns were opened. Nothing tuned on 2020–24 or 2025–26 results.

## 0. Common definitions

- Input: one ticker, daily bars sorted by date, columns `Open, High, Low, Close, Volume` (O,H,L,C,V). Day t = the evaluation day; all windows end at t inclusive. No future bars.
- Window notation: `W(n)` = the n trading days t-n+1 … t.
- Green day: `C > O`. Red day: `C < O`. Doji `C == O`: neither (excluded from green and red sums). Colour is candle colour, NOT close vs prior close.
- Body: `|C - O|`.
- True range: `TR_t = max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)`; first bar TR = H - L.
- ATR14: Wilder smoothing. Seed = simple mean of the first 14 TR; then `ATR_t = (13*ATR_{t-1} + TR_t)/14`.
- Bollinger: period 20 on Close, mid = SMA20(C), sd = population std (ddof=0) of C over W(20), upper = mid + 2*sd, lower = mid - 2*sd.
- 20d high: on **Highs** (not closes): `h20 = max(H over W(20))`. `i_h` = index of that high; ties → the most recent day.
- Swing low before the run: `s_low = min(L)` over the 20 trading days ending the day before `i_h` (i_h-20 … i_h-1).
- Missing data: need ≥ 60 bars of history before t; otherwise every feature = NaN, and the gate treats NaN as a failed HARD gate (same as chart_picture_gate.py "missing").

## 1. The 7 cp_* tags (gate questions) — exact formulas

| Tag | Feature formula | Lookback | Inputs | YES cutoff (from gate) | Role |
|-----|-----------------|----------|--------|------------------------|------|
| cp_mid_slope_up | `slope20 = (mid_t - mid_{t-5}) / mid_{t-5}`; `mid_slope_up = 1 if slope20 > 0 else 0` | BB20 + 5 days | C | `mid_slope_up == 1` | HARD |
| cp_gr_body20 | `gr_body20 = sum(body on green days in W(20)) / sum(body on red days in W(20))`; red sum 0 and green sum >0 → +inf (YES); both 0 → NaN | 20 | O, C | `gr_body20 >= 0.9` | HARD |
| cp_pctB | `pctB = (C_t - lower_t) / (upper_t - lower_t)`; if upper==lower → NaN | 20 | C | `pctB >= 0.12` | HARD |
| cp_dip_atr | `dip_atr = (h20 - C_t) / ATR14_t` | 20 (+ATR14) | H, L, C | `dip_atr <= 4.2` | HARD |
| cp_days_since_h20 | `days_since_h20 = t - i_h` (trading days; 0 = high made today; range 0…19) | 20 | H | `5 <= days_since_h20 <= 18` | HARD |
| cp_dd_vs_run | `run = h20 - s_low`; `dd = h20 - min(L over i_h … t)`; `dd_vs_run = dd / run`; run <= 0 → NaN | up to 40 | H, L | `dd_vs_run >= 0.5` | HARD |
| cp_redgreen_vol10 | `redgreen_vol10 = sum(V on red days in W(10)) / sum(V on green days in W(10))`; green vol 0 → +inf | 10 | O, C, V | `redgreen_vol10 > 1.0` | WARN only (never vetoes alone) |

Not a gate: `lower_highs10 = count of days d in W(10) with H_d < H_{d-1}` (continuous, shape-match feature only; no cutoff, as in the original addendum).

## 2. Same-setup rule (unchanged from the gate)

- vs ARQT ref 2026-10-07: candidate must answer YES on all 6 HARD tags; WARN raised if candidate's redgreen_vol10 answer is YES (ref is NO).
- Pairwise: the 6 HARD answers must be identical; any mismatch or NaN → not the same setup.

## 3. Shape kNN features (for completeness, v2 wording)

25-day window W(25); per day: body = (C-O)/ATR14_t, upper wick = (H - max(O,C))/ATR14_t, lower wick = (min(O,C) - L)/ATR14_t (ATR14 at day t, the evaluation day);
close path z-scored over W(25) (ddof=0); %B path (per-day pctB); log(V_d / SMA50(V)_d) path. Distance = RMS over all elements. 1 match per ticker per calendar month (closest kept).
Universe: C_t >= 5 and SMA20(C*V) > 1,000,000. Knee rule text unchanged from FROZEN_RECIPE (k* chosen by distances only, no returns).

## 4. Rules for building v2

- Code written from this file only; record its sha256 next to this file's sha256. Label every output "chart_picture v2".
- Price file: /workspace/pricehist/universe_2020_survivors.parquet (sha fb9bbe69…). 2025–26 stays sealed until the joint open.
- Unit checks AAPL 2022-09-01 (expect FAIL) and ALDX 2021-11-18 (expect PASS) are price-only sanity checks; if v2 disagrees, record it — do NOT change formulas or cutoffs to force agreement.
- The ARQT reference needs a fresh ARQT daily OHLCV file (the old ARQT.csv is lost, no sha was ever recorded); record its sha when fetched.
