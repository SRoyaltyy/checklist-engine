import numpy as np, pandas as pd, glob, json
END=pd.Timestamp("2024-12-31"); DAY=pd.Timedelta(days=1)
def ts(x): return pd.to_datetime(x).astype("datetime64[ns]")
P=pd.read_parquet("/workspace/pricehist/universe_2020_survivors.parquet",filters=[("date","<=",END)],columns=["ticker","date","open","close"])
P["ticker"]=P.ticker.astype(str); P["date"]=ts(P.date); assert P.date.max()<=END
P=P.sort_values(["ticker","date"]).drop_duplicates(["ticker","date"]).reset_index(drop=True); N=len(P)
tk=P.ticker.values; pos=P.groupby("ticker").cumcount().values
def roll(x,w,f="mean"):
    r=np.array(getattr(pd.Series(x).rolling(w),f)().values,dtype=float); r[pos<w-1]=np.nan; return r
def lag(x,k):
    r=np.full(N,np.nan); r[k:]=x[:-k]; r[pos<k]=np.nan; return r
def toD(x):
    r=np.full(N,np.nan); r[1:]=x[:-1]; r[pos==0]=np.nan; return r
def B(cond,valid): return np.where(valid,np.asarray(cond,bool).astype(int),-1).astype(np.int8)
c=P.close.values.astype(float); o=P.open.values.astype(float)
OUT=pd.DataFrame({"ticker":P.ticker,"date":P.date}); IX=np.arange(N)
c1=toD(c)
# ---- price
s20=roll(c,20); sl=toD(s20)/toD(lag(s20,5)); OUT["SMA20_SLOPE_UP"]=B(sl>1,~np.isnan(sl))
g=toD(o/lag(c,1)-1); v=~np.isnan(g)
for t in (1,2,4,8): OUT[f"GAPD1_UP{t}"]=B(g>=t/100,v); OUT[f"GAPD1_DN{t}"]=B(g<=-t/100,v)
up5=toD(c/lag(c,5)-1)>0
def asof(right,key,cols,maxage=None):  # right: ticker, key(avail date) ; returns cols aligned to OUT rows
    q=OUT[["ticker","date"]].assign(ix=IX).sort_values("date"); r=right.copy(); r[key]=ts(r[key]); r=r.sort_values(key)
    m=pd.merge_asof(q,r[["ticker",key]+cols],left_on="date",right_on=key,by="ticker",direction="backward")
    if maxage is not None: m.loc[(m.date-m[key])>maxage,cols]=np.nan
    return m.set_index("ix").sort_index()
# ---- FINRA short volume (file t usable from t+1)
fr=[]
for f in sorted(glob.glob("finra/*.parquet")): fr.append(pd.read_parquet(f))
F=pd.concat(fr); F["ticker"]=F.Symbol.astype(str).str.replace("/","-"); F["date"]=ts(F.date); F=F[F.date<=END]
F=F[F.ticker.isin(set(tk))].groupby(["ticker","date"])[["ShortVolume","TotalVolume"]].sum().reset_index().sort_values(["ticker","date"])
gb=F.groupby("ticker")
for k in (1,5,20,60):
    F[f"svr{k}"]=gb.ShortVolume.transform(lambda s:s.rolling(k,min_periods=k).sum())/gb.TotalVolume.transform(lambda s:s.rolling(k,min_periods=k).sum())
F["p90"]=F.groupby("ticker").svr5.transform(lambda s:s.rolling(252,min_periods=120).quantile(0.9))
F["svr5_l5"]=F.groupby("ticker").svr5.shift(5); F["avail"]=F.date+DAY
S=asof(F,"avail",["svr1","svr5","svr20","svr60","p90","svr5_l5"],pd.Timedelta(days=6))
for k,i in ((1,""),(5,""),(20,"")):
    x=S[f"svr{k}"].values; v=~np.isnan(x)
    OUT[f"SVR{k}_HI"]=B(x>=0.6,v); OUT[f"SVR{k}_LO"]=B(x<=0.3,v); d=x-S.svr60.values; OUT[f"SVR{k}_JUMP"]=B(d>=0.1,~np.isnan(d))
