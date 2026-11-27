"""DIAL_TABLE v2.7 additions: OHLC|gap_given_back, HiLo_window|range_box, 3ATR_legs|pump_fade_cycles (2 columns).
All as of close of bar t (engine shifts 1 bar -> uses bars < D). Sizes in the stock's own ATR14."""
import numpy as np
from facets import REG, facet, W, pick, ok
from facets_v26 import phases_asof
from params import P

# ---- gap_given_back: latest gap in window (gap up: O > prev H; gap down: O < prev L)
GG = [f"{d}:{s}" for d in ('gap_up', 'gap_down') for s in ('given_back', 'partial', 'held')] + ['none']
@facet('OHLC', 'gap_given_back', GG, lbs=(10, 20, 60))
def gap_given_back(I, N):
    o, h, l, c = I['o'], I['h'], I['l'], I['c']; T = len(c); out = np.full(T, -1, np.int16)
    gu = np.r_[False, o[1:] > h[:-1]]; gd = np.r_[False, o[1:] < l[:-1]]; last = -1; kind = 0
    for t in range(T):
        if gu[t]: last, kind = t, 1
        elif gd[t]: last, kind = t, -1
        if t < N or np.isnan(c[t]): continue
        if last < 0 or last <= t - N: out[t] = 6; continue
        O, Cg, x = o[last], c[last], c[t]
        if kind == 1: s = 0 if x <= O else (2 if x > max(O, Cg) else 1); out[t] = s
        else: s = 0 if x >= O else (2 if x < min(O, Cg) else 1); out[t] = 3 + s
    return out

# ---- range_box
RB = [f"{side}:{hgt}:{cr}" for side in ('upper_half', 'lower_half') for hgt in ('<5', '5-10', '>10ATR')
      for cr in ('0-1', '2-3', '4+')] + ['none']
def _strict_piv(h, l, k=2):
    T = len(h); ph = np.zeros(T, bool); pl = np.zeros(T, bool)
    for j in range(1, k+1):
        pass
    hh = np.pad(h, k, constant_values=np.nan); ll = np.pad(l, k, constant_values=np.nan)
    ph[:] = True; pl[:] = True
    for j in range(1, k+1):
        ph &= (h > hh[k-j:k-j+T]) & (h > hh[k+j:k+j+T]); pl &= (l < ll[k-j:k-j+T]) & (l < ll[k+j:k+j+T])
    return ph, pl   # pivot at i is known only at bar i+k
@facet('HiLo_window', 'range_box', RB, lbs=(10, 20, 60))
def range_box(I, N, k=2):
    h, l, c, atr = I['h'], I['l'], I['c'], I['atr']; T = len(c); out = np.full(T, -1, np.int16)
    ph, pl = _strict_piv(h, l, k)
    for t in range(N, T):
        if np.isnan(atr[t]) or np.isnan(c[t]): continue
        lo0 = t - N + 1; seq = []                       # alternating pivots walking back, confirmed by t
        for i in range(t - k, lo0 - 1, -1):
            kd = 1 if ph[i] else (-1 if pl[i] else 0)
            if kd and (not seq or seq[-1][1] != kd): seq.append((i, kd))
            if len(seq) == 4: break
        if len(seq) < 4: out[t] = 18; continue
        s0 = seq[-1][0]; bt, bb = h[s0:t+1].max(), l[s0:t+1].min(); a = atr[t]
        s = s0
        while s - 1 >= lo0 and bb - .5*a <= c[s-1] <= bt + .5*a: s -= 1
        top, bot = h[s:t+1].max(), l[s:t+1].min()
        npiv = sum(1 for (i, _) in seq if i >= s)
        if t - s + 1 < 10 or npiv < 4: out[t] = 18; continue
        hgt = (top - bot)/a; hb = 0 if hgt < 5 else (1 if hgt <= 10 else 2)
        z = (c[s:t+1] - bot)/(top - bot + 1e-12); st = 0; n = 0
        for v in z:
            if v <= .25:
                if st == 1: n += 1
                st = -1
            elif v >= .75:
                if st == -1: n += 1
                st = 1
        cb = 0 if n <= 1 else (1 if n <= 3 else 2); side = 0 if z[-1] >= .5 else 1
        out[t] = side*9 + hb*3 + cb
    return out

# ---- pump_fade_cycles (two columns)
PF = [f"{n}:{p}" for n in ('0', '1', '2', '3+') for p in ('lower_peaks', 'higher_peaks', 'mixed', 'n/a')]
DR = [f"{n}:{p}" for n in ('0', '1', '2', '3+') for p in ('higher_troughs', 'lower_troughs', 'mixed', 'n/a')]
def _cycles(I, N, up):
    PH = phases_asof(I); c = I['c']; T = len(c); out = np.full(T, -1, np.int16)
    labs = (0, 2) if up else (1, 3)
    for t in range(N, T):
        ps = PH[t]
        if ps is None or np.isnan(c[t]): continue
        lo0 = t - N + 1; mv = [p for p in ps if p['lab'] in labs and abs(p['size']) >= P['leg_atr'] and p['s'] >= lo0 and p['e'] <= t]
        ext = []
        for j, p in enumerate(mv):
            nxt = mv[j+1]['s'] if j + 1 < len(mv) else t
            seg = c[p['e']:nxt+1]; amp = c[p['e']] - c[p['s']]
            if not len(seg): continue
            if up and seg.min() <= c[p['e']] - .5*amp: ext.append(p['hi'])
            if not up and seg.max() >= c[p['e']] - .5*amp: ext.append(p['lo'])
        n = min(len(ext), 3)
        if len(ext) < 2: q = 3
        else:
            d = np.sign(np.diff(ext)); dn, upp = (d < 0).all(), (d > 0).all()
            q = (0 if dn else 1 if upp else 2) if up else (0 if upp else 1 if dn else 2)
        out[t] = n*4 + q
    return out
@facet('3ATR_legs', 'pump_fade_cycles:pump_fade', PF, lbs=(10, 20, 60))
def pump_fade(I, N): return _cycles(I, N, True)
@facet('3ATR_legs', 'pump_fade_cycles:dump_recover', DR, lbs=(10, 20, 60))
def dump_recover(I, N): return _cycles(I, N, False)
