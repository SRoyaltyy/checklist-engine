"""Full buyable universe outcomes 2020-24 (lean). Same labels as trajectory/traj_run.py."""
import hashlib, numpy as np, pandas as pd
END = pd.Timestamp("2024-12-31"); FEE = 0.006
PX = "/workspace/pricehist/universe_2020_survivors.parquet"
h = hashlib.sha256(); f = open(PX, "rb")
for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
assert h.hexdigest() == "fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337"
P = pd.read_parquet(PX, filters=[("date", "<=", END)], columns=["ticker","date","open","high","close"])
P["ticker"] = P.ticker.astype(str); P["date"] = pd.to_datetime(P.date).astype("datetime64[ns]"); assert P.date.max() <= END
P = P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True)
tk = P.ticker.values; N = len(P); O = P.open.values; Hh = P.high.values; Cc = P.close.values
def sh(a, d):
    o = np.full(N, np.nan); o[:N-d] = a[d:]; same = np.zeros(N, bool); same[:N-d] = tk[d:] == tk[:N-d]; o[~same] = np.nan; return o
e = O; tp = e*1.2; ex = np.full(N, np.nan)
for d in range(15):
    od, hd = sh(O, d), sh(Hh, d); t = np.isnan(ex) & (hd >= tp); ex[t] = np.maximum(od[t], tp[t])
c14, c9, c20 = sh(Cc, 14), sh(Cc, 9), sh(Cc, 20)
rA = np.where(np.isnan(ex), c14, ex)/e - 1 - FEE; rB = c9/e - 1 - FEE
U = pd.DataFrame(dict(ticker=P.ticker, date=P.date, rA=rA.astype(np.float32), rB=rB.astype(np.float32)))[~np.isnan(c20)]
del P, O, Hh, Cc, ex, c14, c9, c20, rA, rB, tp
M = pd.read_parquet("/workspace/state_test/story_q/panel.parquet", columns=["ticker","date"]); M["ticker"] = M.ticker.astype(str); M["date"] = pd.to_datetime(M.date).astype("datetime64[ns]")
U = U.merge(M[M.date <= END], on=["ticker","date"]); del M
Dr = pd.read_csv("/workspace/state_test/buyable_filter/drop_list_v2.csv", parse_dates=["date"]); Dr["drop"] = True
U = U.merge(Dr, on=["ticker","date"], how="left"); U = U[U["drop"].isna()].drop(columns="drop"); del Dr
U = U[np.isfinite(U.rA) & np.isfinite(U.rB)].sort_values(["ticker","date"]).reset_index(drop=True)
for v in "AB": U["x"+v] = (U["r"+v] - U.groupby("date")["r"+v].transform("mean")).astype(np.float32)
U.to_parquet("/workspace/tmp_utv2/U.parquet"); print(len(U), U.date.min(), U.date.max(), U.ticker.nunique())
