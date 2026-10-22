#!/usr/bin/env python3
"""Add-on: James's 489 sector rows with sector_map=current_backfilled (current Theme Radar snapshot sector applied to every date).
Engine = readers/james.py itself (unchanged), _tr_universe patched to the current snapshot. Price source = James reader's own Yahoo cache.
Tier A (all stocks): 437 SECTOR_ONLY rows computed once per (sector, date) with a representative ticker, broadcast to every ticker of
  that sector. The stock-mcap rotation row is date bit (rep mcap forced tiny) AND the ticker's current Finviz Market Cap < threshold
  (fundamentals=as_restated/current). Tickers not in the snapshot -> NR, as the reader does.
Tier B (S&P 500 long-listed subset): the 52 STOCK_SECTOR rows run per cell through the reader. All-stocks file marks them NR.
Rows dated >= 2026-08-06 are report-only. Codes 0=NR 1=NO 2=YES.
usage: sector_addon.py A YEAR [--workers 2] | B YEAR [--workers 2] | assemble YEAR | equiv YEAR"""
import sys, json, re, time, importlib.util, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ENG = HERE.parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ENG))
import engine_year as E
from build_preburn_fast import memo, CELL_MEMO
CL = json.load(open(HERE / "sector_row_class.json")); MCAP = "__none__"  # mcap/tech rotation rows (SEC-JA-026/027) are STOCK_SECTOR -> tier B
OUT = HERE / "secadd"; OUT.mkdir(exist_ok=True); CODE = {"NOT_READY": 0, "NO": 1, "YES": 2}
U = pd.read_csv(E.SECT, dtype=str).set_index("Ticker")
def reader():
    sp = importlib.util.spec_from_file_location("jr", ENG / "readers/james.py"); J = importlib.util.module_from_spec(sp); sp.loader.exec_module(J)
    for f in ("pit", "bars"): setattr(J, f, memo("j" + f, getattr(J, f)))
    return J
def reps():
    px = set(pd.read_parquet(E.PX, columns=["ticker"]).ticker.astype(str).unique())
    return {s: sorted(t for t in g.index if t in px)[0] for s, g in U.groupby("Sector")}
def sp500():
    first = pd.read_parquet(E.PX, columns=["ticker", "date"]); first["ticker"] = first.ticker.astype(str); f = first.groupby("ticker").date.min()
    sp = [t for t in U.index if "S&P 500" in str(U.loc[t, "Index"])]
    return sorted(t for t in sp if t in f.index and f[t] <= pd.Timestamp("2020-01-10"))
def sessions(y):
    s = pd.read_parquet(E.PX, columns=["date"], filters=[("ticker", "=", "SPY")]).date
    return [d.strftime("%Y-%m-%d") for d in sorted(s) if d.year == y]
def runA(dates):
    J = reader(); R = reps(); U2 = U.copy(); U2.loc[list(R.values()), "Market Cap"] = "0.001"; J._tr_universe = lambda d: U2
    rows = J._rows(); rows = rows[rows.id.isin([i for i, v in CL.items() if v == "SECTOR_ONLY"])]; J._rows = lambda: rows; out = []
    for d in dates:
        fp = OUT / "A" / f"{d}.parquet"
        if fp.exists(): continue
        rec = []; t0 = time.time()
        for sec, rep in R.items():
            CELL_MEMO.clear()
            for a in J.answer(rep, d): rec.append((d, sec, a["row_id"], CODE[a["answer"]]))
        pd.DataFrame(rec, columns=["date", "sector", "row_id", "code"]).astype({"code": "int8"}).to_parquet(fp, index=False)
        print(f"A {d} {time.time()-t0:.1f}s", flush=True)
def runB(pairs):
    J = reader(); J._tr_universe = lambda d: U
    rows = J._rows(); rows = rows[rows.id.isin([i for i, v in CL.items() if v == "STOCK_SECTOR"])]; J._rows = lambda: rows
    for t, ds in pairs:
        fp = OUT / "B" / f"{t}_{ds[0][:4]}.parquet"
        if fp.exists(): continue
        rec = []; t0 = time.time()
        for d in ds:
            CELL_MEMO.clear()
            for a in J.answer(t, d): rec.append((t, d, a["row_id"], CODE[a["answer"]]))
        pd.DataFrame(rec, columns=["ticker", "date", "row_id", "code"]).astype({"code": "int8"}).to_parquet(fp, index=False)
        print(f"B {t} {len(ds)} {time.time()-t0:.0f}s", flush=True)
