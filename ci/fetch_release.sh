#!/usr/bin/env bash
# Download every asset of a GitHub release into DEST and verify SHA256SUMS. Usage: fetch_release.sh <tag> <dest>
set -euo pipefail
TAG="$1"; DEST="$2"; mkdir -p "$DEST"
API="https://api.github.com/repos/${GH_REPO:-${GITHUB_REPOSITORY}}"
AUTH=(-H "Authorization: token ${GITHUB_TOKEN:?need GITHUB_TOKEN}" -H "Accept: application/octet-stream")
python3 - "$API" "$TAG" "$DEST" <<'PY'
import sys, json, os, urllib.request
api, tag, dest = sys.argv[1], sys.argv[2], sys.argv[3]
tok = os.environ['GITHUB_TOKEN']
req = urllib.request.Request(f"{api}/releases/tags/{tag}", headers={'Authorization': f'token {tok}'})
rel = json.load(urllib.request.urlopen(req))
for a in rel['assets']:
    out = os.path.join(dest, a['name'])
    if os.path.exists(out) and os.path.getsize(out) == a['size']:
        print('cached', a['name']); continue
    req = urllib.request.Request(a['url'], headers={'Authorization': f'token {tok}', 'Accept': 'application/octet-stream'})
    with urllib.request.urlopen(req) as r, open(out, 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
    print('downloaded', a['name'], a['size'])
PY
cd "$DEST" && sha256sum -c SHA256SUMS
