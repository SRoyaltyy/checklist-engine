import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast, hashlib
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; W='OWN-TR-00051-C'
assert hashlib.sha256(open('/workspace/checklist_brainstorm/engine/out/tags/new-bot_earn_tags.csv','rb').read()).hexdigest().startswith('08f15079')
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
def load(kind,ids):
    X=[]
    for y in range(2020,2025):
        for f in sorted(glob.glob(C+f'{y}__{kind}__*.parquet')):
            j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids']); ix=[fid.index(w) for w in ids]
            D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
            cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
            X.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=ids)],axis=1))
    return pd.concat(X)
A=load('F4TR',[W]); E=load('EARN',['nbx-EARN-LAST5','nbx-EARN-POST1'])
M=A.merge(E,on=['ticker','date'],how='left')
F=pd.read_parquet('f4tr_frame_tmp.parquet') if False else None
R=pd.read_parquet('../multi_h_rets.parquet',columns=['ticker','date','f5_30','f20_30','f60_30'])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','high','low','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d'); px=px.sort_values(['ticker','date']); g=px.groupby('ticker',sort=False); pc=g.close.shift(1)
tr=np.maximum(px.high,pc.fillna(px.high))-np.minimum(px.low,pc.fillna(px.low))
px['atrp']=tr.groupby(px.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/px.close; px['r1']=px.close/pc-1
px=px[px.date>='2020-01-01'][['ticker','date','atrp','close','r1']]
M=M.merge(px,on=['ticker','date']).merge(R,on=['ticker','date']); del px,R,A,E; gc.collect()
for col,q,nm in [('atrp',5,'ba'),('close',5,'bp'),('r1',10,'br')]:
    M[nm]=M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
M=M[M[W]>0].dropna(subset=['ba','bp','br']).sort_values(['ticker','date']).reset_index(drop=True)
y=M[W]==2; M['start']=y&~y.groupby(M.ticker).shift(1,fill_value=False)
M['earn']=(M['nbx-EARN-LAST5']==2)|(M['nbx-EARN-POST1']==2); M['year']=M.date.str[:4]
K=['date','ba','bp','br']
def res(sel,col):
    c=M[M[W]==1].groupby(K)[col].mean().rename('cm').reset_index()
    Y=M[sel&M[col].notna()].merge(c,on=K)
    if len(Y)<5: return dict(n=len(Y))
    r=Y[col]-Y.cm; m=r.mean(); e=(r-m).groupby(Y.date).sum(); se=np.sqrt((e**2).sum())/len(r)
    s=r.groupby(Y.year).mean(); return dict(n=len(Y),tickers=Y.ticker.nunique(),dates=Y.date.nunique(),resid=m,lo=m-1.96*se,hi=m+1.96*se,win=(r>0).mean(),signs=''.join('+' if s.get(str(k),0)>0 else ('-' if str(k) in s.index else '.') for k in range(2020,2025)))
ev=M[M.start]; first=ev.groupby('ticker').head(1).index
top10=ev.ticker.value_counts().head(10)
print('YES days',int(y.sum()),'events',len(ev),'distinct tickers',ev.ticker.nunique()); print('top10',top10.to_dict())
out=[]
sets={'all YES days':y,'event starts':M.start,'first event per ticker':M.index.isin(first),'events excl top-10 tickers':M.start&~M.ticker.isin(top10.index),
      'events with LAST5|POST1':M.start&M.earn,'events neither':M.start&~M.earn}
for nm,s in sets.items():
    for H in (5,20,60): out.append(dict(set=nm,H=H,fee='30bp',**res(pd.Series(s,index=M.index),f'f{H}_30')))
O=pd.DataFrame(out); O.to_csv('../2020_24_f4tr_00051_checks.csv',index=False,float_format='%.5f'); pd.set_option('display.width',220); print(O.round(4).to_string())
