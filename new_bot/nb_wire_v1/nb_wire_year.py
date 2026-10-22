#!/usr/bin/env python3
"""New Bot (merge_owner=new-bot) universe engine, v8.2 sheet. Split-only prices ONLY (universe_2020_survivors.parquet),
SPY from etf_2015.parquet. survivor_only=true, sector_map=current_backfilled (Finviz Sector/Industry from current.csv used
for every year). Answer for session D uses only bars with date < D (last bar < D, lag<=7d, not stale) and calendar facts
for D itself (OPX rows). Codes 0=NOT_READY 1=NO 2=YES, 2-bit packed 4/byte along ids (same pack() as engine_year.py).
Output: chunks/{y}__NB__{sector}.parquet (ticker,date,packed) + .json sidecar (ids, NR reasons)."""
import sys, json, re, time, argparse, gc
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ENG = HERE.parent
PX = "/workspace/pricehist/universe_2020_survivors.parquet"; ETF = "/workspace/pricehist/etf_2015.parquet"
SHEET = Path("/workspace/checklist_brainstorm/merged_draft_v8.2.csv"); EXCL = Path("/workspace/checklist_brainstorm/engine/out/tags/new-bot_excluded_inference.csv")
SECT = "/workspace/theme-radar-shadowlock/data/snapshots/current.csv"; SNAPD = Path("/workspace/theme-radar-repo/data/snapshots")
CHUNKS = HERE / "chunks"; CACHE = Path("/workspace/checklist_brainstorm/engine/universe/nb_cache")
EARN_PQ = "/workspace/checklist_brainstorm/data/earnings/nasdaq_calendar_2020_2024.parquet"
WIRE_IND = ["NB-014", "NB-022", "NB-024", "NB-091"]
STALE_CUT = np.datetime64("2026-10-14")

# ---------- indicator catalogue ----------
NR_IND = {  # indicator -> reason (never guessed)
 "NB-027": "needs foreign home-listing tickers + FX - not in files",
 "NB-028": "needs NG=F/uranium/lithium futures 09:25 ET - not in files",
 "NB-088": "AH outlier needs 250 sessions of Finviz AH snapshots; snapshots start 2026-08-06",
 "NB-039": "needs LULD/news halt history - not in files",
 "NB-056": "needs Reg SHO threshold list history - not in files",
 "NB-042": "needs Nasdaq dividend announcement_Date (known-by-D-1 rule); dividends_2020 has ex_date/amount only",
 "NB-043": "needs Nasdaq dividend announcement_Date + dividend_Rate type; not in files",
 "NB-050": "needs snapshot 60 sessions earlier; snapshots start 2026-08-06 (earliest usable ~2026-11)",
}
SNAP_IND = {"NB-008": "After-Hours Change", "NB-010": "After-Hours Volume", "NB-022": "EPS Surprise", "NB-023": "Revenue Surprise", "NB-051": "Shares Float"}
PRICE_X = ["NB-015", "NB-025", "NB-026", "NB-029", "NB-035"]
PRICE_EV = ["NB-036", "NB-057", "NB-075", "NB-076"]; CAL_EV = ["NB-071", "NB-072", "NB-073"]
MKT_ROWS_IND = set(CAL_EV)   # ticker-free event (EVT/CNT/EXT/RNK lenses)

def load_rows():
    s = pd.read_csv(SHEET, dtype=str); s = s[s.merge_owner == "new-bot"]
    ex = set(pd.read_csv(EXCL).row_id) if EXCL.exists() else set(); s = s[~s.id.isin(ex)].copy()
    s["ind"] = s.id.str.extract(r"(NB-\d+)")[0]
    s["lk"] = s.id.str.replace(r"^nb4-\w+-NB-\d+-", "", regex=True)
    s["but"] = s.lk.str.contains("-BUT"); s["lens"] = s.lk.str.replace("-BUT", "", regex=False).str.replace("-SNAP", "", regex=False)
    thr = {}
    for _, r in s[s.lens == "T1-THR"].iterrows():
        m = re.search(r"YES if X_N(>=|<=)(-?[\d.]+)", r.strict_definition); thr[r.id] = (m.group(1), float(m.group(2)))
    return s.reset_index(drop=True), thr

