"""Path-level set v2 (LOOKBACK_GRID.md). PIT: bars < D only. Outputs TMP/path2.parquet (scalar rows) and TMP/zpath.npz (z-normalised 60/126 close paths)."""
import sys, os, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from build import PX, PX_SHA, HI, sha, TMP
FT = ["dd126", "dd126_recov", "dd126_days_since_peak", "swings60", "swing_up60", "swing_dn60", "trendq_leg", "trendq20", "trendq60", "hl60", "lh60",
      "ceiling_tests60", "base_len", "base_shrink", "updn_vol_leg", "spike_share"]
G = {}
def r2(y):
    if len(y) < 5: return np.nan
    x = np.arange(len(y)); c = np.corrcoef(x, y)[0, 1]; return c * c
def z(p): s = p.std(); return (p - p.mean()) / s if s > 0 else np.zeros_like(p)
def one(tk):
    g, rows, dates = G[tk]; o, h, l, c, v = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "volume")); d = g.date.values
    n = len(c); sh = np.zeros(n, bool); sl = np.zeros(n, bool); k = np.arange(2, n - 2)
    sh[k] = (h[k] > h[k - 1]) & (h[k] > h[k - 2]) & (h[k] > h[k + 1]) & (h[k] > h[k + 2]); sl[k] = (l[k] < l[k - 1]) & (l[k] < l[k - 2]) & (l[k] < l[k + 1]) & (l[k] < l[k + 2])
    out = np.full((len(rows), len(FT)), np.nan); Z60 = np.full((len(rows), 60), np.nan, np.float32); Z126 = np.full((len(rows), 126), np.nan, np.float32)
    for r, D in enumerate(dates):
        i = np.searchsorted(d, D); f = out[r]
        if i >= 60:
            Z60[r] = z(np.log(c[i - 60:i]))
            w = slice(i - 60, i); cs = np.arange(i - 60, i - 2)  # swing confirmed needs 2 bars after -> only pivots <= i-3
            ups, dns = sh[cs], sl[cs]; f[3] = ups.sum() + dns.sum(); f[4] = ups.sum(); f[5] = dns.sum()
            hv = h[cs][ups]; lv = l[cs][dns]; f[9] = (np.diff(lv) > 0).sum() if len(lv) > 1 else 0; f[10] = (np.diff(hv) < 0).sum() if len(hv) > 1 else 0
            hh = h[w]; m = hh.argmax(); f[11] = ((hh >= 0.99 * hh.max()).sum() - 1)
            f[7] = r2(np.log(c[i - 20:i])); f[8] = r2(np.log(c[i - 60:i]))
            cc = c[i - 60:i]; ex = max(cc.argmax(), cc.argmin()); leg = slice(i - 60 + ex, i)
            if i - (i - 60 + ex) >= 10:
                lc = c[leg]; f[6] = r2(np.log(lc)); dr = np.diff(lc); vv = v[leg][1:]
                dv = vv[dr < 0].sum(); f[14] = vv[dr > 0].sum() / dv if dv > 0 else np.nan
                gain = lc[-1] - lc[0]; f[15] = dr.max() / gain if gain > 0 else np.nan
            ref = c[i - 1]; b = 0
            while b < i and abs(c[i - 1 - b] / ref - 1) <= 0.075: b += 1
            f[12] = b
            if b >= 6: rg = (h - l)[i - b:i]; f[13] = rg[b // 2:].mean() / max(rg[:b // 2].mean(), 1e-9)
        if i >= 126:
            Z126[r] = z(np.log(c[i - 126:i])); cc = c[i - 126:i]; pk = np.maximum.accumulate(cc); ddv = cc / pk - 1; t = ddv.argmin()
            f[0] = -ddv[t]; p = cc[:t + 1].argmax()
            f[1] = (cc[-1] - cc[t]) / (cc[p] - cc[t]) if cc[p] > cc[t] else np.nan; f[2] = 125 - cc.argmax()
    return rows, out, Z60, Z126
if __name__ == "__main__":
    assert sha(PX) == PX_SHA
    cells = pd.read_parquet(f"{TMP}/cells.parquet", columns=["ticker", "date"])
    px = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"], filters=[("date", "<=", HI), ("ticker", "in", sorted(cells.ticker.unique()))]).to_pandas()
    assert px.date.max() <= HI; px["ticker"] = px.ticker.astype(str); px = px.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"]); ci = cells.groupby("ticker").indices
    for tk, g in px.groupby("ticker"):
        if tk in ci: G[tk] = (g, ci[tk], cells.date.values[ci[tk]])
    del px
    A = np.full((len(cells), len(FT)), np.nan, np.float32); Z6 = np.full((len(cells), 60), np.nan, np.float32); Z12 = np.full((len(cells), 126), np.nan, np.float32)
    with Pool(6) as p:
        for rows, out, a, b in p.imap_unordered(one, sorted(G), chunksize=20): A[rows] = out; Z6[rows] = a; Z12[rows] = b
    pd.DataFrame(A, columns=[f"path2_{f}" for f in FT]).to_parquet(f"{TMP}/path2.parquet"); np.savez(f"{TMP}/zpath.npz", z60=Z6, z126=Z12)
    print("path2", A.shape, np.isnan(A).mean(0).round(2))
