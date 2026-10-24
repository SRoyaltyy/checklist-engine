"""Shortlist stage (COMBINING_PREREG §3-5): turn the per-year exit-grid aggregates into a screened
question shortlist on the FIT window (2020-21), with 2022 check stats recorded untouched beside it.

Junk rule (§3): a question is junk if >95% blank, or its "yes" share of answered days is >95% or <0.5%.
Signal screen: n >= 30, EV after fees > 0, and EV beats the same-day benchmark (equal-weight, same rule).
Ranked by a screening t = (EV - bench_EV) / SE(EV) from the grid's moment sums; the formal 5.4 bar is
applied later at trade level with stats/luck_check.py (clustered SEs) - this screen only narrows the field.

Streams file by file (keys are unique within a file; chunks partition questions), so memory stays bounded.
Usage: python3 scoring/shortlist.py --indir grid_chunks --bench grid_pre/bench_pre.npz --out shortlist.csv
"""
import os, glob, argparse
import numpy as np, pandas as pd

LEGACY = dict(tp=20, hold=15, stop=0)                     # exit rule v1 anchor; n is rule-invariant
STATC = ['n', 'win_cnt', 'win_sum', 'sum_ret', 'sum_bench', 'sum_spy', 'sum_sq']
KEYC = ['qid', 'ans', 'tp', 'hold', 'stop']


def derive(df):
    n = df.n.clip(lower=1)
    df = df.copy()
    df['ev'] = df.sum_ret / n
    df['bench_ev'] = df.sum_bench / n
    df['spy_ev'] = df.sum_spy / n
    df['win'] = df.win_cnt / n
    df['sd'] = np.sqrt((df.sum_sq / n - df.ev ** 2).clip(lower=0))
    df['se'] = df.sd / np.sqrt(n)
    df['t'] = (df.ev - df.bench_ev) / df.se.replace(0, np.nan)
    return df


def files_by_chunk(indir):
    out = {}
    for f in glob.glob(os.path.join(indir, 'gridy_*.parquet')):
        b = os.path.basename(f)
        c = int(b.split('_')[1])
        y = int(b.rsplit('_', 1)[1].split('.')[0])
        out.setdefault(c, {})[y] = f
    for f in glob.glob(os.path.join(indir, 'grid_*.parquet')):
        out.setdefault(int(os.path.basename(f).split('_')[1].split('.')[0]), {})[0] = f
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--indir', default='grid_chunks')
    ap.add_argument('--bench', default=None, help='bench_pre.npz (per-year trade counts for the junk rule)')
    ap.add_argument('--out', default='shortlist.csv')
    a = ap.parse_args()
    chunks = files_by_chunk(a.indir)
    fit_years = [y for y in (2020, 2021) if any(y in v for v in chunks.values())]
    use_yearly = bool(fit_years)
    fit_years = fit_years or [0]
    check_year = 2022 if any(2022 in v for v in chunks.values()) else 0

    # ---- pass 1: junk rule from the legacy-rule slice (n is rule-invariant) ----
    leg_rows = []
    for c, m in sorted(chunks.items()):
        if not any(y in m for y in fit_years):
            continue
        for y in fit_years:
            df = pd.read_parquet(m[y], columns=KEYC + ['n'])
            leg_rows.append(df[(df.tp == LEGACY['tp']) & (df.hold == LEGACY['hold']) & (df['stop'] == LEGACY['stop'])][['qid', 'ans', 'n']])
    leg = pd.concat(leg_rows).groupby(['qid', 'ans']).n.sum().reset_index()
    answered = leg.groupby('qid').n.sum()
    n_fit = None
    if a.bench and os.path.exists(a.bench):
        B = np.load(a.bench)
        yrs = pd.DatetimeIndex(pd.to_datetime(B['dates'])).year.to_numpy()
        n_fit = float(B['cnt'][np.isin(yrs, fit_years)].sum()) if use_yearly else float(B['cnt'].sum())
    yes = (leg[leg.ans == 1].set_index('qid').n / answered).fillna(0)
    junk = (set(blank[blank > 0.95].index) if (blank := (1 - answered / n_fit)) is not None else set()) \
        | set(yes[yes > 0.95].index) | set(yes[yes < 0.005].index)
    print(f'questions: {len(answered)}, junk: {len(junk)}; fit trades: {n_fit}', flush=True)

    # ---- pass 2: stream, screen, attach untouched 2022 stats ----
    survivors, tries = [], 0
    for c, m in sorted(chunks.items()):
        if not any(y in m for y in fit_years):
            continue
        frames = [pd.read_parquet(m[y]) for y in fit_years if y in m]
        f = frames[0]
        for g in frames[1:]:
            f[STATC] = f[STATC] + g[STATC].to_numpy()
        tries += len(f)
        f = derive(f)
        f = f[(~f.qid.isin(junk)) & (f.n >= 30) & (f.ev > 0) & (f.ev > f.bench_ev)]
        if check_year in m and len(f):
            chk = derive(pd.read_parquet(m[check_year], columns=KEYC + STATC))
            f = f.merge(chk[KEYC + ['n', 'ev', 'bench_ev', 'spy_ev', 'win', 't']].rename(
                columns={k: f'chk_{k}' for k in ('n', 'ev', 'bench_ev', 'spy_ev', 'win', 't')}), on=KEYC, how='left')
        if len(f):
            survivors.append(f)
        print(f'chunk {c}: survivors so far {sum(len(s) for s in survivors)}', flush=True)
    s = pd.concat(survivors).sort_values('t', ascending=False)
    print(f'cells examined (try ledger): {tries}; survived screen: {len(s)}')
    s.to_csv(a.out, index=False)
    print('wrote', a.out, len(s), 'rows')


if __name__ == '__main__':
    main()
