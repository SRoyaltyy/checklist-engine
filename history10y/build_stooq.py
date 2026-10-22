import zipfile, io, pandas as pd, numpy as np, re
Z=zipfile.ZipFile('/home/box/Downloads/d_us_txt.zip')
U=set(pd.read_parquet('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker']).ticker.astype(str).unique())
out=[]
for n in Z.namelist():
    if not n.endswith('.us.txt') or 'etf' in n.lower(): continue
    t=n.rsplit('/',1)[1][:-7].upper().replace('-','.')
    if t not in U: continue
    d=pd.read_csv(io.BytesIO(Z.read(n)),usecols=[2,7],names=['date','close'],header=0)
    d=d[d.date<=20241231]  # never read 2025-26
    if len(d)==0: continue
    d['ticker']=t; out.append(d)
S=pd.concat(out); S['date']=pd.to_datetime(S.date.astype(str)); S['close']=S.close.astype('float64')
assert S.date.max()<=pd.Timestamp('2024-12-31')
S.to_parquet('stooq_close_le2024.parquet',index=False)
print(S.ticker.nunique(), len(S), S.date.min(), (S.groupby('ticker').date.min()<'2015-01-01').sum())
