"""Checklist engine, dials 1-4 + lever 5 history (DIAL_TABLE v2.7 / HISTORY_LEVER v2.6).
Answers only. No outcomes and no returns-after-D are computed anywhere in this file. Data stops at 2024-12-31 (2025-26 sealed).
usage: python3 engine.py --tickers AAPL,MSFT,...   (smoke)   |   python3 engine.py --all  (full run; not yet authorised)"""
import os
from datapaths import D
import sys as _s; _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'integrity')); import mcap_fix as MF
import sys, os, time, json, argparse, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facets, facets_ext, facets_cal, facets_v26, facets_v27, facets_events
from facets import REG, indicators
import facets_v271 as H71
from params import P, DEFAULTS, CROSS, set_params
HIST = []
END = pd.Timestamp('2024-12-31'); START = pd.Timestamp('2020-01-02')
QUAR = D('/workspace/checklist_engine/integrity/quarantine.csv')
DIALS = D('/workspace/checklist_dials/DIAL_TABLE_v2.7.csv'); HISTF = D('/workspace/checklist_dials/v2.7.1/HISTORY_LEVER_v2.7.1.csv')
OUT = os.environ.get('OUT_DIR', '/workspace/checklist_engine/answers_2020_24')

def load_context():
    etf = pd.read_parquet(D('/workspace/pricehist/etf_2015.parquet')); etf = etf[etf.date <= END]
    spy = etf[etf.ticker == 'SPY'].set_index('date').close.sort_index()
    vix = pd.read_parquet(D('/workspace/data/fred/VIXCLS.parquet')).set_index('date').value.sort_index()
    vix.index = pd.to_datetime(vix.index); vix = vix[vix.index <= END]
    sh = pd.read_parquet(D('/workspace/mcap/nb_tags_v2/sec_shares_out_filed_le_2024.parquet'))
    sh['filed'] = pd.to_datetime(sh.filed); sh = sh[(sh.filed <= END) & (sh.val > 0)].sort_values('filed')
    rs = pd.read_csv(D('/workspace/regsho_nasdaq_th_2020_24.csv'), usecols=['date', 'symbol']); rs['date'] = pd.to_datetime(rs.date.astype(str))
    rs = rs[rs.date <= END]
    br = D('/workspace/checklist_engine/breadth_2020_24.parquet')
    if os.path.exists(br): breadth = pd.read_parquet(br).breadth
    else:
        u = pd.read_parquet(D('/workspace/pricehist/universe_2020_survivors.parquet'), columns=['ticker', 'date', 'close'], filters=[('date', '<=', END)])
        px = u.pivot_table(index='date', columns='ticker', values='close'); m = px.rolling(50).mean()
        breadth = ((px > m).sum(1) / m.notna().sum(1)).where(m.notna().sum(1) > 100); breadth.to_frame('breadth').to_parquet(br)
    return dict(spy=spy, vix=vix, shares=sh, regsho=rs, breadth=breadth, sessions=spy.index.values,
                halts_by=_load_halts(), si_by=_load_si(), earn_by=_load_earnings())

# ---- event sources for groups 034+ (facets_events). Every load is OPTIONAL: a missing file yields an
# empty dict and every event column answers -1 (n_a), so runs without the data are unaffected.
def _opt_parq(name_glob):
    import glob
    fs = sorted(glob.glob(D(name_glob)))
    if not fs: return None
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)

def _load_halts():
    """nasdaq halts: reason factorized LUDP=0 / regulatory(T12)=2 / everything else=1(news/other)."""
    h = _opt_parq('/workspace/data-ext/nasdaq_halts_2020_2026.parquet')
    if h is None: return {}
    h = h.copy()
    h['halt_dt'] = pd.to_datetime(h.halt_date, format='%m/%d/%Y').values
    h['resume_dt'] = pd.to_datetime(h.resume_date, format='%m/%d/%Y').values
    h = h[h.halt_dt <= END]
    r = h.reason.astype(str).str.upper()
    h['rsn_code'] = np.where(r.str.startswith('LUDP'), 0, np.where(r == 'T12', 2, 1))
    return {k: g[['halt_dt', 'resume_dt', 'rsn_code']] for k, g in h.groupby('symbol')}

