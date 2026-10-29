"""Fetch CBOE market-wide put/call ratios -> data-ext/mkt_pc_2020_26.parquet.

Block I201 (CBOE market-wide options) wiring for the world snapshot. Keyless
CBOE endpoints (cdn.cboe.com). Put/call counts for day D are published after
the close of D, so the consumer must join strict < D (same convention as
mkt_wide VIX). Values are official counts and are never revised.

Primary source: the published put/call historical CSVs, one request total:
  https://cdn.cboe.com/resources/options/volume_and_open_interest/totalpc.csv
    columns: DATE, CALL VOLUME, PUT VOLUME, TOTAL VOLUME, P/C RATIO (total)
Fallback (probe-verified): per-day market_statistics files under one of the
CDN layouts below.

Usage:
  python3 fetch/fetch_cboe.py probe   # print HTTP status + head for every candidate
  python3 fetch/fetch_cboe.py fetch --out mkt_pc_2020_26.parquet
"""
import argparse, io, sys, time, urllib.error, urllib.request

import numpy as np
import pandas as pd

UA = {'User-Agent': 'checklist-engine-fetch/1.0'}

# One-shot historical CSVs (single request covers 2020..today).
HIST_CSV = {
    'totalpc-cdn': 'https://cdn.cboe.com/resources/options/volume_and_open_interest/totalpc.csv',
    'equitypc-cdn': 'https://cdn.cboe.com/resources/options/volume_and_open_interest/equitypc.csv',
    'indexpc-cdn': 'https://cdn.cboe.com/resources/options/volume_and_open_interest/indexpc.csv',
    # legacy www.cboe.com paths (historically hosted the same files)
    'totalpc-www': 'https://www.cboe.com/publish/ScheduledTask/MktData/datahouse/totalpc.csv',
    'totalpc-www2': 'https://www.cboe.com/us/options/market_statistics/daily/totalpc.csv',
}

# Per-day file layout candidates (first one that probes 200 wins):
#   {y}/{m:02d}/{d:02d}.csv  with Expiration,Calls,Puts,Total,P/C Ratio rows.
DAILY_PATTERNS = [
    'https://cdn.cboe.com/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv',
    'https://cdn.cboe.com/data/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv',
    'https://cdn.cboe.com/us/options/market_statistics/daily/{y}-{m:02d}-{d:02d}.csv',
    'https://www.cboe.com/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv',
]

# CBOE's CDN 403s plain-script UAs from datacenter IPs; probe a browser UA too.
UAS = [
    ('fetch', 'checklist-engine-fetch/1.0'),
    ('browser', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
]


def get(url, ua=None):
    req = urllib.request.Request(url, headers={'User-Agent': ua or UA['User-Agent']})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception:
        return None, b''


def parse_hist_csv(raw):
    """Parse the put/call historical CSV -> DataFrame[date, calls, puts, total_n, ratio]."""
    df = pd.read_csv(io.StringIO(raw.decode('utf-8', 'ignore')))
    cols = {c.lower().strip(): c for c in df.columns}
    date_c = df.columns[0]
    df = df.rename(columns={
        cols.get('call volume', ''): 'calls',
        cols.get('put volume', ''): 'puts',
        cols.get('total volume', ''): 'total_n',
        cols.get('p/c ratio', ''): 'ratio',
    })
    need = {'calls', 'puts', 'total_n', 'ratio'}
    if not need.issubset(df.columns):
        return None
    df['date'] = pd.to_datetime(df[date_c], errors='coerce', format='mixed')
    for c in ('calls', 'puts', 'total_n', 'ratio'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['date'])[['date', 'calls', 'puts', 'total_n', 'ratio']]
    return df.reset_index(drop=True)


def parse_day(raw):
    """-> (calls, puts, total, ratio) from a daily market-statistics file's Total row."""
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
    for ua_name, ua in UAS:
        print(f'--- UA={ua_name} ---')
        for name, url in HIST_CSV.items():
            st, raw = get(url, ua)
            print(f'{name}: HTTP {st}, {len(raw)} bytes')
            if raw:
                print('  head: ' + ' | '.join(raw.decode('utf-8', 'ignore').splitlines()[:3]))
        for pat in DAILY_PATTERNS:
            st, raw = get(pat.format(y=2024, m=3, d=15), ua)
            print(f'daily {pat}: HTTP {st}, {len(raw)} bytes')
            if raw:
                print('  head: ' + ' | '.join(raw.decode('utf-8', 'ignore').splitlines()[:6]))


def fetch_all(out, start='2020-01-01', end=None, pace=0.15):
    end = pd.Timestamp(end or pd.Timestamp.today().date())
    start = pd.Timestamp(start)

    # Fast path: single historical CSV.
    for ua_name, ua in UAS:
        for name, url in HIST_CSV.items():
            st, raw = get(url, ua)
            df = parse_hist_csv(raw) if raw else None
            if df is not None and len(df):
                print(f'historical CSV {name} (UA={ua_name}): HTTP {st}, {len(df)} parsed rows')
                df = df[(df.date >= start) & (df.date <= end)].reset_index(drop=True)
                if len(df) == 0:
                    continue
                df = df.rename(columns={'total_n': 'pc_total_n', 'ratio': 'pc_total',
                                        'calls': 'pc_calls', 'puts': 'pc_puts'})
                df.to_parquet(out, index=False)
                print(f'wrote {out}: {len(df)} rows {df.date.min().date()}..{df.date.max().date()}, '
                      f'nulls: {int(df.pc_total.isna().sum())}')
                return
    print('historical CSVs unavailable; falling back to per-day walk')

    # Fallback: find a working (UA, daily pattern) pair, then walk business days.
    pat = ua = None
    for ua_name, ua_c in UAS:
        for p in DAILY_PATTERNS:
            st, raw = get(p.format(y=2022, m=6, d=15), ua_c)
            if raw and parse_day(raw):
                pat, ua = p, ua_c
                print(f'daily pattern OK (UA={ua_name}):', p)
                break
        if pat:
            break
    if pat is None:
        sys.exit('no CBOE endpoint answered -- all candidates failed (see probe output)')

    days = pd.bdate_range(start, end)          # CBOE files keyed by trade date; weekends 404
    rows = []
    t0 = time.time()
    for i, dt in enumerate(days):
        st, raw = get(pat.format(y=dt.year, m=dt.month, d=dt.day), ua)
        if raw:
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
