"""Checklist engine, dials 1-4 + lever 5 history (DIAL_TABLE v2.7 / HISTORY_LEVER v2.6).
Answers only. No outcomes and no returns-after-D are computed anywhere in this file. Data stops at 2024-12-31 (2025-26 sealed).
usage: python3 engine.py --tickers AAPL,MSFT,...   (smoke)   |   python3 engine.py --all  (full run; not yet authorised)"""
import os
from datapaths import D
import sys as _s; _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'integrity')); import mcap_fix as MF
import sys, os, time, json, argparse, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facets, facets_ext, facets_cal, facets_v26, facets_v27
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
    return dict(spy=spy, vix=vix, shares=sh, regsho=rs, breadth=breadth, sessions=spy.index.values)

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
    return I

def kbars(d, k, o):
    """k-day bars ending on every day t with t % k == o (bar = days t-k+1..t). Returns frame + positions in d."""
    if k == 1: return d, np.arange(len(d))
    r = pd.DataFrame(dict(date=d.date, open=d.open.shift(k-1), high=d.high.rolling(k).max(), low=d.low.rolling(k).min(),
                          close=d.close, volume=d.volume.rolling(k).sum()))
    pos = np.arange(o, len(d), k); pos = pos[pos >= k-1]
    return r.iloc[pos].reset_index(drop=True), pos

USES = {}; GRIDV = {}
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
                    try: name, a = one(N)
                    except Exception as e: err[f"{key}|{k}d|{N}"] = repr(e)[:160]; continue
                    if a is None: continue
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
    I = make_I(d, tk, C)
    dv = pd.Series(I['dv']).rolling(20).median().shift(1).values
    mcap = (pd.Series(I['craw'] * I['shares']).shift(1)).values
    if tk in C.get('mcap_bad', ()): mcap[:] = np.nan          # ADR/units problem: mcap unknown
    suspect = tk in C.get('mcap_jump', ())
    A['mcap_D1'] = mcap.astype(np.float32); A['dollar_vol_med20_D1'] = dv.astype(np.float32)
    # 553 suspect-mcap names: dollar-volume-only filter (mcap not trusted)
    A['passes_filter'] = (dv >= 1e6) if suspect else ((np.isnan(mcap) | (mcap >= 1e8)) & (dv >= 1e6))
    A = A[(A.date >= START) & (A.date <= END)]
    A['mcap_suspect'] = suspect
    A['split'] = np.where(A.date <= pd.Timestamp('2022-12-31'), 'discover_2020_22', 'check_2023_24')
    return A, err

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
