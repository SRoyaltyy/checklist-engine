"""Draft 2.6 additions: phase list (3-ATR legs), the 19 new dial rows that have a clear rule, and the
lever-5 history questions (HISTORY_LEVER_v2.6 'keep' rows) as generic questions on each variant's main line.
All sizes are in the stock's own ATR14. Everything as of close of bar t; engine shifts by 1 bar."""
import numpy as np, talib
from facets import REG, facet, W, pick, ok, tstat_slope, pairs, own_pct
from params import P

# ---------------- phase list ----------------
LAB = ['up_run', 'down_run', 'shock_up', 'shock_down', 'base', 'retest_high', 'retest_low', 'break_up', 'break_down']
UPL = {0, 2, 5, 7}; DNL = {1, 3, 6, 8}

def _zigzag(h, l, atr):
    """online 3-ATR zigzag. returns pivots [(bar, price, kind +1 high/-1 low, confirm_bar)]"""
    T = len(h); piv = []; d = 0; ei = None; ea = np.nan
    for t in range(T):
        if np.isnan(atr[t]) or np.isnan(h[t]): continue
        if ei is None: ei, d, ea = t, 1, atr[t]; lo_i = t; continue
        if d == 1:
            if h[t] >= h[ei]: ei = t
            elif h[ei] - l[t] >= P['leg_atr']*ea: piv.append((ei, h[ei], 1, t)); d = -1; ei = t; ea = atr[t]
        else:
            if l[t] <= l[ei]: ei = t
            elif h[t] - l[ei] >= P['leg_atr']*ea: piv.append((ei, l[ei], -1, t)); d = 1; ei = t; ea = atr[t]
    return piv

def _label(s, e, h, l, c, atr, prev):
    """label a phase spanning bars s..e. prev = list of earlier phases (dicts)."""
    a = atr[s] if not np.isnan(atr[s]) else atr[e]
    hi, lo = np.nanmax(h[s:e+1]), np.nanmin(l[s:e+1]); n = e - s + 1
    size = (c[e] - c[s]) / a
    base = [p for p in prev if p['lab'] == 4]
    if base:
        b = base[-1]
        if c[e] > b['hi'] + a and size > 0: return 7, hi, lo, size
        if c[e] < b['lo'] - a and size < 0: return 8, hi, lo, size
    if n >= 10 and (hi - lo) <= P['leg_atr']*a: return 4, hi, lo, size
    up = size > 0
    for p in prev[::-1][:6]:
        if up and abs(hi - p['hi']) <= .5*a: return 5, hi, lo, size
        if (not up) and abs(lo - p['lo']) <= .5*a: return 6, hi, lo, size
    if abs(size) >= P['leg_atr'] and n <= 3: return (2 if up else 3), hi, lo, size
    return (0 if up else 1), hi, lo, size

def phases_asof(I):
    """for every bar t, list of phases using bars <= t (confirmed legs + in-progress stretch). cached."""
    key = ('_ph', P['leg_atr'])
    if key in I: return I[key]
    h, l, c, v, atr = I['h'], I['l'], I['c'], I['v'], I['atr']; T = len(c)
    piv = _zigzag(h, l, atr); out = [None]*T; done = []; k = 0
    for t in range(T):
        while k < len(piv) and piv[k][3] <= t:
            s = done[-1]['e'] if done else (piv[0][0] if k == 0 else piv[k-1][0])
            if k == 0: s = int(np.argmax(~np.isnan(atr)))
            e = piv[k][0]
            if e > s:
                lab, hi, lo, sz = _label(s, e, h, l, c, atr, done)
                done.append(dict(s=s, e=e, lab=lab, hi=hi, lo=lo, size=sz, vol=np.nanmean(v[s:e+1])))
            k += 1
        if not done and k == 0: continue
        s = done[-1]['e'] if done else 0
        cur = []
        if t > s:
            lab, hi, lo, sz = _label(s, t, h, l, c, atr, done)
            cur = [dict(s=s, e=t, lab=lab, hi=hi, lo=lo, size=sz, vol=np.nanmean(v[s:t+1]))]
        out[t] = done[-8:] + cur
    I[key] = out; return out

def _inwin(P, t, N): return [p for p in P if p['e'] > t - N] if P else []

