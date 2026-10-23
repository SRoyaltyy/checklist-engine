"""Point-in-time market cap, split-consistent.
raw_close(t) = adj_close(t) * prod(num/den) over Yahoo splits dated AFTER t   (undo back-adjustment -> as-traded price)
shares(t)    = SEC shares (latest filed <= t) * prod(num/den) over splits dated in (end_of_count, t]   (count was taken before a split)
mcap(t) = raw_close(t) * shares(t). Split dates are corporate-action metadata, used only to put price and share count in the same units."""
import json, os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
S = pd.read_parquet(f'{D}/splits_yahoo.parquet')
add = []
for t in ['CYCN', 'VTAK']:
    for e in (json.load(open(f'{D}/yraw2_{t}.json'))['chart']['result'][0].get('events') or {}).get('splits', {}).values():
        add.append((t, pd.to_datetime(e['date'], unit='s').normalize(), e['numerator'], e['denominator']))
S = pd.concat([S, pd.DataFrame(add, columns=S.columns)]).drop_duplicates(); S['r'] = S.num / S.den
S.to_parquet(f'{D}/splits_yahoo_all.parquet')
SB = {k: g.sort_values('split_date') for k, g in S.groupby('ticker')}

def factor_after(tk, dates):
    """prod r over splits with date > d  (vector over dates)"""
    g = SB.get(tk); f = np.ones(len(dates))
    if g is None: return f
    for d, r in zip(g.split_date.values, g.r.values): f[dates < d] *= r
    return f
def factor_between(tk, start, dates):
    g = SB.get(tk); f = np.ones(len(dates))
    if g is None: return f
    for d, r in zip(g.split_date.values, g.r.values): f[(start < d) & (dates >= d)] *= r
    return f
def mcap_series(tk, dates, adj_close, sh):
    """sh: DataFrame of SEC rows (end, val, filed) for ticker, sorted by filed"""
    dates = np.asarray(dates, 'datetime64[ns]'); raw = adj_close * factor_after(tk, dates)
    if sh is None or not len(sh): return raw, np.full(len(dates), np.nan)
    i = np.searchsorted(sh.filed.values, dates, side='right') - 1; okk = i >= 0; i = np.maximum(i, 0)
    val = np.where(okk, sh.val.values[i], np.nan); end = np.where(okk, pd.to_datetime(sh.end).values[i], np.datetime64('NaT'))
    shares = val * factor_between(tk, end, dates)
    return raw, raw * shares
