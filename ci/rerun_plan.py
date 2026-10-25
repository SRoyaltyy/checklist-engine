"""Rerun plan: map changed question IDs (from impact_diff.json) to Step A chunks.

Chunk layout MUST stay frozen: answers_NNN.npz and grid_NNN.parquet are already produced for the
first chunks, so the fixed engine must reproduce the ORIGINAL sort order and 400-per-chunk layout for
existing questions. New questions (added by a fix, e.g. the SMA100 / MACDsig variants) do not fit the
frozen layout - they are reported separately as proposed EXTRA chunks (34, 35, ...) so old pieces stay valid.

Usage (on the fixed branch, data dir set):
  python3 ci/rerun_plan.py --changed C414 C07 I006 I030 ...            # facet/cutoff id prefixes
  python3 ci/rerun_plan.py --impact impact_diff.json                    # read changed column names from a diff run
Outputs JSON: affected chunks, their column counts, and extra (new) chunks.
"""
import os, sys, json, argparse, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', '/nonexistent')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E

def build_items(chunk=400):
    E.H71.load_buckets(); E.HIST.clear(); E.load_history(E.HISTF); E.GRIDV.clear(); E.GRIDV.update(E.load_grid())
    plan, rep = E.tf_plan()
    items = sorted(((key, kn) for key, tfs in plan.items() for kn in tfs), key=lambda x: (x[1][0], x[0], x[1][1]))
    col = lambda key, kn: ((f"H|{key[1]}|{key[2]}" if key[0] == 'H' else f"{key[1]}|{key[2]}") + f"|{kn[0]}d|{kn[1]}")
    cols = [col(k, kn) for k, kn in items]
    chunks = [cols[i:i + chunk] for i in range(0, len(cols), chunk)]
    return cols, chunks, rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--changed', nargs='*', default=[])          # id prefixes e.g. C414 I006 MACDsig
    ap.add_argument('--impact')                                   # impact_diff.json from ci/impact_diff.py
    ap.add_argument('--chunk', type=int, default=400)
    a = ap.parse_args()
    pats = list(a.changed)
    if a.impact:
        d = json.load(open(a.impact))
        pats += [c.split('|')[2] if c.count('|') >= 2 else c for r in d['per_ticker'].values()
                 for c in r.get('changed_columns', {})]
        pats = sorted(set(pats))
    cols, chunks, rep = build_items(a.chunk)
    print(f"plan: {len(cols)} questions, {len(chunks)} chunks of {a.chunk}; coverage {rep}")
    print(f"changed id patterns: {pats}")
    affected = {}
    unmatched = []
    for p in pats:
        hits = [i for i, c in enumerate(cols) if p in c]
        if not hits: unmatched.append(p)
        for i in hits: affected.setdefault(i // a.chunk, set()).add(p)
    print(json.dumps({
        'chunks_total': len(chunks),
        'affected_chunks': {str(ci): sorted(v) for ci, v in sorted(affected.items())},
        'n_affected': len(affected),
        'patterns_with_no_match': unmatched,
        'note': 'new-question variants that raise len(cols) above the frozen 13,600 get appended as extra chunks 34+; keep old pieces valid',
    }, indent=1))

if __name__ == '__main__':
    main()
