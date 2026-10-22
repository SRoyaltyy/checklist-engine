# Exploratory 2024 STATE test - builds per stock-morning state frame (sector by sector)
import pandas as pd, numpy as np, pyarrow.parquet as pq, glob, re, gc
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
P='/workspace/pricehist/'
# ---- prices 2024 only (no 2025+ touched) ----
px=pq.read_table(P+'universe_2020_survivors.parquet',columns=['ticker','date','open','close'],
   filters=[('date','>=',pd.Timestamp('2024-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px.sort_values(['ticker','date']).reset_index(drop=True)
dv=pd.read_parquet(P+'dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str)
dv=dv[(dv.ex_date>='2024-01-01')&(dv.ex_date<'2025-01-01')].groupby(['ticker','ex_date']).amount.sum().reset_index()
px=px.merge(dv.rename(columns={'ex_date':'date','amount':'div'}),on=['ticker','date'],how='left'); px['div']=px['div'].fillna(0.0)
px['divflag']=px['div']>0.2*px.close; px.loc[px.divflag,'div']=0.2*px.close[px.divflag]
g=px.groupby('ticker',sort=False)
px['cumdiv']=g['div'].cumsum()
o1=g.open.shift(-1); # entry = next session open after the morning
for h in (1,5):
    cx=g.close.shift(-h); cd=g.cumdiv.shift(-h)-g.cumdiv.shift(-1)+g['div'].shift(-1)  # dividends with ex-date in [entry day, exit day]
    px[f'r{h}']=(cx+cd)/o1-1-0.002
    px[f'dflag{h}']=g.divflag.transform(lambda s: s[::-1].rolling(h,min_periods=1).max()[::-1].shift(-1)).astype(float)
px=px[['ticker','date','r1','r5','dflag5']]; px['date']=px.date.dt.strftime('%Y-%m-%d')
for c in ('r1','r5'): px.loc[px[c].abs()>2,c]=np.nan   # junk-price guard
out=[]
secs=sorted({re.sub(r'_part\d+$','',f.split('STK__')[1][:-8]) for f in glob.glob(C+'2024__COUNTS2_STK__*.parquet')})
for s in secs:
    fs=glob.glob(C+f'2024__COUNTS2_STK__{s}*.parquet'); names=pq.ParquetFile(fs[0]).schema.names
    cols=['ticker','date','lean_bull_share','votes_bull_yes','votes_bear_yes']+[c for c in names if c.startswith('ctx_opp|') or (c.startswith('stk|') and c.endswith('|yes'))]
    S=pd.concat([pd.read_parquet(f,columns=cols) for f in fs])
    tf=C+f'2024__COUNTS2_TR__{s}.parquet'; tn=pq.ParquetFile(tf).schema.names
    tc=['ticker','date','lean_bull_share_all']+[c for c in tn if c.startswith('ctx_opp|') or (c.startswith('stk|') and c.endswith('|yes'))]
    T=pd.read_parquet(tf,columns=tc)
    D=S.merge(T,on=['ticker','date'],how='inner')  # TR only has traded days
    def ssum(pred): 
        cs=[c for c in D.columns if pred(c)]; return D[cs].sum(axis=1) if cs else 0
    r=pd.DataFrame({'ticker':D.ticker.astype(str),'date':D.date,'sector':s,'lean':D.lean_bull_share_all})
    r['ast_stk']=ssum(lambda c:c.startswith('ctx_opp|stk|'))
    r['ast_mkt']=ssum(lambda c:c.startswith('ctx_opp|mkt|'))
    r['ast_div']=ssum(lambda c:c.startswith('ctx_opp|stk|') and 'iverg' in c)
    for src in ('grok','james','theme-radar'): r['ast_'+src]=ssum(lambda c,src=src:c.startswith(f'ctx_opp|stk|{src}|'))
    r['qw']=ssum(lambda c:c.startswith('stk|') and '|quiet_warning|' in c)
    r['qw_div']=ssum(lambda c:c.startswith('stk|') and '|quiet_warning|' in c and 'iverg' in c)
    r['lb']=ssum(lambda c:c.startswith('stk|') and '|loud_bearish|' in c)
    r['bull_stk']=ssum(lambda c:c.startswith('stk|') and '|bullish|' in c)
    out.append(r.merge(px,on=['ticker','date'],how='left')); print(s,len(r),flush=True)
    del S,T,D; gc.collect()
A=pd.concat(out); A.to_parquet('states_2024.parquet'); print(A.describe().T)
