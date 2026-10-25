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


def _col_of(answers, q):
    off = 0
    for M, c in answers:
        if off <= q < off + M.shape[1]:
            return M[:, q - off]
        off += M.shape[1]
    return None


def run_group(feats, answers, qs, fit_rows, check_rows, y_fit, y_chk, min_cell):
    """One question group (pair or triple): mains-only vs mains+interactions logistic.
    Interaction dummies = full joint cells over kept levels with count >= min_cell."""
    levs = []
    Ms = []
    for q in qs:
        l = feats.levels[q]
        M = _col_of(answers, q)
        if l is None or M is None or len(l) == 0:
            return None
        levs.append(l)
        Ms.append(M)
    Mf = [M[fit_rows] for M in Ms]
    # joint contingency over the kept-level product
    from itertools import product
    keys = []
    # per-question level codes (vectorized)
    def codes_of(M, l):
        ls = np.sort(l)
        si = np.clip(np.searchsorted(ls, M), 0, len(ls) - 1)
        match = (ls[si] == M) & np.isin(M, ls)
        return np.where(match, si, -1)
    codes_fit = np.stack([codes_of(M, l) for M, l in zip(Mf, levs)], 1)
    n_m = sum(len(l) for l in levs)
    for combo in product(*[range(len(l)) for l in levs]):
        m = np.ones(len(fit_rows), bool)
        for j, cj in enumerate(combo):
            m &= codes_fit[:, j] == cj
        if int(m.sum()) >= min_cell:
            keys.append(combo)
    if len(keys) < 2:
        return None
    n_i = len(keys)
    n = len(fit_rows)
    D0 = np.zeros((n, n_m + n_i))
    o = 0
    for j, (M, l) in enumerate(zip(Mf, levs)):
        for i, v in enumerate(l):
            D0[:, o + i] = (M == v)
        o += len(l)
    for k, combo in enumerate(keys):
        m = np.ones(n, bool)
        for j, cj in enumerate(combo):
            m &= codes_fit[:, j] == cj
        D0[:, n_m + k] = m
    win_fit = (y_fit > 0).astype(np.float64)
    b0 = fit_pair(D0[:, :n_m], win_fit, n_m)
    b1 = fit_pair(D0, win_fit, n_m + n_i)
    lift_fit = ev_of_beta(D0, b1, y_fit) - ev_of_beta(D0[:, :n_m], b0, y_fit)
    if not np.isfinite(lift_fit):
        return None
    Mc = [M[check_rows] for M in Ms]
    codes_chk = np.stack([codes_of(M, l) for M, l in zip(Mc, levs)], 1)
    nc = len(check_rows)
    Dc0 = np.zeros((nc, n_m + n_i))
    o = 0
    for j, (M, l) in enumerate(zip(Mc, levs)):
        for i, v in enumerate(l):
            Dc0[:, o + i] = (M == v)
        o += len(l)
    for k, combo in enumerate(keys):
        m = np.ones(nc, bool)
        for j, cj in enumerate(combo):
            m &= codes_chk[:, j] == cj
        Dc0[:, n_m + k] = m
    win_chk = (y_chk > 0).astype(np.float64)
    lift_chk = ev_of_beta(Dc0, b1, y_chk) - ev_of_beta(Dc0[:, :n_m], b0, y_chk)
    out = dict(n_cells=n_i, min_cell=min_cell, lift_fit=lift_fit, lift_check=lift_chk,
               n_fit=int(D0[:, n_m:].sum()), n_check=int(Dc0[:, n_m:].sum()), k=len(qs))
    for i, q in enumerate(qs):
        out[f'q{i}'] = q
    return out


def run_pair(feats, answers, q_a, q_b, fit_rows, check_rows, y_fit, y_chk, min_cell):
    """One pair: mains-only vs mains+interactions logistic; returns dict or None."""
    r = run_group(feats, answers, (q_a, q_b), fit_rows, check_rows, y_fit, y_chk, min_cell)
    if r is None:
        return None
    return dict(q_a=q_a, q_b=q_b, n_cells=r['n_cells'], min_cell=r['min_cell'],
                lift_fit=r['lift_fit'], lift_check=r['lift_check'],
                n_fit=r['n_fit'], n_check=r['n_check'])


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
    ap.add_argument('--triple-pool', type=int, default=40)
    ap.add_argument('--max-triples', type=int, default=50000)
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
        # ---- stage 3: triples from pair survivors (bounded pool by survivor frequency) ----
        from collections import Counter
        freq = Counter(list(surv.q_a) + list(surv.q_b))
        tpool = [q for q, _ in freq.most_common(a.triple_pool)]
        log('triple pool:', len(tpool), 'questions from', len(surv), 'surviving pairs')
        trows, ttried = [], 0
        for combo3 in __import__('itertools').combinations(range(len(tpool)), 3):
            if ttried >= a.max_triples:
                break
            ttried += 1
            qs3 = tuple(tpool[i] for i in combo3)
            r = run_group(feats, answers, qs3, fit_rows, check_rows, y_fit, y_chk, a.min_cell)
            if r:
                for i, q in enumerate(qs3):
                    r[f'qid_{i}'] = cols[q]
                trows.append(r)
        log('triples tried', ttried, 'kept', len(trows))
        if trows:
            tdf = pd.DataFrame(trows).sort_values('lift_fit', ascending=False)
            tdf.to_csv(a.out.replace('.csv', '_triples.csv'), index=False)
            log('triple survivors (check lift > 0):', int((tdf.lift_check > 0).sum()), 'of', len(tdf))
    log('wrote', a.out)


if __name__ == '__main__':
    main()
