import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; FEE=0.002; LCUT=0.6205
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
NBT=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/new-bot_si_tags.csv'); TFT=pd.read_csv('pv_tfc_si_tags.csv',keep_default_na=False)
W=list(NBT.row_id)+list(TFT.row_id)
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True)
g=A.groupby('ticker',sort=False); A['cd']=g['div'].cumsum(); o=g.open; cd=A.groupby('ticker',sort=False).cd; pc=g.close.shift(1)
A['f']=(o.shift(-6)+cd.shift(-6)-cd.shift(-1))/o.shift(-1)-1-FEE; A.loc[A.f.abs()>2,'f']=np.nan
tr=np.maximum(A.high,pc.fillna(A.high))-np.minimum(A.low,pc.fillna(A.low))
A['atrp']=tr.groupby(A.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/A.close; A['r1']=A.close/pc-1; A['px']=A.close
A=A[A.date>='2020-01-01'].dropna(subset=['f'])[['ticker','date','f','atrp','px','r1']]
A['ex']=A.f-A.groupby('date').f.transform('mean')
for col,q,nm in [('atrp',5,'b_atr'),('px',5,'b_px'),('r1',10,'b_r1')]:
    A[nm]=A.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
A=A.drop(columns=['atrp','r1']); gc.collect()
X=[]
for y in range(2020,2025):
    st=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean','jumpz']); st['ticker']=st.ticker.astype(str); st['date']=st.date.astype(str).str[:10]
    P=[]
    for f in sorted(glob.glob(C+f'{y}__SI__*.parquet')):
        j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids']); ix=[fid.index(w) for w in W]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=W)],axis=1)); del D
    X.append(pd.concat(P).merge(st.drop_duplicates(['ticker','date']),on=['ticker','date'],how='left')); print(y,flush=True); gc.collect()
M=pd.concat(X).merge(A,on=['ticker','date']); del A,X; gc.collect()
M=M.sort_values(['ticker','date']).reset_index(drop=True)
M['L5']=M.lean>=LCUT; M['spike']=M.jumpz>=1.5; M['year']=M.date.str[:4]
M.to_parquet('si_frame.parquet')
