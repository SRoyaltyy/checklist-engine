import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc
C='/workspace/data/nb_v2/chunks/'; FEE=0.002; LCUT=0.6205
IDS={'NBX':['nb4-PDS-NB-039-W0-EVT','nb4-PDS-NB-039-T20-CNT','nb4-PDS-NB-039-T20-EXT','nb4-BRW-NB-056-W0-EVT','nb4-BRW-NB-056-T20-EXT','nb4-BRW-NB-056-T20-CNT'],
     'NB':['nb4-PDS-NB-015-T1-RNK','nb4-PDS-NB-015-T1-RNK-BUT']}
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry','Exchange'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')]); nasd=set(snap.Ticker[snap.Exchange=='NASD'])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','close','volume'],filters=[('date','>=',pd.Timestamp('2019-12-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True)
g=A.groupby('ticker',sort=False); A['cd']=g['div'].cumsum(); o=g.open; cd=A.groupby('ticker',sort=False).cd; c=g.close
A['f_next']=(o.shift(-6)+cd.shift(-6)-cd.shift(-1))/o.shift(-1)-1-FEE   # used in v2 score: entry open D+1, exit open D+6
A['f_same']=(o.shift(-5)+cd.shift(-5)-A.cd)/A.open-1-FEE                   # variant: entry open D, exit open D+5
for k in ['f_next','f_same']: A.loc[A[k].abs()>2,k]=np.nan
# matching features known before entry at open D+1: through close D
A['r1']=A.close/c.shift(1)-1; A['r5']=A.close/c.shift(5)-1
A['dvol']=(A.close*A.volume); A['dvol20']=A.groupby('ticker',sort=False).dvol.transform(lambda x:x.rolling(20,min_periods=10).mean())
# features known before entry at open D (through close D-1)
A['r1p']=c.shift(1)/c.shift(2)-1; A['r5p']=c.shift(1)/c.shift(6)-1; A['dvol20p']=A.groupby('ticker',sort=False).dvol20.shift(1)
A=A[A.date>='2020-01-01']; A=A[['ticker','date','f_next','f_same','r1','r5','dvol20','r1p','r5p','dvol20p']]
codes=[]
for y in range(2020,2025):
    st=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']); st['ticker']=st.ticker.astype(str); st['date']=st.date.astype(str).str[:10]
    parts=[]
    for kind,want in IDS.items():
        P=[]
        for f in sorted(glob.glob(C+f'{y}__{kind}__*.parquet')):
            fid=json.load(open(f[:-8]+'.json'))['ids']; ix=[fid.index(w) for w in want]
            D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
            cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
            P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=want)],axis=1))
        parts.append(pd.concat(P))
    X=parts[0].merge(parts[1],on=['ticker','date']).merge(st.drop_duplicates(['ticker','date']),on=['ticker','date'],how='left')
    codes.append(X); print(y,len(X),flush=True)
X=pd.concat(codes); M=X.merge(A,on=['ticker','date'],how='inner'); del A,X; gc.collect()
M['L5']=M.lean>=LCUT; M['nasd']=M.ticker.isin(nasd); M['year']=M.date.str[:4]
def bucket(col,q):
    return M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q else np.nan)
for col,q in [('r1',20),('r5',20),('dvol20',3),('r1p',20),('r5p',20),('dvol20p',3)]: M['b_'+col]=bucket(col,q)
def cl(r,d):
    n=len(r)
    if n<2: return [np.nan]*3
    m=r.mean(); e=pd.Series(r-m).groupby(d).sum(); se=np.sqrt((e**2).sum())/n; return m,m-1.96*se,m+1.96*se
out=[]
for idc in IDS['NBX']+IDS['NB']:
    for ret,(b1,b5,bt) in [('f_next',('b_r1','b_r5','b_dvol20')),('f_same',('b_r1p','b_r5p','b_dvol20p'))]:
        for ver,bk in [('raw same-date',None),('match r1x20 + dvol3',[b1,bt]),('match r5x20 + dvol3',[b5,bt])]:
            for scope in ['all','L5']:
                d=M[(M[idc]>0)&M[ret].notna()]
                if '056' in idc: d=d[d.nasd]
                if bk: d=d.dropna(subset=bk)
                keys=['date']+(bk or [])
                ctrl=d[d[idc]==1].groupby(keys)[ret].agg(['mean','size']).rename(columns={'mean':'cm','size':'cn'}).reset_index()
                y_=d[d[idc]==2].merge(ctrl,on=keys,how='inner')
                if scope=='L5': y_=y_[y_.L5]
                res=(y_[ret]-y_.cm).values; m,lo,hi=cl(res,y_.date.values)
                yr=pd.Series(res).groupby(y_.year.values).mean()
                out.append(dict(id=idc,entry='open D+1 (as scored)' if ret=='f_next' else 'open D (variant)',control=ver,scope=scope,resid=m,lo95=lo,hi95=hi,n_dates=y_.date.nunique(),n_obs=len(y_),
                    signs=''.join(('+' if yr.get(str(Y),0)>0 else '-') if str(Y) in yr.index else '.' for Y in range(2020,2025)),
                    nasdaq_only=('056' in idc)))
R=pd.DataFrame(out); R.to_csv('../2020_24_nb_v2_matched.csv',index=False,float_format='%.5f')
pd.set_option('display.width',250); print(R.round(5).to_string())