def sessions_all():
    e = pd.read_parquet(ETF, columns=["ticker", "date", "close"]); spy = e[e.ticker == "SPY"].sort_values("date")
    spy["date"] = spy.date.astype("datetime64[ns]"); return spy.set_index("date").close.astype("float64")

_EARN = None
def earn_table(sess):
    """report_date -> rd_sess = first session STRICTLY after report_date (2020-24 Nasdaq time is always unknown,
    so the conservative 'usable next session' rule from data/earnings/COVERAGE.md). Only 2020-24 file read."""
    global _EARN
    if _EARN is None:
        e = pd.read_parquet(EARN_PQ, columns=["symbol", "report_date", "surprise_pct"])
        e = e[(e.report_date >= "2020-01-01") & (e.report_date <= "2024-12-31")].copy()
        e["symbol"] = e.symbol.astype(str); e["report_date"] = e.report_date.astype("datetime64[ns]")
        S = pd.DatetimeIndex(sess); i = S.searchsorted(e.report_date.values, side="right")
        e = e[i < len(S)]; e["rd_sess"] = S[i[i < len(S)]]
        e = e.sort_values(["symbol", "rd_sess"]).drop_duplicates(["symbol", "rd_sess"], keep="last")
        e["pre_sess"] = S[S.searchsorted(e.report_date.values, side="left") - 1]
        _EARN = e
    return _EARN

def cal_events(sess):
    """OPX events on sessions: third Friday / every Friday / quad witching, shifted to prior session if not a session."""
    S = pd.DatetimeIndex(sess); out = {k: pd.Series(False, index=S) for k in CAL_EV}
    allf = pd.date_range(S[0], S[-1], freq="W-FRI")
    def mark(k, days):
        for d in days:
            i = S.searchsorted(d, side="right") - 1
            if i >= 0 and (d - S[i]).days < 7: out[k].iloc[i] = True
    mark("NB-072", allf)
    third = [d for d in allf if 15 <= d.day <= 21]
    mark("NB-071", third); mark("NB-073", [d for d in third if d.month in (3, 6, 9, 12)])
    return out

# ---------- global medians (industry r1, fwd3) ----------
def global_tables(spy, test_only=None):
    fn = CACHE / "indmed.parquet"
    if fn.exists() and not test_only: return pd.read_parquet(fn)
    ind = pd.read_csv(SECT, usecols=["Ticker", "Industry"]).set_index("Ticker").Industry
    parts = []
    for y in range(2020, 2027):      # one year at a time (+10 sessions each side for r1/f3) to stay small
        flt = [("date", ">=", pd.Timestamp(f"{y-1}-12-15")), ("date", "<=", pd.Timestamp(f"{y+1}-01-15"))]
        if test_only: flt.append(("ticker", "in", test_only))
        p = pd.read_parquet(PX, columns=["ticker", "date", "close"], filters=flt)
        p["ticker"] = p.ticker.astype(str); p["date"] = p.date.astype("datetime64[ns]"); p = p.sort_values(["ticker", "date"])
        g = p.groupby("ticker", sort=False).close; c = p.close.astype("float64")
        p["r1"] = c / g.shift(1) - 1; p["f3"] = g.shift(-3) / c - 1
        p["industry"] = p.ticker.map(ind); p = p[(p.date.dt.year == y) & p.industry.notna()]
        gg = p.groupby(["industry", "date"])
        m = gg[["r1", "f3"]].median().astype("float32"); n = gg[["r1", "f3"]].count()
        parts.append(m.where(n >= 3).reset_index()); del p, gg, g, c
    m = pd.concat(parts, ignore_index=True)
    if not test_only: m.to_parquet(fn)
    return m

