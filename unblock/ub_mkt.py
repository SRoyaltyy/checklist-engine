import numpy as np, pandas as pd, glob
END=pd.Timestamp("2024-12-31"); S="/workspace/unblock/src/"
def ts(x): return pd.to_datetime(x).astype("datetime64[ns]")
# ---------- prices (<=2024 only)
E_=pd.read_parquet("/workspace/pricehist/etf_2015.parquet",filters=[("date","<=",END)]); E_["date"]=ts(E_.date); E_["ticker"]=E_.ticker.astype(str)
spy=E_[E_.ticker=="SPY"].set_index("date").close.sort_index()
TD=pd.DatetimeIndex(spy.index); TD=TD[TD>="2015-01-01"]
tdi=lambda d: np.searchsorted(TD.values,np.asarray(d,dtype="datetime64[ns]"))
B=pd.read_parquet("ub_breadth_ckpt.parquet").iloc[:,0]
ER=pd.concat([pd.read_parquet(f) for y in range(2020,2025) for f in glob.glob(S+f"earn/data/earnings/nasdaq_*_{y}.parquet")])
ER["report_date"]=ts(ER.report_date); ER=ER[ER.report_date<=END].drop_duplicates(["symbol","report_date"])
OUT=pd.read_parquet("ub_stock_ckpt.parquet")
# ---------- market-level by date D (in TD)
D=pd.Series(TD[TD>="2020-01-01"]); MK=pd.DataFrame({"date":D})
def asof(s,lagd=0):
    s=s.dropna().sort_index(); q=pd.DataFrame({"k":D-pd.Timedelta(days=lagd)})
    r=pd.merge_asof(q,pd.DataFrame({"k":s.index.astype("datetime64[ns]"),"v":s.values}),on="k",allow_exact_matches=False); return r.v.values
def fred(n):
    p=f"/workspace/data/fred/{n}.parquet"; 
    try: x=pd.read_parquet(p)
    except Exception: x=pd.read_parquet(S+n+".parquet")
    x["date"]=ts(x.date); x=x[x.date<=END]; return pd.to_numeric(x.set_index("date").value,errors="coerce").dropna()
def yb(x): return np.where(np.isnan(x),-1,x).astype(np.int8)
def B_(cond,valid): return np.where(valid,cond.astype(int),-1).astype(np.int8)
for nm,ser in (("DGS10","DGS10"),("DGS2","DGS2"),("DGS30","DGS30"),("DFII10","DFII10")):
    s=fred(ser); sm=s.rolling(20).mean(); hi=s.rolling(252).max()
    MK[nm+"_SMA20"]=yb(asof((s>=sm+0.15).astype(float).where(sm.notna())))
    MK[nm+"_HI252"]=yb(asof((s>=hi).astype(float).where(hi.notna())))
d10,d2=fred("DGS10"),fred("DGS2"); d3m=fred("DGS10")  # placeholder
for nm,ser,short in (("C2s10","T10Y2Y",d2),("C3m10","T10Y3M",None)):
    s=fred(ser); ch=s.diff(5)
    if short is None:
        short=d10-s  # 3m yield implied = 10y - spread
    sh=short.reindex(s.index).diff(5); lg=d10.reindex(s.index).diff(5)
    MK[nm+"_INV"]=yb(asof((s<0).astype(float)))
    MK[nm+"_BULLSTEEP"]=yb(asof(((ch>=0.15)&(sh<0)).astype(float).where(ch.notna())))
    MK[nm+"_BEARSTEEP"]=yb(asof(((ch>=0.15)&(lg>0)).astype(float).where(ch.notna())))
    cr=((s>=0)&(s.shift()<0)).astype(float); MK[nm+"_UNINV"]=yb(asof(cr.rolling(20).max()))
def trend(s):
    sm=s.rolling(50).mean(); up=((s>sm)&(sm.diff(5)>0)).astype(float).where(sm.notna()); lo=(s<=s.rolling(252).min()).astype(float).where(s.rolling(252).count()==252); return up,lo
