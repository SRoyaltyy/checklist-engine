# 2024 v4: market-wide fresh warnings added (FRESH_MKT_ADDON). EXPLORATORY, survivors only, no 2025–26

Inputs: `chunks/2024__FRESH_MKT_ADDON.parquet` (252 dates, 48 market lenses), joined on date to the per-sector `2024__FRESH__*` files.
- Market fraction = Σ yes / Σ ready over market lenses. Market jump z = trailing 20-day (≥ 10 days of history), ≥ 1.5. 37 of 252 dates qualify.
- Combined stock+market jump = z of (stock yes + market yes) / (stock ready + market ready).
- Same v2/v3 rules: funds excluded, next-open entry, fixed 5-day hold, 0.20% fee, date-clustered CIs, L5 = 2020–24 pooled cut (lean ≥ 0.619).
- Sample differences from v3 2024: Financial is excluded (no 2024 FRESH Financial file), and dividends are not added back (negligible in v3).

## Stock states, 2024 (5-day edge vs same-date average)
| state | edge | 95% CI | dates / obs |
|---|---|---|---|
| L5 all | +0.12% | +0.03 / +0.20 | 246 / 200,848 |
| L5 & stock-only jump (v3 definition) | 0.00% | −0.37 / +0.36 | 223 / 8,348 |
| L5 & combined stock+market jump | +0.17% | −0.23 / +0.57 | 221 / 6,405 |
| L5 & stock jump but not combined jump | −0.26% | −0.77 / +0.25 | 158 / 2,925 |
| L5 & combined jump but not stock jump | +0.38% | −0.48 / +1.24 | 87 / 982 |
| L5 on market-jump dates (judged by dates) | +0.25% | −0.08 / +0.57 | **35 dates** / 13,873 |
| L5 & combined fresh, top third | +0.20% | +0.07 / +0.33 | 245 / 69,061 |
| L5 & combined fresh, bottom third | +0.05% | −0.06 / +0.16 | 241 / 70,837 |

## Market-wide vs IWM (one observation per date, 5-day next-open to next-open, after fee)
| state | n dates | IWM 5d | 95% CI | hit rate |
|---|---|---|---|---|
| all | 246 | +0.12% | −0.27 / +0.52 | 51% |
| market jump z ≥ 1.5 | 35 | **−0.69%** | −1.96 / +0.58 | 51% |
| no market jump | 201 | +0.28% | −0.14 / +0.70 | 52% |
| market fresh, top third | 82 | +0.11% | −0.60 / +0.83 | 55% |
| market fresh, bottom third | 82 | +0.40% | −0.19 / +0.99 | 49% |

## What changed vs before (2024)
- Adding market-wide warnings **does not change the 2024 picture.** In 2024 the "bull + warning spike" state was already flat (v3 2024: +0.08%; here, stock-only: 0.00%). With the market part added it is +0.17%. All CIs cross zero.
- Market warning spikes line up with weaker IWM weeks (−0.69% vs +0.28%), but with 35 dates the CI is wide and crosses zero. It is a hint, not a result.
- Market-wide pieces are identical for every stock on a date, so the effective sample for them is about 35 dates, not 13,873 observations.

## Does the 2020–24 −0.32% spike result need a redo?
**No, it stands as a stock-level result.** `build_y.py` used only stock-scope quiet warnings:
- the COUNTS2 columns filtered on `stk|...|quiet_warning|` (lines 11 and 16);
- the per-sector `FRESH__<sector>` files, which are the stock-only ones Grok says skipped the market lenses.

So the −0.32% (CI −0.50 / −0.13) is a consistent, stock-level-only spike measure in every year, and the FRESH bug does not touch it. What it does **not** answer is whether a combined stock+market spike behaves the same. That would need the 2020–23 MKT_ADDON files, which now exist locally (exploratory only; not run here).
