import pandas as pd, numpy as np, pyarrow.parquet as pq, gc
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close','volume'],filters=[('date','>=',pd.Timestamp('2018-12-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
assert px.date.max()<pd.Timestamp('2025-01-01')
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A=A.drop_duplicates(['ticker','date']).sort_values(['ticker','date']).reset_index(drop=True)
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open)
for c in ['open','high','low','close','volume']: A[c]=A[c].astype('float64')
g=A.groupby('ticker',sort=False); T=A.ticker
A['cd']=g['div'].cumsum(); cdg=A.groupby('ticker',sort=False).cd
O,H,L,C,V=A.open,A.high,A.low,A.close,A.volume
for h in (5,10,20):
    r=(g.open.shift(-(1+h))+cdg.shift(-(1+h))-cdg.shift(-1))/g.open.shift(-1)-1
    r[r.abs()>2]=np.nan; A[f'r{h}']=r.astype('float32')   # gross; fee applied later
def sh(s,k=1): return s.groupby(T,sort=False).shift(k)
def roll(s,n,f,mp=None): return s.groupby(T,sort=False).transform(lambda x:getattr(x.rolling(n,min_periods=mp or n),f)())
def ewm(s,a): return s.groupby(T,sort=False).transform(lambda x:x.ewm(alpha=a,adjust=False,min_periods=int(1/a)).mean())
pc=sh(C); A['pc']=pc
tr=np.maximum(H,pc.fillna(H))-np.minimum(L,pc.fillna(L))
A['atrp']=roll(tr,20,'mean',15)/C; A['atr14']=roll(tr,14,'mean')
A['r1']=C/pc-1
d=C.diff().where(T.eq(T.shift()))
def rsi(n):
    up=ewm(d.clip(lower=0),1/n); dn=ewm((-d).clip(lower=0),1/n); return 100-100/(1+up/dn.replace(0,np.nan))
A['rsi14']=rsi(14); A['rsi2']=rsi(2)
hh=roll(H,14,'max'); ll=roll(L,14,'min'); k=100*(C-ll)/(hh-ll).replace(0,np.nan)
A['wr']=k; A['stoch']=roll(k,3,'mean')
m20=roll(C,20,'mean'); s20=roll(C,20,'std'); A['bbp']=(C-(m20-2*s20))/(4*s20).replace(0,np.nan); A['ext20']=C/m20-1
tp=(H+L+C)/3; mt=roll(tp,20,'mean'); md=roll((tp-mt).abs(),20,'mean'); A['cci']=(tp-mt)/(0.015*md).replace(0,np.nan)
mf=tp*V; pos=mf.where(tp>sh(tp),0); neg=mf.where(tp<sh(tp),0); A['mfi']=100*roll(pos,14,'sum')/(roll(pos,14,'sum')+roll(neg,14,'sum')).replace(0,np.nan)
hi252=roll(H,252,'max',200); lo252=roll(L,252,'min',200)
A['d52h']=C/hi252-1; A['d52l']=C/lo252-1
A['new52h']=(H>=sh(roll(H,252,'max',200))).astype(float).where(sh(hi252).notna()); A['new52l']=(L<=sh(roll(L,252,'min',200))).astype(float).where(sh(lo252).notna())
v50=roll(V,50,'mean',40); A['rvol']=V/sh(v50)
A['gap']=O/pc-1; A['gapfill_up']=((A.gap>=0.03)&(L<=pc)).astype(float).where(A.gap.notna())
rng=(H-L).replace(0,np.nan); A['lwick']=(np.minimum(O,C)-L)/rng; A['body']=(C-O)/O
A['giantred']=((C<O)&((C-O)/O<=-0.05)&((H-L)>=2*A.atr14)&(A.lwick<0.1)).astype(float).where(A.atr14.notna())
lr=np.log(C/pc); A['rv']=roll(lr,10,'std')/roll(lr,60,'std')
mfm=((C-L)-(H-C))/rng; A['cmf']=roll((mfm*V).fillna(0),20,'sum')/roll(V,20,'sum').replace(0,np.nan)
upv=V.where(C>pc,0); A['upvs']=roll(upv,20,'sum')/roll(V,20,'sum').replace(0,np.nan)
grn=(C>O).astype(float); A['g10']=roll(grn,10,'sum')
e12=ewm(C,2/13); e26=ewm(C,2/27); mac=e12-e26; sig=mac.groupby(T,sort=False).transform(lambda x:x.ewm(alpha=0.2,adjust=False).mean()); A['mh']=mac-sig; A['mh1']=sh(A.mh)
e9=ewm(C,0.2); e21=ewm(C,2/22); A['ec']=e9/e21-1; A['ec1']=sh(A.ec)
A['sma20']=m20
# fading: smaller green body & lower vol vs prior day, prior day green
bd=C-O; G=(C>O); fade1=G&sh(G).fillna(False).astype(bool)&(bd<sh(bd))&(V<sh(V))
A['fade1']=fade1.astype(float); A['fade2']=(fade1&sh(fade1).fillna(False).astype(bool)).astype(float)
A['fade3']=(A.fade2.astype(bool)&sh(fade1,2).fillna(False).astype(bool)).astype(float)
R=~G&(C<O); rfade=R&sh(R).fillna(False).astype(bool)&(bd>sh(bd))&(V<sh(V)); A['rfade1']=rfade.astype(float)
A['rfade2']=(rfade&sh(rfade).fillna(False).astype(bool)).astype(float)
A['up5']=C/sh(C,5)-1
A=A[A.date>='2020-01-01'].copy(); A['year']=A.date.str[:4]
def bk(col,q): return A.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
A['b_atr']=bk('atrp',5); A['b_px']=bk('close',5); A['b_r1']=bk('r1',10)
drop=['open','high','low','div','cd','atr14','pc']
A.drop(columns=drop).to_parquet('feat.parquet'); print(A.shape, A.date.min(), A.date.max())
