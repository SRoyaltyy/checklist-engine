#!/usr/bin/env python3
"""NBX add-on: New Bot halt (NB-039) + Nasdaq Reg SHO threshold (NB-056) rows (12+12, previously NOT_READY) and FINRA
short-volume add-on rows (out/tags/new-bot_finra_tags.csv, sha256 frozen). Same layout/pack as nb_year. Does not touch NB files.
Point-in-time: answer for session D uses bar = last price bar < D (prior session). Halt event on bar b = any Nasdaq-feed halt
record with halt_date b. Reg SHO event on bar b = ticker on Nasdaq threshold file dated b; ready only for current Finviz
Exchange == NASD (survivor listing, current_backfilled). FINRA values on bar b = CNMS file dated b (published evening of b)."""
import sys, json, re, time, argparse, gc, os
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ENG = HERE.parent; sys.path.insert(0, str(HERE))
import nb_year as NB
D = Path("/workspace/checklist_brainstorm/data")
FT = ENG / "out/tags/new-bot_finra_tags.csv"
def norm(s): return s.astype(str).str.strip().str.replace(r"[./ ]", "-", regex=True)
def ev_tables():
    h = pd.read_parquet(D / "halts_regsho/nasdaq_halts_2020_2026.parquet", columns=["halt_date", "symbol"])
    h = pd.DataFrame({"ticker": norm(h.symbol), "date": pd.to_datetime(h.halt_date, format="%m/%d/%Y", errors="coerce")}).dropna().drop_duplicates()
    t = pd.read_parquet(D / "halts_regsho/nasdaq_regsho_threshold_2020_2026.parquet", columns=["date", "symbol"])
    t = pd.DataFrame({"ticker": norm(t.symbol), "date": t.date.astype("datetime64[ns]")}).drop_duplicates()
    return h, t
def finra(year, tickers):
    parts = []
    for y in range(year - 2, year + 1):
        f = D / f"finra_shvol/finra_shvol_{y}.parquet"
        if f.exists():
            x = pd.read_parquet(f); x["ticker"] = norm(x.symbol); x = x[x.ticker.isin(tickers)]; parts.append(x.drop(columns="symbol"))
    x = pd.concat(parts).sort_values(["ticker", "date"]).reset_index(drop=True); x["date"] = x.date.astype("datetime64[ns]")
    x = x.drop_duplicates(["ticker", "date"], keep="last")
    tk = x.ticker; sr = x.short_ratio.astype("float64")
    def roll(s, n, fn): return s.groupby(tk).transform(lambda v: getattr(v.shift(1).rolling(n, min_periods=n), fn)())
    F = pd.DataFrame({"ticker": tk, "date": x.date, "sr": sr})
    for n in (20, 60):
        m, s = roll(sr, n, "mean"), roll(sr, n, "std"); F[f"z{n}"] = (sr - m) / s.where(s > 0)
    F["sv"] = x.short_volume.astype("float64"); F["svm20"] = roll(F.sv, 20, "mean")
    F["exr"] = (x.short_exempt_volume / x.short_volume.where(x.short_volume > 0)).astype("float64")
    F["srp"] = sr.groupby(tk).shift(1)
    F["sr5"] = sr.groupby(tk).transform(lambda v: v.rolling(5, min_periods=5).mean()); F["sr5p"] = F.sr5.groupby(tk).shift(5)
    def pct(v):
        a = v.values; out = np.full(len(a), np.nan)
        for i in range(252, len(a)):
            w = a[i - 252:i]; w = w[~np.isnan(w)]
            if len(w) == 252 and not np.isnan(a[i]): out[i] = (w <= a[i]).mean() if True else 0
        return pd.Series(out, index=v.index)
    F["pct"] = sr.groupby(tk, group_keys=False).apply(pct)
    F["lo"] = sr.groupby(tk).transform(lambda v: v.shift(1).rolling(252, min_periods=252).quantile(0.0))
    return F
