import pandas as pd, numpy as np
from scipy.stats import norm
FEE=0.006
A=pd.read_parquet('../ohlcv/feat.parquet',columns=['ticker','date','close','r5','r20','b_atr','b_px','b_r1','year'])
assert A.date.max()<'2025-01-01'
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Sector'])
M={'Technology':'XLK','Financial':'XLF','Healthcare':'XLV','Energy':'XLE','Industrials':'XLI','Consumer Cyclical':'XLY','Consumer Defensive':'XLP','Utilities':'XLU','Basic Materials':'XLB','Real Estate':'XLRE','Communication Services':'XLC'}
snap['etf']=snap.Sector.map(M); A=A.merge(snap[['Ticker','etf']].rename(columns={'Ticker':'ticker'}),on='ticker',how='inner').dropna(subset=['etf'])
A=A.sort_values(['ticker','date']); A['s20']=A.close/A.groupby('ticker').close.shift(20)-1
E=pd.read_csv('etf_2019_24.csv',index_col=0)
f=lambda x:x.stack().rename_axis(['date','etf'])
S=pd.DataFrame({'e5':f(E/E.shift(5)-1),'e20':f(E/E.shift(20)-1),'ma50':f(E>E.rolling(50).mean()),'x20':f((E/E.shift(20)-1).sub(E.SPY/E.SPY.shift(20)-1,axis=0))}).reset_index()
S=S[S.etf!='SPY']
for c in ['e5','e20']: S['k'+c]=S.groupby('date')[c].rank(ascending=False)  # 1=best of 11
A=A.merge(S,on=['date','etf'],how='left')
A=A[(A.close>=2)].dropna(subset=['b_atr','b_px','b_r1','e20']).reset_index(drop=True)
cell=A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values; nc=cell.max()+1
dt=A.date.values; yr=A.year.values
rs=A.s20-A.e20
rows={'SEC5d-top2of11':A.ke5<=2,'SEC5d-bottom2of11':A.ke5>=10,'SEC20d-top2of11':A.ke20<=2,'SEC20d-bottom2of11':A.ke20>=10,
 'SEC5d>+3%':A.e5>.03,'SEC5d<-3%':A.e5<-.03,'SEC20d>+5%':A.e20>.05,'SEC20d<-5%':A.e20<-.05,
 'SEC-above50MA':A.ma50==True,'SEC-below50MA':A.ma50==False,'SEC20d-beats-SPY>3%':A.x20>.03,'SEC20d-lags-SPY>3%':A.x20<-.03,
 'CATCHUP-sec>50MA&up20d&stock-lags>5%':(A.ma50==True)&(A.e20>0)&(rs<-.05),'CATCHUP-strict-sec20d>5%&stock-lags>10%':(A.e20>.05)&(rs<-.10),
 'RS-stock-beats-sec20d>10%':rs>.10,'RS-stock-lags-sec20d>10%':rs<-.10,'RS-leader-in-up-sector':(A.ma50==True)&(rs>.10),'RS-laggard-in-down-sector':(A.ma50==False)&(rs<-.10)}
for q in range(1,6):  # time-series-free cross-sector quintile proxy: rank buckets
    pass
YR=['2020','2021','2022','2023','2024']; out=[]
for name,s in rows.items():
    y=s.fillna(False).values.astype(bool)
    for h in (5,20):
        r=A[f'r{h}'].values; ok=~np.isnan(r); no=ok&~y
        sm=np.bincount(cell[no],r[no],nc); n=np.bincount(cell[no],minlength=nc)
        i=np.where(y&ok&(n[cell]>0))[0]; e=r[i]-sm[cell[i]]/n[cell[i]]; raw=r[i]
        m=e.mean(); dd=pd.Series(e-m).groupby(dt[i]).sum(); se=np.sqrt((dd**2).sum())/len(e)
        # date-clustered bootstrap
        g=pd.Series(e).groupby(dt[i]).agg(['sum','count']); rng=np.random.default_rng(0); k=len(g)
        b=[(lambda j:g['sum'].values[j].sum()/g['count'].values[j].sum())(rng.integers(0,k,k)) for _ in range(1000)]
        sg=1 if m>0 else -1; ys=pd.Series(e).groupby(yr[i]).mean(); yw=pd.Series((sg*raw-FEE)>0).groupby(yr[i]).mean()
        out.append(dict(row=name,h=h,n_obs=len(i),n_dates=k,side='long' if sg>0 else 'short',resid=m,boot_lo=np.percentile(b,2.5),boot_hi=np.percentile(b,97.5),
          p=2*norm.sf(abs(m/se)),raw_mean_after_fee=(sg*raw).mean()-FEE,win_after_fee=((sg*raw-FEE)>0).mean(),win_vs_match=(sg*e>0).mean(),
          signs=''.join('+' if ys.get(Y,0)>0 else '-' for Y in YR),**{f'y{Y}':ys.get(Y) for Y in YR},**{f'w{Y}':yw.get(Y) for Y in YR}))
T=pd.DataFrame(out); ps=T.p.values; o_=np.argsort(ps); n=len(ps); th=ps[o_]<=0.05*np.arange(1,n+1)/n; bh=np.zeros(n,bool)
if th.any(): bh[o_[:np.where(th)[0].max()+1]]=True
T['bh']=bh; T['nsame']=[sum((c=='+')==(sd=='long') for c in s) for s,sd in zip(T.signs,T.side)]
T['ci_clear']=np.where(T.side=='long',T.boot_lo>0,T.boot_hi<0)
T['pass']=T.bh&T.ci_clear&(T.win_after_fee>.5)&(T.raw_mean_after_fee>0)&(T.nsame>=4)
T.to_csv('2020_24_sector_score.csv',index=False,float_format='%.5f'); print(len(A),A.ticker.nunique())
pd.set_option('display.width',250); print(T[['row','h','n_obs','side','resid','boot_lo','boot_hi','win_after_fee','raw_mean_after_fee','signs','bh','pass']].to_string())
