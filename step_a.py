"""Step A: every built question at default cutoffs, full survivors universe, DISCOVER window 2020-01-02..2022-12-31 only.
Bars are cut at 2022-12-31 before anything is computed, so 2023-24 (confirm) and 2025-26 (sealed) are never touched.
Disk: answers are saved per chunk as compressed int8 (answers_NNN.npz, SAVE_ANSWERS=1 default; chunks with scores but no answers are re-run). Questions are processed in chunks: compute the chunk for every
ticker in RAM -> build trade rows -> score -> write small result file -> drop. Resumable (finished chunks are skipped).
Disk floor checked before each chunk: 7GB free 17:00-21:00 HKT, 2GB otherwise; it waits if below.
usage: CHECKLIST_DATA_DIR=... OUT_DIR=... python3 step_a.py [--workers 5] [--chunk 400] [--tickers A,B]"""
import os, sys, time, json, shutil, argparse, warnings, datetime as dt; warnings.filterwarnings('ignore')
os.environ.setdefault('Q_TIMEOUT_S', '120')          # one question on one ticker may not take > 2 min; recorded as error
os.environ.setdefault('GRID_FILE', '/nonexistent')            # Step A = default cutoffs only (grid sweep is Step B)
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from scoring import trades as TR
from multiprocessing import Pool
WEND = pd.Timestamp('2022-12-31'); G = {}

def log(*a): print(dt.datetime.now().strftime('%m-%d %H:%M:%S'), *a, flush=True)
def disk_ok(path):
    free = shutil.disk_usage(path).free / 1e9; h = dt.datetime.now().hour; need = 7 if 17 <= h < 21 else 2
    return free >= need, free, need

def _init_child(plan, cols):
    """Windows-spawn compat: Pool workers re-import this module and start with empty globals (Unix fork would
    inherit them). Restore engine state and the small shared objects in each worker. Plumbing only — no formula,
    data, or scoring changes. C is rebuilt from the data folder per worker (cheap) instead of being pickled.
    plan/cols may be None (base phase doesn't need them)."""
    os.environ.setdefault('GRID_FILE', '/nonexistent')
    E.H71.load_buckets(); E.HIST.clear(); E.load_history(E.HISTF); E.GRIDV.clear(); E.GRIDV.update(E.load_grid())
    c = E.load_context()
    c['shares_by'] = {k: g for k, g in c['shares'].groupby('ticker')}
    c['regsho_by'] = {k: g.date.values for k, g in c['regsho'].groupby('symbol')}
    q = pd.read_csv(E.QUAR); c['mcap_bad'] = set(q[q.action == 'mcap_unknown'].ticker); c['mcap_jump'] = set(q[q.action == 'flag'].ticker)
    G['C'], G['plan'], G['cols'] = c, plan, cols

def w_base(t):
    tk, d = t          # task carries its own bars (spawn-safe; fork used to read them from G['B'])
    tr = TR.ticker_trades(tk, d, G['C']['sessions'], 'discover')
    F = E.filter_cols(tk, d, G['C']).set_index('date'); return tr.join(F[['passes_filter', 'mcap_D1']], on='date')

def w_answers(t):
    tk, d, idx = t
    if idx is None: return tk, None, {}
    A, err = E.run_ticker(tk, d, G['C'], G['plan']); A = A.set_index('date').reindex(idx)
    M = np.full((len(idx), len(G['cols'])), -1, np.int8)
    for j, c in enumerate(G['cols']):
        if c in A.columns: M[:, j] = A[c].fillna(-1).to_numpy(np.int8)
    return tk, M, err

def _init_score(kk, _unused):
    """Scoring-phase workers: trade rows + a fresh luck-check module (module objects don't
    pickle, so each worker rebuilds it identically via TR.luck_check())."""
    G['k'] = kk
    G['L'] = TR.luck_check()

