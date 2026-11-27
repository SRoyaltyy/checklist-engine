"""Synthetic tests for groups 034+ event facets (halts, short_interest, earnings) + their _load_* parsers.
No real market data needed for the facet tests: synthetic bars + synthetic event frames, aligned via
engine.make_I exactly as in production. Leak contract asserted directly: every aligned value at bar t
must equal the value recomputed on bars truncated at t (only events <= dates[t] are visible).
Run: python3 tests/test_facets_events.py"""
import os, sys, types
if 'CHECKLIST_DATA_DIR' not in os.environ:
    os.environ['CHECKLIST_DATA_DIR'] = ''   # caller may point at fixtures before import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- functional talib stub: every function returns an all-NaN array the length of the first input
_talib = types.ModuleType('talib')
def _mk(name):
    def f(*a, **k):
        import numpy as np
        n = len(a[0]) if a and hasattr(a[0], '__len__') else 1
        nan = np.full(n, np.nan)
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
from facets import REG

PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print(f'FAIL: {name}')

# ---------------------------------------------------------------- synthetic fixture
def make_bars(T=140):
    d = pd.bdate_range('2020-06-01', periods=T)
    r = np.zeros(T)
    r[45:50] = 0.01                       # rise into the halt at session 50
    r[51] = 0.06                          # resume reaction: up
    r[41:44] = -0.02                      # sharp dip between SI report dates 40->50 (net move still negative)
    r[78] = -0.01; r[79] = -0.01          # drift down into T12 halt at 80
    r[81] = 0.01                          # bounce after resume (session 81)
    r[100] = -0.02
    r[21:30] = 0.008                      # 20-bar up-run into earnings at 30 (net of the early-June dip)
    r[31] = 0.05                          # gap-day follow-through (earnings 30)
    r[71] = -0.04                         # AMC miss at 70 -> down next session
    r[111] = 0.03                         # post-earnings 110 drift
    c = 100 * np.cumprod(1 + r)
    o = np.r_[c[0], c[:-1]] * (1 + np.r_[0, r[1:]] * 0.2)
    return pd.DataFrame(dict(date=d, open=o, high=np.fmax(o, c) * 1.01, low=np.fmin(o, c) * 0.99, close=c, volume=1e6))

