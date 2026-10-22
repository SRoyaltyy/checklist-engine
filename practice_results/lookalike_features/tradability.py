"""PROVISIONAL tradability filter (pluggable). Manager Bot ruling: ONE shared filter file will come from Taskforce and be frozen in
lock index v9; set env TRADABILITY_FILE=<that parquet/csv with ticker,date,tradable> to swap this implementation out.
Own implementation of fullscan research/hot_n4_clean_v4/PREREG.md (liquid gate) as of D, bars < D:
  mcap_m >= 100 (MIN_MCAP_M), avg volume 20d >= 500k shares (MIN_AVG_VOL_K), volume(D-1) > 0, Industry != Exchange Traded Fund, no price floor;
  plus SPAC-shell drop: ticker ends -U/-WS/-R, or flat near $10 (>=80% of prior 60 closes in [9.5,10.5] and 60-bar range < 6% of median).
Market cap 2020-24 = PROXY: Finviz `Shares Outstanding` (fullscan data/finviz/latest.csv, commit 1a8f969a3c, 2026-10-21) x close(D-1).
There is no point-in-time shares/mcap feed for 2020-24 on the box, so this is not truly PIT for share count. Missing shares -> fails mcap."""
import os, numpy as np, pandas as pd, pyarrow.parquet as pq
FV = "/workspace/fullscan/data/finviz/latest.csv"
def tradable(cells, px):
    """cells: DataFrame ticker,date. px: price rows (ticker,date,close,volume) <= 2024. Returns DataFrame with rule flags + tradable."""
    d = os.environ.get("TASKFORCE_DROP")
    if d:  # Taskforce buyable_filter_v1 drop_list_v2 (liquidity+SPAC+partial ETF; mcap NOT applied). Rows > 2024 discarded on read.
        D = pd.concat([c[c.date <= "2024-12-31"] for c in pd.read_csv(d, chunksize=2_000_000, dtype=str)]); D["date"] = pd.to_datetime(D.date)
        D["fail_taskforce_drop_v2"] = True; X = cells.merge(D, on=["ticker", "date"], how="left")
        X["fail_taskforce_drop_v2"] = X.fail_taskforce_drop_v2.fillna(False).astype(bool); X["tradable"] = ~X.fail_taskforce_drop_v2
        return X[["ticker", "date", "fail_taskforce_drop_v2", "tradable"]]
    f = os.environ.get("TRADABILITY_FILE")
    if f:
        T = pd.read_parquet(f) if f.endswith(".parquet") else pd.read_csv(f, parse_dates=["date"])
        return cells.merge(T[["ticker", "date", "tradable"]], on=["ticker", "date"], how="left").fillna({"tradable": False})
    fv = pd.read_csv(FV, usecols=["Ticker", "Industry", "Shares Outstanding"]).drop_duplicates("Ticker").set_index("Ticker")
    p = px.sort_values(["ticker", "date"]).copy(); g = p.groupby("ticker")
    p["c1"] = g.close.shift(1); p["v1"] = g.volume.shift(1)
    p["av20"] = g.volume.transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    nr = g.close.transform(lambda s: s.shift(1).between(9.5, 10.5).astype(float).rolling(60, min_periods=60).mean())
    hi = g.close.transform(lambda s: s.shift(1).rolling(60, min_periods=60).max()); lo = g.close.transform(lambda s: s.shift(1).rolling(60, min_periods=60).min())
    md = g.close.transform(lambda s: s.shift(1).rolling(60, min_periods=60).median())
    p["flat10"] = (nr >= 0.8) & ((hi - lo) / md < 0.06)
    X = cells.merge(p[["ticker", "date", "c1", "v1", "av20", "flat10"]], on=["ticker", "date"], how="left")
    sh = X.ticker.map(fv["Shares Outstanding"]); ind = X.ticker.map(fv["Industry"])
    X["fail_etf"] = ind.eq("Exchange Traded Fund")
    X["fail_spac_suffix"] = X.ticker.str.contains(r"-(U|WS|R)$|\.(U|WS|R)$", regex=True)
    X["fail_spac_flat10"] = X.flat10.fillna(False).astype(bool)
    X["fail_mcap"] = ~((sh * X.c1) >= 100)
    X["fail_avgvol"] = ~(X.av20 >= 500_000)
    X["fail_vol0"] = ~(X.v1 > 0)
    F = [c for c in X if c.startswith("fail_")]; X["tradable"] = ~X[F].any(axis=1)
    return X[["ticker", "date"] + F + ["tradable"]]
