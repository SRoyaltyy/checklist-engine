"""World-snapshot facets (groups 035+): generic fixed-answer families over the
per-stock per-day world columns built by facets_world (kimi/world-snapshot).
Column kinds drive which families are generated; every threshold is hard-coded
here (frozen with the dial tables, same discipline as facets_events).

Data contract (engine._world_i): I['w_<col>'][t] holds the world-snapshot row for
the NEXT session after dates[t]; that row contains only data strictly before its
own date, so the value at bar t uses bars <= dates[t] — exactly the facet
contract. engine then shifts one bar: the stored answer for day D uses data <= D-1.
Missing ticker / column / NaN -> -1 (n_a), the designed missing-data semantics.

Kinds and their families:
  days    level {'<=5','5-20','20-60','>60','none'} + direction + percentile
  count   level {'0','1','2-5','5+','none'}         + direction + percentile
  frac    level {'<0.2','0.2-0.4','0.4-0.6','0.6-0.8','>=0.8','none'} + direction + percentile
  ratio   level {'<0.8','0.8-1.2','>=1.2','none'}   + direction + percentile
  vix     level {'<15','15-20','20-30','>30','none'}+ direction + percentile
  moon    level {'new','crescent','quarter','gibbous','full','none'} (calendar, no direction)
  pos     direction + percentile only (scale-free level buckets make no sense)
  signed  direction + percentile only
  bool    state {'yes','no','n_a'} + flip {'changed','same','n_a'} (vs 1 bar ago)
  tri     state {'bull','bear','neutral','n_a'} (+ flip for event-style tri columns)
"""
import numpy as np
from facets import facet, W, pick, ok

WV = 'world'

def _v(I, col):
    return I.get('w_' + col)

def _T(I):
    return len(I['c'])

def _miss(I):
    return np.full(_T(I), -1, np.int8)

def _lag(v, N):
    out = np.full(len(v), np.nan)
    out[N:] = v[:-N]
    return out

def _pct_rank_1y(v):
    """trailing-252-session percentile of v at t (min 60 obs), NaN before that."""
    X = W(v, 252)
    cnt = np.isfinite(X).sum(1)
    with np.errstate(all='ignore'):
        le = (X <= v[:, None]) & np.isfinite(X)
        r = le.sum(1) / cnt
    r[(cnt < 60) | np.isnan(v)] = np.nan
    return r

