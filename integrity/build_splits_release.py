"""Build splits_yahoo.parquet from the yraw/ Yahoo chart cache (fetch_yahoo_release.py output).
One row per split event: ticker, split_date, num, den. Dated corporate-action metadata only."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

D = os.path.dirname(os.path.abspath(__file__))

def one(f):
    t = f[:-5]
    try:
        d = json.load(open(f'{D}/yraw/{f}'))
        r = (d.get('chart') or {}).get('result')
        if not r:
            return t, []
        ev = (r[0].get('events') or {}).get('splits') or {}
        return t, [(t, pd.to_datetime(e['date'], unit='s').normalize(),
                    float(e['numerator']), float(e['denominator'])) for e in ev.values()]
    except Exception:
        return t, None

files = [f for f in sorted(os.listdir(f'{D}/yraw')) if f.endswith('.json')]
rows, bad = [], 0
with ThreadPoolExecutor(24) as ex:
    for t, r in ex.map(one, files):
        if r is None:
            bad += 1
        else:
            rows.extend(r)
S = pd.DataFrame(rows, columns=['ticker', 'split_date', 'num', 'den'])
S = S.drop_duplicates().sort_values(['ticker', 'split_date']).reset_index(drop=True)
out = f'{D}/splits_yahoo.parquet'
S.to_parquet(out, index=False)
print(f'tickers with splits: {S.ticker.nunique()}, rows: {len(S)}, unreadable files: {bad}')
print(S.tail(5).to_string())
