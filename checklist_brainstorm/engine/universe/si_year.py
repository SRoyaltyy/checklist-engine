#!/usr/bin/env python3
"""SI add-on (New Bot): FINRA bi-monthly short interest answers, 2020-2024 ONLY, per stock per session.
Rows: new New Bot rows nbx-SI-* (tags out/tags/new-bot_si_tags.csv) + other owners' rows that were NOT_READY only for SI:
 Taskforce PV-TFC-0921..0960 (X=SI/ADV, X=SI change), answered at N=1d -> id 'PV-TFC-09xx|1';
 Theme Radar Short Ratio rows OWN-TR-00793..00914 at N=1 -> 'OWN-TR-xxxxx-C|1', POS-TR-F0121..F0127 at native window -> '|20','|60','|252','|1'.
PIT: report usable from first session D with publication_date < D (FINRA publishes after the close), forward-filled to next report;
stale (D - settlement_date > 45 cal days) -> NOT_READY. Price bar = last bar < D (same as nbx_year). Codes 0=NR 1=NO 2=YES, packed as nb_year.pack.
Extreme vs own history (fixed rule): main YES = X>0 and X >= own trailing p95; BUT mirror = X <= p05 and NOT main."""
import sys, json, re, time, argparse, gc, os
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ENG = HERE.parent; sys.path.insert(0, str(HERE))
import nb_year as NB
SID = Path("/workspace/checklist_brainstorm/data/short_interest")
TAGS = ENG / "out/tags/new-bot_si_tags.csv"
NBR = ["nbx-SI-ABS-DTC-HI", "nbx-SI-ABS-DTC-LO", "nbx-SI-REL-RANK-HI", "nbx-SI-REL-RANK-LO", "nbx-SI-EXT-HI", "nbx-SI-EXT-HI-BUT",
       "nbx-SI-DIV-ADD-INTO-RALLY", "nbx-SI-DIV-COVER-RALLY", "nbx-SI-THR-UP20", "nbx-SI-THR-DN20", "nbx-SI-POS-HI", "nbx-SI-POS-LO",
       "nbx-SI-B7-SQZ-FUEL", "nbx-SI-B7-TP-FUEL"]
TF = [f"PV-TFC-{i:04d}|1" for i in range(921, 961)]
TRO = [f"OWN-TR-{i:05d}-{'C' if i % 2 else 'BUT-C'}|1" for i in (793, 794, 805, 806, 817, 818, 829, 830, 841, 842, 853, 854, 865, 866, 877, 878, 889, 890, 913, 914)]
TRP = []
for k, w in ((121, 20), (122, 20), (123, 60), (124, 60), (125, 252), (126, 252), (127, 1)):
    TRP += [f"POS-TR-F0{k}-C|{w}", f"POS-TR-F0{k}-BUT-C|{w}"]
IDS = NBR + TF + TRO + TRP
STALE = 45
def norm(s): return s.astype(str).str.strip().str.replace(r"[./ ]", "-", regex=True)
def si_table(year, tickers):
    parts = []
    for y in range(max(2020, year - 2), year + 1):   # never reads 2025-26
        x = pd.read_parquet(SID / f"finra_si_{y}.parquet"); x["ticker"] = norm(x.symbol); parts.append(x[x.ticker.isin(tickers)])
    x = pd.concat(parts).drop(columns=["symbol", "market"])
    x["pub"] = x.publication_date.astype("datetime64[ns]"); x["settle"] = x.settlement_date.astype("datetime64[ns]")
    x = x.sort_values(["ticker", "settle"]).drop_duplicates(["ticker", "settle"], keep="last")
    return x[["ticker", "pub", "settle", "current_short_qty", "previous_short_qty", "avg_daily_volume", "days_to_cover"]]
def g_roll(s, tk, n, fn, q=None, minp=None):
    r = s.groupby(tk).transform(lambda v: (v.shift(1).rolling(n, min_periods=minp or n).quantile(q) if fn == "q" else getattr(v.shift(1).rolling(n, min_periods=minp or n), fn)()))
    return r
