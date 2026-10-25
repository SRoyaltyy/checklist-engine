"""Exit-grid driver for GitHub runners (METHODOLOGY 0b 13:30). Heavy lifting happens here, NOT on anyone's laptop.

Phases (each resumable; everything checkpointed to the release):
  prep    build per-trade first-hit arrays from bars + trade_base_rows.parquet, sharded to grid_pre/shard_XXX.npz,
          plus the per-date benchmark tables (bench_pre.npz: equal-weight same-day benchmark + SPY, per (m,s,h,date)).
  chunk   aggregate one answers chunk (answers_NNN.npz) across the whole 26,100-rule grid via matmul -> grid_NNN.parquet
          (long form: question_id, answer, tp, hold, stop, n, win_cnt, win_sum, loss_sum, sum_ret, sum_bench, sum_spy).
Usage:
  CHECKLIST_DATA_DIR=... python3 step_grid.py prep  --base chunks/trade_base_rows.parquet --out grid_pre
  python3 step_grid.py bench --base ... --pre grid_pre --out grid_pre/bench_pre.npz
  python3 step_grid.py chunk --i 12 --answers answers_012.npz --pre grid_pre --out grid_chunks
Discover window only: engine.load_bars cuts bars at 2022-12-31; 2023-24 / 2025-26 are never opened.
"""
import os, sys, time, argparse, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from scoring import exit_grid as X

WEND = pd.Timestamp('2022-12-31')
N_SHARD = 8


def log(*a):
    print(time.strftime('%m-%d %H:%M:%S'), *a, flush=True)


def load_pre(pre):
    """Reassemble per-trade arrays from shards. Returns dict of concatenated arrays plus dates/didx."""
    d = {}
    for k in ('tp_day', 'tp_ret', 'sl_day', 'sl_ret', 'clos', 'didx'):
        parts = [np.load(os.path.join(pre, f'shard_{s:03d}.npz'))[k] for s in range(N_SHARD)]
        d[k] = np.concatenate(parts, 1) if parts[0].ndim == 2 else np.concatenate(parts)
    meta = json.load(open(os.path.join(pre, 'meta.json')))
    d['dates'] = np.array(meta['dates'], dtype='datetime64[ns]')
    return d


def prep(args):
    base = pd.read_parquet(args.base)
    log('base trades:', len(base), base.date.min(), base.date.max())
    tks = base.ticker.unique().tolist()
    bars = E.load_bars(tks)
    log('bars loaded:', len(bars), 'rows,', bars.ticker.nunique(), 'tickers')
    base_dates_np = base.date.to_numpy()
    dates = np.sort(base_dates_np)
    # check_tick the fast way: dates must be exactly the sorted unique set
    dates = np.unique(base_dates_np)
    didx_all = np.searchsorted(dates, base_dates_np).astype(np.int32)
    assert (dates[didx_all] == base_dates_np).all()
    n = len(base)
    # group base rows by ticker once (O(n) total, not per-ticker scans)
    bt = base.ticker.to_numpy()
    order = np.argsort(bt, kind='stable')
    by_tk = {}
    for tk in np.unique(bt):
        r = order[np.searchsorted(bt[order], tk, side='left'):np.searchsorted(bt[order], tk, side='right')]
        by_tk[tk] = r

    tp_day = np.full((X.NTP, n), -1, np.int16); tp_ret = np.full((X.NTP, n), np.nan, np.float32)
    sl_day = np.full((X.NSL, n), -1, np.int16); sl_ret = np.full((X.NSL, n), np.nan, np.float32)
    clos = np.zeros((X.MAXH, n), np.float32)
    didx = didx_all

    for tk, g in bars.groupby('ticker', sort=False):
        cols = by_tk.get(tk)
        if cols is None:
            continue
        b = g.reset_index(drop=True)
        bidx = pd.DatetimeIndex(b.date.values)
        ix = bidx.get_indexer(pd.DatetimeIndex(base_dates_np[cols]))    # bar row for each base date
        if (ix < 0).any():
            raise SystemExit(f'{tk}: base date missing from bars')
        if (ix.max() + X.MAXH > len(b)):
            raise SystemExit(f'{tk}: base row without {X.MAXH} forward bars (NOT_READY breach)')
        o, h, l, c = (b[x].to_numpy(np.float64) for x in ('open', 'high', 'low', 'close'))
        td, tr = X.first_hits(o, h, l, c, X.TP_PCTS, '+')
        sd, sr = X.first_hits(o, h, l, c, X.SL_PCTS, '-')
        cr = X.close_rets(o, c)
        tp_day[:, cols] = td[:, ix]; tp_ret[:, cols] = tr[:, ix]
        sl_day[:, cols] = sd[:, ix]; sl_ret[:, cols] = sr[:, ix]
        clos[:, cols] = cr[:, ix]

    os.makedirs(args.out, exist_ok=True)
    edges = np.linspace(0, n, N_SHARD + 1).astype(int)
    for s in range(N_SHARD):
        a, bnd = edges[s], edges[s + 1]
        np.savez_compressed(os.path.join(args.out, f'shard_{s:03d}.npz'),
                            tp_day=tp_day[:, a:bnd], tp_ret=tp_ret[:, a:bnd],
                            sl_day=sl_day[:, a:bnd], sl_ret=sl_ret[:, a:bnd],
                            clos=clos[:, a:bnd], didx=didx[a:bnd])
        log(f'shard {s + 1}/{N_SHARD} written ({bnd - a} trades)')
    json.dump(dict(dates=[str(pd.Timestamp(d).date()) for d in dates], n=n, ntp=X.NTP, nsl=X.NSL, maxh=X.MAXH),
              open(os.path.join(args.out, 'meta.json'), 'w'))
    log('prep done:', n, 'trades,', len(dates), 'dates')


