# Twin trade tests (312) + winners-vs-losers (A3) + BH over family 14,075 + all tests.
import numpy as np, pandas as pd, json
from scipy.stats import norm
KS = [10, 25, 50, 100, 200, 400]; EX = [f"HOLD_{h}" for h in range(1, 22)] + [f"TP_{x}" for x in [5, 10, 15, 20, 30]]
K = pd.read_parquet("/workspace/state_test/combo/keys_labels.parquet")[["ticker", "date", "split"]]
Y = np.load("Y.npy"); R = Y[:, :26]; X = np.load("X.npy"); Tw = np.load("twins.npz")
dates = K.date.values; has = np.isfinite(Tw["W"][:, 0, 0])
def boot_p(x, d, rng):
    g = pd.DataFrame(dict(x=x, d=d)).groupby("d").x.agg(["sum", "count"]); s, n = g["sum"].values, g["count"].values
    b = rng.integers(0, len(n), (500, len(n))); bs = s[b].sum(1)/n[b].sum(1); se = bs.std()
    return (2*norm.sf(abs(x.mean()/se)) if se > 0 else 1.0), len(n)
rng = np.random.default_rng(13); rows = []; PICK = {}
for per, sp in [("discover_2020_22", "train"), ("check_2023_24", "check")]:
    base = np.where(has & (K.split.values == sp))[0]
    for q, k in enumerate(KS):
        for e, en in enumerate(EX):
            w = Tw["W"][base, q, e]; tx = Tw["X"][base, q, e]; el = base[(w > 0.55) & (tx > 0)]
            o = pd.DataFrame(dict(i=el, d=dates[el], s=Tw["X"][el, q, e])).sort_values("s", ascending=False).groupby("d").head(5)
            p_i = o.i.values; r = R[p_i, e]; x = X[p_i, e]
            if len(p_i) < 2: rows.append(dict(period=per, K=k, exit=en, n=len(p_i), p=1.0)); continue
            p, nd = boot_p(x, dates[p_i], rng)
            rows.append(dict(period=per, K=k, exit=en, n=len(p_i), n_dates=nd, win=(r > 0).mean()*100, pop_win=(R[base, e] > 0).mean()*100,
                             mean=r.mean()*100, excess=x.mean()*100, beat_day=(x > 0).mean()*100, p=p,
                             twin_hit10=np.nanmean(Tw["HIT"][p_i, q]), pick_hit10=Y[p_i, 26].mean(), pop_hit10=Y[base, 26].mean()))
            if k == 100 and en == "HOLD_10": PICK[sp] = p_i
T = pd.DataFrame(rows)
# ---- A3 winners vs losers (K=100, HOLD_10) ----
pbn = json.load(open("/workspace/state_test/combo/pb_names.json")); nbn = json.load(open("/workspace/state_test/combo/nb_ids.json"))
pbB = np.load("/workspace/state_test/combo/pb_bits.npy", mmap_mode="r"); nbB = np.load("/workspace/state_test/combo/nb2_bits.npy", mmap_mode="r"); haB = np.load("/workspace/state_test/combo/halt_bits.npy", mmap_mode="r")
names = ["PB:"+n for n in pbn] + ["NB2:"+n for n in nbn] + ["HALT:"+str(i) for i in range(7)] + ["MASTER:downtrend_2m_earlier", "MASTER:setup_up_price_flat"]
P = pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet", columns=["ticker", "date", "close"]); P = P[P.date <= "2024-12-31"]
F = np.load("F.npy")
def master(rows_):
    sub = K.iloc[rows_][["ticker", "date"]].reset_index()
    out = np.zeros((len(rows_), 2), np.float32); g = P.groupby("ticker")
    for tk, s in sub.groupby("ticker"):
        X_ = g.get_group(tk); d = X_.date.values; c = X_.close.values; j = np.searchsorted(d, s.date.values)
        ok = j >= 43; jj = np.where(ok, j, 43)
        dt = (c[jj-43] > c[jj-22]).astype(np.float32); flat = np.abs(c[jj-1]/c[jj-11]-1) < 0.02
        out[s.index.values - 0, 0] = np.where(ok, dt, np.nan) if False else np.where(ok, dt, 0.5)
    return out
def items(rws):
    U = np.unpackbits(pbB[rws], axis=1)[:, :len(pbn)].astype(np.float32)
    m = np.zeros((len(rws), 2), np.float32)
    return np.c_[U, nbB[rws].astype(np.float32), haB[rws].astype(np.float32), m]
