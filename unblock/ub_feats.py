import numpy as np, pandas as pd, glob
END=pd.Timestamp("2024-12-31"); S="/workspace/unblock/src/"
def ts(x): return pd.to_datetime(x).astype("datetime64[ns]")
# ---------- prices (<=2024 only)
P=pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet",filters=[("date","<=",END)],columns=["ticker","date","open","high","low","close","volume"])
P["ticker"]=P.ticker.astype(str); P["date"]=ts(P.date); assert P.date.max()<=END
P=P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True); N=len(P)
tk=P.ticker.values; pos=P.groupby("ticker").cumcount().values
E_=pd.read_parquet("/workspace/pricehist/etf_2015.parquet",filters=[("date","<=",END)]); E_["date"]=ts(E_.date); E_["ticker"]=E_.ticker.astype(str)
spy=E_[E_.ticker=="SPY"].set_index("date").close.sort_index()
TD=pd.DatetimeIndex(sorted(set(spy.index)|set(P.date.unique()))); TD=TD[TD>="2015-01-01"]
TD=TD[TD.isin(spy.index)]  # NYSE sessions = SPY sessions
tdi=lambda d: np.searchsorted(TD.values,np.asarray(d,dtype="datetime64[ns]"))
P["ti"]=tdi(P.date)
def roll(x,w,f="mean"):
    r=np.array(getattr(pd.Series(x).rolling(w),f)().values,dtype=float); r[pos<w-1]=np.nan; return r
def lag(x,k):
    r=np.full(N,np.nan); r[k:]=x[:-k]; r[pos<k]=np.nan; return r
c,o,h,l,v=(P[k].values.astype(float) for k in ["close","open","high","low","volume"])
ret=c/lag(c,1)-1
F={}  # stock features at bar t (using data <= t); later shifted to D=t+1
F["PERF_W30"]=c/lag(c,5)-1>0.30, ~np.isnan(lag(c,5))
F["PERF_M_N30"]=c/lag(c,21)-1<-0.30, ~np.isnan(lag(c,21))
s5,s21=roll(ret,5,"std"),roll(ret,21,"std"); F["VOLW_2X"]=s5>2*s21, ~np.isnan(s21)
pc=lag(c,1); tr=np.fmax(h-l,np.fmax(abs(h-pc),abs(l-pc))); atr=roll(tr,14); F["ATR8"]=atr/c>0.08, ~np.isnan(atr)
m=pd.Series(spy.pct_change()).reindex(P.date).values
a,b=ret,m; ok=~(np.isnan(a)|np.isnan(b)); a0=np.where(ok,a,0); b0=np.where(ok,b,0)
def rc(w):
    n=roll(ok*1.,w,"sum"); sa,sb=roll(a0,w,"sum"),roll(b0,w,"sum"); sab,sbb,saa=roll(a0*b0,w,"sum"),roll(b0*b0,w,"sum"),roll(a0*a0,w,"sum")
    cov=sab/n-sa*sb/n**2; vb=sbb/n-(sb/n)**2; va=saa/n-(sa/n)**2; return cov/vb, cov/np.sqrt(va*vb), n
beta,_,n252=rc(252); F["BETA2"]=beta>2, n252>=200
_,c20,n20=rc(20); _,c120,n120=rc(120); F["BETA_BREAK"]=abs(c20-c120)>=0.4, (n120>=100)&(n20>=18)
F["CFO_N5"]=c/o-1<=-0.05, np.ones(N,bool)
d=np.diff(np.r_[np.nan,c]); d[pos==0]=np.nan
def wild(x,n=14):
    return pd.Series(x).groupby(tk).transform(lambda s:s.ewm(alpha=1/n,adjust=False,min_periods=n).mean()).values
