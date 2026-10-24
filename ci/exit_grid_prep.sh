#!/usr/bin/env bash
# Exit-grid prep job: build per-trade first-hit shards + per-rule benchmark tables once, upload to GRID_RELEASE.
# Idempotent: skips everything if the assets already exist. Discover window (2020-22) only.
set -euo pipefail
TAG="${GRID_RELEASE:?need GRID_RELEASE}"
W="$RUNNER_TEMP"
bash ci/fetch_release.sh "$RELEASE" "$W/data"
export CHECKLIST_DATA_DIR="$W/data"
export GRID_FILE=/nonexistent
git fetch -q origin results/step-a-2020-22
git show origin/results/step-a-2020-22:step_a/trade_base_rows.parquet > "$W/trade_base_rows.parquet"
if python3 ci/release_assets.py have "$TAG" shard_000.npz shard_007.npz bench_pre.npz meta.json; then
    echo 'grid precompute already uploaded; nothing to do'
    exit 0
fi
python3 step_grid.py prep --base "$W/trade_base_rows.parquet" --out "$W/grid_pre"
python3 step_grid.py bench --base "$W/trade_base_rows.parquet" --pre "$W/grid_pre" --out "$W/grid_pre/bench_pre.npz"
python3 ci/release_assets.py upload "$TAG" "$W"/grid_pre/shard_*.npz "$W/grid_pre/meta.json" "$W/grid_pre/bench_pre.npz"
echo 'prep done'
