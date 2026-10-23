# LOOKALIKE_V1 + Addendum A: build match vectors (bars < D only) and 26 outcomes. Price read filter <= 2024-12-31.
import numpy as np, pandas as pd, hashlib, glob, sys
sys.path.insert(0, "/workspace/data/nb_v2"); from nb_year import unpack
from numpy.lib.stride_tricks import sliding_window_view as sw
END = pd.Timestamp("2024-12-31"); FEE = 0.006; W = 25; H = 21; XS = [5, 10, 15, 20, 30]
PQ = "/workspace/pricehist/universe_2020_survivors.parquet"
assert hashlib.sha256(open(PQ, "rb").read()).hexdigest().startswith("fb9bbe69")
assert hashlib.sha256(open("nb/cp_build/cp_tags.csv", "rb").read()).hexdigest() == "54a731b2af3f20f7a3a1c82e3c78da9975d40e6f72528238b9dba649b4ea0d64"
K = pd.read_parquet("/workspace/state_test/combo/keys_labels.parquet")[["ticker", "date", "split"]]
P = pd.read_parquet(PQ, columns=["ticker", "date", "open", "high", "low", "close", "volume"])
P = P[P.date <= END].sort_values(["ticker", "date"]).reset_index(drop=True); assert P.date.max() <= END
def ema(x, n):
    a = 2/(n+1); out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)): out[i] = a*x[i] + (1-a)*out[i-1]
    return out
def rsi(c, n=14):
    d = np.diff(c, prepend=c[0]); up = np.maximum(d, 0); dn = np.maximum(-d, 0); au = np.empty_like(c); ad = np.empty_like(c); au[0]=ad[0]=0
    for i in range(1, len(c)): au[i] = (au[i-1]*(n-1)+up[i])/n; ad[i] = (ad[i-1]*(n-1)+dn[i])/n
    return 100 - 100/(1 + au/np.maximum(ad, 1e-12))
def feats(o, h, l, c, v, j):
    """vectors for target bar indices j using bars j-W..j-1 only (indicator series computed causally on bars < j)."""
    n = len(c); sma = pd.Series(c).rolling(20).mean().values; sd = pd.Series(c).rolling(20).std(ddof=0).values
    pb = (c - (sma-2*sd))/np.maximum(4*sd, 1e-12); R = rsi(c); mh = ema(c,12)-ema(c,26); mh = mh-ema(mh,9)
    vm = pd.Series(v).rolling(20).mean().shift(1).values; rv = np.log((v+1)/(vm+1))
    rng = pd.Series(h-l).rolling(W).mean().values
    hi = pd.Series(h).rolling(W).max().values; lo = pd.Series(l).rolling(W).min().values
    out = []
    for jj in j:
        t = jj-1; s = slice(jj-W, jj); sc = max(rng[t], 1e-9); span = max(hi[t]-lo[t], 1e-9)
        body = (c[s]-o[s]); g = body[body > 0].sum(); r = -body[body < 0].sum()
        tr = (sma[t]-sma[t-5])/sc; dip = (hi[t]-c[t])/span
        ind = lambda k: np.array([R[k], pb[k], mh[k]/sc, (sma[k]-sma[k-5])/sc, (hi[k]-c[k])/max(hi[k]-lo[k],1e-9), rv[k]])
        cur = ind(t)
        out.append(np.r_[body/sc, (c[s]-lo[t])/span, np.log((g+1e-3*sc)/(r+1e-3*sc)), pb[t], tr, dip, R[t], mh[t]/sc, rv[t], cur-ind(t-5), cur-ind(t-10)])
    return np.array(out, np.float32)
def outcomes(o, h, l, c, j):
    out = []
    for jj in j:
        e = o[jj]; cl = c[jj:jj+H]; r = list(cl/e-1-FEE)
        hh = h[jj:jj+H]; oo = o[jj:jj+H]
        for X in XS:
            tgt = e*(1+X/100); hit = np.where(hh >= tgt)[0]
            if len(hit): k = hit[0]; px = oo[k] if (k > 0 and oo[k] >= tgt) else tgt; r.append(px/e-1-FEE)
            else: r.append(cl[-1]/e-1-FEE)
        r.append(float(hh.max()/e-1 >= 0.10)); out.append(r)
    return np.array(out, np.float32)
F = np.full((len(K), 25+25+4+3+12), np.nan, np.float32); Y = np.full((len(K), 27), np.nan, np.float32)
pos = P.groupby("ticker").indices; kg = K.groupby("ticker").indices; done = 0
for tk, ki in kg.items():
    if tk not in pos: continue
    pi = pos[tk]; X = P.iloc[pi]; d = X.date.values; o, h, l, c, v = (X[k].values.astype(float) for k in ["open","high","low","close","volume"])
    j = np.searchsorted(d, K.date.values[ki]); ok = (j < len(d)) & (j >= 60) & (j + H <= len(d))
    ok[ok] &= d[j[ok]] == K.date.values[ki][ok]
    if ok.any():
        F[ki[ok]] = feats(o, h, l, c, v, j[ok]); Y[ki[ok]] = outcomes(o, h, l, c, j[ok])
        if done % 500 == 0:  # lookahead self-test: perturb bars >= D, vector must not change
            jj = j[ok][:1]; o2, h2, l2, c2, v2 = (a.copy() for a in (o, h, l, c, v))
            for a in (o2, h2, l2, c2, v2): a[jj[0]:] *= 1.7
            assert np.allclose(feats(o2, h2, l2, c2, v2, jj), feats(o, h, l, c, v, jj), equal_nan=True), tk
    done += 1
# New Bot tags
T = []
for f in sorted(glob.glob("nb/cp_build/chunks/20*__NBCP__*.parquet")):
    t = pd.read_parquet(f); U = unpack(np.frombuffer(b"".join(t.packed), np.uint8).reshape(len(t), -1), 7)
    T.append(pd.DataFrame(np.where(U == 2, 1, np.where(U == 1, -1, 0)).astype(np.int8), columns=[f"cp{i}" for i in range(7)]).assign(ticker=t.ticker.values, date=pd.to_datetime(t.date.values)))
T = pd.concat(T).drop_duplicates(["ticker", "date"]); M = K[["ticker", "date"]].merge(T, how="left", on=["ticker", "date"])
TG = M[[f"cp{i}" for i in range(7)]].fillna(0).values.astype(np.float32)
print("rows", len(K), "with features", int(np.isfinite(F).all(1).sum()), "tag coverage", float((TG != 0).any(1).mean()))
np.save("F.npy", np.c_[F, TG]); np.save("Y.npy", Y)