def finra_codes(F):
    """codes per FINRA row id on F rows (needs price cols c, c5 merged)."""
    out = {}
    def put(rid, y, rd): out["nbx-FINRA-" + rid] = np.where(rd, np.where(np.asarray(y, bool), 2, 1), 0).astype(np.uint8)
    sr = F.sr; ok = sr.notna()
    put("FS-ABS-HI", sr >= 0.60, ok); put("FS-ABS-LO", sr <= 0.30, ok)
    for n in (20, 60):
        z = F[f"z{n}"]; put(f"FS-Z{n}-HI", z >= 1, z.notna()); put(f"FS-Z{n}-LO", z <= -1, z.notna())
    z = F.z60
    put("FS-OUT2-HI", z >= 2, z.notna()); put("FS-OUT2-LO", z <= -2, z.notna()); put("FS-OUT3-HI", z >= 3, z.notna()); put("FS-OUT3-LO", z <= -3, z.notna())
    rdd = F.c.notna() & F.c5.notna() & F.sr5.notna() & F.sr5p.notna()
    put("FS-DIV-UP", (F.c > F.c5) & (F.sr5 > F.sr5p), rdd); put("FS-DIV-DN", (F.c < F.c5) & (F.sr5 < F.sr5p), rdd)
    put("FS-THR-SVSPIKE", F.sv >= 2 * F.svm20, F.svm20.notna() & (F.svm20 > 0))
    put("FS-THR-X50", (F.srp < 0.5) & (sr >= 0.5), F.srp.notna() & ok)
    put("FS-THR-EXEMPT", F.exr >= 0.05, F.exr.notna())
    p = F.pct; put("FS-PCT-HI", p >= 0.95, p.notna()); put("FS-PCT-LO", p <= 0.05, p.notna()); put("FS-PCT-UPPER", p >= 0.80, p.notna())
    return out
def ev_codes(p, E, Ev, rows, med, spy):
    """copy of nb_year T20/W0 event logic for one indicator."""
    tk = p.ticker; g = p.groupby("ticker", sort=False); c = p.close.astype("float64")
    f3 = g.close.shift(-3).astype("float64") / c - 1
    spf3 = (spy.shift(-3) / spy - 1).reindex(p.date.values).values
    mm = p[["industry", "date"]].merge(med, on=["industry", "date"], how="left"); imf3 = mm.f3.values.astype("float64")
    def roll(s, n, fn): return s.groupby(tk).transform(lambda x: getattr(x.rolling(n, min_periods=n), fn)())
    e = E.fillna(False).astype(bool); ev = Ev; ef = e.astype(float).where(ev); cnt = roll(ef, 20, "sum")
    out = {}; rnk = {}
    for _, r in rows.iterrows():
        L, b, rid_ = r.lens, r.but, r.id
        if L == "W0-EVT": y = e & False if b else e; rd = ev
        elif L == "T20-CNT": y = (cnt == 0) if b else (cnt >= 2); rd = cnt.notna()
        elif L == "T20-EXT":
            # EXT fix 2026-10-22: main YES needs cnt>0 & cnt>=p95 (so cnt>p95 when p95==0); BUT = sheet cnt<=p05 AND NOT main (never both YES)
            q95 = cnt.groupby(tk).transform(lambda s: s.expanding(250).quantile(0.95)); main = (cnt > 0) & (cnt >= q95)
            if b: q = cnt.groupby(tk).transform(lambda s: s.expanding(250).quantile(0.05)); y = (cnt <= q) & ~main
            else: q = q95; y = main
            rd = q.notna() & q95.notna()
        elif L in ("T20-RXS", "T20-RXM"):
            ref = imf3 if L == "T20-RXS" else spf3
            d = pd.Series(np.where(e.values, f3.values - ref, np.nan), index=p.index)
            dv = pd.Series(np.where(e.values & np.isnan(ref), 1.0, 0.0), index=p.index)
            d3 = d.groupby(tk).shift(3); bad = roll(dv.groupby(tk).shift(3), 17, "sum")
            sm_ = roll(d3.fillna(0), 17, "sum"); n_ = roll(d3.notna().astype(float), 17, "sum"); mean = sm_ / n_.where(n_ > 0)
            y = ((mean <= -0.03) if b else (mean >= 0.03)).fillna(False); rd = n_.notna() & (bad == 0) & cnt.notna()
            if L == "T20-RXS": rd = rd & p.industry.notna()
        elif L == "T20-RNK": rnk[rid_] = cnt.where(cnt.notna()); continue
        out[rid_] = np.where(rd.values, np.where(np.asarray(y, dtype=bool), 2, 1), 0).astype(np.uint8)
    return out, rnk
