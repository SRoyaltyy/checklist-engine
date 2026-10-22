"""UNTESTED_V2 stats — rules UNTESTED_V2_RULES.md (commit 915eead1). PRACTICE 2020-24, HINT, survivors-only."""
import pickle, re, numpy as np, pandas as pd
from scipy.stats import norm
U = pd.read_parquet("/workspace/tmp_utv2/U.parquet"); assert U.date.max() <= pd.Timestamp("2024-12-31")
yr = U.date.dt.year.values; dt = U.date.values
A = {}; ANS = {}
for f in ["answers_engine.pkl", "answers_mpv.pkl"]:
    d = pickle.load(open(f"/workspace/tmp_utv2/{f}", "rb")); A.update(d["yes"]); ANS.update(d["ans"])
L = pd.read_csv("../untested_v1/untested_results_v1.csv"); L = L[L.status.str.startswith("TOO")][["list","row_id","label","col"]].reset_index(drop=True)
rng = np.random.default_rng(13); out = []
def stats(ix, v):
    if len(ix) == 0: return dict(n=0)
    r = U["r"+v].values[ix].astype(float); xx = U["x"+v].values[ix].astype(float)
    g = pd.DataFrame(dict(d=dt[ix], x=xx)).groupby("d").x.agg(["sum","count"]); sx, dn = g["sum"].values, g["count"].values
    bb = rng.integers(0, len(dn), (500, len(dn))); bs = sx[bb].sum(1)/dn[bb].sum(1); se = bs.std()
    z = xx.mean()/se if se > 0 else 0
    return dict(n=len(r), win=(r > 0).mean()*100, mean=r.mean()*100, excess=xx.mean()*100, p=2*norm.sf(abs(z)) if se > 0 else 1.0)
for c in sorted(set(L.col)):
    ix = np.unique(A.get(c, np.array([], np.int64))); row = dict(col=c, n_answered=ANS.get(c, 0), n_yes_all=len(ix), in_reader=c in A)
    for per, pm in (("d", yr[ix] <= 2022), ("c", yr[ix] >= 2023)):
        for v in "AB":
            for k, val in stats(ix[pm], v).items(): row[f"{v}_{per}_{k}"] = val
    out.append(row)
R = pd.DataFrame(out); ntest = len(R); fam = 10060 + 2*ntest
allp = np.r_[R.A_d_p.fillna(1).values, R.B_d_p.fillna(1).values]
o = np.argsort(allp); a = allp[o]*fam/np.arange(1, len(allp)+1); a = np.minimum.accumulate(a[::-1])[::-1]; q = np.empty(len(allp)); q[o] = np.minimum(a, 1)
R["A_d_q"] = q[:ntest]; R["B_d_q"] = q[ntest:]; R["bh_family"] = fam
for v, nm in (("A","exit_v1"),("B","10d")):
    base = (R[f"{v}_d_n"] >= 30) & (R[f"{v}_c_n"] >= 30) & (R[f"{v}_d_win"] > 55) & (R[f"{v}_c_win"] > 55) & (R[f"{v}_d_excess"] > 0) & (R[f"{v}_c_excess"] > 0)
    R[f"pass_{nm}_noBH"] = base; R[f"pass_{nm}"] = base & (R[f"{v}_d_q"] < 0.1)
L = L.merge(R, on="col", how="left")
# never-fires check (mechanical part; hand read in UNTESTED_RESULTS_V2.md)
L["sib_key"] = L.label
grp_yes = L.groupby("sib_key").n_yes_all.transform("sum")
def status(r, gy):
    if r.n_yes_all == 0:
        if not r.in_reader or r.n_answered == 0: return "BUG: no stored answer on any buyable day (NR everywhere) - should be BLOCKED"
        if gy == 0: return "BUG: every sibling bucket of this indicator is zero-YES while answered NO - missing data coded as NO"
        return "GENUINELY_RARE: siblings fire, this threshold never met"
    if min(r.A_d_n, r.A_c_n) < 30: return "TOO_RARE_TO_TEST"
    return "PASS" if (r.pass_exit_v1 or r.pass_10d) else "FAIL"
L["status"] = [status(r, gy) for r, gy in zip(L.itertuples(), grp_yes)]
L["flags"] = "HINT; SURVIVORS-ONLY; mcap floor not applied"
L.round(4).to_csv("untested_results_v2.csv", index=False)
L["s"] = L.status.str.split(":").str[0]
print("tests", ntest, "family", fam); print(pd.crosstab(L.s, L.list, margins=True))
print(L[L.s.isin(["PASS"]) | L.pass_exit_v1_noBH.fillna(False) | L.pass_10d_noBH.fillna(False)].round(2).T.to_string())
print(L[L.s == "FAIL"][["list","row_id","label","A_d_n","A_d_win","A_d_excess","A_c_n","A_c_win","A_c_excess","B_d_win","B_d_excess","B_c_win","B_c_excess"]].round(2).sort_values("A_c_win").tail(15).to_string())
