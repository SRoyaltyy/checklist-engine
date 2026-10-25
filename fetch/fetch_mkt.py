"""Fetch market-wide daily series -> data-ext/mkt_wide_2020_26.parquet.

Block I178 (VIX level) wiring for the world snapshot (0b FULL-DATA FIRST).
Source: FRED fredgraph.csv?id=VIXCLS -- keyless public CSV endpoint (verified
2026-10-25), full history in one request. VIX is a market index: values are
never revised, so current-values CSV + strict < D shift in facets_world.py is
point-in-time safe (no ALFRED vintages needed for this series).

Output columns (all shifted < D by the consumer):
  date      trading/calendar date of the VIX observation
  vix       VIX close level
  vix_r5    5-observation pct change
  vix_d20   level / 20-obs SMA - 1

Runner:  python3 fetch/fetch_mkt.py --out mkt_wide_2020_26.parquet
"""
import argparse, io, sys, urllib.request
import numpy as np
import pandas as pd

FRED_VIX = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'checklist-engine-fetch/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='mkt_wide_2020_26.parquet')
    ap.add_argument('--start', default='2019-06-01')   # padding for 20d SMA at 2020-01-01
    ap.add_argument('--end', default='2026-12-31')
    a = ap.parse_args()

    raw = fetch(FRED_VIX).decode('utf-8')
    df = pd.read_csv(io.StringIO(raw))
    df.columns = ['date', 'vix']
    df['vix'] = pd.to_numeric(df['vix'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna().sort_values('date').reset_index(drop=True)
    df = df[(df.date >= a.start) & (df.date <= a.end)]
    if df.empty:
        sys.exit('no VIX rows fetched -- endpoint changed?')

    s = pd.Series(df.vix.to_numpy(float), index=df.date)
    df['vix_r5'] = s.pct_change(5).to_numpy()
    df['vix_d20'] = (s / s.rolling(20).mean() - 1).to_numpy()
    df = df[df.date >= '2020-01-01'].reset_index(drop=True)
    df.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(df)} rows {df.date.min().date()}..{df.date.max().date()}, '
          f'nulls: vix={int(df.vix.isna().sum())} r5={int(df.vix_r5.isna().sum())} d20={int(df.vix_d20.isna().sum())}')


if __name__ == '__main__':
    main()
