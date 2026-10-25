#!/usr/bin/env bash
# Exit-grid shortlist job: download whatever gridy/grid outputs exist on GRID_RELEASE, run the
# prereg §3-5 shortlist (2020-21 fit screen + untouched 2022 stats), upload shortlist.csv.
# Idempotent and partial-tolerant: re-runs pick up newly finished chunk outputs.
set -euo pipefail
TAG="${GRID_RELEASE:?need GRID_RELEASE}"
W="$RUNNER_TEMP"
python3 ci/release_assets.py get "$TAG" "$W/grid_out"
# prep meta/bench for junk-rule trade counts
python3 ci/release_assets.py get "$TAG" "$W/grid_pre"
N_GRID=$(ls "$W/grid_out" | grep -c -E '^gridy?_' || true)
if [ "$N_GRID" -eq 0 ]; then
    echo 'no grid outputs yet; nothing to do'
    exit 0
fi
echo "aggregating over $N_GRID grid files"
python3 scoring/shortlist.py --indir "$W/grid_out" --bench "$W/grid_pre/bench_pre.npz" --out "$W/shortlist.csv"
python3 ci/release_assets.py upload "$TAG" "$W/shortlist.csv"
echo 'shortlist done'
