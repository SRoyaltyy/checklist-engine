"""Shortlist stage (COMBINING_PREREG §3-5): turn the per-year exit-grid aggregates into a screened
question shortlist on the FIT window (2020-21), with 2022 check stats recorded untouched beside it.

Junk rule (§3): a question is junk if >95% blank, or its "yes" share of answered days is >95% or <0.5%.
Signal screen: n >= 30, EV after fees > 0, and EV beats the same-day benchmark (equal-weight, same rule).
Ranked by a screening t = (EV - bench_EV) / SE(EV) from the grid's moment sums; the formal 5.4 bar is
applied later at trade level with stats/luck_check.py (clustered SEs) - this screen only narrows the field.

SHARDED MODE (0b 2026-10-25 ~15:40): one job per grid chunk, streaming parquet batches so peak RAM stays
bounded on ubuntu-latest; each shard uploads its survivors + its legacy-rule counts; a small merge job
applies the global junk rule and writes shortlist.csv. Junk-at-merge is equivalent to junk-first because
the junk rule only removes cells.

Modes:
  python3 scoring/shortlist.py --prep ... (kept for reference)
  python3 scoring/shortlist.py --shard N --indir DIR --out FILE   -> screened survivors for chunk N
  python3 scoring/shortlist.py --merge --indir DIR --bench bench_pre.npz --out shortlist.csv
Default (no mode flag) = the original single-job path.
"""
import os, glob, argparse
import numpy as np, pandas as pd

LEGACY = dict(tp=20, hold=15, stop=0)                     # exit rule v1 anchor; n is rule-invariant
STATC = ['n', 'win_cnt', 'win_sum', 'sum_ret', 'sum_bench', 'sum_spy', 'sum_sq']
KEYC = ['qid', 'ans', 'tp', 'hold', 'stop']
BATCH = 200_000


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


