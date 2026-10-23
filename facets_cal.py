"""calendar_context rows. Uses bar dates (I['dates'], datetime64[D]) and the exchange session list I['sessions']
(the holiday schedule is published in advance, so knowing tomorrow is a holiday is not a leak)."""
import numpy as np, pandas as pd
from facets import facet, W, pick, ok
CV = 'calendar_context'
def _d(I): return pd.DatetimeIndex(I['dates'])
@facet(CV, 'month_turn', ['yes', 'no'])
def c_mt(I, N):
    m = _d(I).month.values.astype(float); M = W(m, N); return pick([M[:, 0] != M[:, -1], np.ones(len(M), bool)], ok(M))
def _opex(d):  # 3rd Friday of month
    f = d.to_period('M').to_timestamp(); third = f + pd.to_timedelta((4 - f.weekday) % 7 + 14, 'D')
    prev = (f - pd.offsets.MonthBegin(1)); tp = prev + pd.to_timedelta((4 - prev.weekday) % 7 + 14, 'D')
    return np.where(d >= third, third, tp)
@facet(CV, 'opex', ['0-5', '6-10', '>10'], lbs=(1,))
def c_ox(I, N):
    d = _d(I); s = pd.DatetimeIndex(I['sessions']); last = pd.DatetimeIndex(_opex(d))
    n = np.searchsorted(s.values, d.values) - np.searchsorted(s.values, last.values)
    return pick([n <= 5, n <= 10, np.ones(len(d), bool)], np.ones(len(d), bool))
@facet(CV, 'pre_holiday', ['yes', 'no'])
def c_ph(I, N):
    d = _d(I); s = pd.DatetimeIndex(I['sessions']).values; i = np.searchsorted(s, d.values)
    nxt = s[np.minimum(i + 1, len(s) - 1)]; bd = np.busday_count(d.values.astype('datetime64[D]'), nxt.astype('datetime64[D]'))
    X = W((bd > 1).astype(float), N); return pick([X.max(1) == 1, np.ones(len(X), bool)], ok(X))
@facet(CV, 'weekday_drift', ['mon', 'fri', 'even'])
def c_wd(I, N):
    wd = _d(I).weekday.values; up = (I['ret'] > 0).astype(float); up[np.isnan(I['ret'])] = np.nan
    U, D = W(up, N), W(wd.astype(float), N)
    with np.errstate(all='ignore'):
        m = np.nanmean(np.where(D == 0, U, np.nan), 1); f = np.nanmean(np.where(D == 4, U, np.nan), 1)
    return pick([m - f > .25, f - m > .25, np.ones(len(U), bool)], ok(U) & np.isfinite(m) & np.isfinite(f))
@facet(CV, 'quarter_pos', ['early', 'mid', 'late'], lbs=(1,))
def c_qp(I, N):
    m = (_d(I).month.values - 1) % 3; return pick([m == 0, m == 1, np.ones(len(m), bool)], np.ones(len(m), bool))
@facet(CV, 'seasonal_vs_own', ['above', 'below', 'none'])
def c_so(I, N):
    c = I['c']; T = len(c); r = np.r_[np.full(N, np.nan), c[N:]/c[:-N] - 1] if T > N else np.full(T, np.nan)
    out = np.full(T, -1, np.int8)
    for t in range(T):
        if np.isnan(r[t]): continue
        past = [r[t - 252*k] for k in (1, 2, 3) if t - 252*k >= 0 and not np.isnan(r[t - 252*k])]
        out[t] = 2 if len(past) < 2 else (0 if r[t] > np.mean(past) else 1)
    return out
