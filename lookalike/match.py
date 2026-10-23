# Exact twin search (faiss flat L2). Library = 2020-22 train rows, eligible if dated <= month_start(D) - 35 days.
import numpy as np, pandas as pd, faiss
faiss.omp_set_num_threads(8)
KS = [10, 25, 50, 100, 200, 400]; KM = 400
K = pd.read_parquet("/workspace/state_test/combo/keys_labels.parquet")[["ticker", "date", "split"]]
keep = np.load("/workspace/state_test/combo/mcap_keep.npy"); F = np.load("F.npy"); Y = np.load("Y.npy")
good = keep & np.isfinite(F).all(1) & np.isfinite(Y).all(1)
R = Y[:, :26].copy(); X = np.full_like(R, np.nan)
for sp in ["train", "check"]:
    m = good & (K.split.values == sp); df = pd.DataFrame(R[m]); X[m] = (df - df.groupby(K.date.values[m]).transform("mean")).values
np.save("X.npy", X)
blocks = [25, 25, 1, 1, 1, 1, 1, 1, 1, 12, 7]; w = np.concatenate([np.full(b, 1/np.sqrt(b)) for b in blocks]).astype(np.float32)
lib = np.where(good & (K.split.values == "train"))[0]
mu = F[lib].mean(0); sd = F[lib].std(0) + 1e-6; Z = ((F - mu)/sd*w).astype(np.float32); Z[~good] = 0
rng = np.random.default_rng(5); a, b = rng.choice(lib, 20000), rng.choice(lib, 20000)
RAND = float(np.median(np.sqrt(((Z[a]-Z[b])**2).sum(1)))); print("median random-pair distance", RAND)
Hl = Y[lib, 26]; ld = K.date.values[lib]; Wl = (R[lib] > 0).astype(np.float32); Xl = X[lib]
tgt = np.where(good)[0]; ms = K.date.values[tgt].astype("datetime64[M]")
OUT_W = np.full((len(K), 6, 26), np.nan, np.float32); OUT_X = OUT_W.copy(); DK = np.full((len(K), 6), np.nan, np.float32); DM = DK.copy()
I100 = np.full((len(K), 100), -1, np.int32); HIT = np.full((len(K), 6), np.nan, np.float32)
for mo in np.unique(ms):
    cut = (pd.Timestamp(mo) - pd.Timedelta(days=35)).to_datetime64(); el = np.where(ld <= cut)[0]
    if len(el) < 2000: continue
    idx = faiss.IndexFlatL2(Z.shape[1]); idx.add(Z[lib[el]]); T = tgt[ms == mo]
    for s in range(0, len(T), 4000):
        t = T[s:s+4000]; D, I = idx.search(Z[t], KM); D = np.sqrt(np.maximum(D, 0)); G = el[I]   # G = positions in lib
        assert (ld[G] <= cut).all()
        I100[t] = lib[G[:, :100]]
        cw = np.cumsum(Wl[G], 1); cx = np.cumsum(Xl[G], 1); cd = np.cumsum(D, 1); ch = np.cumsum(Hl[G], 1)
        for q, k in enumerate(KS):
            OUT_W[t, q] = cw[:, k-1]/k; OUT_X[t, q] = cx[:, k-1]/k; DK[t, q] = D[:, k-1]; DM[t, q] = cd[:, k-1]/k; HIT[t, q] = ch[:, k-1]/k
    print(mo, len(el), len(T), flush=True)
np.savez("twins.npz", W=OUT_W, X=OUT_X, DK=DK, DM=DM, HIT=HIT, RAND=RAND); np.save("I100.npy", I100)
