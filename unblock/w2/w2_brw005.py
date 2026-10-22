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
MC=pd.read_parquet("mcap.parquet"); MC["date"]=MC.date.astype("datetime64[ns]"); M=M.merge(MC,on=["ticker","date"],how="left")
print("pre-filter",len(M),"mcap known",M.mcap.notna().mean(),"dropped <100M",(M.mcap<1e8).sum()); M=M[~(M.mcap<1e8)].drop(columns="mcap")
for v in "AB": M["x"+v]=M["r"+v]-M.groupby("date")["r"+v].transform("mean")
M=M.drop(columns="i").sort_values("date")
import numpy as _n
L=pd.read_csv("/workspace/regsho_nasdaq_th_2020_24.csv",parse_dates=["date"]); assert L.date.max()<=END
L["symbol"]=L.symbol.astype(str).str.replace(".","-",regex=False)
LD=_n.sort_values(L.date.unique()) if False else _n.sort(L.date.unique())
TX=pd.read_parquet("sec_tex.parquet"); NQ=set(TX[TX.exchange=="Nasdaq"].ticker.str.replace(".","-",regex=False))
F=M[["ticker","date"]].drop_duplicates().copy()
pos=_n.searchsorted(LD,F.date.values,side="left")-1; F["L"]=pd.NaT; ok=pos>=0; F.loc[ok,"L"]=LD[pos[ok]]
first=L.groupby("symbol").date.min()
on=set(zip(L.symbol,L.date))
F["onl"]=[(t,l) in on for t,l in zip(F.ticker,F.L)]
F["nq"]=F.ticker.isin(NQ)|(F.ticker.map(first)<=F.L)
stale=F.L.isna()|((F.date-F.L).dt.days>5)
F["REGSHO_TH"]=_n.where(stale,-1,_n.where(F.onl,1,_n.where(F.nq,0,-1))).astype("int8")
F=F[["ticker","date","REGSHO_TH"]]; print(F.REGSHO_TH.value_counts())
FEATS=[c for c in F.columns if c not in("ticker","date")]
J=M.merge(F,on=["ticker","date"],how="left"); del F
J["yr"]=J.date.dt.year; print("pop",len(J))
rng=np.random.default_rng(13); out=[]
for f in FEATS:
    G=J[J[f]==1]
    for per,pm in (("2020_22",G.yr<=2022),("2023_24",G.yr>=2023)):
        x=G[pm]; row=dict(feature=f,bucket="YES",period=per,n=len(x),n_dates=x.date.nunique(),no_data_share=round(float((J[f]==-1).mean()),4))
        for v in "AB":
            if len(x)==0: row.update({f"{v}_p":1.0}); continue
            r=x["r"+v].values; xx=x["x"+v].values
            dd=x.groupby("date")["x"+v].agg(["sum","count"]); sx,dn=dd["sum"].values,dd["count"].values
            bb=rng.integers(0,len(dn),(500,len(dn))); bs=sx[bb].sum(1)/dn[bb].sum(1); se=bs.std(); z=xx.mean()/se if se>0 else 0
            row.update({f"{v}_win":(r>0).mean()*100,f"{v}_mean":r.mean()*100,f"{v}_median":np.median(r)*100,f"{v}_excess":xx.mean()*100,
                        f"{v}_ci_lo":np.percentile(bs,2.5)*100,f"{v}_ci_hi":np.percentile(bs,97.5)*100,f"{v}_p":2*norm.sf(abs(z))})
        out.append(row); print(f,per,len(x),flush=True)
R=pd.DataFrame(out)
DL=[]
R["date_level"]=R.feature.isin(DL)
for v in "AB":
    pm={per:J[(J.yr<=2022) if per=="2020_22" else (J.yr>=2023)]["r"+v].mean()*100 for per in ("2020_22","2023_24")}
    R[v+"_vs_alldays"]=R[v+"_mean"]-R.period.map(pm)
    R.loc[R.date_level,v+"_p"]=1.0; R.loc[R.date_level,v+"_excess"]=0.0  # excess vs same-date mean is 0 by construction
BASE=14059
own=np.r_[R.A_p.values,R.B_p.values]; n=BASE+len(own); print("family n",n)
o=np.argsort(own); k=len(own); a=own[o]*n/np.arange(1,k+1); a=np.minimum.accumulate(a[::-1])[::-1]; q=np.empty(k); q[o]=np.minimum(a,1)
R["A_bh_q"]=q[:len(R)]; R["B_bh_q"]=q[len(R):2*len(R)]; R["bh_family"]=n
for v in "AB": R[v+"_ok"]=(R[v+"_win"]>55)&(R.n>=30)&(R[v+"_bh_q"]<0.05)&(R[v+"_excess"]>0)
R.round(4).to_csv("unblock_results_brw005.csv",index=False)
pas=R.groupby("feature")[["A_ok","B_ok"]].all(); print("PASS:\n",pas[pas.any(axis=1)])
pd.set_option("display.width",250); print(R[["feature","period","n","A_excess","A_win","A_bh_q","B_excess","B_win","B_bh_q"]].round(3).to_string())