def _load_si():
    """FINRA short interest by PUBLICATION date (never settlement date)."""
    s = _opt_parq('/workspace/data-ext/finra_si_*.parquet')
    if s is None: return {}
    s = s.copy()
    s['pub'] = pd.to_datetime(s.publication_date).values
    s = s[(s.pub <= END) & (s.current_short_qty > 0)].sort_values('pub')
    return {k: g[['pub', 'current_short_qty', 'previous_short_qty', 'days_to_cover']] for k, g in s.groupby('symbol')}

def _load_earnings():
    """Nasdaq earnings calendar (report date, surprise %, eps delta)."""
    e = _opt_parq('/workspace/data-ext/nasdaq_calendar_*.parquet')
    if e is None: return {}
    e = e.copy()
    e['rep'] = pd.to_datetime(e.report_date).values
    e = e[e.rep <= END]
    tl = e.time_label.astype(str).str.upper()
    e['bmo'] = tl.str.contains('BMO') & ~tl.str.contains('AMC')   # AMC/unknown prints are only knowable next session
    return {k: g[['rep', 'surprise_pct_fill', 'eps_delta', 'bmo']] for k, g in e.groupby('symbol')}

def load_bars(tickers=None):
    f = [('date', '<=', END)] + ([('ticker', 'in', tickers)] if tickers else [])
    u = pd.read_parquet(D('/workspace/pricehist/universe_2020_survivors.parquet'), filters=f)
    p = pd.read_parquet(D('/workspace/updown/bars_all.parquet'), filters=[('date', '<', START)] + ([('ticker', 'in', tickers)] if tickers else []))
    cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
    b = pd.concat([p[cols], u[cols]]); b['ticker'] = b.ticker.astype(str)
    return b.drop_duplicates(['ticker', 'date']).sort_values(['ticker', 'date'])

TREE = D('/workspace/checklist_dials/v2.7.1/QUESTION_TREE_v2.7.1.csv')   # v2.7.1 FINAL (Drive 1fuvR3MLfADWUXIpT996xG6CrUec539s-)
GRID = os.environ.get('GRID_FILE', '/workspace/checklist_engine/grid.csv')

def load_history(path):
    h = pd.read_csv(path); h = h[h.status == 'keep']; bad = []
    for r in h.itertuples():
        if r.history_value not in H71.LAB: bad.append(r.history_value); continue
        HIST.append((r.lever1_type, r.variant, r.history_value, H71.LAB[r.history_value], ()))
    if bad: raise SystemExit(f'history values with no locked buckets: {sorted(set(bad))}')
    return h

def load_grid():
    """grid.csv: name,values,mode  (mode cross = full cross with the other cross params; oat = one at a time, others at default)"""
    if not os.path.exists(GRID): return {}
    g = pd.read_csv(GRID); return {r['name']: ([(int(float(x)) if isinstance(DEFAULTS[r['name']], int) else float(x)) for x in str(r['values']).split('|')], r['mode']) for _, r in g.iterrows()}

def settings_for(used, grid):
    """list of (suffix, overrides) for a question that reads params `used`. Default first."""
    cr = [p for p in CROSS if p in used and p in grid]; oat = [p for p in sorted(used) if p in grid and p not in CROSS]
    import itertools
    out = []
    for combo in itertools.product(*[grid[p][0] for p in cr]) if cr else [()]:
        o = dict(zip(cr, combo)); out.append(('|p:' + ','.join(f"{k}={v:g}" for k, v in o.items()) if o else '', o))
    for p in oat:
        for x in grid[p][0]:
            if x == DEFAULTS[p]: continue
            o = {q: DEFAULTS[q] for q in cr}; o[p] = x
            out.append(('|p:' + ','.join(f"{k}={v:g}" for k, v in o.items()), o))
    return out

def tf_plan():
    """(kind, key) -> sorted [(k, N)]. Tree timeframes for every question the engine has; engine's own daily lookbacks are kept too
    (flagged engine_extra) so nothing is silently dropped. Returns plan + coverage report."""
    t = pd.read_csv(TREE); t['k'] = t.L2_timeframe.str.split('x').str[0].astype(int); t['N'] = t.L2_timeframe.str.split('x').str[1].astype(int)
    tb = t[t.part == 'base'].groupby(['L3_derivative', 'L4_analysis'])[['k', 'N']].apply(lambda g: set(map(tuple, g.values))).to_dict()
    th = t[t.part == 'history'].groupby(['L3_derivative', 'L4_analysis'])[['k', 'N']].apply(lambda g: set(map(tuple, g.values))).to_dict()
    plan = {}; rep = dict(tree_base=int((t.part == 'base').sum()), tree_hist=int((t.part == 'history').sum()), base_built=0, hist_built=0, extra=0)
    for (v, f, labels, fn, lbs) in REG:
        tree = tb.get((v, f), set()); own = {(1, N) for N in lbs}; plan[('B', v, f)] = sorted(tree | own)
        rep['base_built'] += len(tree); rep['extra'] += len(own - tree)
    for (lt, v, hv, labels, lbs) in HIST:
        tree = th.get((v, hv), set()); plan[('H', v, hv)] = sorted(tree); rep['hist_built'] += len(tree)
    return plan, rep

