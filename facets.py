"""Facet library for dials 1-4 (DIAL_TABLE draft 2.5). Every function answers 'as of the close of bar t'
using only bars <= t. engine.py shifts all answers by one bar, so the answer for day D uses only bars < D.
Each facet returns int8 codes (index into its label list); -1 = cannot compute (not enough history / no data)."""
import numpy as np, talib
from params import P
from numpy.lib.stride_tricks import sliding_window_view as swv

REG = []          # (variant, facet, labels, fn, lookbacks)
LB_STD = (10, 20, 60)
def facet(variant, name, labels, lbs=LB_STD):
    def deco(fn):
        REG.append((variant, name, list(labels), fn, lbs)); return fn
    return deco

def W(x, N):
    """(T,N) window matrix, row t = bars t-N+1..t; rows before N-1 are NaN."""
    x = np.asarray(x, float); T = len(x); out = np.full((T, N), np.nan)
    if T >= N: out[N-1:] = swv(x, N)
    return out

def pick(conds, valid):
    """first true condition -> its index; default = last label index if conds shorter."""
    T = len(valid); out = np.full(T, -1, np.int8)
    rem = valid.copy()
    for k, c in enumerate(conds):
        c = np.asarray(c, bool) & rem; out[c] = k; rem &= ~c
    return out

def ok(*arrs):
    v = None
    for a in arrs:
        a = np.asarray(a, float)
        m = ~np.isnan(a).any(axis=1) if a.ndim == 2 else ~np.isnan(a)
        v = m if v is None else v & m
    return v

def nanmean(a, axis=1):
    with np.errstate(all='ignore'): return np.nanmean(a, axis=axis)

def tstat_slope(Wm):
    N = Wm.shape[1]; x = np.arange(N) - (N-1)/2
    with np.errstate(all='ignore'):
        b = (Wm * x).sum(1) / (x**2).sum()
        res = Wm - Wm.mean(1, keepdims=True) - b[:, None]*x
        se = np.sqrt((res**2).sum(1)/(N-2) / (x**2).sum())
        return b / se

def zone(v, lo, hi):
    return np.where(np.isnan(v), -1, np.where(v > hi, 0, np.where(v < lo, 2, 1)))

def route9(Wm, lo, hi):
    a = zone(Wm[:, 0], lo, hi); b = zone(Wm[:, -1], lo, hi)
    return np.where((a < 0) | (b < 0), -1, a*3 + b).astype(np.int8)

def pairs(names): return [f"{a}->{b}" for a in names for b in names]

def own_pct(x, look=250):
    """percentile of x[t] within its own prior `look` values (bars < t) -> 0..100"""
    x = np.asarray(x, float); Wm = W(x, look+1)
    with np.errstate(all='ignore'):
        p = (Wm[:, :-1] < Wm[:, -1:]).sum(1) / (~np.isnan(Wm[:, :-1])).sum(1) * 100
    p[ok(Wm) == False] = np.nan
    return p

def thirds_pos(idx, N):
    return np.where(idx < N/3, 0, np.where(idx < 2*N/3, 1, 2))

# ------------------------------------------------------------------ indicators
def indicators(d):
    o, h, l, c, v = (d[k].to_numpy(dtype=float) for k in ('open', 'high', 'low', 'close', 'volume'))
    I = dict(o=o, h=h, l=l, c=c, v=v)
    I['pc'] = np.r_[np.nan, c[:-1]]
    for n in (6, 12, 24, 14): I[f'rsi{n}'] = talib.RSI(c, n)
    I['stoch'] = talib.STOCH(h, l, c, 14, 3, 0, 3, 0)[0]
    I['willr'] = talib.WILLR(h, l, c, 14)
    I['macd'] = talib.MACD(c, 12, 26, 9)[0]
    I['roc20'] = talib.ROC(c, 20); I['roc5'] = talib.ROC(c, 5); I['roc60'] = talib.ROC(c, 60)
    I['mfi'] = talib.MFI(h, l, c, v, 14)
    I['obv'] = talib.OBV(c, v); I['ad'] = talib.AD(h, l, c, v)
    I['obv_p'] = own_pct(I['obv']); I['ad_p'] = own_pct(I['ad'])
    I['atr'] = talib.ATR(h, l, c, 14); I['rng'] = h - l
    I['adx'] = talib.ADX(h, l, c, 14); I['pdi'] = talib.PLUS_DI(h, l, c, 14); I['mdi'] = talib.MINUS_DI(h, l, c, 14)
    for n in (5, 10, 20, 30, 50, 200): I[f'sma{n}'] = talib.SMA(c, n)
    I['ema21'] = talib.EMA(c, 21)
    up, mid, lo = talib.BBANDS(c, 20, 2, 2, 0); I['bbu'], I['bbm'], I['bbl'] = up, mid, lo
    kc_mid = talib.EMA(c, 20); I['kcu'] = kc_mid + 1.5*I['atr']; I['kcl'] = kc_mid - 1.5*I['atr']
    I['squeeze'] = np.where(np.isnan(up) | np.isnan(I['kcu']), np.nan, ((up < I['kcu']) & (lo > I['kcl'])).astype(float))
    I['dv'] = c * v
    I['rvol'] = v / talib.SMA(np.r_[np.nan, v[:-1]], 20)
    I['ret'] = c / I['pc'] - 1
    # Ichimoku (no forward shift of future data: cloud at t = spans computed 26 bars ago)
    hh = lambda n: talib.MAX(h, n); ll = lambda n: talib.MIN(l, n)
    I['tenkan'] = (hh(9) + ll(9))/2; I['kijun'] = (hh(26) + ll(26))/2
    sa = (I['tenkan'] + I['kijun'])/2; sb = (hh(52) + ll(52))/2
    sh = lambda x, k: np.r_[np.full(k, np.nan), x[:-k]]
    I['spa'] = sh(sa, 26); I['spb'] = sh(sb, 26)
    I['typ_rng_med60'] = pd_median(I['rng'], 60)
    return I

def pd_median(x, n):
    import pandas as pd
    return pd.Series(x).rolling(n, min_periods=n).median().to_numpy()

# ------------------------------------------------------------------ oscillator template
OSC = [  # variant, key, lo, hi, cross level, zone names
    ('RSI6', 'rsi6', 30, 70, 50), ('RSI12', 'rsi12', 30, 70, 50), ('RSI24', 'rsi24', 30, 70, 50), ('RSI14', 'rsi14', 30, 70, 50),
    ('Stoch14_3', 'stoch', 20, 80, 50), ('WilliamsR14', 'willr', -80, -20, -50), ('MACD12_26_9', 'macd', None, None, 0),
    ('ROC20', 'roc20', -5, 5, 0), ('MFI14', 'mfi', 20, 80, 50), ('OBV', 'obv_p', 20, 80, 50), ('AD_line', 'ad_p', 20, 80, 50)]

def _osc_series(I, key):
    x = I[key]
    if key == 'macd':  # zone in ATR units so it is scale-free
        x = x / I['atr']
    return x

