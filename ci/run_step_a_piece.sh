#!/usr/bin/env bash
# Parallel Step A matrix leg: builds exactly ONE chunk (I, zero-padded) end to end on a runner.
# Seeds this piece's scores/errors/answers if already done (skip rule), runs the engine for the piece,
# checkpoints scores+errors to the results branch and answers to the release, then kicks that chunk's
# exit-grid jobs. Math code unchanged - this is launch plumbing only.
set -uo pipefail
I="$(printf '%03d' "${I:?need I}")"
W="$RUNNER_TEMP"
bash ci/fetch_release.sh "$RELEASE" "$W/data"
export CHECKLIST_DATA_DIR="$W/data" OUT_DIR="$W/out" TMPDIR="$W/tmp"
mkdir -p "$OUT_DIR/chunks" "$TMPDIR"
git fetch -q origin "$RESULTS_BRANCH"
if [ "${SKIP_SEED:-0}" != "1" ]; then
    for f in "scores_${I}.parquet" "errors_${I}.json"; do
        if git cat-file -e "origin/${RESULTS_BRANCH}:step_a/${f}" 2>/dev/null; then
            git show "origin/${RESULTS_BRANCH}:step_a/${f}" > "$OUT_DIR/chunks/${f}" && echo "seeded ${f}"
        fi
    done
    python3 - "$RELEASE" "answers_${I}.npz" "$OUT_DIR/chunks" <<'PY'
import sys, json, os, urllib.request
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{sys.argv[1]}",
                             headers={'Authorization': f'token {tok}'})))
a = next((x for x in rel['assets'] if x['name'] == sys.argv[2]), None)
if a:
    req = urllib.request.Request(a['url'], headers={'Authorization': f'token {tok}', 'Accept': 'application/octet-stream'})
    with urllib.request.urlopen(req) as r, open(os.path.join(sys.argv[3], sys.argv[2]), 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
    print('seeded', sys.argv[2], a['size'])
PY
fi
export GRID_FILE=/nonexistent
python3 step_a.py --workers 4 --chunk 400 --only "$((10#$I))"
rc=$?
python3 ci/push_loop.py --chunks "$OUT_DIR/chunks" --once
# kick this chunk's exit-grid jobs as soon as its answers are up (idempotent; skips if grid exists)
if [ $rc -eq 0 ] || [ $rc -eq 143 ] || [ $rc -eq 137 ]; then
    curl -s -X POST -H "Authorization: token ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${GH_REPO}/actions/workflows/grid_chunk.yml/dispatches" \
        -d "{\"ref\":\"kimi/exit-grid\",\"inputs\":{\"i\":\"$((10#$I))\"}}" -o /dev/null -w "grid dispatch:%{http_code}\n"
fi
exit $rc
