import numpy as np, pandas as pd
from scipy.stats import norm
END = pd.Timestamp("2024-12-31"); FEE = 0.006; HMAX = 21
P = pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet", filters=[("date", "<=", END)], columns=["ticker","date","open","high","low","close"])
P["ticker"] = P.ticker.astype(str); P["date"] = pd.to_datetime(P.date).astype("datetime64[ns]")
P = P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True); P["i"] = np.arange(len(P)); N = len(P); tk = P.ticker.values
assert P.date.max() <= END
M = pd.read_parquet("/workspace/state_test/story_q/panel.parquet", columns=["ticker","date"]); M["ticker"] = M.ticker.astype(str)
Dr = pd.read_csv("/workspace/state_test/buyable_filter/drop_list_v2.csv", parse_dates=["date"]); Dr["drop"] = True
M = M.merge(Dr, on=["ticker","date"], how="left"); M = M[M["drop"].isna()].drop(columns="drop"); del Dr
M = M.merge(P[["ticker","date","i"]], on=["ticker","date"])
idx = M.i.values[:, None] + np.arange(HMAX); ok = idx[:, -1] < N; idx = np.minimum(idx, N-1); ok &= tk[idx[:, -1]] == M.ticker.values
M = M[ok].reset_index(drop=True); idx = idx[ok]
gp = P.groupby("ticker"); c1 = gp.close.shift(1); adr = ((P.high-P.low)/P.close); P["adr20"] = adr.groupby(P.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
for k in (3,5,10): P[f"ret{k}"] = c1/gp.close.shift(1+k) - 1
PX = P[["ticker","date","adr20","ret3","ret5","ret10"]].copy()
O, H, C = (P[k].values.astype(np.float64)[idx] for k in ["open","high","close"]); del P
e = O[:, 0]; tp = e*1.2; ex = np.full(len(M), np.nan)
for d in range(15):
    t = np.isnan(ex) & (H[:, d] >= tp); ex[t] = np.maximum(O[t, d], tp[t])
M["rA"] = np.where(np.isnan(ex), C[:, 14], ex)/e - 1 - FEE; M["rB"] = C[:, 9]/e - 1 - FEE; del O, H, C, idx
for v in "AB": M["x"+v] = M["r"+v] - M.groupby("date")["r"+v].transform("mean")
M["buy"] = True; M = M[["ticker","date","rA","rB","xA","xB","buy"]]
S = pd.read_parquet("../exit_grid_v1/score/score_raw.parquet", columns=["ticker","date","score"])
Fz = pd.read_parquet("flips_raw.parquet"); S = S.merge(Fz, on=["ticker","date"], how="left"); del Fz
S = S.sort_values(["ticker","date"]).reset_index(drop=True); g = S.groupby("ticker")
S["s5"] = S.score - g.score.shift(5); S["s10"] = S.score - g.score.shift(10)
for k in (3,5,10): S[f"np{k}"] = S.np_yes - g.np_yes.shift(k)
S = S.merge(PX, on=["ticker","date"], how="left"); del PX
fams = {"F5": S.score.values > 78, "F1": S.score.values <= -84}
trades = []
for fam, pas in fams.items():
    T = S[["ticker","date","s5","s10","flip5","wf1","lf1","np_yes","np3","np5","np10","adr20","ret3","ret5","ret10"]].copy(); T["pass"] = pas
    newtk = (T.ticker != T.ticker.shift()).values
    start = pas & (newtk | ~np.r_[False, pas[:-1]])
    rid = np.cumsum(start); runlen = T.groupby(rid).cumcount().values + 1
    T["runlen"] = np.where(pas, runlen, 0); T["start"] = start
    # REPASS: any pass in 20 ticker days before the run start (excluding start)
    pp = pd.Series(pas.astype(int)).groupby(T.ticker.values).transform(lambda s: s.shift(1).rolling(20, min_periods=1).sum()).fillna(0).values
    T["repass"] = pp > 0
    T = T.merge(M, on=["ticker","date"], how="inner")  # buyable + 21 bars
    T["fam"] = fam; T["yr"] = T.date.dt.year
    st = T[T.start].copy(); d = st.yr <= 2022
    def terc(col, lab):
        c = np.nanpercentile(st.loc[d, col], [100/3, 200/3]); v = st[col].values
        return np.where(np.isnan(v), None, np.where(v <= c[0], lab[2], np.where(v <= c[1], lab[1], lab[0]))), c
    rows = [("BASE", "ALL_RUNSTARTS", st)]
    for col, lab in (("s5", ("UP","FLAT","DOWN")), ("s10", ("UP","FLAT","DOWN")), ("flip5", ("HI","MID","LO"))):
        b, c = terc(col, lab); print(fam, col, "cuts", c)
        for L in lab: rows.append(({"s5":"SLOPE5","s10":"SLOPE10","flip5":"FLIP5"}[col], L, st[b == L]))
    lf = np.where(st.wf1 > st.lf1, "W_LAST", np.where(st.lf1 > st.wf1, "L_LAST", "NONE_TIE"))
    for L in ("W_LAST","L_LAST","NONE_TIE"): rows.append(("LASTFLIP", L, st[lf == L]))
    rows += [("REPASS","REPASS",st[st.repass]), ("REPASS","FRESH",st[~st.repass])]
    for k in (3,5,10):
        up = st[f"np{k}"].values >= 2; r = st[f"ret{k}"].values; a = st.adr20.values
        flat = np.abs(r) < a; pu = r >= a; pdn = r <= -a
        div = up & flat; rows += [("DIV%d"%k, f"DIV{k}", st[div]), ("DIV%d"%k, f"DIV{k}_PDOWN", st[up & pdn]), ("DIV%d"%k, f"CTRL{k}_PUP", st[up & pu])]
        med = np.median(st.np_yes.values[div & d.values]); rows.append(("DIV%d"%k, f"CTRL{k}_NORISE", st[(st[f"np{k}"].values <= 0) & (st.np_yes.values >= med)]))
        print(fam, k, "NORISE level >=", med)
    ok5 = st.np5.notna() & st.ret5.notna(); ref = st[ok5 & d]
    pa = np.searchsorted(np.sort(ref.np5.values), st.np5.values, side="right")/len(ref); pb_ = np.searchsorted(np.sort(ref.ret5.values), st.ret5.values, side="right")/len(ref)
    dv = pa - pb_; cut = np.percentile(dv[(ok5 & d).values], 80); print(fam, "DIVC cut", cut)
    rows += [("DIVC", "DIVC_TOP", st[ok5.values & (dv > cut)]), ("DIVC", "DIVC_REST", st[ok5.values & (dv <= cut)])]
    for k, L in ((1,"R1"),(2,"R2"),(5,"R5")): rows.append(("RUNLEN", L, T[T.runlen == k]))
    for feat, L, sub in rows: trades.append(sub.assign(fam=fam, feat=feat, bucket=L)[["fam","feat","bucket","ticker","date","yr","rA","rB","xA","xB"]])
TR = pd.concat(trades, ignore_index=True)
rng = np.random.default_rng(13); out = []
for (fam, feat, b), G in TR.groupby(["fam","feat","bucket"], sort=False):
    for per, pm in (("2020_22", G.yr <= 2022), ("2023_24", G.yr >= 2023)):
        x = G[pm]; row = dict(family=fam, feature=feat, bucket=b, period=per, n=len(x))
        for v in "AB":
            r = x["r"+v].values; xx = x["x"+v].values
            dd = x.groupby("date")["x"+v].agg(["sum","count"]); sx, dn = dd["sum"].values, dd["count"].values
            bb = rng.integers(0, len(dn), (500, len(dn))); bs = sx[bb].sum(1)/dn[bb].sum(1); se = bs.std()
            z = xx.mean()/se if se > 0 else 0
            row.update({f"{v}_win": (r>0).mean()*100, f"{v}_mean": r.mean()*100, f"{v}_median": np.median(r)*100, f"{v}_excess": xx.mean()*100,
                        f"{v}_ci_lo": np.percentile(bs,2.5)*100, f"{v}_ci_hi": np.percentile(bs,97.5)*100, f"{v}_p": 2*norm.sf(abs(z))})
        out.append(row)
R = pd.DataFrame(out)
prev = pd.read_csv("../exit_grid_v1/score/score_results_v1.csv"); prev = prev[prev.group != "ALL"]
prevp = np.r_[prev.A_p.values, prev.B_p.values, pd.read_csv("../exit_grid_v1/stacks/stacks_results_v1.csv").query("group!='ALL'").p.values, pd.read_csv("../exit_grid_v1/exit_grid_results_v1.csv").query("group!='ALL'").p.values]
mine = np.r_[R.A_p.values, R.B_p.values]; allp = np.r_[mine, prevp]; n = len(allp)
o = np.argsort(allp); a = allp[o]*n/np.arange(1, n+1); a = np.minimum.accumulate(a[::-1])[::-1]; q = np.empty(n); q[o] = np.minimum(a, 1)
R["A_bh_q"] = q[:len(R)]; R["B_bh_q"] = q[len(R):2*len(R)]; R["bh_family"] = n
R.round(4).to_csv("trajectory_results_v1.csv", index=False); print("family", n); pd.set_option("display.width", 250)
print(R[["family","feature","bucket","period","n","A_excess","A_median","A_win","A_bh_q","B_excess","B_median","B_win","B_bh_q"]].round(3).to_string())
