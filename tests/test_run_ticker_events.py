"""End-to-end smoke: engine.run_ticker on synthetic bars produces the groups 034+ event columns with the
tree's (k,N) grid, and the answers survive the one-bar leak shift correctly (answer stored at day D used
events <= D-1 only - verified here by construction dates).
Run: python3 tests/test_run_ticker_events.py  (CHECKLIST_DATA_DIR must point at a dir with the dials CSVs)"""
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

# synthetic bars: halt on 2020-08-03 (session 45), earnings BMO beat on 2020-07-15 (session 32)
bars = pd.DataFrame(dict(
    date=pd.bdate_range('2020-06-01', periods=80),
    open=100.0, high=101.0, low=99.0, close=100.0, volume=1e6))
dt = bars.date.values
r = np.zeros(80); r[33] = 0.05; r[46] = 0.06
bars.close = 100 * np.cumprod(1 + r)
C = dict(sessions=pd.bdate_range('2019-01-01', periods=500).values,
         spy=pd.Series(100.0, index=pd.bdate_range('2019-01-01', periods=500)),
         vix=pd.Series(20.0, index=pd.bdate_range('2019-01-01', periods=500)),
         breadth=pd.Series(0.5, index=pd.bdate_range('2019-01-01', periods=500)),
         shares_by={'TEST': pd.DataFrame(dict(filed=[dt[0] - 1], end=[dt[0] - 1], val=[1e6]))}, regsho_by={},
         halts_by={'TEST': pd.DataFrame(dict(halt_dt=[dt[45]], resume_dt=[dt[45]], rsn_code=[0]))},
         si_by={'TEST': pd.DataFrame(dict(pub=[dt[10], dt[20]], current_short_qty=[3e5, 3.3e5],
                                          previous_short_qty=[2.7e5, 3e5], days_to_cover=[1.5, 6.0]))},
         earn_by={'TEST': pd.DataFrame(dict(rep=[dt[32]], surprise_pct_fill=[10.0], eps_delta=[0.1], bmo=[True]))},
         mcap_bad=set(), mcap_jump=set())

E.H71.load_buckets(); E.HIST.clear(); E.load_history(E.HISTF); E.GRIDV.clear()
plan, rep = E.tf_plan()
ok('coverage counts new base facets', rep['base_built'] >= 5150)   # 5159 with groups 034+ event facets
ok('coverage: every tree history row wired', rep['hist_built'] == rep['tree_hist'])
A, err = E.run_ticker('TEST', bars, C, plan)
cols = set(A.columns)
for c in ('halts|halt_occurred|1d|10', 'halts|halt_count|1d|20', 'halts|halt_type|1d|10', 'halts|time_since|1d|10',
          'short_interest|level_bucket|1d|10', 'short_interest|si_trend|1d|10', 'short_interest|dtc_route|1d|10',
          'earnings|beat_miss|1d|10', 'earnings|time_since|1d|10', 'earnings|streak|1d|10'):
    ok(f'column {c}', c in cols)
A = A.set_index('date')
d_halt = pd.Timestamp(dt[45]); d_earn = pd.Timestamp(dt[32])
ok('halt_occurred fires the day AFTER the halt (shift)', A.loc[d_halt + pd.Timedelta(days=1), 'halts|halt_occurred|1d|10'] == 0)
ok('halt_occurred silent on the halt day itself', A.loc[d_halt, 'halts|halt_occurred|1d|10'] == 1)
ok('beat_miss: BMO beat visible next day', A.loc[d_earn + pd.Timedelta(days=1), 'earnings|beat_miss|1d|10'] == 0)
ok('si_trend up after second report', A.loc[pd.Timestamp(dt[20]) + pd.Timedelta(days=1), 'short_interest|si_trend|1d|10'] == 0)
cb = E.codebook_cols(A.columns)
ok('codebook has halt labels', cb.get('halts|halt_occurred|1d|10') == ['yes', 'no'])
ok('codebook has si_vs_price labels', any('building_in_fall' in x for x in cb.get('short_interest|si_vs_price|1d|10', [])))
n_event_err = [k for k in err if k.startswith(('halts|', 'short_interest|', 'earnings|'))]
ok('no errors on event questions', len(n_event_err) == 0)
if n_event_err: print(n_event_err[:5])

n_fail = sum(1 for _, c in PASS if not c)
print(f'RUN_TICKER EVENT SMOKE {"PASS" if n_fail == 0 else "FAIL"} ({len(PASS) - n_fail}/{len(PASS)} passed)')
sys.exit(1 if n_fail else 0)
