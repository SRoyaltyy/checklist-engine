"""Impact diff: run the SAME tickers through the base engine and the branch engine, diff answers.

Usage (inside a job on the branch, with base checked out at BASE_DIR):
  python3 ci/impact_diff.py run <engine_dir> <out_dir> <tickers.csv>
  python3 ci/impact_diff.py diff <base_out> <branch_out>

`run` saves one parquet per ticker (all question-answer columns, indexed by date).
`diff` aligns on date, counts changed cells per question column, and prints/writes impact_diff.json.
"""
import os, sys, json, subprocess, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUNNER = r'''
import sys, os, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', os.environ.get('IMPACT_GRID_FILE', '/nonexistent'))
sys.path.insert(0, sys.argv[1])
import numpy as np, pandas as pd, engine as E
from multiprocessing import Pool

def one(tk):
    E.H71.load_buckets(); E.HIST.clear(); E.load_history(E.HISTF); E.GRIDV.clear(); E.GRIDV.update(E.load_grid())
    plan, _ = E.tf_plan(); C = E.load_context()
    C['shares_by'] = {k: g for k, g in C['shares'].groupby('ticker')}; C['regsho_by'] = {k: g.date.values for k, g in C['regsho'].groupby('symbol')}
    Q = pd.read_csv(E.QUAR); C['mcap_bad'] = set(Q[Q.action == 'mcap_unknown'].ticker); C['mcap_jump'] = set(Q[Q.action == 'flag'].ticker)
    g = E.load_bars([tk]); fr, _ = E.run_ticker(tk, g, C, plan)
    fr.to_parquet(os.path.join(sys.argv[3], tk + '.parquet'))
    return tk, len(fr.columns), len(fr)

if __name__ == '__main__':
    tks = open(sys.argv[2]).read().split()
    os.makedirs(sys.argv[3], exist_ok=True)
    with Pool(min(4, len(tks))) as p:
        for tk, nc, nr in p.map(one, tks): print('done', tk, nc, 'cols', nr, 'rows', flush=True)
'''

def run(engine_dir, out_dir, tickers_csv):
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(RUNNER); script = f.name
    env = dict(os.environ, PYTHONPATH='')
    r = subprocess.run([sys.executable, script, engine_dir, tickers_csv, out_dir], env=env)
    sys.exit(r.returncode)

def diff(base_out, branch_out):
    import pandas as pd
    report = {}
    for fn in sorted(os.listdir(base_out)):
        if not fn.endswith('.parquet'): continue
        tk = fn[:-8]
        b_path, n_path = os.path.join(base_out, fn), os.path.join(branch_out, fn)
        if not os.path.exists(n_path):
            report[tk] = {'error': 'missing in branch run'}; continue
        b = pd.read_parquet(b_path).set_index('date'); n = pd.read_parquet(n_path).set_index('date')
        common = b.index.intersection(n.index)
        b, n = b.loc[common], n.loc[common]
        changed = {}
        for c in b.columns.intersection(n.columns):
            bb, nn = b[c].to_numpy(), n[c].to_numpy()
            m = (bb != nn) & ~(pd.isna(bb) & pd.isna(nn))
            if m.any(): changed[c] = int(m.sum())
        only_b = sorted(set(b.columns) - set(n.columns)); only_n = sorted(set(n.columns) - set(b.columns))
        report[tk] = dict(rows=int(len(common)), changed_columns=changed, n_changed=len(changed),
                          cells_changed=int(sum(changed.values())), only_base=only_b[:20], only_branch=only_n[:20])
    tot_cols = sum(r.get('n_changed', 0) for r in report.values())
    tot_cells = sum(r.get('cells_changed', 0) for r in report.values())
    agg = {}
    for r in report.values():
        for c, k in r.get('changed_columns', {}).items(): agg[c] = agg.get(c, 0) + k
    out = dict(tickers=len(report), questions_changed=tot_cols, cells_changed=tot_cells,
               top_changed=sorted(agg.items(), key=lambda x: -x[1])[:50], per_ticker=report)
    print(json.dumps({k: v for k, v in out.items() if k != 'per_ticker'}, indent=1))
    with open('impact_diff.json', 'w') as f: json.dump(out, f, indent=1)
    print('wrote impact_diff.json')

if __name__ == '__main__':
    if sys.argv[1] == 'run': run(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == 'diff': diff(sys.argv[2], sys.argv[3])
    else: raise SystemExit(__doc__)
