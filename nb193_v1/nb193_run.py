"""NB193_V1 run — rules in NB193_V1_RULES.md (committed first). PRACTICE 2020-24, HINT, survivors-only, full buyable universe."""
import hashlib, json, numpy as np, pandas as pd
from scipy.stats import norm
END = pd.Timestamp("2024-12-31"); FEE = 0.006; HMAX = 21; TG = "/workspace/nb193_in/nb_tags_v1"
PX = "/workspace/pricehist/universe_2020_survivors.parquet"
h = hashlib.sha256(); f = open(PX, "rb")
for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
assert h.hexdigest() == "fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337"
P = pd.read_parquet(PX, filters=[("date", "<=", END)], columns=["ticker","date","open","high","close"])
P["ticker"] = P.ticker.astype(str); P["date"] = pd.to_datetime(P.date).astype("datetime64[ns]")
P = P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True); P["i"] = np.arange(len(P)); N = len(P); tk = P.ticker.values
assert P.date.max() <= END
M = pd.read_parquet("/workspace/state_test/story_q/panel.parquet", columns=["ticker","date"]); M["ticker"] = M.ticker.astype(str); M["date"] = pd.to_datetime(M.date).astype("datetime64[ns]")
M = M[M.date <= END]
Dr = pd.read_csv("/workspace/state_test/buyable_filter/drop_list_v2.csv", parse_dates=["date"]); Dr["drop"] = True
M = M.merge(Dr, on=["ticker","date"], how="left"); M = M[M["drop"].isna()].drop(columns="drop")
M = M.merge(P[["ticker","date","i"]], on=["ticker","date"])
idx = M.i.values[:, None] + np.arange(HMAX); ok = idx[:, -1] < N; idx = np.minimum(idx, N-1); ok &= tk[idx[:, -1]] == M.ticker.values
M = M[ok].reset_index(drop=True); idx = idx[ok]
O, H, C = (P[k].values.astype(np.float64)[idx] for k in ["open","high","close"]); del P
e = O[:, 0]; tp = e*1.2; ex = np.full(len(M), np.nan)
for d in range(15):
    t = np.isnan(ex) & (H[:, d] >= tp); ex[t] = np.maximum(O[t, d], tp[t])
M["rA"] = np.where(np.isnan(ex), C[:, 14], ex)/e - 1 - FEE; M["rB"] = C[:, 9]/e - 1 - FEE; del O, H, C, idx
M = M[np.isfinite(M.rA) & np.isfinite(M.rB)]
for v in "AB": M["x"+v] = M["r"+v] - M.groupby("date")["r"+v].transform("mean")
J = json.load(open(f"{TG}/nb_tags_ids.json")); ids = J["ids"]
req = pd.read_csv("for_james_step3.csv"); pos = [ids.index(r) for r in req.row_id]
parts = []
for y in range(2020, 2025):
    d = pd.read_parquet(f"{TG}/nb_tags_{y}.parquet"); d["ticker"] = d.ticker.astype(str); d["date"] = pd.to_datetime(d.date).astype("datetime64[ns]")
    assert d.date.max() <= END
    b = np.frombuffer(b"".join(d.packed.values), np.uint8).reshape(len(d), -1)
    A = np.stack([(b >> s) & 3 for s in (0, 2, 4, 6)], -1).reshape(len(d), -1)[:, :len(ids)][:, pos]
    parts.append(pd.concat([d[["ticker","date"]].reset_index(drop=True), pd.DataFrame(A, columns=req.row_id)], axis=1))
T = pd.concat(parts, ignore_index=True); del parts
X = T.merge(M[["ticker","date","rA","rB","xA","xB"]], on=["ticker","date"])
print("tag rows", len(T), "tradable", len(X), "buyable control days", len(M))
yr = X.date.dt.year.values; dt = X.date.values
rng = np.random.default_rng(13); out = []
def stats(sel, v):
    r = X["r"+v].values[sel]; xx = X["x"+v].values[sel]
    if len(r) == 0: return dict(n=0)
    g = pd.DataFrame(dict(d=dt[sel], x=xx)).groupby("d").x.agg(["sum","count"]); sx, dn = g["sum"].values, g["count"].values
    bb = rng.integers(0, len(dn), (500, len(dn))); bs = sx[bb].sum(1)/dn[bb].sum(1); se = bs.std()
    z = xx.mean()/se if se > 0 else 0
    return dict(n=len(r), win=(r > 0).mean()*100, mean=r.mean()*100, excess=xx.mean()*100, p=2*norm.sf(abs(z)))
for c in req.row_id:
    a = X[c].values; yes = a == 2
    row = dict(row_id=c, n_answered=int((a > 0).sum()), n_yes=int(yes.sum()), yes_share=yes.sum()/max((a > 0).sum(), 1))
    for per, pm in (("d", yr <= 2022), ("c", yr >= 2023)):
        for v in "AB":
            for kk, vv in stats(yes & pm, v).items(): row[f"{v}_{per}_{kk}"] = vv
    out.append(row)
R = pd.DataFrame(out); ntest = len(R); fam = 10112 + 2*ntest
allp = np.r_[R.A_d_p.fillna(1).values, R.B_d_p.fillna(1).values]
o = np.argsort(allp); a = allp[o]*fam/np.arange(1, len(allp)+1); a = np.minimum.accumulate(a[::-1])[::-1]; q = np.empty(len(allp)); q[o] = np.minimum(a, 1)
R["A_d_q"] = q[:ntest]; R["B_d_q"] = q[ntest:]; R["bh_family"] = fam
for v, nm in (("A","exit_v1"),("B","10d")):
    base = (R[f"{v}_d_n"] >= 30) & (R[f"{v}_c_n"] >= 30) & (R[f"{v}_d_win"] > 55) & (R[f"{v}_c_win"] > 55) & (R[f"{v}_d_excess"] > 0) & (R[f"{v}_c_excess"] > 0)
    R[f"pass_{nm}_noBH"] = base; R[f"pass_{nm}"] = base & (R[f"{v}_d_q"] < 0.1)
R = req.merge(R, on="row_id")
def status(r):
    if r.n_yes == 0: return "NOT_COMPUTABLE: never YES on a tradable 2020-24 buyable day"
    if min(r.A_d_n, r.A_c_n) < 30: return "TOO_RARE: <30 YES trades in a period"
    return "PASS" if (r.pass_exit_v1 or r.pass_10d) else "FAIL"
R["status"] = [status(r) for r in R.itertuples()]
ern = R.row_id.str.contains("ERN-|NB-014|NB-022|NB-023|NB-024|NB-091")
R["flags"] = "HINT; SURVIVORS-ONLY; mcap filter not applied" + np.where(R.yes_share >= 0.99, "; ALWAYS-YES", "") \
    + np.where(ern, "; earnings caveats (consensus may be back-filled, reaction day +-1, AVWAP from daily bars)", "") \
    + np.where(ern & (R.status == "PASS"), "; POSSIBLE LOOK-AHEAD (HINT only, not a keep)", "")
R.round(4).to_csv("nb193_results_v1.csv", index=False)
print("tests", ntest, "family", fam); print(R.status.str.split(":").str[0].value_counts())
print("noBH near-pass:\n", R[R.pass_exit_v1_noBH | R.pass_10d_noBH][["row_id","A_d_n","A_d_win","A_c_n","A_c_win","B_d_win","B_c_win","A_d_q","B_d_q"]].to_string())
print(R[R.status == "PASS"].T.to_string())
