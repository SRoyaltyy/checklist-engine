# 2020-24 ONLY. Volume filter on long setups.
import pandas as pd, numpy as np, pyarrow.parquet as pq
from scipy.stats import norm
FEE=0.006; YR=['2020','2021','2022','2023','2024']
c=['ticker','date','close','r1','r5','r20','rsi14','rsi2','mfi','ext20','up5','rvol','year','b_atr','b_px','b_r1']
A=pd.read_parquet('/workspace/checklist_brainstorm/mine/state_test/ohlcv/feat.parquet',columns=c); assert A.date.max()<'2025-01-01'
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],filters=[('date','>=',pd.Timestamp('2019-12-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d'); px=px.drop_duplicates(['ticker','date'])
A=A.merge(px,on=['ticker','date'],how='inner').sort_values(['ticker','date']).reset_index(drop=True); del px
T=A.ticker; C=A.close; same=T.eq(T.shift()).values
g=(C>A.open).astype(np.int8).values
run=np.cumsum((g!=np.roll(g,1))|~same); pos=pd.Series(1,index=A.index).groupby(run).cumsum().values; A['gs']=np.where(g==1,pos,0)
gr=pd.Series(g,index=A.index).groupby(T).rolling(5).mean().reset_index(level=0,drop=True)
up=A.r1.clip(lower=0).groupby(T).rolling(5).sum().reset_index(level=0,drop=True); dn=(-A.r1).clip(lower=0).groupby(T).rolling(5).sum().reset_index(level=0,drop=True)
mx=A.r1.groupby(T).rolling(5).min().reset_index(level=0,drop=True)
cmin=C.groupby(T).rolling(5).min().reset_index(level=0,drop=True); cmax=C.groupby(T).rolling(5).max().reset_index(level=0,drop=True)
r5b=A.up5
green=(gr>=.7)&(up>=2*dn.clip(lower=1e-9))&(r5b>0); push=(r5b>.005)&(-mx<=r5b/3)&(-(cmin/cmax-1)<=r5b/3)
nob=(A.rsi14<=70)&(A.mfi<=80)&(A.ext20<=.1)
fr=A.gs.between(2,5)
A['FRESH_FULL_N5']=(green&push&nob&fr).values
A['FRESH_green+fresh']=(green&fr).values
A['OS_RSI14<30']=A.rsi14<30; A['OS_RSI2<5']=A.rsi2<5; A['OS_MFI<20']=A.mfi<20; A['OS_EXT20<-10%']=A.ext20<-.10
A['ALL']=True
A=A[(A.close>=2)&A.b_atr.notna()&A.b_px.notna()&A.b_r1.notna()].reset_index(drop=True)
cell=A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values; nc=cell.max()+1; dt=A.date.values; yr=A.year.values
rv=A.rvol
F={'none':pd.Series(True,index=A.index),'RVOL>=1':rv>=1,'RVOL>=1.5':rv>=1.5,'RVOL>=2':rv>=2,'RVOL<1(quiet)':rv<1}
rows={}
for b in ['FRESH_FULL_N5','FRESH_green+fresh','OS_RSI14<30','OS_RSI2<5','OS_MFI<20','OS_EXT20<-10%','ALL']:
    for f,m in F.items(): rows[(b,f,'long')]=A[b].astype(bool)&m.fillna(False)
rows[('AVOID','RVOL<1&r1<0','short')]=(rv<1)&(A.r1<0)
rows[('AVOID','RVOL<1&up5<0','short')]=(rv<1)&(A.up5<0)
rows[('AVOID','RVOL<1&up5<-5%','short')]=(rv<1)&(A.up5<-.05)
out=[]
for (b,f,side),s in rows.items():
  y=s.fillna(False).values; sg=1 if side=='long' else -1
  for h in (5,20):
    r=A[f'r{h}'].values; ok=~np.isnan(r); no=ok&~y
    sm=np.bincount(cell[no],r[no],nc); n=np.bincount(cell[no],minlength=nc)
    i=np.where(y&ok&(n[cell]>0))[0]
    if b=='ALL' and f=='none':  # control is itself; use cell mean incl all
        e=r[i]-np.bincount(cell[ok],r[ok],nc)[cell[i]]/np.bincount(cell[ok],minlength=nc)[cell[i]]
    else: e=r[i]-sm[cell[i]]/n[cell[i]]
    m=e.mean(); gs=pd.Series(e).groupby(dt[i]).agg(['sum','count'])
    dd=pd.Series(e-m).groupby(dt[i]).sum(); se=np.sqrt((dd**2).sum())/len(e)
    rng=np.random.default_rng(0); k=len(gs); S,Cn=gs['sum'].values,gs['count'].values
    bs=[(lambda j:S[j].sum()/Cn[j].sum())(rng.integers(0,k,k)) for _ in range(300)]
    raw=sg*r[i]-FEE; ys=pd.Series(sg*e).groupby(yr[i]).mean(); yw=pd.Series(raw>0).groupby(yr[i]).mean()
    out.append(dict(base=b,filter=f,side=side,h=h,n=len(i),n_dates=k,win_after_fee=(raw>0).mean(),mean_after_fee=raw.mean(),
      median_after_fee=np.median(raw),edge_vs_ctrl=sg*m,ci_lo=sg*np.percentile(bs,2.5 if sg>0 else 97.5),ci_hi=sg*np.percentile(bs,97.5 if sg>0 else 2.5),
      p=2*norm.sf(abs(m/se)) if se>0 else 1,yrs_pos=int((ys>0).sum()),**{f'w{Y}':yw.get(Y) for Y in YR}))
R=pd.DataFrame(out); o=np.argsort(R.p.values); nn=len(R); th=R.p.values[o]<=.05*np.arange(1,nn+1)/nn
R['bh']=False
if th.any(): R.loc[R.index[o[:np.where(th)[0].max()+1]],'bh']=True
R['pass']=R.bh&(R.ci_lo>0)&(R.win_after_fee>.5)&(R.mean_after_fee>0)&(R.yrs_pos>=4)
R.to_csv('volfilter_2020_24.csv',index=False,float_format='%.4f')
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(R[['base','filter','h','n','win_after_fee','mean_after_fee','median_after_fee','edge_vs_ctrl','ci_lo','yrs_pos','bh','pass']].round(4).to_string())
