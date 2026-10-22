#!/usr/bin/env python3
"""Theme Radar Form 4 answers -> chunks/{y}__F4TR__{sector}.parquet, 2025-01-01..2026-06-30. BLIND: no prices read.
Copy of f4tr_year.py; changes: DERA 2023-24 (history) + 2025-26; calendar = FRESH key dates; price rows NR; sessions after DERA coverage NR.
Net-buy $ from DERA P/S; insider ownership % = NR (no PIT shares outstanding on box)."""
import json, hashlib, gc, time
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
CH = HERE / "chunks"
import os
F4 = Path("/workspace/data/edgar_form4/dera_2020_24")
F4B = Path(os.environ.get("F4B", "/MISSING_JAMES_PATH"))          # James's 2025Q1-2026Q2 parquet dir: form4_2025.parquet, form4_2026.parquet
END = os.environ.get("END", "2026-06-30")
COVER_END = os.environ.get("COVER_END", END)                      # last session with complete filings; later sessions NR
YEARS = tuple(int(y) for y in os.environ.get("YEARS", "2025,2026").split(","))
OUTDIR = Path(os.environ.get("OUTDIR", str(Path(__file__).resolve().parent / "chunks")))
HIST_YEARS = tuple(int(y) for y in os.environ.get("HIST_YEARS", "2023,2024").split(","))
# (no price path: blind build)
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
    flt = [("transaction_code","in",["P","S"])]
    def rd(path):
        have = set(pq.ParquetFile(path).schema_arrow.names)
        d = pd.read_parquet(path, columns=[c for c in cols if c in have], filters=flt)
        if "is_derivative" in d: d = d[~d.is_derivative.astype(bool)]
        else: d["is_derivative"] = False
        if "is_amendment" not in d: d["is_amendment"] = False
        return d
    parts = [rd(F4 / f"form4_{y}.parquet") for y in HIST_YEARS]
    for y in (2025, 2026):
        f = F4B / f"form4_{y}.parquet"
        if f.exists(): parts.append(rd(f))
        elif y in YEARS: raise SystemExit(f"missing {f} (set F4B to James's dir)")
    x = pd.concat(parts, ignore_index=True)
    x["is_amendment"] = x.is_amendment.astype(bool)
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

    funds = set(pd.read_csv(HERE/"nb_cache/fund_exclusion_tickers.csv").ticker)
    keyfiles = [f for y in YEARS for f in sorted(CH.glob(f"{y}__FRESH__*.parquet"))]
    # same universe rule as 2020-24 (tickers with a bar in the window); reads ticker+date columns only, never prices
    lst = pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet", columns=["ticker","date"],
        filters=[("date",">=",pd.Timestamp(f"{HIST_YEARS[0]}-01-01")),("date","<=",pd.Timestamp(END))])
    tickers = sorted(set(lst.ticker.astype(str)) - funds); del lst
    secmap = pd.read_csv(SECT, usecols=["Ticker","Sector","Industry"]).dropna(subset=["Ticker"]).drop_duplicates("Ticker")
    secmap["Ticker"] = norm(secmap.Ticker)
    sec_of = secmap.set_index("Ticker").Sector.reindex(tickers).fillna("Unknown")
    ind_of = secmap.set_index("Ticker").Industry.reindex(tickers)

    # NYSE sessions = FRESH chunk key dates (dates only, no prices)
    dd = set()
    for f in sorted(CH.glob("202[3456]__FRESH__*.parquet")):
        dd |= set(pd.read_parquet(f, columns=["date"]).date.unique())
    S = pd.DatetimeIndex(sorted(pd.to_datetime(sorted(dd))))
    S = S[(S >= f"{HIST_YEARS[0]}-01-01") & (S <= END)].values.astype("datetime64[ns]")
    kidx = {pd.Timestamp(d): i for i,d in enumerate(S)}
    nS = len(S)
    first_ok = 1  # first session after the first history filing date
    last_ok = int(np.searchsorted(S, np.datetime64(COVER_END,"ns"), side="right")) - 1
    # daily net matrix (nT, nS)
    T = tickers
    ti = {t:i for i,t in enumerate(T)}; nT = len(T)
    M = np.zeros((nT, nS), dtype=np.float64)
    net = net[net.ticker.isin(ti)]
    for tk, d, v in zip(net.ticker, net.date, net.net):
        j = kidx.get(pd.Timestamp(d))
        if j is not None: M[ti[tk], j] += v
    del net; gc.collect()

    # BLIND: no price/volume loaded for 2025-26; divergence rows are NR
    # N-day net reading: rolling sum of daily net over N sessions ending at D (inclusive of D's open = filings effective on D)
    RN = {N: pd.DataFrame(M, index=T, columns=S).T.rolling(N, min_periods=N).sum().T for N in (1,3,5,10,20,60)}
    # for validity: window start >= first_ok
    validN = {N: ((np.arange(nS) - N + 1) >= first_ok) & (np.arange(nS) <= last_ok) for N in (1,3,5,10,20,60)}

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
            ready = np.broadcast_to((np.arange(nS) >= (first_ok + N)) & (np.arange(nS) <= last_ok), (nT,nS))
        elif lens in ("divergence vs price", "divergence vs volume"):
            yes = np.zeros((nT,nS), bool); ready = np.zeros((nT,nS), bool)   # BLIND rule: no prices for 2025-26
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
        0 and print(rid, "YES%", round((codes[rid]==2).mean()*100,3), "NR%", round((codes[rid]==0).mean()*100,3), flush=True)

    # write per year x sector (one F4TR file per FRESH file; FRESH uses underscores)
    for y in YEARS:
        flist = sorted(CH.glob(f"{y}__FRESH__*.parquet"))
        for fres in flist:
            sec = fres.name.split("__FRESH__")[1].replace(".parquet","").rsplit("_part",1)[0]
            if True:
                key = pd.read_parquet(fres, columns=["ticker", "date"]); key = key[key.date.astype(str) <= END].reset_index(drop=True)
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
                OUTDIR.mkdir(parents=True, exist_ok=True); fn = OUTDIR / fres.name.replace("__FRESH__", "__F4TR__")
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
                    n_ids=len(ids), ids=ids, survivor_only=True, sector_map="current_backfilled", date_end=END,
                    blind="no prices/returns read; divergence vs price/volume rows (24) NR",
                    dera_source=str(F4B), cover_end=COVER_END,
                )
                json.dump(meta, open(str(fn)[:-8] + ".json", "w"), indent=1)
                print(y, fres.name, len(key), flush=True)
        print("year", y, "done", round(time.time() - t0), flush=True)
    print("ALL", round(time.time() - t0), flush=True)

if __name__ == "__main__":
    main()
