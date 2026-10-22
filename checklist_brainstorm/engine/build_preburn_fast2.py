#!/usr/bin/env python3
"""Two-tier fast path. Readers unchanged. Ticker-INDEPENDENT ids (structural, ticker_dependence.json)
are computed once per date (by one reference ticker) and broadcast; DEP ids computed per (ticker,date).
Output cells identical in format to build_preburn_matrix.py."""
import argparse, csv, json, time, traceback
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import build_preburn_matrix as B
from build_preburn_fast import patch, CELL_MEMO
DEPF = B.OUT / "ticker_dependence.json"

def setup():
    dep = set(json.load(open(DEPF))["ticker_dependent"])
    owner = B.load_sheet_owners(); R = patch(B.load_readers()); M = dict(R)
    J, G = M["james"], M["grok"]
    jall = J._rows(); gall = G.grok_rows()
    sets = {"dep": (jall[jall.id.isin(dep)], [r for r in gall if r["id"] in dep]),
            "ind": (jall[~jall.id.isin(dep)], [r for r in gall if r["id"] not in dep])}
    def use(which):
        j, g = sets[which]; J._rows = lambda j=j: j; G.grok_rows = lambda g=g: g
    return owner, R, use

def claims_for(owner, readers, t, d):
    cl = defaultdict(list)
    for name, m in readers:
        try: res = list(m.answer(t, d) or [])
        except Exception as e: print("ERR", name, t, d, e, flush=True); continue
        for r in res:
            rid = str(r.get("row_id", "")).strip()
            if rid not in owner or owner[rid] not in {"james", "grok-bot"}: continue
            ans = r.get("answer"); why = str(r.get("reason") or "").strip()
            if ans not in {"YES", "NO", "NOT_READY"}: ans, why = "NOT_READY", f"contract_error:{ans!r}"
            elif ans == "NOT_READY" and not why: why = "contract_error:no_reason"
            cl[rid].append((ans, why, str(r.get("data_as_of") or "")))
    return cl

def write(owner, cl, t, d, cells):
    op = Path(cells) / f"{t}_{d}.csv"; tmp = op.with_suffix(".tmp"); cnt = Counter()
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["row_id", "owner", "ticker", "date", "answer", "reason", "data_as_of"])
        for rid in sorted(cl):
            ans, why, asof = cl[rid][0]
            if len(cl[rid]) > 1: ans, why, asof = "NOT_READY", "conflict", ""
            cnt[ans] += 1; w.writerow([rid, owner[rid], t, d, ans, why, asof])
    tmp.replace(op); return cnt

def worker_dates(dates, ref):   # independent tier, one ref ticker per date
    owner, R, use = setup(); use("ind"); out = {}
    for d in dates:
        CELL_MEMO.clear(); out[d] = dict(claims_for(owner, R, ref, d))
    return out

def worker_cells(pairs, indep, cells):
    owner, R, use = setup(); use("dep"); n = 0
    for t, d in pairs:
        CELL_MEMO.clear(); t0 = time.time()
        cl = claims_for(owner, R, t, d); cl.update(indep[d])
        cnt = write(owner, cl, t, d, cells); print(f"OK {t} {d} {dict(cnt)} {time.time()-t0:.2f}s", flush=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--outdir", default=str(B.CELLS)); ap.add_argument("--pairs-file"); a = ap.parse_args()
    if a.pairs_file: pairs = [tuple(l.split()) for l in open(a.pairs_file) if l.strip()]
    else:
        tk = (B.OUT/"tickers.txt").read_text().split(); ds = (B.OUT/"dates_train.txt").read_text().split()
        pairs = [(t, d) for t in tk for d in ds if not ((Path(a.outdir)/f"{t}_{d}.csv").exists())]
    dates = sorted({d for _, d in pairs}); t0 = time.time()
    ch = [dates[i::a.workers] for i in range(a.workers)]; indep = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(worker_dates, c, "AAPL") for c in ch if c]): indep.update(f.result())
    t1 = time.time(); print(f"INDEP tier {len(dates)} dates {t1-t0:.1f}s", flush=True)
    byt = defaultdict(list)
    for p in pairs: byt[p[0]].append(p)
    chunks = [[] for _ in range(a.workers)]
    for t in sorted(byt, key=lambda t: -len(byt[t])): min(chunks, key=len).extend(byt[t])
    with ProcessPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(worker_cells, c, {d: indep[d] for d in {x[1] for x in c}}, a.outdir) for c in chunks if c]): f.result()
    t2 = time.time(); print(f"DEP tier {len(pairs)} cells {t2-t1:.1f}s TOTAL {t2-t0:.1f}s per-cell {(t2-t0)/max(1,len(pairs)):.2f}s", flush=True)
if __name__ == "__main__": main()
