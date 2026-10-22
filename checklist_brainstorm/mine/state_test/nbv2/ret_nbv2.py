# returns frame, logic copied from analyze_v5.py (fix5/ex5). dates < 2025-01-01 only.
import pandas as pd, numpy as np, pyarrow.parquet as pq
FEE=0.002
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],filters=[('date','>=',pd.Timestamp('2020-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True)
g=A.groupby('ticker',sort=False); A['cumdiv']=g['div'].cumsum(); o=g.open; cd=A.groupby('ticker',sort=False).cumdiv
A['fix5']=(o.shift(-6)+cd.shift(-6)-cd.shift(-1))/o.shift(-1)-1-FEE; A.loc[A.fix5.abs()>2,'fix5']=np.nan
A['ex5']=A.fix5-A.groupby('date').fix5.transform('mean')
A=A.dropna(subset=['ex5'])[['ticker','date','ex5']]; A['ex5']=A.ex5.astype('float32')
print(len(A),A.date.min(),A.date.max()); A.to_parquet('ret_2020_24.parquet')
