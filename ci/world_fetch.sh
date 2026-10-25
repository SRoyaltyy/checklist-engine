#!/usr/bin/env bash
# Fetch only the inputs facets_world.py needs from release data-2020-24-v1. Usage: world_fetch.sh <dest>
set -euo pipefail
DEST="$1"; mkdir -p "$DEST"
API="https://api.github.com/repos/${GH_REPO:-${GITHUB_REPOSITORY}}"
TAG="data-2020-24-v1"
FILES=(bars_all_le2024.parquet universe_2020_survivors_le2024.parquet breadth_2020_24.parquet etf_2015_le2024.parquet)
python3 - "$API" "$TAG" "$DEST" <<'PY'
import sys, json, os, urllib.request
api, tag, dest = sys.argv[1], sys.argv[2], sys.argv[3]
tok = os.environ['GITHUB_TOKEN']
want = {'bars_all_le2024.parquet', 'universe_2020_survivors_le2024.parquet', 'breadth_2020_24.parquet',
        'etf_2015_le2024.parquet', 'nasdaq_earn_2020-24.tar', 'SHA256SUMS'}
req = urllib.request.Request(f"{api}/releases/tags/{tag}", headers={'Authorization': f'token {tok}'})
rel = json.load(urllib.request.urlopen(req))
for a in rel['assets']:
    if a['name'] not in want:
        continue
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
cd "$DEST"
grep -E "nasdaq_earn_2020-24.tar|bars_all_le2024\.parquet|universe_2020_survivors_le2024\.parquet|breadth_2020_24\.parquet|etf_2015_le2024\.parquet" SHA256SUMS > SUBSET_SUMS
sha256sum -c SUBSET_SUMS
# earnings calendar lives inside the tar; unpack it next to the other inputs
if [ -f nasdaq_earn_2020-24.tar ]; then
  tar xf nasdaq_earn_2020-24.tar
  echo "earnings calendars:"; ls data/earnings/ | head -8
fi

# ---- data-ext-2020-26-v1: box-only blocks (FINRA SI/short volume, halts, Reg SHO) ----
mkdir -p "$DEST/data-ext"
API2="https://api.github.com/repos/${GH_REPO:-${GITHUB_REPOSITORY}}"
TAG2="data-ext-2020-26-v1"
python3 - "$API2" "$TAG2" "$DEST" <<'PY'
import sys, json, os, urllib.request
api, tag, dest = sys.argv[1], sys.argv[2], sys.argv[3]
tok = os.environ['GITHUB_TOKEN']
want = {f'finra_si_{y}.parquet' for y in range(2020, 2027)} | \
       {f'finra_shvol_{y}.parquet' for y in range(2020, 2027)} | \
       {'nasdaq_halts_2020_2026.parquet', 'nasdaq_regsho_threshold_2020_2026.parquet',
        'box_uploads_SHA256SUMS.txt'}
req = urllib.request.Request(f"{api}/releases/tags/{tag}", headers={'Authorization': f'token {tok}'})
rel = json.load(urllib.request.urlopen(req))
for a in rel['assets']:
    if a['name'] not in want and not a['name'].startswith(('xbrl_shard_', 'divsplits_shard_')):
        continue
    out = os.path.join(dest, 'data-ext', a['name'])
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
cd "$DEST/data-ext"
# verify only what we actually download (nb tar intentionally skipped)
grep -v '^.*  nb_nbx_' box_uploads_SHA256SUMS.txt > SUBSET_SUMS
sha256sum -c SUBSET_SUMS
echo "data-ext files:"; ls

# ---- market-wide daily series (I178 VIX) + Form4 counts (I187): small parquets ----
python3 - "$API2" "$TAG2" "$DEST" <<'PY'
import sys, json, os, urllib.request
api, tag, dest = sys.argv[1], sys.argv[2], sys.argv[3]
tok = os.environ['GITHUB_TOKEN']
want = {'mkt_wide_2020_26.parquet', 'form4_counts_2020_26.parquet', 'xbrl_fundamentals_2020_26.parquet',
        'analyst_actions_2020_26.parquet', 'gdelt_counts_2020_26.parquet', 'f13_hits_2020_26.parquet', 'fred_wide_2020_26.parquet'}
req = urllib.request.Request(f"{api}/releases/tags/{tag}", headers={'Authorization': f'token {tok}'})
rel = json.load(urllib.request.urlopen(req))
for a in rel['assets']:
    if a['name'] not in want and not a['name'].startswith(('xbrl_shard_', 'divsplits_shard_')):
        continue
    out = os.path.join(dest, 'data-ext', a['name'])
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