def bench(args):
    """Per-rule same-day benchmark: equal-weight mean net ret of base trades per date, and SPY under the same rule."""
    d = load_pre(args.pre)
    n, dates = d['tp_day'].shape[1], d['dates']
    nd = len(dates)
    cnt = np.bincount(d['didx'], minlength=nd).astype(np.float64)
    assert (cnt > 0).all() and cnt.sum() == n
    spy = _spy_trades(args)
    # bench[mi, si(-1=none stored at index 0?), h, date] -> layout (NTP, 1+NSL, NH, nd)
    bench = np.zeros((X.NTP, 1 + X.NSL, X.NH, nd), np.float32)
    spy_t = np.zeros((X.NTP, 1 + X.NSL, X.NH, nd), np.float32)
    for mi in range(X.NTP):
        for si in range(-1, X.NSL):                        # -1 = no stop
            rm = X.rule_ret_mat(d['tp_day'][mi], d['tp_ret'][mi],
                                None if si < 0 else d['sl_day'][si], None if si < 0 else d['sl_ret'][si],
                                d['clos'], sl_none=si < 0)          # (NH, n)
            bench[mi, si + 1] = (_date_sums(rm, d['didx'], nd) / cnt[None, :]).astype(np.float32)
            srm = X.rule_ret_mat(spy['tp_day'][mi], spy['tp_ret'][mi],
                                 None if si < 0 else spy['sl_day'][si], None if si < 0 else spy['sl_ret'][si],
                                 spy['clos'], sl_none=si < 0)
            spy_t[mi, si + 1] = (_date_sums(srm, spy['didx'], nd) / np.maximum(spy_cnt(spy, nd), 1)[None, :]).astype(np.float32)
        log(f'bench m={X.TP_PCTS[mi]:.0%} done')
    np.savez_compressed(args.out, bench=bench, spy=spy_t, cnt=cnt, dates=dates)
    log('bench saved:', args.out, bench.shape)


def _date_sums(rm, didx, nd):
    return np.stack([np.bincount(didx, weights=rm[h], minlength=nd) for h in range(rm.shape[0])])


def _spy_trades(args):
    """SPY first-hit arrays, one candidate entry per SPY session that is also a base trade date (like trades.py)."""
    etf = pd.read_parquet(E.D('/workspace/pricehist/etf_2015.parquet'))
    sp = etf[(etf.ticker == 'SPY') & (etf.date <= WEND)].sort_values('date').reset_index(drop=True)
    dmap = {d: i for i, d in enumerate(np.sort(pd.read_parquet(args.base).date.unique()))}
    keep = np.array([d in dmap for d in sp.date.to_numpy()])
    sp = sp[keep].reset_index(drop=True)                       # entries only on dates the benchmark is defined
    o, h, l, c = (sp[x].to_numpy(np.float64) for x in ('open', 'high', 'low', 'close'))
    n = len(o) - X.MAXH + 1
    if n <= 0:
        raise SystemExit('SPY history too short for MAXH forward window')
    td, tr = X.first_hits(o, h, l, c, X.TP_PCTS, '+')
    sd, sr = X.first_hits(o, h, l, c, X.SL_PCTS, '-')
    cr = X.close_rets(o, c)
    didx = np.array([dmap[d] for d in sp.date.to_numpy()[:n]], np.int32)
    return dict(tp_day=td, tp_ret=tr, sl_day=sd, sl_ret=sr, clos=cr, didx=didx)


def spy_cnt(spy, nd):
    return np.bincount(spy['didx'], minlength=nd).astype(np.float64)


