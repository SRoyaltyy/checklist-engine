"""Data-integrity check. Uses Yahoo split events + monthly split-adjusted closes as the outside reference.
Outputs: splits_yahoo.parquet, price_check.parquet (per ticker), quarantine.csv."""
import json, os, numpy as np, pandas as pd
sp, mo, st = [], [], {}
for f in os.listdir('yraw'):
    t = f[:-5]; d = json.load(open('yraw/' + f))
    try: r = d['chart']['result'][0]
    except Exception: st[t] = 'no_yahoo'; continue
    for e in (r.get('events') or {}).get('splits', {}).values():
        sp.append((t, pd.to_datetime(e['date'], unit='s').normalize(), e['numerator'], e['denominator']))
    ts = r.get('timestamp') or []; q = r['indicators']['quote'][0].get('close') or []
    for a, b in zip(ts, q):
        if b is not None: mo.append((t, pd.to_datetime(a, unit='s').to_period('M'), b))
    st[t] = 'ok'
S = pd.DataFrame(sp, columns=['ticker', 'split_date', 'num', 'den']); S.to_parquet('splits_yahoo.parquet')
M = pd.DataFrame(mo, columns=['ticker', 'month', 'y_close'])
u = pd.read_parquet('/workspace/pricehist/universe_2020_survivors.parquet', columns=['ticker', 'date', 'close'])
u['ticker'] = u.ticker.astype(str); u['month'] = u.date.dt.to_period('M')
ours = u.sort_values('date').groupby(['ticker', 'month']).close.last().reset_index()
J = ours.merge(M, on=['ticker', 'month'])
J = J[J.month <= pd.Period('2024-12', 'M')]          # only the period the engine uses
J['ratio'] = J.close / J.y_close
g = J.groupby('ticker').ratio
P = pd.DataFrame({'months': g.size(), 'med_ratio': g.median(), 'share_bad': g.apply(lambda r: ((r > 1.15) | (r < 1/1.15)).mean())})
P['yahoo'] = pd.Series(st)
P = P.reindex(sorted(set(u.ticker))); P['yahoo'] = pd.Series(st).reindex(P.index).fillna('no_yahoo')
P['status'] = np.where(P.months.isna(), 'no_reference', np.where(P.share_bad > .2, 'MISMATCH', np.where(P.share_bad > 0.05, 'partial_mismatch', 'ok')))
P.to_parquet('price_check.parquet')
print(P.status.value_counts().to_dict())
print(P[P.status == 'MISMATCH'].sort_values('share_bad', ascending=False).head(25).round(3).to_string())
print('MVIS', P.loc['MVIS'].to_dict(), 'TSLA', P.loc['TSLA'].to_dict())
print('splits rows', len(S), 'tickers with split after 2024', S[S.split_date > '2024-12-31'].ticker.nunique())
