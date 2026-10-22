"""Cyrus's extra NEW rows (not all on sheet), PIT: values for day D use bars < D only (everything shifted 1). PRACTICE 2020-24 HINT."""
import sys, os, numpy as np, pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import PX, PX_SHA, LO, HI, sha, TMP
def feats(p):
    o, h, l, c, v = p.open, p.high, p.low, p.close, p.volume; f = pd.DataFrame(index=p.index)
    col = np.sign(c - o); body = (c - o).abs() / o
    for n in (5, 10, 20): f[f"new_red_green_ratio{n}"] = (col < 0).rolling(n).sum() / (col > 0).rolling(n).sum().clip(lower=1)
    lg = body.where(col > 0).ffill(); lrd = body.where(col < 0).ffill(); f["new_last_green_vs_red_body"] = lg / lrd.clip(lower=1e-6)
    f["new_trend42_ret"] = c / c.shift(41) - 1
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    f["new_rsi14"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); f["new_macd_hist_pct"] = (m - m.ewm(span=9, adjust=False).mean()) / c
    f["new_rvol20"] = v / v.rolling(20).mean().shift(1)
    sm = c.rolling(20).mean(); sd = c.rolling(20).std(); f["new_bb_pctb"] = (c - (sm - 2 * sd)) / (4 * sd).replace(0, np.nan); f["new_bb_width"] = 4 * sd / sm
    for n in (5, 10, 20, 50, 100, 200): f[f"new_dist_sma{n}"] = c / c.rolling(n).mean() - 1
    return f.shift(1)  # PIT: row D sees bars < D
if __name__ == "__main__":
    assert sha(PX) == PX_SHA
    cells = pd.read_parquet(f"{TMP}/cells.parquet", columns=["ticker", "date"])
    px = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"], filters=[("date", ">=", LO), ("date", "<=", HI), ("ticker", "in", sorted(cells.ticker.unique()))]).to_pandas()
    assert px.date.max() <= HI
    px = px.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    F = pd.concat([feats(g) for _, g in px.groupby("ticker", sort=True)]); F[["ticker", "date"]] = px[["ticker", "date"]]
    out = cells.merge(F, on=["ticker", "date"], how="left").drop(columns=["ticker", "date"]); assert len(out) == len(cells)
    out.to_parquet(f"{TMP}/new2.parquet"); print("new2", out.shape, out.notna().mean().round(2).to_dict())
