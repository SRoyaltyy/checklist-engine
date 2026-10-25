#!/usr/bin/env python3
"""Fetch CBOE market-wide options series (Block N market-wide part, METHODOLOGY 0b).

Keyless CSV endpoints on cdn.cboe.com. These are index/market aggregates (not
single-stock), so they join the world snapshot by date with the usual
date < D discipline handled at join time.

Outputs one combined parquet (series, date, value) + the raw CSVs.
"""
import os, json, argparse, urllib.request, urllib.error

SERIES = {
    'pcratio_all': 'https://cdn.cboe.com/resources/pcratio/pcratio_all.csv',
    'VIX': 'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv',
    'VVIX': 'https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv',
}

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            time.sleep(2 * (k + 1)) if False else None
            import time; time.sleep(2 * (k + 1))
        except Exception:
            import time; time.sleep(2 * (k + 1))
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='cboe_out')
    a = ap.parse_args()
    import pandas as pd, io
    os.makedirs(a.out, exist_ok=True)
    frames, got = [], []
    for name, url in SERIES.items():
        blob = get(url)
        if blob is None:
            print('FAILED', name, url); continue
        open(os.path.join(a.out, f'{name}.csv'), 'wb').write(blob)
        try:
            df = pd.read_csv(io.BytesIO(blob))
        except Exception as e:
            print('parse fail', name, e); continue
        df.columns = [c.strip() for c in df.columns]
        dcol = next((c for c in df.columns if 'date' in c.lower()), None)
        if dcol is None:
            print('no date col', name, list(df.columns)); continue
        df = df.rename(columns={dcol: 'date'})
        df['date'] = pd.to_datetime(df.date, errors='coerce').dt.strftime('%Y-%m-%d')
        df = df.dropna(subset=['date'])
        long = df.melt(id_vars=['date'], var_name='field', value_name='value')
        long['series'] = name
        frames.append(long)
        got.append((name, len(df)))
        print('got', name, len(df), 'rows, cols:', list(df.columns)[:8])
    if frames:
        out = pd.concat(frames, ignore_index=True)
        fn = os.path.join(a.out, 'cboe_market_wide.parquet')
        out.to_parquet(fn, index=False)
        json.dump({'series': got, 'pit': 'join with date < D'},
                  open(os.path.join(a.out, 'cboe_market_wide.json'), 'w'), indent=1)
        print('wrote', fn, len(out), 'rows')

if __name__ == '__main__':
    main()