def run_year(year, block=500, only=None):
    assert 2020 <= year <= 2024, "SI add-on is 2020-2024 only"
    t0 = time.time(); col = {r: j for j, r in enumerate(IDS)}
    spy = NB.sessions_all(); sess = spy.index.values
    ys = sess[(sess >= np.datetime64(f"{year}-01-01")) & (sess <= np.datetime64(f"{year}-12-31"))]
    hs = sess[(sess >= np.datetime64(f"{max(2020, year - 2)}-01-01")) & (sess <= ys[-1])]
    last = pd.read_parquet(NB.CACHE / "last.parquet").date
    funds = set(pd.read_csv(NB.CACHE / "fund_exclusion_tickers.csv").ticker)
    tickers = sorted(only or [t for t in last.index if t not in funds])
    cur = pd.read_csv(NB.SECT, usecols=["Ticker", "Sector", "Industry"]).set_index("Ticker")
    sec_of = pd.Series(tickers, index=tickers).map(cur.Sector).fillna("Unknown")
    hi = pd.Timestamp(ys[-1]); blocks = []; RV = []
    for i in range(0, len(tickers), block):
        bt = tickers[i:i + block]
        p = pd.read_parquet(NB.PX, columns=["ticker", "date", "close", "volume"], filters=[("ticker", "in", bt), ("date", "<", hi), ("date", ">=", pd.Timestamp(f"{max(2020, year - 2) - 1}-10-01"))])
        p["ticker"] = p.ticker.astype(str); p["date"] = p.date.astype("datetime64[ns]"); p = p.sort_values(["ticker", "date"]).reset_index(drop=True)
        g = p.groupby("ticker"); c = p.close.astype("float64"); v = p.volume.astype("float64")
        B = pd.DataFrame({"ticker": p.ticker, "bar": p.date, "c": c})
        B["r1"] = c / g.close.shift(1) - 1; B["r10"] = c / g.close.shift(10) - 1; B["r20"] = c / g.close.shift(20) - 1
        B["hi20"] = g.close.transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
        B["rv"] = v / v.groupby(p.ticker).transform(lambda s: s.rolling(50, min_periods=50).mean()).where(lambda z: z > 0)
        B["rvp"] = B.rv.groupby(p.ticker).shift(1)
        grid = pd.DataFrame({"ticker": np.repeat(bt, len(hs)), "D": np.tile(hs, len(bt))})
        grid = pd.merge_asof(grid.sort_values("D"), B.sort_values("bar"), left_on="D", right_on="bar", by="ticker", allow_exact_matches=False)
        S = si_table(year, set(bt)).sort_values("pub")
        grid = pd.merge_asof(grid.sort_values("D"), S, left_on="D", right_on="pub", by="ticker", allow_exact_matches=False).sort_values(["ticker", "D"]).reset_index(drop=True)
        del p, B, S
        lag = (grid.D - grid.bar).dt.days.fillna(9999).values; lastd = grid.ticker.map(last).values.astype("datetime64[ns]")
        ok = grid.bar.notna().values & (lag <= 7) & ~((grid.D.values > lastd) & (lastd < NB.STALE_CUT))
        fresh = grid.settle.notna().values & ((grid.D - grid.settle).dt.days.values <= STALE)
        tk = grid.ticker
        si = grid.current_short_qty.astype("float64").where(fresh); psi = grid.previous_short_qty.astype("float64").where(fresh)
        adv = grid.avg_daily_volume.astype("float64").where(fresh)
        dtc = grid.days_to_cover.astype("float64").where(fresh)
        siadv = (si / adv.where(adv > 0))
        chg = (si / psi.where(psi > 0) - 1)
        F = {"dtc": dtc, "siadv": siadv, "chg": chg, "si": si}
        sh = lambda s, n=1: s.groupby(tk).shift(n)
        H = {}
        for nm, X in (("siadv", siadv), ("chg", chg)):
            dX = X - sh(X); H[nm] = dict(X=X, dX=dX, Xp=sh(X), q95=g_roll(X, tk, 252, "q", .95), q05=g_roll(X, tk, 252, "q", .05),
                                        sd=g_roll(dX, tk, 252, "std"), sma3=X.groupby(tk).transform(lambda s: s.rolling(3, min_periods=3).mean()),
                                        dX1=sh(dX), dX2=sh(dX, 2))
            H[nm]["sma3p"] = sh(H[nm]["sma3"])
        dd = dtc - sh(dtc); dtcp = sh(dtc)
        d60q95 = g_roll(dtc, tk, 60, "q", .95); d60q05 = g_roll(dtc, tk, 60, "q", .05); d252q95 = g_roll(dtc, tk, 252, "q", .95); d252q05 = g_roll(dtc, tk, 252, "q", .05)
        posw = {}
        for w in (20, 60, 252):
            mn = dtc.groupby(tk).transform(lambda s: s.rolling(w, min_periods=w).min()); mx = dtc.groupby(tk).transform(lambda s: s.rolling(w, min_periods=w).max())
            posw[w] = (dtc - mn) / (mx - mn).where(mx > mn)
        smn = si.groupby(tk).transform(lambda s: s.rolling(252, min_periods=252).min()); smx = si.groupby(tk).transform(lambda s: s.rolling(252, min_periods=252).max())
        sipos = (si - smn) / (smx - smn).where(smx > smn)
        r1, r10, r20, rv, rvp, cc, hi20 = (grid[k].astype("float64") for k in ("r1", "r10", "r20", "rv", "rvp", "c", "hi20"))
        m = np.isin(grid.D.values, ys); idx = np.where(m)[0]
        out = {}
        def put(rid, y, rd):
            rd = np.asarray(rd, bool)[idx] & ok[idx]; y = np.asarray(pd.Series(y).fillna(False), bool)[idx]
            out[rid] = np.where(rd, np.where(y, 2, 1), 0).astype(np.uint8)
        # ---- New Bot rows (six lenses + bucket-7 flags)
        put("nbx-SI-ABS-DTC-HI", dtc >= 7, dtc.notna()); put("nbx-SI-ABS-DTC-LO", dtc <= 1.5, dtc.notna())
        main = (dtc > 0) & (dtc >= d252q95); rdx = dtc.notna() & d252q95.notna() & d252q05.notna()
        put("nbx-SI-EXT-HI", main, rdx); put("nbx-SI-EXT-HI-BUT", (dtc <= d252q05) & ~main, rdx)
        rdd = chg.notna() & r10.notna()
        put("nbx-SI-DIV-ADD-INTO-RALLY", (chg > 0) & (r10 > 0), rdd); put("nbx-SI-DIV-COVER-RALLY", (chg < 0) & (r10 > 0), rdd)
        put("nbx-SI-THR-UP20", chg >= 0.2, chg.notna()); put("nbx-SI-THR-DN20", chg <= -0.2, chg.notna())
        put("nbx-SI-POS-HI", sipos >= 0.9, sipos.notna()); put("nbx-SI-POS-LO", sipos <= 0.1, sipos.notna())
        put("nbx-SI-B7-SQZ-FUEL", (dtc >= 5) & (chg > 0) & (cc > hi20), dtc.notna() & chg.notna() & hi20.notna())
        put("nbx-SI-B7-TP-FUEL", (dtc >= 5) & (chg <= -0.2) & (r20 >= 0.15), dtc.notna() & chg.notna() & r20.notna())
        # ---- Taskforce rows (N=1d)
        for base, nm, hiT, loT in ((921, "siadv", 8, 1), (941, "chg", 0.2, -0.2)):
            h = H[nm]; X, dX = h["X"], h["dX"]; P = lambda k: f"PV-TFC-{base + k:04d}|1"
            put(P(0), X >= hiT, X.notna()); put(P(1), X <= loT, X.notna())
            mn_ = (X > 0) & (X >= h["q95"]); rq = X.notna() & h["q95"].notna() & h["q05"].notna()
            put(P(2), mn_, rq); put(P(3), (X <= h["q05"]) & ~mn_, rq)
            rs = dX.notna() & h["sd"].notna()
            put(P(4), (dX > 0) & (dX.abs() >= 0.5 * h["sd"]), rs); put(P(5), (dX < 0) & (dX.abs() >= 0.5 * h["sd"]), rs)
            rr = dX.notna() & r1.notna(); put(P(6), (dX > 0) & (r1 < 0), rr); put(P(7), (dX < 0) & (r1 > 0), rr)
            rl = dX.notna() & rv.notna(); put(P(10), (dX > 0) & (rv < 0.8), rl); put(P(11), (dX > 0) & (rv >= 1.5), rl)
            rc = h["sma3"].notna() & h["sma3p"].notna() & h["Xp"].notna()
            put(P(16), (h["Xp"] <= h["sma3p"]) & (X > h["sma3"]), rc); put(P(17), (h["Xp"] >= h["sma3p"]) & (X < h["sma3"]), rc)
            r3 = dX.notna() & h["dX1"].notna() & h["dX2"].notna()
            put(P(18), (dX > 0) & (h["dX1"] > 0) & (h["dX2"] > 0), r3); put(P(19), (dX < 0) & (h["dX1"] < 0) & (h["dX2"] < 0), r3)
        # ---- Theme Radar Short Ratio rows (FINRA days_to_cover as the short ratio)
        T = lambda n, b=False: f"OWN-TR-{n:05d}-{'BUT-C' if b else 'C'}|1"
        put(T(793), dtc >= 7, dtc.notna()); put(T(794, 1), dtc <= 1, dtc.notna())
        mn_ = (dtc > 0) & (dtc >= d60q95); rq = dtc.notna() & d60q95.notna() & d60q05.notna()
        put(T(805), mn_, rq); put(T(806, 1), (dtc <= d60q05) & ~mn_, rq)
        rel = dtc / dtcp.where(dtcp > 0) - 1; put(T(817), rel >= 0.10, rel.notna()); put(T(818, 1), rel <= -0.10, rel.notna())
        rx = dtc.notna() & dtcp.notna(); put(T(829), (dtcp < 7) & (dtc >= 7), rx); put(T(830, 1), (dtcp >= 1) & (dtc < 1), rx)
        put(T(841), dd > 0, dd.notna()); put(T(842, 1), dd < 0, dd.notna())
        put(T(853), (r1 < 0) & (dd > 0), dd.notna() & r1.notna()); put(T(854, 1), (r1 > 0) & (dd < 0), dd.notna() & r1.notna())
        drv = rv - rvp; put(T(865), (drv < 0) & (dd > 0), dd.notna() & drv.notna()); put(T(866, 1), (drv > 0) & (dd < 0), dd.notna() & drv.notna())
        for k, w in ((121, 20), (123, 60), (125, 252)):
            pw = posw[w]; put(f"POS-TR-F0{k}-C|{w}", pw >= 0.75, pw.notna()); put(f"POS-TR-F0{k}-BUT-C|{w}", pw <= 0.25, pw.notna())
            put(f"POS-TR-F0{k+1}-C|{w}", pw >= 0.90, pw.notna()); put(f"POS-TR-F0{k+1}-BUT-C|{w}", pw <= 0.10, pw.notna())
        C = np.zeros((len(idx), len(IDS)), np.uint8)
        for rid_, v_ in out.items(): C[:, col[rid_]] = v_
        okk = ok[idx]
        rvc = pd.DataFrame({"dtc": dtc.values[idx], "siadv": siadv.values[idx], "chg": chg.values[idx],
                            "d_siadv": H["siadv"]["dX"].values[idx], "d_chg": H["chg"]["dX"].values[idx]}).astype("float32")
        rvc = rvc.where(np.broadcast_to(okk[:, None], rvc.shape)); rvc["ticker"] = grid.ticker.values[idx]; rvc["D"] = grid.D.values[idx]
        RV.append(rvc); blocks.append((bt, NB.pack(C)))
        del grid, F, H, C; gc.collect(); print(f"  block {i//block} t={time.time()-t0:.0f}s", flush=True)
    A = pd.concat(RV, ignore_index=True); A["sector"] = A.ticker.map(sec_of); A["industry"] = A.ticker.map(cur.Industry)
    known = A.sector != "Unknown"; rc = {}
    def rk(v, by, asc): return v.groupby(by).rank(method="min", ascending=asc, pct=True)
    def code(y, rd): return np.where(rd, np.where(np.asarray(y.fillna(False), bool), 2, 1), 0).astype(np.uint8)
    for nm, base in (("siadv", 921), ("chg", 941)):
        X = A[nm]; rd = X.notna() & known; P = lambda k: f"PV-TFC-{base + k:04d}|1"
        rc[P(12)] = code(rk(X, [A.D, A.sector], False) <= .10, rd); rc[P(13)] = code(rk(X, [A.D, A.sector], True) <= .10, rd)
        rc[P(14)] = code(rk(X, A.D, False) <= .10, X.notna()); rc[P(15)] = code(rk(X, A.D, True) <= .10, X.notna())
        dX = A["d_" + nm]; med = dX.groupby([A.D, A.sector]).transform("median"); rdm = dX.notna() & med.notna() & known
        rc[P(8)] = code((dX > 0) & (med < 0), rdm); rc[P(9)] = code((dX < 0) & (med > 0), rdm)
    X = A.dtc; rd = X.notna() & known
    rc["OWN-TR-00877-C|1"] = code(rk(X, [A.D, A.sector], False) <= .10, rd); rc["OWN-TR-00878-BUT-C|1"] = code(rk(X, [A.D, A.sector], True) <= .10, rd)
    rdi = X.notna() & A.industry.notna()
    rc["OWN-TR-00889-C|1"] = code(rk(X, [A.D, A.industry], False) <= .10, rdi); rc["OWN-TR-00890-BUT-C|1"] = code(rk(X, [A.D, A.industry], True) <= .10, rdi)
    rc["OWN-TR-00913-C|1"] = code(rk(X, A.D, False) <= .10, X.notna()); rc["OWN-TR-00914-BUT-C|1"] = code(rk(X, A.D, True) <= .10, X.notna())
    ps = rk(X, [A.D, A.sector], True)   # percentile within sector (1 = highest)
    rc["POS-TR-F0127-C|1"] = code(ps >= .90, rd); rc["POS-TR-F0127-BUT-C|1"] = code(ps <= .10, rd)
    mk = (rk(X, A.D, False) <= .10) & (rk(X, [A.D, A.sector], False) <= .10); ml = (rk(X, A.D, True) <= .10) & (rk(X, [A.D, A.sector], True) <= .10)
    rc["nbx-SI-REL-RANK-HI"] = code(mk, rd); rc["nbx-SI-REL-RANK-LO"] = code(ml, rd)
    del A, RV; off = 0; res = {}
    for bt, P_ in blocks:
        n = len(bt) * len(ys); C = NB.unpack(P_, len(IDS))
        for rid_, v_ in rc.items(): C[:, col[rid_]] = v_[off:off + n]
        off += n; res[tuple(bt)] = NB.pack(C)
    return dict(ids=IDS, ys=ys, tickers=tickers, sec_of=sec_of, res=res, secs=time.time() - t0)