def chunk(args):
    """Aggregate one answers chunk across the whole grid. Output long-form parquet per chunk.
    --year Y restricts to trades of that calendar year (for the 2020-21 fit / 2022 check splits);
    writes gridy_NNN_YYYY.parquet instead. Per-rule per-date benchmark is year-agnostic (same-day)."""
    d = load_pre(args.pre)
    B = np.load(args.bench)
    bench_all, spy_all = B['bench'], B['spy']                 # (NTP, 1+NSL, NH, nd)
    n = d['tp_day'].shape[1]
    A = np.load(args.answers)
    M, cols = A['M'], A['cols']
    assert M.shape[0] == n, (M.shape, n)
    ysel = None
    if args.year:
        meta = json.load(open(os.path.join(args.pre, 'meta.json')))
        ty = pd.DatetimeIndex(pd.to_datetime(meta['dates'])).year.to_numpy()[d['didx']]
        ysel = ty == args.year
        log(f'year {args.year}: {int(ysel.sum())} of {n} trades')

    didx = d['didx']
    out_rows = {k: [] for k in ('qid', 'ans', 'tp', 'hold', 'stop')}
    stats = {k: [] for k in ('n', 'win_cnt', 'win_sum', 'sum_ret', 'sum_bench', 'sum_spy', 'sum_sq')}
    QB = 100                                                # questions per matmul batch (float32 (QB*2, n) ~ 2.2GB)
    for mi in range(X.NTP):
        for si in range(-1, X.NSL):
            rm = X.rule_ret_mat(d['tp_day'][mi], d['tp_ret'][mi],
                                None if si < 0 else d['sl_day'][si], None if si < 0 else d['sl_ret'][si],
                                d['clos'], sl_none=si < 0)
            bm = bench_all[mi, si + 1][:, didx]             # (NH, n) benchmark for this rule per trade
            sm = spy_all[mi, si + 1][:, didx]
            if ysel is not None:
                rm, bm, sm = rm[:, ysel], bm[:, ysel], sm[:, ysel]
            for q0 in range(0, len(cols), QB):
                qs = slice(q0, min(q0 + QB, len(cols)))
                Mq = M[:, qs]
                if ysel is not None:
                    Mq = Mq[ysel]
                G0 = np.ascontiguousarray((Mq == 0).T, dtype=np.float32)
                G1 = np.ascontiguousarray((Mq == 1).T, dtype=np.float32)
                for G, ans in ((G0, 0), (G1, 1)):
                    n_ = G.sum(1)
                    if not (n_ > 0).any():
                        continue
                    sum_ret = G @ rm.T
                    win = (rm > 0)
                    win_cnt = G @ win.T
                    win_sum = G @ np.where(win, rm, 0.0).T
                    sum_bench = G @ bm.T
                    sum_spy = G @ sm.T
                    sum_sq = G @ (rm * rm).T
                    k = len(cols[qs])
                    out_rows['qid'].append(np.repeat(cols[qs], X.NH))
                    out_rows['ans'].append(np.tile(np.full(k, ans, np.int8), X.NH))
                    out_rows['tp'].append(np.tile(np.full(k, int(round(X.TP_PCTS[mi] * 100)), np.int8), X.NH))
                    out_rows['hold'].append(np.tile(X.HOLDS, k))
                    out_rows['stop'].append(np.tile(np.full(k, 0 if si < 0 else int(round(X.SL_PCTS[si] * 100)), np.int8), X.NH))
                    stats['n'].append(n_[:, None].repeat(X.NH, 1).ravel())
                    stats['win_cnt'].append(np.asarray(win_cnt).ravel())
                    stats['win_sum'].append(np.asarray(win_sum, np.float64).ravel())
                    stats['sum_ret'].append(np.asarray(sum_ret, np.float64).ravel())
                    stats['sum_bench'].append(np.asarray(sum_bench, np.float64).ravel())
                    stats['sum_spy'].append(np.asarray(sum_spy, np.float64).ravel())
                    stats['sum_sq'].append(np.asarray(sum_sq, np.float64).ravel())
        log(f'chunk {args.i}: m={X.TP_PCTS[mi]:.0%} done')
    df = pd.DataFrame({k: np.concatenate(v) for k, v in out_rows.items()})
    for k, v in stats.items():
        df[k] = np.concatenate(v)
    os.makedirs(args.out, exist_ok=True)
    p = os.path.join(args.out, (f'gridy_{args.i:03d}_{args.year}.parquet' if args.year else f'grid_{args.i:03d}.parquet'))
    df.to_parquet(p, index=False)
    log('wrote', p, len(df), 'rows')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['prep', 'bench', 'chunk'])
    ap.add_argument('--base', default='chunks/trade_base_rows.parquet')
    ap.add_argument('--pre', default='grid_pre')
    ap.add_argument('--bench', default='grid_pre/bench_pre.npz')
    ap.add_argument('--out', default='grid_chunks')
    ap.add_argument('--i', type=int, default=0)
    ap.add_argument('--year', type=int, default=None)
    ap.add_argument('--answers', default=None)
    a = ap.parse_args()
    os.environ.setdefault('CHECKLIST_DATA_DIR', os.environ.get('CHECKLIST_DATA_DIR', 'data-2020-24-v1'))
    if a.phase == 'prep':
        prep(a)
    elif a.phase == 'bench':
        bench(a)
    else:
        assert a.answers, '--answers required for chunk phase'
        chunk(a)
