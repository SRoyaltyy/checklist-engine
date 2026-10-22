# build multi-horizon returns 2020-24 only; entry open D+1, exit open D+1+H
import pandas as pd, numpy as np, pyarrow.parquet as pq
FEE10,FEE30=0.002,0.006
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],filters=[('date','>=',pd.Timestamp('2020-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True)
g=A.groupby('ticker',sort=False); A['cd']=g['div'].cumsum(); o=g.open; cd=A.groupby('ticker',sort=False).cd
# entry = open of next session (shift -1), exit = open of session H after that (shift -(1+H))
out=A[['ticker','date']].copy()
for H in (5,10,20,60):
    raw=(o.shift(-(1+H))+cd.shift(-(1+H))-cd.shift(-1))/o.shift(-1)-1
    out[f'r{H}']=raw; out.loc[raw.abs()>2,f'r{H}']=np.nan
    out[f'f{H}_10']=out[f'r{H}']-FEE10; out[f'f{H}_30']=out[f'r{H}']-FEE30
    out[f'ex{H}']=out[f'f{H}_10']-out.groupby('date')[f'f{H}_10'].transform('mean')
out=out.dropna(subset=['f5_10'],how='all')
# keep rows with at least one horizon usable
print(out.shape, out.date.min(), out.date.max())
out.to_parquet('multi_h_rets.parquet'); print('saved')
