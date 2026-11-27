# Step A answering engine — port provenance (2026-11-24)

Branch: `kimi/step-a-engine-port` (base `main` @ `7020524b`, verified 2026-11-24 18:20 HKT
as the live tip, unchanged since 9 Nov 2026 13:09 HKT).

## Why

The Step A answering engine existed only on orphan branches with no common ancestor
with `main` (`engine/v2.7.2.2`, `kimi/step-a-wincompat`, `kimi/dictionary-fixes`,
`kimi/pre-register`). Workflows on `main` (`step_a.yml`, `step_a_rerun.yml`,
`leak_sweep.yml`, `leak_verify.yml`) therefore had to check out those orphan branches to
find any code, and `ci/fetch_release.sh` / `ci/run_step_a_piece.sh` / `ci/verify_piece.sh`
/ `ci/run_step_a.sh` were missing from `main` entirely. HANDOFF.md section 5 step 4 ruled
the fix: copy/adapt the engine onto `main`; do not attempt a git merge of the orphans.

## What was copied, from where

Source of truth for math: **`kimi/dictionary-fixes` @ `1761ab64`** (newest engine state),
which descends from orphan **`engine/v2.7.2.2` @ `487387f`** via
**`kimi/step-a-wincompat` @ `6dbaf3cd`**.

| Files | Source |
|---|---|
| `engine.py`, `facets.py`, `facets_cal.py`, `facets_ext.py`, `facets_v26.py`, `facets_v27.py`, `facets_v271.py`, `facets_events.py`, `facets_worldq.py`, `params.py`, `datapaths.py`, `dials_pins.json`, `grid.csv`, `grid_v272_hist.csv`, `scoring/` (`trades.py`, `cp_v2_extra.py`), `integrity/`, `stats/`, `sample_data/`, `ci/fetch_release.sh`, `ci/run_step_a.sh`, `ci/push_loop.py`, `ci/fetch_ext.py`, `tests/test_leak.py`, `tests/test_facets_events.py`, `tests/test_events_empty_window.py`, `tests/test_run_ticker_events.py`, `tests/test_run_ticker_worldq.py` | `kimi/dictionary-fixes` @ `1761ab64` (byte-identical) |
| `ci/run_step_a_piece.sh`, `ci/verify_piece.sh`, `tests/leak_sweep.py`, `tests/leak_verify_history.py` | `kimi/step-a-wincompat` @ `6dbaf3cd` (byte-identical) |
| `step_a.py` | **merged**: dictfix base (math, `--force`) + wincompat `--only` matrix plumbing; both `ci/run_step_a.sh` and `ci/run_step_a_piece.sh` run this one file |

Workflows changed (only `ref:` pins removed — they now check out the ref they are
dispatched from, i.e. code that exists on the branch): `step_a.yml`, `step_a_rerun.yml`,
`leak_sweep.yml`, `leak_verify.yml`.

## Deliberately NOT ported (out of scope, do not add silently)

- `scoring/combine.py`, `step_grid.py`, `scoring/exit_grid.py`, `scoring/shortlist.py` —
  Stage 5 / Step B territory; **scoring stays CLOSED** until the world gate is proven and
  the full-universe answer matrix exists (HANDOFF hard rule).
- Exit-grid / combiner / shortlist / impact-diff ci scripts — those workflows still check
  out `kimi/exit-grid` / `kimi/shortlist-shards` and are a separate port decision.
- `QUESTION_TREE_v2.7.csv` (4.1MB reference doc) — not read at runtime (the engine reads
  `QUESTION_TREE_v2.7.1.csv` from the data release, sha-checked); stays on the orphan
  branches. Runtime inputs come from release `data-2020-24-v1` via `ci/fetch_release.sh`.
- `integrity/splits_yahoo.parquet` (binary splits table) — not committed on main because
  binary content cannot ride the file-push channel. Instead
  `integrity/splits_yahoo.parquet.b64` ships in-repo (base64 of the exact
  `kimi/dictionary-fixes` bytes) and `integrity/mcap_fix.py` loads it lazily at first use
  (adapted from the orphan version's module-level load, which also rewrote a derived
  parquet). Verified: split factors identical to the orphan module across all 1,842
  tickers (`verifier/v1/check_mcap_fix.py`). The derived `splits_yahoo_all.parquet`
  build artifact is no longer written; `yraw2_*.json` ship as normal text.

## Runtime parameters that stay OPEN (not decided by this port)

`scoring/trades.py` carries lineage constants `FEE = 0.003` (30bp each way), win-rate
floors 35/40/45/50 with main floor 40%, exit rule v1 (+20% / day 15). These are pre-existing
lineage values, not new rulings; the official fee/slippage number remains OPEN per HANDOFF
section 7 and must be settled by Cyrus.

## Verification

- Static + import verifier: `verifier/v1/check.py` (PASS, logs under `verifier/runs/`).
- Runtime identity proof: dispatch `step-a` with `verify=true` on this branch — rebuilds
  chunk 1 and byte-compares against `results/step-a-2020-22` and release `data-2020-24-v1`.
- Leak sweep: dispatch `leak-sweep` on this branch (`tests/leak_sweep.py`, 60 tickers × 12
  cut dates); `leak-verify` adjudicates any flags.
