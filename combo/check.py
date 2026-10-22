# One-shot 2023-24 check of the frozen model. Excess = vs same-day mean of the $100M-filtered population.
import json, numpy as np, pandas as pd, joblib, sys
from scipy.stats import norm
M = joblib.load("COMBO_MODEL_V1_frozen.joblib"); names = M["features"]; fi = {n: j for j, n in enumerate(names)}
K = pd.read_parquet("keys_labels.parquet"); keep = np.load("mcap_keep.npy"); unk = np.load("mcap_unknown.npy")
ci = np.where(K.split.values == "check")[0]; ck = keep[ci]; R = ci[ck]; C = K.iloc[R].reset_index(drop=True)
assert C.date.min() >= pd.Timestamp("2023-01-01") and C.date.max() <= pd.Timestamp("2024-12-31")
for v in "AB": C["x"+v] = C["r"+v] - C.groupby("date")["r"+v].transform("mean")
need = sorted(set(json.load(open("needed_feats.json"))))
pbn = json.load(open("pb_names.json")); nbn = ["NB2:"+i for i in json.load(open("nb_ids.json"))]
hn = ["HALT:"+s for s in ["halt_1d","halt_5d","halt_20d","ludp_5d","news_t123_20d","cnt1","cnt2p"]]
W = {ex: M[ex]["logit"].coef_.ravel() for ex in "AB"}; SC = {ex: np.full(len(R), float(M[ex]["logit"].intercept_[0])) for ex in "AB"}
TN = set(n for ex in "AB" for n, b in M[ex]["best_leaf"]); TC = {}; NZ = {}
def put(n, col):
    col = np.asarray(col, np.float32); NZ[n] = bool(col.any())
    for ex in "AB": SC[ex] += W[ex][fi[n]] * col
    if n in TN: TC[n] = col > 0
PART = {}
def put_part(n, s, c): PART.setdefault(n, []).append(c)
pbB = np.load("pb_bits.npy", mmap_mode="r")
for s in range(0, len(R), 100000):
    U = np.unpackbits(pbB[R[s:s+100000]], axis=1)
    for j, n in enumerate(pbn):
        if n in fi and n in need: put_part(n, s, U[:, j])
for n, L in PART.items(): put(n, np.concatenate(L))
del PART
nbB = np.load("nb2_bits.npy", mmap_mode="r"); haB = np.load("halt_bits.npy", mmap_mode="r")
for lst, B in ((nbn, nbB), (hn, haB)):
    for j, n in enumerate(lst):
        if n in fi and n in need: put(n, B[R, j])
eid = json.load(open("eng_check_ids.json")); EB = np.load("eng_check_yes.npy", mmap_mode="r")
for j, i in enumerate(eid):
    n = "ENG:"+i
    if n in fi and n in need: put(n, EB[ck, j])
miss = [n for n in need if not NZ.get(n, False)]; print("needed", len(need), "all-zero on check", len(miss))
def inleaf(path):
    m = np.ones(len(R), bool)
    for n, b in path: m &= TC[n] == bool(b)
    return m
rng = np.random.default_rng(13); rows = []
for ex in "AB":
    E = M[ex]; sc = SC[ex]
    for rule, m in (("TREE_BEST", inleaf(E["best_leaf"])), ("LOGIT_TOP1", sc >= E["thr1"]), ("LOGIT_TOP10", sc >= E["thr10"])):
        x = C[m]; r = x["r"+ex].values; xx = x["x"+ex].values
        dd = x.groupby("date")["x"+ex].agg(["sum", "count"]); sx, dn = dd["sum"].values, dd["count"].values
        bb = rng.integers(0, len(dn), (500, len(dn))); bs = sx[bb].sum(1)/dn[bb].sum(1); se = bs.std(); z = xx.mean()/se if se > 0 else 0
        rows.append(dict(exit={"A":"EXIT_RULE_V1","B":"HOLD_10D"}[ex], rule=rule, n=len(x), n_dates=len(dn), n_cap_unknown=int(unk[R][m].sum()),
            win=(r > 0).mean()*100, mean=r.mean()*100, median=np.median(r)*100, excess=xx.mean()*100,
            ci_lo=np.percentile(bs, 2.5)*100, ci_hi=np.percentile(bs, 97.5)*100, p=2*norm.sf(abs(z)),
            pop_win=(C["r"+ex] > 0).mean()*100))
T = pd.DataFrame(rows); BASE = 13851; n = BASE + len(T)
allp = np.r_[T.p.values, np.ones(BASE)]; o = np.argsort(allp); a = allp[o]*n/np.arange(1, n+1); a = np.minimum.accumulate(a[::-1])[::-1]; q = np.empty(n); q[o] = np.minimum(a, 1)
T["bh_q"] = q[:len(T)]; T["bh_family"] = n; T["PASS"] = (T.n >= 30) & (T.win > 55) & (T.excess > 0) & (T.bh_q < 0.05)
T.to_csv("COMBO_MODEL_RESULTS_V1.csv", index=False); print(T.round(4).to_string()); print("check rows", len(R), "dropped<100M", int((~ck).sum()), "cap-unknown kept", int(unk[R].sum()))
