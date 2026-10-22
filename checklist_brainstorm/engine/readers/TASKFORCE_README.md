# Trading Bot Taskforce reader

`readers/trading-bot-taskforce.py` → `answer(ticker, date)` returns one dict per Taskforce row:
`row_id, ticker, date, answer (YES/NO/NOT_READY), reason (always set when NOT_READY), data_as_of (last daily bar used)`.
Order: 8,309 compact ids `PV-TFC-*` (v8.1 uses 8,289 of them), then 224 timeframe ids `PV-TFX-*`, then 43,326 full ids `PV-TF-*` (inbox v10.5).

- **Cutoff:** only daily bars dated before D (last bar = the D-1 close, known 16:00 ET D-1, before 09:25 ET D). Splits with ex-date on or before D are applied with `tf/adjust.py`. An unfinished live bar is dropped.
- **Data:** Yahoo chart API (stock, SPY, sector SPDR, ^VIX, ^VIX3M) and Yahoo search (sector). Cached in `engine/cache/taskforce/`, and re-fetched only when the cache is older than D, so the same inputs always give the same output.
- **Compact rows:** YES if any folded timeframe is YES, NO if all are NO, otherwise NOT_READY.
- **Timeframe rows:** 2D/3D blocks on the SPY calendar, ISO weeks and calendar months, either completed or period-to-date through D-1 (same rules as `tf/tfx/tfx.py`).
- **Twins:** every base/BUT pair is checked on each call (`TWIN_STATS`). Exclusive pairs must never both be YES. Same-trigger pairs (streak/outlier/tug-of-war hypothesis rows) must be equal.
- **Not answered yet:** rank vs sector/market (needs a full-universe cross-section), halts, FINRA short data, FTD, Finviz earnings, point-in-time market cap, and 18 exotic indicators.

Test CLI: `python3 readers/_tf_cli.py --ticker AAPL --date 2024-05-15` or `--tickers f.txt --dates 2024-05-15,2021-01-27` (or `START:END`). Add `--trunc D-1` to cut the raw data at D-1.
