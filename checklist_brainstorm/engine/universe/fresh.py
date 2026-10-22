#!/usr/bin/env python3
"""FRESH quiet_warning features per sector. Sources: per-question 2-bit STK chunks ({y}__<sector>.npz, ids by row_id) and
TR chunks ({y}__TR__<sector>.npz, keys row|N), joined to locked tags (grok_tags sha checked) on (row_id,N); meaning==quiet_warning only.
Per ticker x date, per source|lens group:
  qw_fresh  = # qw question ids YES today and NO on that stock's previous session (previous row of same ticker in the date-sorted chunk)
  qw_yes, qw_ready, qw_frac = yes/ready
  qw_jump_z = (frac_t - mean(frac over prior 20 sessions)) / std(prior 20), prior sessions only, NaN if <10 prior sessions with a frac (or std==0)
Output chunks/{y}__FRESH__<base_sector>.parquet (JG parts merged; outer join with TR on ticker,date)."""
import sys, glob, re, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '.'); from engine_year import unpack, CHUNKS
y = int(sys.argv[1]); TD = CHUNKS.parent.parent / "out/tags"
assert hashlib.sha256(open(TD/"grok_tags.csv","rb").read()).hexdigest() == "505f452c65cdabda1576f978ad9a76be5acc546b4b41d0268caeb05d14f58ad7"
SRC = {"james_tags.csv": "james", "theme-radar_tags.csv": "theme-radar", "new-bot_tags.csv": "new-bot", "grok_tags.csv": "grok"}
excl = set(pd.read_csv(TD/"new-bot_excluded_inference.csv", dtype=str).row_id)
T = []
for f, s in SRC.items():
    t = pd.read_csv(TD/f, dtype=str); t["source"] = s
    t["key"] = t.row_id + ("|" + t.N.fillna("0") if "N" in t else ""); T.append(t[["row_id","key","source","meaning","lens"]])
T = pd.concat(T); T = T[~T.row_id.isin(excl)]; T["lens"] = T.lens.fillna("none")
bykey = T.drop_duplicates("key").set_index("key"); byrow = T.drop_duplicates("row_id").set_index("row_id")
def qwgroups(ids):
    g = {}
    for j, q in enumerate(ids):
        r = bykey.loc[q] if q in bykey.index else (byrow.loc[q.split("|")[0]] if q.split("|")[0] in byrow.index else None)
        if r is not None and r.meaning == "quiet_warning": g.setdefault(f"{r.source}|{r.lens}", []).append(j)
    return g
def feats(tk, dt, C, G):
    """C: rows x qw-cols codes (uint8) sorted by ticker,date."""
    o = np.argsort(np.char.add(tk.astype(str), dt.astype(str)), kind="stable"); tk, dt, C = tk[o], dt[o], C[o]
    first = np.r_[True, tk[1:] != tk[:-1]]
    prev = np.vstack([np.zeros((1, C.shape[1]), np.uint8), C[:-1]]); prev[first] = 0
    d = {"ticker": tk, "date": dt}
    for g, cols in G.items():
        c = C[:, cols]; p = prev[:, cols]
        yes = (c == 2).sum(1); rdy = (c > 0).sum(1); fr = np.where(rdy > 0, yes / np.maximum(rdy, 1), np.nan)
        s = pd.Series(fr); grp = pd.Series(tk)
        sh = s.groupby(grp).shift(1)
        m = sh.groupby(grp).transform(lambda x: x.rolling(20, min_periods=10).mean()); sd = sh.groupby(grp).transform(lambda x: x.rolling(20, min_periods=10).std())
        z = ((s - m) / sd.where(sd > 0)).values
        d[f"{g}|qw_fresh"] = ((c == 2) & (p == 1)).sum(1).astype(np.int16)
        d[f"{g}|qw_yes"] = yes.astype(np.int16); d[f"{g}|qw_ready"] = rdy.astype(np.int16)
        d[f"{g}|qw_frac"] = fr.astype(np.float32); d[f"{g}|qw_jump_z"] = z.astype(np.float32)
    return pd.DataFrame(d)
def load(files, idkey, tkkey, dkey, keep=None):
    out = []
    for f in files:
        z = np.load(f); ids = list(z[idkey]); G = qwgroups(ids); cols = sorted({j for v in G.values() for j in v})
        if not cols: continue
        P = z["packed"]; parts = []
        if tkkey == "tickers": tk = np.repeat(z["tickers"], len(z["dates"])); dt = np.tile(z["dates"], len(z["tickers"]))
        else: tk = z[tkkey]; dt = z[dkey]
        m = np.ones(len(tk), bool) if keep is None else np.isin(tk, list(keep))
        for i in range(0, len(P), 25000):
            mi = m[i:i+25000]
            if mi.any(): parts.append(unpack(P[i:i+25000][mi], len(ids))[:, cols].astype(np.uint8))
        if not parts: continue
        C = np.vstack(parts); tk = tk[m]; dt = dt[m]; remap = {j: k for k, j in enumerate(cols)}; G2 = {g: [remap[j] for j in v] for g, v in G.items()}
        out.append(feats(tk, dt, C, G2)); del C, parts
    return pd.concat(out) if out else None
secs = sorted({re.sub(r"_part\d+$", "", f.split("__")[-1][:-4]) for f in glob.glob(str(CHUNKS/f"{y}__*.npz")) if "SHARED" not in f and "__TR__" not in f and "SECADD" not in f})
for sec in secs:
    jf = [f for f in sorted(glob.glob(str(CHUNKS/f"{y}__{sec}*.npz"))) if re.fullmatch(rf"{y}__{sec}(_part\d+)?\.npz", f.split("/")[-1])]
    tf = [f for f in sorted(glob.glob(str(CHUNKS/f"{y}__TR__{sec}*.npz"))) if re.fullmatch(rf"{y}__TR__{sec}(_part\d+)?\.npz", f.split("/")[-1])]
    for f in jf:
        part = f.split("__")[-1][:-4]; out = CHUNKS/f"{y}__FRESH__{part}.parquet"
        if out.exists(): print("skip", out.name); continue
        keep = set(np.load(f)["tickers"]) if len(jf) > 1 else None
        A = load([f], "ids", "tickers", None); B = load(tf, "keys", "ticker", "answer_date", keep)
        D = A if B is None else (B if A is None else A.merge(B, on=["ticker","date"], how="outer"))
        D = D.sort_values(["ticker","date"]); D.to_parquet(out, index=False)
        print(f"fresh {y} {part} rows={len(D)} cols={D.shape[1]}", flush=True); del A, B, D
print(f"FRESHREADY {y}")