up,dn=wild(np.where(d>0,d,0.)*np.where(np.isnan(d),np.nan,1)),wild(np.where(d<0,-d,0.)*np.where(np.isnan(d),np.nan,1))
rsi=100-100/(1+up/dn); F["RSI80"]=rsi>80,~np.isnan(rsi); F["RSI20"]=rsi<20,~np.isnan(rsi)
hi252,lo252=roll(h,252,"max"),roll(l,252,"min"); F["NEAR_52WH"]=c>=0.98*hi252,~np.isnan(hi252); F["NEAR_52WL"]=c<=1.02*lo252,~np.isnan(lo252)
uh=h-lag(h,1); dl=lag(l,1)-l; pdm=np.where((uh>dl)&(uh>0),uh,0.); mdm=np.where((dl>uh)&(dl>0),dl,0.); nn=np.isnan(pc)
pdm[nn]=np.nan; mdm[nn]=np.nan; tr2=np.where(nn,np.nan,tr)
atrw=wild(tr2); pdi=100*wild(pdm)/atrw; mdi=100*wild(mdm)/atrw; dx=100*abs(pdi-mdi)/(pdi+mdi); adx=wild(dx)
F["ADX25_UP"]=(adx>25)&(pdi>mdi), ~np.isnan(adx)&(pos>=40)
F["PENNY"]=c<5,np.ones(N,bool); F["HIGH_PRICE"]=c>500,np.ones(N,bool)
first=P.groupby("ticker").date.transform("min").values
F["NEW_LISTING"]=(first>np.datetime64("2020-03-01"))&((P.date.values-first)<=np.timedelta64(180,"D")), np.ones(N,bool)
yr=P.date.dt.year.values; ly=P.groupby(["ticker",yr]).close.transform("last")
yclose=pd.Series(ly.values,index=pd.MultiIndex.from_arrays([tk,yr])).groupby(level=[0,1]).first()
py=pd.Series(list(zip(tk,yr-1))).map(yclose.to_dict()).values.astype(float); ppy=pd.Series(list(zip(tk,yr-2))).map(yclose.to_dict()).values.astype(float)
mo,dy=P.date.dt.month.values,P.date.dt.day.values
F["_YTD"]=c/py-1, ~np.isnan(py)
sma50=roll(c,50); r20=c/lag(c,20)-1
sma200=roll(c,200)
# breadth per date (bar t)
B=pd.DataFrame({"date":P.date,"a":c>sma200,"v":~np.isnan(sma200)}); B=B[B.v].groupby("date").a.mean()
# ---- shift stock features to D: value at row i-1 used for row i
def toD(x):
    r=np.empty_like(x); r[1:]=x[:-1]; r[0]=x[0]; return r
same=np.r_[False,tk[1:]==tk[:-1]]
OUT=pd.DataFrame({"ticker":P.ticker,"date":P.date})
for k,(y,val) in F.items():
    if k.startswith("_"): continue
    val=np.asarray(val)&same; OUT[k]=np.where(toD(val),toD(np.asarray(y,bool)).astype(np.int8),-1).astype(np.int8)
ytd=toD(F["_YTD"][0]); yv=toD(F["_YTD"][1])&same&(P.date.dt.year.values==np.r_[0,yr[:-1]])
OUT["TAXLOSS"]=np.where((mo==12)&(dy<=20), np.where(yv,(ytd<-0.30).astype(int),-1),0).astype(np.int8)
pyr=py/ppy-1; first5=(P.groupby(["ticker",yr]).cumcount().values<5)&(mo==1)
OUT["TAXLOSS_REV"]=np.where(first5, np.where(~np.isnan(pyr),(pyr<-0.30).astype(int),-1),0).astype(np.int8)
c1,s50,r20d=toD(c),toD(sma50),toD(r20)
# ---------- earnings (Nasdaq 2020-24)
ER=pd.concat([pd.read_parquet(f) for y in range(2020,2025) for f in glob.glob(S+f"earn/data/earnings/nasdaq_*_{y}.parquet")])
ER["report_date"]=ts(ER.report_date); ER=ER[ER.report_date<=END]; ER["symbol"]=ER.symbol.astype(str)
ER=ER.sort_values("surprise_pct",na_position="last").drop_duplicates(["symbol","report_date"])[["symbol","report_date","surprise_pct"]].rename(columns={"symbol":"ticker"})
ER["rs"]=tdi(ER.report_date)
key=pd.Series(np.arange(N),index=pd.MultiIndex.from_arrays([tk,P.ti.values]))
def at(t,s):
    ix=pd.MultiIndex.from_arrays([t,s]); r=key.reindex(ix).values; return r
