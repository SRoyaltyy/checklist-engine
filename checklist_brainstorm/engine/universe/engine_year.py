#!/usr/bin/env python3
"""Vectorized universe engine (James+Grok, v8.2). Price source: /workspace/pricehist/universe_2020_survivors.parquet ONLY
(split-only). survivor_only=true, sector_map=current_backfilled, labels dividend_adjusted=false.
Answer for ticker-dependent BUT rows = base(date, row) [shared tier] AND stock BUT check (whole-column numpy).
Stock check uses only bars with date < D (09:25 ET cutoff; D-1 close known).
Codes: 0=NOT_READY 1=NO 2=YES, 2-bit packed (4 per byte) per (cell, id)."""
import sys, json, re, time, argparse, importlib.util, zlib
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ENG = HERE.parent
PX = "/workspace/pricehist/universe_2020_survivors.parquet"
SHEET = ENG.parent / "merged_draft_v8.2.csv"
DEPJ = ENG / "out/pilot_matrix/preburn/ticker_dependence.json"
SNAP_START = pd.Timestamp("2026-08-06")          # first Theme Radar universe snapshot
STALE_CUT = pd.Timestamp("2026-10-14")
SECT = "/workspace/theme-radar-repo/data/snapshots/current.csv"
CHUNKS = HERE / "chunks"; CHUNKS.mkdir(exist_ok=True)