def pool(fn, chunks, w):
    with ProcessPoolExecutor(w) as ex:
        for f in as_completed([ex.submit(fn, c) for c in chunks if c]): f.result()
def ids_all(): return sorted(CL)
def assemble(y):
    ds = sessions(y); A = pd.concat([pd.read_parquet(OUT / "A" / f"{d}.parquet") for d in ds])
    A = A.pivot_table(index=["sector", "date"], columns="row_id", values="code", aggfunc="first")
    ids = ids_all(); jm = {i: k for k, i in enumerate(ids)}
    tick = sorted(pd.read_parquet(E.PX, columns=["ticker"]).ticker.astype(str).unique())
    mrow = U["Market Cap"].reindex(tick); thr = 0.0
    sec = U.Sector.reindex(tick)
    for name, tks in (("ALL", tick), ("SP500", sp500())):
        C = np.zeros((len(tks) * len(ds), len(ids)), np.uint8)
        for i, t in enumerate(tks):
            s = sec.get(t)
            if not isinstance(s, str) or (s, ds[0]) not in A.index: continue      # not in snapshot -> NR
            blk = A.loc[s].reindex(ds)
            for c in blk.columns:
                if c in jm: C[i*len(ds):(i+1)*len(ds), jm[c]] = blk[c].fillna(0).astype(np.uint8).values
            if MCAP in jm:
                raw = str(mrow.get(t, "")).replace(",", "").strip()
                try: mc = float(raw)
                except ValueError: mc = None
                col = C[i*len(ds):(i+1)*len(ds), jm[MCAP]]
                C[i*len(ds):(i+1)*len(ds), jm[MCAP]] = 0 if mc is None else np.where(col == 0, 0, np.where((col == 2) & (mc < thr), 2, 1))
        if name == "SP500":
            for i, t in enumerate(tks):
                fp = OUT / "B" / f"{t}_{y}.parquet"
                if not fp.exists(): continue
                b = pd.read_parquet(fp).pivot(index="date", columns="row_id", values="code").reindex(ds)
                for c in b.columns: C[i*len(ds):(i+1)*len(ds), jm[c]] = b[c].fillna(0).astype(np.uint8).values
        np.savez_compressed(E.CHUNKS / f"{y}__SECADD_{name}.npz", packed=E.pack(C), tickers=np.array(tks), dates=np.array(ds), ids=np.array(ids))
        json.dump(dict(year=y, subset=name, sector_map="current_backfilled", fundamentals="current Finviz Market Cap (as_restated) for " + MCAP,
                       price_source="readers/james.py own Yahoo cache", survivor_only=True, report_only_from="2026-08-06",
                       tier_b_rows_ready=(name == "SP500"), n_tickers=len(tks), n_dates=len(ds), ids_sector_only=sum(v == "SECTOR_ONLY" for v in CL.values()),
                       ids_stock_sector=sum(v == "STOCK_SECTOR" for v in CL.values())), open(E.CHUNKS / f"{y}__SECADD_{name}.json", "w"), indent=1)
        print(name, len(tks), C.shape, flush=True)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("mode"); ap.add_argument("year", type=int); ap.add_argument("--workers", type=int, default=2); a = ap.parse_args()
    if a.mode == "A":
        (OUT / "A").mkdir(exist_ok=True); ds = sessions(a.year); pool(runA, [ds[i::a.workers] for i in range(a.workers)], a.workers)
    elif a.mode == "B":
        (OUT / "B").mkdir(exist_ok=True); ds = sessions(a.year); tk = sp500(); pool(runB, [[(t, ds) for t in tk[i::a.workers]] for i in range(a.workers)], a.workers)
    elif a.mode == "assemble": assemble(a.year)
