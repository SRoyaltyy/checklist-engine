import pandas as pd, numpy as np, glob, pyarrow.parquet as pq, os
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
M=pd.read_parquet(C+'2024__FRESH_MKT_ADDON.parquet'); M['date']=M.date.astype(str).str[:10]
f=lambda s:[c for c in M.columns if c.endswith(s)]
mk=pd.DataFrame({'date':M.date,'m_fresh':M[f('qw_fresh')].sum(axis=1),'m_fresh_div':M[[c for c in f('qw_fresh') if 'iverg' in c]].sum(axis=1),
  'm_yes':M[f('qw_yes')].sum(axis=1),'m_rdy':M[f('qw_ready')].sum(axis=1)}).sort_values('date')
mk['m_frac']=mk.m_yes/mk.m_rdy.replace(0,np.nan); r=mk.m_frac.shift(1).rolling(20,min_periods=10)
mk['m_jumpz']=(mk.m_frac-r.mean())/r.std().replace(0,np.nan)
# stock yes/ready from FRESH (stock-scope) per sector; combined frac = (stk+mkt)
A=pd.read_parquet('states_2024_v3.parquet'); A=A[A.tr_joined]
parts=[]
for s in A.sector.unique():
    ff=C+f'2024__FRESH__{s}.parquet'
    if not os.path.exists(ff): continue
    n=pq.ParquetFile(ff).schema.names; y=[c for c in n if c.endswith('qw_yes')]; rr=[c for c in n if c.endswith('qw_ready')]
    F=pd.read_parquet(ff,columns=['ticker','date']+y+rr); parts.append(pd.DataFrame({'ticker':F.ticker.astype(str),'date':F.date.astype(str).str[:10],'s_yes':F[y].sum(axis=1),'s_rdy':F[rr].sum(axis=1)}))
S=pd.concat(parts); A=A.merge(S,on=['ticker','date'],how='inner').merge(mk,on='date',how='left')
A=A.sort_values(['ticker','date']).reset_index(drop=True)
A['c_frac']=(A.s_yes+A.m_yes)/(A.s_rdy+A.m_rdy).replace(0,np.nan)
g=A.groupby('ticker').c_frac
A['c_jumpz']=(A.c_frac-g.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean()))/g.transform(lambda x:x.shift(1).rolling(20,min_periods=10).std()).replace(0,np.nan)
A['c_fresh']=A.fresh+A.m_fresh
# returns (2024 prices only)
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],filters=[('date','>=',pd.Timestamp('2024-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d')
A=A.merge(px,on=['ticker','date'],how='left').sort_values(['ticker','date']).reset_index(drop=True)
o=A.groupby('ticker').open; A['fix5']=o.shift(-6)/o.shift(-1)-1-0.002; A.loc[A.fix5.abs()>2,'fix5']=np.nan  # dividends omitted here (v3 cap/flag negligible) 
A['ex5']=A.fix5-A.groupby('date').fix5.transform('mean')
lq=[0.44224423,0.50784594,0.56261683,0.61891115]; A['L']=np.digitize(A.lean,lq)+1  # 2020-24 pooled cuts (v3)
def cl(d,y='ex5'):
    d=d.dropna(subset=[y]); m=d[y].mean(); e=(d[y]-m).groupby(d.date).sum(); se=np.sqrt((e**2).sum())/len(d); return m,m-1.96*se,m+1.96*se,d.date.nunique(),len(d)
L5=A[A.L==5]; rows=[]
for nm,mask in [('L5 all',L5.L==5),('L5 & stock-only jump (v3 def)',L5.jumpz>=1.5),('L5 & stock-only no jump',L5.jumpz<1.5),
  ('L5 & combined stk+mkt jump',L5.c_jumpz>=1.5),('L5 & combined no jump',L5.c_jumpz<1.5),
  ('L5 & stock jump & NOT combined jump',(L5.jumpz>=1.5)&(L5.c_jumpz<1.5)),('L5 & combined jump & NOT stock jump',(L5.c_jumpz>=1.5)&(L5.jumpz<1.5)),
  ('L5 on mkt-jump dates (m_jumpz>=1.5)',L5.m_jumpz>=1.5),('L5 on non-mkt-jump dates',L5.m_jumpz<1.5)]:
    m,lo,hi,nd,n=cl(L5[mask]); rows.append(dict(state=nm,ex5=m,lo95=lo,hi95=hi,n_dates=nd,n_obs=n))
for q,lab in ((L5.c_fresh>=L5.c_fresh.quantile(2/3),'L5 & combined fresh top third'),(L5.c_fresh<=L5.c_fresh.quantile(1/3),'L5 & combined fresh bottom third')):
    m,lo,hi,nd,n=cl(L5[q]); rows.append(dict(state=lab,ex5=m,lo95=lo,hi95=hi,n_dates=nd,n_obs=n))
R=pd.DataFrame(rows); R.to_csv('2024_v4_stock_states.csv',index=False,float_format='%.5f')
# market-wide by date vs IWM
E=pd.read_parquet('/workspace/pricehist/etf_2015.parquet'); E=E[(E.ticker.astype(str)=='IWM')&(E.date>='2024-01-01')&(E.date<'2025-01-01')].sort_values('date')
E['iwm5']=E.open.shift(-6)/E.open.shift(-1)-1-0.002; E['date']=E.date.dt.strftime('%Y-%m-%d')
D=mk.merge(E[['date','iwm5']],on='date').dropna(subset=['iwm5'])
D['mf_t']=pd.qcut(D.m_fresh.rank(method='first'),3,labels=['mfresh_lo','mfresh_mid','mfresh_hi']).astype(str)
MR=[]
for nm,mask in [('IWM all',D.iwm5==D.iwm5),('mkt jump z>=1.5',D.m_jumpz>=1.5),('mkt no jump',D.m_jumpz<1.5),('mkt fresh top third',D.mf_t=='mfresh_hi'),('mkt fresh bottom third',D.mf_t=='mfresh_lo')]:
    d=D[mask]; MR.append(dict(state=nm,n_dates=len(d),iwm5=d.iwm5.mean(),se=d.iwm5.std()/np.sqrt(len(d)),hit=(d.iwm5>0).mean()))
MR=pd.DataFrame(MR); MR['lo95']=MR.iwm5-1.96*MR.se; MR['hi95']=MR.iwm5+1.96*MR.se; MR.to_csv('2024_v4_mkt_iwm.csv',index=False,float_format='%.5f')
pd.set_option('display.width',200); print(R.round(4).to_string()); print(MR.round(4).to_string())
print('mkt fresh qw lenses',len(f('qw_fresh')),'mkt jump dates',(mk.m_jumpz>=1.5).sum(),'stocks rows',len(A))
