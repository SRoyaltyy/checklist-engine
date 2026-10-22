# James v5.5e answer engine — test run (2026-10-22 HKT)
Engine: /workspace/checklist_brainstorm/engine/readers/james.py (`answer(ticker,date)`), CLI engine/answer_james.py; symlink /workspace/tf/engine/readers/james.py.
Rule: bars strictly before D (Asian cash sessions of D allowed — they close before 09:25 ET); cached series => reruns byte-identical (verified).
Pairs: 30 (large/small caps, BBBY+SIVB delisted, recent incl. today, holiday-adjacent, 6 market-stress dates), 2015-2026. 233,820 answers.
- 5,116 / 7,794 rows (65.6%) answer YES/NO on every pair; per-pair coverage 71-77%.
- Rows NOT_READY on some pair, by main cause: data_source_gap 1,563 · no_evaluator 508 · no_history_yet 475 · held calendar 118 · to_cut_v5.5f 14.
- Top causes: no PIT stock->SPDR sector map (450 rows) · Stockcharts breadth (392) · slow-series outlier of derived rows not coded (492) · pre-09:25 indication history (120) · FedWatch (44) · CNH=X feed only 1 bar (44) · 2015 dates short of 252-day windows (BTC/ETH etc.) · SIVB/BBBY no Yahoo chart (446 stock-BUT rows).
- FRED unreachable from box: DGS10/2/30, T10Y2Y, T10Y3M, DFII10, T10YIE taken from Treasury's official par/real yield-curve CSVs (same H.15 numbers).
- To cut in v5.5f (Manager Bot calendar audit fail): CAL-JA-004 CPI, 005 NFP, 013 Russell recon, 014 Russell deletion, 020 pre-holiday, 021 post-holiday, 022 half-day (+BUT twins = 14 rows).
- New sources: v5.5e has 0 rows on SOFR/RRP/auctions/TGA/curve; first-print reader newroots_value() added (earliest nightly file wins, NOT_READY building until 2 clean runs).
Files: james_v55e_results.csv, not_ready_rows.csv (per-row cause).
