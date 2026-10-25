#!/usr/bin/env python3
"""State-change study runner (docs/STATE_CHANGE_PREREG.md §3 + §6 addendum).

Runs the pre-registered day-to-day probability-change cells on ONE final pass over
confirm-window data. Nothing here fits or tunes: every threshold, the residualisation,
and the pass rule were fixed in the prereg BEFORE results.

Inputs (all point-in-time confirm-window outputs, no 2020-22 retuning):
  --cells  long parquet, one row per (ticker, date, cell):
             ticker, date, role, m, h, stop, p_win, ev_net, realised_net, bench_net
           role = 'map' for the strategy-map (chosen) cell, 'fixed' for the continuity
           cell (exactly one fixed row per stock-day, matching --study-cell). Rows with
           any other role are ignored.
  --ret    optional daily-return parquet (ticker, date, ret) for residualisation
           (last-5/10/20-session returns, §1). If absent the run is flagged
           'unresidualised'; the registered form is residualised.

Output JSON: one entry per registered cell with n, mean net-vs-bench excess, the four
SE estimates (naive, stock-cluster, date-cluster, 20-day block resample), the worst-SE
t-stat, and PASS = (mean excess > 0, i.e. beats benchmark after fees) AND
(t_worst >= 5.4). One test, no retuning, 2023-24 only.
"""
import argparse, json
import numpy as np, pandas as pd

BANDS = [5, 10, 15, 20, 30]                    # §3 rise/fall thresholds (percentage points)
PERSIST_K = [2, 3, 5]                          # §3 persistence windows
PASS_T = 5.4                                   # §4 pass bar on the worst SE estimate
RNG = np.random.default_rng(20261024)          # frozen seed, fixed before results


def residualise(dv, tdf, rets):
    """Regress change measure dv (array/Series) on the stock's last-5/10/20-session
    returns (§1). tdf carries the matching ticker/date columns."""
    dv = np.asarray(dv, float)
    if rets is None:
        return dv, False
    r = rets.set_index(['ticker', 'date'])['ret']
    idx = pd.MultiIndex.from_frame(tdf)
    roll = lambda w: r.groupby(level=0, group_keys=False).apply(lambda s: s.rolling(w).sum())
    X = np.column_stack([np.ones(len(dv)), roll(5).reindex(idx).to_numpy(),
                         roll(10).reindex(idx).to_numpy(), roll(20).reindex(idx).to_numpy()])
    ok = np.isfinite(X).all(1) & np.isfinite(dv)
    out = np.full(len(dv), np.nan)
    if ok.sum() > X.shape[1]:
        beta, *_ = np.linalg.lstsq(X[ok], dv[ok], rcond=None)
        out[ok] = dv[ok] - X[ok] @ beta
    return out, True


def se_estimates(g, block=20, n_boot=200):
    """SE of the mean of per-trade net excess g (cols ticker,date,x)."""
    x = g['x'].to_numpy()
    n = len(x)
    out = {'naive': float(np.std(x, ddof=1) / np.sqrt(n))}
    for key in ('ticker', 'date'):
        grp = g.groupby(key)['x'].sum()      # cluster sums S_c; CRVE: Var(mean) = sum(S_c^2)/n^2
        out[f'cluster_{key}'] = float(np.sqrt((grp ** 2).sum()) / n)
    days = np.sort(g['date'].unique())
    by_day = g.groupby('date')['x'].mean().reindex(days).fillna(0.0)
    nb = int(np.ceil(len(by_day) / block))
    blocks = [by_day.iloc[i * block:(i + 1) * block].to_numpy() for i in range(nb)]
    rng = np.random.default_rng(20261024)          # re-seeded per call: identical input ->
    boots = np.empty(n_boot)                       # identical resample (reproducible report)
    for b in range(n_boot):
        pick = rng.integers(0, nb, nb)
        boots[b] = np.concatenate([blocks[i] for i in pick]).mean()
    out['block20'] = float(boots.std(ddof=1))
    out['n'] = int(n)
    return out


def trial(rows):
    """Pass-rule one registered cell on the triggered stock-days."""
    if len(rows) < 30:
        return {'n': int(len(rows)), 'pass': False, 'reason': 'n<30'}
    g = rows[['ticker', 'date']].copy()
    g['x'] = rows['realised_net'].to_numpy() - rows['bench_net'].to_numpy()
    se = se_estimates(g)
    mean = float(g['x'].mean())
    t_worst = mean / max(se[k] for k in ('naive', 'cluster_ticker', 'cluster_date', 'block20'))
    return {'n': int(len(rows)), 'mean_net_excess': mean, 'se': se,
            't_worst': float(t_worst), 'pass': bool(mean > 0 and t_worst >= PASS_T)}


