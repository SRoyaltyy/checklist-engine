import numpy as np, pandas as pd
from scipy.stats import norm
END=pd.Timestamp("2024-12-31"); FEE=0.006; HMAX=21
P=pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet",filters=[("date","<=",END)],columns=["ticker","date","open","high","close"])
P["ticker"]=P.ticker.astype(str); P["date"]=pd.to_datetime(P.date).astype("datetime64[ns]")
P=P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True); P["i"]=np.arange(len(P)); N=len(P); tk=P.ticker.values
assert P.date.max()<=END
M=pd.read_parquet("/workspace/state_test/story_q/panel.parquet",columns=["ticker","date"]); M["ticker"]=M.ticker.astype(str); M["date"]=pd.to_datetime(M.date).astype("datetime64[ns]")
M=M[M.date<=END]
Dr=pd.read_csv("/workspace/state_test/buyable_filter/drop_list_v2.csv",parse_dates=["date"]); Dr["drop"]=True
M=M.merge(Dr,on=["ticker","date"],how="left"); M=M[M["drop"].isna()].drop(columns="drop"); del Dr
M=M.merge(P[["ticker","date","i"]],on=["ticker","date"])
idx=M.i.values[:,None]+np.arange(HMAX); ok=idx[:,-1]<N; idx=np.minimum(idx,N-1); ok&=tk[idx[:,-1]]==M.ticker.values
M=M[ok].reset_index(drop=True); idx=idx[ok]
O,H,C=(P[k].values.astype(np.float64)[idx] for k in ["open","high","close"]); del P
e=O[:,0]; tp=e*1.2; ex=np.full(len(M),np.nan)
for d in range(15):
    t=np.isnan(ex)&(H[:,d]>=tp); ex[t]=np.maximum(O[t,d],tp[t])
M["rA"]=np.where(np.isnan(ex),C[:,14],ex)/e-1-FEE; M["rB"]=C[:,9]/e-1-FEE; del O,H,C,idx
M=M[np.isfinite(M.rA)&np.isfinite(M.rB)]
for v in "AB": M["x"+v]=M["r"+v]-M.groupby("date")["r"+v].transform("mean")
M=M.drop(columns="i").sort_values("date")
F=pd.read_parquet("h10_feats.parquet").sort_values("sdate"); F["sdate"]=F.sdate.astype("datetime64[ns]")
FEATS=[c for c in F.columns if c.startswith("H10_")]
# features from last Stooq close strictly before D
J=pd.merge_asof(M,F,left_on="date",right_on="sdate",by="ticker",allow_exact_matches=False,direction="backward")
J.loc[J.sdate.isna()|((J.date-J.sdate).dt.days>10),FEATS]="NO_DATA"
J["yr"]=J.date.dt.year; print("pop",len(J),"no_data share",(J.H10_AGE=="NO_DATA").mean())
rng=np.random.default_rng(13); out=[]
for f in FEATS:
    for b,G in J.groupby(f):
        if b=="NO_DATA": continue
        for per,pm in (("2020_22",G.yr<=2022),("2023_24",G.yr>=2023)):
            x=G[pm]; row=dict(feature=f,bucket=b,period=per,n=len(x),n_dates=x.date.nunique())
            for v in "AB":
                r=x["r"+v].values; xx=x["x"+v].values
                dd=x.groupby("date")["x"+v].agg(["sum","count"]); sx,dn=dd["sum"].values,dd["count"].values
                bb=rng.integers(0,len(dn),(500,len(dn))); bs=sx[bb].sum(1)/dn[bb].sum(1); se=bs.std(); z=xx.mean()/se if se>0 else 0
                row.update({f"{v}_win":(r>0).mean()*100,f"{v}_mean":r.mean()*100,f"{v}_median":np.median(r)*100,f"{v}_excess":xx.mean()*100,
                            f"{v}_ci_lo":np.percentile(bs,2.5)*100,f"{v}_ci_hi":np.percentile(bs,97.5)*100,f"{v}_p":2*norm.sf(abs(z))})
            out.append(row)
R=pd.DataFrame(out)
base="/workspace/state_test/exit_grid_v1/"
prev=pd.read_csv(base+"score/score_results_v1.csv"); prev=prev[prev.group!="ALL"]
T=pd.read_csv("../trajectory/trajectory_results_v1.csv")
prevp=np.r_[prev.A_p.values,prev.B_p.values,pd.read_csv(base+"stacks/stacks_results_v1.csv").query("group!='ALL'").p.values,pd.read_csv(base+"exit_grid_results_v1.csv").query("group!='ALL'").p.values,T.A_p.values,T.B_p.values]
print("prior tests",len(prevp))
allp=np.r_[R.A_p.values,R.B_p.values,prevp]; n=len(allp)
o=np.argsort(allp); a=allp[o]*n/np.arange(1,n+1); a=np.minimum.accumulate(a[::-1])[::-1]; q=np.empty(n); q[o]=np.minimum(a,1)
R["A_bh_q"]=q[:len(R)]; R["B_bh_q"]=q[len(R):2*len(R)]; R["bh_family"]=n
for v in "AB": R[v+"_ok"]=(R[v+"_win"]>55)&(R.n>=30)&(R[v+"_bh_q"]<0.05)&(R[v+"_excess"]>0)
R.round(4).to_csv("history10y_results_v1.csv",index=False)
pas=R.groupby(["feature","bucket"])[["A_ok","B_ok"]].all(); print("PASS:\n",pas[pas.any(axis=1)])
pd.set_option("display.width",250); print(R[["feature","bucket","period","n","A_excess","A_win","A_bh_q","B_excess","B_win","B_bh_q"]].round(3).to_string())
