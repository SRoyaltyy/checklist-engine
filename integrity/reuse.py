import json, os, pandas as pd, numpy as np
u = pd.read_parquet('/workspace/pricehist/universe_2020_survivors.parquet', columns=['ticker', 'date'])
u['ticker'] = u.ticker.astype(str)
f = u.groupby('ticker').date.agg(first='min', last='max', n='size')
f['n_le2024'] = u[u.date <= '2024-12-31'].groupby('ticker').size().reindex(f.index).fillna(0).astype(int)
ft, ty = {}, {}
for t in f.index:
    try: m = json.load(open(f'yraw/{t}.json'))['chart']['result'][0]['meta']
    except Exception: continue
    ft[t] = pd.to_datetime(m.get('firstTradeDate'), unit='s') if m.get('firstTradeDate') else pd.NaT; ty[t] = m.get('instrumentType')
f['y_first_trade'] = pd.Series(ft); f['y_type'] = pd.Series(ty)
f['reuse'] = (f.y_first_trade - f['first']).dt.days > 30
P = pd.read_parquet('price_check.parquet'); f = f.join(P[['months', 'med_ratio', 'share_bad', 'status']])
f.to_parquet('ticker_integrity.parquet')
r = f[f.reuse & (f.n_le2024 > 0)]
print('ticker reuse (our rows begin >30d before Yahoo first trade), with 2020-24 rows:', len(r))
print(r.y_type.value_counts().to_dict())
print(r.sort_values('n_le2024', ascending=False).head(12)[['first', 'y_first_trade', 'n_le2024', 'y_type']].to_string())
print('no_reference & not reuse & n_le2024>0:', ((f.status == 'no_reference') & ~f.reuse & (f.n_le2024 > 0)).sum())
