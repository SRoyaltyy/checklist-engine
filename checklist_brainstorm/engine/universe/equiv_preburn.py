"""Compare universe-engine 2024 answers vs the 1,200 slow-path preburn cells (all 9,654 ids)."""
import sys, glob, numpy as np, pandas as pd
sys.path.insert(0, '.'); import engine_year as E
C = E.CHUNKS; INV = np.array(["NOT_READY", "NO", "YES"])
sh = np.load(C / "2024__SHARED.npz"); sids = list(sh["ids"]); sdi = {d: i for i, d in enumerate(sh["dates"])}; S = E.unpack(sh["packed"], len(sids))
cells = sorted(glob.glob(str(E.ENG / "out/pilot_matrix/preburn/cells/*.csv")))
want = {Path_t for Path_t in {c.split('/')[-1].split('_')[0] for c in cells}}
dep = {}
for f in glob.glob(str(C / "2024__*.npz")):
    if "SHARED" in f: continue
    z = np.load(f); tk = list(z["tickers"]); nd = len(z["dates"]); ids = list(z["ids"]); ddi = {d: i for i, d in enumerate(z["dates"])}
    for t in want & set(tk):
        i = tk.index(t); dep[t] = (E.unpack(z["packed"][i*nd:(i+1)*nd], len(ids)), ids, ddi)
kinds = {r[0]: r[1] for r in E.dep_rules()}; rows = []
for c in cells:
    a = pd.read_csv(c, dtype=str).fillna(""); t, d = a.ticker[0], a.date[0]
    fast = {}
    s = S[sdi[d]]; fast.update(zip(sids, INV[s]))
    M, ids, ddi = dep[t]; fast.update(zip(ids, INV[M[ddi[d]]]))
    a["fast"] = a.row_id.map(fast); a["kind"] = a.row_id.map(kinds).fillna("shared")
    rows.append(a[a.answer != a.fast][["ticker", "date", "row_id", "kind", "answer", "fast", "reason"]])
    if len(rows) == 1: n_ids = len(a)
bad = pd.concat(rows, ignore_index=True); n = len(cells) * n_ids
print("cells", len(cells), "answers", n, "mismatch", len(bad))
print(pd.crosstab(bad.kind, bad.answer + ">" + bad.fast.astype(str)))
bad.to_parquet("equiv_2024_mismatches.parquet", index=False)
for k, x in bad.groupby("kind"): print(k, x.reason.str[:70].value_counts().head(4).to_dict())