OUT["SVR5_TOPDEC"]=B(S.svr5.values>=S.p90.values,~np.isnan(S.p90.values)&~np.isnan(S.svr5.values))
dd=S.svr5.values-S.svr5_l5.values; OUT["PRICEUP_SVRUP"]=B(up5&(dd>=0.1),~np.isnan(dd)&~np.isnan(toD(c/lag(c,5))))
del F,fr,S
# ---- SEC shares (cleaned)
SH=pd.read_parquet("nb/nb_tags_v2/sec_shares_out_filed_le_2024.parquet"); SH["ticker"]=SH.ticker.astype(str)
SH["filed"]=ts(SH.filed); SH["end"]=ts(SH.end); SH=SH[SH.filed<=END]
med=SH.groupby("ticker").val.transform("median"); SH=SH[(SH.val>0)&(SH.val<=1e11)&(SH.val<=50*med)].sort_values(["ticker","filed","end"])
rows=[]
for t,d in SH.groupby("ticker"):
    for fd in d.filed.unique():
        K=d[d.filed<=fd]; L=K.sort_values(["end","filed"]).iloc[-1]
        y=K[(K.end>=L.end-pd.Timedelta(days=430))&(K.end<=L.end-pd.Timedelta(days=300))]
        r=L.val/y.sort_values(["end","filed"]).val.iloc[-1] if len(y) else np.nan
        rows.append((t,fd+DAY,L.val,r))
SS=pd.DataFrame(rows,columns=["ticker","avail","sh","gr"])
A=asof(SS,"avail",["sh","gr"]); sh=A.sh.values; mcap=sh*c1; vm=~np.isnan(mcap)
OUT["MICROCAP"]=B(mcap<3e8,vm)
gr=A.gr.values; splitlike=np.zeros(N,bool)
for k in (2,3,4,5,10): splitlike|=np.abs(gr/k-1)<=0.02
OUT["SHARES_UP20"]=B((gr>=1.2)&~splitlike,~np.isnan(gr))
# ---- insider sells % mcap
f4=pd.concat([pd.read_parquet(f"/workspace/data/edgar_form4/dera_2020_24/form4_{y}.parquet",columns=["ticker","is_amendment","filing_date","transaction_code","is_derivative","shares","price"]) for y in range(2020,2025)])
f4=f4[(~f4.is_derivative)&(~f4.is_amendment)&(f4.transaction_code=="S")]; f4["fd"]=ts(f4.filing_date); f4=f4[f4.fd<=END]
f4["ticker"]=f4.ticker.astype(str).str.upper(); f4["val"]=f4.shares*f4.price
def window_sum(ev,col,W,datecol="fd"):
    ev=ev.copy(); ev[datecol]=ts(ev[datecol]); e=ev.groupby(["ticker",datecol])[col].sum().reset_index().sort_values(datecol); e["cs"]=e.groupby("ticker")[col].cumsum()
    q=OUT[["ticker","date"]].copy(); q["k1"]=q.date-DAY; q["k0"]=q.date-pd.Timedelta(days=W+1); q["ix"]=IX
    r1=pd.merge_asof(q.sort_values("k1"),e[["ticker",datecol,"cs"]],left_on="k1",right_on=datecol,by="ticker").set_index("ix").cs
    r0=pd.merge_asof(q.sort_values("k0"),e[["ticker",datecol,"cs"]],left_on="k0",right_on=datecol,by="ticker").set_index("ix").cs
    return (r1.sort_index().fillna(0)-r0.sort_index().fillna(0)).values
