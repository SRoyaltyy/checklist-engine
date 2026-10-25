"""Fetch FRED/ALFRED macro series with VINTAGES -> data-ext/fred_wide_2020_26.parquet.

Block I / I195 (0b FULL-DATA FIRST). Status: BLOCKED_SECRET until Cyrus adds the
FRED_API_KEY Actions secret -- this code is wired and ready; without the key it
exits 2 with a clear message (the calling workflow treats that as skip).

Point-in-time: ALFRED returns every (vintage_date, observation) pair. A value
is knowable on day D only if its vintage_date < D; among those, the latest
observation date wins. Series that are never revised (market rates) pass
through the same machinery harmlessly.

Output (long): series, obs_date, vintage_date, value.
Default series (v1): DGS10, T10Y2Y, DTB3, ICSA (weekly claims), UMCSENT (monthly).

Runner:  FRED_API_KEY=... python3 fetch/fetch_fred.py --out fred_wide_2020_26.parquet
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request
import pandas as pd

SERIES = ['DGS10', 'T10Y2Y', 'DTB3', 'ICSA', 'UMCSENT']


def alfred_observations(key, sid):
    qs = urllib.parse.urlencode({
        'series_id': sid, 'api_key': key, 'file_type': 'json',
        'realtime_start': '1900-01-01', 'realtime_end': '9999-12-31'})
    url = f'https://api.stlouisfed.org/fred/series/observations?{qs}'
    req = urllib.request.Request(url, headers={'User-Agent': 'checklist-engine/1.0'})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            out = []
            for o in d.get('observations', []):
                v = o.get('value')
                if v in (None, '.'):
                    continue
                out.append(dict(series=sid, obs_date=o['date'],
                                vintage_date=o['realtime_start'], value=float(v)))
            return out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (i + 1)); continue
            raise
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='fred_wide_2020_26.parquet')
    ap.add_argument('--series', default=','.join(SERIES))
    a = ap.parse_args()
    key = os.environ.get('FRED_API_KEY', '')
    if not key:
        sys.exit('BLOCKED_SECRET: FRED_API_KEY not set -- wire-only mode, fetch skipped')
    rows = []
    for sid in [s.strip() for s in a.series.split(',') if s.strip()]:
        got = alfred_observations(key, sid)
        rows.extend(got)
        print(sid, len(got), 'vintage observations', flush=True)
        time.sleep(1.5)
    if not rows:
        sys.exit('no observations fetched -- check key/quota')
    df = pd.DataFrame(rows)
    df = df[(df.obs_date >= '2018-01-01') & (df.obs_date <= '2026-12-31')]
    df.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(df)} rows, {df.series.nunique()} series')


if __name__ == '__main__':
    main()
