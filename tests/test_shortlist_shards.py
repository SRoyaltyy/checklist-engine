"""Sharded-shortlist tests: scoring/shortlist.py --shard/--merge must reproduce the single-job path
exactly on a synthetic fixture shaped like the real grid (gridy_001/gridy_008/gridy_010 inputs, per 0b).
Checks the junk rule (blank / yes>95% / yes<0.5%), the EV screen (n>=30, ev>0, ev>bench), the 2022 check
stats attach, and full shard+merge == single-job equivalence.
Run: python3 tests/test_shortlist_shards.py"""
import os, sys, subprocess, tempfile
import numpy as np, pandas as pd

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print(f'FAIL: {name}')

KEYC = ['qid', 'ans', 'tp', 'hold', 'stop']
STATC = ['n', 'win_cnt', 'win_sum', 'sum_ret', 'sum_bench', 'sum_spy', 'sum_sq']
LEG = (20, 15, 0)

def cell(qid, ans, rule, n, ev, bench_ev, win=.5):
    d = dict(zip(KEYC, (qid, ans, *rule)))
    d.update(n=n, win_cnt=int(n * win), win_sum=n * win * ev, sum_ret=n * ev,
             sum_bench=n * bench_ev, sum_spy=n * ev * .8, sum_sq=n * (ev ** 2 + .04 ** 2))
    return d

def build_fixture(root):
    os.makedirs(root, exist_ok=True)
    rules = [LEG, (10, 5, 0)]
    # per-question legacy (n per answer) and per-rule economics
    spec = {   # qid: (n1, n0, ev, bench_ev)
        'q_good':    (20000, 20000, .010, .002),
        'q_bad':     (20000, 20000, -.008, .002),
        'q_small':   (20, 40, .010, .002),        # n < 30 at every rule -> screened out
        'q_junk_yes': (39800, 200, .010, .002),   # yes share 99.5% -> junk
        'q_rare_yes': (50, 19950, .010, .002),    # yes share 0.25% -> junk
        'q_blank':   (500, 500, .010, .002),      # answered 1k / 400k fit -> 99.75% blank -> junk
    }
    for chunk in (1, 8, 10):
        for year in (2020, 2021, 2022):
            rows = []
            for qid, (n1, n0, ev, bev) in spec.items():
                for rule in rules:
                    for ans, n in ((1, n1), (0, n0)):
                        ev_y = ev if year != 2022 else ev - .05        # 2022 check stats differ
                        rows.append(cell(qid, ans, rule, n // 2, ev_y, bev))
            df = pd.DataFrame(rows).groupby(KEYC, sort=False)[STATC].sum().reset_index()
            df.to_parquet(os.path.join(root, f'gridy_{chunk:03d}_{year}.parquet'), index=False)
    dates = pd.bdate_range('2020-01-01', '2021-12-31')
    cnt = np.full(len(dates), 400_000 // (2 * len(dates)))
    np.savez(os.path.join(root, 'bench_pre.npz'), dates=dates.astype('datetime64[ns]'), cnt=cnt)
    return root

def run(args):
    r = subprocess.run([sys.executable, os.path.join(D, 'scoring', 'shortlist.py')] + args,
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:]); print(r.stderr[-2000:])
        raise SystemExit(f'shortlist.py {" ".join(args)} failed')
    return r.stdout

tmp = tempfile.mkdtemp(prefix='shortlist_shards_')
fix = build_fixture(tmp)
run(['--indir', fix, '--bench', os.path.join(fix, 'bench_pre.npz'), '--out', os.path.join(tmp, 'single.csv')])
single = pd.read_csv(os.path.join(tmp, 'single.csv'))
ok('single-job: only q_good survives the full screen', set(single.qid) == {'q_good'})
ok('single-job: legacy rule kept, alt rule kept', set(map(tuple, single[['tp', 'hold', 'stop']].values)) == {LEG, (10, 5, 0)})
ok('single-job: 2022 check stats attached', 'chk_n' in single.columns and single.chk_n.notna().all() and (single.chk_ev < single.ev).all())
ok('single-job: 12 cells = 3 chunks x 1 question x 2 answers x 2 rules', len(single) == 12)

sd = os.path.join(tmp, 'shards'); os.makedirs(sd, exist_ok=True)
for c in (0, 1, 8, 10, 33):   # 0 and 33 have no files: must be a clean no-op
    run(['--shard', str(c), '--indir', fix, '--out', os.path.join(sd, f'shortlist_shard_{c}.parquet')])
ok('missing chunk is a no-op', not os.path.exists(os.path.join(sd, 'shortlist_shard_0.parquet'))
   and not os.path.exists(os.path.join(sd, 'shortlist_shard_33.parquet')))
legs = [f for f in os.listdir(sd) if f.endswith('.leg.parquet')]
ok('leg summaries written for the 3 real chunks', sorted(legs) == ['shortlist_shard_1.parquet.leg.parquet',
    'shortlist_shard_10.parquet.leg.parquet', 'shortlist_shard_8.parquet.leg.parquet'])
run(['--merge', '--indir', sd, '--bench', os.path.join(fix, 'bench_pre.npz'), '--out', os.path.join(tmp, 'merged.csv')])
merged = pd.read_csv(os.path.join(tmp, 'merged.csv'))
ok('merge: same survivors as single job', set(merged.qid) == {'q_good'})
m = merged.sort_values(KEYC).reset_index(drop=True)
s = single.sort_values(KEYC).reset_index(drop=True)
for col in ('n', 'ev', 'bench_ev', 't', 'chk_n', 'chk_ev'):
    ok(f'equivalence: {col} matches single job', np.allclose(m[col], s[col], rtol=1e-9, equal_nan=True))
ok('equivalence: row count matches', len(m) == len(s))
leg = pd.concat([pd.read_parquet(os.path.join(sd, f)) for f in legs])
ok('leg counts: q_good answered 40000 per chunk', int(leg[leg.qid == 'q_good'].n.sum()) == 40000 * 3)

n_fail = sum(1 for _, c in PASS if not c)
print(f'SHORTLIST SHARD TESTS {"PASS" if n_fail == 0 else "FAIL"} ({len(PASS) - n_fail}/{len(PASS)} passed)')
sys.exit(1 if n_fail else 0)