PL = '3ATR_legs'
@facet(PL, 'phase_count', ['1', '2-3', '4-6', '7+'])
def ph_n(I, N):
    P = phases_asof(I); out = np.full(len(P), -1, np.int8)
    for t, ps in enumerate(P):
        if ps: n = len(_inwin(ps, t, N)); out[t] = 0 if n <= 1 else 1 if n <= 3 else 2 if n <= 6 else 3
    return out
@facet(PL, 'last_phase', LAB, lbs=(1,))
def ph_last(I, N):
    P = phases_asof(I); return np.array([ps[-1]['lab'] if ps else -1 for ps in P], np.int8)
@facet(PL, 'phase_seq3', [f"{a}>{b}>{c}" for a in LAB for b in LAB for c in LAB], lbs=(1,))
def ph_seq(I, N):
    P = phases_asof(I); out = np.full(len(P), -1, np.int16)
    for t, ps in enumerate(P):
        if ps and len(ps) >= 3: a, b, c = (p['lab'] for p in ps[-3:]); out[t] = a*81 + b*9 + c
    return out
def _dirk(lab): return 0 if lab in UPL else 1 if lab in DNL else 2
def _ratio_facet(name, key, cuts):
    @facet(PL, name, [f"{d}x{b}" for d in ['up', 'down', 'flat'] for b in cuts[2]], lbs=(1,))
    def f(I, N):
        P = phases_asof(I); out = np.full(len(P), -1, np.int8)
        for t, ps in enumerate(P):
            if not ps or len(ps) < 2: continue
            a, b = key(ps[-1]), key(ps[-2])
            if not (np.isfinite(a) and np.isfinite(b)) or b == 0: continue
            r = a/b; k = 0 if r < cuts[0] else 2 if r > cuts[1] else 1
            out[t] = _dirk(ps[-1]['lab'])*3 + k
        return out
_ratio_facet('len_vs_prev', lambda p: p['e'] - p['s'] + 1, (.5, 2, ['<0.5', '0.5-2', '>2']))
_ratio_facet('size_vs_prev', lambda p: abs(p['size']), (.5, 2, ['<0.5', '0.5-2', '>2']))
_ratio_facet('vol_vs_prev', lambda p: p['vol'], (.7, 1.3, ['<0.7', '0.7-1.3', '>1.3']))
_ratio_facet('speed_vs_prev', lambda p: abs(p['size'])/(p['e'] - p['s'] + 1), (.7, 1.3, ['slower', 'similar', 'faster']))

# ---------------- new 2.6 dial rows ----------------
def _legpair(I, t):
    """last confirmed leg and the in-progress stretch after it (from phase list)"""
    ps = phases_asof(I)[t]
    if not ps or len(ps) < 2: return None
    return ps[-2], ps[-1]
@facet('base_and_run', 'pause_vs_run', [f"{a}x{b}" for a in ['after_up', 'after_down'] for b in ['short<0.33', 'mid', 'long>1']], lbs=(1,))
def bar_pvr(I, N):
    T = len(I['c']); out = np.full(T, -1, np.int8); a = I['atr']
    for t in range(T):
        lp = _legpair(I, t)
        if not lp: continue
        leg, cur = lp; h = I['h'][cur['s']:t+1]; l = I['l'][cur['s']:t+1]
        if np.nanmax(h) - np.nanmin(l) > P['leg_atr']*a[t] or leg['lab'] == 4: continue
        r = (t - cur['s'] + 1)/(leg['e'] - leg['s'] + 1)
        out[t] = (0 if leg['size'] > 0 else 3) + (0 if r < .33 else 2 if r > 1 else 1)
    return out
@facet('base_and_run', 'shelf_depth', [f"{a}x{b}" for a in ['after_up', 'after_down'] for b in ['shallow<0.25', 'mid', 'deep>0.5']], lbs=(1,))
def bar_sd(I, N):
    T = len(I['c']); out = np.full(T, -1, np.int8); a = I['atr']
    for t in range(T):
        lp = _legpair(I, t)
        if not lp: continue
        leg, cur = lp; hh = np.nanmax(I['h'][cur['s']:t+1]) - np.nanmin(I['l'][cur['s']:t+1])
        if hh > P['leg_atr']*a[t] or leg['lab'] == 4 or leg['size'] == 0: continue
        r = (hh/a[t])/abs(leg['size'])
        out[t] = (0 if leg['size'] > 0 else 3) + (0 if r < .25 else 2 if r > .5 else 1)
    return out
