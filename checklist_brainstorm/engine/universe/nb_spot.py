#!/usr/bin/env python3
"""Hand-recompute 20 random (ticker, date, row) cells of {y}__NB__*.parquet with plain loops (independent of vectorised code)."""
import sys, json, glob, random, math
import numpy as np, pandas as pd
sys.path.insert(0, "."); import nb_year as N
year = int(sys.argv[1]); random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
rows, THR = N.load_rows(); rs = rows.set_index("id")
spy = N.sessions_all(); sess = list(spy.index); cal = N.cal_events(spy.index.values)
med = pd.read_parquet(N.CACHE / "indmed.parquet").set_index(["industry", "date"])
ind = pd.read_csv(N.SECT, usecols=["Ticker", "Industry"]).set_index("Ticker").Industry
OK_L = {"T1-THR", "T1-EXT", "T1-CHG", "T3-CRS", "T3-STK", "P5-POSQ", "P5-POSD", "W0-EVT", "T20-CNT", "T20-RXM", "T1-DIV"}
OK_I = ["NB-015", "NB-025", "NB-026", "NB-029", "NB-035", "NB-036", "NB-057", "NB-075", "NB-076", "NB-071", "NB-072", "NB-073"]
files = sorted(glob.glob(f"chunks/{year}__NB__*.parquet"))
def X_at(b, i, k):
    """X for indicator k at bar index i of ticker bars b (plain python)."""
    c = b.close.values.astype("float64"); h = b.high.values.astype("float64"); l = b.low.values.astype("float64"); o = b.open.values.astype("float64"); d = b.date.values
    def atr(j):
        if j < 14: return float("nan")
        return sum(max(h[t]-l[t], abs(h[t]-c[t-1]), abs(l[t]-c[t-1])) for t in range(j-13, j+1)) / 14
    def r(j): return c[j]/c[j-1]-1 if j >= 1 else float("nan")
    if k == "NB-015": return (c[i]-math.ceil(c[i]))/atr(i)
    if k == "NB-029":
        if i < 250: return float("nan")
        return float(sum(abs(r(t)) >= 0.2 for t in range(i-249, i+1)))
    if k == "NB-035":
        n = 0; t = i
        while t >= 1 and o[t] > h[t-1]: n += 1; t -= 1
        return float(n) if i >= 1 else float("nan")
    if k == "NB-026":
        try: return r(i) - float(np.float32(med.loc[(ind[b.ticker.iloc[0]], pd.Timestamp(d[i]))].r1))
        except KeyError: return float("nan")
    if k == "NB-025":
        sr = (spy / spy.shift(1) - 1)
        def beta(n):
            if i - n + 1 < 1: return float("nan")
            a = np.array([r(t) for t in range(i-n+1, i+1)]); s = sr.reindex(d[i-n+1:i+1]).values
            return np.mean(a*s)-a.mean()*s.mean() if False else (np.mean(a*s)-a.mean()*s.mean())/(np.mean(s*s)-s.mean()**2)
        return beta(20)/beta(250)
def ev_at(b, i, k):
    c = b.close.values.astype("float64"); h = b.high.values.astype("float64"); l = b.low.values.astype("float64")
    if k in N.CAL_EV: return bool(cal[k].get(pd.Timestamp(b.date.values[i]), False))
    if i < 2: return None
    r1 = c[i]/c[i-1]-1
    if k == "NB-057": return l[i] <= 0.9*c[i-1]
    if k == "NB-075": return r1 >= 0.2
    if k == "NB-076": s = spy.get(pd.Timestamp(b.date.values[i])) / spy.shift(1).get(pd.Timestamp(b.date.values[i])) - 1; return r1 > 0 and s <= -0.01
    if k == "NB-036":
        j = i-1
        if j < 15: return None
        a = sum(max(h[t]-l[t], abs(h[t]-c[t-1]), abs(l[t]-c[t-1])) for t in range(j-13, j+1))/14/c[j]
        return h[i] < h[j] and l[i] > l[j] and abs(c[j]/c[j-1]-1) >= 2*a
