"""Event-family facets (groups 034+): halts, short_interest, earnings.
All heavy as-of alignment lives in engine.make_I, which provides per-bar arrays where every value at
bar t is computed ONLY from events with event_date <= dates[t] (engine then shifts one bar, so the stored
answer for day D uses events <= D-1). Missing data -> arrays are all-NaN / zero-count -> facets return -1 (n_a).

Thresholds below are hard-coded per the locked answer buckets and documented inline; they freeze with the
groups 034+ dial tables (same style as facets_ext.py reg_sho thresholds).
form4 / analyst_actions: raw data not on any release yet -> NOT registered here (registered when the data lands;
coding them now would produce permanent-blank columns).
"""
import numpy as np
from facets import facet, W, pick, ok, pairs

HALT = 'halts'

def _wcnt(I, key, N):
    """window count of a per-bar event-count array; NaN rows when the window is incomplete."""
    X = W(I[key].astype(float), N)
    return X, ok(X)

@facet(HALT, 'halt_occurred', ['yes', 'no'])
def h_oc(I, N):
    X, v = _wcnt(I, 'halt_cnt', N)
    return pick([(X.sum(1) >= 1), np.ones(len(X), bool)], v)

@facet(HALT, 'halt_count', ['0', '1', '2+'])
def h_cn(I, N):
    X, v = _wcnt(I, 'halt_cnt', N); n = X.sum(1)
    return pick([n == 0, n == 1, np.ones(len(n), bool)], v)

_RSN = ['LUDP', 'news', 'regulatory']
@facet(HALT, 'halt_type', _RSN, lbs=(1,))
def h_ty(I, N):
    """reason code of the most recent halt within the last N bars; -1 when no halt in the window."""
    r = I['halt_rsn']; last = I['halt_last']; T = len(r)
    out = np.full(T, -1, np.int8); idx = np.arange(T)
    m = np.isfinite(last) & (last > idx - N)          # a halt exists and its bar is inside the window
    out[m] = r[m].astype(np.int8)
    return out

@facet(HALT, 'time_since', ['<5', '5-20', '>20', 'none'], lbs=(1,))
def h_ts(I, N):
    s = I['halt_since']; T = len(s)                   # sessions since last halt; NaN = never halted (as of t)
    out = np.full(T, -1, np.int8)
    m = np.isfinite(s)
    out[m] = np.where(s[m] < 5, 0, np.where(s[m] <= 20, 1, 2))
    out[~m] = 3                                        # 'none' bucket = no halt on record yet
    return out

@facet(HALT, 'direction_before', ['up', 'down'], lbs=(1,))
def h_db(I, N):
    d = I['halt_predir']; T = len(d)                  # net return over <=5 bars before the last halt
    out = np.full(T, -1, np.int8)
    m = np.isfinite(d) & (d != 0)
    out[m] = (d[m] < 0).astype(np.int8)
    return out

@facet(HALT, 'resume_reaction', ['up', 'down', 'flat'], lbs=(1,))
def h_rr(I, N):
    r = I['halt_resret']; T = len(r)                  # c[t]/close(resume session)-1 for the last RESUMED halt
    out = np.full(T, -1, np.int8)
    m = np.isfinite(r)
    out[m] = np.where(r[m] > .02, 0, np.where(r[m] < -.02, 1, 2))
    return out

SI = 'short_interest'

@facet(SI, 'level_bucket', ['>20%', '5-20%', '<5%'], lbs=(1,))
def si_lb(I, N):
    with np.errstate(all='ignore'):
        pct = I['si_qty'] / I['shares'] * 100         # last report's short qty vs shares outstanding as of t
    v = np.isfinite(pct) & (pct >= 0)
    out = np.full(len(pct), -1, np.int8)
    out[v] = np.where(pct[v] > 20, 0, np.where(pct[v] >= 5, 1, 2))
    return out

@facet(SI, 'si_trend', ['up', 'down', 'flat'], lbs=(1,))
def si_tr(I, N):
    with np.errstate(all='ignore'):
        chg = (I['si_qty'] - I['si_prev']) / I['si_prev']   # last report vs its own previous report
    v = np.isfinite(chg) & (I['si_prev'] > 0)
    out = np.full(len(chg), -1, np.int8)
    out[v] = np.where(chg[v] > .05, 0, np.where(chg[v] < -.05, 1, 2))
    return out

@facet(SI, 'si_vs_own_past', ['high', 'normal', 'low'], lbs=(1,))
def si_vp(I, N):
    p = I['si_pct26']                                  # percentile of last report's SI% within its trailing 26 reports
    out = np.full(len(p), -1, np.int8)
    v = np.isfinite(p)
    out[v] = np.where(p[v] > 80, 0, np.where(p[v] >= 20, 1, 2))
    return out

