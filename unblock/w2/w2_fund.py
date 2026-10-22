# per (ticker, filed-date) snapshot of fundamentals using only facts filed <= that date
import pandas as pd, numpy as np, glob, multiprocessing as mp, sys
REV=["Revenues","RevenueFromContractWithCustomerExcludingAssessedTax","SalesRevenueNet"]
def latest(d):  # latest end; ties -> latest filed
    if len(d)==0: return np.nan, None
    r=d.sort_values(["end","filed"]).iloc[-1]; return r.val, r.end
def one(f):
    d=pd.read_parquet(f)
    if len(d)==0: return None
    d=d[d.unit.isin(["USD","USD/shares"])&(d.filed<="2024-12-31")].copy()
    d["val"]=pd.to_numeric(d.val,errors="coerce"); d["end"]=pd.to_datetime(d.end); d["start"]=pd.to_datetime(d.start); d["filed"]=pd.to_datetime(d.filed)
    d["dur"]=(d.end-d.start).dt.days
    d["pri"]=d.concept.map({c:i for i,c in enumerate(REV)}).fillna(9)
    out=[]
    for fd in sorted(d.filed.unique()):
        if fd<pd.Timestamp("2018-06-01"): continue
        K=d[d.filed<=fd]
        def ann(c): return latest(K[(K.concept==c)&K.dur.between(350,380)])[0]
        def inst(c): return latest(K[(K.concept==c)&K.start.isna()])[0]
        R=K[K.concept.isin(REV)].sort_values(["pri","filed"]).drop_duplicates(["start","end"],keep="first")  # concept priority, then... 
        Ra=R[R.dur.between(350,380)]; rev_ann=Ra.sort_values("end").val.iloc[-1] if len(Ra) else np.nan
        Rq=R[R.dur.between(80,100)].sort_values("end"); yoy=qq=np.nan
        if len(Rq):
            e=Rq.end.iloc[-1]; v=Rq.val.iloc[-1]
            y=Rq[(Rq.end>=e-pd.Timedelta(days=385))&(Rq.end<=e-pd.Timedelta(days=345))]
            p=Rq[(Rq.end>=e-pd.Timedelta(days=105))&(Rq.end<=e-pd.Timedelta(days=75))]
            if len(y) and y.val.iloc[-1]>0: yoy=v/y.val.iloc[-1]-1
            if len(p) and p.val.iloc[-1]>0: qq=v/p.val.iloc[-1]-1
        O=K[(K.concept=="NetCashProvidedByUsedInOperatingActivities")&K.dur.between(80,380)]
        burn=np.nan
        if len(O): r=O.sort_values(["end","dur","filed"]).iloc[-1]; burn=r.val/(r.dur/91)
        out.append(dict(ticker=d.ticker.iloc[0],filed=fd,rev_ann=rev_ann,ni_ann=ann("NetIncomeLoss"),oi_ann=ann("OperatingIncomeLoss"),
            ocf_ann=ann("NetCashProvidedByUsedInOperatingActivities"),capex_ann=ann("PaymentsToAcquirePropertyPlantAndEquipment"),
            rev_yoy=yoy,rev_qq=qq,eq=inst("StockholdersEquity"),liab=inst("Liabilities"),ac=inst("AssetsCurrent"),lc=inst("LiabilitiesCurrent"),
            cash=inst("CashAndCashEquivalentsAtCarryingValue"),ocf_q=burn))
    return pd.DataFrame(out)
if __name__=="__main__":
    fs=sorted(glob.glob("cf/*.parquet"))
    with mp.Pool(6) as p: R=p.map(one,fs,chunksize=20)
    R=pd.concat([r for r in R if r is not None]); R.to_parquet("fund_snap.parquet"); print(len(R),R.ticker.nunique()); print(R.describe().T)
