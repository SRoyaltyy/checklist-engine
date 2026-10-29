"""Fetch CBOE market-wide put/call ratios -> data-ext/mkt_pc_2020_26.parquet.

Block I201 (CBOE market-wide options) wiring for the world snapshot. Source:
CBOE daily market statistics CSV (cdn.cboe.com, no key). Put/call counts for
day D are published after the close of D, so the consumer must join strict
< D (same convention as mkt_wide VIX). Values are official counts and are
never revised.

Daily file layout (one file per calendar day that had trading):
  Expiration,Calls,Puts,Total,P/C Ratio
  ...                                     <- per-expiry rows
  Total,      <calls>, <puts>, <total>, <ratio>

Usage:
  python3 fetch/fetch_cboe.py probe                 # one request, print what CBOE returns
  python3 fetch/fetch_cboe.py fetch --out mkt_pc_2020_26.parquet
"""
import argparse, io, sys, time, urllib.request
import numpy as np
import pandas as pd

BASE = 'https://cdn.cboe.com/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv'
UA = {'User-Agent': 'checklist-engine-fetch/1.0'}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        return None
    except Exception:
        return None


def parse_day(raw):
    """-> (calls, puts, total, ratio) from the Total row, or None."""
    try:
        df = pd.read_csv(io.StringIO(raw.decode('utf-8', 'ignore')))
    except Exception:
        return None
    cols = {c.lower().strip(): c for c in df.columns}
    key_col = df.columns[0]
    total = df[df[key_col].astype(str).str.strip().str.lower() == 'total']
    if not len(total):
        return None
    row = total.iloc[0]
    def num(name):
        c = cols.get(name)
        if c is None:
            return np.nan
        return pd.to_numeric(row[c], errors='coerce')
    return num('calls'), num('puts'), num('total'), num('p/c ratio')


def probe():
    for ds in ('2024-03-15', '2022-06-15', '2020-06-15'):
        y, m, d = ds.split('-')
        url = BASE.format(y=y, m=int(m), d=int(d))
        raw = get(url)
        if raw is None:
            print(ds, 'NO RESPONSE (404 or blocked)')
            continue
        print(ds, 'OK', len(raw), 'bytes; head:')
        print('\n'.join(raw.decode('utf-8', 'ignore').splitlines()[:6]))
        parsed = parse_day(raw)
        print('parsed Total row:', parsed)


def fetch_all(out, start='2020-01-01', end=None, pace=0.15):
    end = end or pd.Timestamp.today().date()
    days = pd.bdate_range(start, end)          # CBOE files keyed by trade date; weekends 404
    rows = []
    t0 = time.time()
    for i, dt in enumerate(days):
        url = BASE.format(y=dt.year, m=dt.month, d=dt.day)
        raw = get(url)
        if raw is not None:
            p = parse_day(raw)
            if p is not None:
                rows.append((dt.date(), *p))
        if (i + 1) % 100 == 0:
            el = time.time() - t0
            print(f'{i+1}/{len(days)} days, {len(rows)} rows, {el:.0f}s', flush=True)
        time.sleep(pace)
    df = pd.DataFrame(rows, columns=['date', 'pc_calls', 'pc_puts', 'pc_total_n', 'pc_total'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    if df.empty:
        sys.exit('no put/call rows fetched -- endpoint changed?')
    df.to_parquet(out, index=False)
    print(f'wrote {out}: {len(df)} rows {df.date.min().date()}..{df.date.max().date()}, '
          f'nulls: {int(df.pc_total.isna().sum())}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['probe', 'fetch'])
    ap.add_argument('--out', default='mkt_pc_2020_26.parquet')
    a = ap.parse_args()
    probe() if a.cmd == 'probe' else fetch_all(a.out)
