#!/usr/bin/env python3
"""Fetch dividends + splits for the universe via the Yahoo chart events API (Block J).

Source: query1.finance.yahoo.com/v8/finance/chart/<T>?range=max&interval=1d&events=div,splits
(keyless; proven in checklist_brainstorm/fetch_tests). Splits are already baked
into the bars (split-adjusted backwards); this file carries the EVENT dates so
questions like "split in last N days" / "dividend in last N days" are answerable
point-in-time (event date < D).

Usage: fetch_divsplits.py --shard N --shards 8 --universe universe.parquet --out dir
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--shards', type=int, default=8)
    ap.add_argument('--universe', required=True); ap.add_argument('--out', default='divsplits_out')
    a = ap.parse_args()

    import pandas as pd
    u = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(u.ticker.unique())
    mine = tickers[a.shard::a.shards]
    print(f'divsplits shard {a.shard}/{a.shards}: {len(mine)} tickers', flush=True)

    rows, fail = [], []
    for i, t in enumerate(mine):
        url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(t)}'
               f'?range=max&interval=1d&events=div%2Csplits')
        blob = get(url)
        if blob is None:
            fail.append((t, 'no-chart')); continue
        try:
            res = json.loads(blob)['chart']['result'][0]
        except Exception:
            fail.append((t, 'bad-json')); continue
        ev = (res.get('events') or {})
        for d in (ev.get('dividends') or {}).values():
            rows.append((t, 'div', d.get('date'), d.get('amount'), None, None))
        for d in (ev.get('splits') or {}).values():
            num, den = d.get('numerator'), d.get('denominator')
            ratio = (num / den) if num and den else None
            rows.append((t, 'split', d.get('date'), ratio, num, den))
        time.sleep(0.25)          # stay under Yahoo rate limits
        if i % 300 == 299:
            print(f'{i+1}/{len(mine)} tickers, {len(rows)} rows', flush=True)
    os.makedirs(a.out, exist_ok=True)
    df = pd.DataFrame(rows, columns=['ticker', 'kind', 'epoch', 'value', 'numerator', 'denominator'])
    if len(df):
        df['date'] = pd.to_datetime(df.epoch, unit='s', utc=True).dt.tz_convert('America/New_York').dt.date.astype(str)
    else:
        df['date'] = []
    fn = os.path.join(a.out, f'divsplits_shard_{a.shard:03d}.parquet')
    df.drop(columns=['epoch']).to_parquet(fn, index=False)
    meta = {'shard': a.shard, 'shards': a.shards, 'tickers': len(mine), 'rows': len(df),
            'fail_count': len(fail), 'fail_sample': fail[:20],
            'pit': 'use only rows with event date < D; splits already in bars'}
    json.dump(meta, open(fn.replace('.parquet', '.json'), 'w'), indent=1)
    print('wrote', fn, len(df), 'rows,', len(fail), 'failures')

if __name__ == '__main__':
    import urllib.parse
    main()
