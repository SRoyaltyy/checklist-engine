#!/usr/bin/env python3
"""Shared (per-date) tier for the universe engine. Readers unchanged.
For each session D: (a) all ticker-INDEPENDENT ids, (b) 'base' answer of each ticker-DEPENDENT james/grok row
with the stock BUT check neutralised (stock_but -> True), computed with ref ticker AAPL.
Output: universe/shared/{year}.parquet  columns date,row_id,tier(ind|base),code(int8: 0=NR,1=NO,2=YES)"""
import sys, json, time, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_preburn_matrix as B
from build_preburn_fast import patch, CELL_MEMO
from build_preburn_fast2 import claims_for
OUTD = Path(__file__).resolve().parent / "shared"; OUTD.mkdir(exist_ok=True)
DEP = set(json.load(open(B.OUT / "ticker_dependence.json"))["ticker_dependent"])
CODE = {"NOT_READY": 0, "NO": 1, "YES": 2}

def work(dates):
    owner = B.load_sheet_owners(); R = patch(B.load_readers()); M = dict(R); J, G = M["james"], M["grok"]
    jall = J._rows(); gall = G.grok_rows()
    jind, gind = jall[~jall.id.isin(DEP)], [r for r in gall if r["id"] not in DEP]
    jdep = jall[jall.id.isin(DEP)]; gdep = [r for r in gall if r["id"] in DEP and " BUT stock" in r["strict_definition"]]
    js0, gs0 = J.stock_but, G.stock_but
    for d in dates:
        fp = OUTD / "days" / f"{d}.parquet"
        if fp.exists(): continue
        out = []; CELL_MEMO.clear(); t0 = time.time()
        J._rows = lambda: jind; G.grok_rows = lambda: gind; J.stock_but, G.stock_but = js0, gs0
        for rid, c in claims_for(owner, R, "AAPL", d).items(): out.append((d, rid, "ind", CODE[c[0][0]]))
        J._rows = lambda: jdep; G.grok_rows = lambda: gdep
        J.stock_but = lambda *a, **k: (True, pd.Timestamp("2100-01-01")); G.stock_but = lambda *a, **k: (True, "0000-00-00")
        for rid, c in claims_for(owner, R, "AAPL", d).items(): out.append((d, rid, "base", CODE[c[0][0]]))
        pd.DataFrame(out, columns=["date", "row_id", "tier", "code"]).astype({"code": "int8"}).to_parquet(fp, index=False)
        print(f"shared {d} {time.time()-t0:.1f}s", flush=True)
    return len(dates)

def sessions(year):
    p = pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet", columns=["date"], filters=[("ticker", "=", "SPY")])
    return [d.strftime("%Y-%m-%d") for d in sorted(p.date) if d.year == year]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("year", type=int); ap.add_argument("--workers", type=int, default=3); a = ap.parse_args()
    (OUTD / "days").mkdir(exist_ok=True)
    ds = sessions(a.year); t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(work, ds[i::a.workers]) for i in range(a.workers)]): f.result()
    df = pd.concat([pd.read_parquet(OUTD / "days" / f"{d}.parquet").astype({"row_id": "category", "tier": "category", "date": "category"}) for d in ds], ignore_index=True)
    df = df.astype({"code": "int8", "tier": "category", "row_id": "category", "date": "category"})
    df.to_parquet(OUTD / f"{a.year}.parquet", index=False)
    print(f"DONE {a.year} dates={len(ds)} rows={len(df)} {time.time()-t0:.0f}s", flush=True)
