#!/usr/bin/env python3
"""JA_F4 add-on: James SEC-JA-166..181 (+BUT) industry insider-cluster rows from SEC DERA Form 4, 2020-2024 ONLY.
Source: data/edgar_form4/dera_2020_24/form4_{y}.parquet (structured fields only). Table I (non-derivative), codes P (buy) / S (sell),
original Form 4 only (4/A excluded), deduped per (accession, transaction_sk) for $ and counts; distinct insiders = reporting_owner_cik.
PIT: a filing counts from the open of effective_date = next NYSE session after filing_date (D+1). 'last N sessions' at session D =
filings with effective_date in the N sessions ending at D (incl. D's open). Prices = last bar < D. Industry = current Theme Radar
snapshot Industry applied to all dates (current_backfilled, same as SI/sector add-on). Issuers only count if their ticker is in the snapshot.
Codes 0=NR 1=NO 2=YES packed like nb_year.pack. Windows needing data before 2020-01-03 effective dates -> NR."""
import sys, json, re, gc, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import nb_year as NB
F4 = Path("/workspace/data/edgar_form4/dera_2020_24"); TAGS = HERE.parent / "out/tags/james_f4_tags.csv"
IDS = [f"SEC-JA-{i}{s}" for i in range(166, 182) for s in ("", "-BUT")]
def norm(s): return s.astype(str).str.strip().str.upper().str.replace(r"[./ ]", "-", regex=True)
def events(cur):
    x = pd.concat([pd.read_parquet(F4 / f"form4_{y}.parquet", columns=["accession_number", "ticker", "issuer_cik", "reporting_owner_cik", "is_amendment",
        "effective_date", "transaction_code", "is_derivative", "transaction_sk", "shares", "price"],
        filters=[("is_derivative", "=", False), ("transaction_code", "in", ["P", "S"])]) for y in range(2020, 2025)])
    x = x[~x.is_amendment & x.ticker.notna()].copy(); x["ticker"] = norm(x.ticker)
    x["industry"] = x.ticker.map(cur.Industry); x = x[x.industry.notna()]
    x["eff"] = pd.to_datetime(x.effective_date); x["usd"] = x.shares * x.price
    return x
