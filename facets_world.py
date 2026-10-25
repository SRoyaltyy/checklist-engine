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

# ---------------- Block B: sector/style ETF overlays ----------------
def etf_wide():
    """All 14 ETFs (SPY, QQQ, IWM, 11 SPDRs) as wide daily columns.
    Every column is shifted by one ETF bar: value labelled D uses the ETF close
    of its last trading day <= D-1, then joins by merge_asof backward, so a
    stock-day D never sees ETF data from D itself. Survivor/label bias: the
    11 SPDR set uses today's sector definitions (flagged in METHODOLOGY)."""
    p = D('/workspace/etf/etf_2015.parquet')
    if not os.path.exists(p):
        return None
    e = pd.read_parquet(p)
    e['date'] = pd.to_datetime(e['date'])
    parts = {}
    for tk, d in e.groupby('ticker'):
        d = d.sort_values('date')
        c = d.close.to_numpy(float)
        s = pd.Series(c)
        cols = {
            f'etf_{tk}_c': c,
            f'etf_{tk}_r1': s.pct_change(1).to_numpy(),
            f'etf_{tk}_r5': s.pct_change(5).to_numpy(),
            f'etf_{tk}_r20': s.pct_change(20).to_numpy(),
            f'etf_{tk}_d50': (s / s.rolling(50).mean() - 1).to_numpy(),
            f'etf_{tk}_d200': (s / s.rolling(200).mean() - 1).to_numpy(),
        }
        dd = pd.DataFrame(cols)
        dd['date'] = d.date.to_numpy()
        parts[tk] = dd
    wide = None
    for tk, dd in parts.items():
        wide = dd if wide is None else pd.merge(wide, dd, on='date', how='outer')
    wide = wide.sort_values('date').reset_index(drop=True)
    val_cols = [c for c in wide.columns if c != 'date']
    wide[val_cols] = wide[val_cols].shift(1)          # D sees the prior ETF bar
    return wide.dropna(subset=val_cols[:1]).sort_values('date')

# ---------------- Block D: earnings calendar ----------------
def load_earnings(tickers):
    """Nasdaq earnings calendars 2020-24 (release nasdaq_earn_2020-24.tar ->
    data/earnings/nasdaq_calendar_*.parquet). Point-in-time: only rows with
    report_date < D are used (strict; an AMC report on D-1 is in, a BMO report
    on D itself is out, keeping one convention for every name)."""
    base = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data', 'earnings')
    if not os.path.isdir(base):
        return None
    fs = [os.path.join(base, f) for f in sorted(os.listdir(base)) if f.startswith('nasdaq_calendar_') and f.endswith('.parquet')]
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f, columns=['symbol', 'report_date', 'time_label',
                                                'surprise_pct_fill', 'eps_delta']) for f in fs], ignore_index=True)
    df = df[df.symbol.isin(tickers)]
    df['report_date'] = pd.to_datetime(df['report_date'])
    df = df.sort_values('report_date').reset_index(drop=True)
    df['amc'] = df.time_label.astype(str).str.upper().str.contains('AMC').astype(np.float32)
    return df

def earn_for(dates, edf):
    """Earnings columns for one ticker's sorted dates (as strings). Uses only
    reports strictly before each date."""
    if edf is None or len(edf) == 0:
        return None
    q = pd.DataFrame({'date': pd.to_datetime(dates)})
    m = pd.merge_asof(q, edf[['report_date', 'amc', 'surprise_pct_fill', 'eps_delta']],
                      left_on='date', right_on='report_date', direction='backward')
    m = m.where(m.report_date < m.date)               # strict: nothing from D onward
    days = (m.date - m.report_date).dt.days.to_numpy(dtype=np.float32)
    return pd.DataFrame({'earn_days': days,
                         'earn_amc': m.amc.to_numpy(dtype=np.float32),
                         'earn_surp': m.surprise_pct_fill.to_numpy(dtype=np.float32),
                         'earn_deps': m.eps_delta.to_numpy(dtype=np.float32)})

