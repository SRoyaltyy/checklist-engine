#!/usr/bin/env python3
"""JA_F4X add-on: SEC-JA-F4-182 same-issuer 2+ distinct insider open-market buys (P) in last 10 sessions.
Tag locked BEFORE any YES rates: engine/out/tags/james_f4_182_tags.csv
PIT: filing counts from D+1 open (effective_date). Last 10 sessions at D = effective_date in those 10 sessions ending at D.
Source: dera_2020_24 only. Leaves JA_F4 chunks untouched."""
import sys, json, re, gc, time, hashlib
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nb_year as NB
F4 = Path("/workspace/data/edgar_form4/dera_2020_24")
TAGS = HERE.parent / "out/tags/james_f4_182_tags.csv"
IDS = ["SEC-JA-F4-182"]
SHA = open(str(TAGS) + ".sha256").read().split()[0]

def norm(s):
    return s.astype(str).str.strip().str.upper().str.replace(r"[./ ]", "-", regex=True)

def main(years):
    assert SHA == hashlib.sha256(TAGS.read_bytes()).hexdigest()
    t0 = time.time()
    cur = pd.read_csv(NB.SECT, usecols=["Ticker", "Sector", "Industry"]).dropna(subset=["Ticker"]).drop_duplicates("Ticker").set_index("Ticker")
    spy = NB.sessions_all()
    spy = spy[(spy.index >= "2019-10-01") & (spy.index <= "2024-12-31")]
    S = spy.index.values
    nS = len(S)
    first_ok = int(np.searchsorted(S, np.datetime64("2020-01-03")))
    valid10 = (np.arange(nS) - 9) >= first_ok

    cols = ["accession_number", "ticker", "issuer_cik", "reporting_owner_cik", "is_amendment",
            "effective_date", "transaction_code", "is_derivative", "transaction_sk", "shares", "price"]
    x = pd.concat([
        pd.read_parquet(F4 / f"form4_{y}.parquet", columns=cols,
            filters=[("is_derivative", "=", False), ("transaction_code", "=", "P")])
        for y in range(2020, 2025)
    ])
    x = x[~x.is_amendment & x.ticker.notna()].copy()
    x["ticker"] = norm(x.ticker)
    x = x[x.ticker.isin(cur.index)]
    x["eff"] = pd.to_datetime(x.effective_date)
    x = x[x.eff <= S[-1]]
    x["k"] = np.searchsorted(S, x.eff.values)

    # expand each buy into the next 10 session indices (so at day D, window covers k in [D-9, D])
    rows = []
    for o in range(10):
        z = x[["ticker", "k", "reporting_owner_cik", "issuer_cik"]].copy()
        z["k"] = z.k + o
        rows.append(z)
    z = pd.concat(rows)
    z = z[z.k < nS]
    # YES when 2+ distinct owner CIKs at same issuer (ticker) in the window
    g = z.groupby(["ticker", "k"]).reporting_owner_cik.nunique()
    yes_pairs = set(g[g >= 2].index.tolist())
    del z, rows, g
    gc.collect()
    print(f"yes_cells_raw={len(yes_pairs)} t={time.time()-t0:.0f}s", flush=True)

    tick_all = sorted(set(pd.read_parquet(NB.CACHE / "last.parquet").date.index) - set(pd.read_csv(NB.CACHE / "fund_exclusion_tickers.csv").ticker))
    p = pd.read_parquet(NB.PX, columns=["ticker", "date", "close"],
        filters=[("date", ">=", pd.Timestamp("2019-08-01")), ("date", "<=", pd.Timestamp("2024-12-31"))])
    p["ticker"] = p.ticker.astype(str)
    p["date"] = p.date.astype("datetime64[ns]")
    C = p.pivot_table(index="date", columns="ticker", values="close", aggfunc="last").reindex(S).astype("float32")
    del p
    gc.collect()
    # last bar before D
    close_at_D = C.shift(1)

    cov_all = []
    cheap_yes = under2_yes = yes_total = 0
    for y in years:
        ky = np.where((S >= np.datetime64(f"{y}-01-01")) & (S <= np.datetime64(f"{y}-12-31")))[0]
        ys = S[ky]
        A = np.zeros((len(tick_all), len(ky), 1), np.uint8)
        tpos = {t: j for j, t in enumerate(tick_all)}
        for ti, t in enumerate(tick_all):
            if t not in cur.index:
                continue  # leave 0 = NR
            for j, k in enumerate(ky):
                if not valid10[k]:
                    A[ti, j, 0] = 0
                elif (t, k) in yes_pairs:
                    A[ti, j, 0] = 2
                else:
                    A[ti, j, 0] = 1
        # cheap / under-$2 among YES (for report only; after tag lock)
        for ti, t in enumerate(tick_all):
            if t not in close_at_D.columns:
                continue
            for j, k in enumerate(ky):
                if A[ti, j, 0] != 2:
                    continue
                yes_total += 1
                px = close_at_D.iloc[k][t] if k < len(close_at_D) else np.nan
                if pd.notna(px) and px < 2:
                    under2_yes += 1
        # cheapest fifth of that day's answered universe
        day_px = close_at_D.iloc[ky].reindex(columns=[t for t in tick_all if t in close_at_D.columns])
        for j, k in enumerate(ky):
            col = day_px.iloc[j].dropna()
            if col.empty:
                continue
            cut = col.quantile(0.2)
            for ti, t in enumerate(tick_all):
                if A[ti, j, 0] != 2 or t not in col.index:
                    continue
                if col[t] <= cut:
                    cheap_yes += 1

        sec_of = cur.Sector.reindex(tick_all).fillna("Unknown")
        cov = np.zeros((1, 3), np.int64)
        dstr = ys.astype("datetime64[D]").astype(str)
        files = []
        for sec0 in sorted(sec_of.unique()):
            tk = [t for t in tick_all if sec_of[t] == sec0]
            jobs = [(sec0, tk)] if len(tk) <= 2000 else [(f"{sec0}_part{k}", tk[i:i+2000]) for k, i in enumerate(range(0, len(tk), 2000))]
            for sec, t2 in jobs:
                idx = [tick_all.index(t) for t in t2]
                U = A[idx].reshape(-1, 1)
                for kk in range(3):
                    cov[0, kk] += int((U == kk).sum())
                P = NB.pack(U)
                df = pd.DataFrame({
                    "ticker": np.repeat(t2, len(ys)),
                    "date": np.tile(dstr, len(t2)),
                    "packed": [bytes(x) for x in P],
                })
                fn = NB.CHUNKS / f"{y}__JA_F4X__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.parquet"
                df.to_parquet(fn, index=False)
                files.append(fn)
                meta = dict(
                    year=y, sector=sec,
                    layout="rows ticker-major then date; packed = 2-bit codes 0=NR 1=NO 2=YES",
                    addon="JA_F4X: SEC-JA-F4-182 same-issuer 2+ insider P buys in 10 sessions",
                    survivor_only=True,
                    source="SEC DERA form4_{y}.parquet Table I code P, 4/A excluded",
                    point_in_time="effective_date = next NYSE open after filing_date; last 10 sessions end at D",
                    tags_csv=str(TAGS), tags_sha256=SHA, n_ids=1, ids=IDS,
                    n_tickers=len(t2), n_cells=len(df),
                )
                json.dump(meta, open(str(fn).replace(".parquet", ".json"), "w"), indent=1)
        cov_df = pd.DataFrame(cov, columns=["nr", "no", "yes"], index=IDS)
        cov_df.to_csv(NB.CHUNKS / f"{y}__JA_F4X_coverage.csv")
        answered = int(cov[0, 1] + cov[0, 2])
        rate = 100.0 * cov[0, 2] / answered if answered else 0.0
        print(f"year {y} YES_rate={rate:.2f}% yes={cov[0,2]} no={cov[0,1]} nr={cov[0,0]} files={len(files)} t={time.time()-t0:.0f}s", flush=True)
        cov_all.append((y, rate, int(cov[0, 2]), int(cov[0, 1]), int(cov[0, 0])))

    print("SUMMARY", cov_all, flush=True)
    print(f"YES under_$2 share={under2_yes}/{yes_total}={100*under2_yes/max(yes_total,1):.1f}%", flush=True)
    print(f"YES cheapest_fifth share={cheap_yes}/{yes_total}={100*cheap_yes/max(yes_total,1):.1f}%", flush=True)
    print(f"tags_sha={SHA}", flush=True)

if __name__ == "__main__":
    ys = [int(a) for a in sys.argv[1:]] or [2020, 2021, 2022, 2023, 2024]
    main(ys)
