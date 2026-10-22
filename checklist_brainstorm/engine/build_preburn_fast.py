#!/usr/bin/env python3
"""Fast path for build_preburn_matrix.py. Reader code is UNCHANGED; we wrap pure point-in-time
loaders with a per-(ticker,date) memo that is cleared before every cell (so no state crosses dates,
no lookahead possible beyond what the reader itself computes). Pairs are grouped per ticker per worker
so each process loads a ticker's raw history once (readers' own _mem cache).
Usage: build_preburn_fast.py --workers N [--outdir DIR] [--only-existing K]"""
import argparse, functools, sys, time, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import build_preburn_matrix as B

CELL_MEMO = {}
def memo(name, fn):
    @functools.wraps(fn)
    def w(*a):
        k = (name,) + a
        if k in CELL_MEMO:
            ok, v = CELL_MEMO[k]
            if ok: return v
            raise v
        try: v = fn(*a)
        except Exception as e: CELL_MEMO[k] = (False, e); raise
        CELL_MEMO[k] = (True, v); return v
    return w

def patch(readers):
    for name, m in readers:
        if name == "james":
            for f in ("pit", "bars"): setattr(m, f, memo("j_" + f, getattr(m, f)))
            rows = m._rows(); m._rows = lambda rows=rows: rows
        if name == "grok":
            for f in ("bars_before", "sessions", "net_daily"): setattr(m, f, memo("g_" + f, getattr(m, f)))
    return readers

def worker(pairs, outdir):
    if outdir: B.CELLS = Path(outdir)
    owner = B.load_sheet_owners(); readers = patch(B.load_readers()); res = []
    for t, d in pairs:
        op = B.cell_path(t, d)
        if op.exists() and op.stat().st_size > 500: res.append((t, d, "skip")); continue
        CELL_MEMO.clear(); t0 = time.time()
        try:
            cnt = B.run_cell(owner, readers, t, d, {"james", "grok-bot"})
            print(f"OK {t} {d} {dict(cnt)} {time.time()-t0:.1f}s", flush=True); res.append((t, d, "ok"))
        except Exception as e:
            traceback.print_exc(); res.append((t, d, f"fail:{e}"))
    return res

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--outdir"); ap.add_argument("--pairs-file"); a = ap.parse_args()
    if a.pairs_file:
        pairs = [tuple(l.split()) for l in open(a.pairs_file) if l.strip()]
    else:
        tick = (B.OUT / "tickers.txt").read_text().split(); dates = (B.OUT / "dates_train.txt").read_text().split()
        pairs = [(t, d) for t in tick for d in dates if not (B.cell_path(t, d).exists() and B.cell_path(t, d).stat().st_size > 500)]
    # group by ticker, round-robin tickers across workers
    byt = {}
    for t, d in pairs: byt.setdefault(t, []).append((t, d))
    chunks = [[] for _ in range(a.workers)]
    for i, t in enumerate(sorted(byt, key=lambda t: -len(byt[t]))): min(chunks, key=len).extend(byt[t])
    chunks = [c for c in chunks if c]
    print(f"fast todo={len(pairs)} workers={len(chunks)}", flush=True)
    with ProcessPoolExecutor(len(chunks)) as ex:
        for f in as_completed([ex.submit(worker, c, a.outdir) for c in chunks]): f.result()
if __name__ == "__main__": main()