def make_I(d, tk, C):
    dates = d.date.values; I = indicators(d); I['dates'] = dates; I['sessions'] = C['sessions']
    al = lambda s: s.reindex(pd.DatetimeIndex(dates)).ffill().values.astype(float)
    I['spy'] = al(C['spy']); I['spyret'] = I['spy'] / np.r_[np.nan, I['spy'][:-1]] - 1
    I['vix'] = al(C['vix']); I['breadth'] = al(C['breadth'])
    f = MF.factor_after(tk, np.asarray(dates, 'datetime64[ns]')); I['f'] = f
    I['craw'], I['hraw'], I['lraw'], I['vraw'] = I['c']*f, I['h']*f, I['l']*f, I['v']/f
    s = C['shares_by'].get(tk)
    if s is not None: _, mc = MF.mcap_series(tk, dates, I['c'], s); I['shares'] = mc / I['craw']
    else: I['shares'] = np.full(len(d), np.nan)
    I['regsho'] = np.isin(dates, C['regsho_by'].get(tk, np.array([], 'datetime64[ns]'))).astype(float)
    I['regsho'][dates < np.datetime64('2020-01-02')] = np.nan
    _events_I(I, tk, C, dates)
    return I

def _ev_cnt_last(dates, ev):
    """events (datetime64 sorted) -> (per-bar counts, per-bar last-event index or -1). An event dated e belongs to
    the first bar whose end date >= e; events after the last bar are DROPPED (they must not pile onto the final
    bar, which would leak future events into a truncated history). Values at bar t use only events <= dates[t]."""
    T = len(dates); cnt = np.zeros(T); li = np.searchsorted(ev, dates, side='right') - 1
    if len(ev):
        j = np.searchsorted(dates, ev, side='right') - 1
        j = j[(j >= 0) & (ev <= dates[-1])]          # events after the last bar are DROPPED, not piled onto it
        np.add.at(cnt, j, 1)
    return cnt, li

def _asof_active(T, bars, vals, lag):
    """per-bar array: vals[k] is knowable from bar bars[k]+lag onwards; NaN before. bars/vals aligned; lag >= 0."""
    out = np.full(T, np.nan)
    if len(bars):
        ab = bars + lag; m = ab < T
        if m.any():
            ab = np.maximum(ab[m], 0); vv = vals[m]
            li = np.searchsorted(ab, np.arange(T), side='right') - 1
            mm = li >= 0; out[mm] = vv[np.clip(li, 0, None)][mm]
    return out

