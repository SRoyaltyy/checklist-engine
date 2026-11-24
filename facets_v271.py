from datapaths import D
"""v2.7.1 history questions coded straight from HISTORY_BUCKETS_v2.7.1_FINAL.csv (sha d8adbb46...9f69, hard-checked).
Rules tested in file order, first match wins; missing data -> -1 (n_a). Window W = last N bars (of k-day bars) ending at t;
engine shifts one bar so W ends D-1. unit = ATR14 for price series, else sX = std of 1-bar changes of X over the 250 bars before W."""
import numpy as np, pandas as pd, talib, hashlib, re
from facets import W, ok, tstat_slope
from params import P
BUCKETS = D('/workspace/checklist_dials/v2.7.1/HISTORY_BUCKETS_v2.7.1_FINAL.csv')
VSER = D('/workspace/checklist_dials/v2.7.1/VARIANT_SERIES_v2.7.1.csv')
SHA_HEAD, SHA_TAIL = 'd8adbb46', '9f69'
LAB = {}; APPLIES = {}; UNIT_ATR = set(); FILE_SHA = None

def load_buckets(path=BUCKETS):
    global FILE_SHA
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    if not (sha.startswith(SHA_HEAD) and sha.endswith(SHA_TAIL)): raise SystemExit(f'HISTORY_BUCKETS sha mismatch: {sha} - not running')
    FILE_SHA = sha; b = pd.read_csv(path)
    for hv, g in b.groupby('history_value', sort=False):
        LAB[hv] = list(g.locked_label); APPLIES[hv] = set(g.applies_to_lever1_types.iloc[0].split('|'))
    v = pd.read_csv(VSER)
    for r in v.itertuples():
        if str(r.unit).startswith('ATR14'): UNIT_ATR.add(r.variant)
    return sha

def code(hv, conds, valid):
    """conds: list of (label, bool array) in file order; first match wins; unmatched valid rows -> error (rules must be exhaustive)."""
    T = len(valid); out = np.full(T, -1, np.int8); rem = valid.copy(); L = LAB[hv]
    for lab, c in conds:
        c = np.asarray(c, bool) & rem; out[c] = L.index(lab); rem &= ~c
    if rem.any(): raise ValueError(f'{hv}: {rem.sum()} rows matched no rule')
    return out

# ---------------- primary series X per VARIANT_SERIES_v2.7.1 ----------------
def series(I, v):
    a = I['atr']; c = I['c']
    M = {'RSI6': 'rsi6', 'RSI12': 'rsi12', 'RSI24': 'rsi24', 'RSI14': 'rsi14', 'Stoch14_3': 'stoch', 'WilliamsR14': 'willr',
         'MFI14': 'mfi', 'ROC20': 'roc20', 'ADX14': 'adx', 'RVOL20': 'rvol', 'OBV': 'obv', 'AD_line': 'ad'}
    with np.errstate(all='ignore'):
        if v in M: return I[M[v]]
        if v in ('OHLC', 'new_highs_lows', 'big_picture', 'base_and_run', '52w_range', 'prior_pivots', 'old_ranges_breakdowns', 'unfilled_gaps'): return c
        if v == 'drawdown': return (c - np.fmax.accumulate(np.nan_to_num(I['h'], nan=-np.inf)))/a
        if v == 'round_numbers(merged price level)': return c
        if v == 'MACD12_26_9': return talib.MACD(c, 12, 26, 9)[2]
        if v in ('SMA20', 'SMA50', 'SMA200', 'EMA21'): return (c - I[v.lower()])/a
        if v == 'MA_group(10/20/50/200)': return (I['sma10'] - I['sma200'])/a
        if v == 'daily_returns': return np.log(c/I['pc'])
        if v == 'dollar_volume': return I['dv']
        if v == 'up_down_volume':
            up = talib.SUM(np.where(I['ret'] > 0, I['v'], 0.), 10); dn = talib.SUM(np.where(I['ret'] < 0, I['v'], 0.), 10); return up/np.where(dn > 0, dn, np.nan)
        if v == 'ATR14': return a/c
        if v == 'squeeze(BB_in_Keltner)': return (I['bbu'] - I['bbl'])/(I['kcu'] - I['kcl'])
        if v == 'Bollinger20_2': return (c - I['bbl'])/(I['bbu'] - I['bbl'])
        if v == 'Donchian20': hh, ll = talib.MAX(I['h'], 20), talib.MIN(I['l'], 20); return (c - ll)/(hh - ll)
        if v == 'HiLo_window': hh, ll = talib.MAX(I['h'], 60), talib.MIN(I['l'], 60); return (c - ll)/(hh - ll)
        if v == 'Ichimoku': return (c - (I['spa'] + I['spb'])/2)/a
        if v == 'vs_SPY': return c/I['spy']
        if v == 'SPY_VIX': return I['spy']
        if v == 'float_turnover': return I['vraw']/I['shares']
        if v == 'reg_sho': return pd.Series(I['regsho']).rolling(20, min_periods=1).sum().to_numpy()
        if v == 'halts': return I.get('halt_cnt')              # groups 034+: per-bar halt count
        if v == 'short_interest': return I.get('si_rep')       # per-bar FINRA SI report count (publication-date keyed)
        if v == 'earnings': return I.get('earn_cnt')           # per-bar earnings report count
        if v == '3ATR_legs':
            from facets_v26 import phases_asof
            Ps = phases_asof(I); return np.array([ps[-1]['size'] if ps else np.nan for ps in Ps])
        if v == 'calendar_context' and 'dates' in I:
            # LEAK FIX: share of the quarter elapsed, using the exchange calendar (known in advance), not this stock's own bar count
            # for the whole quarter (that counted bars after D).
            d = pd.DatetimeIndex(I['dates']); S = pd.DatetimeIndex(I['sessions']) if 'sessions' in I else d
            sq = pd.Series(1, index=S).groupby(S.to_period('Q')); first = sq.apply(lambda g: g.index[0]); size = sq.size()
            q = d.to_period('Q'); f0 = pd.DatetimeIndex(first.reindex(q).values)
            s = np.searchsorted(S.values, d.values) - np.searchsorted(S.values, f0.values)
            n = size.reindex(q).to_numpy(float); return s/n
    return None   # vs_sector_peers, vs_theme_peers, VWAP_anchored, volume_profile, Fibonacci_swing, events, checklist_score_path: no series yet

