import pandas as pd, numpy as np, pyarrow.parquet as pq
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; FEE=0.002
A=pd.concat([pd.read_parquet(f'states_{y}_v5b.parquet' if y==2020 else f'states_{y}_v5.parquet') for y in range(2020,2025)]); A['ticker']=A.ticker.astype(str); A['date']=A.date.astype(str).str[:10]
MK=[]
for y in range(2020,2025):
    M=pd.read_parquet(C+f'{y}__FRESH_MKT_ADDON.parquet'); M['date']=M.date.astype(str).str[:10]
    f=lambda s:[c for c in M.columns if c.endswith(s)]
    MK.append(pd.DataFrame({'date':M.date,'m_fresh':M[f('qw_fresh')].sum(axis=1),'m_yes':M[f('qw_yes')].sum(axis=1),'m_rdy':M[f('qw_ready')].sum(axis=1)}))
mk=pd.concat(MK).sort_values('date').drop_duplicates('date'); mk['m_frac']=mk.m_yes/mk.m_rdy.replace(0,np.nan)
r=mk.m_frac.shift(1).rolling(20,min_periods=10); mk['m_jumpz']=(mk.m_frac-r.mean())/r.std().replace(0,np.nan)
A=A.merge(mk,on='date',how='left')
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],filters=[('date','>=',pd.Timestamp('2020-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=A.merge(px,on=['ticker','date'],how='left').merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True); A['year']=A.date.str[:4]
g=A.groupby('ticker',sort=False)
A['c_frac']=(A.s_yes+A.m_yes)/(A.s_rdy+A.m_rdy).replace(0,np.nan); gc_=A.groupby('ticker',sort=False).c_frac
A['c_jumpz']=(A.c_frac-gc_.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean()))/gc_.transform(lambda x:x.shift(1).rolling(20,min_periods=10).std()).replace(0,np.nan)
A['cumdiv']=g['div'].cumsum(); o=g.open; cd=g.cumdiv
A['fix5']=(o.shift(-6)+cd.shift(-6)-cd.shift(-1))/o.shift(-1)-1-FEE; A.loc[A.fix5.abs()>2,'fix5']=np.nan
A['ex5']=A.fix5-A.groupby('date').fix5.transform('mean')
lq=A.lean.quantile([.2,.4,.6,.8]).values; A['L']=np.digitize(A.lean,lq)+1
def cl(d,y='ex5'):
    d=d.dropna(subset=[y]); 
    if len(d)<2: return [np.nan]*3+[0,0]
    m=d[y].mean(); e=(d[y]-m).groupby(d.date).sum(); se=np.sqrt((e**2).sum())/len(d); return m,m-1.96*se,m+1.96*se,d.date.nunique(),len(d)
rows=[]
for yr in ['2020-24']+[str(y) for y in range(2020,2025)]:
    D=A if yr=='2020-24' else A[A.year==yr]; L5=D[D.L==5]
    for nm,mask in [('L5 all',L5.L==5),('L5 & stock-own jump z>=1.5',L5.jumpz>=1.5),('L5 & stock-own no jump',L5.jumpz<1.5),
       ('L5 & stock+mkt combined jump z>=1.5',L5.c_jumpz>=1.5),('L5 & combined no jump',L5.c_jumpz<1.5),('L5 on mkt-jump dates',L5.m_jumpz>=1.5)]:
        m,lo,hi,nd,n=cl(L5[mask]); rows.append(dict(period=yr,state=nm,ex5=m,lo95=lo,hi95=hi,n_dates=nd,n_obs=n,raw5=L5[mask].fix5.mean(),
            fresh_src='/'.join(sorted(L5[mask].fresh_src.unique()))))
R=pd.DataFrame(rows); R.to_csv('2020_24_v5b_spike_states.csv',index=False,float_format='%.5f')
E=pd.read_parquet('/workspace/pricehist/etf_2015.parquet'); E=E[(E.ticker.astype(str)=='IWM')&(E.date>='2020-01-01')&(E.date<'2025-01-01')].sort_values('date')
E['iwm5']=E.open.shift(-6)/E.open.shift(-1)-1-FEE; E['date']=E.date.dt.strftime('%Y-%m-%d')
Dm=mk.merge(E[['date','iwm5']],on='date').dropna(subset=['iwm5']); Dm['year']=Dm.date.str[:4]; MR=[]
for yr in ['2020-24']+[str(y) for y in range(2020,2025)]:
    D=Dm if yr=='2020-24' else Dm[Dm.year==yr]
    for nm,mask in (('mkt jump',D.m_jumpz>=1.5),('no mkt jump',D.m_jumpz<1.5)):
        d=D[mask]; m=d.iwm5.mean(); se=d.iwm5.std()/np.sqrt(len(d)); MR.append(dict(period=yr,state=nm,n_dates=len(d),iwm5=m,lo95=m-1.96*se,hi95=m+1.96*se,hit=(d.iwm5>0).mean()))
    a=D[D.m_jumpz>=1.5].iwm5; b=D[D.m_jumpz<1.5].iwm5; MR.append(dict(period=yr,state='jump minus no-jump',n_dates=len(a),iwm5=a.mean()-b.mean(),lo95=a.mean()-b.mean()-1.96*np.sqrt(a.var()/len(a)+b.var()/len(b)),hi95=a.mean()-b.mean()+1.96*np.sqrt(a.var()/len(a)+b.var()/len(b))))
MR=pd.DataFrame(MR); MR.to_csv('2020_24_v5b_mkt_iwm.csv',index=False,float_format='%.5f')
pd.set_option('display.width',220); print('lean cut L5 >=',lq[-1]); print(R.round(4).to_string()); print(MR.round(4).to_string())
print(A.groupby('year').fresh_src.value_counts().to_string()); print('rows',len(A),'fin rows',(A.sector=='Financial').sum())
