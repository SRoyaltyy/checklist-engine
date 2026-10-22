import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc
C='/workspace/data/nb_v2/chunks/'; FEE=0.002; LCUT=0.6205
W=['nb4-PDS-NB-015-T1-RNK','nb4-PDS-NB-015-T1-RNK-BUT','nb4-PDS-NB-015-T1-THR-BUT']
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True)
g=A.groupby('ticker',sort=False); A['cd']=g['div'].cumsum(); o=g.open; cd=A.groupby('ticker',sort=False).cd; pc=g.close.shift(1)
A['f']=(o.shift(-6)+cd.shift(-6)-cd.shift(-1))/o.shift(-1)-1-FEE; A.loc[A.f.abs()>2,'f']=np.nan   # entry open D+1, exit open D+6 (as scored)
tr=np.maximum(A.high,pc.fillna(A.high))-np.minimum(A.low,pc.fillna(A.low))
A['atrp']=tr.groupby(A.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/A.close   # through close D
A['r1']=A.close/pc-1; A['px']=A.close
A=A[A.date>='2020-01-01'][['ticker','date','f','atrp','px','r1']]; gc.collect()
X=[]
for y in range(2020,2025):
    st=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']); st['ticker']=st.ticker.astype(str); st['date']=st.date.astype(str).str[:10]
    P=[]
    for f in sorted(glob.glob(C+f'{y}__NB__*.parquet')):
        fid=json.load(open(f[:-8]+'.json'))['ids']; ix=[fid.index(w) for w in W]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=W)],axis=1)); del D
    X.append(pd.concat(P).merge(st.drop_duplicates(['ticker','date']),on=['ticker','date'],how='left')); print(y,flush=True)
M=pd.concat(X).merge(A,on=['ticker','date']); del A,X; gc.collect()
M['L5']=M.lean>=LCUT; M['year']=M.date.str[:4]
def bk(col,q): return M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
M['b_atr']=bk('atrp',5); M['b_px']=bk('px',5); M['b_r1']=bk('r1',10)
def cl(r,d):
    m=r.mean(); e=pd.Series(r-m).groupby(d).sum(); se=np.sqrt((e**2).sum())/len(r); return m,m-1.96*se,m+1.96*se
out=[]
for idc in W:
    for ver,keys in [('raw same-date',[]),('ATR%x5 * price x5',['b_atr','b_px']),('ATR%x5 * price x5 * r1 x10',['b_atr','b_px','b_r1'])]:
        d=M[(M[idc]>0)&M.f.notna()].dropna(subset=keys+['b_atr','b_px','b_r1'])  # same sample in all versions
        k=['date']+keys; ctrl=d[d[idc]==1].groupby(k).f.mean().rename('cm').reset_index()
        Y=d[d[idc]==2].merge(ctrl,on=k)
        for scope in ['all','L5']:
            y_=Y if scope=='all' else Y[Y.L5]; r=(y_.f-y_.cm).values; m,lo,hi=cl(r,y_.date.values); yr=pd.Series(r).groupby(y_.year.values).mean()
            out.append(dict(id=idc,control=ver,scope=scope,resid=m,lo95=lo,hi95=hi,n_dates=y_.date.nunique(),n_obs=len(y_),
               signs=''.join(('+' if yr[str(Y_)]>0 else '-') if str(Y_) in yr.index else '.' for Y_ in range(2020,2025)),**{f'y{Y_}':yr.get(str(Y_),np.nan) for Y_ in range(2020,2025)}))
    # composition: where YES sits
    yy=M[M[idc]==2]; print(idc,'YES share by price quintile',yy.b_px.value_counts(normalize=True).sort_index().round(3).to_dict(),'ATR quintile',yy.b_atr.value_counts(normalize=True).sort_index().round(3).to_dict())
R=pd.DataFrame(out); R.to_csv('../2020_24_nb015_volprice.csv',index=False,float_format='%.5f'); pd.set_option('display.width',250); print(R.round(5).to_string())