xa=pd.read_parquet(S+"xasset_le2024.parquet"); xa=xa.set_index("Date") if "Date" in xa.columns else xa; xa.index=ts(xa.index); xa=xa[xa.index<=END]
for nm,s,lg in (("USD",fred("DTWEXBGS"),7),("WTI",fred("DCOILWTICO"),2),("JPY",xa["JPY=X"].dropna(),0),("GOLD",xa["GC=F"].dropna(),0),("COPPER",xa["HG=F"].dropna(),0)):
    u,lo=trend(s); MK[nm+"_UP"]=yb(asof(u,lg)); MK[nm+"_LO252"]=yb(asof(lo,lg))
cg=(xa["HG=F"]/xa["GC=F"]).dropna(); MK["CUAU_20D"]=yb(asof((cg/cg.shift(20)-1>0.05).astype(float).where(cg.shift(20).notna())))
rr=xa[["^GSPC","TLT"]].dropna().pct_change(); cor=rr["^GSPC"].rolling(60).corr(rr["TLT"]); MK["SPX_TLT_CORR"]=yb(asof((cor>0.3).astype(float).where(cor.notna())))
hi=(xa.HYG/xa.IEF).dropna(); MK["HYG_IEF"]=yb(asof((hi>hi.rolling(20).mean()).astype(float).where(hi.rolling(20).count()==20)))
MK["NFCI_POS"]=yb(asof((fred("NFCI")>0).astype(float),6))
st4=fred("STLFSI4"); MK["STLFSI_JUMP"]=yb(asof((st4.diff()>=0.5).astype(float).where(st4.diff().notna()),7))
wal,tga,rrp=fred("WALCL"),fred("WTREGEN"),fred("RRPONTSYD")
rrpw=rrp.reindex(wal.index,method="ffill").fillna(0); nl=wal-tga.reindex(wal.index,method="ffill")-1000*rrpw
MK["NETLIQ_UP"]=yb(asof((nl.diff(4)>0).astype(float).where(nl.diff(4).notna()),2))
rb=rrp.shift(20); MK["RRP_DROP"]=yb(asof(((rrp/rb-1<=-0.10)&(rb>=1)).astype(float).where(rb.notna())))
be=fred("T10YIE"); MK["BE10_RISE"]=yb(asof((be.diff(20)>=0.20).astype(float).where(be.diff(20).notna())))
CUTS=pd.to_datetime(["2019-07-31","2019-09-18","2019-10-30","2020-03-03","2020-03-15","2024-09-18","2024-11-07","2024-12-18"])
dd=MK.date.values
MK["CUT_90D"]=np.array([any((x>cu)&((x-cu).days<=90) for cu in CUTS) for x in MK.date]).astype(np.int8)
Di=tdi(MK.date); ci=tdi(CUTS)  # first session >= cut day (Sunday cut -> Monday = day 0? treat Sunday announcement: next session is session 1)
post=np.zeros(len(MK),bool)
for cu,k0 in zip(CUTS,ci):
    base=k0 if TD[k0]==cu else k0-1
    post|=(Di-base>=1)&(Di-base<=4)
