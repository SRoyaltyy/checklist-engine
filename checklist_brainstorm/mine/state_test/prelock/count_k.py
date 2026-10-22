import pandas as pd,numpy as np,pyarrow.parquet as pq,json,glob,ast
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
def load(kind,ids):
    X=[]
    for y in range(2020,2025):
        for f in sorted(glob.glob(C+f'{y}__{kind}__*.parquet')):
            j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids']); ix=[fid.index(w) for w in ids]
            D=pd.read_parquet(f,columns=['ticker','date','packed']); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
            cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
            X.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=ids)],axis=1))
    return pd.concat(X)
A=load('F4TR',['OWN-TR-00051-C']); E=load('EARN',['nbx-EARN-TODAY-BMOUNK','nbx-EARN-POST1']).sort_values(['ticker','date'])
g=E.groupby('ticker')
E['old']=g.apply(lambda d:((d['nbx-EARN-TODAY-BMOUNK']==2)|(d['nbx-EARN-POST1']==2)).astype(int).rolling(30,min_periods=1).max()).reset_index(level=0,drop=True)
E['new']=g['nbx-EARN-POST1'].transform(lambda x:(x==2).astype(int).rolling(29,min_periods=1).max())
E['today']=E['nbx-EARN-TODAY-BMOUNK']==2
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','close'],filters=[('date','>=',pd.Timestamp('2020-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas(); px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d')
M=A.merge(E,on=['ticker','date'],how='left').merge(px,on=['ticker','date'])
M=M[M['OWN-TR-00051-C']>0].sort_values(['ticker','date']); y=M['OWN-TR-00051-C']==2
M=M[y&~y.groupby(M.ticker).shift(1,fill_value=False)]
o=M.old==1;n=M.new==1;p5=M.close>=5
print('event starts (price-merged, pre-bin)',len(M))
print('k old flag',o.sum(),' new flag',n.sum(),' old&!new',(o&~n).sum(),' of which signal-day TODAY',(o&~n&M.today).sum(),' new&!old',(n&~o).sum())
print('locked rule close>=5: old',(o&p5).sum(),' new',(n&p5).sum())
