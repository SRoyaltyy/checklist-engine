import numpy as np,pandas as pd
END=pd.Timestamp("2024-12-31"); ts=lambda x:pd.to_datetime(x).astype("datetime64[ns]")
P=pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet",filters=[("date","<=",END)],columns=["ticker","date","close"])
P["ticker"]=P.ticker.astype(str); P["date"]=ts(P.date); P=P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True)
P["c1"]=P.groupby("ticker").close.shift()
SH=pd.read_parquet("nb/nb_tags_v2/sec_shares_out_filed_le_2024.parquet"); SH["ticker"]=SH.ticker.astype(str); SH["filed"]=ts(SH.filed); SH["end"]=ts(SH.end); SH=SH[SH.filed<=END]
med=SH.groupby("ticker").val.transform("median"); SH=SH[(SH.val>0)&(SH.val<=1e11)&(SH.val<=50*med)]
L=SH.sort_values(["ticker","filed","end"]); L["mx"]=L.groupby("ticker").end.cummax(); L=L[L.end==L.mx]  # latest period end known at each filing
L=L.drop_duplicates(["ticker","filed"],keep="last"); L["avail"]=ts(L.filed+pd.Timedelta(days=1))
m=pd.merge_asof(P.sort_values("date"),L.sort_values("avail")[["ticker","avail","val"]],left_on="date",right_on="avail",by="ticker")
m["mcap"]=m.val*m.c1; m[["ticker","date","mcap"]].to_parquet("mcap.parquet"); print(m.mcap.notna().mean(),(m.mcap<1e8).mean())
