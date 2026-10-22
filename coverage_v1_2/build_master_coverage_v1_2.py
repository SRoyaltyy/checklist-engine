"""Build master_coverage v1.2 (add-only). Inputs: v1.1 (Drive 1MX9qVHF3Jj6YtMyfzwvoGScT02TDg36L),
unblock/unblock_coverage_v2.csv (d2b3dda), untested_v2/untested_results_v2.csv. 2020-24 practice only; no 2025+ data read."""
import pandas as pd, sys
v11, root, out = sys.argv[1], sys.argv[2], sys.argv[3]
m = pd.read_csv(v11); m['status_v1_1'] = m.status
m['result'] = ''; m['source_v1_2'] = 'v1.1 unchanged'; m['flag'] = ''
u = pd.read_csv(f'{root}/unblock/unblock_coverage_v2.csv').set_index('id')
v = pd.read_csv(f'{root}/untested_v2/untested_results_v2.csv'); v = v[v.list == 'master'].set_index('row_id')
def setr(i, st, res, src, reason=None):
    m.loc[i, ['status', 'result', 'source_v1_2']] = [st, res, src]
    if reason is not None: m.loc[i, 'reason'] = reason
for i, r in m.iterrows():
    if r.id in v.index:
        s = v.loc[r.id, 'status']; src = 'untested_v2 (915eead/6a791b2)'
        if s == 'PASS': setr(i, 'TESTED', 'PASS (HINT only, 2020-24; EXIT_RULE_V1 + 10d)', src)
        elif s == 'FAIL': setr(i, 'TESTED', 'FAIL', src)
        elif s.startswith('TOO_RARE'): setr(i, 'TOO_FEW_TRADES', '<30 YES trades in a period', src)
        elif 'NR everywhere' in s: setr(i, 'BLOCKED', 'not testable', src, 'no stored answer on any buyable day (answers missing, not a NO)')
        else: setr(i, 'BLOCKED', 'not testable', src, 'data bug: all sibling buckets zero-YES while answered NO (missing coded as NO)')
    elif r.id in u.index:
        x = u.loc[r.id]; vd = x.unblock_verdict; why = str(x.unblock_source_or_reason); src = 'unblock_coverage_v2 (d2b3dda)'
        tr = str(x.tested_result)
        if vd == 'BUILT_TESTED' and tr.startswith('tested'): setr(i, 'TESTED', 'FAIL (0 pass) via ' + why, src)
        elif vd == 'BUILT_TESTED': setr(i, 'TOO_FEW_TRADES', tr, src)
        elif vd == 'BUILDABLE_NOT_BUILT': setr(i, 'BUILDABLE_FROM_FREE_DATA', '', src, why)
        elif vd == 'FAILS_0925' and why.startswith('DROP'): setr(i, 'BLOCKED', 'dropped', src, why)
        elif vd == 'FAILS_0925': setr(i, 'BUILDABLE_FROM_FREE_DATA', 'redefined to pre-09:25 info; not built', src, why)
        else: setr(i, 'BLOCKED', '', src, why)
for k in ['FND-NB-001', 'SUP-NB-004', 'PV-TF-452', 'PV-TF-455', 'PV-TF-458']:
    m.loc[m.id == k, 'flag'] = 'BUILDABLE_NOW (New Bot SEC share counts, Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4)' + \
        ('; %-of-mktcap version not built (proxy version tested)' if k.startswith('PV') else '')
m.to_csv(out, index=False)