for W in (5,30,90): OUT[f"INS_SELL_1PCT_{W}"]=B(window_sum(f4,"val",W)>=0.01*mcap,vm)
del f4
# ---- FTD
FT=pd.read_parquet("ftd.parquet"); FT=FT[FT.ticker.isin(set(tk))]
yy=FT.per.str[:4].astype(int); mm=FT.per.str[4:6].astype(int); hb=FT.per.str[6]
pe=pd.to_datetime(dict(year=yy,month=mm,day=15)); pe=pe.where(hb=="a",pe+pd.offsets.MonthEnd(0)); FT["avail"]=pe+pd.Timedelta(days=15)
FS=FT.groupby(["ticker","per","avail"]).q.sum().reset_index().sort_values(["ticker","per"])
FS["prev"]=FS.groupby("ticker").q.shift(); FS["spike"]=(FS.prev>0)&(FS.q/FS.prev>=3)
# require previous file to be the immediately preceding half-month: approximate by availability gap <= 20 days
FS["pav"]=FS.groupby("ticker").avail.shift(); FS.loc[(FS.avail-FS.pav)>pd.Timedelta(days=20),"prev"]=np.nan
A=asof(FS,"avail",["q","prev"],pd.Timedelta(days=35)); fq=A.q.values; ok=~np.isnan(fq)&vm
# ticker-days with no fails row in an available file count as 0 fails (file exists): treat missing as 0 when any file available
fq0=np.where(np.isnan(fq),0,fq); ok=vm&(OUT.date.values>=np.datetime64("2019-03-01"))
OUT["FTD_01"]=B(fq0/sh>=0.001,ok); OUT["FTD_05"]=B(fq0/sh>=0.005,ok)
OUT["FTD_SPIKE"]=B((fq>0)&(A.prev.values>0)&(fq/A.prev.values>=3),~np.isnan(A.prev.values))
SP=FT.merge(FS[FS.spike][["ticker","per"]],on=["ticker","per"])[["ticker","sd","avail"]].drop_duplicates()
SP["st"]=np.maximum(SP.sd+pd.Timedelta(days=33),SP.avail); SP["en"]=SP.sd+pd.Timedelta(days=38)
SP=SP[SP.st<SP.en]; SP["st"]=ts(SP.st); SP["en"]=ts(SP.en)
ev=pd.concat([SP[["ticker","st"]].rename(columns={"st":"k"}).assign(d=1),SP[["ticker","en"]].rename(columns={"en":"k"}).assign(d=-1)])
ev=ev.groupby(["ticker","k"]).d.sum().reset_index().sort_values(["ticker","k"]); ev["cnt"]=ev.groupby("ticker").d.cumsum()
q=OUT[["ticker","date"]].assign(ix=IX).sort_values("date")
r=pd.merge_asof(q,ev.sort_values("k")[["ticker","k","cnt"]],left_on="date",right_on="k",by="ticker").set_index("ix").cnt.sort_index().fillna(0).values
OUT["FTD_T35"]=(r>0).astype(np.int8)
del FT,FS,SP
# ---- fundamentals
FN=pd.read_parquet("fund_snap.parquet"); FN["avail"]=ts(FN.filed)+DAY
cols=["rev_ann","ni_ann","oi_ann","ocf_ann","capex_ann","rev_yoy","rev_qq","eq","liab","ac","lc","cash","ocf_q"]
A=asof(FN,"avail",cols); a={k:A[k].values for k in cols}
OUT["CASH_RUNWAY4Q"]=B((a["ocf_q"]<0)&(a["cash"]/np.abs(a["ocf_q"])<4),~np.isnan(a["ocf_q"])&((a["ocf_q"]>=0)|~np.isnan(a["cash"])))
OUT["UNPROFITABLE"]=B(a["ni_ann"]<0,~np.isnan(a["ni_ann"]))
OUT["REV_YOY30"]=B(a["rev_yoy"]>=0.30,~np.isnan(a["rev_yoy"]))
OUT["SALES_QQ20"]=B(a["rev_qq"]>0.20,~np.isnan(a["rev_qq"]))
ey=a["ni_ann"]/mcap; OUT["EY3"]=B(ey>=0.03,~np.isnan(ey))
ps=np.where(a["rev_ann"]>0,mcap/a["rev_ann"],np.nan); PSd=pd.DataFrame({"d":OUT.date,"ps":ps})
thr=PSd.groupby("d").ps.transform(lambda s:s.quantile(0.95)).values; OUT["PS_TOP5"]=B(ps>=thr,~np.isnan(ps))
fcf=a["ocf_ann"]-np.nan_to_num(a["capex_ann"]); pf=mcap/fcf
OUT["PFCF_BAD"]=B((fcf<=0)|(pf>100),~np.isnan(fcf)&vm)
om=np.where(a["rev_ann"]>0,a["oi_ann"]/a["rev_ann"],np.nan); OUT["OPM_NEG"]=B(om<0,~np.isnan(om))
roe=np.where(a["eq"]>0,a["ni_ann"]/a["eq"],np.nan); OUT["ROE20"]=B(roe>0.2,~np.isnan(roe))
OUT["DE2"]=B((a["eq"]<=0)|(a["liab"]/a["eq"]>2),~np.isnan(a["eq"])&~np.isnan(a["liab"]))
cr=np.where(a["lc"]>0,a["ac"]/a["lc"],np.nan); OUT["CR_LT1"]=B(cr<1,~np.isnan(cr))
del FN,A,a
# ---- submissions: 8-K items, NT filings, SIC
SB=pd.concat([pd.read_parquet(f) for f in glob.glob("sub/*.parquet")]); SB["fd"]=ts(SB.filingDate); SB=SB[SB.fd<=END]
covered=set(SB.ticker); it=SB["items"].fillna("").astype(str)
k8=SB.form.str.startswith("8-K")
okS=OUT.ticker.isin(covered).values
for name,mask in (("EVT_502",k8&it.str.contains("5.02")),("EVT_NT_401",SB.form.isin(["NT 10-K","NT 10-Q"])|(k8&it.str.contains("4.01"))),("EVT_301",k8&it.str.contains("3.01"))):
    OUT[name]=B(window_sum(SB[mask].assign(one=1.),"one",7)>0,okS)
