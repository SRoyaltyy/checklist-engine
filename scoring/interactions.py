"""Cross-group interaction search (METHODOLOGY 0b fix 4): screened pair search across ALL
question groups and data blocks. Selection happens on the FIT window only (2020-21); the check
year (2022) is evaluated once and never tweaked.

Pipeline:
  1. Screen: per (question, kept level) standalone t = EV / SE on the FIT window at the legacy
     anchor cell (tp 20%, hold 15, no stop - same anchor as scoring/shortlist.py, n rule-invariant).
     Questions entering the pair pool: max |t| over levels >= --screen-t, ranked by max |t|, capped
     at --top-k. Rare levels kept via --min-level-count (replaces the 0.5% share cut, fix 4).
  2. Pairs: for every pair in the pool, contingency over kept levels x kept levels on fit rows;
     cells with count >= --min-cell become interaction dummies. Fit a per-pair logistic
     p(win = net ret > 0) with those dummies (plus level priors); record fit EV lift, t, and the
     untouched check-year out-of-sample EV lift vs the same pair's mains-only baseline.
  3. Triples: only among pair survivors (check-year lift > 0), same procedure one level up.

Usage:
  python3 scoring/interactions.py --answers answers_dir --base chunks/trade_base_rows.parquet \
      --pre grid_pre --out interactions.csv [--fit-years 2020 2021] [--check-year 2022] \
      [--screen-t 2.5] [--top-k 300] [--min-level-count 20] [--min-cell 30] [--max-pairs 200000]

Heavy compute: runners only. Streams answers chunk by chunk (never concatenates).
"""
import os, sys, json, time, argparse, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring import exit_grid as X
from scoring import combine as CB

BLANK = -1
LEGACY_MI = int(round(0.20 * 100)) - 2          # TP_PCTS index for tp=20%
LEGACY_HOLD = 15


def log(*a):
    print(time.strftime('%m-%d %H:%M:%S'), *a, flush=True)


def legacy_profit(pre, rows):
    """Per-trade net ret at the legacy anchor for row indices `rows` (int array)."""
    a = pre['tp_day'][LEGACY_MI, rows].astype(np.int32)
    hit = a >= 0
    within = a < LEGACY_HOLD
    tp = pre['tp_ret'][LEGACY_MI, rows]
    cl = pre['clos'][LEGACY_HOLD - 1, rows]
    return np.where(hit & within, tp, cl).astype(np.float64)


def level_stats(M, lev_mask, y):
    """EV/SE per level for one question column on fit rows. M: (n_fit,) int8 codes."""
    out = {}
    for v in np.unique(M):
        if v == BLANK:
            continue
        m = M == v
        n = int(m.sum())
        if n < 2:
            continue
        r = y[m]
        se = r.std(ddof=1) / np.sqrt(n)
        out[int(v)] = (n, float(r.mean()), float(r.mean() / se) if se > 0 else 0.0)
    return out


def screen(answers, cols, fit_rows, y_fit, min_level_count, screen_t, top_k):
    """Pass 1: per-question level t-stats on fit rows -> pool of screened questions."""
    feats = CB.Featurizer(cols)
    feats.fit([(M[fit_rows], c) for M, c in answers], min_level_count=min_level_count)
    log('featurizer kept', int((~feats.junk).sum()), 'of', len(cols), 'questions;',
        feats.n_feat, 'features; rare-level floor =', min_level_count, 'trades (fix 4)')
    pool = []          # (qidx, best_t)
    off = 0
    for M, c in answers:
        for j in range(M.shape[1]):
            gj = off + j
            lev = feats.levels[gj]
            if lev is None:
                continue
            # re-apply the count floor (featurizer used its own cut) and drop tiny levels
            st = level_stats(M[fit_rows], None, y_fit)
            st = {v: s for v, s in st.items() if s[0] >= min_level_count}
            if not st:
                continue
            best = max(abs(s[2]) for s in st.values())
            if best >= screen_t:
                pool.append((gj, best, sorted(st)))
        off += M.shape[1]
    pool.sort(key=lambda x: -x[1])
    log('screen: pool =', len(pool), 'questions at |t| >=', screen_t, '; keeping top', top_k)
    return feats, pool[:top_k]


def pair_cells(Ma, Mb, la, lb, min_cell):
    """contingency over levels la x lb on fit rows; returns dict (ia,ib) -> (mask_rows, count)."""
    cells = {}
    for ia, va in enumerate(la):
        ma = Ma == va
        if not ma.any():
            continue
        for ib, vb in enumerate(lb):
            m = ma & (Mb == vb)
            n = int(m.sum())
            if n >= min_cell:
                cells[(ia, ib)] = n
    return cells


def fit_pair(design, win, n_feat):
    """Logistic p(win) on a small 0/1 design (n x k) via Newton (few iterations)."""
    Xd = np.asarray(design, np.float64)
    beta = np.zeros(n_feat)
    for _ in range(25):
        z = np.clip(Xd @ beta, -30, 30)
        p = 1 / (1 + np.exp(-z))
        g = Xd.T @ (p - win)
        W = p * (1 - p)
        H = (Xd * W[:, None]).T @ Xd + 1e-6 * np.eye(n_feat)
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
        beta -= step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def ev_of_beta(Xd, beta, y):
    p = 1 / (1 + np.exp(-np.clip(Xd @ beta, -30, 30)))
    return float((p * y).sum() / p.sum()) if p.sum() > 0 else np.nan