MK["POST_CUT_1_4"]=post.astype(np.int8)
gs=pd.read_parquet(S+"gspc_skew_le2024.parquet"); gs=gs.set_index("Date") if "Date" in gs.columns else gs; gs.index=ts(gs.index); gs=gs[gs.index<=END]
MK["SKEW_150"]=yb(asof((gs["^SKEW"].dropna()>150).astype(float)))
sm200,sm50=spy.rolling(200).mean(),spy.rolling(50).mean()
MK["SPY_GT200"]=yb(asof((spy>sm200).astype(float).where(sm200.notna()))); MK["SPY_GOLDEN"]=yb(asof((sm50>sm200).astype(float).where(sm200.notna())))
MK["SPY_DD10"]=yb(asof((spy<=0.9*spy.rolling(252).max()).astype(float)))
MK["BREADTH200_60"]=yb(asof((B>0.60).astype(float)))
gr=gs["^GSPC"].dropna().pct_change().dropna(); gd=pd.DataFrame({"r":gr.values,"y":gr.index.year,"md":gr.index.strftime("%m-%d")})
MK["DOY_SEAS"]=[int(gd[(gd.md==x.strftime("%m-%d"))&(gd.y>=x.year-30)&(gd.y<x.year)].r.mean()>0.001) for x in MK.date]; MK["DOY_SEAS"]=MK.DOY_SEAS.astype(np.int8)
# calendar
dt=MK.date; wd=dt.dt.weekday; mo2=dt.dt.month
def third_fri(y,m): d0=pd.Timestamp(y,m,1); return d0+pd.Timedelta(days=(4-d0.weekday())%7+14)
tf=np.array([third_fri(x.year,x.month) for x in dt]); tfp=pd.to_datetime(tf)
MK["OPEX_DAY"]=(dt.values==tfp.values).astype(np.int8)
wk=lambda x: x.dt.to_period("W-SUN") if hasattr(x,"dt") else x.to_period("W-SUN")
MK["OPEX_WEEK"]=((wk(dt).values==pd.Series(tfp).dt.to_period("W-SUN").values)&(wd<=3)).astype(np.int8)
MK["POST_OPEX_WEEK"]=(wk(dt).values==(pd.Series(tfp).dt.to_period("W-SUN")+1).values).astype(np.int8)
MK["QUAD_WITCH"]=((MK.OPEX_DAY==1)&mo2.isin([3,6,9,12])).astype(np.int8)
TDs=set(TD); ve=[]
for y in range(2019,2026):
    for m_ in range(1,13):
        nm_=(y+(m_==12), m_%12+1); x=third_fri(*nm_)-pd.Timedelta(days=30)
        while x not in TDs and x<=END: x-=pd.Timedelta(days=1)
        ve.append(x)
MK["VIX_EXP"]=dt.isin(ve).astype(np.int8)
nwd=lambda x,s: x+pd.offsets.BDay(s)
MK["PRE_HOLIDAY"]=np.array([(nwd(x,1) not in TDs) and nwd(x,1)<=END for x in dt]).astype(np.int8)
MK["POST_HOLIDAY"]=np.array([nwd(x,-1) not in TDs for x in dt]).astype(np.int8)
MK["HALF_DAY"]=dt.isin(pd.to_datetime(["2020-11-27","2020-12-24","2021-11-26","2022-11-25","2023-07-03","2023-11-24","2024-07-03","2024-11-29","2024-12-24"])).astype(np.int8)
g_=MK.groupby([dt.dt.year,mo2]).cumcount(); g2=MK.iloc[::-1].groupby([dt.dt.year,mo2]).cumcount().iloc[::-1]
MK["SANTA"]=(((mo2==12)&(g2<5))|((mo2==1)&(g_<2))).astype(np.int8)
MK["SEPT"]=(mo2==9).astype(np.int8); MK["NOV_APR"]=mo2.isin([11,12,1,2,3,4]).astype(np.int8)
MK["ELECTION"]=dt.isin(pd.to_datetime(["2020-11-03","2022-11-08","2024-11-05"])).astype(np.int8)
MK["JACKSON_HOLE"]=dt.isin(pd.to_datetime(["2020-08-27","2021-08-27","2022-08-26","2023-08-25","2024-08-23"])).astype(np.int8)
wcnt=ER.groupby(ER.report_date.dt.to_period("W-SUN")).size()
MK["EARN_PEAK_WEEK"]=(wk(dt).map(wcnt).fillna(0).values>=1500).astype(np.int8)
print("weekly earn counts q:",wcnt.quantile([.5,.9,.99]).to_dict())
OUT=OUT.merge(MK,on="date",how="left")
for col in MK.columns[1:]: OUT[col]=OUT[col].fillna(-1).astype(np.int8)
OUT.to_parquet("ub_feats.parquet",index=False)
print(OUT.shape); print((OUT.drop(columns=["ticker","date"])==1).mean().round(4).to_string())