SIC=SB.drop_duplicates("ticker").set_index("ticker").sic
MAP=[("XLV",[(2830,2836),(3841,3851),(8000,8099),(5047,5047),(5122,5122)]),("XLP",[(2000,2199),(2840,2844),(5140,5149),(5400,5499),(5912,5912)]),
("XLE",[(1300,1399),(2900,2999),(4610,4619)]),("XLU",[(4900,4949)]),("XLRE",[(6500,6599),(6798,6798)]),("XLF",[(6000,6499),(6700,6797),(6799,6799)]),
("XLC",[(4800,4899),(2710,2799),(7810,7899)]),("XLK",[(3570,3579),(3600,3629),(3640,3699),(3825,3829),(7370,7379)]),
("XLY",[(2200,2399),(2500,2599),(3630,3639),(3710,3716),(3940,3949),(5200,5999),(7000,7299),(7500,7599),(7900,7999),(8200,8299)]),
("XLB",[(1000,1499),(2600,2699),(2800,2829),(2850,2899),(3200,3399)]),
("XLI",[(1500,1799),(3400,3569),(3580,3599),(3700,3799),(3800,3824),(4000,4599),(4700,4799),(5000,5099),(7380,7389),(8700,8748)])]
def sect(s):
    try: s=int(s)
    except: return None
    for e,rr in MAP:
        if any(a<=s<=b for a,b in rr): return e
    return None
SEC=SIC.map(sect); sec=OUT.ticker.map(SEC).values; print("sector map coverage",pd.notna(sec).mean(), pd.Series(SEC).value_counts().to_dict())
E_=pd.read_parquet("/workspace/pricehist/etf_2015.parquet",filters=[("date","<=",END)]); E_["date"]=ts(E_.date); E_["ticker"]=E_.ticker.astype(str)
EC=E_.pivot_table(index="date",columns="ticker",values="close").sort_index()
SP11=["XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY"]
r20=EC[SP11]/EC[SP11].shift(20)-1; rk=r20.rank(axis=1,ascending=False); nk=r20.notna().sum(1)
rkc=rk-rk.shift(20)  # negative = improved
ratio=(EC.XLY+EC.XLI+EC.XLF)/(EC.XLP+EC.XLU+EC.XLV); rch=ratio/ratio.shift(20)-1
# values at bar t -> used on next session D: build lookup by previous session date
pdate=pd.Series(P.date.values).groupby(tk).shift().values  # previous bar date of same ticker
pdate=np.where(pos>0,pdate,np.datetime64("NaT"))
def look(df,col_by_row):
    st=df.stack(); idx=pd.MultiIndex.from_arrays([pd.DatetimeIndex(pdate),col_by_row]); return st.reindex(idx).values
