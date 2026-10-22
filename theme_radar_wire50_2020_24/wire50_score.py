# WIRE50 V1 scorer. 2020-24 only. Rules: RULES_V1.md + RULES_V1_ADDENDUM_A.md (committed before this ran).
import numpy as np, pandas as pd, glob, json, gc, hashlib
END=pd.Timestamp('2024-12-31'); FEE=0.006; ST='/workspace/checklist_brainstorm/mine/state_test/'; OPT='/workspace/tr_wire44/opt/'; RAW='/workspace/tr_wire44/raw/'
def sha(f): return hashlib.sha256(open(f,'rb').read()).hexdigest()
assert sha(ST+'tr_si/tr_si_frame.parquet').startswith('4fe7bfcd'); assert sha(ST+'attn/attn_frame.parquet').startswith('e6895ee2')
assert sha('/workspace/state_test/buyable_filter/drop_list_v2.csv').startswith('5a6cb756')
P=pd.read_parquet('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close'],filters=[('date','<=',END)])
P['ticker']=P.ticker.astype(str); P['date']=pd.to_datetime(P.date).astype('datetime64[ns]'); assert P.date.max()<=END
P=P.sort_values(['ticker','date']).reset_index(drop=True); n=len(P); tk=P.ticker.values
O,H,L,C=(P[c].values.astype(np.float64) for c in ['open','high','low','close'])
ok=np.zeros(n,bool); ok[:n-20]=tk[20:]==tk[:n-20]   # 21 bars from entry, same ticker
E1=np.full(n,np.nan); E2=np.full(n,np.nan); m=np.where(ok)[0]; e=O[m]; tp=e*1.2; ex=np.full(len(m),np.nan)
for d in range(15):
    live=np.isnan(ex); hit=live&(H[m+d]>=tp); ex[hit]=np.maximum(O[m+d][hit],tp[hit])
ex=np.where(np.isnan(ex),C[m+14],ex); E1[m]=ex/e-1-FEE; E2[m]=C[m+9]/e-1-FEE
E1[~np.isfinite(E1)|(np.abs(E1)>3)]=np.nan; E2[~np.isfinite(E2)|(np.abs(E2)>3)]=np.nan
DL=pd.read_csv('/workspace/state_test/buyable_filter/drop_list_v2.csv',parse_dates=['date']); DL['ticker']=DL.ticker.astype(str)
P['drop']=pd.MultiIndex.from_frame(P[['ticker','date']]).isin(pd.MultiIndex.from_frame(DL[['ticker','date']]))
buy=~P['drop'].values; di=pd.factorize(P.date)[0]
cm={}
for k,R in [('E1',E1),('E2',E2)]:
    v=buy&np.isfinite(R); s=np.bincount(di[v],R[v],minlength=di.max()+1); c=np.bincount(di[v],minlength=di.max()+1); cm[k]=np.where(c>0,s/np.maximum(c,1),np.nan)
# ATR20% and r5 for new rows (bars <= D)
pc=P.groupby('ticker',sort=False).close.shift(1); tr=np.maximum(P.high,pc.fillna(P.high))-np.minimum(P.low,pc.fillna(P.low))
P['atrp']=tr.groupby(P.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/P.close
P['r5']=P.close/P.groupby('ticker',sort=False).close.shift(5)-1
P['i']=np.arange(n); KEY=P[['ticker','date','i']]
def events_from(F,cols,off):
    # F: ticker,date + 0/1/2 cols sorted by ticker,date ; returns long events (row,ticker,i_entry)
    F=F.sort_values(['ticker','date']).reset_index(drop=True); F=F.merge(KEY,on=['ticker','date'],how='left')
    newt=F.ticker.ne(F.ticker.shift()).values; out=[]
    for c in cols:
        y=(F[c].values==2); prev=np.r_[False,y[:-1]]&~newt; first=y&~prev
        ii=F.i.values[first]; good=~np.isnan(ii); ii=ii[good].astype(int)+off
        ii=ii[ii<n]; ii=ii[tk[ii]==F.ticker.values[first][good][:len(ii)]] if len(ii) else ii
        out.append(pd.DataFrame({'row':c,'i':ii}))
    return pd.concat(out)
EV=[]
si=pd.read_parquet(ST+'tr_si/tr_si_frame.parquet'); sic=[c for c in si.columns if c.startswith(('OWN-TR','POS-TR'))]
si=si[['ticker','date']+sic]; si['ticker']=si.ticker.astype(str); si['date']=pd.to_datetime(si.date); assert si.date.max()<=END
e=events_from(si,sic,1); e['row']=e.row.str.split('|').str[0]; EV.append(e); del si; gc.collect()
at=pd.read_parquet(ST+'attn/attn_frame.parquet'); atc=[c for c in at.columns if c.startswith('tr-attn-') and '|' not in c]
at=at[['ticker','date']+atc]; at['ticker']=at.ticker.astype(str); at['date']=pd.to_datetime(at.date); assert at.date.max()<=END
EV.append(events_from(at,atc,1)); del at; gc.collect()
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
OP=[]
for f in sorted(glob.glob(OPT+'20*__OPT__*.parquet')):
    y=int(f.split('/')[-1][:4]); assert 2020<=y<=2024
    ids=json.load(open(f[:-8]+'.json'))['ids']; D=pd.read_parquet(f)
    cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(ids))
    OP.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc,columns=ids)],axis=1))
