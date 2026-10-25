"""Synthetic tests for scoring/state_change.py (docs/STATE_CHANGE_PREREG.md §3+§6 runner).
Builds a fixture where residualised rises >= 10pp on the continuity cell have a planted
positive excess, everything else is noise, and checks:
  1. the planted cell PASSES, its mirror (fall<=-10pp) does not;
  2. tiny cells fail with n<30;
  3. two runs are byte-identical (frozen RNG seed);
  4. no --ret input flags 'residualised': False and still runs;
  5. missing/foreign role or wrong fixed cell is rejected.
Run: python3 tests/test_state_change.py
"""
import os, sys, json, tempfile, subprocess
import numpy as np, pandas as pd

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, D)
from scoring import state_change as SC

PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print('FAIL:', name)

def fixture(n_t=120, n_d=180, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    rets = []
    for t in range(n_t):
        ret = rng.normal(0, .02, n_d)
        jump = (rng.random(n_d) < .06) * rng.choice([-1, 1], n_d) * rng.uniform(10, 20, n_d) / 100
        p = np.clip(.5 + np.cumsum(rng.normal(0, .004, n_d) + jump), .02, .98)
        dp = np.diff(p, prepend=np.nan) * 100
        for d in range(1, n_d):
            excess = 0.006 if dp[d] >= 10 else -0.0005
            rows.append(dict(ticker=f'T{t}', date=pd.Timestamp('2023-01-03') + pd.Timedelta(days=d),
                             role='fixed', m=20, h=15, stop=0,
                             p_win=p[d], ev_net=.001, realised_net=excess + rng.normal(0, .01),
                             bench_net=rng.normal(0, .01)))
            rows.append(dict(ticker=f'T{t}', date=pd.Timestamp('2023-01-03') + pd.Timedelta(days=d),
                             role='map', m=int(rng.integers(2, 31)), h=int(rng.integers(1, 31)),
                             stop=int(rng.choice([0, 2, 5, 10])),
                             p_win=p[d], ev_net=.001, realised_net=rng.normal(0, .01),
                             bench_net=rng.normal(0, .01)))
        rets += [dict(ticker=f'T{t}', date=pd.Timestamp('2023-01-03') + pd.Timedelta(days=d), ret=ret[d])
                 for d in range(n_d)]
    return pd.DataFrame(rows), pd.DataFrame(rets)

cells, rets = fixture()
res = SC.run(cells, rets)
ok('planted rise>=10pp passes', res['continuity|rise>=10pp']['pass'])
ok('mirror fall<=-10pp fails', not res['continuity|fall<=-10pp']['pass'])
ok('n<30 cell fails', not res['continuity|rise>=30pp']['pass'])
ok('meta says residualised', res['_meta']['residualised'])
ok('has all four SEs', all(k in res['continuity|rise>=10pp']['se']
                           for k in ('naive', 'cluster_ticker', 'cluster_date', 'block20')))
res2 = SC.run(cells, rets)
ok('deterministic (frozen seed)', json.dumps(res, sort_keys=True) == json.dumps(res2, sort_keys=True))
res3 = SC.run(cells, None)
ok('no-ret flagged unresidualised', res3['_meta']['residualised'] is False)
ok('no-ret still runs planted cell', res3['continuity|rise>=10pp']['n'] > 0)
try:
    SC.run(cells.assign(role='weird'), rets); ok('bad role rejected', False)
except SystemExit: ok('bad role rejected', True)
bad = cells.copy(); bad.loc[bad.role == 'fixed', 'm'] = 25
try:
    SC.run(bad, rets); ok('wrong fixed cell rejected', False)
except SystemExit: ok('wrong fixed cell rejected', True)

print(f'STATE-CHANGE TESTS PASS ({sum(p for _, p in PASS)}/{len(PASS)} passed)') if all(p for _, p in PASS) else \
    print(f'STATE-CHANGE TESTS FAIL ({sum(p for _, p in PASS)}/{len(PASS)})') or sys.exit(1)