# ---------- per-ticker features ----------
def runs_dur(s, cond, xext, ticker):
    """returns (yes, but, ready) arrays for DUR90 on bar series. cond bool Series."""
    c = cond.fillna(False).values; tk = ticker.values
    newtk = np.r_[True, tk[1:] != tk[:-1]]
    brk = ~c | newtk
    rid = np.cumsum(brk)
    run = pd.Series(np.where(c, 1, 0)).groupby(rid).cumsum().values
    prev_run = np.r_[0, run[:-1]]; prev_run[newtk] = 0
    completed = np.where((~c) & (prev_run > 0), prev_run, np.nan)   # run ended at previous bar, known now
    cs = pd.Series(completed)
    q = cs.groupby(tk).transform(lambda x: x.dropna().expanding().quantile(0.9).reindex(x.index).ffill()) if False else None
    sub = cs.dropna(); gsub = pd.Series(tk[sub.index], index=sub.index)
    qv = sub.groupby(gsub.values).expanding().quantile(0.9).reset_index(level=0, drop=True)
    nv = sub.groupby(gsub.values).cumcount() + 1
    Q = pd.Series(np.nan, index=cs.index); Q.loc[qv.index] = qv.values
    N = pd.Series(np.nan, index=cs.index); N.loc[nv.index] = nv.values
    Q = Q.groupby(tk).ffill().values; N = N.groupby(tk).ffill().fillna(0).values
    ready = (N >= 5) & ~np.isnan(xext.values)
    yes = ready & (run > 0) & (run >= Q)
    # new run-extreme on last bar
    xv = pd.Series(np.where(c, xext.values, np.nan))
    return yes, ready, run, rid, xv