def write_year(year, R):
    ids, ys, sec_of = R["ids"], R["ys"], R["sec_of"]; allC = {}
    for bt, C in R["res"].items():
        for j, t in enumerate(bt): allC[t] = C[j * len(ys):(j + 1) * len(ys)]
    jobs = []
    for sec0 in sorted(sec_of.unique()):
        tk0 = [t for t in R["tickers"] if sec_of[t] == sec0]
        jobs += [(sec0, tk0)] if len(tk0) <= 2000 else [(f"{sec0}_part{k}", tk0[i:i + 2000]) for k, i in enumerate(range(0, len(tk0), 2000))]
    cov = np.zeros((len(ids), 3), np.int64); dstr = ys.astype("datetime64[D]").astype(str)
    sha = open(str(TAGS) + ".sha256").read().split()[0]
    for sec, tk in jobs:
        P = np.concatenate([allC[t] for t in tk]); U = NB.unpack(P, len(ids))
        for k in range(3): cov[:, k] += (U == k).sum(0)
        df = pd.DataFrame({"ticker": np.repeat(tk, len(ys)), "date": np.tile(dstr, len(tk)), "packed": [bytes(x) for x in P]})
        fn = NB.CHUNKS / f"{year}__SI__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.parquet"; df.to_parquet(fn, index=False)
        json.dump(dict(year=year, sector=sec, layout="rows ticker-major then date; packed = 2-bit codes 0=NR 1=NO 2=YES, 4/byte along ids (engine_year.pack)",
                       addon="SI: FINRA bi-monthly short interest (New Bot rows nbx-SI-*, Taskforce PV-TFC-0921..0960 at N=1d, Theme Radar Short Ratio rows)",
                       survivor_only=True, sector_map="current_backfilled", source="FINRA equity short interest (data/short_interest/finra_si_{y}.parquet)",
                       point_in_time="report usable from first session D with publication_date < D, forward-filled; stale if D - settlement_date > 45 days -> NR; price bar = last session < D",
                       ext_rule="main YES = X>0 and X >= own trailing p95; BUT = X <= p05 and NOT main",
                       other_owner_ids_note="ids with '|N' keep owner row ids; Theme Radar short ratio = FINRA days_to_cover (FINRA floors it at 1.00); Taskforce X=SI/ADV uses FINRA avg_daily_volume",
                       si_tags_sha256=sha, n_ids=len(ids), ids=ids, n_tickers=len(tk), n_cells=len(df)),
                  open(str(fn).replace(".parquet", ".json"), "w"), indent=1)
    pd.DataFrame(cov, columns=["nr", "no", "yes"], index=ids).to_csv(NB.CHUNKS / f"{year}__SI_coverage.csv")
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("year", type=int); ap.add_argument("--only"); a = ap.parse_args()
    R = run_year(a.year, only=a.only.split(",") if a.only else None)
    if not a.only: write_year(a.year, R)
    else:
        import pickle; pickle.dump(R, open(f"/tmp/si_test_{a.year}.pkl", "wb"))
    print(f"YEAR {a.year} secs={R['secs']:.0f}", flush=True)
