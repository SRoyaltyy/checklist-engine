#!/usr/bin/env python3
"""Theme Radar Form 4 answers -> chunks/{y}__F4TR__{sector}.parquet, 2020-2024 ONLY.
Net-buy $ from DERA P/S; insider ownership % = NR (no PIT shares outstanding on box)."""
import json, hashlib, gc, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
CH = HERE / "chunks"
F4 = Path("/workspace/data/edgar_form4/dera_2020_24")
PX = "/workspace/pricehist/universe_2020_survivors.parquet"
SECT = "/workspace/theme-radar-repo/data/snapshots/current.csv"
TAGS = HERE.parent / "out/tags/theme-radar_f4_tags.csv"
SHA = hashlib.sha256(TAGS.read_bytes()).hexdigest()
assert SHA == (HERE.parent / "out/tags/theme-radar_f4_tags.csv.sha256").read_text().split()[0]

def pack(codes):
    n, k = codes.shape; pad = (-k) % 4
    if pad: codes = np.concatenate([codes, np.zeros((n, pad), np.uint8)], 1)
    c = codes.reshape(n, -1, 4)
    return (c[..., 0] | (c[..., 1] << 2) | (c[..., 2] << 4) | (c[..., 3] << 6)).astype(np.uint8)

def norm(s):
    return s.astype(str).str.strip().str.upper().str.replace(r"[./ ]", "-", regex=True)

def load_events():
    cols = ["accession_number","ticker","is_amendment","effective_date","transaction_code",
            "is_derivative","transaction_sk","shares","price"]
    x = pd.concat([pd.read_parquet(F4 / f"form4_{y}.parquet", columns=cols,
        filters=[("is_derivative","=",False),("transaction_code","in",["P","S"])]) for y in range(2020,2025)])
    x = x[~x.is_amendment & x.ticker.notna()].copy()
    x["ticker"] = norm(x.ticker)
    x = x.drop_duplicates(["accession_number","is_derivative","transaction_sk"])
    x["eff"] = pd.to_datetime(x.effective_date)
    x["usd"] = x.shares.fillna(0) * x.price.fillna(0)
    x["signed"] = np.where(x.transaction_code=="P", x.usd, -x.usd)
    return x.groupby(["ticker","eff"], as_index=False).signed.sum().rename(columns={"eff":"date","signed":"net"})

