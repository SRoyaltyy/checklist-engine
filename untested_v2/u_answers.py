"""Read stored engine answers for the needed columns on every buyable stock-day (same reader logic as lookalike_features/build.py attach_npz).
Output per column: YES row indices into U + count answered (code>0). Sparse to stay lean."""
import glob, json, os, pickle, numpy as np, pandas as pd, pyarrow.parquet as pq
Uc = "/workspace/checklist_brainstorm/engine/universe/chunks"; T1 = "/workspace/tmp_laf"
U = pd.read_parquet("/workspace/tmp_utv2/U.parquet", columns=["ticker","date"]); U["y"] = U.date.dt.year
L = pd.read_csv("../untested_v1/untested_results_v1.csv"); L = L[L.status.str.startswith("TOO")]
need = set(L.col)
kind_of = {}
for k in ["JG","NB","TR","SHARED"]:
    for i in np.load(f"{T1}/A_{k}.npz", allow_pickle=True)["ids"]: kind_of.setdefault(str(i), k)
need_k = {k: sorted(c for c in need if kind_of.get(c) == k) for k in ["JG","NB","TR","SHARED"]}
print({k: len(v) for k, v in need_k.items()}, "MPV", sum(1 for c in need if c not in kind_of), flush=True)
YES = {c: [] for c in need if c in kind_of}; ANS = {c: 0 for c in YES}
def take(P, ids, cols, rows):
    pos = {i: j for j, i in enumerate(ids)}
    for c in cols:
        j = pos.get(c)
        if j is None: continue
        v = (P[:, j // 4] >> (2 * (j % 4))) & 3
        ANS[c] += int((v > 0).sum()); YES[c].append(rows[v == 2])
for y in range(2020, 2025):
    Uy = U[U.y == y]; ek = pd.Index(Uy.ticker + "|" + Uy.date.dt.strftime("%Y-%m-%d")); rix = Uy.index.values
    for kind in ["JG","NB","TR","SHARED"]:
        cols = need_k[kind]
        if not cols: continue
        if kind == "SHARED":
            z = np.load(f"{Uc}/{y}__SHARED.npz"); ids = [str(i) for i in z["ids"]]; dmap = {str(d)[:10]: i for i, d in enumerate(z["dates"])}
            di = Uy.date.dt.strftime("%Y-%m-%d").map(dmap); ok = di.notna().values
            take(z["packed"][di[ok].astype(int).values], ids, cols, rix[ok]); continue
        if kind == "TR": files = sorted(glob.glob(f"{Uc}/{y}__TR__*.npz"))
        elif kind == "NB": files = sorted(glob.glob(f"{Uc}/{y}__NB__*.parquet"))
        else:
            files = sorted(glob.glob(f"{Uc}/{y}__*.npz"))
            files = [f for f in files if os.path.basename(f).count("__") == 1 and not os.path.basename(f)[6:-4].replace("_part", "").replace("_", "").isupper() and "SHARED" not in f]
        for f in files:
            if kind == "TR":
                z = np.load(f); ids = [str(i) for i in z["keys"]]; key = pd.Index(pd.Series(z["ticker"]).astype(str) + "|" + pd.Series(z["answer_date"]).astype(str).str[:10]); P = z["packed"]
            elif kind == "NB":
                ids = json.load(open(f.replace(".parquet", ".json")))["ids"]; t = pq.read_table(f).to_pandas()
                key = pd.Index(t.ticker.astype(str) + "|" + pd.to_datetime(t.date).dt.strftime("%Y-%m-%d")); P = np.stack(t.packed.map(lambda b: np.frombuffer(b, np.uint8)).values); del t
            else:
                z = np.load(f); ids = [str(i) for i in z["ids"]]; tkz = z["tickers"]; ds = pd.Series(z["dates"]).astype(str).str[:10].values
                key = pd.Index(np.repeat(tkz, len(ds)).astype(str).astype(object) + "|" + np.tile(ds, len(tkz)).astype(object)); P = z["packed"]
            if not any(c in set(ids) for c in cols): continue
            pos = key.get_indexer(ek); ok = pos >= 0
            if ok.any(): take(P[pos[ok]], ids, cols, rix[ok])
            del P
    print(y, "done", flush=True)
out = {c: (np.concatenate(v) if v else np.array([], np.int64)) for c, v in YES.items()}
pickle.dump(dict(yes=out, ans=ANS), open("/workspace/tmp_utv2/answers_engine.pkl", "wb"))
print("cols", len(out), "zero-yes", sum(len(v) == 0 for v in out.values()), "zero-ans", sum(a == 0 for a in ANS.values()))
