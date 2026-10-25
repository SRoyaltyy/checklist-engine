#!/usr/bin/env python3
"""Fetch historical analyst actions per ticker (Block L, METHODOLOGY 0b).

Source: Yahoo quoteSummary upgradeDowngradeHistory module (the endpoint behind
yfinance Ticker.upgrades_downgrades; dated from/to grade rows per firm).
Point-in-time key = the action date carried in each row; the world build joins
with the usual strict date < D discipline. Keyless endpoint, declared UA,
conservative pacing for Yahoo rate limits.

Output: analyst_actions_ shard parquets with columns
  ticker, date, firm, from_grade, to_grade
Grades stay as raw short strings (buysell/perform/weight families); mapping to
fixed answer sets happens at question time (groups 034+), one frozen mapping.

Usage: fetch_analyst.py --shard N --shards 8 --universe universe.parquet --out dir
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

UA = {'User-Agent': 'Mozilla/5.0 (checklist-engine; https://github.com/SRoyaltyy/checklist-engine)'}

def get(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 400, 422):
                return None                     # ticker unknown to Yahoo
            if e.code == 429:
                time.sleep(8 * (k + 1)); continue
            time.sleep(3 * (k + 1))
        except Exception:
            time.sleep(3 * (k + 1))
    return None

def fetch_ticker(tk):
    url = (f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{tk}'
           f'?modules=upgradeDowngradeHistory')
    blob = get(url)
    if not blob:
        return []
    try:
        d = json.loads(blob)
        hist = (d.get('quoteSummary', {}).get('result') or [{}])[0] \
            .get('upgradeDowngradeHistory', {}).get('history') or []
    except Exception:
        return []
    rows = []
    for h in hist:
        try:
            ts = h.get('epochGradeDate')
            if not ts:
                continue
            rows.append((tk, time.strftime('%Y-%m-%d', time.gmtime(int(ts))),
                         str(h.get('firm') or ''), str(h.get('fromGrade') or ''),
                         str(h.get('toGrade') or '')))
        except Exception:
            continue
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--shards', type=int, default=8)
    ap.add_argument('--universe', required=True); ap.add_argument('--out', default='analyst_out')
    a = ap.parse_args()

    import pandas as pd
    u = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(u.ticker.unique())
    mine = tickers[a.shard::a.shards]
    os.makedirs(a.out, exist_ok=True)
    rows, fails = [], []
    for i, tk in enumerate(mine):
        r = fetch_ticker(tk)
        if r:
            rows.extend(r)
        else:
            fails.append(tk)
        if i % 50 == 49:
            print(f'{i+1}/{len(mine)} tickers, {len(rows)} actions, {len(fails)} empty/failed', flush=True)
        time.sleep(0.35)                        # conservative: ~3 req/s across 8 shard legs
    df = pd.DataFrame(rows, columns=['ticker', 'date', 'firm', 'from_grade', 'to_grade'])
    fn = os.path.join(a.out, f'analyst_actions_{a.shard:03d}.parquet')
    df.to_parquet(fn, index=False)
    json.dump({'shard': a.shard, 'shards': a.shards, 'tickers': len(mine),
               'actions': int(len(df)), 'empty_or_failed': len(fails),
               'failed_sample': fails[:20]},
              open(os.path.join(a.out, f'analyst_actions_{a.shard:03d}.json'), 'w'), indent=1)
    print('wrote', fn, len(df), 'actions;', len(fails), 'tickers empty/failed', flush=True)

if __name__ == '__main__':
    main()