def _events_I(I, tk, C, dates):
    """groups 034+ event columns (facets_events). ALL values at bar t use only events dated <= dates[t];
    engine shifts one bar, so the stored answer for day D uses events <= D-1. No data -> all NaN / 0 counts."""
    T = len(dates); idx = np.arange(T)
    c = I['c']; o = I['o']
    nan = np.full(T, np.nan)
    # ---------------- halts
    hf = (C.get('halts_by') or {}).get(tk)
    if hf is not None and len(hf):
        hd = np.sort(hf.halt_dt.values)
        cnt, li = _ev_cnt_last(dates, hd)
        I['halt_cnt'] = cnt
        jb = np.searchsorted(dates, hd, side='right') - 1        # bar of each halt event
        hbar = jb[np.clip(li, 0, None)]
        I['halt_last'] = np.where(li >= 0, hbar, np.nan)
        I['halt_since'] = np.where(li >= 0, idx - hbar, np.nan)
        rsn = hf.rsn_code.values[np.argsort(hf.halt_dt.values, kind='stable')]
        I['halt_rsn'] = np.where(li >= 0, rsn[np.clip(li, 0, None)], np.nan).astype(float)
        ret = np.nan_to_num(I['ret'], nan=0.0)
        cs = np.r_[0.0, np.cumsum(ret)]
        hb = hbar
        lo = np.maximum(hb - 5, 0)
        pre = np.where(li >= 0, cs[hb] - cs[lo], np.nan)      # net 1-bar returns over <=5 bars before the halt
        pre = np.where(li >= 0, np.where(hb >= 1, pre, np.nan), np.nan)
        I['halt_predir'] = pre
        rd = hf.resume_dt.values; mres = np.isfinite(rd) & (rd <= END)
        if mres.any():
            rsub = hf[mres].sort_values('resume_dt')
            rb = np.searchsorted(dates, rsub.resume_dt.values, side='right') - 1   # resume session bar
            mbar = (rb >= 0) & (rsub.resume_dt.values <= dates[-1])              # future resumes: dropped, not piled
            rli = np.searchsorted(rsub.resume_dt.values[mbar], dates, side='right') - 1
            rbb = rb[mbar]
            hres = np.where(rli >= 0, rbb[np.clip(rli, 0, None)], -1)
            know = (rli >= 0) & (hres >= 0) & (hres < T)
            respx = c[np.clip(hres, 0, None)]
            I['halt_res'] = np.where(know, hres, np.nan)
            I['halt_resret'] = np.where(know & (respx > 0), c / respx - 1, np.nan)
        else:
            I['halt_res'] = nan; I['halt_resret'] = nan
    else:
        I['halt_cnt'] = np.zeros(T); I['halt_last'] = nan; I['halt_since'] = nan
        I['halt_rsn'] = nan; I['halt_predir'] = nan; I['halt_res'] = nan; I['halt_resret'] = nan
    # ---------------- short interest (publication-date keyed)
    sf = (C.get('si_by') or {}).get(tk)
    if sf is not None and len(sf):
        sf = sf.sort_values('pub')
        pb = np.searchsorted(dates, sf.pub.values, side='right') - 1      # report bar (pub date on a session)
        mpb = (pb >= 0) & (sf.pub.values <= dates[-1])                    # future reports: dropped, not piled
        pb = pb[mpb]; qty = sf.current_short_qty.values[mpb]; prv = sf.previous_short_qty.values[mpb]
        dtc = sf.days_to_cover.values[mpb]; pubv = sf.pub.values[mpb]
        rcnt, _ = _ev_cnt_last(dates, pubv)
        I['si_rep'] = rcnt
        li = np.searchsorted(pubv, dates, side='right') - 1
        k = np.clip(li, 0, None); has = li >= 0
        I['si_qty'] = np.where(has, qty[k], np.nan); I['si_prev'] = np.where(has, prv[k], np.nan)
        I['si_dtc'] = np.where(has, dtc[k], np.nan)
        sh = I['shares']; shb = np.where(np.isfinite(sh), sh, np.nan)
        shp = shb[np.clip(pb, 0, T - 1)]
        pct_at_pub = np.where((pb < T) & (shp > 0), qty / shp * 100, np.nan)
        p26 = np.full(len(qty), np.nan)
        for k2 in range(len(qty)):                                        # percentile of report k2's SI% within trailing 26
            w = pct_at_pub[max(0, k2 - 25):k2 + 1]; w = w[np.isfinite(w)]
            if len(w): p26[k2] = (w <= pct_at_pub[k2]).mean() * 100
        I['si_pct26'] = np.where(has, p26[k], np.nan)
        pchg = np.full(len(qty), np.nan)                                  # price change between consecutive report dates
        for k2 in range(1, len(qty)):
            b0, b1 = pb[k2 - 1], pb[k2]
            if 0 <= b0 < T and 0 <= b1 < T and c[b0] > 0: pchg[k2] = c[b1] / c[b0] - 1
        I['si_prchg'] = np.where(has & (li >= 1), pchg[k], np.nan)
    else:
        I['si_rep'] = np.zeros(T); I['si_qty'] = nan; I['si_prev'] = nan; I['si_dtc'] = nan
        I['si_pct26'] = nan; I['si_prchg'] = nan
    # ---------------- earnings (report-date calendar; the print itself lags one session unless BMO)
    ef = (C.get('earn_by') or {}).get(tk)
    if ef is not None and len(ef):
        ef = ef.sort_values('rep')
        rb = np.searchsorted(dates, ef.rep.values, side='right') - 1
        mrb = (rb >= 0) & (ef.rep.values <= dates[-1])                    # future reports: dropped, not piled
        rb = rb[mrb]; surp = ef.surprise_pct_fill.values[mrb]; bmo = ef.bmo.values[mrb].astype(int)
        repv = ef.rep.values[mrb]
        ecnt, li = _ev_cnt_last(dates, repv)
        I['earn_cnt'] = ecnt
        rlast = np.clip(li, 0, None)
        I['earn_last'] = np.where(li >= 0, rb[rlast], np.nan)             # BAR of the last report (for staleness windows)
        I['earn_since'] = np.where(li >= 0, idx - rb[rlast], np.nan)
        lag = 1 - bmo                                                     # BMO prints knowable same session; AMC/unknown next
        I['earn_surp'] = _asof_active(T, rb, surp, lag)
        strk = np.zeros(len(surp), int)                                   # consecutive beats ending at each report
        for k2 in range(len(surp)):
            j2 = k2
            while j2 >= 0 and surp[j2] > 0: j2 -= 1
            strk[k2] = k2 - j2 if surp[k2] > 0 else 0
        I['earn_streak'] = _asof_active(T, rb, strk.astype(float), lag)
        prerun = np.full(len(rb), np.nan)                                 # 20-bar move into the report
        for k2 in range(len(rb)):
            if rb[k2] >= 20 and c[rb[k2] - 20] > 0: prerun[k2] = c[rb[k2]] / c[rb[k2] - 20] - 1
        I['earn_prerun'] = _asof_active(T, rb, prerun, 0)
        gap = np.full(len(rb), np.nan)                                    # first-session gap after the report
        post5 = np.full(len(rb), np.nan)
        for k2 in range(len(rb)):
            r0 = rb[k2]
            if 0 <= r0 + 1 < T and c[r0] > 0:
                gap[k2] = o[r0 + 1] / c[r0] - 1
                if 0 <= r0 + 5 < T: post5[k2] = c[r0 + 5] / c[r0] - 1
        I['earn_gap'] = _asof_active(T, rb, gap, 1)
        I['earn_post5'] = _asof_active(T, rb, post5, 5)
    else:
        I['earn_cnt'] = np.zeros(T); I['earn_last'] = nan; I['earn_since'] = nan
        I['earn_surp'] = nan; I['earn_streak'] = nan; I['earn_prerun'] = nan; I['earn_gap'] = nan; I['earn_post5'] = nan

