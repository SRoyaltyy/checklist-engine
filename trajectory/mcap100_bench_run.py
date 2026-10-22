import sys, numpy as np, pandas as pd
from scipy.stats import norm
END=pd.Timestamp("2024-12-31"); FEE=0.006; HMAX=21
P=pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet",filters=[("date","<=",END)],columns=["ticker","date","open","high","low","close"])
P["ticker"]=P.ticker.astype(str); P["date"]=pd.to_datetime(P.date).astype("datetime64[ns]")
P=P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True); P["i"]=np.arange(len(P)); N=len(P); tk=P.ticker.values
assert P.date.max()<=END
P["pclose"]=P.groupby("ticker").close.shift(1)
M=pd.read_parquet("/workspace/state_test/story_q/panel.parquet",columns=["ticker","date"]); M["ticker"]=M.ticker.astype(str)
Dr=pd.read_csv("/workspace/state_test/buyable_filter/drop_list_v2.csv",parse_dates=["date"]); Dr["drop"]=True
M=M.merge(Dr,on=["ticker","date"],how="left"); M=M[M["drop"].isna()].drop(columns="drop"); del Dr
M=M.merge(P[["ticker","date","i","pclose"]],on=["ticker","date"])
idx=M.i.values[:,None]+np.arange(HMAX); ok=idx[:,-1]<N; idx=np.minimum(idx,N-1); ok&=tk[idx[:,-1]]==M.ticker.values
M=M[ok].reset_index(drop=True); idx=idx[ok]
O,H,C=(P[k].values.astype(np.float64)[idx] for k in ["open","high","close"]); del P
e=O[:,0]; tp=e*1.2; ex=np.full(len(M),np.nan)
for d in range(15):
    t=np.isnan(ex)&(H[:,d]>=tp); ex[t]=np.maximum(O[t,d],tp[t])
M["rA"]=np.where(np.isnan(ex),C[:,14],ex)/e-1-FEE; M["rB"]=C[:,9]/e-1-FEE; del O,H,C,idx
# same cleaned share counts as mcap100_clean_run.py
Sh=pd.read_parquet("/workspace/mcap/nb_tags_v2/sec_shares_out_filed_le_2024.parquet"); Sh["filed"]=pd.to_datetime(Sh.filed).astype("datetime64[ns]")
med=Sh.groupby("ticker").val.transform("median"); bad=(Sh.val<=0)|(Sh.val>1e11)|(Sh.val>50*med)|(Sh.val<med/50)
Sh=Sh[~bad].sort_values(["ticker","filed","end"]).drop_duplicates(["ticker","filed"],keep="last"); Sh["d"]=Sh.filed+pd.Timedelta(days=1)
Sh["ticker"]=Sh.ticker.astype(str)
M=M.sort_values("date"); M=pd.merge_asof(M,Sh[["ticker","d","val"]].rename(columns={"d":"date"}).sort_values("date"),on="date",by="ticker",direction="backward")
M["mcap"]=M.pclose*M.val; M.loc[M.mcap>5e12,["val","mcap"]]=np.nan; M["noshares"]=M.mcap.isna()
filt={"OFF":np.ones(len(M),bool),"MAIN_keep_nocount":((M.mcap>=1e8)|M.noshares).values,"WARNING_drop_nocount":(M.mcap>=1e8).values}
B={}
for k,f in filt.items():
    g=M[f].groupby("date")[["rA","rB"]].mean(); g.columns=["bA","bB"]; B[k]=g
    print(k,"bench rows",int(f.sum()),"of",len(M))
T=pd.read_csv("trajectory_mcap100_clean_trades_v1.csv",parse_dates=["date"])
bo=B["OFF"].reindex(T.date).values
print("OFF reproduce max|dx|",np.nanmax(np.abs(T.rA.values-bo[:,0]-T.xA.values)),np.nanmax(np.abs(T.rB.values-bo[:,1]-T.xB.values)))
def score(T,bkey,tag):
    rng=np.random.default_rng(13); out=[]
    for var,G in (("MAIN_keep_nocount",T[(T.mcap>=1e8)|T.noshares]),("WARNING_drop_nocount",T[T.mcap>=1e8])):
        bk=var if bkey=="ON" else "OFF"; G=G.copy(); b=B[bk].reindex(G.date).values; bo=B["OFF"].reindex(G.date).values
        if bkey=="ON": G["xA"]=G.rA-b[:,0]; G["xB"]=G.rB-b[:,1]
        G["bA"]=b[:,0]; G["bAo"]=bo[:,0]; G["bB"]=b[:,1]; G["bBo"]=bo[:,1]
        for per,pm in (("2020_22",G.yr<=2022),("2023_24",G.yr>=2023)):
            x=G[pm]; row=dict(variant=var,period=per,n=len(x),n_noshares=int(x.noshares.sum()))
            for v in "AB":
                r=x["r"+v].values; xx=x["x"+v].values
                dd=x.groupby("date")["x"+v].agg(["sum","count"]); sx,dn=dd["sum"].values,dd["count"].values
                bb=rng.integers(0,len(dn),(500,len(dn))); bs=sx[bb].sum(1)/dn[bb].sum(1); se=bs.std(); z=xx.mean()/se if se>0 else 0
                row.update({f"{v}_win":(r>0).mean()*100,f"{v}_mean":r.mean()*100,f"{v}_median":np.median(r)*100,f"{v}_excess":xx.mean()*100,f"{v}_ci_lo":np.percentile(bs,2.5)*100,f"{v}_ci_hi":np.percentile(bs,97.5)*100,f"{v}_p":2*norm.sf(abs(z))})
                if tag: row.update({f"{v}_bench_filt":x["b"+v].mean()*100,f"{v}_bench_old":x["b"+v+"o"].mean()*100})
            row["A_pass"]=bool(row["A_win"]>55 and row["n"]>=30 and row["A_excess"]>0); out.append(row)
    return pd.DataFrame(out).round(4)
R0=score(T,"OFF",False); F=pd.read_csv("trajectory_mcap100_clean_results_v1.csv")
R0.to_csv("/tmp/off.csv",index=False); F.to_csv("/tmp/frozen.csv",index=False)
print("OFF == frozen 672d437e:",open("/tmp/off.csv").read()==open("/tmp/frozen.csv").read())
R=score(T,"ON",True); R.to_csv("trajectory_mcap100_bench_results_v1.csv",index=False); pd.set_option("display.width",300)
print(R.to_string())