def run_year(year, only=None, block=500):
    t0 = time.time(); rows, _ = NB.load_rows(); rows = rows[rows.ind.isin(["NB-039", "NB-056"])].reset_index(drop=True)
    ftags = pd.read_csv(FT); ids = list(rows.id) + list(ftags.row_id); col = {r: j for j, r in enumerate(ids)}
    spy = NB.sessions_all(); sess = spy.index.values
    ys = sess[(sess >= np.datetime64(f"{year}-01-01")) & (sess <= np.datetime64(f"{year}-12-31"))]
    med = NB.global_tables(spy); last = pd.read_parquet(NB.CACHE / "last.parquet").date
    funds = set(pd.read_csv(NB.CACHE / "fund_exclusion_tickers.csv").ticker)
    tickers = sorted(only or [t for t in last.index if t not in funds])
    cur = pd.read_csv(NB.SECT, usecols=["Ticker", "Sector", "Industry", "Exchange"]).set_index("Ticker")
    sec_of = pd.Series(tickers, index=tickers).map(cur.Sector).fillna("Unknown")
    H, T = ev_tables(); hset = set(zip(H.ticker, H.date)); tset = set(zip(T.ticker, T.date)); tdates = set(T.date)
    hdates = set(pd.read_parquet(D / "halts_regsho/nasdaq_halts_2020_2026.parquet", columns=["file_date"]).file_date.pipe(pd.to_datetime, format="%Y%m%d"))
    hi = pd.Timestamp(ys[-1]); blocks = []; RV = []
    rnk_ids = list(rows[rows.lens == "T20-RNK"].id)
    for i in range(0, len(tickers), block):
        bt = tickers[i:i + block]
        p = pd.read_parquet(NB.PX, columns=["ticker", "date", "close"], filters=[("ticker", "in", bt), ("date", "<", hi)])
        p["ticker"] = p.ticker.astype(str); p["date"] = p.date.astype("datetime64[ns]"); p = p.sort_values(["ticker", "date"]).reset_index(drop=True)
        p["industry"] = p.ticker.map(cur.Industry); pc = p.groupby("ticker").close.shift(1)
        key = list(zip(p.ticker, p.date))
        Eh = pd.Series([k in hset for k in key], index=p.index); Evh = pc.notna() & p.date.isin(hdates)
        Et = pd.Series([k in tset for k in key], index=p.index)
        Evt = pc.notna() & p.date.isin(tdates) & (p.ticker.map(cur.Exchange) == "NASD")
        codes = {}; rv = {}
        for ind_, E, Ev in (("NB-039", Eh, Evh), ("NB-056", Et, Evt)):
            o, r = ev_codes(p, E, Ev, rows[rows.ind == ind_], med, spy); codes.update(o); rv.update(r)
        F = finra(year, set(bt))
        p["c5"] = p.groupby("ticker").close.shift(5)
        Fm = p[["ticker", "date", "close", "c5"]].rename(columns={"close": "c"}).merge(F, on=["ticker", "date"], how="left")
        codes.update(finra_codes(Fm)); del F, Fm
        keys = p[["ticker", "date"]].assign(bi=np.arange(len(p)))
        grid = pd.DataFrame({"ticker": np.repeat(bt, len(ys)), "D": np.tile(ys, len(bt))})
        q = keys.rename(columns={"date": "bar"}).sort_values("bar")
        grid = pd.merge_asof(grid.sort_values("D"), q, left_on="D", right_on="bar", by="ticker", allow_exact_matches=False).sort_values(["ticker", "D"]).reset_index(drop=True)
        bi = grid.bi.values; has = ~np.isnan(bi); bi = np.where(has, bi, 0).astype(int)
        lag = (grid.D - grid.bar).dt.days.fillna(9999).values; lastd = grid.ticker.map(last).values.astype("datetime64[ns]")
        ok = has & (lag <= 7) & ~((grid.D.values > lastd) & (lastd < NB.STALE_CUT))
        C = np.zeros((len(grid), len(ids)), np.uint8)
        for rid_, v in codes.items(): C[:, col[rid_]] = np.where(ok, v[bi], 0)
        rvc = pd.DataFrame({k: np.where(ok, v.values[bi], np.nan).astype("float32") for k, v in rv.items()})
        rvc["ticker"] = grid.ticker.values; rvc["D"] = grid.D.values; RV.append(rvc); blocks.append((bt, NB.pack(C)))
        del p, codes, C, grid; gc.collect(); print(f"  block {i//block} t={time.time()-t0:.0f}s", flush=True)
    RVa = pd.concat(RV, ignore_index=True); RVa["sector"] = RVa.ticker.map(sec_of); rcode = {}
    for rid_ in rnk_ids:
        v = RVa[rid_]; but = rid_.endswith("-BUT"); asc = but
        m = v.groupby(RVa.D).rank(method="min", ascending=asc, pct=True); s_ = v.groupby([RVa.D, RVa.sector]).rank(method="min", ascending=asc, pct=True)
        rcode[rid_] = np.where(v.notna() & (RVa.sector != "Unknown"), np.where((m <= 0.10) & (s_ <= 0.10), 2, 1), 0).astype(np.uint8)
    del RVa, RV; off = 0; res = {}
    for bt, P in blocks:
        n = len(bt) * len(ys); C = NB.unpack(P, len(ids))
        for rid_ in rnk_ids: C[:, col[rid_]] = rcode[rid_][off:off + n]
        off += n; res[tuple(bt)] = NB.pack(C)
    nr = {r: "Reg SHO list = Nasdaq-listed only (Finviz Exchange NASD); other listings NOT_READY" for r in rows[rows.ind == "NB-056"].id}
    return dict(ids=ids, ys=ys, tickers=tickers, sec_of=sec_of, res=res, nr_reason=nr, secs=time.time() - t0)
