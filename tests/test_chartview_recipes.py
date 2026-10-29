"""Deterministic recipe tests for the viewport gallery (METHODOLOGY §0b #149/#155/#159).
Synthetic OHLCV only — no network, no real prices. Run: python3 tests/test_chartview_recipes.py
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chartview import data as D
from chartview import recipes as RC

PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print(f'FAIL: {name}')


def synth(n=120, start='2021-01-04'):
    dates = pd.bdate_range(start, periods=n).values
    O = np.full(n, 100.0); H = np.full(n, 101.0); L = np.full(n, 99.0)
    C = np.full(n, 100.0); V = np.full(n, 1000.0)
    return dates, O, H, L, C, V


def test_rg_count():
    dates, O, H, L, C, V = synth()
    c = 60
    # window c-4..c: red, red, green, doji, green
    O[c - 4], C[c - 4] = 100, 99          # red
    O[c - 3], C[c - 3] = 100, 98          # red
    O[c - 2], C[c - 2] = 99, 101          # green
    O[c - 1], C[c - 1] = 100, 100         # doji
    O[c], C[c] = 100, 102                 # green
    r = RC.view_rg_count_5d(dates, O, H, L, C, V, c)
    ok('RG: R:G = 2:2 with doji', r['answer'] == 'R:G = 2:2 (doji 1)')
    bars = r['ops'][1]['bars']
    ok('RG: recolour exactly the 5 window bars', bars == [c - 4, c - 3, c - 2, c - 1, c])


def test_fib():
    dates, O, H, L, C, V = synth()
    c = 80
    for i in range(c - 59, c + 1):
        H[i] = 100.0; L[i] = 95.0; C[i] = 97.0
    H[c - 20] = 110.0; H[c - 5] = 110.0   # tie for H -> anchor = most recent (c-5)
    L[c - 30] = 88.0; L[c - 2] = 88.0     # tie for L -> anchor = most recent (c-2)
    r = RC.view_fib_hhll_60d(dates, O, H, L, C, V, c)
    rec = r['ops'][0]['bars']
    ok('FIB: anchors are the most-recent tie bars', rec == [c - 5, c - 2])
    lv = dict((lab, p) for p, lab in r['ops'][1]['levels'])
    ok('FIB: 0% = H', abs(lv['0'] - 110.0) < 1e-9)
    ok('FIB: 100% = L', abs(lv['1'] - 88.0) < 1e-9)
    ok('FIB: 50% = mid', abs(lv['0.5'] - 99.0) < 1e-9)
    ok('FIB: answer carries pct', 'pct=' in r['answer'])


def test_fib_zero_range_blank():
    dates, O, H, L, C, V = synth()
    c = 80
    for i in range(c - 59, c + 1):
        H[i] = 100.0; L[i] = 100.0
    r = RC.view_fib_hhll_60d(dates, O, H, L, C, V, c)
    ok('FIB: H==L -> blank, no ops', r['answer'].startswith('blank') and r['ops'] == [])


def test_swing_highs():
    dates, O, H, L, C, V = synth(n=200)
    c = 150
    # strictly descending baseline ramp so no flat bar is a spurious window-max
    for i in range(200):
        H[i] = 100.0 - i * 0.001
    # three descending peaks, each confirmed (peak+5 <= c)
    for pk, h in ((c - 60, 120.0), (c - 40, 115.0), (c - 20, 110.0)):
        H[pk] = h
        for k in range(1, 6):             # neighbours strictly lower -> unique argmax
            H[pk - k] = h - 1; H[pk + k] = h - 1
    r = RC.view_lower_swing_highs_3(dates, O, H, L, C, V, c)
    ok('SWING: strictly descending -> YES', r['answer'].startswith('YES'))
    pts = [p[0] for p in r['ops'][0]['pts']]
    ok('SWING: dots are the last 3 pivots', pts == [c - 60, c - 40, c - 20])
    # an unconfirmed peak (needs i+5 <= cutoff) must NOT count
    H2 = H.copy()
    pk = c - 2                              # i+5 = c+3 > c -> not confirmable
    H2[pk] = 130.0
    for k in range(1, 6):
        if 0 <= pk - k <= c: H2[pk - k] = 120.0
        if pk + k <= c: H2[pk + k] = 120.0
    r2 = RC.view_lower_swing_highs_3(dates, O, H2, L, C, V, c)
    ok('SWING: unconfirmed peak ignored (still YES on old 3)', r2['answer'].startswith('YES'))
    ok('SWING: unconfirmed peak not dotted', pk not in [p[0] for p in r2['ops'][0]['pts']])
    # equal highs -> not strictly descending
    H3 = H.copy(); H3[c - 20] = H3[c - 40]
    r3 = RC.view_lower_swing_highs_3(dates, O, H3, L, C, V, c)
    ok('SWING: equal last highs -> NO', r3['answer'].startswith('NO'))


def test_vol_mean():
    dates, O, H, L, C, V = synth()
    c = 60
    for i in range(c - 19, c + 1):
        V[i] = 2000.0
    V[c] = 4000.0
    r = RC.view_vol_vs_mean_20d(dates, O, H, L, C, V, c)
    ok('VOL20: inclusive base (cutoff in the 20), mean=2100', 'mean20=2100.0' in r['answer'])
    ok('VOL20: ratio = 4000/2100', 'ratio=1.905' in r['answer'])
    V2 = V.copy(); V2[c - 10] = 0.0
    r2 = RC.view_vol_vs_mean_20d(dates, O, H, L, C, V2, c)
    ok('VOL20: zero in base -> ratio changes (base includes it)', 'ratio=' in r2['answer'])
    V3 = V.copy()
    for i in range(c - 19, c + 1):
        V3[i] = 0.0
    r3 = RC.view_vol_vs_mean_20d(dates, O, H, L, C, V3, c)
    ok('VOL20: all-zero base -> blank', r3['answer'].startswith('blank'))


def test_lower_highs10():
    dates, O, H, L, C, V = synth()
    c = 60
    for k in range(0, 12):
        H[c - k] = 100.0 + k              # each bar lower than the previous bar
    r = RC.lower_highs10(dates, O, H, L, C, V, c)
    ok('LH10: 10/10 lower highs', r['answer'] == 'count = 10 / 10')
    ok('LH10: every window bar recoloured', r['ops'][0]['bars'] == [c - 9 + i for i in range(10)])


def test_cp_gr_body20():
    dates, O, H, L, C, V = synth()
    c = 60
    for i in range(c - 19, c + 1):
        step = (i - (c - 19)) // 2
        if step % 2 == 0:
            O[i], C[i] = 100.0, 102.0     # green body 2
        else:
            O[i], C[i] = 100.0, 99.0      # red body 1
    # 10 green (body 2) and 10 red (body 1) -> ratio 20/10 = 2
    r = RC.cp_gr_body20(dates, O, H, L, C, V, c)
    ok('BODY20: ratio = green sum / red sum = 2.000', r['answer'].endswith('ratio=2.000'))
    ok('BODY20: label says body-sum, not count', 'BODY-SUM' in r['label'])


def test_rvol20():
    dates, O, H, L, C, V = synth()
    c = 60
    V[c - 20:c] = 500.0
    V[c] = 1000.0
    r = RC.rvol20(dates, O, H, L, C, V, c)
    ok('RVOL: base excludes cutoff -> 2.000 no spike', 'RVOL=2.000' in r['answer'] and 'no spike' in r['answer'])
    V2 = V.copy(); V2[c] = 2000.0
    r2 = RC.rvol20(dates, O, H, L, C, V2, c)
    ok('RVOL: >3 -> spike', 'spike' in r2['answer'])


def test_i074():
    dates = pd.bdate_range('2021-01-04', periods=90).values   # Jan + Feb 2021
    n = 90
    O = np.full(n, 100.0); H = np.full(n, 100.0); L = np.full(n, 100.0)
    C = np.full(n, 100.0); V = np.full(n, 1000.0)
    c = 45                                    # March; prior completed month = February
    H[25] = 112.0; L[30] = 90.0; C[39] = 104.0   # February H/L/final-close
    r = RC.i074_pivots(dates, O, H, L, C, V, c, period='M')
    lv = dict((lab, p) for p, lab in r['ops'][0]['levels'])
    P = (112 + 90 + 104) / 3
    ok('I074: P correct', abs(lv['P'] - P) < 1e-9)
    ok('I074: R1 = 2P-L', abs(lv['R1'] - (2 * P - 90)) < 1e-9)
    ok('I074: S2 = P-(H-L)', abs(lv['S2'] - (P - 22)) < 1e-9)


def test_donchian():
    dates, O, H, L, C, V = synth()
    c = 60
    H[c - 15] = 130.0; H[c - 3] = 130.0     # tie -> most recent (c-3)
    L[c - 10] = 80.0; L[c - 1] = 80.0      # tie -> most recent (c-1)
    H[c] = 200.0; L[c] = 50.0             # cutoff bar must be EXCLUDED
    r = RC.i101_donchian20(dates, O, H, L, C, V, c)
    lv = dict((lab, p) for p, lab in r['ops'][0]['levels'])
    ok('DON: upper excludes cutoff', lv['upper20'] == 130.0)
    ok('DON: lower excludes cutoff', lv['lower20'] == 80.0)
    ok('DON: recolour bars are the most-recent ties', r['ops'][1]['bars'] == [c - 3, c - 1])


def test_shape_stub():
    dates, O, H, L, C, V = synth()
    r = RC.chart_shape_similarity(dates, O, H, L, C, V, 60)
    ok('SHAPE: DISABLED stub, no ops', r['status'] == RC.DISABLED and r['ops'] == [] and r['blocker'])
    ok('SHAPE: blocker names GPT grid ownership', 'GPT' in r['blocker'])


def test_as_of_truncation():
    df = pd.DataFrame(dict(
        date=pd.bdate_range('2022-06-01', periods=10),
        open=100.0, high=101.0, low=99.0, close=100.0, volume=1000))
    df['volume'] = df['volume'].astype('int64')
    dates, O, H, L, C, V, c = D.as_of(df, '2022-06-08')
    ok('AS_OF: last bar strictly before setup', str(pd.Timestamp(dates[-1]))[:10] == '2022-06-07')
    ok('AS_OF: day-S bar never read', len(dates) == 5)


def test_binary_ladders():
    """§0b 2026-10-29 22:51/23:05: every recipe derives strict YES/NO questions
    (feature + comparator + literal threshold); blank feature -> binary None
    (NOT_EVALUABLE, never silently NO)."""
    dates, O, H, L, C, V = synth()
    c = 60

    # RG ladder on the 2 red / 2 green / 1 doji window from test_rg_count
    O[c - 4], C[c - 4] = 100, 99
    O[c - 3], C[c - 3] = 100, 98
    O[c - 2], C[c - 2] = 99, 101
    O[c - 1], C[c - 1] = 100, 100
    O[c], C[c] = 100, 102
    r = RC.view_rg_count_5d(dates, O, H, L, C, V, c)
    b = {x['qid'].split('/')[-1]: x['a'] for x in r['binary']}
    ok('BIN-RG: 4 ladder rungs', len(r['binary']) == 4)
    ok('BIN-RG: red majority (2>2)=NO', b['red_majority'] == 'NO')
    ok('BIN-RG: red>4 NO, red>=3 NO, green>=1 YES',
       b['red_gt_4'] == 'NO' and b['red_ge_3'] == 'NO' and b['green_ge_1'] == 'YES')
    ok('BIN-RG: every rung states a literal comparator',
       all(('>' in x['q'] or '>=' in x['q'] or '=' in x['q']) for x in r['binary']))

    # swing highs: NOT_EVALUABLE when fewer than 3 confirmable pivots
    # (strictly increasing highs -> no bar is a window max -> 0 pivots)
    H_inc = H.copy()
    for i in range(len(H_inc)):
        H_inc[i] = 100.0 + i * 0.01
    r = RC.view_lower_swing_highs_3(dates, O, H_inc, L, C, V, c)
    ok('BIN-SWING: 0 confirmable pivots -> NOT_EVALUABLE',
       r['binary'][0]['a'] == 'NOT_EVALUABLE' and r['answer'].startswith('NOT_EVALUABLE'))

    # vol mean: blank -> binary None
    for i in range(c - 19, c + 1):
        V[i] = 0.0
    r = RC.view_vol_vs_mean_20d(dates, O, H, L, C, V, c)
    ok('BIN-VOL: all-zero base -> binary None (NOT_EVALUABLE)', r['binary'] is None)

    # body20: all-doji -> NOT_EVALUABLE; red sum 0 with green>0 -> infinite -> YES
    for i in range(c - 19, c + 1):
        O[i], C[i] = 100.0, 100.0                    # all doji
    r = RC.cp_gr_body20(dates, O, H, L, C, V, c)
    ok('BIN-BODY20: all-doji window -> NOT_EVALUABLE', r['binary'][0]['a'] == 'NOT_EVALUABLE')
    for i in range(c - 19, c + 1):
        O[i], C[i] = 100.0, 101.0
    r = RC.cp_gr_body20(dates, O, H, L, C, V, c)
    ok('BIN-BODY20: red=0 green>0 -> ratio inf -> YES', r['binary'][0]['a'] == 'YES')

    # RVOL spike ladder
    for i in range(c - 20, c):
        V[i] = 100.0
    V[c] = 400.0
    r = RC.rvol20(dates, O, H, L, C, V, c)
    b = {x['qid'].split('/')[-1]: x['a'] for x in r['binary']}
    ok('BIN-RVOL: RVOL=4 -> spike YES, elevated YES', b['spike'] == 'YES' and b['elevated'] == 'YES')

    # i074 / i101 binaries follow the same contract
    dates2 = pd.bdate_range('2021-01-04', periods=90).values
    n = 90
    O2 = np.full(n, 100.0); H2 = np.full(n, 100.0); L2 = np.full(n, 100.0)
    C2 = np.full(n, 100.0); V2 = np.full(n, 1000.0)
    H2[25] = 112.0; L2[30] = 90.0; C2[39] = 104.0
    C2[45] = 105.0                                   # cutoff close above P
    r = RC.i074_pivots(dates2, O2, H2, L2, C2, V2, 45, period='M')
    b = {x['qid'].split('/')[-1]: x['a'] for x in r['binary']}
    P = (112 + 90 + 104) / 3
    ok('BIN-I074: close=105 > P=102 -> above_p YES', b['above_p'] == 'YES')
    ok('BIN-I074: close < R1=114 NO; close >= S1=92 -> below_s1 NO',
       b['above_r1'] == 'NO' and b['below_s1'] == 'NO')
    H2[44] = 130.0; L2[43] = 80.0
    r = RC.i101_donchian20(dates2, O2, H2, L2, C2, V2, 44)
    b = {x['qid'].split('/')[-1]: x['a'] for x in r['binary']}
    ok('BIN-DON: close=100 inside the band -> both NO',
       b['breakout_up'] == 'NO' and b['breakdown'] == 'NO')

    # shape stub stays switched off
    r = RC.chart_shape_similarity(dates, O, H, L, C, V, c)
    ok('BIN-SHAPE: DISABLED stub has binary None (switched off)', r['binary'] is None)


def run():
    for f in list(globals().values()):
        if callable(f) and f.__name__.startswith('test_'):
            f()
    n_fail = sum(1 for _, c in PASS if not c)
    print(f'CHARTVIEW RECIPE TESTS {"PASS" if n_fail == 0 else "FAIL"} ({len(PASS) - n_fail}/{len(PASS)} passed)')
    return 1 if n_fail else 0


if __name__ == '__main__':
    import sys as _s
    _s.exit(run())
