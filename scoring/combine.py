"""Combining model ("world state" -> P(win) / E[profit] for every exit cell).

Implements docs/COMBINING_PREREG.md:
  * features: every non-junk question's answer (one-hot per fixed-set level; blank = all zero)
    + the exit-policy parameters (m, h, stop) as numeric features. No free text, no peeking.
  * junk rule (§7b): >95% blank, or a level on >95% / <0.5% of days is dropped;
    a question with no surviving level is junk and excluded.
  * primary logistic p(win) (trade profit after fees > 0), secondary ridge E[profit].
  * time discipline: fit on --fit-years only; --check-year evaluated once (Brier, deciles,
    EV vs same-day benchmark). 2023-24 is never opened here.
  * the probability is a surface: p(s, D, m, h, s) for every one of the 26,100 cells.

Memory strategy (runs on a 16GB GitHub runner): trades are stratified-subsampled once
(--max-trades); each sampled trade is paired with --cells-per-trade (m,s) pairs (all 30
holds come free per pair via scoring/exit_grid.rule_ret_mat), giving a row set of
n_trades x cells_per_trade x 30 (trade, cell) rows. Gradients are computed with the block
trick: rows contribute through per-trade and per-cell sufficient sums, so the one-hot
design matrix is never materialised. Question features are handled as (question x 256)
lookup tables indexed by the int8 answer code.

Usage:
  python3 scoring/combine.py fit --answers answers_dir --base chunks/trade_base_rows.parquet \
      --pre grid_pre --bench grid_pre/bench_pre.npz --out model [--max-trades 400000] \
      [--cells-per-trade 12] [--iters 80] [--fit-years 2020 2021] [--check-year 2022]
  python3 scoring/combine.py predict --model model --answers answers_dir --base ... --pre ... \
      --bench ... --out preds_dir          # full strategy map + continuity-cell p for the state-change study
"""
import os, sys, json, time, argparse
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring import exit_grid as X

N_RULE = 4                                        # [m/30, h/30, s/30, s_none]
CONTINUITY = (20, 15, 0)                          # (tp%, hold, stop%) legacy exit rule v1 (stop 0 = none)
BLANK = -1


