"""Regression test: _events_I must not IndexError when ALL of a ticker's events fall outside
its bar window (e.g. delisted 2021, FINRA SI reports / earnings / halt-resume dates continue
into 2022-24). Pre-fix this crashed the whole Step A pool with
`IndexError: index 0 is out of bounds for axis 0 with size 0` (run 40180498392).
Also checks in-window events stay knowable and post-window resumes stay NaN (no leak, no pile-on).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import engine

PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print(f'FAIL: {name}')

def make_case():
    dates = pd.bdate_range('2020-01-02', '2021-06-30').values   # ticker delisted 2021-06-30
    T = len(dates)
    I = {'c': np.full(T, 10.0), 'o': np.full(T, 10.0), 'shares': np.full(T, 1e8), 'ret': np.zeros(T)}
    C = {
        'si_by': {'FOO': pd.DataFrame({   # reports span 2020..2024, only the first two in-window (distinct qty)
            'pub': pd.to_datetime(['2020-03-15', '2021-01-15', '2022-03-15', '2023-03-15', '2024-03-15']),
            'current_short_qty': [1e6, 2e6, 3e6, 4e6, 5e6],
            'previous_short_qty': [9e5] * 5, 'days_to_cover': [2.0] * 5})},
        'earn_by': {'FOO': pd.DataFrame({  # earnings continue years after delisting (distinct surprises)
            'rep': pd.to_datetime(['2020-04-15', '2022-04-15', '2023-04-15', '2024-04-15']),
            'surprise_pct_fill': [5.0, 10.0, 20.0, 30.0], 'eps_delta': [0.1] * 4, 'bmo': [True] * 4})},
        'halts_by': {'FOO': pd.DataFrame({  # halt in-window, resume LONG after the last bar
            'halt_dt': pd.to_datetime(['2021-05-03']), 'resume_dt': pd.to_datetime(['2024-06-01']), 'rsn_code': [0]})},
    }
    return I, C, dates, T

I, C, dates, T = make_case()
engine._events_I(I, 'FOO', C, dates)   # pre-fix: IndexError here

ALL = ['si_rep', 'si_qty', 'si_prev', 'si_dtc', 'si_pct26', 'si_prchg',
       'earn_cnt', 'earn_last', 'earn_since', 'earn_surp', 'earn_streak', 'earn_prerun', 'earn_gap', 'earn_post5',
       'halt_cnt', 'halt_last', 'halt_since', 'halt_rsn', 'halt_predir', 'halt_res', 'halt_resret']
ok('all event arrays full length', all(len(I[k]) == T for k in ALL))

# as-of persistence: the last IN-WINDOW report stays knowable to the final bar...
si_pub_bars = np.where(np.isfinite(I['si_qty']))[0]
ok('in-window SI reports knowable', len(si_pub_bars) > 0)
ok('SI qty persists (as-of) to final bar', si_pub_bars.max() == T - 1)
# ...but post-window reports are DROPPED, not piled: final qty = last in-window report (2e6), never 5e6
ok('post-window SI reports dropped not piled (final qty = 2e6)', I['si_qty'][-1] == 2e6)

# the halt is counted exactly once; its post-window resume is NOT knowable (no future pile-on)
ok('halt counted once', float(I['halt_cnt'].sum()) == 1.0)
ok('post-window halt resume unknown', not np.isfinite(I['halt_res']).any())
ok('halt rsn knowable at/after halt bar', np.isfinite(I['halt_rsn'][I['halt_cnt'] > 0]).all())

# earnings: in-window report counted; nothing knowable from post-window reports
ok('in-window earnings counted', float(I['earn_cnt'].sum()) == 1.0)
ok('post-window earnings dropped not piled (final surprise = 5.0)', I['earn_surp'][-1] == 5.0)
last_knowable = np.searchsorted(dates, pd.Timestamp('2020-04-15').to_datetime64(), side='right') - 1
ok('earn_last points at the in-window report to the final bar', I['earn_last'][-1] == last_knowable)

n_fail = sum(1 for _, c in PASS if not c)
print(f'EVENTS EMPTY-WINDOW REGRESSION {"PASS" if n_fail == 0 else "FAIL"} ({len(PASS) - n_fail}/{len(PASS)} passed)')
sys.exit(1 if n_fail else 0)