def hand(tk, D, rid):
    r = rs.loc[rid]; L = r.lens; k = r.ind; but = r.but
    b = pd.read_parquet(N.PX, columns=["ticker", "date", "open", "high", "low", "close"], filters=[("ticker", "=", tk), ("date", "<", pd.Timestamp(D))])
    b = b.sort_values("date").reset_index(drop=True); b["date"] = b.date.astype("datetime64[ns]")
    if len(b) == 0 or (pd.Timestamp(D) - b.date.iloc[-1]).days > 7: return 0
    i = len(b) - 1
    if L == "W0-EVT":
        e = bool(cal[k].get(pd.Timestamp(D), False)) if k in N.CAL_EV else ev_at(b, i, k)
        if e is None: return 0
        return 1 if but else (2 if e else 1)
    if L == "T20-CNT":
        if i - 19 < 0: return 0
        es = [ev_at(b, t, k) for t in range(i-19, i+1)]
        if any(e is None for e in es): return 0
        n = sum(es); return 2 if ((n == 0) if but else (n >= 2)) else 1
    if L == "T20-RXM":
        if i - 19 < 0: return 0
        es = [ev_at(b, t, k) for t in range(i-19, i+1)]
        if any(e is None for e in es): return 0
        vals = []
        for t in range(i-19, i-2):
            if es[t-(i-19)]:
                dt = pd.Timestamp(b.date.values[t]); j = sess.index(dt)
                vals.append(b.close.values[t+3]/b.close.values[t]-1 - (spy.iloc[j+3]/spy.iloc[j]-1))
        if not vals: return 1
        m = np.mean(vals); return 2 if ((m <= -0.03) if but else (m >= 0.03)) else 1
    x = X_at(b, i, k)
    if L == "T1-THR":
        if not np.isfinite(x): return 0
        op, v = THR[rid]; return 2 if ((x >= v) if op == ">=" else (x <= v)) else 1
    if L in ("P5-POSQ", "P5-POSD"):
        xs = [X_at(b, t, k) for t in range(i-4, i+1)]
        if not all(np.isfinite(xs)): return 0
        mn, mx = min(xs), max(xs); q = 0.75 if L == "P5-POSQ" else 0.9
        if mx <= mn: return 1
        return 2 if ((x <= mn+(1-q)*(mx-mn)) if but else (x >= mn+q*(mx-mn))) else 1
    if L == "T3-CRS":
        xs = [X_at(b, t, k) for t in range(i-3, i+1)]
        if not all(np.isfinite(xs)): return 0
        s0 = np.mean(xs[1:4]); s1 = np.mean(xs[0:3])
        if but: return 2 if (xs[3] < s0 and not xs[2] < s1) else 1
        return 2 if (xs[3] > s0 and not xs[2] > s1) else 1
    if L == "T3-STK":
        xs = [X_at(b, t, k) for t in range(i-21, i+1)]
        if not all(np.isfinite(xs)): return 0
        ok = all(((xs[t] < np.mean(xs[t-19:t+1])) if but else (xs[t] > np.mean(xs[t-19:t+1]))) for t in (19, 20, 21))
        return 2 if ok else 1
    if L in ("T1-EXT", "T1-CHG", "T1-DIV"):
        xs = np.array([X_at(b, t, k) for t in range(i-250, i+1)]) if i >= 250 else None
        if xs is None or not np.all(np.isfinite(xs[1:])): return 0
        if L == "T1-EXT":
            q = np.quantile(xs[1:], 0.05 if but else 0.95); return 2 if ((x <= q) if but else (x >= q)) else 1
        if L == "T1-DIV":
            w = xs[1:]; pr = (np.sum(w < x) + (np.sum(w == x) + 1) / 2) / len(w); r1 = b.close.values[i]/b.close.values[i-1]-1
            return 2 if (((pr <= 0.2) and r1 >= 0) if but else ((pr >= 0.8) and r1 <= 0)) else 1
        if not np.isfinite(xs[0]): return 0
        dx = np.diff(xs); sd = np.std(dx, ddof=1); return 2 if ((dx[-1] <= -sd) if but else (dx[-1] >= sd)) else 1
cands = rows[rows.ind.isin(OK_I) & rows.lens.isin(OK_L)].id.tolist()
res = []; tries = 0
while len(res) < 20 and tries < 400:
    tries += 1; fn = random.choice(files); meta = json.load(open(fn.replace(".parquet", ".json"))); ids = meta["ids"]
    df = pd.read_parquet(fn); i = random.randrange(len(df)); rid = random.choice(cands)
    code = int(N.unpack(np.frombuffer(df.packed.iloc[i], np.uint8)[None], len(ids))[0, ids.index(rid)])
    if code == 0 and random.random() < 0.8: continue     # bias toward ready cells
    hcode = hand(df.ticker.iloc[i], df.date.iloc[i], rid)
    res.append((df.ticker.iloc[i], df.date.iloc[i], rid, code, hcode, code == hcode)); print(res[-1], flush=True)
print("MATCH", sum(r[-1] for r in res), "/", len(res))
pd.DataFrame(res, columns=["ticker", "date", "row", "engine", "hand", "match"]).to_csv(f"chunks/{year}__NB_spotcheck.csv", index=False)