def log(*a):
    print(time.strftime('%m-%d %H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- data loading

def load_answers(path):
    """answers dir (answers_*.npz) or single npz -> (M int8 (n, q), cols list)."""
    if os.path.isdir(path):
        files = sorted(f for f in os.listdir(path) if f.startswith('answers_') and f.endswith('.npz'))
        Ms, cols = [], []
        for f in files:
            A = np.load(os.path.join(path, f))
            Ms.append(A['M']); cols.extend([str(c) for c in A['cols']])
        M = np.concatenate(Ms, 1)
    else:
        A = np.load(path); M = A['M']; cols = [str(c) for c in A['cols']]
    return np.ascontiguousarray(M), cols


def load_pre(pre, keep):
    """grid_pre shards -> per-trade first-hit arrays restricted to row indices `keep`."""
    d = {}
    for k in ('tp_day', 'tp_ret', 'sl_day', 'sl_ret', 'clos', 'didx'):
        parts = [np.load(os.path.join(pre, f'shard_{s:03d}.npz'))[k] for s in range(8)]
        arr = np.concatenate(parts, 1) if parts[0].ndim == 2 else np.concatenate(parts)
        d[k] = arr[:, keep] if arr.ndim == 2 else arr[keep]
    meta = json.load(open(os.path.join(pre, 'meta.json')))
    d['dates'] = np.array(meta['dates'], dtype='datetime64[ns]')
    return d


def cell_index():
    """(m%, h, s%) -> cell id; s=0 means no stop. Returns (cells (n_cells,3), rule_feat (n_cells, N_RULE))."""
    cells = []
    for mi in range(X.NTP):
        for si in (-1,) + tuple(range(X.NSL)):
            for h in X.HOLDS:
                cells.append((int(round(X.TP_PCTS[mi] * 100)), int(h),
                              0 if si < 0 else int(round(X.SL_PCTS[si] * 100))))
    cells = np.array(cells, np.int16)                        # (26100, 3)
    s_none = (cells[:, 2] == 0).astype(np.float32)
    rf = np.stack([cells[:, 0] / 30.0, cells[:, 1] / 30.0, cells[:, 2] / 30.0, s_none], 1)
    return cells, rf.astype(np.float32)


# ------------------------------------------------------- features (question LUTs)

class Featurizer:
    """Per-question (q x 256) beta LUTs; one-hot levels with the §7b junk rule."""

    def __init__(self, cols):
        self.cols = cols
        self.levels = [None] * len(cols)                     # list of np.array of kept level codes
        self.junk = np.ones(len(cols), bool)

    def fit(self, M):
        n = M.shape[0]
        for j in range(M.shape[1]):
            v = M[:, j]
            vals, cnt = np.unique(v, return_counts=True)
            freq = cnt / n
            keep = [val for val, f in zip(vals, freq)
                    if val != BLANK and 0.005 <= f <= 0.95]
            blank_f = freq[vals == BLANK]
            if (len(blank_f) and blank_f[0] > 0.95) or not keep:
                continue                                     # junk
            self.levels[j] = np.array(keep, np.int16)
            self.junk[j] = False
        log('featurizer:', int((~self.junk).sum()), 'of', len(self.cols), 'questions kept')

    @property
    def n_feat(self):
        return int(sum(len(l) for l in self.levels if l is not None))

    def luts(self, beta):
        """flat beta (n_feat,) -> (q, 256) LUT per question (blank -> 0)."""
        lut = np.zeros((len(self.cols), 256), np.float32)
        off = 0
        for j, lev in enumerate(self.levels):
            if lev is None: continue
            lut[j, lev.astype(np.int64)] = beta[off:off + len(lev)]
            off += len(lev)
        assert off == len(beta)
        return lut

    def grad(self, M, s):
        """per-feature gradient: sum_t s_t * [M[t,j] == level]. Block bincount trick."""
        g = np.zeros(self.n_feat, np.float64)
        off = 0
        B = 96
        for j0 in range(0, M.shape[1], B):
            j1 = min(j0 + B, M.shape[1])
            blk = M[:, j0:j1].astype(np.int32)
            key = blk + 256 * np.arange(j0, j1, dtype=np.int32)[None, :]
            sums = np.bincount(key.ravel(), weights=np.repeat(s, j1 - j0), minlength=256 * j1)
            for j in range(j0, j1):
                lev = self.levels[j]
                if lev is None: continue
                g[off:off + len(lev)] = sums[256 * j + lev.astype(np.int64)]
                off += len(lev)
        return g

    def predict_trade(self, M, lut):
        """(n,) trade score = sum_j LUT[j, M[:,j]]."""
        out = np.zeros(M.shape[0], np.float64)
        B = 96
        for j0 in range(0, M.shape[1], B):
            j1 = min(j0 + B, M.shape[1])
            blk = M[:, j0:j1].astype(np.int64)
            out += np.take_along_axis(lut[j0:j1][None, :, :], blk[:, :, None], 2)[:, :, 0].sum(1)
        return out


# ------------------------------------------------------------- outcomes for rows

def build_rows(pre_d, n_trades, cells_per_trade, seed=7):
    """Sample (m,s) pairs per trade; resolve all 30 holds per pair.
    Returns dict of (rows,) arrays: tidx (trade), cid (cell), ret (net), bench."""
    rng = np.random.default_rng(seed)
    n_ms = X.NTP * (1 + X.NSL)                             # 29 x 30 = 870 (m,s) pairs
    pair_of_trade = rng.integers(0, n_ms, (n_trades, cells_per_trade))
    tidx, cid, ret, bench = [], [], [], []
    for p in range(n_ms):
        mi = p // (1 + X.NSL); si = p % (1 + X.NSL) - 1    # si=-1 -> no stop
        tt = np.where(pair_of_trade == p)[0]
        if len(tt) == 0: continue
        rm = X.rule_ret_mat(pre_d['tp_day'][mi, tt], pre_d['tp_ret'][mi, tt],
                            None if si < 0 else pre_d['sl_day'][si, tt],
                            None if si < 0 else pre_d['sl_ret'][si, tt],
                            pre_d['clos'][:, tt], sl_none=si < 0)          # (NH, n_tt)
        base_cid = p * X.NH
        for h in range(X.NH):
            tidx.append(tt); cid.append(np.full(len(tt), base_cid + h, np.int32)); ret.append(rm[h])
    tidx = np.concatenate(tidx); cid = np.concatenate(cid); ret = np.concatenate(ret).astype(np.float64)
    return tidx, cid, ret


# ------------------------------------------------------------------ model fitting

def fit_model(F, M, tidx, cid, ret, cells, rf, iters=80, l2=1e-4, target='logistic'):
    """One joint model: pred = alpha + trade_score + rule_feat.gamma.
    Full-batch Adam via sufficient sums (block gradients). target: 'logistic' (y = ret>0)
    or 'ridge' (y = ret, standardised). Returns (lut (q,256), gamma, alpha, history)."""
    n_rows = len(tidx)
    if target == 'logistic':
        y = (ret > 0).astype(np.float64)
    else:
        y = ret / 0.05                                       # standardise profit
    beta = np.zeros(F.n_feat, np.float64)
    gamma = np.zeros(N_RULE, np.float64)
    alpha = np.array([np.log(max(y.mean(), 1e-6) / max(1 - y.mean(), 1e-6))]) if target == 'logistic' else np.array([y.mean()])
    m_b = np.zeros_like(beta); v_b = np.zeros_like(beta)
    m_g = np.zeros_like(gamma); v_g = np.zeros_like(gamma)
    m_a = np.zeros(1); v_a = np.zeros(1)
    b1, b2, eps = 0.9, 0.999, 1e-8
    hist = []
    lut = F.luts(beta.astype(np.float32))
    for it in range(1, iters + 1):
        ts = F.predict_trade(M, lut)                         # (n_trades,)
        pred = alpha[0] + ts[tidx] + rf[cid] @ gamma
        if target == 'logistic':
            p = 1.0 / (1.0 + np.exp(-pred))
            delta = p - y
            loss = -(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1))).mean()
        else:
            delta = 2 * (pred - y) / len(y)
            loss = float(((pred - y) ** 2).mean())
        s_trade = np.bincount(tidx, weights=delta, minlength=M.shape[0])
        s_cell = np.bincount(cid, weights=delta, minlength=len(cells))
        g_beta = F.grad(M, s_trade)
        g_gamma = rf.T @ s_cell
        g_alpha = np.array([delta.sum()])
        for prm, g, m, v in ((beta, g_beta, m_b, v_b), (gamma, g_gamma, m_g, v_g), (alpha, g_alpha, m_a, v_a)):
            np.multiply(m, b1, out=m); np.add(m, (1 - b1) * g, out=m)
            np.multiply(v, b2, out=v); np.add(v, (1 - b2) * g * g, out=v)
            mh = m / (1 - b1 ** it); vh = v / (1 - b2 ** it)
            prm -= 0.01 * mh / (np.sqrt(vh) + eps) + 0.01 * l2 * prm
        lut = F.luts(beta.astype(np.float32))
        hist.append(loss)
        if it % 10 == 0 or it == 1:
            log(f'  {target} iter {it}/{iters} loss {loss:.5f}')
    return F.luts(beta.astype(np.float32)), gamma, float(alpha[0]), hist


