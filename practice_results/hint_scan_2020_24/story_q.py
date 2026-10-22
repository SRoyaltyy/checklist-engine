#!/usr/bin/env python3
"""HINT scan 2020-24: cp_* gate + STORY_QUESTIONS_V1. Prices read date<=2024-12-31 only.
Signal D = ticker bar after t; features from bars<=t; entry open[D]; exit open[D+h] (h trading bars of that ticker); requires exit date <= 2024-12-31.
Net = gross - 0.006 (30bp/side)."""
import sys, glob, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
sys.path.insert(0, "/workspace/data/nb_v2"); from nb_year import unpack
PX = "/workspace/pricehist/universe_2020_survivors.parquet"; HI = pd.Timestamp("2024-12-31")
H = (5, 10, 21); COST = 0.006
SQ = ["sq1_lower_highs3", "sq2_higher_lows3", "sq3_shrinking_green3", "sq4_below_mid_5of10", "sq5_big_red_recent",
      "sq6_dip_vol_lower", "sq7_lowerbb_reclaim", "sq8_above_last_red_high", "sq9_breakdown_vol"]
CP = ["cp_mid_slope_up", "cp_gr_body20_ge_0p9", "cp_pctB_ge_0p12", "cp_dip_atr_le_4p2", "cp_days_since_h20_in_5_18", "cp_dd_vs_run_ge_0p5", "cp_redgreen_vol10_gt_1"]

def last_k_vals(flag_at, vals, k):  # for each t, the last k values where flag (confirmed by t), as array n x k (oldest..latest), nan if missing
    n = len(vals); out = np.full((n, k), np.nan); buf = []
    idx = np.where(flag_at)[0]; p = 0
    for t in range(n):
        while p < len(idx) and idx[p] <= t: buf.append(vals[idx[p]]); p += 1
        m = min(k, len(buf))
        if m: out[t, k - m:] = buf[-m:]
    return out

def story_feats(o, h, l, c, v):
    n = len(c); Q = np.zeros((n, 9), bool)
    if n < 25: return Q
    # swings: bar i, confirmed at i+2
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    i = np.arange(2, n - 2)
    sh[i] = (h[i] > h[i-1]) & (h[i] > h[i-2]) & (h[i] > h[i+1]) & (h[i] > h[i+2])
    sl[i] = (l[i] < l[i-1]) & (l[i] < l[i-2]) & (l[i] < l[i+1]) & (l[i] < l[i+2])
    shc = np.zeros(n, bool); shc[2:] = sh[:-2]; slc = np.zeros(n, bool); slc[2:] = sl[:-2]
    hv = np.r_[np.nan, np.nan, h[:-2]]; lv = np.r_[np.nan, np.nan, l[:-2]]; vv = np.r_[np.nan, np.nan, v[:-2]]
    H3 = last_k_vals(shc, hv, 3); L3 = last_k_vals(slc, lv, 3); V2 = last_k_vals(slc, vv, 2)
    with np.errstate(invalid="ignore"):
        Q[:, 0] = (H3[:, 0] > H3[:, 1]) & (H3[:, 1] > H3[:, 2])
        Q[:, 1] = (L3[:, 0] < L3[:, 1]) & (L3[:, 1] < L3[:, 2])
        Q[:, 5] = V2[:, 1] < V2[:, 0]
    body = np.abs(c - o); green = c > o; red = c < o
    # Q3
    G3 = np.full((n, 3), np.nan); gidx = np.where(green)[0]
    for t in range(n):
        p = np.searchsorted(gidx, t, side="right")
        if p >= 3 and gidx[p - 3] >= t - 9: G3[t] = body[gidx[p-3:p]]
    with np.errstate(invalid="ignore"): Q[:, 2] = (G3[:, 0] > G3[:, 1]) & (G3[:, 1] > G3[:, 2])
    s = pd.Series(c); mid = s.rolling(20).mean().values; sd = s.rolling(20).std(ddof=0).values; lb = mid - 2 * sd
    Q[:, 3] = pd.Series((c < mid).astype(float)).rolling(10).sum().values >= 5
    rb = np.where(red, body, -1.0)
    for t in range(19, n):
        w = rb[t-19:t+1]
        if w.max() > 0: Q[t, 4] = (19 - np.argmax(w[::-1])) >= 15
    touch = l <= lb; inside = c > lb
    rec = np.zeros(n, bool)  # rec[j]: touch at j and inside in j..j+3 (evaluated with cap t later)
    for t in range(n):
        for j in range(max(0, t - 9), t + 1):
            if touch[j] and inside[j:min(j + 3, t) + 1].any(): Q[t, 6] = True; break
    lastred = -1
    for t in range(n):
        if lastred >= 0 and t - lastred <= 60: Q[t, 7] = c[t] > h[lastred]
        if red[t]: lastred = t
    lo20 = pd.Series(l).rolling(20).min().shift(1).values; va20 = pd.Series(v).rolling(20).mean().shift(1).values
    with np.errstate(invalid="ignore"): bd = c < lo20; bdv = v >= 1.5 * va20
    lastbd = -1
    for t in range(n):
        if bd[t]: lastbd = t
        if lastbd >= 0 and t - lastbd <= 9: Q[t, 8] = bdv[lastbd]
    return Q

def per_ticker(args):
    tk, g = args
    o, h, l, c, v = (g[k].values.astype("float64") for k in ("open", "high", "low", "close", "volume"))
    d = g.date.values; n = len(c)
    if n < 62: return None
    Q = story_feats(o, h, l, c, v)
    t = np.arange(60, n - 1); D = t + 1
    rows = {"ticker": tk, "date": d[D], "sq_ready": True}
    for k, q in enumerate(SQ): rows[q] = Q[t, k]
    for hh in H:
        e = D + hh; ok = e < n
        r = np.full(len(D), np.nan); r[ok] = o[e[ok]] / o[D[ok]] - 1 - COST
        r[~np.isfinite(r)] = np.nan; rows[f"r{hh}"] = r
    return pd.DataFrame(rows)

def load_cp():
    out = []
    for f in sorted(glob.glob("/workspace/data/nb_v2/cp_build/chunks/20??__NBCP__*.parquet")):
        df = pd.read_parquet(f); U = unpack(np.frombuffer(b"".join(df.packed), np.uint8).reshape(len(df), -1), 7)
        x = pd.DataFrame(U.astype(np.int8), columns=CP); x["ticker"] = df.ticker.values; x["date"] = pd.to_datetime(df.date.values)
        out.append(x)
    return pd.concat(out, ignore_index=True)

def build():
    tick = sorted(set(pq.read_table(PX, columns=["ticker"], filters=[("date", "<=", HI)]).column(0).to_pylist()))
    parts = []
    with Pool(4) as pool:
        for i in range(0, len(tick), 500):
            p = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"],
                              filters=[("ticker", "in", tick[i:i+500]), ("date", "<=", HI)]).to_pandas()
            p["ticker"] = p.ticker.astype(str); assert p.date.max() <= HI
            p = p.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
            for r in pool.imap_unordered(per_ticker, list(p.groupby("ticker")), chunksize=16):
                if r is not None: parts.append(r)
            print("block", i, flush=True)
    S = pd.concat(parts, ignore_index=True); S["date"] = pd.to_datetime(S.date).astype("datetime64[ns]")
    C = load_cp(); M = S.merge(C, on=["ticker", "date"], how="left")
    for k in CP: M[k] = M[k].fillna(0).astype(np.int8)
    M.to_parquet("/workspace/state_test/story_q/panel.parquet", index=False); return M

if __name__ == "__main__": build()
