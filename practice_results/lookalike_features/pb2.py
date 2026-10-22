"""Path bank v2 (frozen, /workspace/checklist_brainstorm/path_bank_v2, path_bank_v2.py sha d0910085…) answered at every setup cell.
PIT by construction (features shifted 1). Same price file sha fb9bbe69…ef337. Output: TMP/A_PB2.npz (0=NaN,1=NO,2=YES). Label rows skipped."""
import sys, os, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, "/workspace/checklist_brainstorm/path_bank_v2")
from build import PX, PX_SHA, LO, HI, sha, TMP
import path_bank_v2 as pb
cells = pd.read_parquet(f"{TMP}/cells.parquet", columns=["ticker", "date"]); cells["row"] = np.arange(len(cells))
G = {}
def one(tk):
    d = G[tk]
    F = pb.features(d); c = cells[cells.ticker == tk]
    F = F[F.date.isin(c.date)].merge(c[["date", "row"]], on="date"); return F
if __name__ == "__main__":
    assert sha(PX) == PX_SHA
    out = f"{TMP}/pb2_feats.parquet"
    if not os.path.exists(out):
        px = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"], filters=[("date", "<=", HI), ("ticker", "in", sorted(cells.ticker.unique()))]).to_pandas()
        assert px.date.max() <= HI; px = px.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
        for tk, g in px.groupby("ticker"): G[tk] = g
        del px
        with Pool(4) as p: F = pd.concat(p.map(one, sorted(G), chunksize=20), ignore_index=True)
        F.to_parquet(out)
    F = pd.read_parquet(out).sort_values("row").reset_index(drop=True); assert F.row.is_unique
    B = pb.bank(); B = B[B.kind == "yesno"]
    X = np.zeros((len(cells), len(B)), np.uint8); rows = F.row.values  # answer row-by-row into uint8 (same logic as pb.answer; avoids 6GB float frame)
    for j, r in enumerate(B.itertuples()):
        x = F[r.feature]
        if r.family in pb.LABELS: v = (x == r.cut).astype(float).where(x.notna()).values
        else:
            xv = x.astype(float).values; c = float(r.cut)
            with np.errstate(invalid="ignore"): v = {">=": xv >= c, ">": xv > c, "<=": xv <= c, "==": xv == c}[r.op].astype(float); v[np.isnan(xv)] = np.nan
        X[rows, j] = np.where(np.isnan(v), 0, np.where(v > 0, 2, 1))
    np.savez(f"{TMP}/A_PB2.npz", A=X, ids=np.array(B.id.tolist())); print("pb2", X.shape, (X > 0).mean())
