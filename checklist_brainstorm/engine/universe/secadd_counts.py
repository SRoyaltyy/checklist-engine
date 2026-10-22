"""Counts for the sector add-on. Unpacks packed codes in row batches to limit peak RAM."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '.'); import engine_year as E
y = int(sys.argv[1]); t = pd.read_csv(E.ENG / "out/tags/james_tags.csv", dtype=str).set_index("row_id"); t["meaning"] = t.meaning.replace({"asterisk": "context"})
BATCH = 200000
for name in ("ALL", "SP500"):
    z = np.load(E.CHUNKS / f"{y}__SECADD_{name}.npz"); ids = list(z["ids"]); tk = z["tickers"]; ds = z["dates"]; nd = len(ds); packed = z["packed"]
    g = [f"stk|james|{t.lens.get(i, 'none')}|{t.meaning.get(i, 'neutral')}" for i in ids]; G = sorted(set(g))
    M = np.zeros((len(ids), len(G)), np.float32)
    for j, x in enumerate(g): M[j, G.index(x)] = 1
    n = packed.shape[0]
    yes = np.zeros((n, len(G)), np.float32); rdy = np.zeros((n, len(G)), np.float32)
    for i0 in range(0, n, BATCH):
        C = E.unpack(packed[i0:i0+BATCH], len(ids))
        yes[i0:i0+BATCH] = (C == 2).astype(np.float32) @ M
        rdy[i0:i0+BATCH] = (C > 0).astype(np.float32) @ M
        del C
    d = {"ticker": np.repeat(tk, nd), "date": np.tile(ds, len(tk))}
    for k, x in enumerate(G):
        d[x + "|yes"] = yes[:, k].astype(np.int16); d[x + "|ready"] = rdy[:, k].astype(np.int16)
        d[x + "|frac"] = np.where(rdy[:, k] > 0, yes[:, k] / np.maximum(rdy[:, k], 1), np.nan).astype(np.float32)
    D = pd.DataFrame(d); D["report_only"] = D.date >= "2026-08-06"
    D.to_parquet(E.CHUNKS / f"{y}__COUNTS2_SECADD_{name}.parquet", index=False); print(name, D.shape)
