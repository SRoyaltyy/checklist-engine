"""Outcome file for Taskforce EXIT_RULE_V1 (practice_results/exit_grid_2020_24/EXIT_RULE_V1.md, sha 215de513…97d3):
entry open D (day 1 = D); take-profit +20% (exit max(open, target), gap fills at open); no stop; else close of day 15; 30bp/side.
Kept only if bars D..D+14 exist and are <= 2024-12-31. Writes TMP/outcome_v1.parquet with r5=r10=r21=v1 net return (pluggable OUTCOME_FILE)."""
import sys, os, numpy as np, pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from build import PX, PX_SHA, HI, sha, TMP
X, H, COST = 0.20, 15, 0.006
assert sha(PX) == PX_SHA
p = pq.read_table(PX, columns=["ticker", "date", "open", "high", "close"], filters=[("date", "<=", HI)]).to_pandas()
assert p.date.max() <= HI; p["ticker"] = p.ticker.astype(str); p = p.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"]).reset_index(drop=True)
o, h, c = p.open.values, p.high.values, p.close.values; t = p.ticker.values; n = len(p)
ex = np.full(n, np.nan); done = np.zeros(n, bool); tgt = o * (1 + X)
for k in range(H):
    j = np.arange(n) + k; ok = (j < n); jj = np.minimum(j, n - 1); same = ok & (t[jj] == t)
    hit = same & ~done & (h[jj] >= tgt); ex[hit] = np.maximum(o[jj][hit], tgt[hit]); done |= hit
    if k == H - 1: last = same & ~done; ex[last] = c[jj][last]; valid = same
r = ex / o - 1 - COST; r[~valid | ~np.isfinite(r)] = np.nan
O = pd.DataFrame({"ticker": t, "date": p.date.values, "r5": r, "r10": r, "r21": r}); O.to_parquet(f"{TMP}/outcome_v1.parquet"); print(O.r10.describe())