secs=np.where(pd.isna(sec),"NONE",sec).astype(object)
rkv=look(rk,secs); vv=~np.isnan(rkv)
OUT["SECT_TOP3"]=B(rkv<=3,vv); nkv=nk.reindex(pd.DatetimeIndex(pdate)).values; OUT["SECT_BOT3"]=B(rkv>=nkv-2,vv)
rcv=look(rkc,secs); OUT["SECT_RANK_UP5"]=B(rcv<=-5,~np.isnan(rcv))
rchv=rch.reindex(pd.DatetimeIndex(pdate)).values; cyc=np.isin(secs,["XLY","XLI","XLF","XLB"])
OUT["CYC_DEF_UP"]=B((rchv>0.03)&cyc,~np.isnan(rchv)&(secs!="NONE"))
er=EC[SP11].pct_change(); ser=er.stack().reindex(pd.MultiIndex.from_arrays([pd.DatetimeIndex(P.date.values),secs])).values
ret=c/lag(c,1)-1; okr=~(np.isnan(ret)|np.isnan(ser)); a0=np.where(okr,ret,0); b0=np.where(okr,ser,0)
n=roll(okr*1.,60,"sum"); sa,sb=roll(a0,60,"sum"),roll(b0,60,"sum"); sab,sbb,saa=roll(a0*b0,60,"sum"),roll(b0*b0,60,"sum"),roll(a0*a0,60,"sum")
cor=(sab/n-sa*sb/n**2)/np.sqrt((saa/n-(sa/n)**2)*(sbb/n-(sb/n)**2)); cor=toD(np.where(n>=50,cor,np.nan))
OUT["SECT_LOWCORR"]=B(cor<0.3,~np.isnan(cor))
yr=P.date.dt.year.values; ly=P.groupby(["ticker",yr]).close.transform("last").values
yc=pd.Series(ly,index=pd.MultiIndex.from_arrays([tk,yr])).groupby(level=[0,1]).first()
py=yc.reindex(pd.MultiIndex.from_arrays([tk,yr-1])).values; ytd_t=c/py-1  # at bar t (year of t)
EY=EC[SP11].groupby(EC.index.year).transform("last"); eyc=EC[SP11].groupby(EC.index.year).last()
ey_prev=eyc.shift(1).reindex(EC.index.year); ey_prev.index=EC.index; eytd=EC[SP11]/ey_prev-1
ev_=eytd.stack().reindex(pd.MultiIndex.from_arrays([pd.DatetimeIndex(P.date.values),secs])).values
dif=toD(ytd_t-ev_); sameyr=np.r_[False,yr[1:]==yr[:-1]]
OUT["YTD_VS_SECT20"]=B(dif>0.20,~np.isnan(dif)&sameyr)
# ---- date-level: CPI, NFP, CFTC
BL=pd.read_parquet("bls_dates.parquet"); dts=OUT.date.values
OUT["CPI_DAY"]=np.isin(dts,BL[BL.rel=="cpi"].date.values.astype("datetime64[ns]")).astype(np.int8)
OUT["NFP_DAY"]=np.isin(dts,BL[BL.rel=="empsit"].date.values.astype("datetime64[ns]")).astype(np.int8)
CF=pd.read_parquet("cftc_es.parquet").sort_values("rd"); CF["q10"]=CF.net.rolling(156,min_periods=156).quantile(0.1); CF["avail"]=ts(CF.rd+pd.Timedelta(days=4))
m=pd.merge_asof(OUT[["date"]].assign(ix=IX).sort_values("date"),CF[["avail","net","q10"]],left_on="date",right_on="avail").set_index("ix").sort_index()
OUT["CFTC_ES_LEVSHORT"]=B(m.net.values<=m.q10.values,~np.isnan(m.q10.values))
OUT.to_parquet("w2_feats.parquet",index=False)
print(OUT.drop(columns=["ticker","date"]).apply(lambda s:pd.Series({"yes":(s==1).sum(),"nodata":(s==-1).mean()})).T.to_string())
