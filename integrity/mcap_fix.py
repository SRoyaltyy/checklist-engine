"""Point-in-time market cap, split-consistent.
raw_close(t) = adj_close(t) * prod(num/den) over Yahoo splits dated AFTER t   (undo back-adjustment -> as-traded price)
shares(t)    = SEC shares (latest filed <= t) * prod(num/den) over splits dated in (end_of_count, t]   (count was taken before a split)
mcap(t) = raw_close(t) * shares(t). Split dates are corporate-action metadata, used only to put price and share count in the same units.

Port adaptation (2026-11-24, kimi/step-a-engine-port): the splits table loads LAZILY on
first use (was: module-level import that also rewrote splits_yahoo_all.parquet next to the
source). The binary `splits_yahoo.parquet` is not committed on main (binary files cannot
ride the file-push channel); instead `splits_yahoo.parquet.b64` (base64 of the exact bytes
from kimi/dictionary-fixes @ 1761ab64) ships in-repo and is decoded in memory. Results are
byte-identical to the orphan-branch behaviour. If neither file exists, the table starts
empty (no split adjustments) rather than crashing the engine import.
"""
import base64, io, json, os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
SB = None  # built lazily by _load_splits()

def _load_splits():
    global SB
    if SB is not None:
        return SB
    pq, b64 = f'{D}/splits_yahoo.parquet', f'{D}/splits_yahoo.parquet.b64'
    cols = ['ticker', 'split_date', 'num', 'den']
    if os.path.exists(pq):
        S = pd.read_parquet(pq)
    elif os.path.exists(b64):
        S = pd.read_parquet(io.BytesIO(base64.b64decode(open(b64, 'rb').read())))
    else:
        S = pd.DataFrame(columns=cols)
    add = []
    for t in ['CYCN', 'VTAK']:
        jp = f'{D}/yraw2_{t}.json'
        if not os.path.exists(jp):
            continue
        for e in (json.load(open(jp))['chart']['result'][0].get('events') or {}).get('splits', {}).values():
            add.append((t, pd.to_datetime(e['date'], unit='s').normalize(), e['numerator'], e['denominator']))
    if add:
        S = pd.concat([S, pd.DataFrame(add, columns=S.columns)])
    S = S.drop_duplicates(); S['r'] = S.num / S.den
    SB = {k: g.sort_values('split_date') for k, g in S.groupby('ticker')}
    return SB

def factor_after(tk, dates):
    """prod r over splits with date > d  (vector over dates)"""
    g = _load_splits().get(tk); f = np.ones(len(dates))
    if g is None: return f
    for d, r in zip(g.split_date.values, g.r.values): f[dates < d] *= r
    return f
def factor_between(tk, start, dates):
    g = _load_splits().get(tk); f = np.ones(len(dates))
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