# master items from F/prices: setup rising while flat = %B 10-bar change >= 0.2 and |10-bar move of path| small (from prices)
pos = {}
import faiss
keep = np.load("/workspace/state_test/combo/mcap_keep.npy"); good = keep & np.isfinite(F).all(1) & np.isfinite(Y).all(1)
blocks = [25, 25, 1, 1, 1, 1, 1, 1, 1, 12, 7]; wv = np.concatenate([np.full(b, 1/np.sqrt(b)) for b in blocks]).astype(np.float32)
lib = np.where(good & (K.split.values == "train"))[0]; mu0 = F[lib].mean(0); sd0 = F[lib].std(0) + 1e-6
Zl = ((F[lib] - mu0)/sd0*wv).astype(np.float32); ldt = dates[lib]
def nn100(pk):
    out = np.zeros((len(pk), 100), np.int64); ms = dates[pk].astype("datetime64[M]")
    for mo in np.unique(ms):
        cut = (pd.Timestamp(mo) - pd.Timedelta(days=35)).to_datetime64(); el = np.where(ldt <= cut)[0]; t = np.where(ms == mo)[0]
        ix = faiss.IndexFlatL2(Zl.shape[1]); ix.add(Zl[el]); _, I = ix.search(((F[pk[t]] - mu0)/sd0*wv).astype(np.float32), 100); out[t] = lib[el[I]]
    return out
def wl(sp):
    pk = PICK[sp]; G = nn100(pk); uniq = np.unique(G); rowpos = {v: i for i, v in enumerate(uniq)}
    IT = np.zeros((len(uniq), len(names)), np.float32)
    for s in range(0, len(uniq), 20000): IT[s:s+20000] = items(uniq[s:s+20000])
    # master: downtrend 2m earlier and setup-up-while-flat via price lookups
    sub = K.iloc[uniq][["ticker", "date"]]; g = dict(tuple(P.groupby("ticker")))
    for pos_i, (tk, dt) in enumerate(zip(sub.ticker.values, sub.date.values)):
        X_ = g[tk]; d = X_.date.values; c = X_.close.values; j = np.searchsorted(d, dt)
        IT[pos_i, -2] = float(c[j-43] > c[j-22]) if j >= 43 else np.nan
        IT[pos_i, -1] = float(F[uniq[pos_i], 25+25+4+3+6+1] >= 0.2 and abs(c[j-1]/c[j-11]-1) < 0.02) if j >= 11 else np.nan
    Gi = np.vectorize(rowpos.get)(G); win = R[G, 9] > 0; D = np.full((len(pk), len(names)), np.nan, np.float32)
    for a in range(len(pk)):
        if win[a].sum() < 5 or (~win[a]).sum() < 5: continue
        V = IT[Gi[a]]; D[a] = np.nanmean(V[win[a]], 0) - np.nanmean(V[~win[a]], 0)
    mu = np.nanmean(D, 0); se = np.nanstd(D, 0)/np.sqrt(np.isfinite(D).sum(0)); z = np.where(se > 0, mu/se, 0)
    return mu, 2*norm.sf(abs(z))
mu_d, p_d = wl("train"); mu_c, p_c = wl("check")
tested = np.isfinite(mu_d) & (np.nan_to_num(mu_d) != 0)
BASE = 14075; fam = BASE + len(T) + int(tested.sum())
allp = np.r_[T.p.fillna(1).values, np.where(tested, np.nan_to_num(p_d, nan=1), np.nan)[tested], np.ones(BASE)]
n = len(allp); o = np.argsort(allp); a = allp[o]*n/np.arange(1, n+1); a = np.minimum.accumulate(a[::-1])[::-1]; qv = np.empty(n); qv[o] = np.minimum(a, 1)
T["bh_q"] = qv[:len(T)]; T["bh_family"] = fam
T["ok"] = (T.n >= 30) & (T.win > 55) & (T.excess > 0) & (T.bh_q < 0.05)
both = T.pivot_table(index=["K", "exit"], columns="period", values="ok", aggfunc="first")
T = T.merge(both.all(axis=1).rename("PASS_BOTH").reset_index(), on=["K", "exit"])
T.to_csv("LOOKALIKE_RESULTS_V1.csv", index=False)
qi = qv[len(T):len(T)+int(tested.sum())]; ni = np.array(names)[tested]
WL = pd.DataFrame(dict(item=ni, diff_discover=mu_d[tested]*100, p_discover=p_d[tested], bh_q=qi, diff_check=mu_c[tested]*100, p_check=p_c[tested]))
WL["CONFIRMED"] = (WL.bh_q < 0.05) & (np.sign(WL.diff_check) == np.sign(WL.diff_discover)) & (WL.p_check < 0.05)
WL.sort_values("p_discover").to_csv("LOOKALIKE_WINLOSE_V1.csv", index=False)
print("family", fam, "items", int(tested.sum())); print("PASS settings", int(T.PASS_BOTH.sum()//2)); print("WL q<.05", int((WL.bh_q < .05).sum()), "confirmed", int(WL.CONFIRMED.sum()))
print(WL.sort_values("p_discover").head(15).round(4).to_string())
