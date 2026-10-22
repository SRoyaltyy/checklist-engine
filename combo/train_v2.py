import json, numpy as np, pandas as pd, joblib, sys, scipy.sparse as sp
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import log_loss, roc_auc_score
K = pd.read_parquet("keys_labels.parquet"); keep = np.load("mcap_keep.npy")
tri = np.where(K.split.values == "train")[0]; tk = keep[tri]; R = tri[tk]; n = len(R)
lab = K.iloc[R].reset_index(drop=True); yr = lab.yr.values
names0 = json.load(open("model_features.json")); X0 = np.load("X_train.npy", mmap_mode="r")
import re; exec(open("eng.py").read().split("\n")[[i for i,l in enumerate(open("eng.py").read().split("\n")) if l.startswith("SH")][0]])
shared = set("ENG:"+str(i) for i in np.load(SH)["ids"])
d = pd.factorize(lab.date)[0]; G = sp.csr_matrix((np.ones(n, np.float32), (d, np.arange(n))))
cnt = np.asarray(G.sum(1)).ravel(); S = np.zeros((G.shape[0], X0.shape[1]), np.float32)
for c in range(0, X0.shape[1], 1000): S[:, c:c+1000] = G @ np.asarray(X0[:, c:c+1000], np.float32)
ok2 = cnt >= 2; zv = ((S[ok2] == 0) | (S[ok2] == cnt[ok2, None])).all(0)
pref = np.array([nm.split(":",1)[-1].startswith(("MAC-","MKT-")) or nm in shared for nm in names0])
keepc = np.where(~(zv | pref))[0]
print("cols", len(names0), "removed prefix/shared", int(pref.sum()), "removed zero within-date var", int((zv & ~pref).sum()), "kept", len(keepc), flush=True)
names = [names0[j] for j in keepc]; p = len(names)
class SubX:
    def __getitem__(self, k):
        if isinstance(k, tuple): r, c = k; return X0[r, keepc[c]]
        return np.asarray(X0[k])[:, keepc]
json.dump(names, open("model_v2_features.json", "w"))
for v in "AB": lab["x"+v] = lab["r"+v] - lab.groupby("date")["r"+v].transform("mean")
X = SubX()
def fit_sgd(idx, y, a, l1):
    m = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=a, l1_ratio=l1, random_state=7)
    rng = np.random.default_rng(7)
    for ep in range(6):
        o = rng.permutation(idx)
        for s in range(0, len(o), 20000):
            bi = np.sort(o[s:s+20000]); m.partial_fit(X[bi].astype(np.float32), y[bi], classes=[0, 1])
    return m
def score(m, idx):
    return np.concatenate([m.decision_function(X[idx[s:s+20000]].astype(np.float32)) for s in range(0, len(idx), 20000)])
def colstats(idx, y):
    n1 = np.zeros(p); y1 = np.zeros(p)
    for s in range(0, len(idx), 20000):
        B = X[idx[s:s+20000]].astype(np.float32); n1 += B.sum(0); y1 += y[idx[s:s+20000]].astype(np.float32) @ B
    return n1, y1
def grow(idx, y, depth, ml, path=()):
    N = len(idx); Y = y[idx].sum()
    node = dict(n=N, win=Y/N, path=path)
    if depth == 0 or N < 2*ml: return node
    n1, y1 = colstats(idx, y); n0 = N-n1; y0 = Y-y1
    with np.errstate(all="ignore"):
        g = lambda nn, yy: nn*(1-(yy/nn)**2-((nn-yy)/nn)**2)
        imp = np.nan_to_num(g(n1, y1)) + np.nan_to_num(g(n0, y0)); imp[(n1 < ml) | (n0 < ml)] = np.inf
    j = int(np.argmin(imp))
    if not np.isfinite(imp[j]) or imp[j] >= g(N, Y) - 1e-9: return node
    col = np.concatenate([X[idx[s:s+50000], j] for s in range(0, N, 50000)]).astype(bool)
    node.update(feat=j, name=names[j], yes=grow(idx[col], y, depth-1, ml, path+((names[j], 1),)), no=grow(idx[~col], y, depth-1, ml, path+((names[j], 0),)))
    return node
def leaves(t, acc=None):
    acc = [] if acc is None else acc
    if "feat" not in t: acc.append(t); return acc
    leaves(t["yes"], acc); leaves(t["no"], acc); return acc
def apply(t, idx, Xs=None):
    out = np.empty(len(idx), object)
    def rec(t, sel):
        if "feat" not in t:
            for i in sel: out[i] = t["path"]
            return
        col = np.asarray(Xs[sel, t["feat"]] if Xs is not None else X[idx[sel], t["feat"]]).astype(bool)
        rec(t["yes"], sel[col]); rec(t["no"], sel[~col])
    rec(t, np.arange(len(idx))); return out
def tree_prob(t, idx):
    lw = {l["path"]: l["win"] for l in leaves(t)}; return np.array([lw[q] for q in apply(t, idx)])
out = dict(features=names, n_train=n, version='V2')
for ex in ["A", "B"]:
    y = (lab["x"+ex].values > 0).astype(np.int8); f = np.where(yr <= 2021)[0]; v = np.where(yr == 2022)[0]
    best = None
    for a in [1e-5, 1e-4, 1e-3]:
        for l1 in [0.15, 0.5, 0.9]:
            m = fit_sgd(f, y, a, l1); pr = 1/(1+np.exp(-score(m, v)))
            ll = log_loss(y[v], np.clip(pr, 1e-6, 1-1e-6)); print(ex, "logit", a, l1, round(ll, 5), flush=True)
            if best is None or ll < best[0]: best = (ll, a, l1)
    bt = None
    for d in [3, 4]:
        for ml in [300, 1000, 3000]:
            t = grow(f, y, d, ml); auc = roc_auc_score(y[v], tree_prob(t, v)); print(ex, "tree", d, ml, round(auc, 5), flush=True)
            if bt is None or auc > bt[0]: bt = (auc, d, ml)
    al = np.arange(n); lg = fit_sgd(al, y, best[1], best[2]); tr = grow(al, y, bt[1], bt[2])
    sc = score(lg, al); L = leaves(tr); bl = max(L, key=lambda l: l["win"])
    out[ex] = dict(logit=lg, tree=tr, cv_logit=best, cv_tree=bt, best_leaf=bl["path"], best_leaf_trainwin=float(bl["win"]), best_leaf_n=int(bl["n"]))
    print(ex, best, bt, bl["win"], bl["n"], bl["path"], flush=True)
joblib.dump(out, "COMBO_MODEL_V2_frozen.joblib"); print("saved", flush=True)
