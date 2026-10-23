"""Step A: every built question at default cutoffs, full survivors universe, DISCOVER window 2020-01-02..2022-12-31 only.
Bars are cut at 2022-12-31 before anything is computed, so 2023-24 (confirm) and 2025-26 (sealed) are never touched.
Disk: answers are never stored in full (would be ~40GB). Questions are processed in chunks: compute the chunk for every
ticker in RAM -> build trade rows -> score -> write small result file -> drop. Resumable (finished chunks are skipped).
Disk floor checked before each chunk: 7GB free 17:00-21:00 HKT, 2GB otherwise; it waits if below.
usage: CHECKLIST_DATA_DIR=... OUT_DIR=... python3 step_a.py [--workers 5] [--chunk 400] [--tickers A,B]"""
import os, sys, time, json, shutil, argparse, warnings, datetime as dt; warnings.filterwarnings('ignore')
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

def w_base(tk):
    d = G['B'][tk]; t = TR.ticker_trades(tk, d, G['C']['sessions'], 'discover')
    F = E.filter_cols(tk, d, G['C']).set_index('date'); t = t.join(F[['passes_filter', 'mcap_D1']], on='date'); return t

def w_answers(tk):
    d = G['B'][tk]; idx = G['keep'].get(tk)
    if idx is None: return tk, None, {}
    A, err = E.run_ticker(tk, d, G['C'], G['plan']); A = A.set_index('date').reindex(idx)
    M = np.full((len(idx), len(G['cols'])), -1, np.int8)
    for j, c in enumerate(G['cols']):
        if c in A.columns: M[:, j] = A[c].fillna(-1).to_numpy(np.int8)
    return tk, M, err

def w_score(j):
    rows = TR.trade_rows(G['base'], G['M'][:, j], G['cols'][j]); return TR.score_question(rows, G['L'])

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=5); ap.add_argument('--chunk', type=int, default=400)
    ap.add_argument('--tickers'); a = ap.parse_args()
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
        with Pool(a.workers) as p: base = pd.concat(p.map(w_base, list(G['B']), chunksize=20))
        etf = pd.read_parquet(E.D('/workspace/pricehist/etf_2015.parquet')); spy = etf[(etf.ticker == 'SPY') & (etf.date <= WEND)].sort_values('date')
        base = TR.add_bench(base, spy.reset_index(drop=True), C['sessions'], 'discover'); base.to_parquet(bp, index=False)
    k = base[base.ready & base.passes_filter & base.bench.notna()].sort_values(['ticker', 'date']).reset_index(drop=True)
    log(f"base: {len(base)} cases, not_ready {int((~base.ready).sum())}, filtered+ready trades {len(k)}, tickers {k.ticker.nunique()}")
    G['base'] = k; G['keep'] = {t: pd.DatetimeIndex(g.date) for t, g in k.groupby('ticker', sort=False)}
    json.dump(dict(cases=len(base), not_ready=int((~base.ready).sum()), fail_filter=int((~base.passes_filter).sum()), trades=len(k),
                   bench_mean=float(k.drop_duplicates('date').bench.mean())), open(f'{OUT}/base_summary.json', 'w'), indent=1)
    items = sorted(((key, kn) for key, tfs in plan.items() for kn in tfs), key=lambda x: (x[1][0], x[0], x[1][1]))
    chunks = [items[i:i + a.chunk] for i in range(0, len(items), a.chunk)]; log(f'{len(items)} questions in {len(chunks)} chunks')
    for ci, ch in enumerate(chunks):
        fo = f'{OUT}/chunks/scores_{ci:03d}.parquet'
        if os.path.exists(fo): continue
        while True:
            ok, free, need = disk_ok(OUT)
            if ok: break
            log(f'disk {free:.1f}GB < floor {need}GB, waiting'); time.sleep(300)
        sub = {}
        for key, kn in ch: sub.setdefault(key, []).append(kn)
        G['plan'] = sub
        G['cols'] = [(f"H|{key[1]}|{key[2]}" if key[0] == 'H' else f"{key[1]}|{key[2]}") + f"|{kn[0]}d|{kn[1]}" for key, kn in ch]
        tc = time.time()
        with Pool(a.workers) as p: res = p.map(w_answers, list(G['keep']), chunksize=10)
        M = np.full((len(k), len(G['cols'])), -1, np.int8); off = 0; errs = {}
        for tk, m, e in res:
            if m is not None: M[off:off + len(m)] = m; off += len(m)
            errs.update({f'{tk}:{x}': v for x, v in e.items()})
        assert off == len(k); res = None; G['M'] = M
        with Pool(a.workers) as p: S = sum(p.map(w_score, range(len(G['cols']))), [])
        G['M'] = M = None
        pd.DataFrame(S).to_parquet(fo + '.tmp', index=False); os.replace(fo + '.tmp', fo)
        json.dump(errs, open(f'{OUT}/chunks/errors_{ci:03d}.json', 'w'))
        done = ci + 1; el = time.time() - t0
        log(f'chunk {ci+1}/{len(chunks)}: {len(G["cols"])} q, {len(errs)} errors, {time.time()-tc:.0f}s; elapsed {el/3600:.2f}h')
        json.dump(dict(chunk=ci + 1, of=len(chunks), elapsed_h=round(el / 3600, 2), updated=dt.datetime.now().isoformat()), open(f'{OUT}/PROGRESS.json', 'w'))
    R = pd.concat([pd.read_parquet(f'{OUT}/chunks/scores_{i:03d}.parquet') for i in range(len(chunks))])
    R.to_parquet(f'{OUT}/STEP_A_SCORES_discover_2020_22.parquet', index=False)
    log('DONE', len(R), 'question+answer rows;', {f'passes_{int(f*100)}': int(R[f'passes_{int(f*100)}'].sum()) for f in TR.FLOORS})