def feats(p, spy, med, snaps, cal, rows_by_ind):
    """p: bars of a ticker block, full history to year end. Returns DataFrame of per-bar codes per row id (uint8),
    and per-bar values needed for cross-section RNK."""
    p = p.sort_values(["ticker", "date"]).reset_index(drop=True)
    tk = p.ticker; g = p.groupby("ticker", sort=False)
    o, h, l, c, v = [p[k].astype("float64") for k in ("open", "high", "low", "close", "volume")]
    pc = g.close.shift(1).astype("float64"); ph = g.high.shift(1).astype("float64"); pl = g.low.shift(1).astype("float64")
    r1 = c / pc - 1
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1, skipna=False)
    atr = tr.groupby(tk).transform(lambda x: x.rolling(14, min_periods=14).mean())
    sp = spy.reindex(p.date.values).values; spr = (spy / spy.shift(1) - 1).reindex(p.date.values).values
    spf3 = (spy.shift(-3) / spy - 1).reindex(p.date.values).values
    ind = pd.read_csv(SECT, usecols=["Ticker", "Industry"]).set_index("Ticker").Industry
    p["industry"] = tk.map(ind)
    mm = p[["industry", "date"]].merge(med, on=["industry", "date"], how="left")
    imr1 = mm.r1.values.astype("float64"); imf3 = mm.f3.values.astype("float64")
    f3 = g.close.shift(-3).astype("float64") / c - 1    # used only via shift(3) (known by D-1)
    X = {}
    X["NB-015"] = (c - np.ceil(c)) / atr
    def roll(s, n, fn, mp=None):
        return s.groupby(tk).transform(lambda x: getattr(x.rolling(n, min_periods=mp or n), fn)())
    rs = pd.Series(spr, index=p.index)
    def beta(n):
        cov = roll(r1 * rs, n, "mean") - roll(r1, n, "mean") * roll(rs, n, "mean")
        var = roll(rs * rs, n, "mean") - roll(rs, n, "mean") ** 2
        return cov / var
    X["NB-025"] = beta(20) / beta(250)
    X["NB-026"] = r1 - imr1
    X["NB-029"] = roll((r1.abs() >= 0.2).astype(float).where(r1.notna()), 250, "sum")
    gu = (o > ph).fillna(False)
    X["NB-035"] = gu.astype(int).groupby((~gu | (tk != tk.shift())).cumsum()).cumsum().astype(float).where(ph.notna())
    # snapshot X (attached on bar date == snapshot date)
    if snaps is not None:
        sm = p[["ticker", "date"]].merge(snaps, on=["ticker", "date"], how="left")
        X["NB-008"] = sm["After-Hours Change"].values
        ahv = pd.Series(sm["After-Hours Volume"].values, index=p.index)
        X["NB-010"] = ahv / ahv.groupby(tk).transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
        X["NB-022"] = sm["EPS Surprise"].values; X["NB-023"] = sm["Revenue Surprise"].values
        flt = sm["Shares Float"].values
    else:
        for k in ("NB-008", "NB-010", "NB-023"): X[k] = np.full(len(p), np.nan)
        flt = np.full(len(p), np.nan)
    # ---- wire v1: earnings-derived X (bar-dated; the answer for D uses bar < D) ----
    E_ = EARN_T[EARN_T.symbol.isin(set(tk.unique()))]
    ev = p[["ticker", "date"]].merge(E_.rename(columns={"symbol": "ticker", "rd_sess": "date"})[["ticker", "date", "surprise_pct", "pre_sess"]], on=["ticker", "date"], how="left")
    isE = ev.pre_sess.notna().values
    cl = p[["ticker", "date"]].assign(c=c.values)
    pre = ev[["ticker", "pre_sess"]].rename(columns={"pre_sess": "date"}).merge(cl, on=["ticker", "date"], how="left").c.values
    react = pd.Series(np.where(isE, c.values / pre - 1, np.nan), index=p.index)
    anc = pd.Series(isE, index=p.index).groupby(tk).cumsum()
    X["NB-022"] = pd.Series(np.where(isE, ev.surprise_pct.values / 100.0, np.nan), index=p.index).groupby([tk, anc]).transform("first").where(anc > 0)
    rz = []
    for t_, rr in react[isE].groupby(tk[isE]):
        m = rr.shift(1).rolling(12, min_periods=12).mean(); sd = rr.shift(1).rolling(12, min_periods=12).std()
        rz.append((rr - m) / sd.where(sd > 0))
    zz = pd.Series(np.nan, index=p.index)
    if rz: z_ = pd.concat(rz); zz.loc[z_.index] = z_.values
    X["NB-024"] = zz.groupby([tk, anc]).transform("first").where(anc > 0)
    tp = (h + l + c) / 3.0; key = [tk, anc]
    av = (tp * v).groupby(key).cumsum() / v.groupby(key).cumsum()
    X["NB-014"] = (c / av - 1).where(anc > 0)
    ar = r1.abs()
    OUT91 = dict(isE=pd.Series(isE, index=p.index), r1=r1, ar=ar, atr=atr, h=h, l=l, c=c,
                 q99=ar.groupby(tk).transform(lambda x: x.rolling(250, min_periods=250).quantile(0.99)),
                 q95=ar.groupby(tk).transform(lambda x: x.rolling(250, min_periods=250).quantile(0.95)),
                 med=ar.groupby(tk).transform(lambda x: x.rolling(250, min_periods=250).median()))
    X = {k: pd.Series(np.asarray(v, dtype="float64"), index=p.index) for k, v in X.items()}
    # events on bars (bar = D-1 for the answer of D)
    atrp2 = (atr / c).groupby(tk).shift(1)       # ATR14% ending D-2
    E = {}
    E["NB-036"] = (h < ph) & (l > pl) & (r1.groupby(tk).shift(1).abs() >= 2 * atrp2)
    E["NB-057"] = l <= 0.9 * pc
    E["NB-075"] = r1 >= 0.20
    E["NB-076"] = (r1 > 0) & (pd.Series(spr, index=p.index) <= -0.01)
    for k in CAL_EV: E[k] = pd.Series(cal[k].reindex(p.date.values).fillna(False).values, index=p.index)
    E["NB-051"] = pd.Series(flt < 10.0, index=p.index)
    Evalid = {k: pc.notna() for k in E}
    Evalid["NB-036"] = atrp2.notna() & ph.notna(); Evalid["NB-051"] = pd.Series(~np.isnan(flt), index=p.index)
    for k in CAL_EV: Evalid[k] = pd.Series(True, index=p.index)
    out = {}; rnk = {}
    for ind_, rws in rows_by_ind.items():
        lens_set = set(rws.lens)
        if ind_ == "NB-091":
            O = OUT91
            for _, r in rws.iterrows():
                m = re.match(r"W1-(P99|P95|X2|X3|X4)(IN|NR|PS)([GR])", r.lens); kind, pos, col_ = m.groups()
                thr = O["q99"] if kind == "P99" else O["q95"] if kind == "P95" else float(kind[1]) * O["med"]
                rd = thr.notna() & O["r1"].notna() & O["atr"].notna()
                g_ = (O["r1"] > 0) if col_ == "G" else (O["r1"] < 0)
                trig = O["isE"] & (O["ar"] >= thr) & g_
                if pos == "IN": ps = (O["c"] >= O["l"]) & (O["c"] <= O["h"])
                elif pos == "PS": ps = (O["c"] > O["h"]) if col_ == "G" else (O["c"] < O["l"])
                else: ps = ((O["h"] - O["c"] <= O["atr"]) & (O["c"] <= O["h"])) if col_ == "G" else ((O["c"] - O["l"] <= O["atr"]) & (O["c"] >= O["l"]))
                y = trig & ps   # BUT mirror: same trigger by definition (tests undo outcome) -> identical answer
                out[r.id] = np.where(rd.values, np.where(y.fillna(False).values, 2, 1), 0).astype(np.uint8)
            continue
        if ind_ in X:
            x = X[ind_]; xr = x.notna()
            for _, r in rws.iterrows():
                L, b, rid_ = r.lens, r.but, r.id
                if L == "T1-THR":
                    op, val = THR[rid_]; y = (x >= val) if op == ">=" else (x <= val); rd = xr
                elif L == "T1-EXT":
                    q = roll(x, 250, "quantile" if False else "max") if False else x.groupby(tk).transform(lambda s: s.rolling(250, min_periods=250).quantile(0.05 if b else 0.95))
                    y = (x <= q) if b else (x >= q); rd = q.notna() & xr
                elif L == "T1-CHG":
                    dx = x - x.groupby(tk).shift(1); sd = dx.groupby(tk).transform(lambda s: s.rolling(250, min_periods=250).std())
                    y = (dx <= -sd) if b else (dx >= sd); rd = sd.notna() & dx.notna()
                elif L == "T1-DIV":
                    pr = x.groupby(tk).transform(lambda s: s.rolling(250, min_periods=250).rank(pct=True))
                    y = ((pr <= 0.2) & (r1 >= 0)) if b else ((pr >= 0.8) & (r1 <= 0)); rd = pr.notna() & r1.notna()
                elif L == "T1-RNK":
                    rnk[ind_] = x; continue
                elif L == "T3-CRS":
                    sma = roll(x, 3, "mean"); a = x > sma; a1 = a.groupby(tk).shift(1)
                    bl = x < sma; bl1 = bl.groupby(tk).shift(1)
                    y = (bl & ~bl1.fillna(True).astype(bool)) if b else (a & ~a1.fillna(True).astype(bool))
                    rd = sma.notna() & sma.groupby(tk).shift(1).notna()
                elif L == "T3-STK":
                    sma = roll(x, 20, "mean"); z = ((x < sma) if b else (x > sma)).astype(float).where(sma.notna())
                    s3 = roll(z, 3, "sum"); y = s3 == 3; rd = s3.notna()
                elif L in ("P5-POSQ", "P5-POSD"):
                    mn = roll(x, 5, "min"); mx = roll(x, 5, "max"); k = 0.75 if L == "P5-POSQ" else 0.9
                    y = (x <= mn + (1 - k) * (mx - mn)) if b else (x >= mn + k * (mx - mn)); y = y & (mx > mn); rd = mn.notna()
                elif L.startswith("DUR90"):
                    kind = L[-3:]; key = (ind_, kind)
                    if key not in DURC:
                        if kind == "SUP": cond = x > x.groupby(tk).shift(1)
                        elif kind == "SDN": cond = x < x.groupby(tk).shift(1)
                        else:
                            mn = roll(x, 60, "min"); mx = roll(x, 60, "max")
                            cond = (x >= mn + 0.75 * (mx - mn)) if kind == "ZTQ" else (x <= mn + 0.25 * (mx - mn))
                            cond = cond & mn.notna()
                        yes, ready, run, rid, xv = runs_dur(None, cond, x, tk)
                        ext = xv.groupby(rid).cummax() if kind in ("SUP", "ZTQ") else xv.groupby(rid).cummin()
                        newext = (x.values == ext.values) & (run > 0)
                        DURC[key] = (yes, ready, newext)
                    yes, ready, newext = DURC[key]
                    y = pd.Series(yes & newext if b else yes, index=p.index); rd = pd.Series(ready, index=p.index)
                else:
                    raise ValueError(L)
                out[rid_] = np.where(rd.values, np.where(np.asarray(y, dtype=bool), 2, 1), 0).astype(np.uint8)
        elif ind_ in E:
            e = E[ind_].fillna(False).astype(bool); ev = Evalid[ind_]
            ef = e.astype(float).where(ev)
            cnt = roll(ef, 20, "sum")
            for _, r in rws.iterrows():
                L, b, rid_ = r.lens, r.but, r.id
                if L == "W0-EVT":
                    y = e & False if b else e; rd = ev        # BUT: move since event (D-1 close or today) is 0 at the open -> NO
                elif L == "T20-CNT":
                    y = (cnt == 0) if b else (cnt >= 2); rd = cnt.notna()
                elif L == "T20-EXT":
                    # EXT fix 2026-10-22: main YES needs cnt>0 & cnt>=p95 (so cnt>p95 when p95==0); BUT = sheet cnt<=p05 AND NOT main (never both YES)
                    q95 = cnt.groupby(tk).transform(lambda s: s.expanding(250).quantile(0.95)); main = (cnt > 0) & (cnt >= q95)
                    if b: q = cnt.groupby(tk).transform(lambda s: s.expanding(250).quantile(0.05)); y = (cnt <= q) & ~main
                    else: q = q95; y = main
                    rd = q.notna() & q95.notna()
                elif L in ("T20-RXS", "T20-RXM"):
                    ref = imf3 if L == "T20-RXS" else spf3
                    d = pd.Series(np.where(e.values, f3.values - ref, np.nan), index=p.index)
                    dv = pd.Series(np.where(e.values & np.isnan(ref), 1.0, 0.0), index=p.index)  # event with missing ref
                    d3 = d.groupby(tk).shift(3); bad = roll(dv.groupby(tk).shift(3), 17, "sum")
                    sm_ = roll(d3.fillna(0), 17, "sum"); n_ = roll(d3.notna().astype(float), 17, "sum")
                    mean = sm_ / n_.where(n_ > 0)
                    y = (mean <= -0.03) if b else (mean >= 0.03); y = y.fillna(False)
                    rd = n_.notna() & (bad == 0) & cnt.notna()
                    if L == "T20-RXS": rd = rd & p.industry.notna()
                elif L == "T20-RNK":
                    rnk[ind_] = cnt.where(cnt.notna()); continue
                else: raise ValueError(L)
                out[rid_] = np.where(rd.values, np.where(np.asarray(y, dtype=bool), 2, 1), 0).astype(np.uint8)
    return p[["ticker", "date"]], pd.DataFrame(out), pd.DataFrame({k: v.values for k, v in rnk.items()})