def unit_of(I, v, X, N):
    if v in UNIT_ATR:
        if v in ('SPY_VIX',): pass
        elif v in ('drawdown', 'SMA20', 'SMA50', 'SMA200', 'EMA21', 'MA_group(10/20/50/200)'): return np.ones(len(X))  # already in ATR
        else: return I['atr'].astype(float)
    d = pd.Series(np.r_[np.nan, np.diff(X)]).rolling(int(P['hist_250']), min_periods=int(P['hist_250']*0.8)).std().shift(N).to_numpy()   # 250 bars before W
    return np.where(d > 0, d, np.nan)

def _sh(x, k):
    """shift right by k, fill first k with NaN, drop last k. k >= len(x) -> all NaN, len(x)
    (short-history tickers used to get len-k arrays here and broadcast-crash the history questions)."""
    x = np.asarray(x, float)
    if not k: return x
    if k >= len(x): return np.full(len(x), np.nan)
    return np.r_[np.full(k, np.nan), x[:-k]]

def _last_true_idx(m):
    """per row of bool matrix: last column index that is True, else -1"""
    N = m.shape[1]; r = np.where(m.any(1), N - 1 - np.argmax(m[:, ::-1], 1), -1); return r

def _pivots(x, k):
    """C08 strict pivots of a series: bar i qualifies only if x_i is STRICTLY beyond all k bars
    each side (ties disqualify). Confirmed at i+k; callers only use confirmed pivots (i <= t-k).
    Returns bool arrays hi, lo indexed at the pivot bar."""
    sx = pd.Series(x)
    mx_l = sx.shift(1).rolling(k).max().to_numpy(); mx_r = sx.shift(-k).rolling(k).max().to_numpy()
    mn_l = sx.shift(1).rolling(k).min().to_numpy(); mn_r = sx.shift(-k).rolling(k).min().to_numpy()
    return (x > mx_l) & (x > mx_r) & ~np.isnan(x), (x < mn_l) & (x < mn_r) & ~np.isnan(x)

def _pivots_px(I, k):
    """C08 price pivots on WICKS: strict pivot highs from High, strict pivot lows from Low."""
    ph, _ = _pivots(I['h'], k); _, pl = _pivots(I['l'], k); return ph, pl

