import numpy as np, pandas as pd
from scipy.stats import norm
T=pd.read_csv("trajectory_mcap100_trades_v1.csv",parse_dates=["date"]).drop(columns=["val","filed","mcap"])
T=T.rename(columns={"noshares":"noshares_old"})
old=pd.read_csv("trajectory_mcap100_trades_v1.csv",parse_dates=["date"])[["ticker","date","fam","bucket","val"]].rename(columns={"val":"val_old"})
Sh=pd.read_parquet("/workspace/mcap/nb_tags_v2/sec_shares_out_filed_le_2024.parquet"); Sh["filed"]=pd.to_datetime(Sh.filed).astype("datetime64[ns]")
med=Sh.groupby("ticker").val.transform("median")
bad=(Sh.val<=0)|(Sh.val>1e11)|(Sh.val>50*med)|(Sh.val<med/50)
print("rows",len(Sh),"bad",int(bad.sum()),"le0",int((Sh.val<=0).sum()),"gt1e11",int((Sh.val>1e11).sum()),"jump",int(((Sh.val>50*med)|(Sh.val<med/50)).sum()),"tickers",Sh[bad].ticker.nunique())
Sh=Sh[~bad].sort_values(["ticker","filed","end"]).drop_duplicates(["ticker","filed"],keep="last")
Sh["d"]=Sh.filed+pd.Timedelta(days=1)
T["date"]=T.date.astype("datetime64[ns]"); T=T.sort_values("date")
T=pd.merge_asof(T,Sh[["ticker","d","val"]].rename(columns={"d":"date"}).sort_values("date"),on="date",by="ticker",direction="backward")
T["mcap"]=T.pclose*T.val; big=T.mcap>5e12; print("trades >5T",int(big.sum())); T.loc[big,["val","mcap"]]=np.nan
T["noshares"]=T.val.isna()
T=T.drop_duplicates(["ticker","date"]).merge(old.drop_duplicates(["ticker","date"]),on=["ticker","date","fam","bucket"])
ch=~((T.val==T.val_old)|(T.val.isna()&T.val_old.isna()))
for nm,pm in (("2020_22",T.yr<=2022),("2023_24",T.yr>=2023)):
    x=T[pm]; print(nm,"trades",len(x),"count changed",int(ch[pm].sum()),"became missing",int((x.noshares&~x.noshares_old).sum()),"noshares",int(x.noshares.sum()),"known<100M",int(((x.mcap<1e8)&~x.noshares).sum()))
T.to_csv("trajectory_mcap100_clean_trades_v1.csv",index=False)
rng=np.random.default_rng(13); out=[]
for var,G in (("MAIN_keep_nocount",T[(T.mcap>=1e8)|T.noshares]),("WARNING_drop_nocount",T[T.mcap>=1e8])):
    for per,pm in (("2020_22",G.yr<=2022),("2023_24",G.yr>=2023)):
        x=G[pm]; row=dict(variant=var,period=per,n=len(x),n_noshares=int(x.noshares.sum()))
        for v in "AB":
            r=x["r"+v].values; xx=x["x"+v].values
            dd=x.groupby("date")["x"+v].agg(["sum","count"]); sx,dn=dd["sum"].values,dd["count"].values
            bb=rng.integers(0,len(dn),(500,len(dn))); bs=sx[bb].sum(1)/dn[bb].sum(1); se=bs.std(); z=xx.mean()/se if se>0 else 0
            row.update({f"{v}_win":(r>0).mean()*100,f"{v}_mean":r.mean()*100,f"{v}_median":np.median(r)*100,f"{v}_excess":xx.mean()*100,f"{v}_ci_lo":np.percentile(bs,2.5)*100,f"{v}_ci_hi":np.percentile(bs,97.5)*100,f"{v}_p":2*norm.sf(abs(z))})
        row["A_pass"]=bool(row["A_win"]>55 and row["n"]>=30 and row["A_excess"]>0); out.append(row)
R=pd.DataFrame(out).round(4); R.to_csv("trajectory_mcap100_clean_results_v1.csv",index=False); print(R[["variant","period","n","n_noshares","A_win","A_excess","A_ci_lo","A_ci_hi","A_p","A_pass","B_win","B_excess","B_p"]].to_string())