@facet('volume', 'ledge_fade', [f"{a}x{b}" for a in ['after_up', 'after_down'] for b in ['fading<0.7', 'steady', 'rising>1.3']], lbs=(1,))
def rv_lf(I, N):
    T = len(I['c']); out = np.full(T, -1, np.int8); a = I['atr']
    for t in range(T):
        lp = _legpair(I, t)
        if not lp: continue
        leg, cur = lp; n = t - cur['s'] + 1
        if n < 5 or np.nanmax(I['h'][cur['s']:t+1]) - np.nanmin(I['l'][cur['s']:t+1]) > P['leg_atr']*a[t] or leg['vol'] <= 0: continue
        r = np.nanmean(I['v'][cur['s']:t+1])/leg['vol']
        out[t] = (0 if leg['size'] > 0 else 3) + (0 if r < .7 else 2 if r > 1.3 else 1)
    return out
REG[-1] = ('RVOL20',) + REG[-1][1:]
@facet('new_highs_lows', 'giveback_speed', [f"{a}x{b}" for a in ['fast<0.5', 'similar', 'slow>2'] for b in ['bull', 'bear']], lbs=(1,))
def nh_gs(I, N):
    T = len(I['c']); out = np.full(T, -1, np.int8); c = I['c']
    for t in range(T):
        lp = _legpair(I, t)
        if not lp: continue
        leg, cur = lp; mid = (c[leg['s']] + c[leg['e']])/2; seg = c[cur['s']:t+1]
        hit = np.where(seg <= mid)[0] if leg['size'] > 0 else np.where(seg >= mid)[0]
        if not len(hit): continue
        r = (hit[0] + 1)/(leg['e'] - leg['s'] + 1); k = 0 if r < .5 else 2 if r > 2 else 1
        out[t] = k*2 + (1 if leg['size'] > 0 else 0)
    return out
@facet('RVOL20', 'absorption_day', [f"{a}x{b}" for a in ['after_decline', 'after_rise'] for b in ['age<=5', '6-20', '>20']] + ['none'])
def rv_abs(I, N):
    c, pc, a, rv = I['c'], I['pc'], I['atr'], I['rvol']
    with np.errstate(all='ignore'): day = (rv > 3) & (np.abs(c - pc) < .5*a)
    prior = c / np.r_[np.full(10, np.nan), c[:-10]] - 1
    D, P = W(day.astype(float), N), W(prior, N); T = len(c); out = np.full(T, -1, np.int8)
    for t in np.where(ok(D))[0]:
        i = np.where(D[t] == 1)[0]
        if not len(i): out[t] = 6; continue
        j = i[-1]; age = N - 1 - j; ag = 0 if age <= 5 else 1 if age <= 20 else 2
        out[t] = (0 if P[t, j] < 0 else 3) + ag
    return out
@facet('RVOL20', 'maxvol_wick', ['bull_wick>1ATR', 'bear_wick>1ATR', 'small'])
def rv_mw(I, N):
    V = W(I['v'], N); T = len(V); out = np.full(T, -1, np.int8); o, h, l, c, a = I['o'], I['h'], I['l'], I['c'], I['atr']
    for t in np.where(ok(V) & ~np.isnan(a))[0]:
        j = t - N + 1 + int(np.argmax(V[t])); lw = (min(o[j], c[j]) - l[j])/a[t]; uw = (h[j] - max(o[j], c[j]))/a[t]
        out[t] = 0 if lw > 1 and lw >= uw else 1 if uw > 1 else 2
    return out
@facet('RVOL20', 'pullback_vs_run_volume', [f"{a}x{b}" for a in ['bull', 'bear'] for b in ['lighter<0.7', 'similar', 'heavier>1.3']], lbs=(20, 60))
def rv_pr(I, N):
    C, V = W(I['c'], N), W(I['v'], N); T = len(C); out = np.full(T, -1, np.int8)
    for t in np.where(ok(C, V))[0]:
        i = int(np.argmax(C[t])); j = int(np.argmin(C[t]))
        if i > j and i < N - 2: a, b, s = V[t, j:i+1].mean(), V[t, i+1:].mean(), 0
        elif j > i and j < N - 2: a, b, s = V[t, i:j+1].mean(), V[t, j+1:].mean(), 3
        else: continue
        if a <= 0: continue
        r = b/a; out[t] = s + (0 if r < .7 else 2 if r > 1.3 else 1)
    return out
