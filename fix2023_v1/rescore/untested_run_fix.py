"""UNTESTED_V1 run — rules in UNTESTED_V1_RULES.md (committed first). PRACTICE 2020-24, HINT, survivors-only."""
import hashlib, numpy as np, pandas as pd
from scipy.stats import norm
END = pd.Timestamp("2024-12-31"); FEE = 0.006; HMAX = 21; T = "/workspace/tmp_fix23"
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
M = M.merge(Dr, on=["ticker","date"], how="left"); M = M[M["drop"].isna()].drop(columns="drop"); del Dr
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
cells = pd.read_parquet(f"{T}/cells.parquet"); cells["ticker"] = cells.ticker.astype(str); cells["date"] = pd.to_datetime(cells.date).astype("datetime64[ns]")
cells["c"] = np.arange(len(cells)); X = cells.merge(M[["ticker","date","rA","rB","xA","xB"]], on=["ticker","date"])
ci = X.c.values; yr = X.date.dt.year.values; dt = X.date.values
print("tradable cells", len(X), "of", len(cells))
cols = {}
for k in ["JG","NB","TR","SHARED","MPV"]:
    z = np.load(f"{T}/A_{k}.npz", allow_pickle=True)
    for j, i in enumerate(z["ids"]): cols.setdefault(str(i), (k, j))
base = {}
for i, kj in cols.items(): base.setdefault(i.split("|")[0], []).append(i)
m = pd.read_csv("../../untested_v1/master_coverage.csv"); m = m[m.status == "BUILT_NOT_TESTED"]
p = pd.read_csv("../../untested_v1/map_coverage.csv"); p = p[p.status == "BUILT_NOT_TESTED"]
req = [("master", r.id, f"{r.data_type}: {r.variant}") for r in m.itertuples()] + [("map", r.row_id, r.indicator) for r in p.itertuples()]
rowcol = []
for lst, rid, lab in req:
    c = [rid] if rid in cols else base.get(rid.split("|")[0], [])
    if len(c) > 1 and rid not in cols: c = [x for x in c if x == rid.split("|")[0]] or c
    rowcol.append((lst, rid, lab, c[0] if c else None))
need = sorted({c for *_, c in rowcol if c}); Z = {}
for k in ["JG","NB","TR","SHARED","MPV"]:
    z = np.load(f"{T}/A_{k}.npz", allow_pickle=True); A = z["A"]
    for c in need:
        if cols[c][0] == k: Z[c] = A[ci, cols[c][1]]
rng = np.random.default_rng(13); out = []
def stats(sel, v):
    r = X["r"+v].values[sel]; xx = X["x"+v].values[sel]
    if len(r) == 0: return dict(n=0)
    g = pd.DataFrame(dict(d=dt[sel], x=xx)).groupby("d").x.agg(["sum","count"]); sx, dn = g["sum"].values, g["count"].values
    bb = rng.integers(0, len(dn), (500, len(dn))); bs = sx[bb].sum(1)/dn[bb].sum(1); se = bs.std()
    z = xx.mean()/se if se > 0 else 0
    return dict(n=len(r), win=(r > 0).mean()*100, mean=r.mean()*100, excess=xx.mean()*100, p=2*norm.sf(abs(z)))
for c in need:
    yes = Z[c] == 2; row = dict(col=c, n_answered=int((Z[c] > 0).sum()))
    for per, pm in (("d", yr <= 2022), ("c", yr >= 2023)):
        for v in "AB":
            for kk, vv in stats(yes & pm, v).items(): row[f"{v}_{per}_{kk}"] = vv
    out.append(row)
R = pd.DataFrame(out); ntest = len(R); fam = 6802 + 2*ntest
allp = np.r_[R.A_d_p.fillna(1).values, R.B_d_p.fillna(1).values]
o = np.argsort(allp); a = allp[o]*fam/np.arange(1, len(allp)+1); a = np.minimum.accumulate(a[::-1])[::-1]; q = np.empty(len(allp)); q[o] = np.minimum(a, 1)
R["A_d_q"] = q[:ntest]; R["B_d_q"] = q[ntest:]; R["bh_family"] = fam
for v, nm in (("A","exit_v1"),("B","10d")):
    R[f"pass_{nm}"] = (R[f"{v}_d_n"] >= 30) & (R[f"{v}_c_n"] >= 30) & (R[f"{v}_d_win"] > 55) & (R[f"{v}_c_win"] > 55) & (R[f"{v}_d_excess"] > 0) & (R[f"{v}_c_excess"] > 0) & (R[f"{v}_d_q"] < 0.1)
    R[f"pass_{nm}_noBH"] = R[f"pass_{nm}"] | ((R[f"{v}_d_n"] >= 30) & (R[f"{v}_c_n"] >= 30) & (R[f"{v}_d_win"] > 55) & (R[f"{v}_c_win"] > 55) & (R[f"{v}_d_excess"] > 0) & (R[f"{v}_c_excess"] > 0))
L = pd.DataFrame(rowcol, columns=["list","row_id","label","col"]).merge(R, on="col", how="left")
def status(r):
    if r.col is None or pd.isna(r.col): return "NOT_COMPUTABLE: no stored answer column"
    if r.n_answered == 0: return "NOT_COMPUTABLE: answered NR on every tradable 2020-24 cell"
    if min(r.A_d_n, r.A_c_n) < 30: return "TOO_FEW: <30 YES trades in a period"
    return "PASS" if (r.pass_exit_v1 or r.pass_10d) else "FAIL"
L["status"] = [status(r) for r in L.itertuples()]
L["flags"] = "HINT; SURVIVORS-ONLY; mcap filter not applied"
L.round(4).to_csv("untested_results_v1_fix2023.csv", index=False)
print("tests", ntest, "family", fam); print(L.groupby("list").status.value_counts())
print("noBH near-pass", L[L.pass_exit_v1_noBH | L.pass_10d_noBH][["list","row_id","label"]].to_string())