def make_C(d, bars):
    T = len(bars)
    dt = bars.date.values
    sess = pd.bdate_range('2019-01-01', periods=400).values   # session calendar wider than bars
    spy = pd.Series(100.0, index=sess); vix = pd.Series(20.0, index=sess); br = pd.Series(0.5, index=sess)
    C = dict(sessions=sess, spy=spy, vix=vix, breadth=br,
             shares_by={'TEST': pd.DataFrame(dict(filed=dt[:1] - 1, end=dt[:1] - 1, val=[1_000_000.0]))},
             regsho_by={})
    # halts: LUDP @50 (same-day resume), T12 @80 (resume next session), unresumed @100
    C['halts_by'] = {'TEST': pd.DataFrame(dict(
        halt_dt=[dt[50], dt[80], dt[100]],
        resume_dt=[dt[50], dt[81], np.datetime64('NaT')],
        rsn_code=[0, 2, 1]))}
    # SI: report every 10 sessions from 10; qty +10% each time; dtc alternates 1.5 / 6.0
    pbs = list(range(10, T, 10))
    qty = 300_000 * 1.1 ** np.arange(len(pbs))
    C['si_by'] = {'TEST': pd.DataFrame(dict(
        pub=dt[pbs], current_short_qty=qty,
        previous_short_qty=np.r_[qty[0] / 1.1, qty[:-1]], days_to_cover=([1.5, 6.0] * (len(pbs) // 2 + 1))[:len(pbs)]))}
    # earnings: BMO beat @30, AMC miss @70, BMO beat @110
    C['earn_by'] = {'TEST': pd.DataFrame(dict(
        rep=[dt[30], dt[70], dt[110]], surprise_pct_fill=[10.0, -5.0, 20.0],
        eps_delta=[0.1, -0.06, 0.2], bmo=[True, False, True]))}
    return C

def facet_fn(variant, name):
    for (v, f, labels, fn, lbs) in REG:
        if v == variant and f == name: return fn, labels
    raise KeyError(f'{variant}|{name}')

bars = make_bars(); dt = bars.date.values
C = make_C(dt, bars)
I = E.make_I(bars, 'TEST', C)
T = len(bars)

# ---------------------------------------------------------------- halts
fn, lab = facet_fn('halts', 'halt_occurred')
a = fn(I, 10)
ok('halt_occurred labels', lab == ['yes', 'no'])
ok('halt_occurred: no halt before 50', a[40] == 1)
ok('halt_occurred: halt visible at its own bar', a[50] == 0)
ok('halt_occurred: window covers 50 at t=54, empty again at t=60', a[54] == 0 and a[45] == 1 and a[60] == 1)
fn, _ = facet_fn('halts', 'halt_count')
a = fn(I, 120)
ok('halt_count: window incomplete early -> n_a', a[100] == -1)
ok('halt_count: 3 halts in completed window -> 2+', a[139] == 2)
fn, lab = facet_fn('halts', 'halt_type')
a = fn(I, 20)
ok('halt_type labels', lab == ['LUDP', 'news', 'regulatory'])
ok('halt_type: LUDP at 50', a[50] == 0)
ok('halt_type: regulatory T12 at 80', a[80] == 2)
ok('halt_type: -1 when no halt in window', a[10] == -1)
fn, lab = facet_fn('halts', 'time_since')
a = fn(I, 10)
ok('time_since labels', lab == ['<5', '5-20', '>20', 'none'])
ok('time_since: 3 sessions after halt', a[53] == 0)
ok('time_since: none before any halt', a[10] == 3)
fn, _ = facet_fn('halts', 'direction_before')
ok('direction_before: rise into halt @50 = up', fn(I, 10)[50] == 0)
ok('direction_before: fall into halt @80 = down', fn(I, 10)[80] == 1)
fn, _ = facet_fn('halts', 'resume_reaction')
a = fn(I, 10)
ok('resume_reaction: up after +6% resume day', a[60] == 0)
ok('resume_reaction: -1 before any halt', a[10] == -1)
ok('resume_reaction: unresumed halt @100 ignored', a[99] == a[98])

# ---------------------------------------------------------------- short interest
fn, lab = facet_fn('short_interest', 'level_bucket')
a = fn(I, 10)
ok('si level: >20% (300k/1M)', a[10] == 0)
fn, lab = facet_fn('short_interest', 'si_trend')
ok('si_trend labels', lab == ['up', 'down', 'flat'])
ok('si_trend: +10% reports = up', a[20] == 0)
fn, _ = facet_fn('short_interest', 'dtc_route')
a = fn(I, 30)
ok('dtc_route: 6.0 at window start (bar 20) and end (bar 40) = >5->>5', a[49] == 2 * 3 + 2)
fn, _ = facet_fn('short_interest', 'report_count_rising')
ok('report_count_rising: 3+ reports in 25 bars', fn(I, 25)[39] == 2)
fn, _ = facet_fn('short_interest', 'si_vs_price')
ok('si_vs_price: si up while price down @50 = building_in_fall', fn(I, 10)[50] == 0)

# ---------------------------------------------------------------- earnings
fn, lab = facet_fn('earnings', 'beat_miss')
a = fn(I, 60)
ok('beat_miss: BMO beat same session', a[30] == 0)
ok('beat_miss: AMC miss only knowable next session', a[70] == 0 and a[71] == 1)
ok('beat_miss: stale report outside N -> n_a', fn(I, 10)[100] == -1)
fn, _ = facet_fn('earnings', 'time_since')
ok('earnings time_since: 3 sessions after report', fn(I, 10)[33] == 0)
fn, _ = facet_fn('earnings', 'streak')
ok('earnings streak: single beat after miss = 1', fn(I, 10)[111] == 1)
fn, _ = facet_fn('earnings', 'pre_run')
ok('earnings pre_run: up into report @30', fn(I, 10)[30] == 0)
fn, lab = facet_fn('earnings', 'gap_reaction')
a = fn(I, 20)
ok('gap_reaction: up-leg x gap-up', a[31] == 0)
ok('gap_reaction labels end with none', lab[-1] == 'none')
fn, _ = facet_fn('earnings', 'drift_after')
ok('drift_after: continued after beat', fn(I, 20)[40] == 0)

# ---------------------------------------------------------------- history series (facets_v271)
for v, key in (('halts', 'halt_cnt'), ('short_interest', 'si_rep'), ('earnings', 'earn_cnt')):
    X = E.H71.series(I, v)
    ok(f'series {v}', X is not None and np.allclose(np.nan_to_num(X), np.nan_to_num(I[key])))
ok('series form4 still None (no data)', E.H71.series(I, 'form4') is None)
ok('series analyst_actions still None (no data)', E.H71.series(I, 'analyst_actions') is None)

# ---------------------------------------------------------------- leak contract: truncation invariance
for cut in (60, 80, 101, 139):
    I2 = E.make_I(bars.iloc[:cut + 1].reset_index(drop=True), 'TEST', C)
    for key in ('halt_cnt', 'halt_last', 'halt_since', 'halt_rsn', 'halt_predir', 'halt_res', 'halt_resret',
                'si_rep', 'si_qty', 'si_prev', 'si_dtc', 'si_pct26', 'si_prchg',
                'earn_cnt', 'earn_last', 'earn_since', 'earn_surp', 'earn_streak', 'earn_prerun', 'earn_gap', 'earn_post5'):
        x, y = np.asarray(I[key][:cut + 1], float), np.asarray(I2[key], float)
        same = (np.isnan(x) & np.isnan(y)) | (x == y)
        ok(f'leak: {key} identical through bar {cut}', same.all())

# ---------------------------------------------------------------- _load_* parsers on fixture files
mdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'boxdata', 'boxdata_mock', 'data-ext')
if os.path.isdir(mdir):
    os.environ['CHECKLIST_DATA_DIR'] = os.path.abspath(mdir)
    import importlib, datapaths
    importlib.reload(datapaths); importlib.reload(E)
    hb = E._load_halts(); sb = E._load_si(); eb = E._load_earnings()
    ok('load_halts parsed', len(hb) > 100 and all(f in next(iter(hb.values())).columns for f in ('halt_dt', 'resume_dt', 'rsn_code')))
    ok('load_halts reason codes in {0,1,2}', all(set(g.rsn_code.unique()) <= {0, 1, 2} for g in hb.values()))
    ok('load_si parsed', len(sb) > 100 and all(f in next(iter(sb.values())).columns for f in ('pub', 'current_short_qty', 'previous_short_qty', 'days_to_cover')))
    ok('load_earnings parsed', len(eb) > 100 and all(f in next(iter(eb.values())).columns for f in ('rep', 'surprise_pct_fill', 'eps_delta', 'bmo')))
    # production round-trip: make_I on a real ticker's bars shape
    if 'AAPL' in eb:
        b2 = make_bars(120); b2['date'] = pd.bdate_range('2020-01-02', periods=120)
        C2 = make_C(None, b2); C2['earn_by'] = {k: g for k, g in eb.items() if k in ('AAPL',)}
        C2['halts_by'] = {k: g for k, g in hb.items() if k in ('AAPL',)}
        C2['si_by'] = {k: g for k, g in sb.items() if k in ('AAPL',)}
        I3 = E.make_I(b2, 'AAPL', C2)
        ok('AAPL earnings aligned', np.nansum(I3['earn_cnt']) >= 2)
        ok('AAPL SI aligned', np.nansum(I3['si_rep']) >= 8)
else:
    print(f'skip _load_* parser tests (fixture dir missing: {mdir})')

n_fail = sum(1 for _, c in PASS if not c)
print(f'EVENT FACET TESTS {"PASS" if n_fail == 0 else "FAIL"} ({len(PASS) - n_fail}/{len(PASS)} passed)')
sys.exit(1 if n_fail else 0)
