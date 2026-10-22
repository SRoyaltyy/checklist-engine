import sys, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
sys.path.insert(0, "/workspace/checklist_brainstorm/path_bank_v2"); import path_bank_v2 as pb
END = pd.Timestamp("2024-12-31")
I = pd.read_csv("../exit_grid_v1/score/items_used_skipped.csv"); I = I[I.status == "use"]
B = pb.bank(); B = B[B.id.isin(I.item)].merge(I[["item", "dirs"]], left_on="id", right_on="item"); assert len(B) == 796
G = {}
NONPRICE = {"natr","atrtrend","rngcomp","rngexp","sqzexp","insidecnt","bodymean","uwickmean","bigvolday","vdry","volrel","voltrend"}
def one(tk):
    F = pb.features(G[tk]); keep = (F.date >= pd.Timestamp("2020-03-01")).values
    n=len(F); f5 = np.zeros(n, np.int32); wf1 = np.zeros(n, np.int32); lf1 = np.zeros(n, np.int32); npy = np.zeros(n, np.int32)
    for r in B.itertuples():
        x = F[r.feature]
        if r.family in pb.LABELS: v = (x == r.cut).values
        else:
            xv = x.astype(float).values; c = float(r.cut)
            with np.errstate(invalid="ignore"): v = {">=": xv >= c, ">": xv > c, "<=": xv <= c, "==": xv == c}[r.op]
        v = np.asarray(v, bool); p1 = np.r_[True, v[:-1]]; p5 = np.r_[np.ones(min(5,n), bool), v[:-5]][:n]
        f5 += v & ~p5
        if r.family in NONPRICE: npy += v
        if r.dirs == "W": wf1 += v & ~p1
        else: lf1 += v & ~p1
    return pd.DataFrame(dict(ticker=tk, date=F.date.values[keep], flip5=f5[keep], wf1=wf1[keep], lf1=lf1[keep], np_yes=npy[keep]))
if __name__ == "__main__":
    M = pd.read_parquet("/workspace/state_test/story_q/panel.parquet", columns=["ticker"]); tks = sorted(set(M.ticker.astype(str))); del M
    px = pq.read_table("/workspace/pricehist/universe_2020_survivors.parquet", columns=["ticker","date","open","high","low","close","volume"], filters=[("date", "<=", END)]).to_pandas()
    px["ticker"] = px.ticker.astype(str); px["date"] = pd.to_datetime(px.date).astype("datetime64[ns]"); assert px.date.max() <= END
    px = px[px.ticker.isin(tks)].drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    for tk, g in px.groupby("ticker"): G[tk] = g.reset_index(drop=True)
    del px
    with Pool(4) as p: S = pd.concat(p.map(one, sorted(G), chunksize=20), ignore_index=True)
    S.to_parquet("flips_raw.parquet"); print(S.shape, S.describe())
