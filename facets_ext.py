"""Facets that need outside series aligned to the stock's bars: SPY, VIX, SEC share counts, Reg SHO list."""
import numpy as np
from facets import REG, facet, W, pick, ok, tstat_slope, pairs, own_pct, _runs

def _rs(I, N): return W(np.log(I['c']/I['spy']), N)
@facet('vs_SPY', 'rs_trend', ['out', 'under', 'flat'])
def rs_t(I, N):
    X = _rs(I, N); t = tstat_slope(X); return pick([t > 2, t < -2, np.ones(len(t), bool)], ok(X))
@facet('vs_SPY', 'rs_new_high', ['yes', 'no'])
def rs_nh(I, N):
    X = _rs(I, N); return pick([X[:, -1] >= np.nanmax(X, 1), np.ones(len(X), bool)], ok(X))
@facet('vs_SPY', 'divergence', ['bull', 'bear', 'none'])
def rs_dv(I, N):
    X = _rs(I, N); C = W(I['c'], N); pr = C[:, -1]/C[:, 0] - 1; rs = X[:, -1] - X[:, 0]
    return pick([(pr < 0) & (rs > .02), (pr > 0) & (rs < -.02), np.ones(len(X), bool)], ok(X, C))
def _beta(R, B):
    Rm, Bm = R - R.mean(1, keepdims=True), B - B.mean(1, keepdims=True)
    with np.errstate(all='ignore'): return (Rm*Bm).sum(1)/(Bm*Bm).sum(1)
@facet('vs_SPY', 'beta_shift', ['rising', 'falling', 'flat'], lbs=(20, 60))
def rs_bs(I, N):
    R, B = W(I['ret'], N), W(I['spyret'], N); h = N//2; a = _beta(R[:, :h], B[:, :h]); b = _beta(R[:, h:], B[:, h:])
    return pick([b > a + .3, b < a - .3, np.ones(len(R), bool)], ok(R, B) & np.isfinite(a) & np.isfinite(b))
@facet('vs_SPY', 'down_day_resilience', ['high', 'low', 'mid'])
def rs_dd(I, N):
    R, B = W(I['ret'], N), W(I['spyret'], N); dn = B < 0
    with np.errstate(all='ignore'): s = np.where(dn, (R > B), np.nan); s = np.nanmean(s, 1)
    return pick([s > .6, s < .4, np.ones(len(R), bool)], ok(R, B) & np.isfinite(s))
@facet('vs_SPY', 'speed', ['speeding', 'slowing', 'steady'])
def rs_sp(I, N):
    X = _rs(I, N); h = N//2; a = np.abs(X[:, h] - X[:, 0]); b = np.abs(X[:, -1] - X[:, h]); return pick([b > 1.5*a, b < a/1.5, np.ones(len(X), bool)], ok(X))
@facet('vs_SPY', 'own_vs_bench_days', [f"{a}x{b}" for a in ['down_days', 'up_days'] for b in ['mostly_own', 'mixed', 'mostly_bench']])
def rs_ob(I, N):
    R, B = W(I['ret'], N), W(I['spyret'], N)
    own = (np.abs(B) < .003) | (np.sign(B) != np.sign(R)); net_dn = R.sum(1) < 0
    side = np.where(net_dn[:, None], R < 0, R > 0)
    with np.errstate(all='ignore'): s = (own & side).sum(1)/side.sum(1)
    k = np.where(s > .6, 0, np.where(s < .3, 2, 1)); out = ((~net_dn)*3 + k).astype(np.int8); out[~(ok(R, B) & np.isfinite(s))] = -1; return out
@facet('vs_SPY', 'leg_attribution', [f"{a}x{b}" for a in ['up_leg', 'down_leg'] for b in ['mostly_bench>60%', 'mixed', 'mostly_own<30%']], lbs=(20, 60))
def rs_la(I, N):
    R, B = W(I['ret'], N), W(I['spyret'], N); be = _beta(R, B); sr = np.log1p(R).sum(1); br = np.log1p(B).sum(1)
    with np.errstate(all='ignore'): share = be*br/sr
    k = np.where(share > .6, 0, np.where(share < .3, 2, 1)); out = ((sr < 0)*3 + k).astype(np.int8); out[~(ok(R, B) & np.isfinite(share))] = -1; return out