def run(years):
    t0 = time.time(); cur = pd.read_csv(NB.SECT, usecols=["Ticker", "Sector", "Industry"]).dropna(subset=["Ticker"]).drop_duplicates("Ticker").set_index("Ticker")
    spy = NB.sessions_all(); spy = spy[(spy.index >= "2019-10-01") & (spy.index <= "2024-12-31")]; S = spy.index.values; nS = len(S)
    kidx = pd.Series(np.arange(nS), index=S)
    first_ok = int(np.searchsorted(S, np.datetime64("2020-01-03")))   # first effective session covered by the data
    X = events(cur); X = X[X.eff <= S[-1]]; X["k"] = np.searchsorted(S, X.eff.values)   # eff is a session; searchsorted exact
    inds = sorted(cur.Industry.dropna().unique()); ii = {s: j for j, s in enumerate(inds)}; nI = len(inds); X["i"] = X.industry.map(ii)
    print("events", X.groupby("transaction_code").size().to_dict(), flush=True)
    # ---- industry x session features
    def win(code, N):
        e = X[X.transaction_code == code]; rows = []
        for o in range(N):
            z = e[["i", "k", "reporting_owner_cik", "issuer_cik", "accession_number", "transaction_sk", "usd", "ticker"]].copy(); z["k"] = z.k + o; rows.append(z)
        z = pd.concat(rows); z = z[z.k < nS]; return z
    F = {}
    for code in ("P", "S"):
        for N in (1, 3, 5):
            z = win(code, N); g = z.groupby(["i", "k"])
            ins = np.zeros((nI, nS)); co = np.zeros((nI, nS))
            a = g.reporting_owner_cik.nunique(); ins[a.index.get_level_values(0), a.index.get_level_values(1)] = a.values
            a = g.issuer_cik.nunique(); co[a.index.get_level_values(0), a.index.get_level_values(1)] = a.values
            F[(code, N, "clu")] = (ins >= 3) & (co >= 2)
            if N == 5:
                F[(code, "ins5")] = ins
                d = z.drop_duplicates(["accession_number", "transaction_sk", "k"])
                cnt = np.zeros((nI, nS)); a = d.groupby(["i", "k"]).accession_number.nunique(); cnt[a.index.get_level_values(0), a.index.get_level_values(1)] = a.values
                usd = np.zeros((nI, nS)); a = d.groupby(["i", "k"]).usd.sum(); usd[a.index.get_level_values(0), a.index.get_level_values(1)] = a.values
                F[(code, "cnt")] = cnt; F[(code, "usd")] = usd
                bt = d.groupby(["i", "k", "ticker"]).usd.sum().reset_index().sort_values("usd").drop_duplicates(["i", "k"], keep="last")
                F[(code, "topsh")] = bt.assign(sh=bt.usd / bt.set_index(["i", "k"]).index.map(lambda t: usd[t])).set_index(["i", "k"])[["ticker", "sh"]]
                F[(code, "tk_in_win")] = set(zip(d.ticker, d.k))
            del z; gc.collect()
    # validity: window fully inside data
    kk = np.arange(nS); valid = {N: (kk - N + 1) >= first_ok for N in (1, 3, 5)}
    valid10 = (kk - 9) >= first_ok; valid_ext = (kk - 4 - 252) >= first_ok
    # extreme vs 252 (trailing history excluding today), change vs prior 5
    def ext(c):
        df = pd.DataFrame(c.T); q = df.shift(1).rolling(252, min_periods=252).quantile(.95).values.T; return (c > 0) & (c >= q)
    def chg(c):
        p = np.full_like(c, np.nan); p[:, 5:] = c[:, :-5]; return (c > 0) & (c >= 2 * p)
    def rank5(u):
        r = pd.DataFrame(u).rank(axis=0, ascending=False, method="min").values; return (r <= 5) & (u > 0)
    # ---- prices: last bar < D
    tick_all = sorted(set(pd.read_parquet(NB.CACHE / "last.parquet").date.index) - set(pd.read_csv(NB.CACHE / "fund_exclusion_tickers.csv").ticker))
    p = pd.read_parquet(NB.PX, columns=["ticker", "date", "close", "volume"], filters=[("date", ">=", pd.Timestamp("2019-08-01")), ("date", "<=", pd.Timestamp("2024-12-31"))])
    p["ticker"] = p.ticker.astype(str); p["date"] = p.date.astype("datetime64[ns]")
    C = p.pivot_table(index="date", columns="ticker", values="close", aggfunc="last").reindex(S).astype("float32")
    V = p.pivot_table(index="date", columns="ticker", values="volume", aggfunc="last").reindex(S).astype("float32"); del p; gc.collect()
    # value known at D = computed on bar D-1 -> shift(1)
    r5 = (C / C.shift(5) - 1).shift(1); r21 = (C / C.shift(21) - 1).shift(1); r1 = (C / C.shift(1) - 1).shift(1)
    vr = (V / V.shift(1).rolling(20, min_periods=20).mean()).shift(1)
    spy5 = (spy / spy.shift(5) - 1).shift(1).values
    tind = cur.Industry.reindex(r5.columns)
    pw = r5.T.groupby(tind).mean().reindex(inds).values; pm = r21.T.groupby(tind).mean().reindex(inds).values   # (nI, nS)
    out = {}
    for y in years:
        ky = np.where((S >= np.datetime64(f"{y}-01-01")) & (S <= np.datetime64(f"{y}-12-31")))[0]
        tks = [t for t in tick_all if t in cur.index and isinstance(cur.Industry.get(t), str)]
        nr_t = [t for t in tick_all if t not in tks]
        A = np.zeros((len(tick_all), len(ky), len(IDS)), np.uint8); col = {r: j for j, r in enumerate(IDS)}; tpos = {t: j for j, t in enumerate(tick_all)}
        ti = np.array([ii[cur.Industry[t]] for t in tks]); tp = np.array([tpos[t] for t in tks])
        def put(rid, yes, rd):   # yes/rd shape (len(tks), len(ky))
            A[tp, :, col[rid]] = np.where(rd, np.where(yes, 2, 1), 0)
        I = lambda m: m[ti][:, ky]; V_ = lambda v: np.broadcast_to(v[ky], (len(tks), len(ky)))
        PW = I(pw); PM = I(pm); pwok = ~np.isnan(PW); pmok = ~np.isnan(PM)
        st = lambda df: df.reindex(columns=tks).values.T[:, ky]
        R1 = st(r1); VR = st(vr)
        SP = V_(spy5)
        for code, base, sgn in (("P", 166, -1), ("S", 174, 1)):
            for o, N in enumerate((1, 3, 5)):
                c = I(F[(code, N, "clu")]); rd = V_(valid[N])
                put(f"SEC-JA-{base+o}", c, rd)
                put(f"SEC-JA-{base+o}-BUT", c & ((PW < -0.05) if code == "P" else (PW > 0.05)), rd & pwok)
            rd5 = V_(valid[5]); u = F[(code, "usd")]; U = I(u)
            put(f"SEC-JA-{base+3}", U >= 5e6, rd5)
            ts = F[(code, "topsh")]; conc = np.zeros((len(tks), len(ky)), bool)
            m = ts[(ts.sh >= .8)]; m = m[np.isin(m.index.get_level_values(1), ky)]
            kpos = {k: j for j, k in enumerate(ky)}; ipos = {}
            for j, i_ in enumerate(ti): ipos.setdefault(i_, []).append(j)
            for (i_, k_), r in m.iterrows():
                for j in ipos.get(i_, []):
                    if tks[j] != r.ticker: conc[j, kpos[k_]] = True
            put(f"SEC-JA-{base+3}-BUT", (U >= 5e6) & conc, rd5)
            e = I(ext(F[(code, "cnt")])); rde = V_(valid_ext)
            put(f"SEC-JA-{base+4}", e, rde)
            put(f"SEC-JA-{base+4}-BUT", e & (np.abs(SP) > .03) & (np.sign(SP) == np.sign(PW)), rde & pwok & ~np.isnan(SP))
            ch = I(chg(F[(code, "cnt")])); rd10 = V_(valid10)
            put(f"SEC-JA-{base+5}", ch, rd10)
            stk = (R1 <= -.03) & (VR >= 2) if code == "P" else (R1 >= .03) & (VR >= 2)
            put(f"SEC-JA-{base+5}-BUT", ch & stk, rd10 & ~np.isnan(R1) & ~np.isnan(VR))
            rk = I(rank5(u)); put(f"SEC-JA-{base+6}", rk, rd5)
            other = F[("S" if code == "P" else "P", "tk_in_win")]
            own = np.array([[(t, k) in other for k in ky] for t in tks])
            put(f"SEC-JA-{base+6}-BUT", rk & own, rd5)
            cl = I(F[(code, "ins5")]) >= 3
            dv = cl & ((PW < 0) if code == "P" else (PW > 0)); put(f"SEC-JA-{base+7}", dv, rd5 & pwok)
            put(f"SEC-JA-{base+7}-BUT", dv & ((PM <= -.10) if code == "P" else (PM >= .10)), rd5 & pwok & pmok)
        out[y] = (tick_all, S[ky], A, cur.Sector.reindex(tick_all).fillna("Unknown"))
        print(f"year {y} built t={time.time()-t0:.0f}s nr_tickers={len(nr_t)}", flush=True)
    return out, X