# ---------------- registry ----------------
# (column, kind); grouped by world block for readable diffs
COLS = [
    # block I market-wide (I178 VIX + M008/M047 breadth math)
    ('mkt_vix', 'vix'), ('mkt_vix_r5', 'ratio'), ('mkt_vix_d20', 'ratio'),
    ('advdecl', 'ratio'), ('cvi_chg20_m', 'signed'),
    # block E Form 4 (I187)
    ('f4_n20', 'count'), ('f4_n60', 'count'), ('f4_n', 'count'), ('f4_days', 'days'),
    # block L analyst (I197)
    ('an_days', 'days'), ('an_n20', 'count'), ('an_n60', 'count'),
    ('an_up20', 'count'), ('an_dn20', 'count'), ('an_up60', 'count'), ('an_dn60', 'count'),
    ('an_dir', 'bool'),
    # block H XBRL fundamentals (I192)
    ('xb_days', 'days'), ('xb_rev', 'pos'), ('xb_rev_days', 'days'), ('xb_rev_g', 'signed'),
    ('xb_ni', 'pos'), ('xb_ni_days', 'days'), ('xb_ni_g', 'signed'),
    ('xb_assets', 'pos'), ('xb_assets_days', 'days'),
    ('xb_debt', 'pos'), ('xb_debt_days', 'days'),
    ('xb_shares', 'pos'), ('xb_shares_days', 'days'),
    # block O GDELT (I200)
    ('gd_n7', 'count'), ('gd_n30', 'count'), ('gd_days', 'days'), ('gd_spike', 'bool'),
    # block M 13F (I199)
    ('f13_days', 'days'), ('f13_qdays', 'days'), ('f13_n', 'count'), ('f13_q4', 'count'),
    # TradingView computed columns (batches 1-6)
    ('tv_pmo', 'signed'), ('tv_pmo_sig', 'signed'), ('tv_pmo_x', 'bool'),
    ('tv_rci9', 'signed'), ('tv_rci26', 'signed'), ('tv_rci52', 'signed'),
    ('tv_rci_ribbon_up', 'bool'),
    ('tv_moon_age', 'moon'),
    ('tv_adbars_up14', 'count'), ('tv_adbars_dn14', 'count'), ('tv_adbars_ratio14', 'ratio'),
    ('tv_tweezer_bottom', 'bool'), ('tv_tweezer_top', 'bool'), ('tv_falling_window', 'bool'),
    ('tv_chop_slope_bp', 'signed'), ('tv_chop_on', 'bool'),
    ('tv_bbtrend', 'signed'), ('tv_env_pos', 'frac'), ('tv_vavg20', 'pos'), ('tv_volr', 'ratio'),
    ('tv_ts_r2_20', 'frac'),
    ('tv_pw_high', 'pos'), ('tv_pw_low', 'pos'), ('tv_pw_close', 'pos'), ('tv_pw_pos', 'frac'),
    ('tv_adxbo', 'bool'), ('tv_rb_rev', 'tri'), ('tv_cci6', 'signed'), ('tv_cci_zx', 'tri'),
    ('tv_bb_pos', 'frac'),
    ('tv_spec_k', 'signed'),
    ('tv_tr_ma', 'frac'), ('tv_tr_osc', 'frac'), ('tv_tr_total', 'frac'),
    ('tv_seas_mo_up', 'frac'), ('tv_seas_dow_up', 'frac'),
    ('tv_lb_dir', 'tri'), ('tv_kagi_dir', 'tri'), ('tv_renko_dir', 'tri'), ('tv_renko_n', 'count'),
    ('tv_pnf_dir', 'tri'),
    ('tv_tl_hslope', 'signed'), ('tv_tl_hdist', 'signed'),
    ('tv_tl_lslope', 'signed'), ('tv_tl_ldist', 'signed'),
    ('tv_fibx', 'signed'),
    ('tv_pf_slope', 'signed'), ('tv_pf_pos', 'signed'),
    ('tv_mpp_dist', 'signed'), ('tv_ghost_dist', 'signed'),
    ('tv_ew_dir', 'tri'), ('tv_ew_npiv', 'count'),
    ('tv_poc_dist', 'signed'), ('tv_avp_dist', 'signed'),
    ('tv_knox', 'tri'),
    ('tv_pat_dbltop', 'bool'), ('tv_pat_dblbot', 'bool'), ('tv_pat_tri', 'bool'),
    ('tv_pat_rect', 'bool'), ('tv_pat_flag', 'bool'), ('tv_pat_wedge', 'bool'),
    ('tv_pat_hs', 'bool'),
]

