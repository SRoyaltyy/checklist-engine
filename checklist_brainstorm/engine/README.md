# Answer engine

Give it a ticker and a date; it answers YES, NO or NOT_READY for every row in `merged_draft_v8.2.csv`.

    python3 engine/answer.py --ticker AAPL --date 2026-10-21 [--out file.csv]

Output (default `engine/out/answers_<TICKER>_<DATE>.csv`), one line per sheet row id, sorted by id:
`row_id,owner,ticker,date,answer,reason,data_as_of`. Two runs on the same cached data give identical files.

## Cutoff
Use only data that was public before **09:25 ET on the date asked**. Anything dated on that day after
09:25, or later, must not be used. Use each source's real publish lag (e.g. a daily close is known at D-1 16:15 ET;
CFTC COT is known Friday 15:30 ET, so it counts from the next session).

## Reader contract
- One file per owner at `/workspace/checklist_brainstorm/engine/readers/<owner>.py` (fallback folder `/workspace/tf/engine/readers/`; symlinks are de-duplicated by real path; dashes in file names are fine). Files starting with `_` are skipped (see `_example_stub.py`).
- It must expose `answer(ticker, date)` (`date` is `YYYY-MM-DD`) returning a list of dicts with
  `row_id`, `ticker`, `date`, `answer` (`YES`/`NO`/`NOT_READY`), `reason`, `data_as_of` (date of the newest data point used).
- `answer` must be exactly `YES`, `NO` or `NOT_READY`. Anything else (`NA`, blank, `True`) is a contract error: flagged, and the row is written as NOT_READY.
- **NOT_READY always needs a reason** (e.g. `held:no_nightly_archive`, `before_series_start`, `missing_data`).
  Never guess, never leave blank. A NOT_READY without a reason is a contract error too.
- Cache your downloads under `engine/cache/` so reruns are fast and identical.

## What the runner does
Loads every reader, runs them all, joins to the sheet. Rows no reader answered become `NOT_READY, no_reader`.
If a reader crashes, its rows become `NOT_READY, reader_error: <msg>` and the other readers still run.
If two readers answer the same row id, that is a conflict: flagged and written as `NOT_READY, conflict: <readers>`.
Unknown ids, duplicate sheet ids, conflicts, contract errors and crashes are printed as `WARN` lines
on stderr.
Row universe = ids in `/workspace/checklist_brainstorm/merged_draft_v8.2.csv`.
