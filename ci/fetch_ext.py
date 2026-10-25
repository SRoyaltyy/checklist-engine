#!/usr/bin/env python3
"""Fetch the data-ext release assets needed by the groups 034+ event facets (halts, FINRA short interest)
into the CHECKLIST_DATA_DIR folder. Verifies each downloaded file against box_uploads_SHA256SUMS.txt when
that file was listed there. Missing release / network failure exits non-zero so callers can warn-and-continue
(event columns then answer blank, which is a safe degradation)."""
import os, sys, json, hashlib, urllib.request

dest = sys.argv[1]
WANT = ['nasdaq_halts_2020_2026.parquet'] + [f'finra_si_{y}.parquet' for y in range(2020, 2027)]
api = f"https://api.github.com/repos/{os.environ.get('GH_REPO', os.environ.get('GITHUB_REPOSITORY', 'SRoyaltyy/checklist-engine'))}"
tok = os.environ['GITHUB_TOKEN']

def get(url, accept=None):
    h = {'Authorization': f'token {tok}'}
    if accept: h['Accept'] = accept
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120)

os.makedirs(dest, exist_ok=True)
try:
    rel = json.load(get(f'{api}/releases/tags/data-ext-2020-26-v1'))
except Exception as e:
    print(f'fetch_ext: release lookup failed: {e}'); sys.exit(1)
assets = {a['name']: a for a in rel.get('assets', [])}

sums = {}
try:
    for line in get(assets['box_uploads_SHA256SUMS.txt']['url'], 'application/octet-stream').read().decode().splitlines():
        p = line.split()
        if len(p) >= 2: sums[p[-1].lstrip('*')] = p[0]
except Exception as e:
    print(f'fetch_ext: checksum file unavailable ({e}); skipping verification')

rc = 0
for name in WANT:
    a = assets.get(name)
    if a is None:
        print(f'fetch_ext: {name} NOT on release'); rc = 1; continue
    out = os.path.join(dest, name)
    if os.path.exists(out) and os.path.getsize(out) == a['size']:
        print('cached', name)
    else:
        with get(a['url'], 'application/octet-stream') as r, open(out, 'wb') as f:
            while True:
                b = r.read(1 << 20)
                if not b: break
                f.write(b)
        print('downloaded', name, a['size'])
    want_sha = sums.get(name)
    if want_sha:
        got = hashlib.sha256(open(out, 'rb').read()).hexdigest()
        if got != want_sha:
            print(f'fetch_ext: SHA256 MISMATCH {name}'); rc = 1
sys.exit(rc)