LEVEL_LABELS = {
    'days': ['<=5', '5-20', '20-60', '>60', 'none'],
    'count': ['0', '1', '2-5', '5+', 'none'],
    'frac': ['<0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '>=0.8', 'none'],
    'ratio': ['<0.8', '0.8-1.2', '>=1.2', 'none'],
    'vix': ['<15', '15-20', '20-30', '>30', 'none'],
    'moon': ['new', 'crescent', 'quarter', 'gibbous', 'full', 'none'],
}
PCT_LABELS = ['<20%', '20-40%', '40-60%', '60-80%', '>=80%', 'none']

def _level(v, kind):
    T = len(v); out = np.full(T, -1, np.int8)
    m = np.isfinite(v)
    if kind == 'days':
        out[m] = np.where(v[m] <= 5, 0, np.where(v[m] <= 20, 1, np.where(v[m] <= 60, 2, 3)))
    elif kind == 'count':
        out[m] = np.where(v[m] < 0.5, 0, np.where(v[m] < 1.5, 1, np.where(v[m] < 5.5, 2, 3)))
    elif kind == 'frac':
        out[m] = np.clip((v[m] * 5).astype(int), 0, 4)      # [0,.2)->0 ... [.8,1]->4
    elif kind == 'ratio':
        out[m] = np.where(v[m] < 0.8, 0, np.where(v[m] <= 1.2, 1, 2))
    elif kind == 'vix':
        out[m] = np.where(v[m] < 15, 0, np.where(v[m] < 20, 1, np.where(v[m] < 30, 2, 3)))
    elif kind == 'moon':
        # moon age 0-29.53: new <2 or >27.5; crescent 2-6.5; quarter 6.5-9.5; gibbous 9.5-12.5
        # ... symmetric around full at ~14.77: quarter 9.5-12.5 & 16.5-19.5 handled by distance-from-full
        df = np.abs(v[m] - 14.765)      # distance from full
        out[m] = np.where(df <= 1.75, 4,
                 np.where(df <= 5.25, 3,
                 np.where(df <= 8.75, 2,
                 np.where(np.minimum(v[m], 29.5305889 - v[m]) <= 2.0, 0, 1))))
    return out

for _col, _kind in COLS:
    if _kind in ('pos', 'signed', 'frac', 'ratio', 'days', 'count', 'vix'):
        def _dir(I, N, _c=_col):
            v = _v(I, _c)
            if v is None: return _miss(I)
            lg = _lag(v, N)
            with np.errstate(all='ignore'):
                chg = np.where(np.isfinite(v) & np.isfinite(lg) & (lg != 0), v / lg - 1.0, np.nan)
            out = np.full(len(v), -1, np.int8)
            m = np.isfinite(chg)
            out[m] = np.where(chg[m] > 0.005, 0, np.where(chg[m] < -0.005, 1, 2))
            return out
        facet(WV, f'{_col}_direction', ['up', 'down', 'flat'])(_dir)

    if _kind not in ('bool', 'tri', 'moon'):
        def _pct(I, N, _c=_col, _lab=None):
            v = _v(I, _c)
            if v is None: return _miss(I)
            r = _pct_rank_1y(v)
            out = np.full(len(v), -1, np.int8)
            m = np.isfinite(r)
            out[m] = np.clip((r[m] * 5).astype(int), 0, 4)
            return out
        facet(WV, f'{_col}_pctile_1y', PCT_LABELS)(_pct)

    if _kind == 'bool':
        def _st(I, N, _c=_col):
            v = _v(I, _c)
            if v is None: return _miss(I)
            out = np.full(len(v), -1, np.int8)
            m = np.isfinite(v)
            out[m] = (v[m] < 0.5).astype(np.int8)        # 0 = yes(true), 1 = no
            return out
        facet(WV, f'{_col}_state', ['yes', 'no'])(_st)

        def _fl(I, N, _c=_col):
            v = _v(I, _c)
            if v is None: return _miss(I)
            lg = _lag(v, 1)
            out = np.full(len(v), -1, np.int8)
            m = np.isfinite(v) & np.isfinite(lg)
            out[m] = (np.abs(v[m] - lg[m]) < 0.01).astype(np.int8)   # 0 = changed, 1 = same
            return out
        facet(WV, f'{_col}_flip', ['changed', 'same'])(_fl)

    if _kind == 'tri':
        def _tri(I, N, _c=_col):
            v = _v(I, _c)
            if v is None: return _miss(I)
            out = np.full(len(v), -1, np.int8)
            m = np.isfinite(v)
            out[m] = np.where(v[m] > 0.5, 0, np.where(v[m] < -0.5, 1, 2))  # bull / bear / neutral
            return out
        facet(WV, f'{_col}_state', ['bull', 'bear', 'neutral'])(_tri)

# level facets must register with frozen labels; do it cleanly here
def _mk_level(col, kind, labels):
    def _lvl(I, N, _c=col, _k=kind, _lab=labels):
        v = _v(I, _c)
        T = len(I['c'])
        if v is None: return np.full(T, -1, np.int8)
        out = _level(v, _k)
        if _k == 'moon':
            # calendar column: NaN never happens; any non-finite row is a data hole -> 'none'
            return np.where(np.isfinite(v), out, len(_lab) - 1)
        return out
    facet(WV, f'{col}_level', labels)(_lvl)

for _col, _kind in COLS:
    if _kind in LEVEL_LABELS:
        _mk_level(_col, _kind, LEVEL_LABELS[_kind])