def snapshots_table(tickers):
    rows = []
    for f in sorted(SNAPD.glob("????-??-??.raw.csv")):
        d = pd.read_csv(f, usecols=["Ticker", "EPS Surprise", "Revenue Surprise", "Shares Float", "After-Hours Change", "After-Hours Volume"])
        d = d[d.Ticker.isin(tickers)]; d["date"] = pd.Timestamp(f.name[:10]); rows.append(d)
    s = pd.concat(rows).rename(columns={"Ticker": "ticker"})
    for k in ("EPS Surprise", "Revenue Surprise", "After-Hours Change"):
        s[k] = pd.to_numeric(s[k].astype(str).str.rstrip("%"), errors="coerce") / 100
    return s

def pack(codes):
    n, k = codes.shape; pad = (-k) % 4
    if pad: codes = np.concatenate([codes, np.zeros((n, pad), np.uint8)], 1)
    c = codes.reshape(n, -1, 4); return (c[..., 0] | (c[..., 1] << 2) | (c[..., 2] << 4) | (c[..., 3] << 6)).astype(np.uint8)
def unpack(b, k):
    return np.stack([(b >> s) & 3 for s in (0, 2, 4, 6)], -1).reshape(b.shape[0], -1)[:, :k]

DURC = {}; THR = {}
def run_year(year, only=None, block=500, d0=None, d1=None, write=True):
    global THR, DURC
    global EARN_T
    t0 = time.time(); rows, THR = load_rows(); rows = rows[rows.ind.isin(WIRE_IND)].reset_index(drop=True); ids = list(rows.id)
    spy = sessions_all(); sess = spy.index.values
    ys = sess[(sess >= np.datetime64(d0 or f"{year}-01-01")) & (sess <= np.datetime64(d1 or f"{year}-12-31"))]
    cal = cal_events(sess); EARN_T = earn_table(sess)
    med = global_tables(spy, test_only=only); med = med[med.date <= pd.Timestamp("2024-12-31")]
    lf = CACHE / "last.parquet"
    if not lf.exists():
        full = pd.read_parquet(PX, columns=["ticker", "date"]); full["ticker"] = full.ticker.astype(str)
        full.groupby("ticker").date.max().astype("datetime64[ns]").to_frame().to_parquet(lf); del full
    last = pd.read_parquet(lf).date
    funds = set(pd.read_csv(CACHE / "fund_exclusion_tickers.csv").ticker)   # v2 fund exclusion (ETF/CEF/shell, snap_2026-09-29)
    tickers = sorted(only or [t for t in last.index if t not in funds])
    secmap = pd.read_csv(SECT, usecols=["Ticker", "Sector"]).set_index("Ticker").Sector
    sec_of = pd.Series(tickers, index=tickers).map(secmap).fillna("Unknown")
    snaps = None
    assert year <= 2024, 'wire v1: 2020-24 only'
    comp = rows[rows.ind.isin(WIRE_IND)]
    rows_by_ind = {k: g for k, g in comp.groupby("ind", sort=False)}
    nr_reason = {}
    for _, r in rows.iterrows():
        if r.ind in NR_IND: nr_reason[r.id] = NR_IND[r.ind]
        elif r.ind in SNAP_IND and r.ind != "NB-022" and year < 2026: nr_reason[r.id] = "Finviz snapshot field; snapshots start 2026-08-06"
    col = {rid: j for j, rid in enumerate(ids)}
    rnk_cols = [r.id for _, r in comp.iterrows() if r.lens in ("T1-RNK", "T20-RNK")]
    hi = pd.Timestamp(ys[-1]); lo = pd.Timestamp("2019-12-01")
    blocks = []; RV = []; t1 = time.time()
    for i in range(0, len(tickers), block):
        bt = tickers[i:i + block]; DURC = {}
        p = pd.read_parquet(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"],
                            filters=[("ticker", "in", bt), ("date", "<", hi)])
        p["ticker"] = p.ticker.astype(str); p["date"] = p.date.astype("datetime64[ns]")
        keys, codes, rv = feats(p, spy, med, snaps, cal, rows_by_ind)
        keys = keys.assign(bi=np.arange(len(keys)))
        grid = pd.DataFrame({"ticker": np.repeat(bt, len(ys)), "D": np.tile(ys, len(bt))})
        q = keys.rename(columns={"date": "bar"}).sort_values("bar")
        grid = pd.merge_asof(grid.sort_values("D"), q, left_on="D", right_on="bar", by="ticker", allow_exact_matches=False)
        grid = grid.sort_values(["ticker", "D"]).reset_index(drop=True)
        bi = grid.bi.values; has = ~np.isnan(bi); bi = np.where(has, bi, 0).astype(int)
        lag = (grid.D - grid.bar).dt.days.fillna(9999).values
        lastd = grid.ticker.map(last).values.astype("datetime64[ns]")
        ok = has & (lag <= 7) & ~((grid.D.values > lastd) & (lastd < STALE_CUT))
        C = np.zeros((len(grid), len(ids)), np.uint8)
        for rid_ in codes.columns:
            C[:, col[rid_]] = np.where(ok, codes[rid_].values[bi], 0)
        # calendar EVT rows: event is dated D itself
        for k in CAL_EV:
            if k in rows_by_ind:
                evD = cal[k].reindex(grid.D.values).values.astype(bool)
                for _, r in rows_by_ind[k][rows_by_ind[k].lens == "W0-EVT"].iterrows():
                    C[:, col[r.id]] = np.where(ok, np.where(evD & (not r.but), 2, 1), 0)
        rvc = rv.astype('float32').iloc[bi].reset_index(drop=True).where(pd.Series(ok)) if len(rv.columns) else pd.DataFrame(index=range(len(grid)))
        rvc["ticker"] = grid.ticker.values; rvc["D"] = grid.D.values
        RV.append(rvc); blocks.append((bt, pack(C)))
        del p, codes, rv, C, grid; gc.collect()
        print(f"  block {i//block} tickers={len(bt)} t={time.time()-t1:.0f}s", flush=True)
    # cross-section RNK
    RVa = pd.concat(RV, ignore_index=True); RVa["sector"] = RVa.ticker.map(sec_of)
    rcode = {}
    for rid_ in rnk_cols:
        r = rows.set_index("id").loc[rid_]; v = RVa[r.ind]
        if r.but:
            m = v.groupby(RVa.D).rank(method="min", ascending=True, pct=True); s_ = v.groupby([RVa.D, RVa.sector]).rank(method="min", ascending=True, pct=True)
        else:
            m = v.groupby(RVa.D).rank(method="min", ascending=False, pct=True); s_ = v.groupby([RVa.D, RVa.sector]).rank(method="min", ascending=False, pct=True)
        y = (m <= 0.10) & (s_ <= 0.10); rd = v.notna() & (RVa.sector != "Unknown")
        rcode[rid_] = np.where(rd, np.where(y, 2, 1), 0).astype(np.uint8)
    del RVa, RV, v, m, s_, y, rd; gc.collect()
    off = 0; res = {}
    while blocks:
        bt, P = blocks.pop(0)
        n = len(bt) * len(ys); C = unpack(P, len(ids))
        for rid_ in rnk_cols: C[:, col[rid_]] = rcode[rid_][off:off + n]
        off += n; res[tuple(bt)] = pack(C)
    el = time.time() - t0
    return dict(ids=ids, rows=rows, ys=ys, tickers=tickers, sec_of=sec_of, res=res, nr_reason=nr_reason, secs=el, comp=comp)

