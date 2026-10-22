# Taskforce checklist YES/NO mining — pilot harness

Walk-forward **first screen** for checklist answers → forward returns.
Owner: Trading Bot Taskforce (labels + miner). Grok owns nightly YES/NO matrix dumps.

## Locked method (War room 2026-10-22)

| Item | Value |
|---|---|
| Primary label | open → next open |
| Secondary | open → close |
| Fees | 10 bp/side (0.20% RT) |
| First screen (James) | test-half n≥30, win>55%, mean_aft>0 |
| Features | YES only (skip NOT_READY; no inventing) |
| Clock | answers known by 09:25 ET; D-1 bars |
| Burned (promote later) | Jul–Oct 2026 — report never select |
| IRONCLAD | no h1 / Factor Mine / sealed / ENGINE_SHA256 / fullscan PRs |



## Current selection panel (USE THIS)

**Grok promote-eligible preburn (ready):**
`/workspace/checklist_brainstorm/engine/out/pilot_matrix/preburn/panel_yesno_preburn_james_grok.parquet`

```bash
cd /workspace/checklist_brainstorm/mine/pilot
# screen already written; to re-run after Grok expands tickers:
python3 -c "exec(open('screen_singles.py').read())"  # or dedicated runner below
```

Singles table: `reports/first_screen_singles.csv` (also `first_screen_singles_preburn.csv`)
Smoke report: `reports/smoke_report.md`

Do **not** promote from burned Aug–Oct smoke panels.

## Date lock (CRITICAL)

**Jul–Oct 2026 is BURNED** — report metrics only, never select/promote (same as Theme Radar’s Aug–Oct clears).

| File | Role |
|---|---|
| `sessions.txt` / `sessions_prejul.txt` | **Selection tape** (≤2026-06-30), default for first screen |
| `sessions_burned_smoke.txt` | Aug–Oct smoke/report only |
| `panel/panel_labeled_burned_smoke.parquet` | Preserved burned smoke panel |

`screen_singles.py` sets `clear_test` only on the pre-Jul test half. Burned rows populate `n_burned` / `win_burned` / `mean_aft_burned` for report.

Pre-Jul labels: `ds1016` OHLC. Burned labels: Grok `pilot_matrix/yahoo_ohlc_pilot.parquet` merged in `labels.py`.

## Layout

```
mine/pilot/
  universe.txt|.md     # 50 liquid names (aligned to Grok pilot_matrix OHLC)
  sessions.txt|.md     # ~56 sessions 2026-08-03 → 2026-10-20
  labels.py            # OHLC → ret_o2o / ret_o2c
  build_panel.py       # dumps → YES panel, or call readers
  answer_one.py        # per-ticker reader worker
  screen_singles.py    # chronological train/test first screen
  run_pilot.py         # orchestrator
  panel/               # yes_panel.parquet, panel_labeled.parquet, meta
  cache/answers/       # yes_<T>_<D>.parquet reader cache
  reports/             # first_screen_singles.csv, smoke_report.md
```

## Prefer Grok’s dump

If files appear under `/workspace/checklist_brainstorm/engine/out/pilot_matrix/`
(`answers_*.csv`, `panel_yes.parquet`, etc. — **not** the OHLC-only parquet),
`build_panel.py` ingests them and skips reader calls.

```bash
cd /workspace/checklist_brainstorm/mine/pilot
python3 run_pilot.py                 # auto: dumps if present else readers
python3 run_pilot.py --force-readers # ignore dumps
python3 run_pilot.py --thin          # smoke cut: 12 names × 20 dates × james-only
```

James reader points at `v8src/James-v5.5f.csv` (7780 rows).

## Thin cut (when full grid is too slow)

`--thin` uses **12 tickers × last 20 sessions × james only**.
Full 50×56×(james+taskforce) is expensive (~18s/date/ticker for james alone).
Taskforce reader is hooked (`--readers james,trading-bot-taskforce`) but omitted
from the thin smoke; re-enable for a fuller panel once Grok’s matrix lands.

## Stubbed for full harness later

- Walk-forward promote: train 2020–24, confirm 2025–mid-2026, burned Jul–Oct 2026
- Newey–West t≥3.37, Bonferroni, beat RANDOM4+IWM
- Pairs miner (YES∧YES)
- signal_group collapse (BUT twins count once) — `--by-signal-group` flag exists on screen
- Nightly append from Grok matrix without re-calling readers

## Re-run screen only

```bash
python3 screen_singles.py
# or
python3 screen_singles.py --by-signal-group
```