for k,dlt in (("im1",-1),("i0",0),("ip1",1)):
    ER[k]=at(ER.ticker.values,ER.rs.values+dlt)
def g(arr,ix): ix=np.asarray(ix); r=np.full(len(ix),np.nan); okk=~np.isnan(ix); r[okk]=arr[ix[okk].astype(int)]; return r
ER["mv2"]=g(c,ER.ip1)/g(c,ER.im1)-1
ER["gapfade"]=(g(o,ER.ip1)/g(c,ER.i0)>=1.05)&(g(c,ER.ip1)<g(o,ER.ip1))
ER=ER.sort_values(["ticker","rs"])
ER["bigmv"]=ER.groupby("ticker").mv2.transform(lambda s:s.abs().rolling(4,min_periods=2).mean())
OUT["ti"]=P.ti.values
OUT=OUT.sort_values("ti",kind="stable"); ORD=OUT.index.values; Es=ER.sort_values("rs")
nx=pd.merge_asof(OUT[["ticker","ti"]],Es[["ticker","rs"]],left_on="ti",right_on="rs",by="ticker",direction="forward")
k=(nx.rs-nx.ti).values; has=~np.isnan(k)
OUT["EARN_TODAY"]=np.where(k==0,1,0).astype(np.int8); OUT["EARN_TOMORROW"]=(k==1).astype(np.int8)
OUT["EARN_WITHIN5"]=((k>=1)&(k<=5)).astype(np.int8); OUT["BUYBACK_BLACKOUT"]=((k>=1)&(k<=20)).astype(np.int8)
OUT["_t2"]=OUT.ti-2
pv=pd.merge_asof(OUT[["ticker","_t2"]].astype({"_t2":"int64"}),Es[["ticker","rs","surprise_pct","mv2","bigmv"]].astype({"rs":"int64"}),left_on="_t2",right_on="rs",by="ticker",direction="backward")
age=(OUT.ti.values-pv.rs.values)
OUT["EPS_BEAT10"]=np.where(age<=60, np.where(pv.surprise_pct.notna(),(pv.surprise_pct>10).astype(int),-1),0).astype(np.int8)
OUT["PEAD"]=((age<=6)&(pv.surprise_pct>10)&(pv.mv2>0)).astype(np.int8).values
OUT["EARN_BIG_MOVER"]=np.where(pv.bigmv.notna(),(pv.bigmv>=0.10).astype(int),-1).astype(np.int8)
gf=pd.merge_asof(OUT[["ticker","_t2"]].astype({"_t2":"int64"}),Es[Es.gapfade][["ticker","rs"]].astype({"rs":"int64"}),left_on="_t2",right_on="rs",by="ticker",direction="backward")
OUT["EARN_GAP_FADE"]=((OUT.ti.values-gf.rs.values)<=11).astype(np.int8)  # gap day rs+1 within last 10 sessions
OUT["_t1"]=OUT.ti-1
lr=pd.merge_asof(OUT[["ticker","_t1"]].astype({"_t1":"int64"}),Es[["ticker","rs","i0"]].astype({"rs":"int64"}),left_on="_t1",right_on="rs",by="ticker",direction="backward")
OUT=OUT.sort_index(); lr.index=ORD; lr=lr.sort_index()
tpv=np.nan_to_num((h+l+c)/3*v); cv=np.cumsum(tpv); cvv=np.cumsum(np.nan_to_num(v))
i=np.arange(N); i0=lr.i0.values; okv=~np.isnan(i0)&((OUT.ti.values-lr.rs.values)<=60)&same
i0i=np.where(okv,i0,1).astype(int); j=i-1
vw=(cv[j]-np.where(i0i>0,cv[i0i-1],0))/(cvv[j]-np.where(i0i>0,cvv[i0i-1],0))
OUT["AVWAP_EARN"]=np.where(okv,(c1>vw).astype(int),0).astype(np.int8)
del F,ER,Es,nx,pv,gf,lr,tpv,cv,cvv,i,i0,i0i,j,vw,okv,beta,c20,c120,n252,n20,n120,a0,b0,a,b,m,ret,s5,s21,tr,tr2,atr,atrw,pdi,mdi,dx,adx,up,dn,rsi,uh,dl,pdm,mdm,hi252,lo252,d
import gc; gc.collect()
# ---------- dividends
DV=pd.read_parquet("/workspace/pricehist/dividends_2020.parquet",filters=[("ex_date","<=",END)]); DV["ticker"]=DV.ticker.astype(str); DV["date"]=ts(DV.ex_date)
DV=DV.groupby(["ticker","date"]).amount.sum().reset_index().sort_values(["ticker","date"]); DV["prev"]=DV.groupby("ticker").amount.shift()
X=OUT[["ticker","date"]].merge(DV,how="left",on=["ticker","date"]); ex=X.amount.notna().values; yl=X.amount.values/c1
OUT["EX_DIV"]=ex.astype(np.int8); OUT["EXDIV_1PCT"]=(ex&(yl>=0.01)&same).astype(np.int8); OUT["SPECIAL_DIV"]=(ex&(yl>=0.03)&same).astype(np.int8)
OUT["DIV_CUT"]=np.where(ex&X.prev.isna().values,-1,(ex&(X.amount.values<0.95*X.prev.values)).astype(int)).astype(np.int8)
# ---------- Form 4
f4=pd.concat([pd.read_parquet(f"/workspace/data/edgar_form4/dera_2020_24/form4_{y}.parquet",columns=["ticker","reporting_owner_cik","is_officer","is_amendment","filing_date","transaction_code","is_derivative","shares","price"]) for y in range(2020,2025)])
f4=f4[(~f4.is_derivative)&(~f4.is_amendment)&f4.transaction_code.isin(["P","S"])]; f4["fd"]=ts(f4.filing_date); f4=f4[f4.fd<=END]
f4["ticker"]=f4.ticker.astype(str).str.upper(); f4["val"]=f4.shares*f4.price
OUT["_dm1"]=OUT.date-pd.Timedelta(days=1)
def window_sum(ev,col,W,name):
    e=ev.groupby(["ticker","fd"])[col].sum().reset_index().sort_values("fd"); e["cs"]=e.groupby("ticker")[col].cumsum()
    q=OUT[["ticker","date"]].copy(); q["k1"]=q.date-pd.Timedelta(days=1); q["k0"]=q.date-pd.Timedelta(days=W+1); q["ix"]=np.arange(len(q))
    r1=pd.merge_asof(q.sort_values("k1"),e[["ticker","fd","cs"]],left_on="k1",right_on="fd",by="ticker").set_index("ix").cs
    r0=pd.merge_asof(q.sort_values("k0"),e[["ticker","fd","cs"]],left_on="k0",right_on="fd",by="ticker").set_index("ix").cs
    return (r1.sort_index().fillna(0)-r0.sort_index().fillna(0)).values
