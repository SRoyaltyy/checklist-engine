# _theme_radar_universe.universe(date)

Read-only. `from _theme_radar_universe import universe` (underscore = not loaded as a reader) (add this folder to `sys.path`).

- Returns a pandas DataFrame indexed by `Ticker` (~11.7k stocks + ETFs), or **None** when no
  snapshot is usable → answer `NOT_READY` with reason `no_universe_snapshot`.
- Rows are theme-radar's latest Finviz Elite export (`data/snapshots/<D>.raw.csv` on origin/main)
  known before **09:25 ET on `date`**: the version must be committed before that cutoff, and a
  snapshot dated D is never used for date D (`snapshot_date < date`). Rewritten files: newest version
  known by the cutoff. Holidays/weekends follow NYSE.
- Columns: every Finviz export column as **strings, unparsed** (e.g. `Ticker` index, `Company`,
  `Sector`, `Industry`, `Index`, `Market Cap` ($M), `Forward P/E`, `P/E`, `EPS (ttm)`, `Short Float`
  ("16.62%"), `Average Volume` (thousands), `Volume` (shares), `Shares Outstanding`/`Shares Float` (M),
  `Price`, `Change`, `Gap`, `Relative Volume`, `Performance (Week|Month|Quarter|Half Year|YTD|Year)`,
  `20/50/200-Day Simple Moving Average` (% distance), `52-Week High/Low`, `All-Time High/Low` (% distance),
  `Earnings Date` ("11/2/2026 4:30:00 PM"), ETF fields (`Net Asset Value %`, `Net Flows (1 Month)` in $,
  `Assets Under Management` in $), ... ~160 total), plus
  - `snapshot_date` – the export date used,
  - `data_as_of` – same date (newest data point in the row; prices are that session's close).
  Empty string = Finviz had no value. Strip `%` / `,` before numeric use.
- Also exposed: `history(date, usecols=None)` (all usable snapshots, oldest first) and
  `usable_versions(date)`.
- Test: `python3 _test_theme_radar_universe.py`.