_SIVP = ['si_up_price_down(building_in_fall)', 'si_up_price_up(squeeze_fuel)', 'si_down_price_up', 'si_down_price_down', 'none']
@facet(SI, 'si_vs_price', _SIVP, lbs=(1,))
def si_pp(I, N):
    with np.errstate(all='ignore'):
        sic = (I['si_qty'] - I['si_prev']) / I['si_prev']  # SI change, last report vs prior
    pr = I['si_prchg']                                     # price change between the same two report dates
    T = len(sic); out = np.full(T, -1, np.int8)
    v = np.isfinite(sic) & np.isfinite(pr) & (I['si_prev'] > 0)
    su, sd = sic > .05, sic < -.05
    out[v & su & (pr < 0)] = 0; out[v & su & (pr >= 0)] = 1
    out[v & sd & (pr > 0)] = 2; out[v & sd & (pr <= 0)] = 3
    out[v & ~(su | sd)] = 4                                # SI roughly flat -> 'none'
    return out

@facet(SI, 'dtc_route', pairs(['<2', '2-5', '>5']), lbs=(1,))
def si_dr(I, N):
    X = W(I['si_dtc'], N); v = ok(X)
    z = lambda x: np.where(x < 2, 0, np.where(x > 5, 2, 1))
    out = (z(X[:, 0]) * 3 + z(X[:, -1])).astype(np.int8); out[~v] = -1
    return out

@facet(SI, 'report_count_rising', ['0', '1', '2+'])
def si_rc(I, N):
    X = W(I['si_rep'].astype(float), N); n = X.sum(1); v = ok(X)
    return pick([n == 0, n == 1, np.ones(len(n), bool)], v)

ER = 'earnings'

@facet(ER, 'beat_miss', ['beat', 'miss', 'inline'], lbs=(1,))
def e_bm(I, N):
    s = I['earn_surp']; T = len(s)                       # last report within N bars, else n_a
    last = I['earn_last']; idx = np.arange(T)
    v = np.isfinite(s) & np.isfinite(last) & (last > idx - N)
    out = np.full(T, -1, np.int8)
    out[v] = np.where(s[v] > 0, 0, np.where(s[v] < 0, 1, 2))
    return out

@facet(ER, 'time_since', ['<5', '5-20', '>20'], lbs=(1,))
def e_ts(I, N):
    s = I['earn_since']; T = len(s)                      # sessions since last report; NaN = no report on record
    out = np.full(T, -1, np.int8)
    m = np.isfinite(s)
    out[m] = np.where(s[m] < 5, 0, np.where(s[m] <= 20, 1, 2))
    return out

@facet(ER, 'streak', ['0', '1', '2+'], lbs=(1,))
def e_st(I, N):
    s = I['earn_streak']; out = np.full(len(s), -1, np.int8)
    v = np.isfinite(s)
    out[v] = np.where(s[v] <= 0, 0, np.where(s[v] == 1, 1, 2))
    return out

@facet(ER, 'pre_run', ['up', 'down', 'flat'], lbs=(1,))
def e_pr(I, N):
    r = I['earn_prerun']; T = len(r)                     # 20-bar move into the last report
    out = np.full(T, -1, np.int8)
    v = np.isfinite(r)
    out[v] = np.where(r[v] > .03, 0, np.where(r[v] < -.03, 1, 2))
    return out

_GAP = [f"{a}x{b}" for a in ['in_up_leg', 'in_down_leg'] for b in ['gap_up', 'gap_down']] + ['none']
@facet(ER, 'gap_reaction', _GAP, lbs=(1,))
def e_gr(I, N):
    g = I['earn_gap']; r = I['earn_prerun']; T = len(g)  # gap = first session after report vs report-day close
    out = np.full(T, -1, np.int8)
    v = np.isfinite(g) & np.isfinite(r)                  # report on record and its reaction knowable
    leg = r > 0
    out[v & leg & (g > 0)] = 0                           # in_up_leg x gap_up
    out[v & leg & (g <= 0)] = 1                          # in_up_leg x gap_down
    out[v & ~leg & (g > 0)] = 2                          # in_down_leg x gap_up
    out[v & ~leg & (g <= 0)] = 3                         # in_down_leg x gap_down
    out[np.isfinite(r) & ~np.isfinite(g)] = 4            # report on record but too recent to react -> 'none'
    return out

@facet(ER, 'drift_after', ['continued', 'faded', 'none'], lbs=(1,))
def e_da(I, N):
    p = I['earn_post5']; s = I['earn_surp']; T = len(p)  # 5-bar post-report move (known only once 5 bars passed)
    out = np.full(T, -1, np.int8)
    v = np.isfinite(p) & np.isfinite(s) & (s != 0)
    same = np.sign(p) == np.sign(s)
    out[v & same & (np.abs(p) >= .03)] = 0               # continued: drift in the surprise direction, >=3%
    out[v & ~same & (np.abs(p) >= .01)] = 1              # faded: moved the other way, >=1%
    out[v] = np.where(out[v] == -1, 2, out[v])           # none: small / ambiguous
    return out