Pp=f4[f4.transaction_code=="P"].assign(one=1.); Sx=f4[f4.transaction_code=="S"]
for W,a1,a2,a3 in ((5,"450","451","452"),(30,"453","454","455"),(90,"456","457","458")):
    OUT[f"INS_P_{W}"]=(window_sum(Pp,"one",W,"p")>0).astype(np.int8)
    OUT[f"INS_SELL_{W}"]=(window_sum(Sx,"val",W,"s")>=1e6).astype(np.int8)
    po=Pp.drop_duplicates(["ticker","reporting_owner_cik","fd"]).sort_values(["ticker","reporting_owner_cik","fd"]).copy()
    po["st"]=po.fd+pd.Timedelta(days=1); po["en"]=po.fd+pd.Timedelta(days=W+1)  # covers D in [st,en)
    gk=[po.ticker,po.reporting_owner_cik]; pe=po.groupby(gk).en.shift(); 
    po["blk"]=(po.st>pe.fillna(pd.Timestamp("1900-01-01"))).astype(int).groupby(gk).cumsum()
    iv=po.groupby(["ticker","reporting_owner_cik","blk"]).agg(st=("st","min"),en=("en","max")).reset_index()
    ev=pd.concat([iv[["ticker","st"]].rename(columns={"st":"k"}).assign(d=1),iv[["ticker","en"]].rename(columns={"en":"k"}).assign(d=-1)])
    ev=ev.groupby(["ticker","k"]).d.sum().reset_index().sort_values(["ticker","k"]); ev["cnt"]=ev.groupby("ticker").d.cumsum(); ev=ev.sort_values("k")
    q=OUT[["ticker","date"]].assign(ix=np.arange(len(OUT))).sort_values("date")
    r=pd.merge_asof(q,ev[["ticker","k","cnt"]],left_on="date",right_on="k",by="ticker").set_index("ix").cnt.sort_index().fillna(0).values
    OUT[f"INS_CLUSTER_{W}"]=(r>=3).astype(np.int8)