@facet('RSI6', 'osc_swing_speed', [f"{a}x{b}" for a in ['bull', 'bear'] for b in ['<=5', '6-15', '>15']] + ['none'], lbs=(20, 60))
def rsi_ss(I, N):
    R = W(I['rsi6'], N); T = len(R); out = np.full(T, -1, np.int8)
    for t in np.where(ok(R))[0]:
        r = R[t]; best = None; lo = np.where(r <= 20)[0]; hi = np.where(r >= 80)[0]
        for e in range(N-1, -1, -1):
            if r[e] >= 80 and len(lo[lo < e]): best = (0, e - lo[lo < e][-1]); break
            if r[e] <= 20 and len(hi[hi < e]): best = (1, e - hi[hi < e][-1]); break
        if best is None: out[t] = 6; continue
        d, n = best; out[t] = d*3 + (0 if n <= 5 else 1 if n <= 15 else 2)
    return out
@facet('MA_group(10/20/50/200)', 'ma30_side_streak', [f"{a}x{b}x{c}" for a in ['above', 'below'] for b in ['<10', '10-30', '>30'] for c in ['record', 'not']], lbs=(1,))
def ma30(I, N):
    c, m = I['c'], I['sma30']; T = len(c); out = np.full(T, -1, np.int8); side = np.where(np.isnan(m), 0, np.sign(c - m))
    run = np.zeros(T, int)
    for t in range(T): run[t] = 0 if side[t] == 0 else (run[t-1] + 1 if t and side[t-1] == side[t] else 1)
    for t in range(T):
        if side[t] == 0 or t < 500: continue
        rec = run[t] >= run[t-500:t][side[t-500:t] == side[t]].max(initial=0)
        out[t] = (0 if side[t] > 0 else 6) + (0 if run[t] < 10 else 1 if run[t] <= 30 else 2)*2 + (0 if rec else 1)
    return out
@facet('new_highs_lows', 'low_spacing', [f"{a}x{b}" for a in ['lows', 'highs'] for b in ['regular', 'uneven', '<3 pivots']], lbs=(20, 60))
def nh_ls(I, N):
    L, H = W(I['l'], N), W(I['h'], N); T = len(L); out = np.full(T, -1, np.int8)
    for t in np.where(ok(L, H))[0]:
        up = L[t, -1] > L[t, 0]; x = L[t] if up else -H[t]
        pv = [i for i in range(2, N-2) if x[i] < x[i-1] and x[i] < x[i-2] and x[i] < x[i+1] and x[i] < x[i+2]]
        base = 0 if up else 3
        if len(pv) < 3: out[t] = base + 2; continue
        g = np.diff(pv); cv = g.std()/g.mean(); out[t] = base + (0 if cv < .25 else 1)
    return out
@facet('Donchian20', 'fail_shape', [f"{a}x{b}" for a in ['bull', 'bear'] for b in ['same_day', 'multi_day']] + ['none'], lbs=(20, 60))
def dc_fs(I, N):
    h, l, c = I['h'], I['l'], I['c']; uh = np.r_[np.nan, talib.MAX(h, 20)[:-1]]; ul = np.r_[np.nan, talib.MIN(l, 20)[:-1]]
    T = len(c); out = np.full(T, -1, np.int8); ev = np.full(T, -1, np.int8)  # event at bar t: failed break resolved
    for t in range(22, T):
        if np.isnan(uh[t]): continue
        if h[t] > uh[t] and c[t] <= uh[t]: ev[t] = 2  # bear same day
        elif c[t] <= uh[t] and c[t-1] > uh[t-1] and c[t-2] > uh[t-2]: ev[t] = 3
        elif l[t] < ul[t] and c[t] >= ul[t]: ev[t] = 0
        elif c[t] >= ul[t] and c[t-1] < ul[t-1] and c[t-2] < ul[t-2]: ev[t] = 1
    E = W(ev.astype(float), N)
    for t in np.where(ok(E))[0]:
        i = np.where(E[t] >= 0)[0]; out[t] = int(E[t, i[-1]]) if len(i) else 4
    return out
# fail_fail_break (prior_pivots) needs the pivot-level engine -> deferred (see README)

