import pandas as pd, numpy as np
from collections import deque
S=pd.read_parquet('stooq_close_le2024.parquet').sort_values(['ticker','date']).drop_duplicates(['ticker','date'])
assert S.date.max()<=pd.Timestamp('2024-12-31')
W=2520; out=[]
for t,g in S.groupby('ticker',sort=False):
    c=g.close.values; d=g.date.values; n=len(c)
    keep=d>=np.datetime64('2019-12-01')
    if not keep.any(): continue
    cs=np.r_[0,np.cumsum(c)]; i=np.arange(n)
    m10=(cs[i+1]-cs[np.maximum(i+1-W,0)])/np.minimum(i+1,W); m5=(cs[i+1]-cs[np.maximum(i+1-1260,0)])/np.minimum(i+1,1260)
    mx=np.empty(n); amx=np.empty(n,int); mn=np.empty(n); qx=deque(); qn=deque()
    for k in range(n):
        while qx and c[qx[-1]]<=c[k]: qx.pop()
        qx.append(k)
        while qn and c[qn[-1]]>=c[k]: qn.pop()
        qn.append(k)
        if qx[0]<=k-W: qx.popleft()
        if qn[0]<=k-W: qn.popleft()
        mx[k]=c[qx[0]]; amx[k]=qx[0]; mn[k]=c[qn[0]]
    out.append(pd.DataFrame(dict(ticker=t,sdate=d[keep],c=c[keep],mx=mx[keep],mn=mn[keep],ysh=(i-amx)[keep]/252,m5=m5[keep],m10=m10[keep],nh=(i+1)[keep],age=((d-d[0])/np.timedelta64(1,'D')/365.25)[keep])))
F=pd.concat(out,ignore_index=True)
L=lambda cond,y,nn,short: np.where(short,'SHORT',np.where(cond,y,nn))
sh=F.nh<W
F['H10_NEAR_HIGH']=L(F.c>=0.95*F.mx,'YES','NO',sh)
F['H10_NEAR_LOW']=L(F.c<=1.10*F.mn,'YES','NO',sh)
dd=1-F.c/F.mx
F['H10_DD']=np.where(sh,'SHORT',np.select([dd<0.05,dd<0.2,dd<0.5,dd<0.8],['DD0_5','DD5_20','DD20_50','DD50_80'],'DD80P'))
F['H10_YRS_SINCE_HIGH']=np.where(sh,'SHORT',np.select([F.ysh<1,F.ysh<3],['Y_LT1','Y1_3'],'Y3P'))
F['H10_ABOVE_5YAVG']=L(F.c>F.m5,'YES','NO',F.nh<1260)
F['H10_ABOVE_10YAVG']=L(F.c>F.m10,'YES','NO',sh)
F['H10_AGE']=np.select([F.age<5,F.age<10],['AGE_LT5','AGE5_10'],'AGE10P')
F.drop(columns=['c','mx','mn','ysh','m5','m10','nh','age']).to_parquet('h10_feats.parquet',index=False); print(len(F))
