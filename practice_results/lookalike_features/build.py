#!/usr/bin/env python3
"""Look-alike feature mining — PRACTICE 2020-24, HINT only. Never reads 2025+ (filtered on load + asserted).
Features = existing checklist sheet rows already answered by the universe engine (YES/NO/NR as of D, bars < D):
  JG stock tier (James v5.5f/v8.2 ticker-dep rows), NB (New Bot v4.4f rows), TR (Theme Radar rows), SHARED (market-wide rows),
  plus the panel's chart-picture v2 checks + story questions; plus NEW rows (Cyrus chains, 40d trend/drawdown) not on the sheet.
Win = stock net return (30bp/side) beats the same-day matched-control mean (same base filter, rule = NO) at h=5/10/21."""
import glob, json, os, sys, hashlib, numpy as np, pandas as pd, pyarrow.parquet as pq
U = "/workspace/checklist_brainstorm/engine/universe/chunks"; TMP = "/workspace/tmp_laf"
PX = "/workspace/pricehist/universe_2020_survivors.parquet"; PX_SHA = "fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337"
PANEL = "/workspace/state_test/story_q/panel.parquet"; LO, HI = pd.Timestamp("2020-01-01"), pd.Timestamp("2024-12-31")
HARD = ["cp_mid_slope_up", "cp_gr_body20_ge_0p9", "cp_pctB_ge_0p12", "cp_dip_atr_le_4p2", "cp_days_since_h20_in_5_18", "cp_dd_vs_run_ge_0p5"]
SQ = [f"sq{i}_{n}" for i, n in enumerate(["lower_highs3", "higher_lows3", "shrinking_green3", "below_mid_5of10", "big_red_recent", "dip_vol_lower", "lowerbb_reclaim", "above_last_red_high", "breakdown_vol"], 1)]
NCAP = 30000; SEED = 7
def unpack(b, k): return np.stack([(b >> s) & 3 for s in (0, 2, 4, 6)], -1).reshape(b.shape[0], -1)[:, :k]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

def events():
    M = pq.read_table(PANEL, filters=[("date", ">=", LO), ("date", "<=", HI)]).to_pandas(); assert M.date.max() <= HI
    M["all6"] = (M[HARD].values == 2).all(1)
    G = {"chartpass_all6": (M.all6, ~M.all6), "q5_in_all6": (M.all6 & M.sq5_big_red_recent, M.all6 & ~M.sq5_big_red_recent),
         "q7_in_all6": (M.all6 & M.sq7_lowerbb_reclaim, M.all6 & ~M.sq7_lowerbb_reclaim), "q8_in_all6": (M.all6 & M.sq8_above_last_red_high, M.all6 & ~M.sq8_above_last_red_high)}
    out = []
    for g, (s, c) in G.items():
        E = M[s].copy()
        for h in (5, 10, 21):
            cm = M[c].groupby("date")[f"r{h}"].mean(); E[f"ex{h}"] = E[f"r{h}"] - E.date.map(cm)
        E["group"] = g; out.append(E)
    E = pd.concat(out, ignore_index=True)
    keep = ["group", "ticker", "date", "r5", "r10", "r21", "ex5", "ex10", "ex21"] + HARD + SQ
    return E[keep]  # ALL matching stock-days (no sampling)

def attach_npz(E, kind):
    """kind: '' JG stock, NB / NBX / JA_F4 parquet, TR npz, SHARED."""
    cols = {}; E = E.reset_index(drop=True); E["y"] = E.date.dt.year
    for y in range(2020, 2025):
        Ey = E[E.y == y]
        if not len(Ey): continue
        if kind == "SHARED":
            z = np.load(f"{U}/{y}__SHARED.npz"); ids = list(z["ids"]); dmap = {d: i for i, d in enumerate(z["dates"])}
            di = Ey.date.dt.strftime("%Y-%m-%d").map(dmap); ok = di.notna()
            A = unpack(z["packed"][di[ok].astype(int).values], len(ids))
            cols.setdefault("ids", ids); cols.setdefault("parts", []).append((Ey.index[ok].values, A)); continue
        files = sorted(glob.glob(f"{U}/{y}__TR__*.npz" if kind == "TR" else (f"{U}/{y}__{kind}__*.parquet" if kind else f"{U}/{y}__*.npz")))
        if not kind: files = [f for f in files if os.path.basename(f).count("__") == 1 and not os.path.basename(f)[6:-4].replace("_part", "").replace("_", "").isupper() and "SHARED" not in f]
        for f in files:
            if kind == "TR":
                z = np.load(f); ids = list(z["keys"]); key = pd.Index(pd.Series(z["ticker"]) + "|" + pd.Series(z["answer_date"]).str[:10]); P = z["packed"]
            elif kind:
                ids = json.load(open(f.replace(".parquet", ".json")))["ids"]; t = pq.read_table(f).to_pandas()
                key = pd.Index(t.ticker + "|" + pd.to_datetime(t.date).dt.strftime("%Y-%m-%d")); P = np.stack(t.packed.map(lambda b: np.frombuffer(b, np.uint8)).values)
            else:
                z = np.load(f); ids = list(z["ids"]); tk = z["tickers"]; ds = pd.Series(z["dates"]).str[:10].values
                key = pd.Index(np.repeat(tk, len(ds)).astype(object) + "|" + np.tile(ds, len(tk)).astype(object)); P = z["packed"]
            ek = Ey.ticker + "|" + Ey.date.dt.strftime("%Y-%m-%d"); pos = key.get_indexer(ek); ok = pos >= 0
            if ok.any():
                cols.setdefault("ids", ids); assert cols["ids"] == ids, f
                cols.setdefault("parts", []).append((Ey.index[ok].values, unpack(P[pos[ok]], len(ids))))
    ids = cols["ids"]; A = np.zeros((len(E), len(ids)), np.uint8)
    for ix, a in cols["parts"]: A[ix] = a
    return ids, A