def make_osc(variant, key, lo, hi, cl):
    if key == 'macd': lo, hi = -0.25, 0.25
    zn = ['high', 'mid', 'low']
    def series(I): return _osc_series(I, key)
    facet(variant, 'path_dir', ['rising', 'falling', 'flat'])(
        lambda I, N: (lambda Wm: pick([tstat_slope(Wm) > 2, tstat_slope(Wm) < -2, np.ones(len(Wm), bool)], ok(Wm)))(W(series(I), N)))
    facet(variant, 'zone_route', pairs(zn))(lambda I, N: route9(W(series(I), N), lo, hi))
    def cross(I, N):
        Wm = W(series(I), N) - cl; s = np.sign(Wm); ch = s[:, 1:] * s[:, :-1] < 0
        upx = (ch & (s[:, 1:] > 0)).any(1); dnx = (ch & (s[:, 1:] < 0)).any(1)
        return pick([upx & dnx, upx, dnx, np.ones(len(Wm), bool)], ok(Wm))
    REG.append((variant, 'cross_event', ['both', 'up', 'down', 'none'], cross, LB_STD))
    def div(I, N):
        P = W(I['c'], N); X = W(series(I), N); h = N//2
        p1, p2 = np.nanmin(P[:, :h], 1), np.nanmin(P[:, h:], 1)
        i1, i2 = np.nanargmin(np.nan_to_num(P[:, :h], nan=np.inf), 1), h + np.nanargmin(np.nan_to_num(P[:, h:], nan=np.inf), 1)
        r = np.arange(len(P)); x1, x2 = X[r, i1], X[r, i2]
        bull = (p2 < p1) & (x2 > x1)
        q1, q2 = np.nanmax(P[:, :h], 1), np.nanmax(P[:, h:], 1)
        j1, j2 = np.nanargmax(np.nan_to_num(P[:, :h], nan=-np.inf), 1), h + np.nanargmax(np.nan_to_num(P[:, h:], nan=-np.inf), 1)
        bear = (q2 > q1) & (X[r, j2] < X[r, j1])
        return pick([bull & ~bear, bear & ~bull, np.ones(len(P), bool)], ok(P, X))
    REG.append((variant, 'price_divergence', ['bull', 'bear', 'none'], div, LB_STD))
    def tiz(I, N):
        Wm = W(series(I), N); hi_s = (Wm > hi).mean(1); lo_s = (Wm < lo).mean(1); mid_s = 1 - hi_s - lo_s
        return pick([hi_s > .6, lo_s > .6, mid_s > .6, np.ones(len(Wm), bool)], ok(Wm))
    REG.append((variant, 'time_in_zone', ['mostly_high', 'mostly_low', 'mostly_mid', 'mixed'], tiz, LB_STD))
    def speed(I, N):
        Wm = W(series(I), N); d = np.abs(np.diff(Wm, axis=1)); k = max(1, d.shape[1]//3)
        with np.errstate(all='ignore'): r = d[:, -k:].mean(1) / d[:, :k].mean(1)
        return pick([r > 1.5, r < 0.67, np.ones(len(Wm), bool)], ok(Wm) & np.isfinite(r))
    REG.append((variant, 'speed', ['speeding_up', 'slowing_down', 'steady'], speed, LB_STD))
    def vop(I, N):
        x = series(I); Wm = W(x, N); rg = np.nanmax(Wm, 1) - np.nanmin(Wm, 1); rg[~ok(Wm)] = np.nan
        p = own_pct(rg); return pick([p > 80, p < 20, np.ones(len(p), bool)], ~np.isnan(p))
    REG.append((variant, 'vs_own_past', ['wider', 'usual', 'narrower'], vop, LB_STD))
    if variant.startswith('RSI'):
        def exit_os(I, N):
            Wm = W(series(I), N); a, b = Wm[:, :-1], Wm[:, 1:]
            eo = ((a < 30) & (b >= 30)).any(1); eb = ((a > 70) & (b <= 70)).any(1)
            # most recent wins
            lo_i = np.where(((a < 30) & (b >= 30)), np.arange(N-1), -1).max(1); hi_i = np.where(((a > 70) & (b <= 70)), np.arange(N-1), -1).max(1)
            return pick([eo & (lo_i >= hi_i), eb, np.ones(len(Wm), bool)], ok(Wm))
        REG.append((variant, 'exit_os', ['exit_os', 'exit_ob', 'none'], exit_os, LB_STD))
        def floor(I, N):
            m = np.nanmin(W(series(I), N), 1); return pick([m < 30, m < 40, m < 50, np.ones(len(m), bool)], ok(W(series(I), N)))
        REG.append((variant, 'rsi_floor', ['<30', '30-40', '40-50', '>=50'], floor, LB_STD))
        def ceil(I, N):
            Wm = W(series(I), N); m = np.nanmax(Wm, 1); return pick([m > 70, m > 60, m > 50, np.ones(len(m), bool)], ok(Wm))
        REG.append((variant, 'rsi_ceiling', ['>70', '60-70', '50-60', '<=50'], ceil, LB_STD))
        def xpos(I, N):
            Wm = W(series(I), N); v = ok(Wm); Z = np.nan_to_num(Wm)
            mx = np.argmax(Z, 1) < N/2; mn = np.argmin(Z, 1) < N/2
            return pick([mx & ~mn, ~mx & mn, mx & mn, np.ones(len(Wm), bool)], v)
        REG.append((variant, 'extreme_position', ['max_early_min_late', 'min_early_max_late', 'both_early', 'both_late'], xpos, LB_STD))

for args in OSC: make_osc(*args)

@facet('RSI12', 'length_fan', [f"{a}x{b}" for a in ['fast>mid>slow', 'slow>mid>fast', 'mixed'] for b in ['bunched', 'fanned']])
def rsi_fan(I, N):
    A, B, C = W(I['rsi6'], N), W(I['rsi12'], N), W(I['rsi24'], N)
    f = ((A > B) & (B > C)).mean(1); s = ((A < B) & (B < C)).mean(1)
    o = np.where(f > .6, 0, np.where(s > .6, 1, 2))
    sp = (np.maximum(np.maximum(A, B), C) - np.minimum(np.minimum(A, B), C)).mean(1)
    out = (o*2 + (sp >= 5)).astype(np.int8); out[~ok(A, B, C)] = -1; return out

@facet('ROC20', 'length_fan', ['fast>mid>slow', 'slow>mid>fast', 'mixed'])
def roc_fan(I, N):
    A, B, C = W(I['roc5'], N), W(I['roc20'], N), W(I['roc60'], N)
    f = ((A > B) & (B > C)).mean(1); s = ((A < B) & (B < C)).mean(1)
    return pick([f > .6, s > .6, np.ones(len(A), bool)], ok(A, B, C))

# ------------------------------------------------------------------ moving-average template
def make_ma(variant, key):
    def base(I, N): return W(I['c'], N), W(I[key], N), W(I['l'], N), W(I['h'], N)
    def above(I, N):
        C, M, _, _ = base(I, N); s = (C > M).mean(1)
        return pick([s > .6, s < .4, np.ones(len(s), bool)], ok(C, M))
    REG.append((variant, 'above_share', ['mostly_above', 'mostly_below', 'mixed'], above, LB_STD))
    def crosses(C, M):
        s = np.sign(C - M); ch = s[:, 1:] * s[:, :-1] < 0; return s, ch
    def fresh(I, N):
        C, M, _, _ = base(I, N); s, ch = crosses(C, M); k = max(2, N//5)
        upx = (ch[:, -k:] & (s[:, 1:][:, -k:] > 0)).any(1); dnx = (ch[:, -k:] & (s[:, 1:][:, -k:] < 0)).any(1)
        return pick([upx & dnx, upx, dnx, np.ones(len(C), bool)], ok(C, M))
    REG.append((variant, 'fresh_cross', ['both', 'up', 'down', 'none'], fresh, LB_STD))
    def ccount(I, N):
        C, M, _, _ = base(I, N); _, ch = crosses(C, M); n = ch.sum(1)
        return pick([n == 0, n <= 2, n <= 5, np.ones(len(n), bool)], ok(C, M))
    REG.append((variant, 'cross_count', ['0', '1-2', '3-5', '6+'], ccount, LB_STD))
    def slope(I, N):
        _, M, _, _ = base(I, N); r = M[:, -1]/M[:, 0] - 1
        return pick([r > .01, r < -.01, np.ones(len(r), bool)], ok(M))
    REG.append((variant, 'slope', ['up', 'down', 'flat'], slope, LB_STD))
    def dist(I, N):
        C, M, _, _ = base(I, N); d = np.abs(C/M - 1)
        with np.errstate(all='ignore'): r = d[:, -1] / (d[:, 0] + 1e-9)
        return pick([r > 1.25, r < 0.8, np.ones(len(r), bool)], ok(C, M))
    REG.append((variant, 'distance_route', ['stretching', 'reverting', 'stable'], dist, LB_STD))
    def tests(I, N):
        C, M, L, H = base(I, N)
        sup = (L <= M) & (C > M); res = (H >= M) & (C < M); s, ch = crosses(C, M)
        brk = np.c_[np.zeros(len(C), bool), ch]
        idx = lambda m: np.where(m, np.arange(N), -1).max(1)
        a, b, k = idx(sup), idx(res), idx(brk); last = np.maximum(np.maximum(a, b), k)
        return pick([(k == last) & (k >= 0), (a == last) & (a >= 0), (b == last) & (b >= 0), np.ones(len(C), bool)], ok(C, M, L, H))
    REG.append((variant, 'tests', ['broke', 'support_held', 'resistance_held', 'none'], tests, LB_STD))
    def speed(I, N):
        _, M, _, _ = base(I, N); h = N//2
        a = np.abs(M[:, h-1]/M[:, 0] - 1); b = np.abs(M[:, -1]/M[:, h] - 1)
        with np.errstate(all='ignore'): r = b/(a + 1e-9)
        return pick([r > 1.5, r < 0.67, np.ones(len(r), bool)], ok(M))
    REG.append((variant, 'speed', ['speeding_up', 'slowing_down', 'steady'], speed, LB_STD))
for v, k in [('SMA20', 'sma20'), ('SMA50', 'sma50'), ('SMA200', 'sma200'), ('EMA21', 'ema21')]: make_ma(v, k)

MAG = 'MA_group(10/20/50/200)'
def _stack(I):  # formula column of the table uses SMA5/10/20/30 for the group
    a, b, c_, d = I['sma5'], I['sma10'], I['sma20'], I['sma30']
    pairs_bull = (a > b).astype(int) + (b > c_) + (c_ > d); pairs_bear = (a < b).astype(int) + (b < c_) + (c_ < d)
    st = np.where(pairs_bull == 3, 0, np.where(pairs_bear == 3, 3, np.where(pairs_bull >= 2, 1, np.where(pairs_bear >= 2, 2, 1))))
    st = st.astype(float); st[np.isnan(d)] = np.nan; return st
STK = ['full_bull', 'partial_bull', 'partial_bear', 'full_bear']
@facet(MAG, 'stack_route', pairs(STK))
def stack_route(I, N):
    S = W(_stack(I), N); out = (S[:, 0]*4 + S[:, -1]); out[~ok(S)] = -1; return out.astype(np.int8)
@facet(MAG, 'stack_flip', ['golden', 'death', 'none'])
def stack_flip(I, N):
    S = W(_stack(I), N); a, b = S[:, :-1], S[:, 1:]
    g = ((b == 0) & (a != 0)).any(1); d = ((b == 3) & (a != 3)).any(1)
    return pick([g & ~d, d & ~g, np.ones(len(S), bool)], ok(S))
@facet(MAG, 'time_bull_stack', ['most', 'some', 'none'])
def tbs(I, N):
    S = W(_stack(I), N); s = (S <= 1).mean(1); return pick([s > .6, s > 0, np.ones(len(s), bool)], ok(S))
@facet(MAG, 'full_stack_streak', [f"{a}x{b}" for a in ['bull', 'bear'] for b in ['0', '1-4', '5-19', '20+']], lbs=(1,))
def streak(I, N):
    st = _stack(I); T = len(st); out = np.full(T, -1, np.int8); run = 0; prev = None
    for t in range(T):
        x = st[t]
        if np.isnan(x): run = 0; prev = None; continue
        side = 0 if x <= 1 else 1; full = x in (0, 3)
        run = run + 1 if (full and prev == x) else (1 if full else 0); prev = x
        b = 0 if run == 0 else 1 if run < 5 else 2 if run < 20 else 3
        out[t] = side*4 + b
    return out
@facet(MAG, 'days_since_partial_flip', ['<5', '5-20', '>20', 'none'], lbs=(60,))
def dspf(I, N):
    st = _stack(I); side = np.where(np.isnan(st), np.nan, (st >= 2).astype(float))
    S = W(side, N); ch = S[:, 1:] != S[:, :-1]
    last = np.where(ch, np.arange(1, N), -1).max(1); age = N - 1 - last
    return pick([(last >= 0) & (age < 5), (last >= 0) & (age <= 20), last >= 0, np.ones(len(S), bool)], ok(S))
@facet(MAG, 'fan_out', ['fanning', 'converging', 'steady'])
def fan(I, N):
    spread = (np.nanmax(np.c_[I['sma5'], I['sma10'], I['sma20'], I['sma30']], 1) - np.nanmin(np.c_[I['sma5'], I['sma10'], I['sma20'], I['sma30']], 1)) / I['atr']
    spread[np.isnan(I['sma30'])] = np.nan; S = W(spread, N); r = S[:, -1]/(S[:, 0] + 1e-9)
    return pick([r > 1.3, r < 0.77, np.ones(len(S), bool)], ok(S))
@facet(MAG, 'bunching_route', pairs(['tight', 'mid', 'wide']))
def bunch(I, N):
    M = np.c_[I['sma5'], I['sma10'], I['sma20'], I['sma30']]
    sp = (M.max(1) - M.min(1)) / I['atr']; S = W(sp, N)
    z = lambda x: np.where(x < 1, 0, np.where(x > 3, 2, 1))
    out = (z(S[:, 0])*3 + z(S[:, -1])).astype(np.int8); out[~ok(S)] = -1; return out
@facet(MAG, 'price_inside', ['mostly_inside', 'mostly_outside'])
def pinside(I, N):
    M = np.c_[I['sma5'], I['sma10'], I['sma20'], I['sma30']]
    ins = ((I['c'] <= M.max(1)) & (I['c'] >= M.min(1))).astype(float); ins[np.isnan(I['sma30'])] = np.nan
    S = W(ins, N); return pick([S.mean(1) > .5, np.ones(len(S), bool)], ok(S))
@facet(MAG, 'deepest_pullback_ma', ['MA10', 'MA20', 'MA30', 'broke_MA30', 'none'])
def deep_pb(I, N):
    L, C = W(I['l'], N), W(I['c'], N); m10, m20, m30 = W(I['sma10'], N), W(I['sma20'], N), W(I['sma30'], N)
    return pick([(C < m30).any(1), (L <= m30).any(1), (L <= m20).any(1), (L <= m10).any(1), np.ones(len(L), bool)], ok(L, m30))

# reorder deep_pb codes to match label order
_orig = REG[-1]
def _dp(I, N):
    x = _orig[3](I, N); m = {0: 3, 1: 2, 2: 1, 3: 0, 4: 4}; out = x.copy()
    for k, v in m.items(): out[x == k] = v
    return out
REG[-1] = (_orig[0], _orig[1], _orig[2], _dp, _orig[4])

# ------------------------------------------------------------------ candles
@facet('OHLC', 'intraday_change', ['up>1%', 'down<-1%', 'flat'])
def intraday(I, N):
    X = W((I['c'] - I['o'])/I['o'], N); m = X.mean(1); return pick([m > .01, m < -.01, np.ones(len(m), bool)], ok(X))
@facet('OHLC', 'interday_change', ['up>5%', 'flat', 'down>5%'])
def interday(I, N):
    C = W(I['c'], N); r = C[:, -1]/C[:, 0] - 1; return pick([r > .05, r >= -.05, np.ones(len(r), bool)], ok(C))
@facet('OHLC', 'overnight_vs_intraday', [f"{a}x{b}" for a in ['up_move', 'down_move'] for b in ['gap_driven', 'intraday_driven', 'mixed']])
def ovi(I, N):
    g = W(np.log(I['o']/I['pc']), N).sum(1); d = W(np.log(I['c']/I['o']), N).sum(1); tot = g + d
    share = np.abs(g)/(np.abs(g) + np.abs(d) + 1e-12)
    k = np.where(share > .6, 0, np.where(share < .4, 1, 2)); out = ((tot < 0)*3 + k).astype(np.int8)
    out[np.isnan(tot)] = -1; return out
def _gap(I, N, up):
    H, L = I['h'], I['l']; T = len(H)
    gap = (I['o'] > np.r_[np.nan, H[:-1]]) if up else (I['o'] < np.r_[np.nan, L[:-1]])
    ref = np.r_[np.nan, H[:-1]] if up else np.r_[np.nan, L[:-1]]
    out = np.full(T, -1, np.int8)
    gi = np.where(gap)[0]
    # for each t: most recent gap within window and whether filled by t
    last = -10**9; lastref = np.nan; filled = False
    for t in range(T):
        if gap[t]:
            last, lastref, filled = t, ref[t], False
        elif last > -1 and not filled:
            if (up and L[t] <= lastref) or ((not up) and H[t] >= lastref): filled = True
        if t < N-1: continue
        out[t] = 2 if t - last >= N else (0 if filled else 1)
    return out
def in_set(a, t): return False
facet('OHLC', 'gap_up', ['filled', 'open', 'none'])(lambda I, N: _gap(I, N, True))
facet('OHLC', 'gap_down', ['filled', 'open', 'none'])(lambda I, N: _gap(I, N, False))
@facet('OHLC', 'inside_outside', ['inside_cluster>=2', 'outside_after_inside', 'mostly_outside', 'none'])
def inout(I, N):
    H, L = I['h'], I['l']; ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    ins = ((H < ph) & (L > pl)).astype(float); outb = ((H > ph) & (L < pl)).astype(float)
    A, B = W(ins, N), W(outb, N)
    cl = (A[:, 1:] * A[:, :-1]).sum(1) > 0; oai = (B[:, 1:] * A[:, :-1]).sum(1) > 0
    return pick([cl, oai, B.mean(1) > .3, np.ones(len(A), bool)], ok(W(ph, N)))
@facet('OHLC', 'red_green_balance', ['green>1.5', 'red<0.67', 'even'])
def rgb(I, N):
    g = W((I['c'] > I['o']).astype(float), N).sum(1); r = W((I['c'] < I['o']).astype(float), N).sum(1)
    x = g/np.maximum(r, 1); return pick([x > 1.5, x < .67, np.ones(len(x), bool)], ok(W(I['c'], N)))
@facet('OHLC', 'last_green_vs_red', ['green_bigger', 'red_bigger', 'similar'])
def lgr(I, N):
    body = I['c'] - I['o']; T = len(body); out = np.full(T, -1, np.int8); lg = lr = np.nan; tg = tr = -10**9
    for t in range(T):
        if body[t] > 0: lg, tg = body[t], t
        elif body[t] < 0: lr, tr = -body[t], t
        if t < N-1 or t - tg >= N or t - tr >= N: continue
        out[t] = 0 if lg > 1.25*lr else 1 if lr > 1.25*lg else 2
    return out
@facet('OHLC', 'wick_body', ['upper_dominant', 'lower_dominant', 'balanced'])
def wickb(I, N):
    rng = I['h'] - I['l'] + 1e-12; uw = (I['h'] - np.maximum(I['o'], I['c']))/rng; lw = (np.minimum(I['o'], I['c']) - I['l'])/rng
    d = W(uw - lw, N).mean(1); return pick([d > .15, d < -.15, np.ones(len(d), bool)], ~np.isnan(d))
@facet('OHLC', 'close_location_route', [f"{a}x{b}" for a in ['near_high_mostly', 'near_low_mostly', 'mixed'] for b in ['improving', 'worsening', 'steady']])
def clr(I, N):
    cl = (I['c'] - I['l'])/(I['h'] - I['l'] + 1e-12); X = W(cl, N); m = X.mean(1); sl = tstat_slope(X)
    a = np.where(m > .6, 0, np.where(m < .4, 1, 2)); b = np.where(sl > 2, 0, np.where(sl < -2, 1, 2))
    out = (a*3 + b).astype(np.int8); out[~ok(X)] = -1; return out
@facet('OHLC', 'size_vs_chart', ['larger', 'similar', 'smaller'])
def svc(I, N):
    R = W(I['rng'], N); r = R[:, -max(1, N//5):].mean(1)/R.mean(1); return pick([r > 1.25, r < .8, np.ones(len(r), bool)], ok(R))
def _runs(sign_row):
    runs = []; cur = 0; cnt = 0
    for s in sign_row:
        if s == cur and s != 0: cnt += 1
        else:
            if cur != 0: runs.append((cur, cnt))
            cur, cnt = s, 1
    if cur != 0: runs.append((cur, cnt))
    return runs
@facet('OHLC', 'run_structure', ['green_longer', 'red_longer', 'equal'])
def runstruct(I, N):
    s = np.sign(I['c'] - I['pc']); T = len(s); out = np.full(T, -1, np.int8)
    for t in range(N, T):
        rr = _runs(s[t-N+1:t+1]); g = max([n for v, n in rr if v > 0] or [0]); r = max([n for v, n in rr if v < 0] or [0])
        out[t] = 0 if g > r else 1 if r > g else 2
    return out
@facet('OHLC', 'run_biggest_move', ['big>1.5ATR', 'normal', 'small'])
def runbig(I, N):
    C = W(I['c'], N); A = W(I['atr'], N); d = np.abs(np.diff(C, axis=1)); m = np.nanmax(d, 1)/A[:, -1]
    return pick([m > 1.5, m > .5, np.ones(len(m), bool)], ok(C, A))
@facet('OHLC', 'down_vs_up_moves', ['downs_bigger', 'ups_bigger', 'equal'])
def dvu(I, N):
    R = W(I['ret'], N); u = np.where(R > 0, R, np.nan); dn = np.where(R < 0, -R, np.nan)
    with np.errstate(all='ignore'): x = np.nanmean(dn, 1)/np.nanmean(u, 1)
    return pick([x > 1.2, x < 1/1.2, np.ones(len(x), bool)], ok(R) & np.isfinite(x))
def _pat(I, fns):
    return np.vstack([np.sign(getattr(talib, f)(I['o'], I['h'], I['l'], I['c'])) for f in fns])
@facet('OHLC', 'pattern_1d_mix', ['bull_reversal', 'bear_reversal', 'indecision', 'trend', 'none'])
def p1(I, N):
    fam = [(_pat(I, ['CDLHAMMER', 'CDLINVERTEDHAMMER']) != 0).sum(0), (_pat(I, ['CDLSHOOTINGSTAR', 'CDLHANGINGMAN']) != 0).sum(0),
           (_pat(I, ['CDLDOJI', 'CDLSPINNINGTOP']) != 0).sum(0), (_pat(I, ['CDLMARUBOZU']) != 0).sum(0)]
    S = np.stack([W(f.astype(float), N).sum(1) for f in fam], 1); tot = S.sum(1)
    out = np.where(tot == 0, 4, np.argmax(S, 1)).astype(np.int8); out[np.isnan(tot)] = -1; return out
@facet('OHLC', 'pattern_2d_mix', ['bull', 'bear', 'none'])
def p2(I, N):
    P = _pat(I, ['CDLENGULFING', 'CDLHARAMI', 'CDLPIERCING', 'CDLDARKCLOUDCOVER'])
    b = W((P > 0).sum(0).astype(float), N).sum(1); r = W((P < 0).sum(0).astype(float), N).sum(1)
    return pick([(b > r), (r > b), np.ones(len(b), bool)], ~np.isnan(b))
@facet('OHLC', 'pattern_3d_seen', [f"{a}x{b}" for a in ['3ws', '3bc', 'morning_star', 'evening_star'] for b in ['early', 'late']] + ['none'])
def p3(I, N):
    fs = ['CDL3WHITESOLDIERS', 'CDL3BLACKCROWS', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR']
    T = len(I['c']); out = np.full(T, -1, np.int8); best = np.full(T, 8, np.int8); lastpos = np.full(T, -1)
    for k, f in enumerate(fs):
        Wm = W((getattr(talib, f)(I['o'], I['h'], I['l'], I['c']) != 0).astype(float), N)
        li = np.where(Wm > 0, np.arange(N), -1).max(1); upd = li > lastpos
        best[upd] = k*2 + (li[upd] >= N/2); lastpos = np.maximum(lastpos, li)
    best[np.arange(T) < N-1] = -1; return best

# ------------------------------------------------------------------ volume
@facet('RVOL20', 'trend', ['rising', 'falling', 'flat'])
def rv_tr(I, N):
    X = W(np.log(I['rvol']), N); t = tstat_slope(X); return pick([t > 2, t < -2, np.ones(len(t), bool)], ok(X))
@facet('RVOL20', 'spike', ['yes_early', 'yes_late', 'no'])
def rv_sp(I, N):
    X = W(I['rvol'], N); sp = X > 3; li = np.where(sp, np.arange(N), -1).max(1)
    return pick([(li >= 0) & (li < N/2), li >= N/2, np.ones(len(X), bool)], ok(X))
@facet('RVOL20', 'dry_up_at_low', ['at_low', 'at_high', 'both', 'none'])
def rv_dry(I, N):
    X, C = W(I['rvol'], N), W(I['c'], N); r = np.arange(len(X))
    lo = X[r, np.argmin(np.nan_to_num(C, nan=np.inf), 1)] < .67; hi = X[r, np.argmax(np.nan_to_num(C, nan=-np.inf), 1)] < .67
    return pick([lo & hi, lo, hi, np.ones(len(X), bool)], ok(X, C))
_o = REG[-1]; REG[-1] = (_o[0], _o[1], _o[2], (lambda f: lambda I, N: (lambda x: np.select([x == 0, x == 1, x == 2], [2, 0, 1], x).astype(np.int8))(f(I, N)))(_o[3]), _o[4])
@facet('RVOL20', 'price_confirm', ['confirm', 'diverge', 'neutral'])
def rv_pc(I, N):
    C, V = W(I['c'], N), W(np.log(I['v'] + 1), N); pt = tstat_slope(C); vt = tstat_slope(V)
    return pick([(np.abs(pt) > 2) & (vt > 2), (np.abs(pt) > 2) & (vt < -2), np.ones(len(C), bool)], ok(C, V))
@facet('RVOL20', 'vs_own_past', ['high', 'normal', 'low'])
def rv_vop(I, N):
    m = W(I['v'], N).mean(1); base = own_base(I['v'], N); r = m/base
    return pick([r > 1.5, r < .67, np.ones(len(r), bool)], np.isfinite(r))
def own_base(v, N):
    """mean volume of the 250 bars before the window"""
    import pandas as pd
    s = pd.Series(v).rolling(250, min_periods=250).mean().shift(N).to_numpy(); return s
@facet('RVOL20', 'spike_then', ['continued', 'reversed', 'no_spike'])
def rv_st(I, N):
    X, C = W(I['rvol'], N), W(I['c'], N); T = len(X); out = np.full(T, -1, np.int8); v = ok(X, C)
    li = np.where(X > 3, np.arange(N), -1).max(1)
    for t in np.where(v)[0]:
        i = li[t]
        if i < 0: out[t] = 2; continue
        d0 = np.sign(C[t, i] - (C[t, i-1] if i > 0 else C[t, i])); d1 = np.sign(C[t, -1] - C[t, i])
        out[t] = 0 if d0*d1 > 0 else 1 if d0*d1 < 0 else 2
    return out
@facet('RVOL20', 'max_vol_position', ['start', 'middle', 'at_price_low', 'end'])
def rv_mp(I, N):
    V, C = W(I['v'], N), W(I['c'], N); iv = np.argmax(np.nan_to_num(V, nan=-1), 1); ic = np.argmin(np.nan_to_num(C, nan=np.inf), 1)
    th = thirds_pos(iv, N); out = np.where(np.abs(iv - ic) <= 2, 2, np.where(th == 2, 3, th)).astype(np.int8); out[~ok(V, C)] = -1; return out
@facet('RVOL20', 'segment_compare', ['rally_heavier', 'decline_heavier', 'similar'])
def rv_seg(I, N):
    V, C = W(I['v'], N), W(I['c'], N); T = len(V); out = np.full(T, -1, np.int8)
    for t in np.where(ok(V, C))[0]:
        i = int(np.argmin(C[t]))
        if i < 2 or i > N-3: out[t] = 2; continue
        a, b = V[t, :i].mean(), V[t, i:].mean(); out[t] = 0 if b > 1.25*a else 1 if a > 1.25*b else 2
    return out

def _dvol_trend(I, N):
    X = W(np.log(I['dv'] + 1), N); t = tstat_slope(X); return pick([t > 2, t < -2, np.ones(len(t), bool)], ok(X))
facet('dollar_volume', 'trend', ['rising', 'falling', 'flat'])(_dvol_trend)
@facet('dollar_volume', 'liquidity_tier_route', pairs(['<1M', '1-10M', '>10M']))
def dv_tier(I, N):
    X = W(I['dv'], N); k = max(1, N//4); a = np.median(X[:, :k], 1); b = np.median(X[:, -k:], 1)
    z = lambda x: np.where(x < 1e6, 0, np.where(x <= 1e7, 1, 2)); out = (z(a)*3 + z(b)).astype(np.int8); out[~ok(X)] = -1; return out
@facet('dollar_volume', 'consistency', ['all', 'most', 'few'])
def dv_cons(I, N):
    X = W(I['dv'], N); s = (X >= 1e6).mean(1); return pick([s == 1, s >= .6, np.ones(len(s), bool)], ok(X))
@facet('dollar_volume', 'concentration', ['concentrated>50%', 'spread'])
def dv_conc(I, N):
    X = W(I['dv'], N); k = max(1, N//10); top = -np.sort(-np.nan_to_num(X), 1)[:, :k].sum(1)/X.sum(1)
    return pick([top > .5, np.ones(len(X), bool)], ok(X))
@facet('dollar_volume', 'speed', ['speeding_up', 'slowing_down', 'steady'])
def dv_speed(I, N):
    X = W(I['dv'], N); h = N//2; r = X[:, h:].mean(1)/(X[:, :h].mean(1) + 1); return pick([r > 1.5, r < .67, np.ones(len(r), bool)], ok(X))
@facet('dollar_volume', 'vs_own_past', ['high', 'normal', 'low'])
def dv_vop(I, N):
    m = W(I['dv'], N).mean(1); r = m/own_base(I['dv'], N); return pick([r > 1.5, r < .67, np.ones(len(r), bool)], np.isfinite(r))

def _udr(I, N):
    up = np.where(I['c'] > I['pc'], I['v'], 0.); dn = np.where(I['c'] < I['pc'], I['v'], 0.)
    return W(up, N), W(dn, N)
@facet('up_down_volume', 'dominance', ['up_heavy>1.3', 'down_heavy<0.77', 'even'])
def ud_dom(I, N):
    U, D = _udr(I, N); r = U.sum(1)/(D.sum(1) + 1); return pick([r > 1.3, r < .77, np.ones(len(r), bool)], ok(U))
@facet('up_down_volume', 'trend', ['improving', 'worsening', 'flat'])
def ud_tr(I, N):
    U, D = _udr(I, N); h = N//2; r1 = U[:, :h].sum(1)/(D[:, :h].sum(1) + 1); r2 = U[:, h:].sum(1)/(D[:, h:].sum(1) + 1); x = r2/(r1 + 1e-9)
    return pick([x > 1.3, x < .77, np.ones(len(x), bool)], ok(U))
@facet('up_down_volume', 'price_divergence', ['bull', 'bear', 'none'])
def ud_div(I, N):
    U, D = _udr(I, N); C = W(I['c'], N); r = U.sum(1)/(D.sum(1) + 1); pr = C[:, -1]/C[:, 0] - 1
    return pick([(pr < 0) & (r > 1.3), (pr > 0) & (r < .77), np.ones(len(r), bool)], ok(U, C))
@facet('up_down_volume', 'flip', ['to_up', 'to_down', 'none'])
def ud_flip(I, N):
    U, D = _udr(I, N); h = N//2; r1 = U[:, :h].sum(1)/(D[:, :h].sum(1) + 1); r2 = U[:, h:].sum(1)/(D[:, h:].sum(1) + 1)
    return pick([(r1 < 1) & (r2 > 1), (r1 > 1) & (r2 < 1), np.ones(len(r1), bool)], ok(U))
@facet('up_down_volume', 'run', ['long', 'short'])
def ud_run(I, N):
    U, D = _udr(I, N); s = np.sign(U - D); T = len(s); out = np.full(T, -1, np.int8)
    for t in np.where(ok(U))[0]:
        rr = _runs(s[t]); m = max([n for _, n in rr] or [0]); out[t] = 0 if m >= 5 else 1
    return out
@facet('up_down_volume', 'vs_own_past', ['unusual_up', 'unusual_down', 'typical'])
def ud_vop(I, N):
    U, D = _udr(I, N); r = np.log((U.sum(1) + 1)/(D.sum(1) + 1)); p = own_pct(r)
    return pick([p > 90, p < 10, np.ones(len(p), bool)], ~np.isnan(p))

# anchored VWAP (anchor = first bar of window)
def _vwap(I, N):
    tp = (I['h'] + I['l'] + I['c'])/3; PV, V = W(tp*I['v'], N), W(I['v'], N)
    with np.errstate(all='ignore'): vw = np.cumsum(PV, 1)/np.cumsum(V, 1)
    return vw, W(I['c'], N)
@facet('VWAP_anchored', 'above_share', ['mostly_above', 'mostly_below', 'mixed'])
def vw_ab(I, N):
    vw, C = _vwap(I, N); s = (C > vw).mean(1); return pick([s > .6, s < .4, np.ones(len(s), bool)], ok(vw, C))
@facet('VWAP_anchored', 'cross', ['both', 'up', 'down', 'none'])
def vw_cr(I, N):
    vw, C = _vwap(I, N); s = np.sign(C - vw); ch = s[:, 1:]*s[:, :-1] < 0
    u = (ch & (s[:, 1:] > 0)).any(1); d = (ch & (s[:, 1:] < 0)).any(1); return pick([u & d, u, d, np.ones(len(C), bool)], ok(vw, C))
@facet('VWAP_anchored', 'distance_route', ['stretching', 'reverting', 'stable'])
def vw_dr(I, N):
    vw, C = _vwap(I, N); h = N//2; a = np.abs(C[:, h]/vw[:, h] - 1); b = np.abs(C[:, -1]/vw[:, -1] - 1); r = b/(a + 1e-9)
    return pick([r > 1.25, r < .8, np.ones(len(r), bool)], ok(vw, C))
@facet('VWAP_anchored', 'slope', ['up', 'down', 'flat'])
def vw_sl(I, N):
    vw, C = _vwap(I, N); r = vw[:, -1]/vw[:, 1] - 1; return pick([r > .01, r < -.01, np.ones(len(r), bool)], ok(vw, C))
@facet('VWAP_anchored', 'reclaim', ['yes', 'no'])
def vw_rc(I, N):
    vw, C = _vwap(I, N); below = (C < vw)[:, :-1].any(1); return pick([below & (C[:, -1] > vw[:, -1]), np.ones(len(C), bool)], ok(vw, C))

# ------------------------------------------------------------------ range position
def _range_tmpl(variant, hi_fn, lo_fn):
    def get(I, N):
        H, L = hi_fn(I, N), lo_fn(I, N); C = W(I['c'], N); return H, L, C
    def zr(I, N):
        H, L, C = get(I, N); P = (C - L)/(H - L + 1e-12); z = lambda x: np.where(x > 2/3, 0, np.where(x < 1/3, 2, 1))
        out = (z(P[:, 0])*3 + z(P[:, -1])).astype(np.int8); out[~ok(H, L, C)] = -1; return out
    REG.append((variant, 'zone_route', pairs(['top', 'mid', 'bottom']), zr, LB_STD))
    def tt(I, N):
        H, L, C = get(I, N); P = (C - L)/(H - L + 1e-12); s = (P > 2/3).mean(1); return pick([s > .6, s > 0, np.ones(len(s), bool)], ok(H, L, C))
    REG.append((variant, 'time_top', ['most', 'some', 'none'], tt, LB_STD))
    def wr(I, N):
        H, L, C = get(I, N); w = (H - L)/C; r = w[:, -1]/(w[:, 0] + 1e-12); return pick([r < .8, r > 1.25, np.ones(len(r), bool)], ok(H, L, C))
    REG.append((variant, 'width_route', ['narrowing', 'widening', 'stable'], wr, LB_STD))
    def mc(I, N):
        H, L, C = get(I, N); s = np.sign(C - (H + L)/2); ch = s[:, 1:]*s[:, :-1] < 0
        u = (ch & (s[:, 1:] > 0)).any(1); d = (ch & (s[:, 1:] < 0)).any(1); return pick([u & d, u, d, np.ones(len(C), bool)], ok(H, L, C))
    REG.append((variant, 'midline_cross', ['both', 'up', 'down', 'none'], mc, LB_STD))
    return get
def _don_h(I, N): return W(np.r_[np.nan, talib.MAX(I['h'], 20)[:-1]], N)
def _don_l(I, N): return W(np.r_[np.nan, talib.MIN(I['l'], 20)[:-1]], N)
_range_tmpl('Donchian20', _don_h, _don_l)
def _hilo_h(I, N): H = W(I['h'], N); return np.repeat(np.nanmax(H, 1)[:, None], N, 1) + 0*H
def _hilo_l(I, N): L = W(I['l'], N); return np.repeat(np.nanmin(L, 1)[:, None], N, 1) + 0*L
_range_tmpl('HiLo_window', _hilo_h, _hilo_l)
def _brk(variant, H, L, C, N):
    up = C > H; dn = C < L
    lu = np.where(up, np.arange(N), -1).max(1); ld = np.where(dn, np.arange(N), -1).max(1)
    return up, dn, lu, ld
@facet('Donchian20', 'breakout', ['up', 'down', 'none'])
def don_b(I, N):
    H, L, C = _don_h(I, N), _don_l(I, N), W(I['c'], N); up, dn, lu, ld = _brk(0, H, L, C, N)
    return pick([(lu >= 0) & (lu >= ld), ld >= 0, np.ones(len(C), bool)], ok(H, L, C))
@facet('Donchian20', 'failed_break', ['bull_trap', 'bear_trap', 'none'])
def don_f(I, N):
    H, L, C = _don_h(I, N), _don_l(I, N), W(I['c'], N); up, dn, lu, ld = _brk(0, H, L, C, N); r = np.arange(len(C))
    bt = (lu >= 0) & (C[:, -1] < H[r, np.maximum(lu, 0)]); br = (ld >= 0) & (C[:, -1] > L[r, np.maximum(ld, 0)])
    return pick([bt & (lu >= ld), br, np.ones(len(C), bool)], ok(H, L, C))
@facet('HiLo_window', 'breakout', ['up', 'down', 'none'])
def hl_b(I, N):  # last bar vs the window before it
    H, L, C = W(I['h'], N), W(I['l'], N), W(I['c'], N)
    u = C[:, -1] > np.nanmax(H[:, :-1], 1); d = C[:, -1] < np.nanmin(L[:, :-1], 1); return pick([u, d, np.ones(len(C), bool)], ok(H, L, C))
@facet('HiLo_window', 'failed_break', ['bull_trap', 'bear_trap', 'none'])
def hl_f(I, N):
    H, L, C = W(I['h'], N), W(I['l'], N), W(I['c'], N); k = max(2, N//5); hb = np.nanmax(H[:, :-k], 1); lb = np.nanmin(L[:, :-k], 1)
    bt = (H[:, -k:].max(1) > hb) & (C[:, -1] < hb); br = (L[:, -k:].min(1) < lb) & (C[:, -1] > lb)
    return pick([bt, br, np.ones(len(C), bool)], ok(H, L, C))

def _bb(I, N):
    return W(I['bbu'], N), W(I['bbl'], N), W(I['c'], N), W(I['bbm'], N)
@facet('Bollinger20_2', 'zone_route', pairs(['top', 'mid', 'bottom']))
def bb_z(I, N):
    U, L, C, M = _bb(I, N); P = (C - L)/(U - L + 1e-12); z = lambda x: np.where(x > .8, 0, np.where(x < .2, 2, 1))
    out = (z(P[:, 0])*3 + z(P[:, -1])).astype(np.int8); out[~ok(U, C)] = -1; return out
@facet('Bollinger20_2', 'band_walk', ['upper', 'lower', 'none'])
def bb_w(I, N):
    U, L, C, M = _bb(I, N); T = len(C); out = np.full(T, -1, np.int8); v = ok(U, C)
    a = (C >= U*0.99); b = (C <= L*1.01)
    def mrun(x): 
        best = cur = 0
        for e in x: cur = cur + 1 if e else 0; best = max(best, cur)
        return best
    for t in np.where(v)[0]: out[t] = 0 if mrun(a[t]) >= 3 else 1 if mrun(b[t]) >= 3 else 2
    return out
@facet('Bollinger20_2', 'reentry', ['from_below', 'from_above', 'none'])
def bb_r(I, N):
    U, L, C, M = _bb(I, N); fb = ((C[:, :-1] < L[:, :-1]) & (C[:, 1:] >= L[:, 1:])); fa = ((C[:, :-1] > U[:, :-1]) & (C[:, 1:] <= U[:, 1:]))
    a = np.where(fb, np.arange(N-1), -1).max(1); b = np.where(fa, np.arange(N-1), -1).max(1)
    return pick([(a >= 0) & (a >= b), b >= 0, np.ones(len(C), bool)], ok(U, C))
@facet('Bollinger20_2', 'time_upper', ['upper', 'lower', 'balanced'])
def bb_t(I, N):
    U, L, C, M = _bb(I, N); s = (C > M).mean(1); return pick([s > .6, s < .4, np.ones(len(s), bool)], ok(U, C))
@facet('Bollinger20_2', 'pctb_path', ['rising', 'falling', 'flat'])
def bb_p(I, N):
    U, L, C, M = _bb(I, N); P = (C - L)/(U - L + 1e-12); t = tstat_slope(P); return pick([t > 2, t < -2, np.ones(len(t), bool)], ok(U, C))
@facet('Bollinger20_2', 'width_route', ['squeezing', 'widening', 'stable'])
def bb_wr(I, N):
    U, L, C, M = _bb(I, N); w = (U - L)/M; r = w[:, -1]/(w[:, 0] + 1e-12); return pick([r < .8, r > 1.25, np.ones(len(r), bool)], ok(U, C))

# ------------------------------------------------------------------ momentum (ADX / Ichimoku)
@facet('ADX14', 'trend_strength_route', pairs(['trending', 'weak', 'none']))
def adx_r(I, N):
    X = W(I['adx'], N); z = lambda x: np.where(x > 25, 0, np.where(x < 15, 2, 1)); out = (z(X[:, 0])*3 + z(X[:, -1])).astype(np.int8); out[~ok(X)] = -1; return out
@facet('ADX14', 'di_cross', ['bull', 'bear', 'none'])
def adx_dc(I, N):
    P, M = W(I['pdi'], N), W(I['mdi'], N); s = np.sign(P - M); ch = s[:, 1:]*s[:, :-1] < 0
    li = np.where(ch, np.arange(1, N), -1).max(1); r = np.arange(len(P)); last = s[r, np.maximum(li, 0)]
    return pick([(li > 0) & (last > 0), (li > 0) & (last < 0), np.ones(len(P), bool)], ok(P, M))
@facet('ADX14', 'adx_slope', ['rising', 'falling', 'flat'])
def adx_s(I, N):
    X = W(I['adx'], N); d = X[:, -1] - X[:, 0]; return pick([d > 5, d < -5, np.ones(len(d), bool)], ok(X))
@facet('ADX14', 'peak_turn', ['yes', 'no'])
def adx_pt(I, N):
    X = W(I['adx'], N); m = np.nanmax(X, 1); return pick([(m > 25) & (X[:, -1] < m - 5) & (np.argmax(np.nan_to_num(X), 1) < N-1), np.ones(len(X), bool)], ok(X))
@facet('ADX14', 'time_trending', ['most', 'some', 'none'])
def adx_tt(I, N):
    X = W(I['adx'], N); s = (X > 25).mean(1); return pick([s > .6, s > 0, np.ones(len(s), bool)], ok(X))
@facet('ADX14', 'speed', ['speeding', 'slowing', 'steady'])
def adx_sp(I, N):
    X = W(I['adx'], N); h = N//2; a = X[:, h] - X[:, 0]; b = X[:, -1] - X[:, h]
    return pick([b > a + 3, b < a - 3, np.ones(len(X), bool)], ok(X))
def _cloud(I): return np.fmax(I['spa'], I['spb']), np.fmin(I['spa'], I['spb'])
@facet('Ichimoku', 'cloud_route', pairs(['above', 'in', 'below']), lbs=(10, 20, 60))
def ich_r(I, N):
    top, bot = _cloud(I); pos = np.where(I['c'] > top, 0, np.where(I['c'] < bot, 2, 1)).astype(float); pos[np.isnan(top)] = np.nan
    S = W(pos, N); out = (S[:, 0]*3 + S[:, -1]); out[~ok(S)] = -1; return out.astype(np.int8)
@facet('Ichimoku', 'tk_cross', ['bull', 'bear', 'none'])
def ich_tk(I, N):
    A, B = W(I['tenkan'], N), W(I['kijun'], N); s = np.sign(A - B); ch = s[:, 1:]*s[:, :-1] < 0
    li = np.where(ch, np.arange(1, N), -1).max(1); r = np.arange(len(A)); last = s[r, np.maximum(li, 0)]
    return pick([(li > 0) & (last > 0), (li > 0) & (last < 0), np.ones(len(A), bool)], ok(A, B))
@facet('Ichimoku', 'cloud_twist', ['bull', 'bear', 'none'])
def ich_tw(I, N):
    A, B = W(I['spa'], N), W(I['spb'], N); s = np.sign(A - B); ch = s[:, 1:]*s[:, :-1] < 0
    li = np.where(ch, np.arange(1, N), -1).max(1); r = np.arange(len(A)); last = s[r, np.maximum(li, 0)]
    return pick([(li > 0) & (last > 0), (li > 0) & (last < 0), np.ones(len(A), bool)], ok(A, B))
@facet('Ichimoku', 'time_above', ['most', 'some', 'none'])
def ich_ta(I, N):
    top, _ = _cloud(I); a = (I['c'] > top).astype(float); a[np.isnan(top)] = np.nan; S = W(a, N); s = S.mean(1)
    return pick([s > .6, s > 0, np.ones(len(s), bool)], ok(S))
@facet('Ichimoku', 'chikou_route', ['improving', 'worsening', 'same'])
def ich_ch(I, N):
    c = I['c']; ch = c - np.r_[np.full(26, np.nan), c[:-26]]; S = W(np.sign(ch), N); a, b = S[:, 0], S[:, -1]
    return pick([b > a, b < a, np.ones(len(S), bool)], ok(S))
@facet('Ichimoku', 'kijun_tests', ['support_held', 'resistance_held', 'broke', 'none'])
def ich_kt(I, N):
    C, M, L, H = W(I['c'], N), W(I['kijun'], N), W(I['l'], N), W(I['h'], N)
    sup = (L <= M) & (C > M); res = (H >= M) & (C < M); s = np.sign(C - M); brk = np.c_[np.zeros(len(C), bool), s[:, 1:]*s[:, :-1] < 0]
    idx = lambda m: np.where(m, np.arange(N), -1).max(1); a, b, k = idx(sup), idx(res), idx(brk); last = np.maximum(np.maximum(a, b), k)
    return pick([(a == last) & (a >= 0) & (a > k), (b == last) & (b >= 0) & (b > k), k >= 0, np.ones(len(C), bool)], ok(C, M))

# ------------------------------------------------------------------ volatility
@facet('ATR14', 'trend', ['expanding', 'contracting', 'flat'])
def atr_t(I, N):
    X = W(I['atr']/I['c'], N); r = X[:, -1]/X[:, 0]; return pick([r > 1.2, r < .83, np.ones(len(r), bool)], ok(X))
@facet('ATR14', 'vs_own_past', ['high', 'normal', 'low'])
def atr_v(I, N):
    p = own_pct(I['atr']/I['c']); X = W(p, 1); return pick([p > 80, p < 20, np.ones(len(p), bool)], ~np.isnan(p))
@facet('ATR14', 'shock', ['3-5xxearly', '3-5xxlate', '>5xxearly', '>5xxlate', 'none'])
def atr_sh(I, N):
    import pandas as pd
    med = pd.Series(I['rng']).rolling(250, min_periods=250).median().shift(N).to_numpy()
    R = W(I['rng'], N); x = np.nanmax(R, 1)/med; i = np.argmax(np.nan_to_num(R), 1); late = i >= N/2
    return pick([(x >= 3) & (x < 5) & ~late, (x >= 3) & (x < 5) & late, (x >= 5) & ~late, (x >= 5) & late, np.ones(len(x), bool)], np.isfinite(x))
@facet('ATR14', 'vol_direction_link', ['down_vol', 'up_vol', 'neutral'])
def atr_dl(I, N):
    R, Rt = W(I['rng']/I['c'], N), W(I['ret'], N)
    with np.errstate(all='ignore'):
        dn = np.nanmean(np.where(Rt < 0, R, np.nan), 1); up = np.nanmean(np.where(Rt > 0, R, np.nan), 1)
    x = dn/up; return pick([x > 1.2, x < 1/1.2, np.ones(len(x), bool)], ok(R, Rt) & np.isfinite(x))
@facet('ATR14', 'route', pairs(['low', 'mid', 'high']))
def atr_rt(I, N):
    p = own_pct(I['atr']/I['c']); S = W(p, N); z = lambda x: np.where(x < 33, 0, np.where(x > 67, 2, 1))
    out = (z(S[:, 0])*3 + z(S[:, -1])).astype(np.int8); out[~ok(S)] = -1; return out
@facet('ATR14', 'speed', ['speeding', 'slowing', 'steady'])
def atr_sp(I, N):
    X = W(I['atr'], N); h = N//2; a = X[:, h]/X[:, 0]; b = X[:, -1]/X[:, h]; return pick([b > a*1.15, b < a/1.15, np.ones(len(X), bool)], ok(X))
@facet('ATR14', 'range_max_position', ['start', 'middle', 'end'])
def atr_mp(I, N):
    R = W(I['rng'], N); out = thirds_pos(np.argmax(np.nan_to_num(R), 1), N).astype(np.int8); out[~ok(R)] = -1; return out
@facet('ATR14', 'segment_compare', ['expanded', 'contracted', 'similar'])
def atr_sc(I, N):
    R, C = W(I['rng'], N), W(I['c'], N); T = len(R); out = np.full(T, -1, np.int8); k = max(2, N//5)
    for t in np.where(ok(R, C))[0]:
        i = int(np.argmax(C[t])); a = R[t, max(0, i-2):i+3].mean(); b = R[t, -k:].mean()
        out[t] = 0 if b > 1.25*a else 1 if b < .8*a else 2
    return out
@facet('ATR14', 'range_calming', [f"{a}x{b}" for a in ['after_crash', 'after_spike'] for b in ['calming', 'steady', 'expanding']] + ['none'], lbs=(60,))
def atr_cal(I, N):
    A, C = W(I['atr'], N), W(I['c'], N); k = 20 if N >= 40 else max(2, N//3); r = A[:, -1]/A[:, k-1]
    tot = C[:, -1]/C[:, 0] - 1; mx = np.nanmax(C, 1)/C[:, 0] - 1; mn = np.nanmin(C, 1)/C[:, 0] - 1
    crash = mn < -.2; spike = (mx > .2) & ~crash; b = np.where(r < .7, 0, np.where(r > 1.3, 2, 1))
    out = np.where(crash, b, np.where(spike, 3 + b, 6)).astype(np.int8); out[~ok(A, C)] = -1; return out

SQ = 'squeeze(BB_in_Keltner)'
@facet(SQ, 'state_route', pairs(['in', 'out']))
def sq_r(I, N):
    S = W(I['squeeze'], N); out = ((1 - S[:, 0])*2 + (1 - S[:, -1])); out[~ok(S)] = -1; return out.astype(np.int8)
def _release(I, N):
    S = W(I['squeeze'], N); rel = (S[:, :-1] == 1) & (S[:, 1:] == 0); li = np.where(rel, np.arange(1, N), -1).max(1); return S, li
@facet(SQ, 'release_dir', ['up', 'down', 'none'])
def sq_d(I, N):
    S, li = _release(I, N); C, M = W(I['c'], N), W(I['bbm'], N); r = np.arange(len(S)); i = np.maximum(li, 0)
    return pick([(li > 0) & (C[r, i] > M[r, i]), li > 0, np.ones(len(S), bool)], ok(S))
@facet(SQ, 'duration', ['long>=10', 'short', 'none'])
def sq_du(I, N):
    S = W(I['squeeze'], N); T = len(S); out = np.full(T, -1, np.int8)
    for t in np.where(ok(S))[0]:
        rr = _runs(np.where(S[t] == 1, 1, -1)); m = max([n for v, n in rr if v > 0] or [0]); out[t] = 0 if m >= 10 else 1 if m > 0 else 2
    return out
@facet(SQ, 'time_in', ['most', 'some', 'none'])
def sq_t(I, N):
    S = W(I['squeeze'], N); s = S.mean(1); return pick([s > .6, s > 0, np.ones(len(s), bool)], ok(S))
@facet(SQ, 'release_volume', ['>3x', '1.5-3x', '<1.5x', 'no_release'])
def sq_v(I, N):
    S, li = _release(I, N); V = W(I['v'], N); r = np.arange(len(S)); i = np.maximum(li, 0)
    with np.errstate(all='ignore'): base = np.nanmean(np.where(S == 1, V, np.nan), 1)
    x = V[r, i]/base; return pick([(li > 0) & (x > 3), (li > 0) & (x > 1.5), li > 0, np.ones(len(S), bool)], ok(S, V))
@facet(SQ, 'release_close_location', ['top_third', 'middle', 'bottom_third', 'no_release'])
def sq_cl(I, N):
    S, li = _release(I, N); cl = W((I['c'] - I['l'])/(I['h'] - I['l'] + 1e-12), N); r = np.arange(len(S)); x = cl[r, np.maximum(li, 0)]
    return pick([(li > 0) & (x > 2/3), (li > 0) & (x >= 1/3), li > 0, np.ones(len(S), bool)], ok(S))
@facet(SQ, 'release_gap', ['gap>1x_width', 'gap<1x_width', 'no_gap', 'no_release'])
def sq_g(I, N):
    S, li = _release(I, N); g = W(np.abs(I['o'] - I['pc'])/(I['bbu'] - I['bbl'] + 1e-12), N); gp = W(((I['o'] > I['pc']*1.005) | (I['o'] < I['pc']*.995)).astype(float), N)
    r = np.arange(len(S)); i = np.maximum(li, 0); x = g[r, i]; has = gp[r, i] > 0
    return pick([(li > 0) & has & (x > 1), (li > 0) & has, li > 0, np.ones(len(S), bool)], ok(S))

# ------------------------------------------------------------------ return path
@facet('daily_returns', 'efficiency', ['smooth<2', 'mid', 'choppy>5'])
def dr_e(I, N):
    C = W(I['c'], N); x = np.abs(np.diff(C, axis=1)).sum(1)/(np.abs(C[:, -1] - C[:, 0]) + 1e-12)
    return pick([x < 2, x <= 5, np.ones(len(x), bool)], ok(C))
@facet('daily_returns', 'speed', ['speeding', 'slowing', 'steady'])
def dr_s(I, N):
    R = W(I['ret'], N); h = N//2; a = np.abs(R[:, :h]).mean(1); b = np.abs(R[:, h:]).mean(1); x = b/(a + 1e-12)
    return pick([x > 1.3, x < .77, np.ones(len(x), bool)], ok(R))
@facet('daily_returns', 'skew', ['pos', 'neg', 'neutral'])
def dr_sk(I, N):
    R = W(I['ret'], N); m = R.mean(1, keepdims=True); s = R.std(1)
    with np.errstate(all='ignore'): sk = ((R - m)**3).mean(1)/s**3
    return pick([sk > .5, sk < -.5, np.ones(len(sk), bool)], ok(R) & np.isfinite(sk))
@facet('daily_returns', 'autocorr', ['trending', 'mean_reverting', 'none'])
def dr_ac(I, N):
    R = W(I['ret'], N); a, b = R[:, 1:], R[:, :-1]; a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
    with np.errstate(all='ignore'): rho = (a*b).sum(1)/np.sqrt((a*a).sum(1)*(b*b).sum(1))
    th = 2/np.sqrt(N); return pick([rho > th, rho < -th, np.ones(len(rho), bool)], ok(R) & np.isfinite(rho))
@facet('daily_returns', 'route', ['up_down', 'down_up', 'straight_up', 'straight_down', 'flat'])
def dr_r(I, N):
    C = W(I['c'], N); h = N//2; a = C[:, h]/C[:, 0] - 1; b = C[:, -1]/C[:, h] - 1; A = W(I['atr']/I['c'], N)[:, -1]*np.sqrt(h)
    u1, d1, u2, d2 = a > A, a < -A, b > A, b < -A
    return pick([u1 & d2, d1 & u2, (u1 | u2) & ~d1 & ~d2, (d1 | d2) & ~u1 & ~u2, np.ones(len(C), bool)], ok(C) & np.isfinite(A))
@facet('daily_returns', 'tail_event', ['up', 'down', 'none'])
def dr_t(I, N):
    import pandas as pd
    sd = pd.Series(I['ret']).rolling(250, min_periods=120).std().shift(N).to_numpy(); R = W(I['ret'], N)
    mx = np.nanmax(R, 1)/sd; mn = np.nanmin(R, 1)/sd; return pick([mx > 4, mn < -4, np.ones(len(R), bool)], ok(R) & np.isfinite(sd))
@facet('daily_returns', 'down_vs_up', ['downs_bigger', 'ups_bigger', 'equal'])
def dr_dvu(I, N):
    R = W(I['ret'], N); dn = -np.where(R < 0, R, 0).sum(1); up = np.where(R > 0, R, 0).sum(1); x = dn/(up + 1e-12)
    return pick([x > 1.2, x < 1/1.2, np.ones(len(x), bool)], ok(R))
@facet('daily_returns', 'segment_compare', ['rally_steeper', 'decline_steeper', 'similar'])
def dr_sc(I, N):
    C = W(I['c'], N); T = len(C); out = np.full(T, -1, np.int8)
    for t in np.where(ok(C))[0]:
        i = int(np.argmin(C[t]))
        if i < 2 or i > N-3: out[t] = 2; continue
        d = abs(np.log(C[t, i]/C[t, 0]))/i; u = abs(np.log(C[t, -1]/C[t, i]))/(N-1-i)
        out[t] = 0 if u > 1.25*d else 1 if d > 1.25*u else 2
    return out

# ------------------------------------------------------------------ extremes
@facet('new_highs_lows', 'new_extreme', ['high', 'low', 'both', 'none'])
def nh_e(I, N):
    H, L = W(I['h'], N), W(I['l'], N); import pandas as pd
    ph = pd.Series(I['h']).rolling(N, min_periods=N).max().shift(N).to_numpy(); pl = pd.Series(I['l']).rolling(N, min_periods=N).min().shift(N).to_numpy()
    hi = np.nanmax(H, 1) > ph; lo = np.nanmin(L, 1) < pl; return pick([hi & ~lo, lo & ~hi, hi & lo, np.ones(len(H), bool)], ok(H) & ~np.isnan(ph))
def _newhi_flags(I, look=20):
    import pandas as pd
    ph = pd.Series(I['h']).rolling(look, min_periods=look).max().shift(1).to_numpy(); return (I['h'] > ph).astype(float), ph
@facet('new_highs_lows', 'count', ['0', '1-2', '3+'])
def nh_c(I, N):
    f, ph = _newhi_flags(I); S = W(np.where(np.isnan(ph), np.nan, f), N); n = S.sum(1); return pick([n == 0, n <= 2, np.ones(len(n), bool)], ok(S))
@facet('new_highs_lows', 'time_since', ['recent', 'mid', 'old', 'none'])
def nh_ts(I, N):
    f, ph = _newhi_flags(I); S = W(np.where(np.isnan(ph), np.nan, f), N); li = np.where(S > 0, np.arange(N), -1).max(1); age = N - 1 - li
    return pick([(li >= 0) & (age < N/3), (li >= 0) & (age < 2*N/3), li >= 0, np.ones(len(S), bool)], ok(S))
@facet('new_highs_lows', 'high_then_low', ['high_first', 'low_first'])
def nh_hl(I, N):
    H, L = W(I['h'], N), W(I['l'], N); return pick([np.argmax(np.nan_to_num(H), 1) < np.argmin(np.nan_to_num(L, nan=np.inf), 1), np.ones(len(H), bool)], ok(H, L))
@facet('new_highs_lows', 'follow_through', ['yes', 'no', 'no_new_high'])
def nh_ft(I, N):
    f, ph = _newhi_flags(I); S = W(np.where(np.isnan(ph), np.nan, f), N); C, H = W(I['c'], N), W(I['h'], N)
    li = np.where(S > 0, np.arange(N), -1).max(1); fi = np.where(S > 0, np.arange(N), N).min(1); r = np.arange(len(S))
    yes = (li >= 0) & (C[:, -1] > H[r, np.minimum(fi, N-1)]); return pick([yes, li >= 0, np.ones(len(S), bool)], ok(S, C))
@facet('new_highs_lows', 'giveback', [f"{a}xwhole_run" for a in ['none<10%', 'partial', 'most>60%']])
def nh_gb(I, N):
    C = W(I['c'], N); T = len(C); out = np.full(T, -1, np.int8)
    ip = np.argmax(np.nan_to_num(C), 1)
    for t in np.where(ok(C))[0]:
        p = ip[t]; lo = C[t, :p+1].min(); pk = C[t, p]; x = (pk - C[t, -1])/(pk - lo + 1e-12) if pk > lo else 0
        out[t] = 0 if x < .1 else 2 if x > .6 else 1
    return out
@facet('drawdown', 'depth', ['shallow<2', 'mid', 'deep>5'])
def dd_d(I, N):
    C, A = W(I['c'], N), W(I['atr'], N); pk = np.maximum.accumulate(np.nan_to_num(C), 1); dd = ((pk - C)/A[:, -1:]).max(1)
    return pick([dd < 2, dd <= 5, np.ones(len(dd), bool)], ok(C, A))
@facet('drawdown', 'recovery', ['full', 'partial', 'none'])
def dd_r(I, N):
    C = W(I['c'], N); T = len(C); out = np.full(T, -1, np.int8)
    pk = np.maximum.accumulate(np.nan_to_num(C), 1); dd = (pk - C)/pk
    i = np.argmax(dd, 1); r = np.arange(T); trough = C[r, i]; peak = pk[r, i]; x = (C[:, -1] - trough)/(peak - trough + 1e-12)
    return pick([(x >= .999) | (dd.max(1) == 0), x > .2, np.ones(T, bool)], ok(C))
@facet('drawdown', 'count', ['0', '1', '2+'])
def dd_c(I, N):
    C, A = W(I['c'], N), W(I['atr'], N); T = len(C); out = np.full(T, -1, np.int8); v = ok(C, A)
    for t in np.where(v)[0]:
        pk = C[t, 0]; ind = False; n = 0; a = A[t, -1]*2
        for x in C[t]:
            if x > pk: pk = x; ind = False
            elif pk - x >= a and not ind: n += 1; ind = True
        out[t] = min(n, 2)
    return out
@facet('drawdown', 'vs_own_past', ['unusual', 'typical', 'small'])
def dd_v(I, N):
    C = W(I['c'], N); pk = np.maximum.accumulate(np.nan_to_num(C), 1); dd = ((pk - C)/pk).max(1); dd[~ok(C)] = np.nan; p = own_pct(dd)
    return pick([p > 90, p > 30, np.ones(len(p), bool)], ~np.isnan(p))
@facet('drawdown', 'move_duration', [f"{a}x{b}" for a in ['down', 'up'] for b in ['<10', '10-40', '>40 days']], lbs=(60,))
def dd_md(I, N):
    C = W(I['c'], N); ih = np.argmax(np.nan_to_num(C), 1); il = np.argmin(np.nan_to_num(C, nan=np.inf), 1)
    down = ih < il; start = np.where(down, ih, il); dur = N - 1 - start; b = np.where(dur < 10, 0, np.where(dur <= 40, 1, 2))
    out = ((~down)*3 + b).astype(np.int8); out[~ok(C)] = -1; return out
@facet('drawdown', 'climax_context', [f"{a}x{b}" for a in ['after_single_sharp_move', 'end_of_long_trend(>=60 bars)', 'mid_trend', 'none'] for b in ['fresh_overnight_shock', 'long_intraday_bleed']], lbs=(120,))
def dd_cc(I, N):
    """leg = move >= 3x the stock's typical daily range (median H-L of prior 60 bars); long trend = >= 60 bars.
    Uses the last leg ending at t: its start = most recent bar where |C_t - C_s| first reached 3x typical range going back."""
    C, O, PC = I['c'], I['o'], I['pc']; tr = I['typ_rng_med60']; T = len(C); out = np.full(T, -1, np.int8)
    ln_g = np.log(O/PC); ln_d = np.log(C/O)
    for t in range(N, T):
        if np.isnan(tr[t]) or np.isnan(C[t-N]): continue
        seg = C[t-N:t+1]; d = np.abs(seg[-1] - seg[::-1]); hit = np.where(d >= P['leg_atr']*tr[t])[0]
        if len(hit) == 0: out[t] = 3*2 + 1; continue
        L = hit[0]  # bars back to where the leg started
        g = np.nansum(ln_g[t-L+1:t+1]); dd_ = np.nansum(ln_d[t-L+1:t+1]); b = 0 if abs(g) > abs(dd_) else 1
        a = 0 if L <= 5 else 1 if L >= P['long_trend'] else 2
        out[t] = a*2 + b
    return out
def _52(I):
    import pandas as pd
    h = pd.Series(I['h']).rolling(252, min_periods=252).max().to_numpy(); l = pd.Series(I['l']).rolling(252, min_periods=252).min().to_numpy(); return h, l
@facet('52w_range', 'dist_route', pairs(['near<5%', 'mid', 'far>30%']))
def w52_dr(I, N):
    h, l = _52(I); d = 1 - I['c']/h; S = W(d, N); z = lambda x: np.where(x < .05, 0, np.where(x > .3, 2, 1))
    out = (z(S[:, 0])*3 + z(S[:, -1])).astype(np.int8); out[~ok(S)] = -1; return out
@facet('52w_range', 'touch_52w', ['high', 'low', 'none'])
def w52_t(I, N):
    h, l = _52(I); H, L, A, B = W(I['h'], N), W(I['l'], N), W(h, N), W(l, N)
    return pick([(H >= A).any(1), (L <= B).any(1), np.ones(len(H), bool)], ok(A))
@facet('52w_range', 'closing_speed', ['faster', 'slower', 'steady'])
def w52_cs(I, N):
    h, l = _52(I); S = W(1 - I['c']/h, N); k = N//2; a = S[:, 0] - S[:, k]; b = S[:, k] - S[:, -1]
    return pick([b > a + .02, b < a - .02, np.ones(len(S), bool)], ok(S))
@facet('52w_range', 'rejection', ['yes', 'no'])
def w52_rj(I, N):
    h, l = _52(I); H, C, A = W(I['h'], N), W(I['c'], N), W(h, N); return pick([(H >= A*.99).any(1) & (C[:, -1] < A[:, -1]*.95), np.ones(len(H), bool)], ok(A))
@facet('52w_range', 'position_share', ['most', 'some', 'none'])
def w52_ps(I, N):
    h, l = _52(I); P = W((I['c'] - l)/(h - l + 1e-12), N); s = (P > .75).mean(1); return pick([s > .6, s > 0, np.ones(len(s), bool)], ok(P))
@facet('52w_range', 'range_width', ['wide', 'normal', 'narrow'], lbs=(1,))
def w52_w(I, N):
    h, l = _52(I); x = h/l; return pick([x > 2, x < 1.3, np.ones(len(x), bool)], ~np.isnan(x))
# big picture (needs up to 756 bars; history_short flagged by engine)
def _rollmax(x, n):
    import pandas as pd; return pd.Series(x).rolling(n, min_periods=n).max().to_numpy()
def _rollmin(x, n):
    import pandas as pd; return pd.Series(x).rolling(n, min_periods=n).min().to_numpy()
@facet('big_picture', 'multi_year_position', [f"{a}x{b}" for a in ['1y', '2y', '3y'] for b in ['top_quartile', 'mid', 'bottom_quartile']], lbs=(252, 504, 756))
def bp_myp(I, N):
    h, l = _rollmax(I['h'], N), _rollmin(I['l'], N); p = (I['c'] - l)/(h - l + 1e-12); y = 0 if N <= 252 else (1 if N <= 504 else 2)   # tree also asks short windows (e.g. 5d x 10): bucket by size, no KeyError
    k = np.where(p > .75, 0, np.where(p < .25, 2, 1)); out = (y*3 + k).astype(np.int8); out[np.isnan(h)] = -1; return out
@facet('big_picture', 'dist_from_high', ['<10%', '10-50%', '>50%'], lbs=(756,))
def bp_dh(I, N):
    h = _rollmax(I['h'], N); d = 1 - I['c']/h; return pick([d < .1, d <= .5, np.ones(len(d), bool)], ~np.isnan(d))
@facet('big_picture', 'ath_age', [f"{a}x{b}" for a in ['high', 'low'] for b in ['<60', '60-250', '>250']], lbs=(756,))
def bp_age(I, N):
    H, L = W(I['h'], N), W(I['l'], N); ah = N - 1 - np.argmax(np.nan_to_num(H), 1); al = N - 1 - np.argmin(np.nan_to_num(L, nan=np.inf), 1)
    hi = ah <= al; age = np.where(hi, ah, al); out = ((~hi)*3 + np.where(age < 60, 0, np.where(age <= 250, 1, 2))).astype(np.int8); out[~ok(H)] = -1; return out
def _weekly(I):
    c = I['c']; return talib.SMA(c, 50), talib.SMA(c, 100), talib.SMA(c, 200)  # ~10/20/40-week MAs from daily bars
@facet('big_picture', 'weekly_trend', ['rising', 'falling', 'flat'], lbs=(100,))
def bp_wt(I, N):
    a, b, c = _weekly(I); r = b/np.r_[np.full(N, np.nan), b[:-N]] - 1; return pick([r > .03, r < -.03, np.ones(len(r), bool)], ~np.isnan(r))
@facet('big_picture', 'weekly_stack', ['bull', 'bear', 'mixed'], lbs=(1,))
def bp_ws(I, N):
    a, b, c = _weekly(I); return pick([(a > b) & (b > c), (a < b) & (b < c), np.ones(len(a), bool)], ~np.isnan(c))
@facet('big_picture', 'range_route', pairs(['low', 'mid', 'high']), lbs=(252,))
def bp_rr(I, N):
    h, l = _rollmax(I['h'], 756), _rollmin(I['l'], 756); p = (I['c'] - l)/(h - l + 1e-12); S = W(p, N)
    z = lambda x: np.where(x < 1/3, 0, np.where(x > 2/3, 2, 1)); out = (z(S[:, 0])*3 + z(S[:, -1])).astype(np.int8); out[~ok(S)] = -1; return out

# ------------------------------------------------------------------ support / resistance: round numbers
def _bucket(c): return np.where(c < 1, 0, np.where(c < 5, 1, np.where(c < 20, 2, np.where(c < 100, 3, 4))))
RN = 'round_numbers(merged price level)'
@facet(RN, 'bucket_route', pairs(['<1', '1-5', '5-20', '20-100', '>100']))
def rn_b(I, N):
    C = W(I['craw'], N); out = (_bucket(C[:, 0])*5 + _bucket(C[:, -1])).astype(np.int8); out[~ok(C)] = -1; return out
@facet(RN, 'sub_dollar_share', ['all', 'some', 'none'])
def rn_s(I, N):
    C = W(I['craw'], N); s = (C < 1).mean(1); return pick([s == 1, s > 0, np.ones(len(s), bool)], ok(C))
def _step(c): return np.where(c < 10, 1., np.where(c < 100, 10., 100.))
@facet(RN, 'cross_round', ['up', 'down', 'none'])
def rn_c(I, N):
    C = W(I['craw'], N); st = _step(C[:, -1:]); k = np.floor(C/st); ch = np.diff(k, axis=1)
    li_u = np.where(ch > 0, np.arange(N-1), -1).max(1); li_d = np.where(ch < 0, np.arange(N-1), -1).max(1)
    return pick([(li_u >= 0) & (li_u >= li_d), li_d >= 0, np.ones(len(C), bool)], ok(C))
@facet(RN, 'rejection', ['yes', 'no'])
def rn_r(I, N):
    H, C = W(I['hraw'], N), W(I['craw'], N); st = _step(C[:, -1:]); lvl = np.ceil(C/st)*st
    rej = (H >= lvl) & (C < lvl); return pick([rej.any(1), np.ones(len(C), bool)], ok(C))
@facet(RN, 'approach_route', ['approaching', 'leaving'])
def rn_a(I, N):
    C = W(I['craw'], N); st = _step(C[:, -1:]); lv = np.round(C[:, -1:]/st)*st
    d0 = np.abs(C[:, 0]/lv[:, 0] - 1); d1 = np.abs(C[:, -1]/lv[:, 0] - 1); return pick([d1 < d0, np.ones(len(C), bool)], ok(C))
@facet(RN, 'magnet', ['yes', 'no'])
def rn_m(I, N):
    C = W(I['craw'], N); st = _step(C[:, -1:]); lv = np.round(C[:, -1:]/st)*st; near = np.abs(C/lv - 1) < .02
    return pick([near.mean(1) > .5, np.ones(len(C), bool)], ok(C))

# ------------------------------------------------------------------ calendar (known in advance; uses D's own date, no prices)
CAL = []  # computed in engine on the target date D directly (no shift)
