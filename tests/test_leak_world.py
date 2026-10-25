"""World-snapshot leak test (fix 5 in 0b audit ceb1b89): row D of the world
build must be identical when every input is truncated at D. Covers EVERY world
column (TA-Lib indicators + 61 candle patterns, ETF overlays, market breadth,
earnings) across several tickers and cut dates.

Run: CHECKLIST_DATA_DIR=<data-2020-24-v1> python3 tests/test_leak_world.py AAPL,MSFT,NVDA
"""
import os, sys, json, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', '/nonexistent')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
import facets_world as fw

CUT_DATES = ('2020-06-15', '2021-03-01', '2021-09-01', '2022-06-01', '2023-02-01', '2024-06-03')

def load_inputs():
    funcs = fw.discover()
    etf = fw.etf_wide()
    br = fw.D('/workspace/updown/breadth_2020_24.parquet')
    breadth = None
    if os.path.exists(br):
        breadth = pd.read_parquet(br)
        if 'date' not in breadth.columns:
            breadth = breadth.reset_index()          # file stores date as the index
        breadth['date'] = pd.to_datetime(breadth['date'])
        breadth = breadth.sort_values('date')
    return funcs, etf, breadth

def check(tk, funcs, etf, breadth, cut_dates=CUT_DATES):
    bars = fw.load_bars({tk}).sort_values('date')
    if not len(bars):
        return [dict(ticker=tk, D='-', cols=0, mismatched=0, examples=[], note='no bars')]
    edf = fw.load_earnings({tk})
    edf_tk = edf[edf.symbol == tk] if edf is not None and len(edf) else None
    full = fw.ticker_frame(tk, bars, funcs, etf, breadth, edf_tk).set_index('date')
    res = []
    for cd in cut_dates:
        ds = full.index[full.index <= pd.Timestamp(cd)]
        if not len(ds):
            continue
        D = ds[-1]
        b = bars[bars.date <= D]
        if not len(b):
            continue
        cut = fw.ticker_frame(tk, b, funcs, etf, breadth, edf_tk).set_index('date')
        if D not in cut.index:
            res.append(dict(ticker=tk, D=str(D.date()), cols=0, mismatched=1, examples=['row D missing in cut build']))
            continue
        a, c = full.loc[D], cut.loc[D]
        cols = [x for x in full.columns if x in cut.columns and x != 'ticker']
        missing = sorted(set(full.columns) - set(cut.columns))
        bad = []
        for col in cols:
            av, cv = a[col], c[col]
            if pd.isna(av) and pd.isna(cv):
                continue
            if isinstance(av, (float, np.floating)) and isinstance(cv, (float, np.floating)) and np.isclose(av, cv, rtol=1e-5, equal_nan=True):
                continue
            if av == cv:
                continue
            bad.append(col)
        res.append(dict(ticker=tk, D=str(D.date()), cols=len(cols), mismatched=len(bad),
                        examples=bad[:5], col_set_diff=len(missing), missing_examples=missing[:5]))
    return res

if __name__ == '__main__':
    tks = (sys.argv[1] if len(sys.argv) > 1 else 'AAPL,MSFT,NVDA').split(',')
    funcs, etf, breadth = load_inputs()
    out = []
    for tk in tks:
        out += check(tk, funcs, etf, breadth)
        print(tk, 'done', flush=True)
    for r in out:
        print(json.dumps(r))
    bad = sum(r['mismatched'] + r.get('col_set_diff', 0) for r in out)
    ncols = sum(r['cols'] for r in out)
    print('WORLD LEAK TEST', 'PASS' if bad == 0 and out else 'FAIL',
          f'({len(out)} cut points, {ncols} column comparisons, {bad} mismatches)')
    sys.exit(0 if bad == 0 and out else 1)