def kbars(d, k, o):
    """k-day bars ending on every day t with t % k == o (bar = days t-k+1..t). Returns frame + positions in d."""
    if k == 1: return d, np.arange(len(d))
    r = pd.DataFrame(dict(date=d.date, open=d.open.shift(k-1), high=d.high.rolling(k).max(), low=d.low.rolling(k).min(),
                          close=d.close, volume=d.volume.rolling(k).sum()))
    pos = np.arange(o, len(d), k); pos = pos[pos >= k-1]
    return r.iloc[pos].reset_index(drop=True), pos

USES = {}; GRIDV = {}
import signal
QTIMEOUT = float(os.environ.get('Q_TIMEOUT_S', '0'))   # per-question time limit (seconds, per ticker); 0 = off
_HAS_ALRM = hasattr(signal, 'SIGALRM') and hasattr(signal, 'setitimer')   # Unix only; Windows: timeout off, run unpatched formulas
class QuestionTimeout(Exception): pass
def _alarm(sig, frm): raise QuestionTimeout(f'question took > {QTIMEOUT}s')
if QTIMEOUT and _HAS_ALRM: signal.signal(signal.SIGALRM, _alarm)
elif QTIMEOUT and not os.environ.get('KIMI_TIMEOUT_WARNED'):
    os.environ['KIMI_TIMEOUT_WARNED'] = '1'   # env is inherited by spawned workers: warn once per run, not once per worker
    print('WARNING: Q_TIMEOUT_S set but SIGALRM unavailable on this platform; per-question timeout disabled', flush=True)
