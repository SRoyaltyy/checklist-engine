"""Leak test: no answer for day D may use data after D.
For each ticker: compute all answers on the full bars, then again with bars cut off at D (D = last kept bar),
and require the row for D to be identical. Run: CHECKLIST_DATA_DIR=... python3 tests/test_leak.py AAPL,KO,NVDA,ALDX,ARQT"""
import os, sys, json, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', '/nonexistent')          # default cutoffs only (same code path, faster)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd, engine as E
from multiprocessing import Pool

def setup():
    E.H71.load_buckets(); E.HIST.clear(); E.load_history(E.HISTF); E.GRIDV.clear(); E.GRIDV.update(E.load_grid())
    plan, _ = E.tf_plan(); C = E.load_context()
    C['shares_by'] = {k: g for k, g in C['shares'].groupby('ticker')}; C['regsho_by'] = {k: g.date.values for k, g in C['regsho'].groupby('symbol')}
    Q = pd.read_csv(E.QUAR); C['mcap_bad'] = set(Q[Q.action == 'mcap_unknown'].ticker); C['mcap_jump'] = set(Q[Q.action == 'flag'].ticker)
    return plan, C

def check(tk, cut_dates=('2020-06-15', '2021-09-01', '2022-12-30', '2024-12-31')):
    plan, C = setup(); g = E.load_bars([tk]); full, _ = E.run_ticker(tk, g, C, plan); full = full.set_index('date')
    res = []
    for cd in cut_dates:
        ds = full.index[full.index <= pd.Timestamp(cd)]
        if not len(ds): continue
        D = ds[-1]; cut, cerr = E.run_ticker(tk, g[g.date <= D], C, plan); cut = cut.set_index('date')
        a, b = full.loc[D], cut.loc[D]
        cols = [c for c in full.columns if c in cut.columns]
        # a column absent from the cut run only counts if the full run had a real answer (not -1) at D
        missing = [c for c in set(full.columns) - set(cut.columns) if a[c] != -1] + list(set(cut.columns) - set(full.columns))
        bad = [c for c in cols if not (a[c] == b[c] or (pd.isna(a[c]) and pd.isna(b[c])) or
               (isinstance(a[c], (float, np.floating)) and np.isclose(a[c], b[c], rtol=1e-5, equal_nan=True)))]
        res.append(dict(ticker=tk, D=str(D.date()), cols=len(cols), mismatched=len(bad), examples=bad[:5], col_set_diff=len(missing), missing_examples=sorted(missing)[:5], cut_errors=list(cerr.items())[:3]))
    return res

if __name__ == '__main__':
    tks = (sys.argv[1] if len(sys.argv) > 1 else 'AAPL,KO,NVDA,ALDX,ARQT').split(',')
    with Pool(min(5, len(tks))) as p: out = sum(p.map(check, tks), [])
    for r in out: print(json.dumps(r))
    bad = sum(r['mismatched'] + r['col_set_diff'] for r in out)
    print('LEAK TEST', 'PASS' if bad == 0 and out else 'FAIL', f'({len(out)} cut points, {bad} mismatches)')
    sys.exit(0 if bad == 0 and out else 1)
