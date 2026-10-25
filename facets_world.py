"""World snapshot builder (METHODOLOGY 0b 2026-10-25 12:30 HKT, world-snapshot order).

Builds a point-in-time per-ticker per-day column store: `world-2020-26-v1`.
Discipline: every column at day D uses only data with available_from_date < D.
Prices/indicators go up to the D-1 close (shift-by-one convention, same as the
engine: questions for day D read snapshot row D, which contains nothing from D).

Block A: full TA-Lib function set + all 61 candle patterns (auto-discovered from
the installed TA-Lib, OHLCV-fed only; anything needing other inputs is skipped and
listed in the coverage table).
Block K: market breadth (NH-NL / advance-decline / %%>200d) from breadth_2020_24.

Output: shard parquets world_shard_NNN.parquet keyed by (ticker, date), float32
for indicators, int8 for candle patterns (-100/0/100). A JSON sidecar per shard
lists the columns and provenance. Not a question module: groups 034+ read these
columns into yes/no / fixed buckets later.

Usage:
  python3 facets_world.py build --shard 0 --shards 8 --out world_out
  python3 facets_world.py coverage            # print TA-Lib coverage table
"""
import os, sys, json, argparse, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', '/nonexistent')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import talib
from talib import abstract
from datapaths import D

END = os.environ.get('WORLD_END', '2026-12-31')   # bars file decides the real end

# ---------------- TA-Lib auto-discovery (Block A) ----------------
def _feed(name):
    """Call TA-Lib function `name` on (o,h,l,c,v); return output array(s) or None if
    it needs inputs we don't provide. price-like inputs get close, volume gets v."""
    try:
        f = abstract.Function(name)
        need = f.input_names
        if isinstance(need, str): need = [need]
        d = {}
        for inp in need:
            k = inp.lower()
            if k in ('open',): d[inp] = None
            elif k in ('high',): d[inp] = None
            elif k in ('low',): d[inp] = None
            elif k in ('close', 'price'): d[inp] = None
            elif 'volume' in k: d[inp] = None
            elif 'openinterest' in k.replace('_', '').replace(' ', ''): return None, f'needs {inp}'
            else: return None, f'needs {inp}'
        return d, None
    except Exception as e:
        return None, f'{type(e).__name__}'

def discover():
    """Split all TA-Lib functions into candle patterns (int8) and indicators (float32),
    keyed by how they consume OHLCV. Returns {name: (kind, feed_map)}."""
    groups = talib.get_function_groups()
    cands = groups.get('Pattern Recognition', [])
    out = {}
    for name in talib.get_functions():
        kind = 'pattern' if name in cands else 'indicator'
        feed, why = _feed(name)
        if feed is not None:
            out[name] = (kind, feed)
    return out

COVERAGE_NOTE = None

def compute_talib(o, h, l, c, v, funcs):
    """Compute every discovered function for one ticker. Returns dict name -> array.
    All arrays are shifted by one bar: value at index t uses bars <= t-1."""
    feed = {'open': o, 'high': h, 'low': l, 'close': c, 'price': c, 'volume': v}
    out = {}
    for name, (kind, need) in funcs.items():
        try:
            f = abstract.Function(name)
            d = {inp: feed[inp.lower()] if inp.lower() in feed else feed['price'] for inp in need} \
                if isinstance(need, list) else {need: feed[str(need).lower()]}
            r = f(d)
            if isinstance(r, tuple): r = r[0]
            a = np.asarray(r, dtype=np.float64)
            if kind == 'pattern':
                out[name] = np.where(np.isnan(a), 0, a / 100).astype(np.float32)   # -1/0/+1
            else:
                out[name] = a.astype(np.float32)
        except Exception:
            continue
    return out

# ---------------- build ----------------
def load_bars(tickers=None):
    p = D('/workspace/updown/bars_all.parquet')
    f = [('date', '<=', END)]
    if tickers: f.append(('ticker', 'in', tickers))
    return pd.read_parquet(p, filters=f)

def main():
    global COVERAGE_NOTE
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'coverage'])
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--shards', type=int, default=8)
    ap.add_argument('--out', default='world_out'); ap.add_argument('--tickers', default=None)
    a = ap.parse_args()
    funcs = discover()
    n_pat = sum(1 for k in funcs if funcs[k][0] == 'pattern')
    if a.cmd == 'coverage':
        for name, (kind, _) in sorted(funcs.items()): print(kind, name)
        print(f'coverage: {len(funcs)} functions ({n_pat} patterns) of {len(talib.get_functions())} total')
        return
    print(f'world build shard {a.shard}/{a.shards}: {len(funcs)} TA-Lib functions ({n_pat} patterns)', flush=True)

    u = pd.read_parquet(D('/workspace/pricehist/universe_2020_survivors.parquet'), columns=['ticker', 'date'])
    tickers = sorted(u.ticker.unique())
    if a.tickers: tickers = [t for t in a.tickers.split(',') if t in set(tickers)]
    mine = tickers[a.shard::a.shards]
    print('tickers in shard:', len(mine), flush=True)

    br = D('/workspace/updown/breadth_2020_24.parquet')
    breadth = pd.read_parquet(br) if os.path.exists(br) else None
    if breadth is not None: print('breadth cols:', list(breadth.columns), flush=True)

    bars = load_bars(set(mine))
    os.makedirs(a.out, exist_ok=True)
    if breadth is not None:
        breadth = breadth.copy()
        breadth['date'] = pd.to_datetime(breadth['date'])
        breadth = breadth.sort_values('date')
        bcols = [c for c in breadth.columns if c != 'date']
    else:
        bcols = []
    parts, meta = [], {'talib_funcs': sorted(funcs), 'shift': 'value at D uses bars <= D-1',
                       'shard': a.shard, 'shards': a.shards, 'breadth_cols': bcols}
    for i, (tk, d) in enumerate(bars.groupby('ticker', sort=False)):
        d = d.sort_values('date')
        if len(d) < 30: continue
        o = d.open.to_numpy(float); h = d.high.to_numpy(float); l = d.low.to_numpy(float)
        c = d.close.to_numpy(float); v = d.volume.to_numpy(float)
        cols = compute_talib(o, h, l, c, v, funcs)
        df = pd.DataFrame({'ticker': tk, 'date': d.date.to_numpy()})
        for k, arr in cols.items():
            df[k] = np.r_[np.nan, arr[:-1]]          # shift-by-one: D sees bars <= D-1
        if bcols:
            key = pd.to_datetime(df['date']) - pd.Timedelta(days=1)   # strict: breadth date < D
            m = pd.merge_asof(pd.DataFrame({'date': key}).sort_values('date'),
                              breadth, on='date', direction='backward')
            for bc in bcols:
                df[bc] = m[bc].to_numpy(dtype=np.float32)
        parts.append(df)
        if i % 200 == 199: print(f'{i+1} tickers', flush=True)
    if parts:
        out = pd.concat(parts, ignore_index=True)
        fn = os.path.join(a.out, f'world_shard_{a.shard:03d}.parquet')
        out.to_parquet(fn, index=False)
        meta['rows'] = int(len(out)); meta['cols'] = int(out.shape[1]); meta['tickers'] = int(out.ticker.nunique())
        json.dump(meta, open(fn.replace('.parquet', '.json'), 'w'), indent=1)
        print('wrote', fn, len(out), 'rows x', out.shape[1], 'cols')
    else:
        print('no data for shard', a.shard)

if __name__ == '__main__':
    main()