def run(cells, ret, study_cell=(20, 15, 0)):
    df = cells.copy()
    df['date'] = pd.to_datetime(df['date'])
    if 'role' not in df.columns:
        raise SystemExit('cells parquet needs a role column (map|fixed)')
    cont = df[df.role == 'fixed']
    if not len(cont) or not ((cont.m == study_cell[0]) & (cont.h == study_cell[1]) & (cont.stop == study_cell[2])).all():
        raise SystemExit(f'fixed rows must all match the study cell {study_cell}')
    frames = {'continuity': cont.drop(columns='role'),
              'strategy_map': df[df.role == 'map'].drop(columns='role')}
    results = {}
    for vname, v0 in frames.items():
        v = v0.sort_values(['ticker', 'date']).copy()
        v['dp_res'], okr = residualise(v.groupby('ticker')['p_win'].diff() * 100, v[['ticker', 'date']], ret)   # pp
        v['dev_res'], _ = residualise(v.groupby('ticker')['ev_net'].diff(), v[['ticker', 'date']], ret)
        base = v.dropna(subset=['dp_res'])
        prev_p = base.groupby('ticker')['p_win'].shift(1)
        cur50, prev50 = base['p_win'] >= 0.5, prev_p >= 0.5
        sgn = np.sign(base['dp_res'])
        persist = {k: sgn.groupby(base['ticker'])
                        .transform(lambda s: s.rolling(k).apply(lambda w: np.all(w == w[0]) and w[0] != 0, raw=True))
                        .astype(bool) for k in PERSIST_K}
        for b in BANDS:
            results[f'{vname}|rise>={b}pp'] = trial(base[base.dp_res >= b])
            results[f'{vname}|fall<=-{b}pp'] = trial(base[base.dp_res <= -b])
        results[f'{vname}|cross_up_50'] = trial(base[cur50 & ~prev50.fillna(False)])
        results[f'{vname}|cross_down_50'] = trial(base[~cur50 & prev50.fillna(False)])
        for k in PERSIST_K:
            results[f'{vname}|persist{k}'] = trial(base[persist[k].fillna(False)])
        eb = v.dropna(subset=['dev_res'])
        for b in BANDS:
            results[f'{vname}|EVrise>={b}'] = trial(eb[eb.dev_res >= b / 100.0])
            results[f'{vname}|EVfall<=-{b}'] = trial(eb[eb.dev_res <= -b / 100.0])

    # ---- Δ-strategy indicators (§6.2), strategy-map variant only ----
    v = frames['strategy_map'].sort_values(['ticker', 'date']).copy()
    v['dstrat'] = v.groupby('ticker')[['m', 'h', 'stop']].diff().abs().sum(axis=1)
    vb = v.dropna(subset=['dstrat'])
    results['strategy_changed'] = trial(vb[vb.dstrat > 0])
    results['strategy_distance:same'] = trial(vb[vb.dstrat == 0])
    results['strategy_distance:near(<=2)'] = trial(vb[(vb.dstrat > 0) & (vb.dstrat <= 2)])
    results['strategy_distance:far(>2)'] = trial(vb[vb.dstrat > 2])
    results['_meta'] = {'residualised': ret is not None, 'pass_t': PASS_T,
                        'bands': BANDS, 'persist_k': PERSIST_K, 'frozen_seed': 20261024,
                        'prereg': 'docs/STATE_CHANGE_PREREG.md §3 + §6 addendum (7e9c117)'}
    return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cells', required=True)
    ap.add_argument('--ret')
    ap.add_argument('--out', required=True)
    ap.add_argument('--study-cell', default='20,15,0', help='m,h,stop of the continuity cell')
    a = ap.parse_args()
    cells = pd.read_parquet(a.cells)
    ret = pd.read_parquet(a.ret) if a.ret else None
    res = run(cells, ret, tuple(int(v) for v in a.study_cell.split(',')))
    json.dump(res, open(a.out, 'w'), indent=1)
    npass = sum(1 for k, v in res.items() if not k.startswith('_') and isinstance(v, dict) and v.get('pass'))
    print(f'state-change study: {sum(1 for k in res if not k.startswith("_"))} cells, {npass} pass -> {a.out}')