def hist(hv, X, I, N, v):
    X = np.asarray(X, float); T = len(X); Xw = W(X, N); vX = ok(Xw); u = unit_of(I, v, X, N); vu = np.isfinite(u)
    one = np.ones(T, bool); k = max(1, int(N//P['hist_kdiv'])); t3 = max(1, int(N//P['hist_thirds']))
    with np.errstate(all='ignore'):
        if hv == 'divergence_sync':
            C = I['c'].astype(float); hi, lo = _pivots_px(I, k); hx, lx = _pivots(X, k)   # C08: strict wick pivots
            idx = np.arange(T); res = {}
            for nm, pm, sgn in (('bull', lo, 1), ('bear', hi, -1)):
                pi = np.where(pm, idx, -1); last = np.maximum.accumulate(pi)       # last pivot <= j
                p1 = np.where(idx - k >= 0, last[np.maximum(idx - k, 0)], -1)         # confirmed by t
                p2 = np.where(p1 > 0, last[np.maximum(p1 - 1, 0)], -1)
                inw = (p2 >= idx - N + 1) & (p1 > p2) & (p2 >= 0)
                a1, a2 = np.where(p1 >= 0, p1, 0), np.where(p2 >= 0, p2, 0)
                aC, aX = a1, a2   # pivot pair compared (default: newest vs previous, K=2)
                if int(P['div_K']) >= 3:   # C11: use the 1st and 3rd pivots (2nd must exist in-window)
                    p3 = np.where(p2 > 0, last[np.maximum(p2 - 1, 0)], -1)
                    inw = inw & (p3 >= idx - N + 1)
                    aX = np.where(p3 >= 0, p3, 0)   # 3rd pivot replaces 2nd as the far anchor
                if sgn == 1: sgn_b, sgn_x = C[a1] < C[aX], X[a1] - X[aX]
                else: sgn_b, sgn_x = C[a1] > C[aX], X[aX] - X[a1]
                res[nm] = inw & sgn_b & (sgn_x >= P['div_unit']*u)
            return code(hv, [('bull_div', res['bull']), ('bear_div', res['bear']), ('none', one)], vX & vu & ok(W(C, N)))
        if hv == 'order_of_events':
            imx = np.nanargmax(np.nan_to_num(Xw, nan=-np.inf), 1); imn = np.nanargmin(np.nan_to_num(Xw, nan=np.inf), 1)
            big = (np.nanmax(Xw, 1) - np.nanmin(Xw, 1)) >= P['ooe_unit']*u
            return code(hv, [('high_first', big & (imx < imn)), ('low_first', big & (imn < imx)), ('none', one)], vX & vu)
        if hv == 'speed':
            net = Xw[:, -1] - Xw[:, 0]; a = np.abs(Xw[:, t3-1] - Xw[:, 0]); b = np.abs(Xw[:, -1] - Xw[:, N-t3])
            r = np.where(a > 0, b/a, np.where(b > 0, np.inf, 1.)); up = net >= P['speed_net']*u; dn = net <= -P['speed_net']*u
            f, s_ = r > P['speed_fast'], r < P['speed_slow']; m = ~f & ~s_
            return code(hv, [('up_speeding', up & f), ('up_slowing', up & s_), ('up_steady', up & m), ('down_speeding', dn & f),
                             ('down_slowing', dn & s_), ('down_steady', dn & m), ('flat', one)], vX & vu)
        if hv == 'change_of_state':
            s = pd.Series(X).rolling(int(P['hist_250']), min_periods=int(P['hist_250']*0.8)); q1 = _sh(s.quantile(1/3).to_numpy(), N); q2 = _sh(s.quantile(2/3).to_numpy(), N)
            z = lambda x: np.where(x > q2, 2, np.where(x < q1, 0, 1)); a, b = z(Xw[:, 0]), z(Xw[:, -1])
            return code(hv, [('moved_up', b > a), ('moved_down', b < a), ('stayed_high', b == 2), ('stayed_mid', b == 1), ('stayed_low', one)],
                        vX & np.isfinite(q1) & np.isfinite(q2))
        if hv == 'time_since':
            m = pd.Series(X).rolling(int(P['hist_250']), min_periods=int(P['hist_250']*0.8)).median().to_numpy(); ab = X > m
            cu = np.r_[False, ab[1:] & ~ab[:-1]] & np.isfinite(m) & np.r_[False, np.isfinite(m[:-1])]
            cd = np.r_[False, ~ab[1:] & ab[:-1]] & np.isfinite(m) & np.r_[False, np.isfinite(m[:-1])] & ~np.isnan(X)
            idx = np.arange(T); lc = np.maximum.accumulate(np.where(cu | cd, idx, -1)); age = idx - lc
            inw = (lc >= 0) & (age < N); up = inw & cu[np.maximum(lc, 0)]; dn = inw & ~up
            th = lambda g: np.where(g < N/P['hist_thirds'], 0, np.where(g < 2*N/P['hist_thirds'], 1, 2))   # 0 = last third (recent)
            p = th(age)
            return code(hv, [('up_recent', up & (p == 0)), ('up_mid', up & (p == 1)), ('up_old', up & (p == 2)), ('down_recent', dn & (p == 0)),
                             ('down_mid', dn & (p == 1)), ('down_old', dn & (p == 2)), ('none', one)], vX & np.isfinite(m))
        if hv == 'route':
            a, b = Xw[:, 0], Xw[:, -1]; c = P['route_flat']*u; e = int(round(N*(1 - P['route_mid']/100)/2))
            inner = Xw[:, e:N-e] if N - 2*e > 0 else Xw
            imx = e + np.nanargmax(np.nan_to_num(inner, nan=-np.inf), 1); imn = e + np.nanargmin(np.nan_to_num(inner, nan=np.inf), 1)
            mx = np.nanmax(Xw, 1); mn = np.nanmin(Xw, 1)
            ud = (Xw[np.arange(T), imx] >= np.maximum(a, b) + c) & (mx == Xw[np.arange(T), imx])
            du = (Xw[np.arange(T), imn] <= np.minimum(a, b) - c) & (mn == Xw[np.arange(T), imn])
            return code(hv, [('up_down', ud), ('down_up', du), ('straight_up', b - a >= c), ('straight_down', b - a <= -c), ('flat', one)], vX & vu)
        if hv == 'character_change':
            dx = np.r_[np.nan, np.diff(X)]; a = pd.Series(dx).rolling(N, min_periods=N).std().to_numpy()
            b = _sh(pd.Series(dx).rolling(int(P['hist_250']), min_periods=int(P['hist_250']*0.8)).std().to_numpy(), N); r = a/b
            return code(hv, [('wilder', r > P['char_wild']), ('calmer', r < P['char_calm']), ('same', one)], np.isfinite(r))
        if hv in ('retests', 'retest_count'):
            hx, lx = _pivots(X, k); idx = np.arange(T); tol = P['retest_tol']*u
            last = np.maximum.accumulate(np.where(hx | lx, idx, -1))
            lim = idx - t3; p = np.where(lim - k >= 0, last[np.maximum(np.minimum(lim, idx - k), 0)], -1)  # pivot before last third, confirmed
            has = (p >= idx - N + 1) & (p >= 0); pp = np.maximum(p, 0); L = X[pp]; ishi = hx[pp]
            j = np.arange(N); start = idx - N + 1; rel = (p - start)[:, None]
            after = j[None, :] > rel; near = (np.abs(Xw - L[:, None]) <= tol[:, None]) & after
            prev = np.c_[np.zeros((T, 1), bool), near[:, :-1]] | (j[None, :] == rel + 1)   # bar right after the pivot = still at level
            prev = np.c_[np.zeros((T, 1), bool), near[:, :-1]] | ((j[None, :] - 1) == rel)
            entry = near & ~prev; n = entry.sum(1)
            if hv == 'retest_count': return code(hv, [('0', has & (n == 0) | ~has), ('1', n == 1), ('2+', one)], vX & vu)
            ft = np.where(entry.any(1), np.argmax(entry, 1), N)
            aft = j[None, :] > ft[:, None]
            beyond = np.where(ishi[:, None], Xw > (L + tol)[:, None], Xw < (L - tol)[:, None]) & aft
            tch = has & (n > 0)
            return code(hv, [('held', tch & ~beyond.any(1)), ('failed', tch & beyond.any(1)), ('none', one)], vX & vu)
        if hv == 'squeeze_release':
            rr = (pd.Series(X).rolling(k).max() - pd.Series(X).rolling(k).min()).to_numpy()
            th = _sh(pd.Series(rr).rolling(int(P['hist_250']), min_periods=int(P['hist_250']*0.8)).quantile(P['squeeze_pct']/100).to_numpy(), 1); sq = rr < th
            sh_ = pd.Series(X).rolling(k).max().to_numpy(); sl = pd.Series(X).rolling(k).min().to_numpy()
            idx = np.arange(T); ls = np.maximum.accumulate(np.where(sq, idx, -1)); has = (ls >= idx - N + 1) & (ls >= 0)
            lsp = np.maximum(ls, 0); H = sh_[lsp] + P['squeeze_break']*u; Lo = sl[lsp] - P['squeeze_break']*u
            j = np.arange(N); aft = j[None, :] > (ls - (idx - N + 1))[:, None]
            upb = (Xw > H[:, None]) & aft; dnb = (Xw < Lo[:, None]) & aft
            fu = np.where(upb.any(1), np.argmax(upb, 1), N); fd = np.where(dnb.any(1), np.argmax(dnb, 1), N)
            return code(hv, [('released_up', has & (fu < N) & (fu <= fd)), ('released_down', has & (fd < N)),
                             ('still_squeezed', has & sq), ('none', one)], vX & vu & np.isfinite(th))
        if hv == 'stage':
            M = talib.SMA(X, max(int(P['stage_min']), int(N//P['stage_div']))); Mw = W(M, N); sl_l = (Mw[:, -1] - Mw[:, N-t3])/max(t3-1, 1)/u
            sl_f = (Mw[:, N-t3] - Mw[:, 0])/max(N-t3, 1)/u; g = P['stage_slope']
            return code(hv, [('advance', (X > M) & (sl_l > g)), ('decline', (X < M) & (sl_l < -g)), ('top', (np.abs(sl_l) <= g) & (sl_f > g)),
                             ('bottom', (np.abs(sl_l) <= g) & (sl_f < -g)), ('base', one)], vX & vu & ok(Mw))
        if hv == 'vs_own_past':
            mN = talib.SMA(X, N); B = W(_sh(mN, N), int(P['hist_250'])); pct = (B < mN[:, None]).sum(1)/(~np.isnan(B)).sum(1)*100
            return code(hv, [('above_usual', pct > P['vop_hi']), ('usual', pct >= P['vop_lo']), ('below_usual', one)], np.isfinite(mN) & (ok(B)))
        if hv == 'lead_lag':
            dx = np.r_[np.nan, np.diff(X)]; db = np.r_[np.nan, np.diff(I['spy'].astype(float))]; best = np.full(T, -np.inf); bl = np.zeros(T, int)
            for L in range(-k, k+1):
                y = _sh(db, -L) if L < 0 else db   # placeholder replaced below
                if L > 0: y = np.r_[db[L:], np.full(L, np.nan)]   # dBench[t+L] (inside W only: trim)
                elif L < 0: y = _sh(db, -L)
                A = W(dx, N); Bm = W(y, N)
                if L > 0: Bm[:, -L:] = np.nan; A = np.where(np.isnan(Bm), np.nan, A)
                ma = np.nanmean(A, 1, keepdims=True); mb = np.nanmean(Bm, 1, keepdims=True)
                c = np.nansum((A-ma)*(Bm-mb), 1)/np.sqrt(np.nansum((A-ma)**2, 1)*np.nansum((Bm-mb)**2, 1))
                c = np.nan_to_num(c, nan=-np.inf); bt = c > best; best[bt] = c[bt]; bl[bt] = L
            okc = best >= P['ll_corr']
            return code(hv, [('leads', okc & (bl > 0)), ('lags', okc & (bl < 0)), ('together', okc & (bl == 0)), ('none', one)], vX & ok(W(db, N)))
        if hv == 'timeframe_agreement':
            a = tstat_slope(Xw); b = tstat_slope(W(X, int(P['tfa_mult'])*N)); g = P['tfa_t']
            return code(hv, [('agree_up', (a > g) & (b > g)), ('agree_down', (a < -g) & (b < -g)), ('disagree', one)], vX & np.isfinite(b))
        if hv == 'shock_recovery':
            D = W(np.r_[np.nan, np.diff(X)], N); big = np.abs(D) > P['shock_unit']*u[:, None]; big[:, -1] = False
            ks = _last_true_idx(big); has = ks >= 0; kk = np.maximum(ks, 0); r_ = np.arange(T)
            sz = D[r_, kk]; lvl = Xw[r_, kk]; back = (lvl - Xw[:, -1])/sz   # share given back (up) / recovered (down)
            up = has & (sz > 0); dn = has & (sz < 0); lo_, hi_ = P['shock_held'], P['shock_gone']
            return code(hv, [('up_shock_held', up & (back < lo_)), ('up_shock_faded', up & (back > hi_)), ('down_shock_held', dn & (back < lo_)),
                             ('down_shock_recovered', dn & (back > hi_)), ('partial', has), ('none', one)], ok(D) & vu)
    raise KeyError(hv)