def _batches(path, cols):
    """stream a parquet file in row-batch DataFrames with only `cols` materialized."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    for b in pf.iter_batches(batch_size=BATCH, columns=cols):
        yield b.to_pandas()


def _legacy_part(df):
    """(qid, ans, n) summed over the legacy-rule slice of one batch."""
    m = (df.tp == LEGACY['tp']) & (df.hold == LEGACY['hold']) & (df['stop'] == LEGACY['stop'])
    if not m.any():
        return None
    return df.loc[m, ['qid', 'ans', 'n']].groupby(['qid', 'ans'], sort=False).n.sum().reset_index()


def shard(chunk, indir, out):
    """process exactly one chunk: screen its cells, attach its own 2022 check stats, write survivors.
    Also streams legacy-rule counts to <out>.leg.parquet for the merge-time junk rule."""
    chunks = files_by_chunk(indir)
    m = chunks.get(chunk)
    if not m:
        print(f'shard {chunk}: no grid files; nothing to do')
        return
    fit_years = [y for y in (2020, 2021) if y in m] or ([0] if 0 in m else [])
    check_year = 2022 if 2022 in m else (0 if 0 in m else None)
    if not fit_years:
        print(f'shard {chunk}: no fit-year files; nothing to do')
        return
    leg_parts, surv_parts, tries = [], [], 0
    # ---- pass A: first fit year fully grouped by cell (unique keys), bounded by one year's cells
    base = None
    for y in fit_years:
        parts = []
        for df in _batches(m[y], KEYC + STATC):
            tries += len(df)
            leg_parts.append(_legacy_part(df))
            parts.append(df.groupby(KEYC, sort=False)[STATC].sum().reset_index())
        g = pd.concat(parts, ignore_index=True).groupby(KEYC, sort=False)[STATC].sum()
        base = g if base is None else base.add(g, fill_value=0)
        del g, parts
    base = base.reset_index()
    # ---- screen on the summed fit moments
    f = derive(base)
    del base
    f = f[(f.n >= 30) & (f.ev > 0) & (f.ev > f.bench_ev)]
    print(f'shard {chunk}: tries {tries}, pre-junk survivors {len(f)}', flush=True)
    if check_year is not None and len(f):
        keys = f[KEYC].drop_duplicates()
        chk_parts = []
        for df in _batches(m[check_year], KEYC + STATC):
            hit = df.merge(keys, on=KEYC, how='inner', sort=False)
            if len(hit):
                chk_parts.append(derive(hit)[KEYC + ['n', 'ev', 'bench_ev', 'spy_ev', 'win', 't']])
        if chk_parts:
            chk = pd.concat(chk_parts, ignore_index=True).drop_duplicates(KEYC)
            f = f.merge(chk.rename(columns={k: f'chk_{k}' for k in ('n', 'ev', 'bench_ev', 'spy_ev', 'win', 't')}),
                        on=KEYC, how='left')
    if len(f):
        f.to_parquet(out, index=False)
    leg = pd.concat([p for p in leg_parts if p is not None], ignore_index=True)
    if len(leg):
        leg.groupby(['qid', 'ans'], sort=False).n.sum().reset_index().to_parquet(out + '.leg.parquet', index=False)
    print(f'shard {chunk}: wrote {out} ({len(f)} rows)', flush=True)


def merge(indir, bench, out):
    """global junk rule from the per-shard legacy counts + bench trade counts; apply; rank; write csv."""
    legs = [pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(indir, 'shortlist_shard_*.leg.parquet')))]
    shards = [pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(indir, 'shortlist_shard_*.parquet')))
              if not f.endswith('.leg.parquet')]
    if not shards:
        print('no shard outputs; nothing to merge')
        return
    s = pd.concat(shards, ignore_index=True)
    print(f'merge: {len(s)} pre-junk survivors from {len(shards)} shards', flush=True)
    if legs:
        leg = pd.concat(legs).groupby(['qid', 'ans']).n.sum().reset_index()
        answered = leg.groupby('qid').n.sum()
        n_fit = None
        if bench and os.path.exists(bench):
            B = np.load(bench)
            yrs = pd.DatetimeIndex(pd.to_datetime(B['dates'])).year.to_numpy()
            n_fit = float(B['cnt'][np.isin(yrs, (2020, 2021))].sum())
        yes = (leg[leg.ans == 1].set_index('qid').n / answered).fillna(0)
        junk = (set(blank[blank > 0.95].index) if n_fit and (blank := (1 - answered / n_fit)) is not None else set()) \
            | set(yes[yes > 0.95].index) | set(yes[yes < 0.005].index)
        print(f'merge: questions {len(answered)}, junk {len(junk)}; fit trades {n_fit}', flush=True)
        s = s[~s.qid.isin(junk)]
    s = s.sort_values('t', ascending=False)
    print(f'merge: post-junk survivors {len(s)}')
    s.to_csv(out, index=False)
    print('wrote', out, len(s), 'rows')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--indir', default='grid_chunks')
    ap.add_argument('--bench', default=None, help='bench_pre.npz (per-year trade counts for the junk rule)')
    ap.add_argument('--out', default='shortlist.csv')
    ap.add_argument('--shard', type=int, default=None, help='process only this chunk index (sharded mode)')
    ap.add_argument('--merge', action='store_true', help='merge shard outputs + apply junk rule')
    a = ap.parse_args()
    if a.shard is not None:
        return shard(a.shard, a.indir, a.out)
    if a.merge:
        return merge(a.indir, a.bench, a.out)

    # ---------------- original single-job path (kept for small runs / compatibility) ----------------
    chunks = files_by_chunk(a.indir)
    fit_years = [y for y in (2020, 2021) if any(y in v for v in chunks.values())]
    use_yearly = bool(fit_years)
    fit_years = fit_years or [0]
    check_year = 2022 if any(2022 in v for v in chunks.values()) else 0

    leg_rows = []
    for c, m in sorted(chunks.items()):
        for y in fit_years:
            if y not in m:
                continue
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
