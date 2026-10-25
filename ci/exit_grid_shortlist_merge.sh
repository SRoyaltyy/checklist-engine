#!/usr/bin/env bash
# Exit-grid shortlist MERGE job (0b 2026-10-25): pull every per-chunk shard output + the
# bench trade counts off the release, apply the global junk rule, write shortlist.csv.
# Runs after all shard jobs; skips cleanly if no shards exist yet.
set -euo pipefail
TAG="${GRID_RELEASE:?need GRID_RELEASE}"
W="$RUNNER_TEMP"
mkdir -p "$W/shards" "$W/grid_pre"
python3 ci/release_assets.py getmatch "$TAG" "$W/shards" 'shortlist_shard_*'
python3 ci/release_assets.py getmatch "$TAG" "$W/grid_pre" 'bench_pre.npz'
N=$(ls "$W/shards" | grep -c -E '^shortlist_shard_[0-9]+\.parquet$' || true)
if [ "$N" -eq 0 ]; then
    echo 'no shard outputs yet; nothing to merge'
    exit 0
fi
echo "merging $N shard outputs"
python3 scoring/shortlist.py --merge --indir "$W/shards" --bench "$W/grid_pre/bench_pre.npz" --out "$W/shortlist.csv"
FORCE_UPLOAD=1 python3 ci/release_assets.py upload "$TAG" "$W/shortlist.csv"
echo 'shortlist merge done'