# ---------------- lever 5: history questions on each variant's main line ----------------
def main_line(I, v):
    a = I['atr']
    M = {'RSI6': 'rsi6', 'RSI12': 'rsi12', 'RSI24': 'rsi24', 'RSI14': 'rsi14', 'Stoch14_3': 'stoch', 'WilliamsR14': 'willr',
         'MFI14': 'mfi', 'ROC20': 'roc20', 'OBV': 'obv_p', 'AD_line': 'ad_p', 'ADX14': 'adx', 'RVOL20': 'rvol'}
    with np.errstate(all='ignore'):
        if v in M: return I[M[v]]
        if v == 'MACD12_26_9': return I['macd']/a
        if v in ('SMA20', 'SMA50', 'SMA200', 'EMA21'): return (I['c'] - I[v.lower()])/a
        if v == 'MA_group(10/20/50/200)': return (np.fmax.reduce([I[f'sma{n}'] for n in (5, 10, 20, 30)]) - np.fmin.reduce([I[f'sma{n}'] for n in (5, 10, 20, 30)]))/a
        if v in ('OHLC', 'daily_returns'): return I['ret']/(a/I['c'])
        if v == 'dollar_volume': return np.log(I['dv'])
        if v == 'up_down_volume': return talib.SUM(np.sign(I['ret'])*I['v'], 20)/talib.SUM(I['v'], 20)
        if v == 'ATR14': return a/I['c']
        if v == 'Bollinger20_2': return (I['c'] - I['bbl'])/(I['bbu'] - I['bbl'])
        if v == 'squeeze(BB_in_Keltner)': return (I['bbu'] - I['bbl'])/(I['kcu'] - I['kcl'])
        if v == 'Donchian20':
            hh, ll = talib.MAX(I['h'], 20), talib.MIN(I['l'], 20); return (I['c'] - ll)/(hh - ll)
        if v == 'Ichimoku': return (I['c'] - np.fmax(I['spa'], I['spb']))/a
        if v in ('52w_range', 'big_picture'):
            hh, ll = talib.MAX(I['h'], 252), talib.MIN(I['l'], 252); return (I['c'] - ll)/(hh - ll)
        if v in ('new_highs_lows', 'HiLo_window'): return (talib.MAX(I['h'], 60) - I['c'])/a
        if v == 'drawdown': return (talib.MAX(I['h'], 120) - I['c'])/a
        if v == '3ATR_legs':
            P = phases_asof(I); st = np.array([ps[-1]['s'] if ps else -1 for ps in P])
            return np.where(st >= 0, (I['c'] - I['c'][np.maximum(st, 0)])/a, np.nan)
        if v == 'round_numbers(merged price level)':
            c = I['craw']; step = np.where(c < 10, 1, np.where(c < 100, 5, np.where(c < 1000, 50, 500)))
            return (c - np.round(c/step)*step)/(a*I['f'])
        if v == 'reg_sho': return I['regsho']
        if v == 'vs_SPY' and 'spy' in I: return np.log(I['c']/I['spy'])
        if v == 'SPY_VIX' and 'vix' in I: return I['vix']
        if v == 'float_turnover' and 'shares' in I: return I['vraw']/I['shares']
    return None

HL = ['divergence_sync', 'order_of_events', 'speed', 'change_of_state', 'time_since', 'route', 'character_change', 'retests',
      'retest_count', 'squeeze_release', 'stage', 'vs_own_past', 'lead_lag', 'timeframe_agreement', 'shock_recovery']
# v2.7.1 calls (Manager, 23 Oct 14:24 HKT): New Bot wording. Overridden by the committed answer file when present (load_answer_file).
HLAB = {'divergence_sync': ['bull_divergence', 'bear_divergence', 'none'], 'order_of_events': ['high_first', 'low_first', 'none'],
        'speed': ['speeding_up', 'slowing_down', 'steady'], 'change_of_state': pairs(['high', 'mid', 'low']),
        'time_since': ['recent', 'mid', 'old', 'none'], 'route': ['up_down', 'down_up', 'straight_up', 'straight_down', 'flat'],
        'character_change': ['changed_up', 'changed_down', 'same'], 'retests': ['held', 'failed', 'none'], 'retest_count': ['0', '1', '2+'],
        'squeeze_release': ['released_up', 'released_down', 'still_squeezed', 'none'], 'stage': ['advance', 'top', 'decline', 'base'],
        'vs_own_past': ['above_usual', 'below_usual', 'usual'], 'lead_lag': ['leads', 'lags', 'together'],
        'timeframe_agreement': ['agree_up', 'agree_down', 'disagree'],
        'shock_recovery': ['up_shock_held', 'up_shock_faded', 'down_shock_held', 'down_shock_recovered', 'partial', 'none']}
