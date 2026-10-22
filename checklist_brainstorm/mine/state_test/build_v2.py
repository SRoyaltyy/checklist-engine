# v2: fund exclusion + fresh warnings + warning jump (New Bot locked defs). EXPLORATORY 2024, survivors only.
import pandas as pd, numpy as np, pyarrow.parquet as pq, glob, re, gc
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; P='/workspace/pricehist/'
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry','Sector'])
FUNDIND=snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')
funds=set(snap.Ticker[FUNDIND]); known=set(snap.Ticker)
px=pq.read_table(P+'universe_2020_survivors.parquet',columns=['ticker','date','open'],
   filters=[('date','>=',pd.Timestamp('2024-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet(P+'dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str)
dv=dv[(dv.ex_date>='2024-01-01')&(dv.ex_date<'2025-01-01')]; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
px=px.merge(dv,on=['ticker','date'],how='left'); px['div']=np.minimum(px['div'].fillna(0),0.2*px.open)
out=[]; log=[]
secs=sorted({re.sub(r'_part\d+$','',f.split('STK__')[1][:-8]) for f in glob.glob(C+'2024__COUNTS2_STK__*.parquet')})
for s in secs:
    fs=glob.glob(C+f'2024__COUNTS2_STK__{s}*.parquet'); n=pq.ParquetFile(fs[0]).schema.names
    sc=[c for c in n if c.startswith('stk|') and '|quiet_warning|' in c and c.endswith(('|yes','|ready'))]
    S=pd.concat([pd.read_parquet(f,columns=['ticker','date']+sc+[c for c in n if c.startswith('ctx_opp|stk|')]) for f in fs])
    tf=C+f'2024__COUNTS2_TR__{s}.parquet'; tn=pq.ParquetFile(tf).schema.names
    tc=[c for c in tn if c.startswith('stk|') and '|quiet_warning|' in c and c.endswith(('|yes','|ready'))]
    T=pd.read_parquet(tf,columns=['ticker','date','lean_bull_share_all']+tc+[c for c in tn if c.startswith('ctx_opp|stk|')])
    D=S.merge(T,on=['ticker','date']); del S,T
    D['ticker']=D.ticker.astype(str); n0=D.ticker.nunique()
    isf=D.ticker.isin(funds); tk=pd.Series(D.ticker.unique())
    log.append(dict(sector=s,tickers=n0,fund_tickers_removed=D.ticker[isf].nunique(),rows_removed=int(isf.sum()),not_in_snapshot=int((~tk.isin(known)).sum())))
    D=D[~isf].sort_values(['ticker','date']).reset_index(drop=True)
    yc=[c for c in D.columns if c.endswith('|yes') and '|quiet_warning|' in c]; rc=[c[:-4]+'|ready' for c in yc]
    g=D.groupby('ticker',sort=False)
    inc=(D[yc]-g[yc].shift(1)).clip(lower=0)
    r=pd.DataFrame({'ticker':D.ticker,'date':D.date,'sector':s,'lean':D.lean_bull_share_all,
       'ast':D[[c for c in D.columns if c.startswith('ctx_opp|stk|')]].sum(axis=1),
       'fresh':inc.sum(axis=1,min_count=1),'fresh_div':inc[[c for c in yc if 'iverg' in c]].sum(axis=1,min_count=1)})
    r.loc[(g.cumcount()==0).values,['fresh','fresh_div']]=np.nan
    fr=D[yc].sum(axis=1)/D[rc].sum(axis=1).replace(0,np.nan); r['qwfrac']=fr
    gg=fr.groupby(D.ticker,sort=False); m=gg.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean()); sd=gg.transform(lambda x:x.shift(1).rolling(20,min_periods=10).std())
    r['jumpz']=(fr-m)/sd.replace(0,np.nan)
    out.append(r); print(s,len(r),flush=True); del D,inc; gc.collect()
A=pd.concat(out); L=pd.DataFrame(log); L.to_csv('v2_fund_exclusion.csv',index=False)
A=A.merge(px,on=['ticker','date'],how='left').sort_values(['ticker','date']).reset_index(drop=True)
A.to_parquet('states_2024_v2.parquet'); print(L); print(L.sum(numeric_only=True)); print(A[['fresh','fresh_div','qwfrac','jumpz','ast']].describe().T)
