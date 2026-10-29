"""End-to-end smoke: engine.run_ticker produces the groups 035+ world columns (variant 'world')
from the per-stock world snapshot, and the one-bar leak shift holds: a world row dated X (which by
construction holds only data strictly before X) may influence the answer stored at day X, never earlier.
Run: python3 tests/test_run_ticker_worldq.py  (CHECKLIST_DATA_DIR must point at a dir with the dials CSVs)"""
import os, sys, types
os.environ.setdefault('CHECKLIST_DATA_DIR', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'boxdata', 'mock_dials')))
os.environ['GRID_FILE'] = '/nonexistent'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_talib = types.ModuleType('talib')
def _mk(name):
    def f(*a, **k):
        import numpy as np
        n = len(a[0]); nan = np.full(n, np.nan)
        if name in ('MACD', 'BBANDS'): return (nan, nan, nan)
        if name in ('STOCH', 'STOCHF', 'AROON', 'STOCHRSI'): return (nan, nan)
        return nan
    return f
_talib.__getattr__ = lambda name: _mk(name)
_talib.get_function_groups = lambda: {}
_talib.get_functions = lambda: []
sys.modules['talib'] = _talib

import numpy as np, pandas as pd
import engine as E

PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print(f'FAIL: {name}')

# synthetic bars, 80 sessions
bars = pd.DataFrame(dict(
    date=pd.bdate_range('2020-06-01', periods=80),
    open=100.0, high=101.0, low=99.0, close=100.0, volume=1e6))
dt = bars.date.values
C = dict(sessions=pd.bdate_range('2019-01-01', periods=500).values,
         spy=pd.Series(100.0, index=pd.bdate_range('2019-01-01', periods=500)),
         vix=pd.Series(20.0, index=pd.bdate_range('2019-01-01', periods=500)),
         breadth=pd.Series(0.5, index=pd.bdate_range('2019-01-01', periods=500)),
         shares_by={'TEST': pd.DataFrame(dict(filed=[dt[0] - 1], end=[dt[0] - 1], val=[1e6]))}, regsho_by={},
         mcap_bad=set(), mcap_jump=set())

# world snapshot for TEST: rows on the same sessions. tv_pmo_x flips 0 -> 1 at the row dated dt[50];
# by the shard contract that row contains only data strictly before dt[50], so the flip must first
# appear in the answer stored at day dt[50] (via bar dt[49]) and must NOT be visible on dt[49] or earlier.
wf = pd.DataFrame(dict(
    date=dt,
    mkt_vix=np.full(80, 25.0),
    f4_n20=np.r_[np.full(50, 0.0), np.full(30, 3.0)],
    tv_pmo_x=np.r_[np.full(50, 0.0), np.full(30, 1.0)],
))
C['world_by'] = {'TEST': wf}

E.H71.load_buckets(); E.HIST.clear(); E.load_history(E.HISTF); E.GRIDV.clear()
plan, rep = E.tf_plan()
A, err = E.run_ticker('TEST', bars, C, plan)
cols = set(A.columns)
for c in ('world|mkt_vix_level|1d|10', 'world|mkt_vix_direction|1d|10',
          'world|f4_n20_level|1d|10', 'world|f4_n20_pctile_1y|1d|10',
          'world|tv_pmo_x_state|1d|10', 'world|tv_pmo_x_flip|1d|10'):
    ok(f'column {c}', c in cols)
A = A.set_index('date')
d_flip = pd.Timestamp(dt[50])
ok('vix level 20-30 bucket', A.loc[d_flip, 'world|mkt_vix_level|1d|10'] == 2)
ok('vix flat (const 25 -> within 0.5% band)', A.loc[d_flip, 'world|mkt_vix_direction|1d|10'] == 2)
ok('f4_n20 level 2-5 bucket after day 50', A.loc[d_flip, 'world|f4_n20_level|1d|10'] == 2)
ok('pmo_x_state yes on the flip day itself (row dt[50] holds <= dt[49] data)',
   A.loc[d_flip, 'world|tv_pmo_x_state|1d|10'] == 0)
ok('pmo_x_state still no the day BEFORE the flip', A.loc[pd.Timestamp(dt[49]), 'world|tv_pmo_x_state|1d|10'] == 1)
ok('flip facet changed on the flip day (state and flip enter answers together)',
   A.loc[d_flip, 'world|tv_pmo_x_flip|1d|10'] == 0)
ok('flip facet same the day before the flip', A.loc[pd.Timestamp(dt[49]), 'world|tv_pmo_x_flip|1d|10'] == 1)
n_world_err = [k for k in err if k.startswith('world|')]
ok('no errors on world questions', len(n_world_err) == 0)
if n_world_err: print(n_world_err[:5])

# ticker with NO world snapshot: world questions exist but are all -1 (n_a), no errors
C2 = dict(C); C2['world_by'] = {}
A2, err2 = E.run_ticker('EMPTY', bars, C2, plan)
wcols2 = [c for c in A2.columns if c.startswith('world|')]
ok('world columns still generated without snapshot', len(wcols2) > 0)
ok('all -1 without snapshot', all((A2[c] == -1).all() for c in wcols2))
ok('no errors without snapshot', len([k for k in err2 if k.startswith('world|')]) == 0)

n_fail = sum(1 for _, c in PASS if not c)
print(f'RUN_TICKER WORLD SMOKE {"PASS" if n_fail == 0 else "FAIL"} ({len(PASS) - n_fail}/{len(PASS)} passed)')
sys.exit(1 if n_fail else 0)
