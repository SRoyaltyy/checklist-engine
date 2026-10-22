# Memory-lean version of train.py (box OOM on sparse build). Same features, filters, grids, CV; dense uint8 memmap,
# SGD elastic-net via partial_fit (6 epochs, row batches), exact greedy gini tree on binary features (same as sklearn CART on 0/1 inputs).
import json, numpy as np, pandas as pd, joblib, hashlib, sys
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import log_loss, roc_auc_score
K = pd.read_parquet("keys_labels.parquet"); keep = np.load("mcap_keep.npy")
tri = np.where(K.split.values == "train")[0]; tk = keep[tri]; R = tri[tk]; n = len(R)
lab = K.iloc[R].reset_index(drop=True); yr = lab.yr.values
bug = set(pd.read_csv("u2_untested_results_v2.csv").query("status.str.startswith('BUG')", engine="python").col.astype(str))
man = set(pd.read_csv("fx_missing_as_no_rows.csv").col.astype(str)); blocked = {"DIL-NB-051"}
eid = json.load(open("eng_train_ids.json")); eans = np.load("eng_train_ans.npy"); nbans = np.load("nb2_train_ans.npy")
srcs = []  # (name, loader(cols)->uint8 n x c, ids, ans)
pbB = np.load("pb_bits.npy", mmap_mode="r")
srcs.append(("pb", lambda a, b: np.unpackbits(pbB[R], axis=1)[:, a:b], json.load(open("pb_names.json")), None))
nbB = np.load("nb2_bits.npy", mmap_mode="r"); srcs.append(("nb", lambda a, b: nbB[R, a:b], ["NB2:"+i for i in json.load(open("nb_ids.json"))], nbans))
haB = np.load("halt_bits.npy", mmap_mode="r"); srcs.append(("halt", lambda a, b: haB[R, a:b], ["HALT:"+s for s in ["halt_1d","halt_5d","halt_20d","ludp_5d","news_t123_20d","cnt1","cnt2p"]], None))
EB = np.load("eng_train_yes.npy", mmap_mode="r"); srcs.append(("eng", lambda a, b: np.asarray(EB[:, a:b])[tk], ["ENG:"+i for i in eid], eans))
# pass 1: choose columns
blocks = []; names = []; seen = set()
for nm, ld, ids, ans in srcs:
    step = 5716 if nm == "pb" else 1500
    for a in range(0, len(ids), step):
        M = ld(a, a+step) if nm != "pb" else ld(0, 5716); b = a + M.shape[1]
        s = M.sum(0, dtype=np.int64); ok = (s > 0) & (s < 0.99*n)
        for j in range(M.shape[1]):
            if not ok[j]: continue
            bid = ids[a+j].split(":", 1)[-1]
            if bid in bug or bid in man or bid in blocked or (ans is not None and ans[a+j] == 0): ok[j] = False; continue
            h = hashlib.md5(np.packbits(M[:, j]).tobytes()).digest()
            if h in seen: ok[j] = False; continue
            seen.add(h)
        blocks.append((nm, a, b, np.where(ok)[0])); names += [ids[a+j] for j in np.where(ok)[0]]; print(nm, a, int(ok.sum()), flush=True)
        if nm == "pb": break
p = len(names); X = np.lib.format.open_memmap("X_train.npy", "w+", np.uint8, (n, p)); c = 0
for nm, a, b, ok in blocks:
    M = srcs[[s[0] for s in srcs].index(nm)][1](a, b); X[:, c:c+len(ok)] = M[:, ok]; c += len(ok); del M
X.flush(); print("X", X.shape, flush=True); json.dump(names, open("model_features.json", "w"))
X = np.load("X_train.npy", mmap_mode="r")
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
out = dict(features=names, n_train=n)
for ex in ["A", "B"]:
    y = (lab["r"+ex].values > 0).astype(np.int8); f = np.where(yr <= 2021)[0]; v = np.where(yr == 2022)[0]
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
    out[ex] = dict(logit=lg, tree=tr, cv_logit=best, cv_tree=bt, thr1=float(np.quantile(sc, .99)), thr10=float(np.quantile(sc, .90)), best_leaf=bl["path"], best_leaf_trainwin=float(bl["win"]), best_leaf_n=int(bl["n"]))
    print(ex, best, bt, bl["win"], bl["n"], bl["path"], flush=True)
joblib.dump(out, "COMBO_MODEL_V1_frozen.joblib"); print("saved", flush=True)
