"""Read engine answers (JG/NB/TR/SHARED) for population keys of one split. Per-year, per-file ids; join on (ticker,date) by name.
usage: python3 eng.py train  -> eng_train_yes.npy (uint8 0/1, rows=keys of split, cols=eng_ids.json), eng_train_ans.npy (answered counts)
       python3 eng.py check cols.json -> only listed ids"""
import glob, json, os, sys, numpy as np, pandas as pd, pyarrow.parquet as pq
SH = "/workspace/state_test/combo/fx_shared_answers_2020_24.npz"
Uc = "/workspace/checklist_brainstorm/engine/universe/chunks"
split = sys.argv[1]; want = set(json.load(open(sys.argv[2]))) if len(sys.argv) > 2 else None
K = pd.read_parquet("keys_labels.parquet", columns=["ticker","date","split"]); K = K[K.split == split].reset_index(drop=True)
assert K.date.max() <= pd.Timestamp("2024-12-31"); assert not K.duplicated(["ticker","date"]).any()
if split == "train": assert K.date.max() <= pd.Timestamp("2022-12-31")
K["y"] = K.date.dt.year
def files(y, kind):
    if kind == "SHARED": return ["FIX2023_V1"]
    if kind == "TR": return sorted(glob.glob(f"{Uc}/{y}__TR__*.npz"))
    if kind == "NB": return sorted(glob.glob(f"{Uc}/{y}__NB__*.parquet"))
    fs = sorted(glob.glob(f"{Uc}/{y}__*.npz"))
    return [f for f in fs if os.path.basename(f).count("__") == 1 and not os.path.basename(f)[6:-4].replace("_part","").replace("_","").isupper() and "SHARED" not in f]
def load(f, kind):
    if kind == "SHARED":  # James FIX2023_V1 corrected file (main d0cc82a): codes per date x id, per-year order fixed, missing-as-NO -> NR
        z = np.load(SH); ids = [str(i) for i in z["ids"]]; return ids, None, pd.Index([str(d)[:10] for d in z["dates"]]), z["A"]
    if kind == "TR":
        z = np.load(f); ids = [str(i) for i in z["keys"]]
        return ids, pd.Index(pd.Series(z["ticker"]).astype(str) + "|" + pd.Series(z["answer_date"]).astype(str).str[:10]), None, z["packed"]
    if kind == "NB":
        ids = json.load(open(f.replace(".parquet", ".json")))["ids"]; t = pq.read_table(f).to_pandas()
        return ids, pd.Index(t.ticker.astype(str) + "|" + pd.to_datetime(t.date).dt.strftime("%Y-%m-%d")), None, np.stack(t.packed.map(lambda b: np.frombuffer(b, np.uint8)).values)
    z = np.load(f); ids = [str(i) for i in z["ids"]]; tkz = z["tickers"]; ds = pd.Series(z["dates"]).astype(str).str[:10].values
    return ids, pd.Index(np.repeat(tkz, len(ds)).astype(str).astype(object) + "|" + np.tile(ds, len(tkz)).astype(object)), None, z["packed"]
G = {}; gid = []
def g(c):
    k = G.get(c)
    if k is None: k = G[c] = len(gid); gid.append(c)
    return k
# pass 1: global id list (by name)
plan = []
for y in sorted(K.y.unique()):
    for kind in ["JG","NB","TR","SHARED"]:
        for f in files(y, kind):
            plan.append((y, kind, f))
CAP = 14000
Y = np.zeros((len(K), CAP), np.uint8); A = np.zeros(CAP, np.int64)
for y, kind, f in plan:
    Ky = K[K.y == y]; ek = Ky.ticker + "|" + Ky.date.dt.strftime("%Y-%m-%d"); rix = Ky.index.values
    ids, key, dkey, P = load(f, kind)
    assert len(set(ids)) == len(ids), f
    if key is not None:
        assert key.is_unique, f
        pos = key.get_indexer(pd.Index(ek))
    else:
        assert dkey.is_unique, f
        pos = dkey.get_indexer(pd.Index(Ky.date.dt.strftime("%Y-%m-%d")))
    ok = pos >= 0
    if not ok.any(): continue
    sel = [(j, c) for j, c in enumerate(ids) if (want is None or c in want)]
    if not sel: continue
    Pr = P[pos[ok]]; rows = rix[ok]
    for j, c in sel:
        v = Pr[:, j] if kind == "SHARED" else (Pr[:, j // 4] >> (2 * (j % 4))) & 3
        k = g(c); Y[rows, k] |= (v == 2); A[k] += int((v > 0).sum())
    print(y, kind, os.path.basename(f), int(ok.sum()), len(sel), len(gid), flush=True)
Y = Y[:, :len(gid)]; np.save(f"eng_{split}_yes.npy", Y); np.save(f"eng_{split}_ans.npy", A[:len(gid)]); json.dump(gid, open(f"eng_{split}_ids.json", "w"))
print("done", Y.shape, "never-answered", int((A[:len(gid)] == 0).sum()))