OP=pd.concat(OP); OP['date']=pd.to_datetime(OP.date); assert OP.date.max()<=END; opc=ids
cov=OP[opc].gt(0).any(axis=1).groupby(OP.date.dt.year).mean().round(3).to_dict()
EV.append(events_from(OP,opc,0)); del OP; gc.collect()
# NEW rows from raw volatility_history
RW=pd.concat([pd.read_csv(f) for f in sorted(glob.glob(RAW+'vol_history_20*.csv.gz'))]); RW['date']=pd.to_datetime(RW.date).astype('datetime64[ns]')
RW=RW[(RW.date>='2020-01-01')&(RW.date<=END)].rename(columns={'act_symbol':'ticker'}).drop_duplicates(['ticker','date'])
RW=RW.merge(P[['ticker','date','atrp','r5']],on=['ticker','date'],how='left')
def code(cond,ready): return np.where(~ready,0,np.where(cond,2,1))
c1=RW.iv_current/RW.iv_month_ago-1; c2=RW.iv_current/RW.iv_week_ago-1; im=(RW.iv_current/np.sqrt(252))/RW.atrp
RW['TR-OPX-IVCHG1M-UP']=code(c1>=0.25,c1.notna()); RW['TR-OPX-IVCHG1M-DN']=code(c1<=-0.25,c1.notna())
RW['TR-OPX-IVUP-PXUP']=code((c2>=0.10)&(RW.r5>0),c2.notna()&RW.r5.notna())
RW['TR-OPX-IMPMV-HI']=code(im>1.5,im.notna()); RW['TR-OPX-IMPMV-LO']=code(im<0.67,im.notna())
nc=['TR-OPX-IVCHG1M-UP','TR-OPX-IVCHG1M-DN','TR-OPX-IVUP-PXUP','TR-OPX-IMPMV-HI','TR-OPX-IMPMV-LO']
# entry = first session strictly after D: map each reading to next P row of same ticker
RW=RW.sort_values(['ticker','date']); out=[]
for c in nc:
    y=RW[c].values==2; newt=RW.ticker.ne(RW.ticker.shift()).values; prev=np.r_[False,y[:-1]]&~newt; F=RW[y&~prev][['ticker','date']]
    F=F.assign(date=F.date+pd.Timedelta(days=1)).sort_values('date')
    K=KEY.sort_values('date'); F=pd.merge_asof(F,K,on='date',by='ticker',direction='forward',tolerance=pd.Timedelta(days=5)).dropna()
    out.append(pd.DataFrame({'row':c,'i':F.i.astype(int).values}))
EV.append(pd.concat(out)); EV=pd.concat(EV,ignore_index=True)
i=EV.i.values; EV['buy']=buy[i]; EV['yr']=P.date.dt.year.values[i]
for k,R in [('E1',E1),('E2',E2)]: EV[k]=R[i]; EV[k+'x']=R[i]-cm[k][di[i]]
EV=EV[EV.buy]
rows=[]
for r,g in EV.groupby('row'):
    for k in ['E1','E2']:
        d=dict(row=r,exit=k)
        for per,msk in [('d',g.yr<=2022),('c',g.yr>=2023)]:
            x=g[msk&g[k].notna()]; d[per+'_n']=len(x); d[per+'_win']=(x[k]>0).mean()*100 if len(x) else np.nan
            d[per+'_mean']=x[k].mean()*100; d[per+'_med']=x[k].median()*100; d[per+'_exc']=x[k+'x'].mean()*100
        d['pass']=all(d[p+'_n']>=30 and d[p+'_win']>55 and d[p+'_exc']>0 for p in 'dc'); rows.append(d)
T=pd.DataFrame(rows).round(2); T.to_csv('WIRE50_RESULTS_V1.csv',index=False)
print(T.to_string()); print('passes',int(T['pass'].sum()),'of',len(T)); print('opt ready share by year',cov)
