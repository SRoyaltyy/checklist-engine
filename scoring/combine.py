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

Memory strategy (runs on a 16GB GitHub runner): the answers are processed as a STREAM of
per-chunk parts (concatenating all 34 chunks would be ~43GB). Trades are stratified-subsampled
once (--max-trades over the fit years); each sampled trade is paired with --cells-per-trade
(m,s) pairs (all 30 holds resolve per pair via scoring/exit_grid.rule_ret_mat). Gradients use
the block trick: rows contribute through per-trade and per-cell sufficient sums, so the
one-hot design matrix is never materialised. Question betas live in (q x 256) lookup tables
indexed by the int8 answer code.

Usage:
  python3 scoring/combine.py fit --answers answers_dir_or_npz --base chunks/trade_base_rows.parquet \
      --pre grid_pre --bench grid_pre/bench_pre.npz --out model [--max-trades 400000] \
      [--cells-per-trade 12] [--iters 60] [--fit-years 2020 2021] [--check-year 2022]
  python3 scoring/combine.py predict --model model --answers answers_dir_or_npz --base ... --pre ... \
      --bench ... --out preds_dir          # per-year strategy maps + summaries
"""
import os, sys, json, time, argparse
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring import exit_grid as X

N_RULE = 4                                        # [m/30, h/30, s/30, s_none]
CONTINUITY = (20, 15, 0)                          # (tp%, hold, stop%) legacy exit rule v1 (stop 0 = none)
BLANK = -1
N_SHARD = 8


def log(*a):
    print(time.strftime('%m-%d %H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- data loading

def answer_files(path):
    if os.path.isdir(path):
        return [os.path.join(path, f) for f in sorted(os.listdir(path))
                if f.startswith('answers_') and f.endswith('.npz')]
    return [path]


def iter_answers(path, keep=None):
    """Yield (M_part int8 (n, q_part), cols_part list). keep = row indices to restrict to
    (answered against the full trade row order), or None for all rows. Never concatenates."""
    for f in answer_files(path):
        A = np.load(f)
        M = A['M'] if keep is None else A['M'][keep]
        yield np.ascontiguousarray(M), [str(c) for c in A['cols']]


def all_cols(path):
    cols = []
    for f in answer_files(path):
        cols.extend([str(c) for c in np.load(f)['cols']])
    return cols


def load_pre(pre, keep):
    """grid_pre shards -> per-trade first-hit arrays restricted to row indices `keep`."""
    d = {}
    for k in ('tp_day', 'tp_ret', 'sl_day', 'sl_ret', 'clos', 'didx'):
        parts = [np.load(os.path.join(pre, f'shard_{s:03d}.npz'))[k] for s in range(N_SHARD)]
        arr = np.concatenate(parts, 1) if parts[0].ndim == 2 else np.concatenate(parts)
        d[k] = arr[:, keep] if arr.ndim == 2 else arr[keep]
    meta = json.load(open(os.path.join(pre, 'meta.json')))
    d['dates'] = np.array(meta['dates'], dtype='datetime64[ns]')
    return d


def cell_index():
    """(m%, h, s%) per cell; s=0 means no stop. Returns (cells (n_cells,3), rule_feat (n_cells, N_RULE))."""
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
    """Per-question (q x 256) beta LUTs; one-hot levels with the §7b junk rule.
    Works on a list of answer parts (streamed chunks), never a concatenated matrix."""

    def __init__(self, cols):
        self.cols = list(cols)
        self.levels = [None] * len(cols)                     # kept level codes per question
        self.junk = np.ones(len(cols), bool)
        self._counts = [None] * len(cols)                    # value -> count, filled by fit()

    def fit(self, parts):
        n = parts[0][0].shape[0]
        off = 0
        for M, _cols in parts:
            for j in range(M.shape[1]):
                vals, cnt = np.unique(M[:, j], return_counts=True)
                d = dict(zip(vals.tolist(), cnt.tolist()))
                gj = off + j
                if self._counts[gj] is None:
                    self._counts[gj] = d
                else:
                    for v, c in d.items():
                        self._counts[gj][v] = self._counts[gj].get(v, 0) + c
            off += M.shape[1]
        assert off == len(self.cols)
        for j, cnt in enumerate(self._counts):
            if cnt is None:
                continue
            keep = [v for v, c in cnt.items()
                    if v != BLANK and 0.005 * n <= c <= 0.95 * n]
            blank_c = cnt.get(BLANK, 0)
            if blank_c > 0.95 * n or not keep:
                continue                                     # junk
            self.levels[j] = np.array(sorted(keep), np.int16)
            self.junk[j] = False
        log('featurizer:', int((~self.junk).sum()), 'of', len(self.cols), 'questions kept,',
            self.n_feat, 'features')

    @property
    def n_feat(self):
        return int(sum(len(l) for l in self.levels if l is not None))

    def luts(self, beta):
        """flat beta (n_feat,) -> (q, 256) LUT per question (blank -> 0)."""
        lut = np.zeros((len(self.cols), 256), np.float32)
        off = 0
        for j, lev in enumerate(self.levels):
            if lev is None: continue
            lut[j, (lev.astype(np.int64) + 256) % 256] = beta[off:off + len(lev)]
            off += len(lev)
        assert off == len(beta)
        return lut

    def grad(self, parts, s):
        """per-feature gradient: sum_t s_t * [M[t,j] == level]. Block bincount over parts."""
        g = np.zeros(self.n_feat, np.float64)
        off_feat = 0; off_col = 0
        B = 96
        for M, _c in parts:
            for j0 in range(0, M.shape[1], B):
                j1 = min(j0 + B, M.shape[1])
                g0, g1 = off_col + j0, off_col + j1
                blk = M[:, j0:j1].astype(np.int32)
                key = (blk + 1) + 257 * np.arange(g0, g1, dtype=np.int32)[None, :]
                sums = np.bincount(key.ravel(), weights=np.repeat(s, j1 - j0), minlength=257 * g1)
                for gj in range(g0, g1):
                    lev = self.levels[gj]
                    if lev is None: continue
                    g[off_feat:off_feat + len(lev)] = sums[257 * gj + 1 + lev.astype(np.int64)]
                    off_feat += len(lev)
            off_col += M.shape[1]
        assert off_col == len(self.cols) and off_feat == self.n_feat
        return g

    def predict_parts(self, parts, lut, out=None, row_block=200000):
        """trade score sum_j LUT[j, M[:,j]], accumulated over parts and row blocks."""
        n = parts[0][0].shape[0]
        if out is None:
            out = np.zeros(n, np.float64)
        off_col = 0
        B = 96
        for M, _c in parts:
            for j0 in range(0, M.shape[1], B):
                j1 = min(j0 + B, M.shape[1])
                luts_b = lut[off_col + j0: off_col + j1]             # (b, 256)
                for r0 in range(0, n, row_block):
                    r1 = min(r0 + row_block, n)
                    blk = M[r0:r1, j0:j1].astype(np.int64) & 255         # int8 codes wrap into [0,255]
                    out[r0:r1] += np.take_along_axis(
                        luts_b[None, :, :], blk[:, :, None], 2)[:, :, 0].sum(1)
            off_col += M.shape[1]
        return out


# ------------------------------------------------------------- outcomes for rows

def build_rows(pre_d, n_trades, cells_per_trade, seed=7):
    """Sample (m,s) pairs per trade; resolve all 30 holds per pair.
    Returns (tidx, cid, ret): one row per (trade, sampled pair, hold)."""
    rng = np.random.default_rng(seed)
    n_ms = X.NTP * (1 + X.NSL)                             # 29 x 30 = 870 (m,s) pairs
    pair_of_trade = rng.integers(0, n_ms, (n_trades, cells_per_trade))
    tidx_l, cid_l, ret_l = [], [], []
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
            tidx_l.append(tt); cid_l.append(np.full(len(tt), base_cid + h, np.int32)); ret_l.append(rm[h])
    return (np.concatenate(tidx_l), np.concatenate(cid_l),
            np.concatenate(ret_l).astype(np.float32))


# ------------------------------------------------------------------ model fitting

def fit_model(F, parts, tidx, cid, ret, cells, rf, iters=60, l2=1e-4, target='logistic'):
    """One joint model: pred = alpha + trade_score + rule_feat.gamma.
    Full-batch Adam via sufficient sums (bincount scatters + block gradients).
    target: 'logistic' (y = ret>0) or 'ridge' (y = ret standardised)."""
    n_trades = parts[0][0].shape[0]
    if target == 'logistic':
        y = (ret > 0).astype(np.float32)
    else:
        y = (ret / 0.05).astype(np.float32)                  # standardise profit
    y = np.ascontiguousarray(y)
    beta = np.zeros(F.n_feat, np.float64)
    gamma = np.zeros(N_RULE, np.float64)
    alpha = np.array([np.log(max(float(y.mean()), 1e-6) / max(1 - float(y.mean()), 1e-6))]
                     ) if target == 'logistic' else np.array([float(y.mean())])
    m_b = np.zeros_like(beta); v_b = np.zeros_like(beta)
    m_g = np.zeros_like(gamma); v_g = np.zeros_like(gamma)
    m_a = np.zeros(1); v_a = np.zeros(1)
    b1, b2, eps = 0.9, 0.999, 1e-8
    hist = []
    lut = F.luts(beta.astype(np.float32))
    for it in range(1, iters + 1):
        ts = F.predict_parts(parts, lut)                     # (n_trades,)
        pred = alpha[0] + ts[tidx] + rf[cid] @ gamma
        if target == 'logistic':
            p = 1.0 / (1.0 + np.exp(-pred))
            delta = (p - y).astype(np.float64)
            loss = float(-(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1))).mean())
        else:
            delta = (2.0 * (pred - y) / len(y)).astype(np.float64)
            loss = float(((pred - y) ** 2).mean())
        s_trade = np.bincount(tidx, weights=delta, minlength=n_trades)
        s_cell = np.bincount(cid, weights=delta, minlength=len(cells))
        g_beta = F.grad(parts, s_trade)
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
    return lut, gamma, float(alpha[0]), hist


# ------------------------------------------------------------------- evaluation

def surface_summary(ts_l, ts_r, gamma_l, gamma_r, alpha_l, alpha_r, pre_d, cells, rf, bench_pre, name):
    """Strategy map on trades with precomputed trade scores: argmax EV over cells,
    realised outcome + benchmark at the chosen cell, Brier, calibration deciles."""
    n = len(ts_l)
    best_ev = np.full(n, -np.inf); best_c = np.zeros(n, np.int32)
    best_logit = np.zeros(n)
    B = 4000
    for c0 in range(0, len(cells), B):
        sl = slice(c0, min(c0 + B, len(cells)))
        ev = ts_r[:, None] + alpha_r + rf[sl] @ gamma_r       # (n, b) EV in std units
        lg = ts_l[:, None] + alpha_l + rf[sl] @ gamma_l
        loc = np.argmax(ev, 1)
        evb = np.take_along_axis(ev, loc[:, None], 1)[:, 0]
        upd = evb > best_ev
        best_ev[upd] = evb[upd]; best_c[upd] = c0 + loc[upd]
        best_logit[upd] = np.take_along_axis(lg, loc[:, None], 1)[:, 0][upd]
    # realised outcome + benchmark at the chosen cell
    realised = np.zeros(n); bench_row = np.zeros(n)
    bench_all = bench_pre['bench']
    didx = pre_d['didx']
    order = np.argsort(best_c, kind='stable')
    for c in np.unique(best_c):
        rows = order[np.searchsorted(best_c[order], c, 'left'):np.searchsorted(best_c[order], c, 'right')]
        m, h, s = (int(v) for v in cells[c])
        mi = m - 2                                           # TP_PCTS index (margins 2..30)
        si = -1 if s == 0 else s - 2                         # SL_PCTS index (stops 2..30; 0 = none)
        rm = X.rule_ret_mat(pre_d['tp_day'][mi, rows], pre_d['tp_ret'][mi, rows],
                            None if si < 0 else pre_d['sl_day'][si, rows],
                            None if si < 0 else pre_d['sl_ret'][si, rows],
                            pre_d['clos'][:, rows], sl_none=si < 0)
        realised[rows] = rm[h - 1]
        bench_row[rows] = bench_all[mi, si + 1, h - 1, didx[rows]]
    p = 1 / (1 + np.exp(-best_logit))
    y = realised > 0
    brier = float(((p - y) ** 2).mean())
    q = np.quantile(p, np.linspace(0, 1, 11)); q[0], q[-1] = -np.inf, np.inf
    cal = []
    for b in range(10):
        msk = (p >= q[b]) & (p < q[b + 1])
        if msk.sum() > 0:
            cal.append(dict(bin=b, n=int(msk.sum()), pred=float(p[msk].mean()), realised=float(y[msk].mean()),
                            ev=float(realised[msk].mean() * 0.05), bench=float(bench_row[msk].mean())))
    ev = realised * 0.05                                     # back to raw return units
    summary = dict(eval=name, n=int(n), brier=brier,
                   mean_ev_net=float(ev.mean()), mean_bench=float(bench_row.mean()),
                   beat_bench=bool(ev.mean() > bench_row.mean()),
                   win_rate_chosen=float(y.mean()), p_mean=float(p.mean()),
                   calibration=cal)
    log(json.dumps({k: v for k, v in summary.items() if k != 'calibration'}))
    return summary, dict(cell=best_c, p=p, ev=ev, realised=realised, bench=bench_row)


# ------------------------------------------------------------------------ main

def cmd_fit(a):
    base = pd.read_parquet(a.base)
    log('base trades:', len(base), base.date.min(), base.date.max())
    cols = all_cols(a.answers)
    year = pd.DatetimeIndex(base.date).year.to_numpy()
    fit_mask = np.isin(year, a.fit_years)
    check_mask = (year == a.check_year) if a.check_year else np.zeros(len(base), bool)
    if a.max_trades and fit_mask.sum() > a.max_trades:       # stratified subsample of fit years
        idx = np.where(fit_mask)[0]
        step = len(idx) / a.max_trades
        sel = idx[(np.arange(a.max_trades) * step).astype(int)]
        fit_mask = np.zeros(len(base), bool); fit_mask[sel] = True
    fit_idx = np.where(fit_mask)[0]
    check_idx = np.where(check_mask)[0]
    parts_fit = [(M, c) for M, c in iter_answers(a.answers, keep=fit_idx)]
    F = Featurizer(cols); F.fit(parts_fit)
    pre_fit = load_pre(a.pre, fit_idx)
    bench_pre = np.load(a.bench)
    cells, rf = cell_index()
    tidx, cid, ret = build_rows(pre_fit, len(fit_idx), a.cells_per_trade)
    log('fit rows:', len(tidx), f'({len(fit_idx)} trades x {a.cells_per_trade} pairs x 30 holds)')
    os.makedirs(a.out, exist_ok=True)
    targets = ['logistic', 'ridge'] if a.target == 'both' else [a.target]
    models = {}
    for t in targets:
        lut, gamma, alpha, hist = fit_model(F, parts_fit, tidx, cid, ret, cells, rf, iters=a.iters, target=t)
        np.savez_compressed(os.path.join(a.out, f'model_{t}.npz'),
                            lut=lut, gamma=gamma, alpha=alpha, hist=hist)
        models[t] = (lut, gamma, alpha)
    del parts_fit
    json.dump(dict(cols=cols, levels=[None if l is None else l.tolist() for l in F.levels],
                   junk=F.junk.tolist(), targets=targets,
                   cells=cells.tolist(), fit_years=a.fit_years, check_year=a.check_year,
                   max_trades=a.max_trades, cells_per_trade=a.cells_per_trade),
              open(os.path.join(a.out, 'model.json'), 'w'))
    log('model saved to', a.out)
    if a.check_year and len(check_idx) and len(targets) == 2:
        parts_chk = [(M, c) for M, c in iter_answers(a.answers, keep=check_idx)]
        pre_chk = load_pre(a.pre, check_idx)
        lut_l, gamma_l, alpha_l = models['logistic']
        lut_r, gamma_r, alpha_r = models['ridge']
        ts_l = F.predict_parts(parts_chk, lut_l); ts_r = F.predict_parts(parts_chk, lut_r)
        summary, _ = surface_summary(ts_l, ts_r, gamma_l, gamma_r, alpha_l, alpha_r,
                                     pre_chk, cells, rf, bench_pre, f'check-{a.check_year}')
        json.dump(summary, open(os.path.join(a.out, f'check_{a.check_year}.json'), 'w'), indent=1)


def cmd_predict(a):
    meta = json.load(open(os.path.join(a.model, 'model.json')))
    base = pd.read_parquet(a.base)
    if all_cols(a.answers) != meta['cols']:
        log('WARNING: answers columns differ from model training columns; alignment not implemented')
    F = Featurizer(meta['cols'])
    F.levels = [None if l is None else np.array(l, np.int16) for l in meta['levels']]
    F.junk = np.array(meta['junk'], bool)
    WL = np.load(os.path.join(a.model, 'model_logistic.npz'))
    WR = np.load(os.path.join(a.model, 'model_ridge.npz'))
    gamma_l, alpha_l = WL['gamma'], float(WL['alpha'])
    gamma_r, alpha_r = WR['gamma'], float(WR['alpha'])
    cells = np.array(meta['cells'], np.int16)
    rf = np.stack([cells[:, 0] / 30.0, cells[:, 1] / 30.0, cells[:, 2] / 30.0,
                   (cells[:, 2] == 0).astype(np.float32)], 1).astype(np.float32)
    year = pd.DatetimeIndex(base.date).year.to_numpy()
    pre_d = load_pre(a.pre, np.arange(len(base)))
    bench_pre = np.load(a.bench)
    # one streaming pass over the answers: accumulate trade scores for every trade
    ts_l = np.zeros(len(base)); ts_r = np.zeros(len(base))
    for M, _c in iter_answers(a.answers):
        F.predict_parts([(M, _c)], WL['lut'], out=ts_l)
        F.predict_parts([(M, _c)], WR['lut'], out=ts_r)
    os.makedirs(a.out, exist_ok=True)
    summaries = []
    for y in sorted(np.unique(year)):
        idx = np.where(year == y)[0]
        pd_y = dict(**{k: (pre_d[k][:, idx] if pre_d[k].ndim == 2 else pre_d[k][idx])
                       for k in ('tp_day', 'tp_ret', 'sl_day', 'sl_ret', 'clos', 'didx')})
        summary, det = surface_summary(ts_l[idx], ts_r[idx], gamma_l, gamma_r,
                                       alpha_l, alpha_r,
                                       pd_y, cells, rf, bench_pre, f'year-{y}')
        df = pd.DataFrame(dict(ticker=base.ticker.to_numpy()[idx], date=base.date.to_numpy()[idx],
                               tp=cells[det['cell']][:, 0], hold=cells[det['cell']][:, 1],
                               stop=cells[det['cell']][:, 2], p_win=np.round(det['p'], 4),
                               ev_net=np.round(det['ev'], 6), realised_net=np.round(det['realised'], 6),
                               bench_net=np.round(det['bench'], 6)))
        df.to_parquet(os.path.join(a.out, f'strategy_map_{y}.parquet'), index=False)
        summaries.append(summary)
        log('strategy map year', y, len(df), 'rows')
    json.dump(summaries, open(os.path.join(a.out, 'predict_summary.json'), 'w'), indent=1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fit')
    f.add_argument('--answers', required=True); f.add_argument('--base', default='chunks/trade_base_rows.parquet')
    f.add_argument('--pre', default='grid_pre'); f.add_argument('--bench', default='grid_pre/bench_pre.npz')
    f.add_argument('--out', default='model'); f.add_argument('--max-trades', type=int, default=400000)
    f.add_argument('--cells-per-trade', type=int, default=12); f.add_argument('--iters', type=int, default=60)
    f.add_argument('--target', choices=['both', 'logistic', 'ridge'], default='both',
                   help='which model to fit; the runner matrix fits one target per job in parallel')
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