def w_score(jm):
    col, m = jm
    return TR.score_question(TR.trade_rows(G['k'], m, col), G['L'])

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=5); ap.add_argument('--chunk', type=int, default=400)
    ap.add_argument('--tickers'); ap.add_argument('--force', default='',
        help='comma chunk indices to recompute even if finished (dictionary-fix reruns); empty = normal resume')
    a = ap.parse_args()
    force = {int(x) for x in a.force.split(',') if x.strip()}
    import threading
    def heartbeat():
        lw, lm = time.time(), time.monotonic()
        while True:
            time.sleep(300); w, m = time.time(), time.monotonic(); ok, free, need = disk_ok(os.environ.get('OUT_DIR', '/workspace'))
            try: load = f", load {os.getloadavg()[0]:.1f}"
            except (AttributeError, OSError): load = ""   # no getloadavg on Windows
            gap = (w - lw) - (m - lm)
            log(f"heartbeat: alive, disk {free:.1f}GB free (floor {need}GB){load}" + (f", box was paused ~{gap/60:.0f} min" if gap > 60 else ''))
            lw, lm = w, m
    threading.Thread(target=heartbeat, daemon=True).start()
    OUT = os.environ.get('OUT_DIR', '/workspace/step_a_out'); os.makedirs(f'{OUT}/chunks', exist_ok=True); t0 = time.time()
    log('HISTORY_BUCKETS sha OK', E.H71.load_buckets()); E.load_history(E.HISTF); E.GRIDV.update(E.load_grid()); log('grid', E.GRIDV)
    plan, rep = E.tf_plan(); log('coverage', rep)
    C = E.load_context(); C['shares_by'] = {k: g for k, g in C['shares'].groupby('ticker')}
    C['regsho_by'] = {k: g.date.values for k, g in C['regsho'].groupby('symbol')}
    Q = pd.read_csv(E.QUAR); C['mcap_bad'] = set(Q[Q.action == 'mcap_unknown'].ticker); C['mcap_jump'] = set(Q[Q.action == 'flag'].ticker)
    skip = set(Q[Q.action == 'exclude'].ticker); tks = a.tickers.split(',') if a.tickers else None
    B = E.load_bars(tks); B = B[(B.date <= WEND) & ~B.ticker.isin(skip)]
    G['B'] = {k: g.reset_index(drop=True) for k, g in B.groupby('ticker')}; del B; G['C'] = C; L = TR.luck_check(); G['L'] = L
    log('tickers', len(G['B']))
    bp = f'{OUT}/trade_base_discover.parquet'
    if os.path.exists(bp): base = pd.read_parquet(bp)
    else:
        with Pool(a.workers, initializer=_init_child, initargs=(None, None)) as p:
            base = pd.concat(p.map(w_base, [(tk, G['B'][tk]) for tk in G['B']], chunksize=20))
        etf = pd.read_parquet(E.D('/workspace/pricehist/etf_2015.parquet')); spy = etf[(etf.ticker == 'SPY') & (etf.date <= WEND)].sort_values('date')
        base = TR.add_bench(base, spy.reset_index(drop=True), C['sessions'], 'discover'); base.to_parquet(bp, index=False)
    k = base[base.ready & base.passes_filter & base.bench.notna()].sort_values(['ticker', 'date']).reset_index(drop=True)
    log(f"base: {len(base)} cases, not_ready {int((~base.ready).sum())}, filtered+ready trades {len(k)}, tickers {k.ticker.nunique()}")
    SAVE = os.environ.get('SAVE_ANSWERS', '1') == '1'
    if SAVE: k[['ticker', 'date']].to_parquet(f'{OUT}/chunks/trade_base_rows.parquet', index=False)
    G['base'] = k; G['keep'] = {t: pd.DatetimeIndex(g.date) for t, g in k.groupby('ticker', sort=False)}
    json.dump(dict(cases=len(base), not_ready=int((~base.ready).sum()), fail_filter=int((~base.passes_filter).sum()), trades=len(k),
                   bench_mean=float(k.drop_duplicates('date').bench.mean())), open(f'{OUT}/base_summary.json', 'w'), indent=1)
    del base   # free ~1-2GB before the chunk loops; k has everything the scoring needs
    items = sorted(((key, kn) for key, tfs in plan.items() for kn in tfs), key=lambda x: (x[1][0], x[0], x[1][1]))
    chunks = [items[i:i + a.chunk] for i in range(0, len(items), a.chunk)]; log(f'{len(items)} questions in {len(chunks)} chunks')
    for ci, ch in enumerate(chunks):
        fo = f'{OUT}/chunks/scores_{ci:03d}.parquet'
        fa = f'{OUT}/chunks/answers_{ci:03d}.npz'
        if ci not in force and os.path.exists(fo) and (not SAVE or os.path.exists(fa)): continue
        while True:
            ok, free, need = disk_ok(OUT)
            if ok: break
            log(f'disk {free:.1f}GB < floor {need}GB, waiting'); time.sleep(300)
        sub = {}
        for key, kn in ch: sub.setdefault(key, []).append(kn)
        G['plan'] = sub
        G['cols'] = [(f"H|{key[1]}|{key[2]}" if key[0] == 'H' else f"{key[1]}|{key[2]}") + f"|{kn[0]}d|{kn[1]}" for key, kn in ch]
        tc = time.time()
        tasks = [(tk, G['B'][tk], idx) for tk, idx in G['keep'].items()]
        with Pool(a.workers, initializer=_init_child, initargs=(sub, G['cols'])) as p:
            M = np.full((len(k), len(G['cols'])), -1, np.int8); off = 0; errs = {}; nc = 0
            for tk, m, e in p.imap(w_answers, tasks, chunksize=10):   # imap: fill M streaming, no full result list in RAM
                if m is not None: M[off:off + len(m)] = m; off += len(m)
                errs.update({f'{tk}:{x}': v for x, v in e.items()})
                nc += 1
                if nc % 250 == 0: log(f'  chunk {ci+1}: {nc}/{len(tasks)} tickers, {off}/{len(k)} rows, {len(errs)} errors')
        del tasks
        assert off == len(k)
        if SAVE:   # every day's answer for every question (-1 = blank), row order = trade_base_rows.parquet; for the combining step
            np.savez_compressed(fa + '.tmp.npz', M=M, cols=np.array(G['cols'])); os.replace(fa + '.tmp.npz', fa)
        S = []
        with Pool(min(a.workers, 4), initializer=_init_score, initargs=(k, L)) as p:   # per-question independent; answers pool already closed
            for part in p.imap(w_score, [(G['cols'][j], M[:, j]) for j in range(len(G['cols']))], chunksize=8):
                S += part
        M = None
        pd.DataFrame(S).to_parquet(fo + '.tmp', index=False); os.replace(fo + '.tmp', fo)
        json.dump(errs, open(f'{OUT}/chunks/errors_{ci:03d}.json', 'w'))
        done = ci + 1; el = time.time() - t0
        log(f'chunk {ci+1}/{len(chunks)}: {len(G["cols"])} q, {len(errs)} errors, {time.time()-tc:.0f}s; elapsed {el/3600:.2f}h')
        json.dump(dict(chunk=ci + 1, of=len(chunks), elapsed_h=round(el / 3600, 2), updated=dt.datetime.now().isoformat()), open(f'{OUT}/PROGRESS.json', 'w'))
    R = pd.concat([pd.read_parquet(f'{OUT}/chunks/scores_{i:03d}.parquet') for i in range(len(chunks))]
                  + ([pd.read_parquet(f'{OUT}/chunks/scores_cp_v2.parquet')] if os.path.exists(f'{OUT}/chunks/scores_cp_v2.parquet') else []))   # + chart-picture v2 extras (scoring/cp_v2_extra.py)
    R.to_parquet(f'{OUT}/STEP_A_SCORES_discover_2020_22.parquet', index=False)
    log('DONE', len(R), 'question+answer rows;', {f'passes_{int(f*100)}': int(R[f'passes_{int(f*100)}'].sum()) for f in TR.FLOORS})
