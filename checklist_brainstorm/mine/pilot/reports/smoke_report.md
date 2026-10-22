# Taskforce pilot — YES-only singles first screen (Grok preburn)

**Source:** `engine/out/pilot_matrix/preburn/panel_yesno_preburn_james_grok.parquet`
**Selection tape:** 2024 train dates (pre-Jul; Jul–Oct 2026 burned — not used here).
**YES only.** Primary label `ret_open_next_open`; fees 10 bp/side (0.20% RT).

- Tickers: **2** `AAPL, NVDA` (expanding; AAPL×60 + NVDA×20 so far)
- Sessions: **60** (2024-01-02 → 2024-12-24)
- YES rows labeled: **32,084** | unique row_ids: **3825**
- Train: 2024-01-02 → 2024-06-26 (30)
- Test: 2024-07-03 → 2024-12-24 (30)
- Clear bar (test): n≥30, win>55%, mean_aft>0
- **Cleared on test (o2o): 0**

## Clears (test open→next open)

_None cleared._

## Top non-clears by mean_aft_test

| row_id | owner | n_test | win_test | mean_aft_test | why |
|---|---|---:|---:|---:|---|
| MAC-JA-2433 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-2439 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-2445 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-2451 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-2286 | james | 1 | 100.0% | +2.0134% | n<30 |
| MKT-JA-668 | james | 1 | 100.0% | +2.0134% | n<30 |
| MKT-JA-657 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-2198 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-256 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-462 | james | 1 | 100.0% | +2.0134% | n<30 |
| MAC-JA-468 | james | 1 | 100.0% | +2.0134% | n<30 |
| MKT-JA-651 | james | 1 | 100.0% | +2.0134% | n<30 |
| SEC-JA-644 | james | 1 | 100.0% | +2.0134% | n<30 |
| MKT-JA-1402 | james | 1 | 100.0% | +1.9469% | n<30 |
| MKT-JA-1402-BUT | james | 1 | 100.0% | +1.9469% | n<30 |

## Notes
- Burned Aug–Oct panels are smoke only — not used for clear/promote.
- Promote still stubbed (NW t, Bonferroni, RANDOM4+IWM).
- Panel still expanding beyond AAPL×60 + NVDA×20; re-run screen when Grok adds tickers.

## Files
- `/workspace/checklist_brainstorm/mine/pilot/reports/first_screen_singles.csv`
- `/workspace/checklist_brainstorm/mine/pilot/reports/first_screen_singles_preburn.csv`
- `/workspace/checklist_brainstorm/mine/pilot/reports/smoke_report.md`
- Working panel copy: `/workspace/checklist_brainstorm/mine/pilot/panel/panel_labeled.parquet`