# ------------------------------------------------------------------- evaluation

def evaluate(F, lut_l, gamma_l, lut_r, gamma_r, alpha_l, alpha_r, M, pre_d, cells, rf, bench_pre, name):
    """Strategy map on the given trades: argmax over cells of EV; report p at argmax,
    Brier, calibration deciles, mean EV vs same-day benchmark. Returns summary dict."""
    ts_l = F.predict_trade(M, lut_l); ts_r = F.predict_trade(M, lut_r)
    n = M.shape[0]
    best_ev = np.full(n, -np.inf); best_c = np.zeros(n, np.int32)
    best_p = np.zeros(n); bench_best = np.zeros(n); realised = np.zeros(n)
    B = 4000
    for c0 in range(0, len(cells), B):
        sl = slice(c0, min(c0 + B, len(cells)))
        ev = ts_r[:, None] + alpha_r + rf[sl] @ gamma_r     # (n, b) EV in std units -> back later
        pv = ts_l[:, None] + alpha_l + rf[sl] @ gamma_l
        loc = np.argmax(ev, 1)
        evb = np.take_along_axis(ev, loc[:, None], 1)[:, 0]
        upd = evb > best_ev
        best_ev[upd] = evb[upd]; best_c[upd] = c0 + loc[upd]
        best_p[upd] = np.take_along_axis(pv, loc[:, None], 1)[:, 0][upd]
    # realised outcome + benchmark at the chosen cell
    realised = np.zeros(n); bench_row = np.zeros(n)
    bench_all = bench_pre['bench']
    didx = pre_d['didx']
    order = np.argsort(best_c, kind='stable')
    for c in np.unique(best_c):
        rows = order[np.searchsorted(best_c[order], c, 'left'):np.searchsorted(best_c[order], c, 'right')]
        m, h, s = (int(v) for v in cells[c])
        mi = m - 2                                       # TP_PCTS index (margins 2..30)
        si = -1 if s == 0 else s - 2                     # SL_PCTS index (stops 2..30; 0 = none)
        tt = rows
        rm = X.rule_ret_mat(pre_d['tp_day'][mi, tt], pre_d['tp_ret'][mi, tt],
                            None if si < 0 else pre_d['sl_day'][si, tt],
                            None if si < 0 else pre_d['sl_ret'][si, tt],
                            pre_d['clos'][:, tt], sl_none=si < 0)
        realised[tt] = rm[h - 1]
        bench_row[tt] = bench_all[mi, si + 1, h - 1, didx[tt]]
    p = 1 / (1 + np.exp(-best_p))
    y = realised > 0
    brier = float(((p - y) ** 2).mean())
    # calibration deciles
    q = np.quantile(p, np.linspace(0, 1, 11)); q[0], q[-1] = -np.inf, np.inf
    cal = []
    for b in range(10):
        msk = (p >= q[b]) & (p < q[b + 1])
        if msk.sum() > 0:
            cal.append(dict(bin=b, n=int(msk.sum()), pred=float(p[msk].mean()), realised=float(y[msk].mean()),
                            ev=float(realised[msk].mean() * 0.05), bench=float(bench_row[msk].mean())))
    ev = realised * 0.05                                     # back to raw return units
    summary = dict(eval=name, n=n, brier=brier,
                   mean_ev_net=float(ev.mean()), mean_bench=float(bench_row.mean()),
                   beat_bench=bool(ev.mean() > bench_row.mean()),
                   win_rate_chosen=float(y.mean()), p_mean=float(p.mean()),
                   calibration=cal)
    log(json.dumps({k: v for k, v in summary.items() if k != 'calibration'}))
    return summary, dict(ticker_year=None, cell=best_c, p=p, ev=ev, realised=realised, bench=bench_row)


