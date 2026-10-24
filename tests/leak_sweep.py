"""Extended leak sweep (Job 3): no answer for day D may use data from day D or later.
Extends tests/test_leak.py (calendar_context base test, 20 cut points, 0 diffs) to a stratified ticker sample
x cut dates chosen at volatility/split/earnings/year-edge stress points. Run on a runner, not the shared box:
  CHECKLIST_DATA_DIR=... python3 tests/leak_sweep.py [--tickers N] [--out leak_sweep.json]
Exit 0 = pass; mismatches are reported per (ticker, cut) with question names and written to the JSON.
"""
import os, sys, json, argparse, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', '/nonexistent')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np, pandas as pd
import engine as E
from test_leak import check

CUTS = ('2020-03-16', '2020-06-30', '2021-02-16', '2021-09-01', '2021-12-31', '2022-06-17',
        '2022-12-30', '2023-03-15', '2023-12-29', '2024-06-28', '2024-09-06', '2024-12-31')


def pick_tickers(n):
    """Stratified sample: short/long histories, split names, mcap flags, earnings-heavy, random mid."""
    u = pd.read_parquet(E.D('/workspace/pricehist/universe_2020_survivors.parquet'),
                        columns=['ticker', 'date'])
    cnt = u.groupby('ticker').size().sort_values()
    Q = pd.read_csv(E.QUAR)
    flags = set(Q[Q.action.isin(['mcap_unknown', 'flag'])].ticker)
    splits = set(pd.read_parquet(os.path.join(HERE, '..', 'integrity', 'splits_yahoo.parquet')).ticker)
    try:
        earn = pd.read_csv(E.D('/workspace/nasdaq_earn_2020-24.tar'), sep='\t').ticker.value_counts()
        heavy = set(earn[earn >= earn.quantile(0.9)].index)
    except Exception:
        heavy = set()
    rng = np.random.default_rng(20261024)
    picks, pool = [], [list(cnt.index[:max(1, n // 6)]), list(cnt.index[-max(1, n // 6):]),
                       sorted(splits), sorted(flags), sorted(heavy & set(cnt.index))]
    for group in pool:
        rng.shuffle(group)
        for t in group:
            if t not in picks:
                picks.append(t)
            if len(picks) >= n:
                return picks
    mid = sorted(set(cnt.index) - set(picks))
    rng.shuffle(mid)
    return (picks + mid)[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tickers', type=int, default=60)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    tks = pick_tickers(a.tickers)
    print('tickers:', ','.join(tks), flush=True)
    from multiprocessing import Pool
    with Pool(min(4, len(tks))) as p:
        out = sum(p.starmap(check, [(t, CUTS) for t in tks]), [])
    bad = [r for r in out if r['mismatched'] or r['col_set_diff']]
    summary = dict(tickers=len(tks), cut_points=len(out), mismatched_runs=len(bad),
                   total_mismatches=sum(r['mismatched'] + r['col_set_diff'] for r in out),
                   bad=bad, runs=out)
    print(json.dumps({k: summary[k] for k in ('tickers', 'cut_points', 'mismatched_runs', 'total_mismatches')}))
    for r in bad[:20]:
        print('LEAK?', json.dumps(r))
    if a.out:
        json.dump(summary, open(a.out, 'w'), indent=1)
    print('LEAK SWEEP', 'PASS' if not bad and out else 'FAIL')
    sys.exit(0 if not bad and out else 1)


if __name__ == '__main__':
    main()
