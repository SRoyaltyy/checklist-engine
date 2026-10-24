#!/usr/bin/env bash
# Proof for METHODOLOGY 0b 22:50: rebuild chunk 1 fresh in a matrix-style job and show the outputs are
# identical to the existing scores_001.parquet (results branch) and answers_001.npz (release asset).
# Byte-identity is reported; if bytes differ (e.g. numpy header drift) the arrays must match exactly.
set -euo pipefail
I=001
W="$RUNNER_TEMP"
bash ci/fetch_release.sh "$RELEASE" "$W/data"
export CHECKLIST_DATA_DIR="$W/data" OUT_DIR="$W/verify" TMPDIR="$W/tmp"
mkdir -p "$OUT_DIR/chunks" "$TMPDIR"
export GRID_FILE=/nonexistent SKIP_SEED=1
python3 step_a.py --workers 4 --chunk 400 --only 1
echo "== rebuilt shas =="
sha256sum "$OUT_DIR/chunks/scores_001.parquet" "$OUT_DIR/chunks/answers_001.npz"
git fetch -q origin "$RESULTS_BRANCH"
git show "origin/${RESULTS_BRANCH}:step_a/scores_001.parquet" > "$W/scores_001.orig.parquet"
echo "== existing scores_001 sha =="
sha256sum "$W/scores_001.orig.parquet"
python3 - "$RELEASE" "$W" <<'PY'
import sys, json, os, urllib.request, hashlib
tok = os.environ['GITHUB_TOKEN']
api = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
rel = json.load(urllib.request.urlopen(urllib.request.Request(f"{api}/releases/tags/{sys.argv[1]}",
                             headers={'Authorization': f'token {tok}'})))
a = next(x for x in rel['assets'] if x['name'] == 'answers_001.npz')
req = urllib.request.Request(a['url'], headers={'Authorization': f'token {tok}', 'Accept': 'application/octet-stream'})
h = hashlib.sha256()
with urllib.request.urlopen(req) as r, open(os.path.join(sys.argv[2], 'answers_001.orig.npz'), 'wb') as f:
    while True:
        b = r.read(1 << 20)
        if not b: break
        h.update(b); f.write(b)
print('existing answers_001 sha256:', h.hexdigest())
PY
python3 - "$OUT_DIR" "$W" <<'PY'
import sys, json, hashlib
import numpy as np, pandas as pd
out, w = sys.argv[1], sys.argv[2]
res = {}
for name, new, old in (
    ('scores_001.parquet', f'{out}/chunks/scores_001.parquet', f'{w}/scores_001.orig.parquet'),
    ('answers_001.npz', f'{out}/chunks/answers_001.npz', f'{w}/answers_001.orig.npz')):
    hn = hashlib.sha256(open(new, 'rb').read()).hexdigest()
    ho = hashlib.sha256(open(old, 'rb').read()).hexdigest()
    if name.endswith('.parquet'):
        same = pd.read_parquet(new).equals(pd.read_parquet(old))
    else:
        a, b = np.load(new), np.load(old)
        same = list(a.keys()) == list(b.keys()) and all(np.array_equal(a[k], b[k]) for k in a.keys())
    res[name] = dict(bytes_identical=hn == ho, content_identical=bool(same), new_sha=hn[:16], old_sha=ho[:16])
print(json.dumps(res, indent=1))
ok = all(r['content_identical'] for r in res.values())
print('VERIFY', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
PY