def _james():
    sp = importlib.util.spec_from_file_location("jr", ENG / "readers/james.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def dep_rules():
    """For each ticker-dependent id: kind + params."""
    dep = sorted(json.load(open(DEPJ))["ticker_dependent"])
    s = pd.read_csv(SHEET, dtype=str).set_index("id").loc[dep]
    J = _james(); rules = []
    for rid, r in s.iterrows():
        d = str(r.strict_definition); ym = str(r["yes_means (bullish/bearish)"])
        if r.merge_owner == "grok-bot":
            if " BUT stock's own prior-session return" in d: rules.append((rid, "g_but", ("bull" in ym.lower(),)))
            else: rules.append((rid, "g_analyst", ()))
        else:
            m = J.BUTRE.search(d) if (" BUT " in d and "stock's own" in d) else None
            if m:
                X, cmp_, val, k, N = m.groups()
                rules.append((rid, "j_but", (ym.startswith("Bull"), float(X) if X else None, cmp_, float(val) if val else None, float(k), int(N))))
            else: rules.append((rid, "j_base", ()))
    return rules

def load_px(year):
    lo = pd.Timestamp(f"{year-1}-09-01"); hi = pd.Timestamp(f"{year}-12-31")
    p = pd.read_parquet(PX, columns=["ticker", "date", "close", "volume"], filters=[("date", ">=", lo), ("date", "<=", hi)])
    p["ticker"] = p.ticker.astype(str); p["date"] = p.date.astype("datetime64[ns]"); p = p.sort_values(["ticker", "date"]).reset_index(drop=True)
    full = pd.read_parquet(PX, columns=["ticker", "date"]); full["ticker"] = full.ticker.astype(str)
    g = full.groupby("ticker").date; tot = g.size(); first = g.min(); last = g.max()
    # bars before window start (for count of history)
    pre = full[full.date < lo].groupby("ticker").size()
    return p, tot, first, last, pre

def stock_features(p, pre, windows):
    g = p.groupby("ticker", sort=False)
    c = p.close.astype("float64"); v = p.volume.astype("float64")
    p["r"] = c / g.close.shift(1).astype("float64") - 1
    p["n"] = g.cumcount() + 1 + p.ticker.map(pre).fillna(0).astype(int)   # bars up to and incl. this bar
    for N in windows:
        p[f"va{N}"] = v.groupby(p.ticker).transform(lambda x: x.shift(1).rolling(N, min_periods=1).mean())
    p["v"] = v
    return p

def year_cells(p, tickers, sessions):
    """For every (ticker, D): last bar with date < D."""
    grid = pd.DataFrame({"ticker": np.repeat(tickers, len(sessions)), "D": np.tile(sessions, len(tickers))})
    q = p.rename(columns={"date": "bar"}).sort_values("bar")
    grid = pd.merge_asof(grid.sort_values("D"), q, left_on="D", right_on="bar", by="ticker", allow_exact_matches=False)
    return grid.sort_values(["ticker", "D"]).reset_index(drop=True)

def pack(codes):
    n, k = codes.shape; pad = (-k) % 4
    if pad: codes = np.concatenate([codes, np.zeros((n, pad), np.uint8)], 1)
    c = codes.reshape(n, -1, 4)
    return (c[..., 0] | (c[..., 1] << 2) | (c[..., 2] << 4) | (c[..., 3] << 6)).astype(np.uint8)

def unpack(b, k):
    n, m = b.shape
    out = np.empty((n, m * 4), np.uint8)
    out[:, 0::4] = b & 3
    out[:, 1::4] = (b >> 2) & 3
    out[:, 2::4] = (b >> 4) & 3
    out[:, 3::4] = (b >> 6) & 3
    return out[:, :k]

def shared_matrices(year, sessions, dep_ids):
    sh = pd.read_parquet(HERE / "shared" / f"{year}.parquet"); sh["date"] = pd.to_datetime(sh.date.astype(str))
    ind = sh[sh.tier == "ind"].pivot(index="date", columns="row_id", values="code")
    base = sh[sh.tier == "base"].pivot(index="date", columns="row_id", values="code")
    ind = ind.reindex(pd.DatetimeIndex(sessions)); base = base.reindex(index=pd.DatetimeIndex(sessions), columns=dep_ids)
    return ind, base

def compute_block(cells, base, rules, last):
    """cells: rows for a block of tickers (ticker,D,bar,r,n,va*,v). Returns (n_cells, n_dep) uint8 codes."""
    D = cells.D.values; dates = base.index.values
    di = np.searchsorted(dates, D); BV = base.values.astype(np.float32)   # NaN -> missing (small: dates x ids)
    n = cells.n.fillna(0).values; r = cells.r.values; v = cells.v.values
    lagd = (cells.D - cells.bar).dt.days.fillna(9999).values
    lastd = cells.ticker.map(last).values
    stale = (D > lastd.astype("datetime64[ns]")) & (lastd.astype("datetime64[ns]") < np.datetime64(STALE_CUT))
    out = np.zeros((len(cells), len(rules)), np.uint8); cache = {}
    tot_ok = True
    for j, (rid, kind, prm) in enumerate(rules):
        b = BV[di, j]; bnr = np.isnan(b) | (b == 0); byes = b == 2
        if kind == "j_base":
            code = np.where(bnr, 0, b).astype(np.uint8)
            code[D >= np.datetime64(SNAP_START)] = 0          # sector rows once snapshots exist: not vectorized
        elif kind == "g_analyst":
            code = np.zeros(len(cells), np.uint8)              # deferred: per-ticker Yahoo analyst history
        else:
            if prm not in cache:
                if kind == "j_but":
                    bull, X, cmp_, val, k, N = prm; va = cells[f"va{N}"].values; rr = r * 100
                    snr = (n < N + 2) | (lagd > 7) | stale
                    if X is not None: ok = (rr <= -X) if bull else (rr >= X)
                    else: ok = (rr <= val) if cmp_ == "<=" else (rr >= val)
                    ok = ok & (v >= k * va)
                else:
                    (bull,) = prm; va = cells["va20"].values
                    snr = (n < 22) | ~(va > 0) | stale
                    ok = ((r <= -0.03) if bull else (r >= 0.03)) & (v >= 2 * va)
                cache[prm if kind == "j_but" else ("g",) + prm] = (snr, ok)
                key = prm if kind == "j_but" else ("g",) + prm
            key = prm if kind == "j_but" else ("g",) + prm
            snr, ok = cache[key]
            code = np.where(bnr | snr, 0, np.where(byes & ok, 2, 1)).astype(np.uint8)
        out[:, j] = code
    return out

def run_year(year, block=400, only=None):
    t0 = time.time(); rules = dep_rules(); dep_ids = [r[0] for r in rules]
    p, tot, first, last, pre = load_px(year)
    sessions = np.sort(pd.read_parquet(PX, columns=["date"], filters=[("ticker", "=", "SPY")]).date.values.astype("datetime64[ns]"))
    sessions = sessions[(sessions >= np.datetime64(f"{year}-01-01")) & (sessions <= np.datetime64(f"{year}-12-31"))]
    ind, base = shared_matrices(year, sessions, dep_ids)
    wins = sorted({r[2][5] for r in rules if r[1] == "j_but"} | {20})
    p = stock_features(p, pre, wins)
    sect = pd.read_csv(SECT, usecols=["Ticker", "Sector"]).set_index("Ticker").Sector
    tickers = sorted(only or tot.index)
    sec_of = pd.Series(tickers, index=tickers).map(sect).fillna("Unknown")
    t1 = time.time(); stats = {}
    # shared chunk (date x ticker-free ids), once per year
    sh_ids = list(ind.columns); shc = ind.fillna(0).values.astype(np.uint8)
    np.savez_compressed(CHUNKS / f"{year}__SHARED.npz", packed=pack(shc), ids=np.array(sh_ids), dates=sessions.astype("datetime64[D]").astype(str))
    jobs = []
    for sec0 in sorted(sec_of.unique()):
        tk0 = [t for t in tickers if sec_of[t] == sec0]
        if len(tk0) <= 2000: jobs.append((sec0, tk0))
        else: jobs += [(f"{sec0}_part{k}", tk0[i:i + 2000]) for k, i in enumerate(range(0, len(tk0), 2000))]
    for sec, tk in jobs:
        parts = []
        for i in range(0, len(tk), block):
            bt = tk[i:i + block]; cells = year_cells(p[p.ticker.isin(bt)], np.array(bt), sessions)
            codes = compute_block(cells, base, rules, last); parts.append(pack(codes))
        P = np.concatenate(parts); n_cells = len(tk) * len(sessions)
        cov = {"n_tickers": len(tk), "n_cells": n_cells, "tickers_with_bars_in_year": int(p[p.ticker.isin(tk) & (p.date.dt.year == year)].ticker.nunique())}
        fn = CHUNKS / f"{year}__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.npz"
        np.savez_compressed(fn, packed=P, tickers=np.array(tk), dates=sessions.astype("datetime64[D]").astype(str), ids=np.array(dep_ids))
        meta = dict(year=year, sector=sec, layout="cells ordered ticker-major then date; codes 0=NR 1=NO 2=YES, 2-bit packed 4/byte along ids",
                    survivor_only=True, sector_map="current_backfilled", price_source=PX, price_adjust="split_only",
                    dividend_adjusted_labels=False, fundamentals="none_used", n_dep_ids=len(dep_ids),
                    deferred_ids={"grok_analyst_NR": sum(r[1] == "g_analyst" for r in rules)}, **cov)
        json.dump(meta, open(str(fn).replace(".npz", ".json"), "w"), indent=1)
        stats[sec] = (n_cells, fn.stat().st_size)
        print(f"chunk {year} {sec} tickers={len(tk)} cells={n_cells} bytes={fn.stat().st_size} t={time.time()-t1:.0f}s", flush=True)
    tc = sum(v[0] for v in stats.values()); el = time.time() - t0
    print(f"YEAR {year} cells={tc} total={el:.0f}s per_cell_us={el/tc*1e6:.1f} bytes={sum(v[1] for v in stats.values())}", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("year", type=int); ap.add_argument("--only"); a = ap.parse_args()
    run_year(a.year, only=a.only.split(",") if a.only else None)
