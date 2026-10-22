# James sector-wire QA — AAPL 2026-10-21

## Change
Patched `engine/readers/james.py` (tf path is a symlink to the same file).

- `SECTOR_TO_SPDR` + `spdr_for(ticker, D)` via `_theme_radar_universe.universe(D)` (D-1 Finviz Sector → XLK/XLF/…). Finviz aliases: Consumer Cyclical→XLY, Consumer Defensive→XLP, Basic Materials→XLB, Healthcare→XLV, Financials→XLF.
- PIT rule: single sector assignment from `universe(D)` applied to the whole Yahoo price history (documented in code; no multi-year membership-change history).
- `resolve(..., D)` no longer raises `no point-in-time stock->SPDR sector map`; returns SPDR ticker, `RATIO(SPDR,SPY)`, or `STOCK_SPDR`.
- `sector_row_measure` / `sector_measure_from_cond` for the 72 slow-meta sector-row parents (JA-007..011, JA-033).
- `sector_eval` for stock-vs-SPDR / SPDR-vs-SPY / divergence / ATR / tech+mcap rotation rows.
- Existing `slow_meta` patch kept; Outlier/Exhaustion on stock's SPDR reuse `outlier`/`generic` after resolve→XLK.

## Counts (James reader only)

| | YES | NO | NOT_READY |
|---|---:|---:|---:|
| Prior post-slow_meta baseline (war-room) | ~300 | ~6075 | ~1419 |
| After sector wire | 349 | 6536 | 884 |

- Rows answered: 7769 (James-v5.5e minus James-removed-v5.5e overlap).
- SPDR map-gap reason remaining: **0**.
- Two identical runs: run1 == run2 (byte-identical answers).

## Sector-ish slice (548 rows that previously hit the SPDR/sector-row blockers)
- YES 49 / NO 461 / NOT_READY 38
- Remaining sector NOT_READY are not map-gap: MAC slow-meta with mislabeled stock+SPDR source (24), pre-09:25 indication (10), constituents/breadth (4).

## Top remaining NOT_READY reasons (all James)
- 392: data_source_gap: Stockcharts breadth is not a free official feed; constituent rebuild not built
- 130: data_source_gap: pre-09:25 ET indication history not archived
- 93: held/to_cut_review: calendar/macro event row; needs official archived event history wired (Manager Bot calendar audit)
- 44: data_source_gap: CNH=X feed returns only 1 bars in total
- 44: data_source_gap: no free official archived history wired (CME FedWatch next-meeting probabilities)
- 25: data_source_gap: no free official archived history wired (Yahoo daily OHLC of index/sector constit)
- 24: no_evaluator: slow-meta parent measure not sector-row / not wired for stock+SPDR source
- 23: data_source_gap: multi-source/composite row, no evaluator for source "CME Globex front-month (Yahoo =F)"
- 16: no_evaluator: definition template not implemented in engine yet
- 15: data_source_gap: needs intraday 09:00 ET snapshot; no archived official intraday history
- 14: to_cut_v5.5f: Manager Bot calendar audit failed (no official archived history proving every past date)
- 12: data_source_gap: no free official archived history wired (CME FedWatch)
- 8: data_source_gap: no free official archived history wired (CBOE daily market statistics (cboe.com))
- 6: data_source_gap: needs stock attribute (revenue mix/industry/corr) with no PIT official feed
- 4: data_source_gap: multi-source/composite row, no evaluator for source "CBOE + OHLC"

## Grok re-run?
**Yes** — `james.py` is ready for AAPL/NVDA/CRMT 10-21 page refresh. Caveat: 24 MAC slow-meta rows with source `Yahoo daily OHLC (stock + SPDR ETFs)` still NOT_READY (`slow-meta parent measure not sector-row / not wired`); they no longer emit the old SPDR map-gap reason.

## Artifacts
- `/workspace/checklist_brainstorm/qa/james_sector_wire/AAPL_2026-10-21.csv`
- `/workspace/checklist_brainstorm/qa/james_sector_wire/AAPL_2026-10-21_run1.csv`
- `/workspace/checklist_brainstorm/qa/james_sector_wire/AAPL_2026-10-21_run2.csv`
- `/workspace/checklist_brainstorm/qa/james_sector_wire/summary.md`