# ------------------------------------------------------------------------ main

def cmd_fit(a):
    base = pd.read_parquet(a.base)
    log('base trades:', len(base), base.date.min(), base.date.max())
    M, cols = load_answers(a.answers)
    assert M.shape[0] == len(base)
    year = pd.DatetimeIndex(base.date).year.to_numpy()
    fit_mask = np.isin(year, a.fit_years)
    check_mask = (year == a.check_year) if a.check_year else np.zeros(len(base), bool)
    if a.max_trades and fit_mask.sum() > a.max_trades:       # stratified subsample of fit years
        idx = np.where(fit_mask)[0]
        keep_n = a.max_trades
        step = len(idx) / keep_n
        sel = idx[(np.arange(keep_n) * step).astype(int)]
        fit_mask = np.zeros(len(base), bool); fit_mask[sel] = True
        log(f'fit subsample: {int(fit_mask.sum())} trades')
    fit_idx = np.where(fit_mask)[0]
    check_idx = np.where(check_mask)[0]
    pre_fit = load_pre(a.pre, fit_idx)
    bench_pre = np.load(a.bench)
    cells, rf = cell_index()
    tidx, cid, ret = build_rows(pre_fit, len(fit_idx), a.cells_per_trade)
    log('fit rows:', len(tidx), f'({len(fit_idx)} trades x {a.cells_per_trade} pairs x 30 holds)')
    F = Featurizer(cols); F.fit(M[fit_idx])
    os.makedirs(a.out, exist_ok=True)
    lut_l, gamma_l, alpha_l, hist_l = fit_model(F, M[fit_idx], tidx, cid, ret, cells, rf, iters=a.iters, target='logistic')
    lut_r, gamma_r, alpha_r, hist_r = fit_model(F, M[fit_idx], tidx, cid, ret, cells, rf, iters=a.iters, target='ridge')
    json.dump(dict(cols=cols, levels=[None if l is None else l.tolist() for l in F.levels],
                   junk=F.junk.tolist(), gamma_log=gamma_l.tolist(), alpha_log=alpha_l,
                   gamma_ridge=gamma_r.tolist(), alpha_ridge=alpha_r, hist_log=hist_l, hist_ridge=hist_r,
                   cells=cells.tolist(), fit_years=a.fit_years, check_year=a.check_year,
                   max_trades=a.max_trades, cells_per_trade=a.cells_per_trade),
              open(os.path.join(a.out, 'model.json'), 'w'))
    np.savez_compressed(os.path.join(a.out, 'model.npz'), lut_log=lut_l, lut_ridge=lut_r)
    log('model saved to', a.out)
    if a.check_year and len(check_idx):
        pre_chk = load_pre(a.pre, check_idx)
        M_chk = M[check_idx]
        summary, _ = evaluate(F, lut_l, gamma_l, lut_r, gamma_r, alpha_l, alpha_r,
                              M_chk, pre_chk, cells, rf, bench_pre, f'check-{a.check_year}')
        json.dump(summary, open(os.path.join(a.out, f'check_{a.check_year}.json'), 'w'), indent=1)