def run_pair(feats, answers, q_a, q_b, fit_rows, check_rows, y_fit, y_chk, min_cell):
    """One pair: mains-only vs mains+interactions logistic; returns dict or None."""
    la, lb = feats.levels[q_a], feats.levels[q_b]
    if la is None or lb is None:
        return None
    Ma = Mb = None
    off = 0
    for M, c in answers:
        w = slice(off, off + M.shape[1])
        if w.start <= q_a < w.stop:
            Ma = M[:, q_a - w.start]
        if w.start <= q_b < w.stop:
            Mb = M[:, q_b - w.start]
        off = w.stop
    if Ma is None or Mb is None:
        return None
    Maf, Mbf = Ma[fit_rows], Mb[fit_rows]
    cells = pair_cells(Maf, Mbf, la, lb, min_cell)
    if len(cells) < 2:
        return None
    n_m = len(la) + len(lb)
    n_i = len(cells)
    keys = list(cells)
    # build design on fit rows
    n = len(fit_rows)
    D0 = np.zeros((n, n_m + n_i))
    for i, v in enumerate(la):
        D0[:, i] = (Maf == v)
    for j, v in enumerate(lb):
        D0[:, len(la) + j] = (Mbf == v)
    for k, (ia, ib) in enumerate(keys):
        D0[:, n_m + k] = (Maf == la[ia]) & (Mbf == lb[ib])
    win_fit = (y_fit > 0).astype(np.float64)
    b0 = fit_pair(D0[:, :n_m], win_fit, n_m)
    b1 = fit_pair(D0, win_fit, n_m + n_i)
    lift_fit = ev_of_beta(D0, b1, y_fit) - ev_of_beta(D0[:, :n_m], b0, y_fit)
    if not np.isfinite(lift_fit):
        return None
    # check-year evaluation (untouched): same design columns on check rows
    Mac, Mbc = Ma[check_rows], Mb[check_rows]
    nc = len(check_rows)
    Dc0 = np.zeros((nc, n_m + n_i))
    for i, v in enumerate(la):
        Dc0[:, i] = (Mac == v)
    for j, v in enumerate(lb):
        Dc0[:, len(la) + j] = (Mbc == v)
    for k, (ia, ib) in enumerate(keys):
        Dc0[:, n_m + k] = (Mac == la[ia]) & (Mbc == lb[ib])
    win_chk = (y_chk > 0).astype(np.float64)
    lift_chk = ev_of_beta(Dc0, b1, y_chk) - ev_of_beta(Dc0[:, :n_m], b0, y_chk)
    return dict(q_a=q_a, q_b=q_b, n_cells=n_i, min_cell=min_cell,
                lift_fit=lift_fit, lift_check=lift_chk,
                n_fit=int(D0[:, n_m:].sum()), n_check=int(Dc0[:, n_m:].sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--answers', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--pre', required=True)
    ap.add_argument('--out', default='interactions.csv')
    ap.add_argument('--fit-years', type=int, nargs='+', default=[2020, 2021])
    ap.add_argument('--check-year', type=int, default=2022)
    ap.add_argument('--screen-t', type=float, default=2.5)
    ap.add_argument('--top-k', type=int, default=300)
    ap.add_argument('--min-level-count', type=int, default=20)
    ap.add_argument('--min-cell', type=int, default=30)
    ap.add_argument('--max-pairs', type=int, default=200000)
    ap.add_argument('--cols', default=None, help='optional comma list of question ids to restrict (smoke)')
    a = ap.parse_args()

    base = pd.read_parquet(a.base)
    yrs = pd.DatetimeIndex(base.date).year.to_numpy()
    fit_rows = np.where(np.isin(yrs, a.fit_years))[0]
    check_rows = np.where(yrs == a.check_year)[0]
    log('trades', len(base), 'fit', len(fit_rows), 'check', len(check_rows))
    pre = CB.load_pre(a.pre, None)
    y = legacy_profit(pre, np.arange(len(base)))
    y_fit, y_chk = y[fit_rows], y[check_rows]

    answers = [(np.ascontiguousarray(M), c) for M, c in CB.iter_answers(a.answers)]
    cols = CB.all_cols(a.answers)
    if a.cols:
        keep = set(a.cols.split(','))
        pick = [j for j, c in enumerate(cols) if c.split('|')[1] in keep or c in keep]
        if pick:
            answers = [(M[:, pick], [cols[j] for j in pick])]
            cols = [cols[j] for j in pick]
            log('restricted to', len(cols), 'columns (smoke)')

    feats, pool = screen(answers, cols, fit_rows, y_fit, a.min_level_count, a.screen_t, a.top_k)
    rows, tried = [], 0
    for ia in range(len(pool)):
        for ib in range(ia + 1, len(pool)):
            if tried >= a.max_pairs:
                break
            tried += 1
            r = run_pair(feats, answers, pool[ia][0], pool[ib][0], fit_rows, check_rows,
                         y_fit, y_chk, a.min_cell)
            if r:
                r['qid_a'], r['qid_b'] = cols[pool[ia][0]], cols[pool[ib][0]]
                r['t_a'], r['t_b'] = pool[ia][1], pool[ib][1]
                rows.append(r)
        if tried >= a.max_pairs:
            break
    log('pairs tried', tried, 'kept', len(rows))
    df = pd.DataFrame(rows).sort_values('lift_fit', ascending=False)
    df.to_csv(a.out, index=False)
    if len(df):
        surv = df[df.lift_check > 0]
        log('pair survivors (check lift > 0):', len(surv), 'of', len(df))
    log('wrote', a.out)


if __name__ == '__main__':
    main()