def new_rows(E):
    """NEW rows (not on sheet): 40-bar trend/drawdown + Cyrus chain features, from bars < D."""
    px = pq.read_table(PX, columns=["ticker", "date", "open", "close"], filters=[("date", ">=", LO), ("date", "<=", HI),
         ("ticker", "in", sorted(E.ticker.unique()))]).to_pandas().drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    assert px.date.max() <= HI
    R = np.full((len(E), 16), np.nan); names = ["new_ret40", "new_slope40", "new_maxdd40", "new_g60_max", "new_r60_max", "new_g60_mean", "new_r60_mean",
        "new_gr60_lenratio", "new_gr60_moveratio", "new_g250_max", "new_r250_max", "new_gr250_lenratio", "new_gr250_moveratio", "new_cur_len_signed", "new_gmove60_max", "new_rmove60_max"]
    Eg = E.reset_index().groupby("ticker")
    for tk, p in px.groupby("ticker"):
        if tk not in Eg.groups: continue
        d = p.date.values; o = p.open.values; c = p.close.values; col = np.sign(c - o)
        for ei, D in zip(Eg.get_group(tk)["index"].values, Eg.get_group(tk).date.values):
            i = np.searchsorted(d, D)  # bars < D are [:i]
            if i < 60: continue
            cc = c[i - 40:i]; lr = np.log(cc); R[ei, 0] = cc[-1] / cc[0] - 1; R[ei, 1] = np.polyfit(np.arange(40), lr, 1)[0] * 40
            R[ei, 2] = (cc / np.maximum.accumulate(cc) - 1).min()
            def chains(n):
                s = col[max(0, i - n):i]; cl = c[max(0, i - n) - 1 if i - n > 0 else 0:i]
                b = np.flatnonzero(np.diff(s) != 0) + 1; st = np.r_[0, b]; en = np.r_[b, len(s)]
                L = en - st; sg = s[st]; base = c[max(0, i - n) - 1 + st].clip(1e-9) if i - n > 0 else c[np.maximum(st - 1, 0)]
                mv = c[max(0, i - n) - 1 + en] / base - 1 if i - n > 0 else c[en - 1] / base - 1
                return L, sg, mv
            L, sg, mv = chains(60); g, r = sg > 0, sg < 0
            if g.any() and r.any():
                R[ei, 3:7] = [L[g].max(), L[r].max(), L[g].mean(), L[r].mean()]; R[ei, 7] = L[g].max() / L[r].max()
                R[ei, 8] = mv[g].max() / max(-mv[r].min(), 1e-6); R[ei, 14] = mv[g].max(); R[ei, 15] = -mv[r].min()
            R[ei, 13] = L[-1] * sg[-1]
            if i >= 251:
                L, sg, mv = chains(250); g, r = sg > 0, sg < 0
                if g.any() and r.any(): R[ei, 9:13] = [L[g].max(), L[r].max(), L[g].max() / L[r].max(), mv[g].max() / max(-mv[r].min(), 1e-6)]
    return pd.DataFrame(R, columns=names, index=E.index)

if __name__ == "__main__":
    assert sha(PX) == PX_SHA, "price sha mismatch"
    E = events(); print("events", E.group.value_counts().to_dict(), flush=True)
    E.to_parquet(f"{TMP}/events.parquet")
    E = E[["ticker", "date"]].drop_duplicates().sort_values(["ticker", "date"]).reset_index(drop=True); E.to_parquet(f"{TMP}/cells.parquet")
    print("unique cells", len(E), flush=True)
    for kind in ["", "NB", "TR", "SHARED"]:
        ids, A = attach_npz(E, kind); np.savez_compressed(f"{TMP}/A_{kind or 'JG'}.npz", A=A, ids=np.array(ids)); print(kind or "JG", A.shape, (A > 0).mean(), flush=True)
    new_rows(E).to_parquet(f"{TMP}/new.parquet"); print("new done")
