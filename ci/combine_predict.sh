#!/usr/bin/env bash
# Combiner predict phase: builds the per-year strategy maps once BOTH model targets are
# published. Idempotent: exits cleanly while inputs are missing or outputs exist.
set -euo pipefail
W="$RUNNER_TEMP"
TAG="${MODEL_RELEASE:-combine-2020-22-v1}"
GRID_TAG="${GRID_RELEASE:-grid-2020-22-v1}"
bash ci/fetch_release.sh "$RELEASE" "$W/data"
export CHECKLIST_DATA_DIR="$W/data" GRID_FILE=/nonexistent

dl() {  # dl <release-tag> <asset-name> <dest-dir>
    python3 - "$1" "$2" "$3" <<'PY'
import sys, json, os, urllib.request
tag, name, dest = sys.argv[1:4]
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
out = os.path.join(dest, name)
if os.path.exists(out):
    print('have', name); sys.exit(0)
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{tag}",
                             headers={'Authorization': f'token {tok}'})))
a = next((x for x in rel['assets'] if x['name'] == name), None)
if not a:
    print(f'MISSING {name} on {tag}'); sys.exit(1)
req = urllib.request.Request(a['url'], headers={'Authorization': f'token {tok}', 'Accept': 'application/octet-stream'})
os.makedirs(dest, exist_ok=True)
with urllib.request.urlopen(req) as r, open(out + '.part', 'wb') as f:
    while True:
        b = r.read(1 << 20)
        if not b: break
        f.write(b)
os.replace(out + '.part', out)
print('downloaded', name, a['size'])
PY
}

# gate: both models + answers + grid precompute
python3 ci/release_assets.py have "$TAG" model_logistic.npz model_ridge.npz model.json \
    || { echo 'both model targets not published yet; nothing to do'; exit 0; }
names=$(python3 - "$RELEASE" <<'PY'
import sys, json, os, urllib.request
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{sys.argv[1]}",
                             headers={'Authorization': f'token {tok}'})))
print('\n'.join(a['name'] for a in rel['assets']))
PY
)
for i in $(seq 0 33); do
    echo "$names" | grep -qx "$(printf 'answers_%03d.npz' "$i")" || { echo 'answers not complete'; exit 0; }
done
if python3 ci/release_assets.py have "$TAG" predict_summary.json; then
    echo 'strategy maps already published; nothing to do'
    exit 0
fi

dl "$TAG" model_logistic.npz "$W/model"; dl "$TAG" model_ridge.npz "$W/model"; dl "$TAG" model.json "$W/model"
git fetch -q origin results/step-a-2020-22
if git cat-file -e origin/results/step-a-2020-22:step_a/trade_base_rows.parquet 2>/dev/null; then
    git show origin/results/step-a-2020-22:step_a/trade_base_rows.parquet > "$W/trade_base_rows.parquet"
else
    dl "$RELEASE" trade_base_rows.parquet "$W" || { echo 'trade_base_rows.parquet not available'; exit 0; }
fi
for i in $(seq 0 33); do dl "$RELEASE" "$(printf 'answers_%03d.npz' "$i")" "$W/answers"; done
for i in 000 001 002 003 004 005 006 007; do dl "$GRID_TAG" "shard_${i}.npz" "$W/grid_pre"; done
dl "$GRID_TAG" meta.json "$W/grid_pre"; dl "$GRID_TAG" bench_pre.npz "$W/grid_pre"

python3 scoring/combine.py predict --model "$W/model" --answers "$W/answers" \
    --base "$W/trade_base_rows.parquet" --pre "$W/grid_pre" --bench "$W/grid_pre/bench_pre.npz" \
    --out "$W/preds"
python3 ci/release_assets.py upload "$TAG" "$W"/preds/strategy_map_*.parquet "$W/preds/predict_summary.json"
echo 'strategy maps published to' "$TAG"