def write(y, tick_all, ys, A, sec_of, sha):
    cov = np.zeros((len(IDS), 3), np.int64); dstr = ys.astype("datetime64[D]").astype(str); files = []
    for sec0 in sorted(sec_of.unique()):
        tk = [t for t in tick_all if sec_of[t] == sec0]; jobs = [(sec0, tk)] if len(tk) <= 2000 else [(f"{sec0}_part{k}", tk[i:i+2000]) for k, i in enumerate(range(0, len(tk), 2000))]
        for sec, t2 in jobs:
            idx = [tick_all.index(t) for t in t2]; U = A[idx].reshape(-1, len(IDS))
            for k in range(3): cov[:, k] += (U == k).sum(0)
            P = NB.pack(U); df = pd.DataFrame({"ticker": np.repeat(t2, len(ys)), "date": np.tile(dstr, len(t2)), "packed": [bytes(x) for x in P]})
            fn = NB.CHUNKS / f"{y}__JA_F4__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.parquet"; df.to_parquet(fn, index=False); files.append(fn)
            json.dump(dict(year=y, sector=sec, layout="rows ticker-major then date; packed = 2-bit codes 0=NR 1=NO 2=YES, 4/byte along ids (engine_year.pack)",
                addon="JA_F4: SEC DERA Form 4 industry insider clusters (James SEC-JA-166..181 + BUT)", survivor_only=True, sector_map="current_backfilled (industry = current snapshot Industry)",
                source="SEC DERA insider transactions, form4_{y}.parquet (Table I, codes P/S, 4/A excluded)",
                point_in_time="filing counts from open of next NYSE session after filing_date (effective_date); last N sessions = effective_date in N sessions ending D; prices = last bar < D",
                tags_csv=str(TAGS), tags_sha256=sha, n_ids=len(IDS), ids=IDS, n_tickers=len(t2), n_cells=len(df)), open(str(fn).replace(".parquet", ".json"), "w"), indent=1)
    pd.DataFrame(cov, columns=["nr", "no", "yes"], index=IDS).to_csv(NB.CHUNKS / f"{y}__JA_F4_coverage.csv"); return files
if __name__ == "__main__":
    ys = [int(a) for a in sys.argv[1:]] or [2020, 2021, 2022, 2023, 2024]
    sha = open(str(TAGS) + ".sha256").read().split()[0]
    out, X = run(ys); X.to_parquet("/tmp/f4_events.parquet")
    for y in ys: write(y, *out[y], sha)