def run_ticker(tk, d, C, plan):
    d = d.reset_index(drop=True); T = len(d); cols = {}; err = {}
    REGd = {(v, f): (labels, fn) for (v, f, labels, fn, lbs) in REG}; HISTd = {(v, hv) for (lt, v, hv, labels, lbs) in HIST}
    ks = sorted({k for tfs in plan.values() for k, N in tfs})
    for k in ks:
        for o in range(k):
            dk, pos = kbars(d, k, o)
            if len(dk) < 15: continue
            I = make_I(dk, tk, C); I['dates'] = d.date.values[pos]; ML = {}
            for key, tfs in plan.items():
                Ns = [N for kk, N in tfs if kk == k]
                if not Ns: continue
                if key[0] == 'H' and key[1] not in ('3ATR_legs',) and ML.get(key[1], 0) is None: continue
                def one(N):
                    if key[0] == 'B':
                        return f"{key[1]}|{key[2]}|{k}d|{N}", np.asarray(REGd[key[1:]][1](I, N))
                    v, hv = key[1:]; mk = (v, P['leg_atr'] if v == '3ATR_legs' else 0)
                    if mk not in ML: ML[mk] = H71.series(I, v)
                    if ML[mk] is None: ML[v] = None; return f"H|{v}|{hv}|{k}d|{N}", None
                    return f"H|{v}|{hv}|{k}d|{N}", H71.hist(hv, ML[mk], I, N, v)
                for N in Ns:
                    P.used = set()
                    try:
                        if QTIMEOUT and _HAS_ALRM: signal.setitimer(signal.ITIMER_REAL, QTIMEOUT)
                        name, a = one(N)
                    except Exception as e: err[f"{key}|{k}d|{N}"] = repr(e)[:160]; continue
                    finally:
                        if QTIMEOUT and _HAS_ALRM: signal.setitimer(signal.ITIMER_REAL, 0)
                    if a is None: continue
                    if len(a) != len(pos): err[f"{key}|{k}d|{N}"] = f'length {len(a)} != bars {len(pos)}'; continue
                    used = USES.setdefault(key, set()); used |= P.used
                    for suf, o in settings_for(used, GRIDV):
                        if all(DEFAULTS[q] == x for q, x in o.items()): a2 = a
                        else:
                            set_params(o)
                            try: _, a2 = one(N)
                            except Exception as e: err[f"{key}|{k}d|{N}{suf}"] = repr(e)[:160]; continue
                            finally: set_params({})
                        cols.setdefault(name + suf, np.full(T, -1, np.int8))[pos] = a2
    A = pd.DataFrame(cols)
    A = A.shift(1).fillna(-1).astype(np.int8)        # LEAK RULE: answer for day D uses bars < D only (k-day bar ending D-1)
    dates = d.date.values; A.insert(0, 'date', dates); A.insert(0, 'ticker', tk)
    A['bars_before_D'] = np.arange(T).astype(np.int32)
    A['history_short_252'] = A.bars_before_D < 252; A['history_short_756'] = A.bars_before_D < 756
    F = filter_cols(tk, d, C)
    for c in ('mcap_D1', 'dollar_vol_med20_D1', 'passes_filter'): A[c] = F[c].values
    A = A[(A.date >= START) & (A.date <= END)]
    A['mcap_suspect'] = tk in C.get('mcap_jump', ())
    A['split'] = np.where(A.date <= pd.Timestamp('2022-12-31'), 'discover_2020_22', 'check_2023_24')
    return A, err

def filter_cols(tk, d, C):
    """Tradeable filter for day D, known at D-1: mcap (split-fixed) >= $100M (UNKNOWN EXCLUDED per
    dictionary C27 as directed in 0b 2026-10-25: 'unknown market cap means excluded') and median
    20d $vol >= $1M."""
    d = d.reset_index(drop=True); I = make_I(d, tk, C)
    dv = pd.Series(I['dv']).rolling(20).median().shift(1).values
    mcap = np.array(pd.Series(I['craw'] * I['shares']).shift(1).values, float)   # writable copy (mcap_bad tickers set it to nan)
    if tk in C.get('mcap_bad', ()): mcap[:] = np.nan          # ADR/units problem: mcap unknown
    suspect = tk in C.get('mcap_jump', ())
    # 553 suspect-mcap names keep the dollar-volume-only path (their mcap exists but is distrusted);
    # genuinely-unknown mcap (mcap_bad) now FAILS the filter instead of passing.
    pf = (dv >= 1e6) if suspect else ((mcap >= 1e8) & (dv >= 1e6))
    return pd.DataFrame(dict(date=d.date.values, mcap_D1=mcap.astype(np.float32), dollar_vol_med20_D1=dv.astype(np.float32), passes_filter=pf))

