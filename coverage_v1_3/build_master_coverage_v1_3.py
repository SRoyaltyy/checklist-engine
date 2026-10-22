"""Build master_coverage v1.3 (add-only). Inputs: coverage_v1_2/master_coverage_v1_2.csv (227223e),
unblock/unblock_coverage_v4.csv (5662076; = v3 1232fca + appended BRW-NB-005 row, last row per id wins),
unblock/unblock_results_v2.csv (5b79b21), combo/COMBO_MODEL_RESULTS_V1.csv (4f67edc). 2020-24 only; no 2025+ data read."""
import pandas as pd, sys
root, out = sys.argv[1], sys.argv[2]
m = pd.read_csv(f'{root}/coverage_v1_2/master_coverage_v1_2.csv')
m['status_v1_2'] = m.status; m['source_v1_3'] = 'v1.2 unchanged'
u = pd.read_csv(f'{root}/unblock/unblock_coverage_v4.csv').drop_duplicates('id', keep='last').set_index('id')
u = u[u.w2_verdict.notna()]
for i, r in m.iterrows():
    if r.id not in u.index: continue
    x = u.loc[r.id]
    if x.w2_verdict == 'TESTED_FAIL':
        src = 'unblock wave 2 (57e7676/5b79b21/1232fca)' if r.id != 'BRW-NB-005' else 'BRW-NB-005 addendum3 (8bdeb3c/e942e2f/5662076)'
        res = f'FAIL (wave 2, feature {x.w2_feature}, 0 pass)'
        if r.status == 'TESTED' and str(r.result): res = str(r.result) + '; ' + res
        m.loc[i, ['status', 'result', 'source_v1_3']] = ['TESTED', res, src]
    elif x.w2_verdict == 'OPEN':
        m.loc[i, ['status', 'result', 'source_v1_3', 'reason']] = ['STILL_OPEN', 'not built in wave 2', 'unblock wave 2 (1232fca)', 'missing data: ' + str(x.w2_reason)]
m.to_csv(out, index=False)
