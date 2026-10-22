import pandas as pd, numpy as np, json, pyarrow.parquet as pq, gc
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; FEE=0.002
rows=[]
for y in range(2020,2025):
    meta=json.load(open(C+f'{y}__JA_FRED_MKT.json')); ids=meta['ids']; k=len(ids)
    d=pd.read_parquet(C+f'{y}__JA_FRED_MKT.parquet'); b=np.stack([np.frombuffer(x,np.uint8) for x in d.packed])
    u=np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
    f=pd.DataFrame(u,columns=ids); f['date']=d.date.astype(str).str[:10].values; rows.append(f)
Q=pd.concat(rows,ignore_index=True); Q=Q[Q.date<'2025-01-01']; ids=[c for c in Q.columns if c!='date']
E=pd.read_parquet('/workspace/pricehist/etf_2015.parquet'); E=E[(E.ticker.astype(str)=='IWM')&(E.date>='2020-01-01')&(E.date<'2025-01-01')].sort_values('date')
E['iwm5']=E.open.shift(-6)/E.open.shift(-1)-1-FEE; E['date']=E.date.dt.strftime('%Y-%m-%d')
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],filters=[('date','>=',pd.Timestamp('2020-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)].sort_values(['ticker','date'])
g=px.groupby('ticker',sort=False).open; px['r']=(g.shift(-6)/g.shift(-1)-1).clip(-0.5,0.5)-FEE
ew=px.dropna(subset=['r']).groupby(px.date.dt.strftime('%Y-%m-%d')).r.mean().rename('ew5'); del px; gc.collect()
Q=Q.merge(E[['date','iwm5']],on='date',how='left').merge(ew,left_on='date',right_index=True,how='left')
rng=np.random.default_rng(0); B=2000; L=5
def boot(yes,ret):
    m=~np.isnan(ret); yes=yes[m]; ret=ret[m]; n=len(ret); nb=int(np.ceil(n/L)); st=rng.integers(0,n-L+1,(B,nb))
    idx=(st[:,:,None]+np.arange(L)).reshape(B,-1)[:,:n]; Y=yes[idx]; R=ret[idx]
    with np.errstate(invalid='ignore'):
        dd=(R*Y).sum(1)/Y.sum(1)-(R*~Y).sum(1)/(~Y).sum(1)
    obs=ret[yes].mean()-ret[~yes].mean(); dd=dd[~np.isnan(dd)]
    lo,hi=np.percentile(dd,[2.5,97.5]); p=min(1,2*min((dd<=0).mean(),(dd>=0).mean())); p=max(p,1/B)
    return obs,lo,hi,p
out=[]
for i in ids:
    c=Q[i].values; ready=c>0
    for side,code in (('YES',2),('NO',1)):
        yes=(c==code)[ready]; ny=int(yes.sum()); rec=dict(id=i,side=side,n_ready=int(ready.sum()),n_dates=ny)
        if ny<30 or ny>ready.sum()-30: rec['status']='too_few'; out.append(rec); continue
        for t in ('iwm5','ew5'):
            o,lo,hi,p=boot(yes,Q[t].values[ready]); rec.update({f'{t}_edge':o,f'{t}_lo':lo,f'{t}_hi':hi,f'{t}_p':p})
        sub=Q[ready]
        for y in range(2020,2025):
            s=sub[sub.date.str[:4]==str(y)]; yy=s[i].values==code
            rec[f'iwm_{y}']=s.iwm5[yy].mean()-s.iwm5[~yy].mean() if yy.sum()>0 and (~yy).sum()>0 else np.nan; rec[f'n_{y}']=int(yy.sum())
        rec['status']='tested'; out.append(rec)
R=pd.DataFrame(out); T=R[R.status=='tested'].copy()
for t in ('iwm5','ew5'):
    p=T[f'{t}_p'].values; o=np.argsort(p); m=len(p); th=(np.arange(1,m+1)/m)*0.05; ok=p[o]<=th
    kmax=np.max(np.where(ok)[0])+1 if ok.any() else 0; s=np.zeros(m,bool); s[o[:kmax]]=True; T[f'{t}_bh']=s
    T[f'{t}_ci_ex0']=(T[f'{t}_lo']>0)|(T[f'{t}_hi']<0)
R=R.merge(T[['id','side','iwm5_bh','ew5_bh','iwm5_ci_ex0','ew5_ci_ex0']],on=['id','side'],how='left')
R.to_csv('2020_24_fred_score.csv',index=False)
print(len(Q),Q.date.min(),Q.date.max(),'tested',len(T),'too_few',(R.status=='too_few').sum())
for t in ('iwm5','ew5'): print(t,'ci_ex0',int(T[f'{t}_ci_ex0'].sum()),'expected',0.05*len(T),'BH',int(T[f'{t}_bh'].sum()))
pd.set_option('display.width',250); print(R[R.iwm5_ci_ex0.fillna(False)|R.ew5_ci_ex0.fillna(False)|R.iwm5_bh.fillna(False)].drop(columns=['status']).round(4).to_string())