OUT["INS_OFFICER_P30"]=(window_sum(Pp[Pp.is_officer].assign(one=1.),"one",30,"o")>0).astype(np.int8)
OUT["INS_P_AFTER_DROP"]=((OUT.INS_P_30==1)&(r20d<=-0.15)&same).astype(np.int8)
OUT["INS_P_BELOW50"]=((OUT.INS_P_5==1)&(c1<s50)&same).astype(np.int8)
# ---------- own seasonality (Stooq monthly, prior 10 yrs)
st=pd.read_parquet("/workspace/state_test/history10y/stooq_close_le2024.parquet"); st["date"]=ts(st.date); st=st[st.date<=END]; st["ticker"]=st.ticker.astype(str)
mc=st.groupby(["ticker",st.date.dt.to_period("M")]).close.last(); mr=(mc/mc.groupby(level=0).shift()-1).dropna().reset_index(); mr.columns=["ticker","per","r"]
mr["y"]=mr.per.dt.year; mr["m"]=mr.per.dt.month
W_=mr.pivot_table(index=["ticker","m"],columns="y",values="r")
rows=[]
for Y in range(2020,2025):
    cols=[y for y in range(Y-10,Y) if y in W_.columns]; sub=W_[cols]; full=sub.notna().sum(1)==10
    val=((sub.mean(1)>0.02)&((sub>0).sum(1)>=7)).astype(int).where(full,-1)
    rows.append(val.rename("OWN_SEAS").reset_index().assign(y=Y))
OS=pd.concat(rows)
X=OUT[["ticker","date"]].assign(y=OUT.date.dt.year,m=OUT.date.dt.month).merge(OS,how="left",on=["ticker","y","m"])
OUT["OWN_SEAS"]=X.OWN_SEAS.fillna(-1).astype(np.int8).values
OUT=OUT.drop(columns=[c for c in OUT.columns if c.startswith("_")]+["ti"])
OUT.to_parquet("ub_stock_ckpt.parquet"); B.to_frame().to_parquet("ub_breadth_ckpt.parquet")
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