@facet('vs_SPY', 'turn_sync', [f"{a}x{b}" for a in ['bottom', 'top'] for b in ['bench_first', 'together', 'stock_first']], lbs=(20, 60))
def rs_ts(I, N):
    C, S = W(I['c'], N), W(I['spy'], N); a = np.argmin(np.nan_to_num(C, nan=np.inf), 1); b = np.argmin(np.nan_to_num(S, nan=np.inf), 1)
    top = (np.argmax(np.nan_to_num(C), 1) > a)  # most recent turn: if the max came after the min, the recent turn is a top
    ah = np.argmax(np.nan_to_num(C), 1); bh = np.argmax(np.nan_to_num(S), 1)
    x = np.where(top, ah, a); y = np.where(top, bh, b); tol = max(1, N//10)
    k = np.where(np.abs(x - y) <= tol, 1, np.where(y < x, 0, 2)); out = (top*3 + k).astype(np.int8); out[~ok(C, S)] = -1; return out

# market condition (same answer for every stock on a day except stock_vs_regime)
@facet('SPY_VIX', 'spy_trend', ['up', 'down', 'flat'])
def m_st(I, N):
    S = W(I['spy'], N); r = S[:, -1]/S[:, 0] - 1; return pick([r > .02, r < -.02, np.ones(len(r), bool)], ok(S))
@facet('SPY_VIX', 'vix_route', pairs(['<15', '15-25', '>25']))
def m_vr(I, N):
    V = W(I['vix'], N); z = lambda x: np.where(x < 15, 0, np.where(x > 25, 2, 1)); out = (z(V[:, 0])*3 + z(V[:, -1])).astype(np.int8); out[~ok(V)] = -1; return out
@facet('SPY_VIX', 'vix_spike', ['yes', 'no'])
def m_vs(I, N):
    V = W(I['vix'], N); return pick([(V[:, 1:]/V[:, :-1] > 1.2).any(1), np.ones(len(V), bool)], ok(V))
@facet('SPY_VIX', 'breadth', ['rising', 'falling', 'flat'])
def m_br(I, N):
    X = W(I['breadth'], N); d = X[:, -1] - X[:, 0]; return pick([d > .1, d < -.1, np.ones(len(d), bool)], ok(X))
@facet('SPY_VIX', 'stock_vs_regime', ['with', 'against'])
def m_sr(I, N):
    C, S = W(I['c'], N), W(I['spy'], N); return pick([np.sign(C[:, -1] - C[:, 0]) == np.sign(S[:, -1] - S[:, 0]), np.ones(len(C), bool)], ok(C, S))
@facet('SPY_VIX', 'speed', ['speeding', 'slowing', 'steady'])
def m_sp(I, N):
    S = W(I['spy'], N); h = N//2; a = np.abs(S[:, h]/S[:, 0] - 1); b = np.abs(S[:, -1]/S[:, h] - 1); return pick([b > 1.5*a, b < a/1.5, np.ones(len(S), bool)], ok(S))

# liquidity / float (share count = SEC dei:EntityCommonStockSharesOutstanding by filing date; NOT a true float)
LF = 'float_turnover'
@facet(LF, 'turnover_trend', ['rising', 'falling', 'flat'])
def lf_tt(I, N):
    X = W(np.log(I['vraw']/I['shares'] + 1e-9), N); t = tstat_slope(X); return pick([t > 2, t < -2, np.ones(len(t), bool)], ok(X))
@facet(LF, 'float_change', ['up', 'down', 'none'])
def lf_fc(I, N):
    S = W(I['shares'], N); r = S[:, -1]/S[:, 0]; return pick([r > 1.05, r < .95, np.ones(len(r), bool)], ok(S))
@facet(LF, 'turnover_vs_past', ['high', 'normal', 'low'])
def lf_tv(I, N):
    tv = W(I['vraw']/I['shares'], N).mean(1); p = own_pct(tv); return pick([p > 80, p < 20, np.ones(len(p), bool)], ~np.isnan(p))
@facet(LF, 'spread_proxy_route', pairs(['tight', 'mid', 'wide']))
def lf_sp(I, N):
    h, l = I['h'], I['l']; ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(all='ignore'):
        beta = np.log(h/l)**2 + np.log(ph/pl)**2; gamma = np.log(np.fmax(h, ph)/np.fmin(l, pl))**2
        k = 3 - 2*np.sqrt(2); alpha = (np.sqrt(2*beta) - np.sqrt(beta))/k - np.sqrt(gamma/k)
        cs = np.clip(2*(np.exp(alpha) - 1)/(1 + np.exp(alpha)), 0, None)
    S = W(cs, N); k2 = max(2, N//4); a = np.nanmean(S[:, :k2], 1); b = np.nanmean(S[:, -k2:], 1)
    z = lambda x: np.where(x < .005, 0, np.where(x > .02, 2, 1)); out = (z(a)*3 + z(b)).astype(np.int8); out[~ok(S)] = -1; return out
@facet(LF, 'zero_volume_days', ['none', 'some', 'many'])
def lf_z(I, N):
    V = W(I['v'], N); n = (V == 0).sum(1); return pick([n == 0, n <= N/10, np.ones(len(n), bool)], ok(V))
@facet(LF, 'cumulative_turnover', ['<0.5x', '0.5-2x', '>2x'])
def lf_ct(I, N):
    x = W(I['vraw']/I['shares'], N).sum(1); return pick([x < .5, x <= 2, np.ones(len(x), bool)], np.isfinite(x))

# Reg SHO threshold list (list date < D)
RS = 'reg_sho'
@facet(RS, 'days_on_list', ['0', '1-5', '>5'], lbs=(20,))
def rs_dl(I, N):
    X = W(I['regsho'], N); T = len(X); out = np.full(T, -1, np.int8)
    for t in np.where(ok(X))[0]:
        run = 0
        for e in X[t][::-1]:
            if e: run += 1
            else: break
        out[t] = 0 if run == 0 else 1 if run <= 5 else 2
    return out
@facet(RS, 'on_off_route', pairs(['on', 'off']))
def rs_oo(I, N):
    X = W(I['regsho'], N); out = ((1 - X[:, 0])*2 + (1 - X[:, -1])); out[~ok(X)] = -1; return out.astype(np.int8)
@facet(RS, 'entered', ['yes', 'no'])
def rs_en(I, N):
    X = W(I['regsho'], N); return pick([((X[:, :-1] == 0) & (X[:, 1:] == 1)).any(1), np.ones(len(X), bool)], ok(X))
@facet(RS, 'exited', ['yes', 'no'])
def rs_ex(I, N):
    X = W(I['regsho'], N); return pick([((X[:, :-1] == 1) & (X[:, 1:] == 0)).any(1), np.ones(len(X), bool)], ok(X))
@facet(RS, 'price_while_on', ['up', 'down', 'flat', 'not_on'])
def rs_pw(I, N):
    X, R = W(I['regsho'], N), W(I['ret'], N)
    with np.errstate(all='ignore'): s = np.nansum(np.where(X == 1, R, np.nan), 1)
    on = (X == 1).any(1); return pick([on & (s > .05), on & (s < -.05), on, np.ones(len(X), bool)], ok(X, R))
@facet(RS, 'repeat', ['yes', 'no'], lbs=(60,))
def rs_rp(I, N):
    X = W(I['regsho'], N); return pick([((X[:, :-1] == 0) & (X[:, 1:] == 1)).sum(1) >= 2, np.ones(len(X), bool)], ok(X))
