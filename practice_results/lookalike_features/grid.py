"""Fixed lookback grid features (see LOOKBACK_GRID.md). PIT: all windows end at or before D-1. Output TMP/grid.parquet aligned with cells."""
import sys, os, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from build import PX, PX_SHA, HI, sha, TMP
WIN = [(f"lgE{e}L{n}", e, n) for e in (5, 10, 21, 42, 63, 126) for n in (5, 10, 21)] + [(f"trL{n}", 1, n) for n in (3, 5, 10, 20, 40, 60, 120)]
FT = ["trend", "redgreen", "gchain_len", "rchain_len", "gchain_move", "rchain_move", "voltrend", "dist_high"]
G = {}
def one(tk):
    g, rows, dates = G[tk]; o, h, c, v = (g[k].values.astype(float) for k in ("open", "high", "close", "volume")); d = g.date.values
    col = np.sign(c - o); out = np.full((len(rows), len(WIN) * 8), np.nan)
    for r, D in enumerate(dates):
        i = np.searchsorted(d, D)  # bars < D are [:i]
        for w, (_, e, n) in enumerate(WIN):
            end = i - e; st = end - n + 1
            if st < 1 or end < 0: continue
            s = col[st:end + 1]; cc = c[st:end + 1]; f = out[r, w * 8:(w + 1) * 8]
            f[0] = c[end] / c[st - 1] - 1; f[1] = (s < 0).sum() / max((s > 0).sum(), 1)
            b = np.flatnonzero(np.diff(s) != 0) + 1; a0 = np.r_[0, b]; a1 = np.r_[b, len(s)]; L = a1 - a0; sg = s[a0]
            mv = np.abs(c[st + a1 - 1] / c[st + a0 - 1] - 1)
            f[2] = L[sg > 0].max() if (sg > 0).any() else 0; f[3] = L[sg < 0].max() if (sg < 0).any() else 0
            f[4] = mv[sg > 0].max() if (sg > 0).any() else 0; f[5] = mv[sg < 0].max() if (sg < 0).any() else 0
            pv = v[max(0, st - 20):st]; f[6] = v[st:end + 1].mean() / pv.mean() if len(pv) == 20 and pv.mean() > 0 else np.nan
            f[7] = c[end] / h[st:end + 1].max() - 1
    return rows, out
if __name__ == "__main__":
    assert sha(PX) == PX_SHA
    cells = pd.read_parquet(f"{TMP}/cells.parquet", columns=["ticker", "date"])
    px = pq.read_table(PX, columns=["ticker", "date", "open", "high", "close", "volume"], filters=[("date", "<=", HI), ("ticker", "in", sorted(cells.ticker.unique()))]).to_pandas()
    assert px.date.max() <= HI; px["ticker"] = px.ticker.astype(str); px = px.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    ci = cells.groupby("ticker").indices
    for tk, g in px.groupby("ticker"):
        if tk in ci: G[tk] = (g, ci[tk], cells.date.values[ci[tk]])
    del px
    A = np.full((len(cells), len(WIN) * 8), np.nan, np.float32)
    with Pool(6) as p:
        for rows, out in p.imap_unordered(one, sorted(G), chunksize=20): A[rows] = out
    cols = [f"grid_{w}_{f}" for w, _, _ in WIN for f in FT]
    pd.DataFrame(A, columns=cols).to_parquet(f"{TMP}/grid.parquet"); print("grid", A.shape, np.isnan(A).mean())