# engine's old words -> v2.7.1 words (same code order); used to cross-check the answer file's mapping column
OLD2NEW = {'speeding': 'speeding_up', 'slowing': 'slowing_down', '<5': 'recent', '5-20': 'mid', '>20': 'old', 'wilder': 'changed_up',
           'calmer': 'changed_down', 'rising': 'advance', 'topping': 'top', 'falling': 'decline', 'bottoming': 'base', 'high': 'above_usual',
           'low': 'below_usual', 'normal': 'usual', 'stock_led': 'leads', 'spy_led': 'lags', 'bull': 'bull_divergence', 'bear': 'bear_divergence'}

def load_answer_file(path):
    """Committed v2.7.1 answer file is final: replace HLAB order-preserving where the label SET matches the code's meaning; else stop."""
    import pandas as pd, re, os
    if not path or not os.path.exists(path): return False
    A = pd.read_csv(path); hv_col = next(c for c in A.columns if c.lower() in ('history_value', 'question', 'l4_analysis', 'name'))
    ans_col = next(c for c in A.columns if 'answer' in c.lower() and 'map' not in c.lower())
    bad = []
    for r in A.itertuples():
        hv = getattr(r, hv_col); labs = [x.strip() for x in re.sub(r'^proposed:\s*|[{}]', '', str(getattr(r, ans_col))).replace('|', ',').split(',') if x.strip()]
        if hv not in HLAB: bad.append(f"{hv}: not in engine"); continue
        if hv == 'change_of_state': continue
        if set(labs) != set(HLAB[hv]): bad.append(f"{hv}: file {labs} vs engine {HLAB[hv]}")
    if bad: raise SystemExit('ANSWER FILE MISMATCH (fix engine before running):\n' + '\n'.join(bad))
    return True

def _route5(X, cut):
    a = X[:, 0]; b = X[:, -1]; hi = np.nanmax(X, 1); lo = np.nanmin(X, 1); net = b - a
    up_ex = hi - np.maximum(a, b) >= cut; dn_ex = np.minimum(a, b) - lo >= cut
    o = np.where(net >= cut, np.where(a - lo >= cut, 1, 2), np.where(net <= -cut, np.where(hi - a >= cut, 0, 3),
                 np.where(up_ex, 0, np.where(dn_ex, 1, 4))))
    return o.astype(np.int8)

