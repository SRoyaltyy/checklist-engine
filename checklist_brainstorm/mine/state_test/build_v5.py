# per-year state frame (v2 method). FRESH files used where present, else per-lens count-diff approximation.
import sys, pandas as pd, numpy as np, pyarrow.parquet as pq, glob, re, gc, os
y=int(sys.argv[1]); assert 2020<=y<=2024
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
out=[]; log=[]
secs=sorted({re.sub(r'_part\d+$','',f.split('STK__')[1][:-8]) for f in glob.glob(C+f'{y}__COUNTS2_STK__*.parquet')})
for s in secs:
    fs=glob.glob(C+f'{y}__COUNTS2_STK__{s}*.parquet'); n=pq.ParquetFile(fs[0]).schema.names
    sc=[c for c in n if c.startswith('stk|') and '|quiet_warning|' in c and c.endswith(('|yes','|ready'))]
    S=pd.concat([pd.read_parquet(f,columns=['ticker','date','lean_bull_share']+sc+[c for c in n if c.startswith('ctx_opp|stk|')]) for f in fs])
    tfs=sorted(glob.glob(C+f'{y}__COUNTS2_TR__{s}.parquet')+glob.glob(C+f'{y}__COUNTS2_TR__{s}_part*.parquet'))
    if tfs:
        tn=pq.ParquetFile(tfs[0]).schema.names
        tc=[c for c in tn if c.startswith('stk|') and '|quiet_warning|' in c and c.endswith(('|yes','|ready'))]
        T=pd.concat([pd.read_parquet(tf,columns=['ticker','date','lean_bull_share_all']+tc+[c for c in tn if c.startswith('ctx_opp|stk|')]) for tf in tfs])
        D=S.merge(T,on=['ticker','date']); D['lean']=D.lean_bull_share_all; trok=True
    else: D=S; D['lean']=D.lean_bull_share; trok=False
    del S; gc.collect()
    D['ticker']=D.ticker.astype(str); isf=D.ticker.isin(funds)
    D=D[~isf].sort_values(['ticker','date']).reset_index(drop=True)
    yc=[c for c in D.columns if c.endswith('|yes') and '|quiet_warning|' in c]; rc=[c[:-4]+'|ready' for c in yc]
    r=pd.DataFrame({'ticker':D.ticker,'date':D.date,'sector':s,'lean':D.lean,'tr_joined':trok,
       'ast':D[[c for c in D.columns if c.startswith('ctx_opp|stk|')]].sum(axis=1)})
    ffs=sorted(glob.glob(C+f'{y}__FRESH__{s}.parquet')+glob.glob(C+f'{y}__FRESH__{s}_part*.parquet'))
    if ffs:
        fn=pq.ParquetFile(ffs[0]).schema.names; fc=[c for c in fn if c.endswith(('|qw_fresh','|qw_yes','|qw_ready'))]
        F=pd.concat([pd.read_parquet(ff,columns=['ticker','date']+fc) for ff in ffs]); F['ticker']=F.ticker.astype(str); F['date']=F.date.astype(str).str[:10]
        F=F.drop_duplicates(['ticker','date'])
        F=r[['ticker','date']].merge(F,on=['ticker','date'],how='left')
        fr=[c for c in fc if c.endswith('qw_fresh')]
        r['fresh']=F[fr].sum(axis=1,min_count=1).values; r['fresh_div']=F[[c for c in fr if 'iverg' in c]].sum(axis=1,min_count=1).values
        frac=(F[[c for c in fc if c.endswith('qw_yes')]].sum(axis=1)/F[[c for c in fc if c.endswith('qw_ready')]].sum(axis=1).replace(0,np.nan)).values
        r['s_yes']=F[[c for c in fc if c.endswith('qw_yes')]].sum(axis=1).values; r['s_rdy']=F[[c for c in fc if c.endswith('qw_ready')]].sum(axis=1).values
        r['fresh_src']='FRESH_file'; del F
    else:
        g=D.groupby('ticker',sort=False); inc=(D[yc]-g[yc].shift(1)).clip(lower=0)
        r['fresh']=inc.sum(axis=1,min_count=1); r['fresh_div']=inc[[c for c in yc if 'iverg' in c]].sum(axis=1,min_count=1)
        r.loc[(g.cumcount()==0).values,['fresh','fresh_div']]=np.nan
        r['s_yes']=D[yc].sum(axis=1).values; r['s_rdy']=D[rc].sum(axis=1).values; frac=(D[yc].sum(axis=1)/D[rc].sum(axis=1).replace(0,np.nan)).values; r['fresh_src']='approx_countdiff'; del inc
    fs_=pd.Series(frac,index=r.index); gg=fs_.groupby(r.ticker.values,sort=False)
    m=gg.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean()); sd=gg.transform(lambda x:x.shift(1).rolling(20,min_periods=10).std())
    r['jumpz']=(fs_-m)/sd.replace(0,np.nan)
    log.append(dict(year=y,sector=s,rows=len(r),fund_rows_removed=int(isf.sum()),tr_joined=trok,fresh_src=r.fresh_src.iloc[0]))
    out.append(r); print(y,s,len(r),r.fresh_src.iloc[0],trok,flush=True); del D; gc.collect()
pd.concat(out).to_parquet(f'states_{y}_v5.parquet'); pd.DataFrame(log).to_csv(f'log_{y}_v5.csv',index=False)
