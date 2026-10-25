"""FRED/ALFRED macro fetch (wave 2, dictionary item I195). Point-in-time via ALFRED vintages:
each row keeps the vintage (realtime_start) it first became known, so a PIT join on day D uses
only vintages with realtime_start <= D. Free API, needs FRED_API_KEY secret.

Usage: FRED_API_KEY=... python3 ci/fetch_fred.py <out_dir> [series.csv]
series.csv: one FRED id per line (optional 'id,human name' columns). Default: a small starter set.
Output: <out_dir>/fred_<ID>.parquet with columns date, value, vintage; plus SHA256SUMS lines on stdout.
"""
import os, sys, json, time, hashlib, urllib.request, urllib.parse

BASE = 'https://api.stlouisfed.org/fred'
DEFAULT_SERIES = [   # starter set - War room to confirm/extend the final list (dictionary I195)
    ('VIXCLS', 'VIX close'),
    ('DGS10', '10y Treasury'),
    ('DGS2', '2y Treasury'),
    ('DTB3', '3m T-bill'),
    ('T10Y2Y', '10y-2y spread'),
    ('BAMLC0A0CM', 'IG credit spread'),
    ('BAMLH0A0HYM2', 'HY spread'),
    ('WALCL', 'Fed balance sheet'),
    ('RRPONTSYD', 'reverse repo'),
    ('SOFR', 'SOFR'),
]

def get(path, **params):
    key = os.environ.get('FRED_API_KEY')
    if not key:
        raise SystemExit('FRED_API_KEY not set (add repo secret, then dispatch data_fetch job=fred)')
    params['api_key'] = key; params['file_type'] = 'json'
    url = f'{BASE}/{path}?{urllib.parse.urlencode(params)}'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3: raise
            time.sleep(2 * (attempt + 1))

def fetch_series(sid, out_dir):
    """All ALFRED vintages from series start (vintage_date = realtime_start)."""
    obs = get('series/observations', series_id=sid, output_type=2,  # 2 = ALFRED vintage dates
              realtime_start='1776-07-04', realtime_end='9999-12-31',
              observation_start='1900-01-01', limit=100000)['observations']
    import pandas as pd
    df = pd.DataFrame(obs)[['realtime_start', 'date', 'value']]
    df.columns = ['vintage', 'date', 'value']
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(df['date']); df['vintage'] = pd.to_datetime(df['vintage'])
    df = df.sort_values(['date', 'vintage']).reset_index(drop=True)
    p = os.path.join(out_dir, f'fred_{sid}.parquet')
    df.to_parquet(p, index=False)
    time.sleep(0.34)   # FRED rate limit: ~30 calls/min with key
    return p, len(df)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'fred_out'
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 2:
        series = [tuple(l.strip().split(',')[:2]) for l in open(sys.argv[2]) if l.strip() and not l.startswith('#')]
    else:
        series = DEFAULT_SERIES
    rows = []
    for sid, name in series:
        try:
            p, n = fetch_series(sid, out)
            rows.append((os.path.basename(p), n, name, hashlib.sha256(open(p, 'rb').read()).hexdigest()))
            print('ok', sid, n, 'vintage rows')
        except Exception as e:
            rows.append((f'fred_{sid}.parquet', 0, name, f'ERROR {e}'))
            print('FAIL', sid, e)
    with open(os.path.join(out, 'SHA256SUMS'), 'w') as f:
        for name, n, _, sha in rows:
            if isinstance(sha, str) and len(sha) == 64:
                f.write(f'{sha}  {name}\n')
    print(json.dumps([dict(file=n, rows=c, name=nm, sha=s) for n, c, nm, s in rows], indent=1))

if __name__ == '__main__':
    main()