def write_year(year, R):
    ids, ys, sec_of = R["ids"], R["ys"], R["sec_of"]; allC = {}
    for bt, C in R["res"].items():
        for j, t in enumerate(bt): allC[t] = C[j * len(ys):(j + 1) * len(ys)]
    jobs = []
    for sec0 in sorted(sec_of.unique()):
        tk0 = [t for t in R["tickers"] if sec_of[t] == sec0]
        jobs += [(sec0, tk0)] if len(tk0) <= 2000 else [(f"{sec0}_part{k}", tk0[i:i + 2000]) for k, i in enumerate(range(0, len(tk0), 2000))]
    cov = np.zeros((len(ids), 3), np.int64); dstr = ys.astype("datetime64[D]").astype(str)
    sha = open(str(FT) + ".sha256").read().split()[0]
    for sec, tk in jobs:
        P = np.concatenate([allC[t] for t in tk]); U = NB.unpack(P, len(ids))
        for k in range(3): cov[:, k] += (U == k).sum(0)
        df = pd.DataFrame({"ticker": np.repeat(tk, len(ys)), "date": np.tile(dstr, len(tk)), "packed": [bytes(x) for x in P]})
        fn = NB.CHUNKS / f"{year}__NBX__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.parquet"; df.to_parquet(fn, index=False)
        json.dump(dict(year=year, sector=sec, layout="rows ticker-major then date; packed = 2-bit codes 0=NR 1=NO 2=YES, 4/byte along ids (engine_year.pack)",
                       addon="NBX: NB-039 halts + NB-056 Nasdaq Reg SHO + FINRA short volume", survivor_only=True, sector_map="current_backfilled",
                       sources=dict(halts="Nasdaq trade-halt feed per date 2020-01-02..2026-10-21", regsho="Nasdaq nasdaqth{date}.txt", finra="FINRA CNMSshvol{date}.txt"),
                       point_in_time="bar = last session < D; event/values dated bar", finra_tags_sha256=sha,
                       n_ids=len(ids), ids=ids, nr_reasons=R["nr_reason"], n_tickers=len(tk), n_cells=len(df)), open(str(fn).replace(".parquet", ".json"), "w"), indent=1)
    pd.DataFrame(cov, columns=["nr", "no", "yes"], index=ids).to_csv(NB.CHUNKS / f"{year}__NBX_coverage.csv")
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("year", type=int); ap.add_argument("--only"); a = ap.parse_args()
    R = run_year(a.year, only=a.only.split(",") if a.only else None)
    if not a.only: write_year(a.year, R)
    else:
        import pickle; pickle.dump(R, open(f"/tmp/nbx_test_{a.year}.pkl", "wb"))
    print(f"YEAR {a.year} secs={R['secs']:.0f}", flush=True)
