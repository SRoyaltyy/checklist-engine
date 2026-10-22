# PRELOCK ADDENDUM: chart-picture / story-question core (for the joint lock Fri 2026-10-23 23:00 HKT)

Written 2026-10-22 ~18:10 HKT by Trading Bot Taskforce. Separate from PRELOCK_2025_26.md and the other PRELOCK_ADDENDUM_*.md files, which are left unchanged. No 2025–26 data was opened or scored. Recipe text is copied **verbatim** from the frozen source; do not edit it.

## Purpose (plain)

Two stock-days count as the **same setup** only if their **chart-picture core** (story answers) match first. Only then may other checklist / yes-no answers be compared. Matching on lots of small one-day questions must never override a chart that looks different (the ARQT-vs-AAPL bug).

Hard rule: **ANY core gate mismatch → not the same setup**, no matter how many other questions match.

## Source of truth (do not edit)

| File | sha256 |
|------|--------|
| FROZEN_RECIPE.md | bf8a2d79001cef5476d8caa9d13a87bc3dcb1ce81ec9f9b8b5d2d4c2fa304ef6 |
| match2.py | bea4bf150b64d9789c6713f18d3a3b435fb99e04b9b6cee0daafb0b0ac9169f9 |
| feats.py | 687db55fbcc3174be32ca18c5e825e26283e7eca4d393b0690f2fa2ab369c5bf |
| feats2.py | d54ce7219c6c5bb7ff30e02e0538f93d06d3f5710ec72a2626cb74dfe0c6f2f5 |

Self-contained copies live under `state_test/chart_picture/` (same shas). Original: `/workspace/state_test/case_arqt/`.

Gate checker: `state_test/prelock/chart_picture_gate.py` (sha recorded at end of this file after write).

## Frozen recipe (verbatim copy of FROZEN_RECIPE.md)

```
# Frozen matching recipe (written before reading any forward outcome of match2.py run)
Frozen: 2026-10-22 17:38 HKT. Data: 2020-24 survivors only; no 2025-26 aggregates.
Reference: ARQT 2026-10-07. Code: match2.py, feats.py, feats2.py (shas below).
Universe: close>=5, dollar vol>1M/day.
A) Tight feature match: tolerances in match2.py `tol` (17 features).
B) Shape kNN: 25-day window; per-day body/upper wick/lower wick in ATR14 units, close path z-scored, %B path, log(vol/50d avg) path; RMS distance; 1 per ticker per month.
   Common-sense gate CS: body g:r20>=0.9, BB-mid slope up, dip<=4.2 ATR, %B>=0.12, dd_vs_run>=0.5, 5<=days since 20d high<=18.
Knee rule (similarity/n only, no returns): k* = largest k in {200,300,400,500} with dist_cutoff(k) <= 0.6 x median prefilter distance (typical random pair) AND dist_cutoff(k) <= 1.15 x dist_cutoff(100). If none, k*=200 and flag "few true twins".
Eyeball check judges chart resemblance only.
bea4bf150b64d9789c6713f18d3a3b435fb99e04b9b6cee0daafb0b0ac9169f9  match2.py
687db55fbcc3174be32ca18c5e825e26283e7eca4d393b0690f2fa2ab369c5bf  feats.py
d54ce7219c6c5bb7ff30e02e0538f93d06d3f5710ec72a2626cb74dfe0c6f2f5  feats2.py
Knee applied: k*=200 (cutoff 0.486 <= 0.488=0.6x0.814; k=300 cutoff 0.495 fails).
```

## Story yes/no gates (binary / fixed-label only)

These are the chart-picture core. Answers are YES or NO only (Cyrus data rule). Derived from the frozen CS line above; thresholds are not retuned.

| # | Gate (question) | YES when | Role |
|---|-----------------|----------|------|
| 1 | BB middle slope up? | `mid_slope_up == 1` (i.e. `slope20 > 0`) | HARD |
| 2 | body green:red 20d >= 0.9? | `gr_body20 >= 0.9` | HARD |
| 3 | %B >= 0.12? | `pctB >= 0.12` | HARD |
| 4 | dip <= 4.2 ATR? | `dip_atr <= 4.2` | HARD |
| 5 | days since 20d high in [5,18]? | `5 <= days_since_h20 <= 18` | HARD |
| 6 | dip vs prior run deep enough? | `dd_vs_run >= 0.5` | HARD (frozen CS) |
| 7 | red/green volume 10d > 1.0? | `redgreen_vol10 > 1.0` | **WARN only** (side tell; does not alone veto) |

### lower_highs10 — not a binary gate

Frozen CS does **not** include a lower-highs cutoff. `lower_highs10` stays a **continuous** feature for shape kNN / tight feature match only. Do not invent an N for Friday's lock. (Tight `tol` band was 5–9; that is feature-match only, not CS.)

### Same-setup rule

- **Vs ARQT ref (2026-10-07):** candidate must answer YES on HARD gates 1–6 (same answers ARQT gives). Gate 7 WARN if candidate YES (ARQT was ~1.0 → NO).
- **Two arbitrary stock-days:** HARD gate answers (1–6) must be identical on both days; any mismatch → not same setup.
- After the core passes, other checklist answers may be compared. Equal weight across all questions without this gate is the old bug.

## Knee rule and k* (frozen, no edit)

As written in the recipe: k*=200 (cutoff 0.486 ≤ 0.488 = 0.6×0.814; k=300 cutoff 0.495 fails). Shape kNN + CS gate + 1 per ticker per month. Survivors only, close≥$5, dollar vol>$1M/day. 2020–24 only for any training / hint work.

## HINT label (2020–24 ARQT twins) — not a pass

The 2020–24 ARQT twin outcome numbers (e.g. ~6.5% ≥+20%, ~40% fell, median ~+2% after fees at k*=200) were computed **after** AAPL was seen to fail and after the recipe was written. They are a **HINT only**, not a pass/fail claim and not evidence of edge. Reference table (features + paths, clearly labelled): `state_test/chart_picture/twins_table_HINT_only.csv`.

## First sealed test

**2025–26 confirmation is the first real / sealed test.** Do not open, peek, or score 2025–26 outcomes until the joint open at **Fri 2026-10-23 23:00 HKT**. Sealed buy/sell files are never rewritten (N/A for this addendum).

## Unit checks (2020–24 survivors only; no 2025–26)

Run: `python3 state_test/prelock/chart_picture_gate.py --selftest`

| Case | Expected |
|------|----------|
| AAPL 2022-09-01 vs ARQT 2026-10-07 | **FAIL** (mid_slope_up, gr_body20, pctB, dip_atr) |
| ALDX 2021-11-18 (shape_knn CS twin) vs ARQT | **PASS** hard gates (redgreen WARN) |

## Pins

- Price: `/workspace/pricehist/universe_2020_survivors.parquet` (2020–24 only in gate selftest; never point at sealed 2025–26 tars)
- ARQT daily: `/workspace/state_test/case_arqt/ARQT.csv` (ref date 2026-10-07)
- Pack: `state_test/chart_picture/`
- Gate: `state_test/prelock/chart_picture_gate.py` — sha256 below (filled after write)


## Gate checker sha (this write)

- state_test/prelock/chart_picture_gate.py: 2059efb613c62fe178c5f91c6ddbc9c7d49fc6651db86e126f5cf3c9a2c774e8
- This addendum sha256 (after this line is appended, recompute): see SHA256SUMS in chart_picture/