def hist_answer(hv, s, I, N, unit=None):
    """generic history question on line s (as of close t, window N bars). unit = the line's own '1 ATR' (route flat cutoff)."""
    X = W(s, N); v = ok(X); T = len(X); one = np.ones(T, bool); h = N//2
    with np.errstate(all='ignore'):
        sd = W(s, 250).std(1) if T else None; sd = np.where(sd > 0, sd, np.nan)
        if hv == 'divergence_sync':
            C = W(I['c'], N); dp = C[:, -1] - C[:, 0]; ds = X[:, -1] - X[:, 0]
            return pick([(dp < 0) & (ds > .5*sd), (dp > 0) & (ds < -.5*sd), one], v & ok(C) & np.isfinite(sd))
        if hv == 'order_of_events':
            imx = np.argmax(np.nan_to_num(X, nan=-np.inf), 1); imn = np.argmin(np.nan_to_num(X, nan=np.inf), 1)
            flat = (np.nanmax(X, 1) - np.nanmin(X, 1)) < .5*sd
            return pick([~flat & (imx < imn), ~flat & (imn < imx), one], v & np.isfinite(sd))
        if hv == 'speed':
            a = np.abs(X[:, h] - X[:, 0]); b = np.abs(X[:, -1] - X[:, h]); return pick([b > 1.5*a, b < a/1.5, one], v)
        if hv == 'route':
            u = unit if unit is not None else pd_mean_abs_diff(s)
            o = _route5(X, u); o[~(v & np.isfinite(u))] = -1; return o
        if hv in ('change_of_state', 'vs_own_past', 'stage', 'time_since'):
            p = own_pct(s)
            z = lambda q: np.where(q > 67, 0, np.where(q < 33, 2, 1))
            P = W(p, N); vp = ok(P)
            if hv == 'change_of_state': o = (z(P[:, 0])*3 + z(P[:, -1])).astype(np.int8); o[~vp] = -1; return o
            if hv == 'vs_own_past': return pick([p > 80, p < 20, one], ~np.isnan(p))
            if hv == 'time_since':
                o = np.full(T, -1, np.int8)
                for t in np.where(vp)[0]:
                    i = np.where((P[t] > 90) | (P[t] < 10))[0]
                    o[t] = 3 if not len(i) else (lambda a: 0 if a < 5 else 1 if a <= 20 else 2)(N - 1 - i[-1])
                return o
            ts = tstat_slope(X); hi = p > 67; lo = p < 33
            return pick([(ts > 2), hi & (ts <= 2), ts < -2, one], v & ~np.isnan(p))
        if hv == 'character_change':
            d = np.diff(X, axis=1); a = d[:, :h].std(1); b = d[:, h:].std(1); return pick([b > 1.5*a, b < a/1.5, one], v)
        if hv in ('retests', 'retest_count'):
            # old high = max of first half; retest = separate visit within tol of it in the second half; failed = broke above it
            L = np.nanmax(X[:, :h], 1, keepdims=True); tol = .25*np.nanstd(X, 1, keepdims=True); S2 = X[:, h:]
            near = np.abs(S2 - L) <= tol; n = (near[:, 1:] & ~near[:, :-1]).sum(1) + near[:, 0]
            broke = (S2 > L + tol).any(1)
            if hv == 'retest_count': return pick([n == 0, n == 1, one], v)
            return pick([(n > 0) & ~broke, (n > 0) & broke, one], v)
        if hv == 'squeeze_release':
            r = W(np.abs(np.r_[np.nan, np.diff(s)]), N); a = np.nanmean(r[:, :h], 1); b = np.nanmean(r[:, h:], 1)
            mv = X[:, -1] - X[:, h]
            return pick([(b > 1.5*a) & (mv > 0), (b > 1.5*a) & (mv <= 0), b < a/1.5, one], ok(r) & v)
        if hv == 'lead_lag':
            if 'spy' not in I: return np.full(T, -1, np.int8)
            S = W(I['spy'], N); i = np.argmin(np.nan_to_num(X, nan=np.inf), 1); j = np.argmin(np.nan_to_num(S, nan=np.inf), 1)
            return pick([i < j - 1, j < i - 1, one], v & ok(S))
        if hv == 'timeframe_agreement':
            a = s - np.r_[np.full(10, np.nan), s[:-10]]; b = s - np.r_[np.full(60, np.nan), s[:-60]]
            return pick([(a > 0) & (b > 0), (a < 0) & (b < 0), one], ~np.isnan(a) & ~np.isnan(b))
        if hv == 'shock_recovery':
            # given back fraction g of the shock: <1/3 held, 1/3-2/3 partial, >2/3 faded (up) / recovered (down)
            d = W(np.r_[np.nan, np.diff(s)], N); o = np.full(T, -1, np.int8)
            for t in np.where(ok(d) & np.isfinite(sd))[0]:
                k = int(np.argmax(np.abs(d[t])))
                if abs(d[t, k]) < 3*np.nanstd(d[t]) or k == N - 1: o[t] = 5; continue
                g = (X[t, k] - X[t, -1]) / d[t, k]
                if 1/3 <= g <= 2/3: o[t] = 4
                elif d[t, k] > 0: o[t] = 0 if g < 1/3 else 1
                else: o[t] = 2 if g < 1/3 else 3
            return o
    return np.full(T, -1, np.int8)

def pd_mean_abs_diff(s, n=14):
    import pandas as pd
    return pd.Series(np.abs(np.r_[np.nan, np.diff(s)])).rolling(n).mean().to_numpy()

HIST = []   # (lever1_type, variant, history_value, labels, lookbacks)
def load_history(path):
    import pandas as pd
    h = pd.read_csv(path); h = h[h.status == 'keep']
    for r in h.itertuples():
        HIST.append((r.lever1_type, r.variant, r.history_value, HLAB[r.history_value], (10, 20, 60)))
        if r.history_value == 'retests': HIST.append((r.lever1_type, r.variant, 'retest_count', HLAB['retest_count'], (10, 20, 60)))
    return h
