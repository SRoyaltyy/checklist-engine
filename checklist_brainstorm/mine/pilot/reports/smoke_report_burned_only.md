# Taskforce pilot — single-question first screen

**Selection tape: dates ≤ 2026-06-30 only. Jul–Oct 2026 is BURNED (report never select).**

- Panel: `/workspace/checklist_brainstorm/mine/pilot/panel/panel_labeled.parquet`
- Cut / source: `seed:50pair_answers_intersect_universe_sessions` / `dumps:engine/out/50pair(+r2)`
- Select rows / burned rows: **0** / **48926**
- Unique keys scored: **7578**
- Train (pre-Jul): — → — (0)
- Test (pre-Jul): — → — (0)
- Fees: 10 bp/side (0.20% RT) on open→next-open
- Clear bar (pre-Jul test): n≥30, win>55%, mean_aft>0
- **Cleared on selection test: 0**

## Top clears (pre-Jul test o2o)

_None cleared on selection tape. Top 15 by mean_aft_test:_

| row_id | owner | n_test | win_test | mean_aft_test | n_burned |
|---|---|---:|---:|---:|---:|
| ANL-TR-00002-BUT-C | theme-radar | 0 | nan% | +nan% | 14 |
| ANL-TR-00050-BUT-C | theme-radar | 0 | nan% | +nan% | 1 |
| ANL-TR-00062-BUT-C | theme-radar | 0 | nan% | +nan% | 1 |
| ANL-TR-00074-BUT-C | theme-radar | 0 | nan% | +nan% | 1 |
| ANL-TR-00133-C | theme-radar | 0 | nan% | +nan% | 10 |
| ANL-TR-00157-C | theme-radar | 0 | nan% | +nan% | 4 |
| ANL-TR-00158-BUT-C | theme-radar | 0 | nan% | +nan% | 1 |
| ANL-TR-00181-C | theme-radar | 0 | nan% | +nan% | 11 |
| ANL-TR-00182-BUT-C | theme-radar | 0 | nan% | +nan% | 10 |
| ANL-TR-00193-C | theme-radar | 0 | nan% | +nan% | 11 |
| ANL-TR-00194-BUT-C | theme-radar | 0 | nan% | +nan% | 10 |
| ANL-TR-00205-C | theme-radar | 0 | nan% | +nan% | 5 |
| ANL-TR-00206-BUT-C | theme-radar | 0 | nan% | +nan% | 3 |
| ANL-TR-00230-BUT-C | theme-radar | 0 | nan% | +nan% | 1 |
| ANL-TR-00254-BUT-C | theme-radar | 0 | nan% | +nan% | 1 |

## Burned window (Jul–Oct 2026) — report only

Columns `n_burned` / `win_burned` / `mean_aft_burned` must **not** drive KEEP/promote.

| row_id | n_burned | win_burned | mean_aft_burned |
|---|---:|---:|---:|
| PV-TFC-1241 | 1 | 100.0% | +2.2153% |
| PV-TFC-0800 | 1 | 100.0% | +2.2153% |
| PV-TFX-00149 | 1 | 100.0% | +2.2153% |
| PV-TFC-6169 | 1 | 100.0% | +2.2153% |
| SEC-JA-300-BUT | 1 | 100.0% | +2.2153% |
| PV-TFC-0200 | 1 | 100.0% | +2.2153% |
| SEC-JA-388 | 1 | 100.0% | +2.2153% |
| nb4-EVT-NB-076-T20-CNT | 1 | 100.0% | +2.2153% |
| PV-TFC-4851 | 1 | 100.0% | +2.2153% |
| SEC-JA-388-BUT | 1 | 100.0% | +2.2153% |

## Stubbed for full walk-forward promote
- Train/pick 2020–24, confirm 2025–mid-2026; **Jul–Oct 2026 burned**.
- Newey–West t ≥ 3.37 after fees; beat RANDOM4 + IWM; Bonferroni.
- Pairs miner next after singles clear on selection tape.

## Files
- `/workspace/checklist_brainstorm/mine/pilot/reports/first_screen_singles.csv`
- `/workspace/checklist_brainstorm/mine/pilot/reports/smoke_report.md`