def write_year(year, R):
    ids, ys, sec_of = R["ids"], R["ys"], R["sec_of"]
    allC = {}; tick = []
    for bt, C in R["res"].items():
        for j, t in enumerate(bt): allC[t] = C[j * len(ys):(j + 1) * len(ys)]
    jobs = []
    for sec0 in sorted(sec_of.unique()):
        tk0 = [t for t in R["tickers"] if sec_of[t] == sec0]
        if len(tk0) <= 2000: jobs.append((sec0, tk0))
        else: jobs += [(f"{sec0}_part{k}", tk0[i:i + 2000]) for k, i in enumerate(range(0, len(tk0), 2000))]
    files = []; cov = np.zeros((len(ids), 3), np.int64)
    dstr = ys.astype("datetime64[D]").astype(str)
    for sec, tk in jobs:
        C = np.concatenate([allC[t] for t in tk])
        P = C
        for a in range(0, len(P), 20000):
            U = unpack(P[a:a + 20000], len(ids))
            for k in range(3): cov[:, k] += (U == k).sum(0)
            del U
        df = pd.DataFrame({"ticker": np.repeat(tk, len(ys)), "date": np.tile(dstr, len(tk)), "packed": [bytes(x) for x in P]})
        fn = CHUNKS / f"{year}__NBW__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.parquet"; df.to_parquet(fn, index=False)
        meta = dict(year=year, sector=sec, layout="rows ticker-major then date; packed = 2-bit codes 0=NR 1=NO 2=YES, 4/byte along ids (engine_year.pack)",
                    survivor_only=True, sector_map="current_backfilled", industry_map="current_backfilled (Finviz Industry, current.csv)",
                    price_source=PX, price_adjust="split_only", dividend_adjusted=False, n_ids=len(ids), ids=ids,
                    nr_reasons=R["nr_reason"], n_tickers=len(tk), n_cells=len(df))
        json.dump(meta, open(str(fn).replace(".parquet", ".json"), "w"), indent=1); files.append(str(fn))
    return files, cov

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("year", type=int); ap.add_argument("--only"); ap.add_argument("--block", type=int, default=500)
    a = ap.parse_args()
    import pickle
    R = run_year(a.year, only=a.only.split(",") if a.only else None, block=a.block)
    gc.collect(); files, cov = write_year(a.year, R)
    c = pd.DataFrame(cov, columns=["nr", "no", "yes"], index=R["ids"]); c.to_csv(CHUNKS / f"{a.year}__NBW_coverage.csv")
    print(f"YEAR {a.year} secs={R['secs']:.0f} files={len(files)}", flush=True)
