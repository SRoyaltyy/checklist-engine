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
if git cat-file -e origin/results/step-a-2020-22:step_a/trade_base_rows.parquet 2>/dev/null; then
    git show origin/results/step-a-2020-22:step_a/trade_base_rows.parquet > "$W/trade_base_rows.parquet"
else
    # fallback: single-asset download from the data release (release_assets.py get would fetch ALL assets)
    python3 - "$RELEASE" "$W" <<'PY'
import sys, json, os, urllib.request
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{sys.argv[1]}",
                             headers={'Authorization': f'token {tok}'})))
a = next((x for x in rel['assets'] if x['name'] == 'trade_base_rows.parquet'), None)
if not a:
    print('trade_base_rows.parquet not on results branch or release yet (Step A still starting); retry later')
    sys.exit(1)
req = urllib.request.Request(a['url'], headers={'Authorization': f'token {tok}', 'Accept': 'application/octet-stream'})
with urllib.request.urlopen(req) as r, open(os.path.join(sys.argv[2], 'trade_base_rows.parquet'), 'wb') as f:
    while True:
        b = r.read(1 << 20)
        if not b: break
        f.write(b)
print('downloaded trade_base_rows.parquet', a['size'])
PY
fi
if python3 ci/release_assets.py have "$TAG" shard_000.npz shard_007.npz bench_pre.npz meta.json; then
    echo 'grid precompute already uploaded; nothing to do'
    exit 0
fi
python3 step_grid.py prep --base "$W/trade_base_rows.parquet" --out "$W/grid_pre"
python3 step_grid.py bench --base "$W/trade_base_rows.parquet" --pre "$W/grid_pre" --out "$W/grid_pre/bench_pre.npz"
python3 ci/release_assets.py upload "$TAG" "$W"/grid_pre/shard_*.npz "$W/grid_pre/meta.json" "$W/grid_pre/bench_pre.npz"
echo 'prep done'
