# Methodology

## 1. Questions
- **Snapshot bank (~10,000 yes/no questions):** each asks something about a stock on day D ("is RSI14 < 30?", "is the stock on the Reg SHO list?"). Answers can only be YES, NO or NOT_READY (data missing or too short).
- **Path bank ("how it got here", in progress):** the same yes/no form, but about the route to today over 5/10/20/60-day lookbacks: trend of the middle band, pullback depth in ATR, distance from the 20-day high, volume pattern, the swing-low structure. It was inspired by the ALDX (pass) vs AAPL 2022-09-01 (lookalike fail) case: two charts can look the same today but have got there differently.
- **Macro state:** the same idea applied to market regime (FRED rates, copper/yields, VIX, put/call, CFTC).
- **SEC rule:** only binary or fixed-set structured fields (e.g. Form 4 transaction codes, filing present yes/no). No free text and no LLM reading of filings.

## 2. Point-in-time (PIT) rule
The answer for day D uses only data available before D. Price questions use the last bar before D, at most 7 days old. (The gate's one-off selftest reads D's own bar; the bulk `cp_*` build uses the strict before-D rule.) The Taskforce truncation test (210/210 passed) cuts the history at D and checks the answer doesn't change.

## 3. Scoring
- Forward returns at **5, 10 and 21 trading days**. 21 is the cap, because Cyrus trades at most 1-month horizons.
- Each YES is compared against **matched controls** (similar stocks on the same date), not the raw market.
- **Fees:** 30 bp per side (60 bp round trip) deducted.
- **Pass bar:** win rate > 50% after fees vs controls (Theme Radar packs use >55%), n ≥ 30, and surviving the **Benjamini–Hochberg** false-discovery correction across all questions tested.
- Negative results are kept as **warnings** (a sign to avoid or short), not discarded.

## 4. Practice vs exam
- **2020–24 = practice.** It's open, and you may iterate on it.
- **2025–26 = sealed exam.** It's opened once, only after the **Fri 2026-10-23 23:00 HKT lock** (FRIDAY_LOCK_INDEX v5). Every question, formula, file fingerprint and cutoff is frozen first, so rules can't be tuned after seeing results.

## 5. Chart-picture gate
`chart_picture_pack/gate/chart_picture_gate.py` (sha `2059efb6…`) with `feats.py` (`687db55f…`), `feats2.py` (`d54ce721…`) and `match2.py` (`bea4bf15…`). The selftest must give **AAPL 2022-09-01 = FAIL** (on 4 hard rules: mid_slope_up, gr_body20, pctB, dip_atr) and **ALDX 2021-11-18 = PASS**. The reference case ARQT.csv `e239c454…b9ca` is a copy restored after the wipe and can't be verified against an original. The v2 formulas (drive_docs) are a spare and are not built.

## 6. Caveats
- **Survivors-only universe:** the price file contains stocks that survived to 2020+. That means survivorship bias, and long-side results are likely optimistic.
- The SECADD sector add-on is a known gap.
- Map v4 was lost in the box wipe; use map v5.1.