def main():
    t0 = time.time()
    tags = pd.read_csv(TAGS)
    ids = tags.row_id.tolist()
    id_meta = tags.set_index("row_id")
    nb_ids = [i for i in ids if id_meta.loc[i,"indicator"]=="Insider Form 4 net buy value $"]
    own_ids = [i for i in ids if id_meta.loc[i,"indicator"]=="Insider ownership %"]
    print("ids", len(ids), "netbuy", len(nb_ids), "own", len(own_ids), flush=True)

    net = load_events()
    print("net days", len(net), "tickers", net.ticker.nunique(), flush=True)

    px = pd.read_parquet(PX, columns=["ticker","date","close","volume"],
        filters=[("date",">=",pd.Timestamp("2019-06-01")),("date","<=",pd.Timestamp("2024-12-31"))])
    px["ticker"] = px.ticker.astype(str); px["date"] = pd.to_datetime(px.date)
    funds = set(pd.read_csv(HERE/"nb_cache/fund_exclusion_tickers.csv").ticker)
    tickers = sorted(set(px.ticker) - funds)
    secmap = pd.read_csv(SECT, usecols=["Ticker","Sector","Industry"]).dropna(subset=["Ticker"]).drop_duplicates("Ticker")
    secmap["Ticker"] = norm(secmap.Ticker)
    sec_of = secmap.set_index("Ticker").Sector.reindex(tickers).fillna("Unknown")
    ind_of = secmap.set_index("Ticker").Industry.reindex(tickers)

    # trading calendar from SPY-like: all unique dates in px
    S = pd.DatetimeIndex(sorted(px.date.unique()))
    S = S[(S >= "2019-06-01") & (S <= "2024-12-31")].values.astype("datetime64[ns]")
    kidx = {pd.Timestamp(d): i for i,d in enumerate(S)}
    nS = len(S)
    first_ok = int(np.searchsorted(S, np.datetime64("2020-01-03","ns")))

    # daily net matrix (nT, nS)
    T = tickers
    ti = {t:i for i,t in enumerate(T)}; nT = len(T)
    M = np.zeros((nT, nS), dtype=np.float64)
    net = net[net.ticker.isin(ti)]
    for tk, d, v in zip(net.ticker, net.date, net.net):
        j = kidx.get(pd.Timestamp(d))
        if j is not None: M[ti[tk], j] += v
    del net; gc.collect()

    # price/volume known at D = bar D-1
    C = px.pivot_table(index="date", columns="ticker", values="close", aggfunc="last").reindex(S)[T].astype("float32")
    V = px.pivot_table(index="date", columns="ticker", values="volume", aggfunc="last").reindex(S)[T].astype("float32")
    del px; gc.collect()
    # features at session D use prior closes: shift so column D has T-1 info... actually we index by D and use shift(1)
    rN = {}; 
    for N in (1,3,5,10,20,60):
        rN[N] = (C / C.shift(N) - 1).shift(1)  # return over N sessions ending T-1, known at D open
    vr = (V / V.shift(1).rolling(20, min_periods=20).mean()).shift(1)
    # N-day net reading: rolling sum of daily net over N sessions ending at D (inclusive of D's open = filings effective on D)
    RN = {N: pd.DataFrame(M, index=T, columns=S).T.rolling(N, min_periods=N).sum().T for N in (1,3,5,10,20,60)}
    # for validity: window start >= first_ok
    validN = {N: (np.arange(nS) - N + 1) >= first_ok for N in (1,3,5,10,20,60)}

    # precompute sector/industry groups for rank
    sec_groups = {}
    for t,s in sec_of.items():
        sec_groups.setdefault(s, []).append(ti[t])
    ind_groups = {}
    for t,ind in ind_of.items():
        if pd.isna(ind): continue
        ind_groups.setdefault(ind, []).append(ti[t])

    def rank_top10(mat, groups):
        """mat (nT,nS) -> bool top 10% within group (higher better)."""
        out = np.zeros_like(mat, dtype=bool)
        for members in groups.values():
            if len(members) < 5: continue
            sub = mat[members]
            # rank pct high=1
            order = np.argsort(np.argsort(sub, axis=0), axis=0)
            pct = order / max(len(members)-1, 1)
            out[members] = pct >= 0.90
        return out

    def rank_bot10(mat, groups):
        out = np.zeros_like(mat, dtype=bool)
        for members in groups.values():
            if len(members) < 5: continue
            sub = mat[members]
            order = np.argsort(np.argsort(sub, axis=0), axis=0)
            pct = order / max(len(members)-1, 1)
            out[members] = pct <= 0.10
        return out

    def mkt_top10(mat):
        order = np.argsort(np.argsort(mat, axis=0), axis=0)
        pct = order / max(nT-1, 1)
        return pct >= 0.90
    def mkt_bot10(mat):
        order = np.argsort(np.argsort(mat, axis=0), axis=0)
        pct = order / max(nT-1, 1)
        return pct <= 0.10

    # answer each net-buy id -> (nT, nS) uint8 codes
    codes = {i: np.zeros((nT, nS), np.uint8) for i in ids}  # own stay 0

    hist_win = {1:60,3:60,5:60,10:60,20:100,60:300}

    for rid in nb_ids:
        N = int(id_meta.loc[rid,"N"]); lens = id_meta.loc[rid,"lens"]; but = "-BUT" in rid
        R = RN[N].values  # (nT,nS)
        ok = validN[N]
        ok2 = np.broadcast_to(ok, (nT, nS))
        if lens == "fixed threshold":
            # 1d net >= 1e6 (or <= -1e6) held on each of last N sessions
            d1 = RN[1].values
            thr_ok = d1 >= 1e6 if not but else d1 <= -1e6
            # rolling min of thr_ok over N
            held = pd.DataFrame(thr_ok.astype(float).T).rolling(N, min_periods=N).min().T.values == 1
            yes = held & ok2
            ready = ok2 & np.isfinite(d1)
        elif lens == "extreme vs own history":
            W = hist_win[N]
            # prior W sessions of R, exclude today
            qhi = pd.DataFrame(R.T).shift(1).rolling(W, min_periods=W).quantile(0.95).T.values
            qlo = pd.DataFrame(R.T).shift(1).rolling(W, min_periods=W).quantile(0.05).T.values
            cnt = pd.DataFrame(R.T).shift(1).rolling(W, min_periods=W).count().T.values
            yes = (((R > 0) & (R >= qhi)) if not but else ((R < 0) & (R <= qlo))) & ok2 & (cnt >= W)
            ready = ok2 & (pd.DataFrame(R.T).shift(1).rolling(W, min_periods=W).count().T.values >= W)
        elif lens == "change since last value":
            prev = np.full_like(R, np.nan); prev[:, N:] = R[:, :-N]
            # rises >=10% relative; careful with sign of net
            chg = (R - prev) / np.maximum(np.abs(prev), 1.0)
            yes = ((chg >= 0.10) if not but else (chg <= -0.10)) & ok2 & np.isfinite(prev) & (np.abs(prev) > 0)
            ready = ok2 & np.isfinite(prev) & (np.abs(prev) > 0)
        elif lens == "cross":
            d1 = RN[1].values
            prev = np.full_like(d1, np.nan); prev[:,1:] = d1[:,:-1]
            if not but:
                yes = (prev < 1e6) & (d1 >= 1e6) & ok2 & np.isfinite(prev)
            else:
                yes = (prev >= -1e6) & (d1 < -1e6) & ok2 & np.isfinite(prev)
            ready = ok2 & np.isfinite(prev)
        elif lens == "streak":
            d1 = RN[1].values
            up = np.zeros_like(d1, dtype=bool); up[:,1:] = d1[:,1:] > d1[:,:-1]
            dn = np.zeros_like(d1, dtype=bool); dn[:,1:] = d1[:,1:] < d1[:,:-1]
            series = up if not but else dn
            held = pd.DataFrame(series.astype(float).T).rolling(N, min_periods=N).min().T.values == 1
            yes = held & ok2
            ready = ok2 & (np.arange(nS) >= N)  # need N diffs
            ready = np.broadcast_to(np.arange(nS) >= (first_ok + N), (nT,nS))
        elif lens == "divergence vs price":
            # price N-d change vs R change vs R N sessions ago
            prev = np.full_like(R, np.nan); prev[:, N:] = R[:, :-N]
            dR = R - prev
            pr = rN[N].reindex(columns=T).to_numpy().T  # (nT,nS)
            if not but:
                yes = (pr < 0) & (dR > 0) & ok2 & np.isfinite(pr) & np.isfinite(prev)
            else:
                yes = (pr > 0) & (dR < 0) & ok2 & np.isfinite(pr) & np.isfinite(prev)
            ready = ok2 & np.isfinite(pr) & np.isfinite(prev)
        elif lens == "divergence vs volume":
            prev = np.full_like(R, np.nan); prev[:, N:] = R[:, :-N]
            dR = R - prev
            # volume change over N: use vr proxy at D vs D-N roughly
            vnow = vr.reindex(columns=T).to_numpy().T
            vprev = np.full_like(vnow, np.nan); vprev[:, N:] = vnow[:, :-N]
            dv = vnow - vprev
            if not but:
                yes = (dv < 0) & (dR > 0) & ok2 & np.isfinite(dv) & np.isfinite(prev)
            else:
                yes = (dv > 0) & (dR < 0) & ok2 & np.isfinite(dv) & np.isfinite(prev)
            ready = ok2 & np.isfinite(dv) & np.isfinite(prev)
        elif lens == "rank vs sector":
            top = rank_top10(R, sec_groups); bot = rank_bot10(R, sec_groups)
            act = (R > 0) if not but else (R < 0)
            yes = (top if not but else bot) & ok2 & act
            ready = ok2
        elif lens == "rank vs industry":
            top = rank_top10(R, ind_groups); bot = rank_bot10(R, ind_groups)
            act = (R > 0) if not but else (R < 0)
            has = np.zeros(nT, bool)
            for tk_,ind in ind_of.items():
                if pd.notna(ind): has[ti[tk_]] = True
            ready = ok2 & has[:, None]
            yes = (top if not but else bot) & ready & act
        elif lens == "rank vs theme":
            # no theme membership map on box -> all NR
            yes = np.zeros((nT,nS), bool); ready = np.zeros((nT,nS), bool)
        elif lens == "rank vs SPY/market":
            top = mkt_top10(R); bot = mkt_bot10(R)
            act = (R > 0) if not but else (R < 0)
            yes = (top if not but else bot) & ok2 & act
            ready = ok2
        else:
            raise ValueError(lens)
        codes[rid] = np.where(ready, np.where(yes, 2, 1), 0).astype(np.uint8)
        print(rid, "YES%", round((codes[rid]==2).mean()*100,3), "NR%", round((codes[rid]==0).mean()*100,3), flush=True)

    # write per year x sector (one F4TR file per FRESH file; FRESH uses underscores)
    for y in range(2020, 2025):
        flist = sorted(CH.glob(f"{y}__FRESH__*.parquet"))
        for fres in flist:
            sec = fres.name.split("__FRESH__")[1].replace(".parquet","").rsplit("_part",1)[0]
            if True:
                key = pd.read_parquet(fres, columns=["ticker", "date"])
                tix = key.ticker.map(ti)
                six = key.date.apply(lambda d: kidx.get(pd.Timestamp(d)))
                mask = tix.notna() & six.notna()
                arr = np.zeros((len(key), len(ids)), np.uint8)
                ii = np.where(mask.values)[0]
                if len(ii):
                    tt = tix[mask].astype(int).values
                    ss = six[mask].astype(int).values
                    for j, rid in enumerate(ids):
                        arr[ii, j] = codes[rid][tt, ss]
                fn = CH / fres.name.replace("__FRESH__", "__F4TR__")
                pd.DataFrame({
                    "ticker": key.ticker.astype(str),
                    "date": key.date.astype(str),
                    "packed": list(pack(arr)),
                }).to_parquet(fn, index=False)
                meta = dict(
                    year=y, sector=sec, layout="rows ticker-major then date; packed=2-bit 0=NR 1=NO 2=YES along ids",
                    addon="Theme Radar Form 4: net-buy USD from DERA P/S; insider ownership % NR (no PIT shares outstanding)",
                    tags_file="out/tags/theme-radar_f4_tags.csv", tags_sha256=SHA,
                    point_in_time="filing counts from effective_date (= next NYSE open after filing_date)",
                    dedupe="accession_number+is_derivative+transaction_sk",
                    codes="P=buy S=sell; 4/A excluded; non-derivative only",
                    insider_own_pct="ALL NR — no point-in-time shares-outstanding feed on box (only current Finviz Shares_outstanding_M_.csv)",
                    n_ids=len(ids), ids=ids, survivor_only=True, sector_map="current_backfilled",
                )
                json.dump(meta, open(str(fn)[:-8] + ".json", "w"), indent=1)
                print(y, fres.name, len(key), "NR", round(float((arr == 0).mean()), 3), flush=True)
        print("year", y, "done", round(time.time() - t0), flush=True)
    print("ALL", round(time.time() - t0), flush=True)

if __name__ == "__main__":
    main()
