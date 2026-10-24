#!/usr/bin/env bash
# Exit-grid matrix job: aggregate answers chunk $I across the full 26,100-rule grid, upload grid_NNN.parquet.
# Idempotent and dependency-aware: skips cleanly if its answers chunk isn't built yet (Step A still running)
# or its output already exists. Discover window (2020-22) only.
set -euo pipefail
TAG="${GRID_RELEASE:?need GRID_RELEASE}"
I="$(printf '%03d' "${I:?need I}")"
YEAR="${YEAR:-}"                       # empty = full discover window; else restrict to that calendar year
W="$RUNNER_TEMP"
OUT_NAME="grid_${I}.parquet"
[ -n "$YEAR" ] && OUT_NAME="gridy_${I}_${YEAR}.parquet"
# does Step A's answers chunk exist on the data release yet?
if ! python3 ci/release_assets.py have "$RELEASE" "answers_${I}.npz"; then
    echo "answers_${I}.npz not on $RELEASE yet (Step A still running); skipping"
    exit 0
fi
if python3 ci/release_assets.py have "$TAG" "$OUT_NAME"; then
    echo "$OUT_NAME already uploaded; nothing to do"
    exit 0
fi
python3 ci/release_assets.py get "$TAG" "$W/grid_pre"          # shards + meta + bench tables
python3 - "$RELEASE" "answers_${I}.npz" "$W" <<'PY'
import sys, json, os, urllib.request
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{sys.argv[1]}",
                                 headers={'Authorization': f'token {tok}'})))
a = next(x for x in rel['assets'] if x['name'] == sys.argv[2])
req = urllib.request.Request(a['url'], headers={'Authorization': f'token {tok}', 'Accept': 'application/octet-stream'})
with urllib.request.urlopen(req) as r, open(os.path.join(sys.argv[3], sys.argv[2]), 'wb') as f:
    while True:
        b = r.read(1 << 20)
        if not b:
            break
        f.write(b)
print('downloaded', sys.argv[2], a['size'])
PY
export GRID_FILE=/nonexistent
YEAR_ARGS=""
[ -n "$YEAR" ] && YEAR_ARGS="--year $YEAR"
python3 step_grid.py chunk --i "$((10#$I))" --answers "$W/answers_${I}.npz" \
    --pre "$W/grid_pre" --bench "$W/grid_pre/bench_pre.npz" --out "$W/grid_chunks" $YEAR_ARGS
python3 ci/release_assets.py upload "$TAG" "$W/grid_chunks/$OUT_NAME"
echo "chunk $I (year=${YEAR:-all}) done"
