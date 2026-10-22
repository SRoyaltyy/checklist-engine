# BUYABLE_FILTER_V1 - drop stock-days we'd never buy. Uses only bars before D.
import pandas as pd, numpy as np, sys
SRC='/workspace/pricehist/universe_2020_survivors.parquet'
df=pd.read_parquet(SRC,columns=['ticker','date','close','volume'])
df['ticker']=df.ticker.astype(str)
df=df[(df.date>='2019-09-01')&(df.date<='2024-12-31')].sort_values(['ticker','date'])
g=df.groupby('ticker',sort=False)
df['avgvol20']=g.volume.transform(lambda s:s.shift(1).rolling(20,min_periods=20).mean())
df['vol_prev']=g.volume.shift(1)
near=((df.close>=9.5)&(df.close<=10.5)).astype(float)
df['near10']=near.groupby(df.ticker,sort=False).transform(lambda s:s.shift(1).rolling(60,min_periods=60).mean())
df=df[(df.date>='2020-01-01')]
r=pd.DataFrame({'ticker':df.ticker,'date':df.date.dt.strftime('%Y-%m-%d')})
r['r_avgvol']=~(df.avgvol20>=500000)
r['r_zero_vol']=(df.vol_prev<=0)|df.vol_prev.isna()
r['r_spac_suffix']=df.ticker.str.upper().str.contains(r'[-.](U|WS|R)$',regex=True)
r['r_flat10']=(df.near10>=0.9)
r['drop']=r[['r_avgvol','r_zero_vol','r_spac_suffix','r_flat10']].any(axis=1)
r[r['drop']][['ticker','date']].to_csv('drop_list.csv',index=False)
c={k:int(r[k].sum()) for k in ['r_avgvol','r_zero_vol','r_spac_suffix','r_flat10','drop']}
c['total']=len(r);print(c)
dc=r[(r.ticker=='DCGO')&(r.date=='2021-09-27')];print(dc.to_dict('records'))