def codebook(plan):
    lab = {('B', v, f): labels for (v, f, labels, fn, lbs) in REG}; lab.update({('H', v, hv): labels for (lt, v, hv, labels, lbs) in HIST})
    cb = {}
    for key, tfs in plan.items():
        for k, N in tfs: cb[(f"H|{key[1]}|{key[2]}" if key[0] == 'H' else f"{key[1]}|{key[2]}") + f"|{k}d|{N}"] = lab[key]
    assert max(len(x) for x in cb.values()) < 127, 'int8 codes overflow'
    return cb

def codebook_cols(cols):
    lab = {f"{v}|{f}": labels for (v, f, labels, fn, lbs) in REG}; lab.update({f"H|{v}|{hv}": labels for (lt, v, hv, labels, lbs) in HIST})
    cb = {}
    for c in cols:
        p = c.split('|p:')[0].split('|')
        if len(p) < 4: continue
        base = '|'.join(p[:-2])
        if base not in lab: raise SystemExit(f'column {c}: no label set')
        cb[c] = list(lab[base])
    return cb

def wait_upload(yr, path, sha):
    """Year-by-year mode: the agent uploads `path` to Drive, checks it, then writes <path>.uploaded = JSON {drive_id, sha256}.
    Only when the sha matches is the local copy deleted and the next year started."""
    mark = path + '.uploaded'; print(f"WAITING_UPLOAD {yr} {path} sha256={sha}", flush=True)
    while not os.path.exists(mark): time.sleep(20)
    m = json.load(open(mark))
    if m.get('sha256') != sha: raise SystemExit(f"upload check failed for {yr}: {m}")
    os.remove(path); print(f"UPLOADED {yr} drive_id={m.get('drive_id')} local deleted", flush=True)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--tickers'); ap.add_argument('--all', action='store_true')
    ap.add_argument('--i-am-authorised', action='store_true'); ap.add_argument('--years', default='2020,2021,2022,2023,2024'); a = ap.parse_args()
    t0 = time.time(); print('HISTORY_BUCKETS sha256 OK:', H71.load_buckets()); load_history(HISTF)
    GRIDV.update(load_grid()); print('grid:', GRIDV)
    plan, rep = tf_plan(); print('coverage:', rep)
    C = load_context()
    C['shares_by'] = {k: g for k, g in C['shares'].groupby('ticker')}
    C['regsho_by'] = {k: g.date.values for k, g in C['regsho'].groupby('symbol')}
    tks = a.tickers.split(',') if a.tickers else None
    Q = pd.read_csv(QUAR); C['mcap_bad'] = set(Q[Q.action == 'mcap_unknown'].ticker); C['mcap_jump'] = set(Q[Q.action == 'flag'].ticker)
    skip = set(Q[Q.action == 'exclude'].ticker)
    if tks: print('quarantined, skipped:', sorted(set(tks) & skip)); tks = [t for t in tks if t not in skip]
    if not tks and not (a.all and a.i_am_authorised): sys.exit('pass --tickers (smoke); --all needs --i-am-authorised (not given)')
    os.makedirs(OUT, exist_ok=True); 
    B = load_bars(tks); B = B[~B.ticker.astype(str).isin(skip)]; allerr = {}
    if tks:
        parts = []
        for tk, g in B.groupby('ticker'):
            A, e = run_ticker(tk, g, C, plan); parts.append(A); allerr.update({f"{tk}:{k}": v for k, v in e.items()})
        R = pd.concat(parts); json.dump(codebook_cols(R.columns), open(f"{OUT}/codebook.json", 'w')); R.to_parquet(f"{OUT}/smoke.parquet", index=False, compression='zstd')
        print(json.dumps(dict(rows=len(R), cols=R.shape[1], secs=round(time.time() - t0, 1), n_err=len(allerr), errors=dict(list(allerr.items())[:30])), indent=1))
    else:   # year-by-year: compute every ticker, keep only that year's rows, write+compress, upload+verify, delete, next year
        import hashlib
        for yr in map(int, a.years.split(',')):
            parts = []
            for tk, g in B.groupby('ticker'):
                A, e = run_ticker(tk, g[g.date <= pd.Timestamp(f'{yr}-12-31')], C, plan)
                parts.append(A[A.date.dt.year == yr])
            p = f"{OUT}/answers_{yr}.parquet"; pd.concat(parts).to_parquet(p, index=False, compression='zstd'); parts = None
            sha = hashlib.sha256(open(p, 'rb').read()).hexdigest(); wait_upload(yr, p, sha)
