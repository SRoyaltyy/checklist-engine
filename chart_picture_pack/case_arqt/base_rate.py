# 2020-24 ONLY. Stock-days that look like ARQT on 2026-10-07 (and 10-09 breakout day).
import pandas as pd, numpy as np
FEE=0.006
c=['ticker','date','close','r20','rsi14','mfi','ext20','up5','rvol','d52h','g10','b_atr','b_px','b_r1']
A=pd.read_parquet('/workspace/checklist_brainstorm/mine/state_test/ohlcv/feat.parquet',columns=c)
assert A.date.max()<'2025-01-01'
A=A[(A.close>=2)&A.b_atr.notna()&A.r20.notna()].reset_index(drop=True)
cell=A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values; nc=cell.max()+1
r=A.r20.values; base=np.bincount(cell,r,nc)/np.bincount(cell,minlength=nc)
P={'ARQT_Oct6-7_pullback':(A.rsi14.between(37,46))&(A.mfi<32)&(A.ext20.between(-.08,-.03))&(A.up5.between(-.13,-.05))&(A.rvol.between(.5,1.3))&(A.d52h.between(-.30,-.05)),
   'ARQT_Oct9_breakout':(A.rsi14.between(52,60))&(A.mfi.between(30,45))&(A.ext20.between(0,.07))&(A.up5.between(.03,.09))&(A.rvol.between(.5,1.1))&(A.d52h.between(-.25,-.03)),
   'ALL_stock_days':pd.Series(True,index=A.index)}
out=[]
for k,m in P.items():
    m=m.fillna(False).values; x=r[m]; e=x-base[cell[m]]
    out.append(dict(profile=k,n=int(m.sum()),n_days=A.date[m].nunique(),n_tickers=A.ticker[m].nunique(),
      share_rally_ge20=(x>=.2).mean(),share_up_ge10=(x>=.1).mean(),share_fell=(x<0).mean(),share_fell_le_m10=(x<=-.1).mean(),
      win_after_fee=(x-FEE>0).mean(),mean_after_fee=x.mean()-FEE,median_after_fee=np.median(x)-FEE,
      mean_vs_control=e.mean(),median_vs_control=np.median(e),
      **{f'mean_vs_ctrl_{y}':e[A.date.values[m].astype(str).astype('U4')==str(y)].mean() for y in range(2020,2025)}))
T=pd.DataFrame(out); T.to_csv('base_rate_2020_24.csv',index=False,float_format='%.4f'); print(T.T.to_string())