def cmd_predict(a):
    meta = json.load(open(os.path.join(a.model, 'model.json')))
    base = pd.read_parquet(a.base)
    M, cols = load_answers(a.answers)
    if cols != meta['cols']:
        log('WARNING: answers columns differ from model training columns; aligning is NOT implemented')
    F = Featurizer(meta['cols'])
    F.levels = [None if l is None else np.array(l, np.int16) for l in meta['levels']]
    F.junk = np.array(meta['junk'], bool)
    W = np.load(os.path.join(a.model, 'model.npz'))
    cells = np.array(meta['cells'], np.int16); rf = np.stack(
        [cells[:, 0] / 30.0, cells[:, 1] / 30.0, cells[:, 2] / 30.0, (cells[:, 2] == 0)], 1).astype(np.float32)
    year = pd.DatetimeIndex(base.date).year.to_numpy()
    pre_d = load_pre(a.pre, np.arange(len(base)))
    bench_pre = np.load(a.bench)
    out_all = []
    for y in sorted(np.unique(year)):
        idx = np.where(year == y)[0]
        summary, det = evaluate(F, W['lut_log'], np.array(meta['gamma_log']), W['lut_ridge'],
                                np.array(meta['gamma_ridge']), meta['alpha_log'], meta['alpha_ridge'],
                                M[idx], dict(**{k: pre_d[k][:, idx] if pre_d[k].ndim == 2 else pre_d[k][idx]
                                                for k in ('tp_day', 'tp_ret', 'sl_day', 'sl_ret', 'clos', 'didx')}),
                                cells, rf, bench_pre, f'year-{y}')
        df = pd.DataFrame(dict(ticker=base.ticker.to_numpy()[idx], date=base.date.to_numpy()[idx],
                               tp=cells[det['cell']][:, 0], hold=cells[det['cell']][:, 1],
                               stop=cells[det['cell']][:, 2], p_win=np.round(det['p'], 4),
                               ev_net=np.round(det['ev'], 6), realised_net=np.round(det['realised'], 6),
                               bench_net=np.round(det['bench'], 6)))
        os.makedirs(a.out, exist_ok=True)
        df.to_parquet(os.path.join(a.out, f'strategy_map_{y}.parquet'), index=False)
        out_all.append(summary)
        log('strategy map year', y, len(df), 'rows')
    json.dump(out_all, open(os.path.join(a.out, 'predict_summary.json'), 'w'), indent=1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fit')
    f.add_argument('--answers', required=True); f.add_argument('--base', default='chunks/trade_base_rows.parquet')
    f.add_argument('--pre', default='grid_pre'); f.add_argument('--bench', default='grid_pre/bench_pre.npz')
    f.add_argument('--out', default='model'); f.add_argument('--max-trades', type=int, default=400000)
    f.add_argument('--cells-per-trade', type=int, default=12); f.add_argument('--iters', type=int, default=80)
    f.add_argument('--fit-years', type=int, nargs='+', default=[2020, 2021]); f.add_argument('--check-year', type=int, default=2022)
    p = sub.add_parser('predict')
    p.add_argument('--model', required=True); p.add_argument('--answers', required=True)
    p.add_argument('--base', default='chunks/trade_base_rows.parquet')
    p.add_argument('--pre', default='grid_pre'); p.add_argument('--bench', default='grid_pre/bench_pre.npz')
    p.add_argument('--out', default='preds')
    a = ap.parse_args()
    os.environ.setdefault('CHECKLIST_DATA_DIR', os.environ.get('CHECKLIST_DATA_DIR', 'data-2020-24-v1'))
    if a.cmd == 'fit':
        cmd_fit(a)
    else:
        cmd_predict(a)