# ---------------- per-ticker assembly (single definition; main + leak test) ----------------
def ticker_frame(tk, d, funcs, etf, breadth, edf_tk):
    """Assemble one ticker's world rows from its sorted bar frame `d`.
    Every join is backward-looking and every TA-Lib array is shifted by one bar:
    row D uses bars <= D-1, ETF bars <= D-1, breadth dated < D, earnings with
    report_date < D. `edf_tk` is the ticker's earnings sub-frame (or None)."""
    df = pd.DataFrame({'ticker': tk, 'date': d.date.to_numpy()})
    if len(d) >= 30:
        o = d.open.to_numpy(float); h = d.high.to_numpy(float); l = d.low.to_numpy(float)
        c = d.close.to_numpy(float); v = d.volume.to_numpy(float)
        cols = compute_talib(o, h, l, c, v, funcs)
        for k, arr in cols.items():
            df[k] = np.r_[np.nan, arr[:-1]]          # shift-by-one: D sees bars <= D-1
    if breadth is not None:
        bcols = [c for c in breadth.columns if c != 'date']
        key = pd.to_datetime(df['date']) - pd.Timedelta(days=1)   # strict: breadth date < D
        m = pd.merge_asof(pd.DataFrame({'date': key}).sort_values('date'),
                          breadth, on='date', direction='backward')
        for bc in bcols:
            df[bc] = m[bc].to_numpy(dtype=np.float32)
    if etf is not None:
        ecols = [c for c in etf.columns if c != 'date']
        key = pd.to_datetime(df['date'])
        m = pd.merge_asof(pd.DataFrame({'date': key}), etf, on='date', direction='backward')
        for ec in ecols:
            df[ec] = m[ec].to_numpy(dtype=np.float32)
    e2 = earn_for(d.date.to_numpy(), edf_tk) if edf_tk is not None else None
    if e2 is not None:
        df = pd.concat([df.reset_index(drop=True), e2.reset_index(drop=True)], axis=1)
    return df

# ---------------- build ----------------
def load_bars(tickers=None):
    p = D('/workspace/updown/bars_all.parquet')
    df = pd.read_parquet(p)
    df['date'] = pd.to_datetime(df['date'])       # file stores timestamp; filter after parse
    df = df[df.date <= END]
    if tickers: df = df[df.ticker.isin(tickers)]
    return df

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
    breadth = None
    if os.path.exists(br):
        breadth = pd.read_parquet(br)
        if 'date' not in breadth.columns:
            breadth = breadth.reset_index()          # file stores date as the index
        breadth['date'] = pd.to_datetime(breadth['date'])
        breadth = breadth.sort_values('date')
    if breadth is not None: print('breadth cols:', list(breadth.columns), flush=True)

    bars = load_bars(set(mine))
    os.makedirs(a.out, exist_ok=True)
    bcols = [c for c in breadth.columns if c != 'date'] if breadth is not None else []
    etf = etf_wide()
    ecols = [c for c in etf.columns if c != 'date'] if etf is not None else []
    if etf is not None: print('ETF overlay cols:', len(ecols), flush=True)
    edf_by_tk = None
    edf = load_earnings(set(mine))
    ecols2 = ['earn_days', 'earn_amc', 'earn_surp', 'earn_deps'] if edf is not None else []
    if edf is not None:
        edf_by_tk = dict(tuple(edf.groupby('symbol')))
        print('earnings rows for shard:', len(edf), flush=True)
    parts, meta = [], {'talib_funcs': sorted(funcs), 'shift': 'value at D uses bars <= D-1',
                       'shard': a.shard, 'shards': a.shards, 'breadth_cols': bcols,
                       'etf_cols': ecols, 'etf_note': 'shifted 1 ETF bar, asof join; SPDR set uses current sector labels (bias flagged)',
                       'earn_cols': ecols2, 'earn_note': 'strict report_date < D (BMO-on-D excluded)'}
    for i, (tk, d) in enumerate(bars.groupby('ticker', sort=False)):
        d = d.sort_values('date')
        if len(d) < 30: continue
        df = ticker_frame(tk, d, funcs, etf if ecols else None,
                          breadth if bcols else None, edf_by_tk.get(tk) if ecols2 else None)
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
