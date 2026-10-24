#!/usr/bin/env bash
# Combiner runner job (METHODOLOGY 0b: combining model per docs/COMBINING_PREREG.md).
# Gates on ALL Step A answers chunks + grid precompute being published, fits the combining
# model on 2020-21 (check on 2022), and publishes model artifacts to MODEL_RELEASE.
# Idempotent: exits cleanly 0 while Step A is still running or the model is already published.
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

# gate 1: every Step A answers chunk must be published (check names only - no downloads yet)
names=$(python3 - "$RELEASE" <<'PY'
import sys, json, os, urllib.request
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{sys.argv[1]}",
                             headers={'Authorization': f'token {tok}'})))
print('\n'.join(a['name'] for a in rel['assets']))
PY
)
missing=0
for i in $(seq 0 33); do
    n=$(printf 'answers_%03d.npz' "$i")
    echo "$names" | grep -qx "$n" || { echo "missing $n"; missing=1; }
done
[ "$missing" -eq 0 ] || { echo 'Step A answers not complete yet; nothing to do'; exit 0; }
# all present: download them for real
for i in $(seq 0 33); do
    dl "$RELEASE" "$(printf 'answers_%03d.npz' "$i")" "$W/answers"
done

# trade base rows (results branch first, release fallback) - same as exit_grid_prep.sh
git fetch -q origin results/step-a-2020-22
if git cat-file -e origin/results/step-a-2020-22:step_a/trade_base_rows.parquet 2>/dev/null; then
    git show origin/results/step-a-2020-22:step_a/trade_base_rows.parquet > "$W/trade_base_rows.parquet"
else
    dl "$RELEASE" trade_base_rows.parquet "$W" || { echo 'trade_base_rows.parquet not available yet'; exit 0; }
fi

# grid precompute + benchmark tables
for i in 000 001 002 003 004 005 006 007; do dl "$GRID_TAG" "shard_${i}.npz" "$W/grid_pre"; done
dl "$GRID_TAG" meta.json "$W/grid_pre"
dl "$GRID_TAG" bench_pre.npz "$W/grid_pre"

# already published?
if python3 ci/release_assets.py have "$TAG" model.npz model.json check_2022.json; then
    echo 'combining model already published; nothing to do'
    exit 0
fi

python3 scoring/combine.py fit --answers "$W/answers" --base "$W/trade_base_rows.parquet" \
    --pre "$W/grid_pre" --bench "$W/grid_pre/bench_pre.npz" --out "$W/model" \
    --max-trades 400000 --cells-per-trade 12 --iters 60
python3 ci/release_assets.py upload "$TAG" "$W/model/model.npz" "$W/model/model.json" "$W/model/check_2022.json"
echo 'combiner fit done and published to' "$TAG"
