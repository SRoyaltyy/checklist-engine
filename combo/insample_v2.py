# 2020-22 discovery-period numbers on the 295,054 filtered training rows (in-sample; same rules as the check)
import json, numpy as np, pandas as pd, joblib
from scipy.stats import norm
M = joblib.load("COMBO_MODEL_V2_frozen.joblib"); names = M["features"]
K = pd.read_parquet("keys_labels.parquet"); keep = np.load("mcap_keep.npy")
tri = np.where(K.split.values == "train")[0]; R = tri[keep[tri]]; C = K.iloc[R].reset_index(drop=True)
assert C.date.max() <= pd.Timestamp("2022-12-31")
names0 = json.load(open("model_features.json")); X0 = np.load("X_train.npy", mmap_mode="r"); assert X0.shape[0] == len(R)
idx = np.array([names0.index(n) for n in names])
for v in "AB": C["x"+v] = C["r"+v] - C.groupby("date")["r"+v].transform("mean")
dcode = pd.factorize(C.date)[0]
def topk(sc, f):
    o = pd.DataFrame(dict(d=dcode, s=sc)); rk = o.groupby("d").s.rank(ascending=False, method="first"); nd = o.groupby("d").s.transform("size")
    return (rk <= np.maximum(1, np.ceil(f*nd))).values
SC = {ex: np.zeros(len(R)) for ex in "AB"}; LF = {ex: np.ones(len(R), bool) for ex in "AB"}
for s in range(0, len(R), 20000):
    B = np.asarray(X0[s:s+20000])[:, idx].astype(np.float32)
    for ex in "AB":
        SC[ex][s:s+20000] = M[ex]["logit"].decision_function(B)
        for n, b in M[ex]["best_leaf"]: LF[ex][s:s+20000] &= (B[:, names.index(n)] > 0) == bool(b)
rng = np.random.default_rng(13); rows = []
for ex in "AB":
    for rule, m in (("TREE_BEST", LF[ex]), ("LOGIT_TOP1", topk(SC[ex], .01)), ("LOGIT_TOP10", topk(SC[ex], .10))):
        x = C[m]; r = x["r"+ex].values; xx = x["x"+ex].values
        dd = x.groupby("date")["x"+ex].agg(["sum", "count"]); sx, dn = dd["sum"].values, dd["count"].values
        bb = rng.integers(0, len(dn), (500, len(dn))); bs = sx[bb].sum(1)/dn[bb].sum(1); se = bs.std()
        rows.append(dict(period="2020-22 (in-sample)", exit={"A":"EXIT_RULE_V1","B":"HOLD_10D"}[ex], rule=rule, n=len(x), n_dates=len(dn),
            win=(r > 0).mean()*100, beat_day=(xx > 0).mean()*100, mean=r.mean()*100, excess=xx.mean()*100,
            ci_lo=np.percentile(bs, 2.5)*100, ci_hi=np.percentile(bs, 97.5)*100, pop_win=(C["r"+ex] > 0).mean()*100))
T = pd.DataFrame(rows); T.to_csv("COMBO_MODEL_V2_INSAMPLE.csv", index=False); print(T.round(3).to_string())
