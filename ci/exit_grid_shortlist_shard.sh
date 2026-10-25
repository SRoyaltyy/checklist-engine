#!/usr/bin/env bash
# Exit-grid shortlist SHARD job (0b 2026-10-25): process exactly ONE grid chunk (env CHUNK),
# streaming parquet batches so peak RAM stays bounded on ubuntu-latest. Uploads the shard's
# screened survivors and its legacy-rule counts; the separate merge job applies the global
# junk rule. Skips cleanly if the chunk's grid files are not on the release yet.
set -euo pipefail
TAG="${GRID_RELEASE:?need GRID_RELEASE}"
CHUNK="${CHUNK:?need CHUNK}"
W="$RUNNER_TEMP"
mkdir -p "$W/grid_out"
python3 ci/release_assets.py getmatch "$TAG" "$W/grid_out" "gridy_${CHUNK}_*.parquet" "grid_${CHUNK}.parquet"
N=$(ls "$W/grid_out" | grep -c -E '^gridy?_' || true)
if [ "$N" -eq 0 ]; then
    echo "chunk $CHUNK: no grid files yet; nothing to do"
    exit 0
fi
echo "chunk $CHUNK: processing $N grid files"
python3 scoring/shortlist.py --shard "$CHUNK" --indir "$W/grid_out" --out "$W/shortlist_shard_${CHUNK}.parquet"
FORCE_UPLOAD=1 python3 ci/release_assets.py upload "$TAG" "$W/shortlist_shard_${CHUNK}.parquet"
LEG="$W/shortlist_shard_${CHUNK}.parquet.leg.parquet"
if [ -f "$LEG" ]; then
    FORCE_UPLOAD=1 python3 ci/release_assets.py upload "$TAG" "$LEG"
fi
echo "chunk $CHUNK: shard done"
