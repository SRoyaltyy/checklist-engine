import pandas as pd, numpy as np
from scipy.stats import norm
FEE=0.006  # 30bp/side round trip
A=pd.read_parquet('feat.parquet'); assert A.date.max()<'2025-01-01'
nb=pd.read_parquet('nb.parquet'); A=A.merge(nb,on=['ticker','date'],how='left'); del nb
A=A.dropna(subset=['b_atr','b_px','b_r1']).reset_index(drop=True)
cell=A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values; nc=cell.max()+1
dt=A.date.values; yr=A.year.values; tk=A.ticker.values; cl=A.close.values
def q(c,op,v): s=A[c]; return (op(s,v)).where(s.notna())
import operator as o
rows={
 # overbought/oversold
 'OB-RSI14>70':q('rsi14',o.gt,70),'OS-RSI14<30':q('rsi14',o.lt,30),'OB-RSI2>95':q('rsi2',o.gt,95),'OS-RSI2<5':q('rsi2',o.lt,5),
 'OB-STOCH>80':q('stoch',o.gt,80),'OS-STOCH<20':q('stoch',o.lt,20),'OB-WILLR>-20':q('wr',o.gt,80),'OS-WILLR<-80':q('wr',o.lt,20),
 'OB-BB%B>1':q('bbp',o.gt,1),'OS-BB%B<0':q('bbp',o.lt,0),'OB-CCI>100':q('cci',o.gt,100),'OS-CCI<-100':q('cci',o.lt,-100),
 'OB-MFI>80':q('mfi',o.gt,80),'OS-MFI<20':q('mfi',o.lt,20),'OB-EXT20>+10%':q('ext20',o.gt,.10),'OS-EXT20<-10%':q('ext20',o.lt,-.10),
 'HI-52WH-within2%':q('d52h',o.ge,-.02),'HI-52WH-within5%':q('d52h',o.ge,-.05),'LO-52WH-below-30%':q('d52h',o.le,-.30),'LO-52WL-within5%':q('d52l',o.le,.05),
 'HI-NEW52WH':A.new52h==1,'LO-NEW52WL':A.new52l==1,
 # momentum fading
 'FADE-greensmaller+lowervol-1d':A.fade1==1,'FADE-2d':A.fade2==1,'FADE-3d':A.fade3==1,
 'FADE-1d&RSI14>70':(A.fade1==1)&(A.rsi14>70),'FADE-2d&above-SMA20':(A.fade2==1)&(A.close>A.sma20),'FADE-1d&up5>10%':(A.fade1==1)&(A.up5>.10),
 'RFADE-redsmaller+lowervol-1d':A.rfade1==1,'RFADE-2d':A.rfade2==1,
 # outliers
 'OUT-r1>=+10%':q('r1',o.ge,.10),'OUT-r1<=-10%':q('r1',o.le,-.10),'OUT-RVOL>=3':q('rvol',o.ge,3),'OUT-RVOL>=5':q('rvol',o.ge,5),
 'OUT-RVOL>=3&up':(A.rvol>=3)&(A.r1>0),'OUT-RVOL>=3&down':(A.rvol>=3)&(A.r1<0),'OUT-RV10/60>2':q('rv',o.gt,2),
 'GAP-up>=5%':q('gap',o.ge,.05),'GAP-down<=-5%':q('gap',o.le,-.05),'GAP-up>=3%-filled':A.gapfill_up==1,
 'CDL-giantred-nopushback':A.giantred==1,'CDL-longlowerwick>60%':q('lwick',o.gt,.6),'CDL-green>=8of10':q('g10',o.ge,8),'CDL-green<=2of10':q('g10',o.le,2),
 # trend/volume
 'VOL-CMF20>0.25':q('cmf',o.gt,.25),'VOL-CMF20<-0.25':q('cmf',o.lt,-.25),'VOL-upvolshare>0.7':q('upvs',o.gt,.7),'VOL-upvolshare<0.3':q('upvs',o.lt,.3),
 'MOM-MACDhist-turn-up':(A.mh>0)&(A.mh1<=0),'MOM-MACDhist-turn-down':(A.mh<0)&(A.mh1>=0),'MOM-EMA9x21-up':(A.ec>0)&(A.ec1<=0),'MOM-EMA9x21-down':(A.ec<0)&(A.ec1>=0),
}
for c in [c for c in A.columns if c.startswith('nb4-')]: rows[c]=(A[c]==2).where(A[c].isin([1,2]))
YR=['2020','2021','2022','2023','2024']
def resid(y,ready,h):
    r=A[f'r{h}'].values; ok=ready&~np.isnan(r); no=ok&~y
    s=np.bincount(cell[no],r[no],nc); n=np.bincount(cell[no],minlength=nc)
    ys=y&ok; ys&=n[cell]>0; i=np.where(ys)[0]; return i, r[i]-s[cell[i]]/n[cell[i]], r[i]
def stat(i,e,raw):
    m=e.mean(); dd=pd.Series(e-m).groupby(dt[i]).sum(); se=np.sqrt((dd**2).sum())/len(e); return m,se
out=[]; keep={}
for name,s in rows.items():
    sv=s.values if hasattr(s,'values') else s
    ready=~pd.isna(sv); y=np.where(ready,sv,False).astype(bool)
    if name.startswith(('FADE','RFADE','HI-NEW','LO-NEW','CDL-giant','GAP-up>=3','MOM-','OUT-RVOL>=3&')): ready=np.ones(len(y),bool)&A.rvol.notna().values|y
    for h in (5,10,20):
        i,e,raw=resid(y,ready,h)
        if len(np.unique(dt[i]))<30: out.append(dict(row=name,h=h,n_obs=len(i),status='n<30 dates')); continue
        m,se=stat(i,e,raw); sgn=1 if m>0 else -1
        win=((raw-FEE)>0).mean() if sgn>0 else ((-raw-FEE)>0).mean()
        ys=pd.Series(e).groupby(yr[i]).mean()
        out.append(dict(row=name,h=h,yes_rate=y[ready].mean(),n_obs=len(i),n_dates=len(np.unique(dt[i])),n_tickers=len(np.unique(tk[i])),
          resid=m,lo95=m-1.96*se,hi95=m+1.96*se,p=2*norm.sf(abs(m/se)),side='long' if sgn>0 else 'short',win_after_fee=win,
          win_vs_match=(sgn*e>0).mean(),signs=''.join(('+' if ys.get(Y,0)>0 else '-') if Y in ys.index else '.' for Y in YR),
          status='tested',**{f'y{Y}':ys.get(Y,np.nan) for Y in YR}))
        keep[(name,h)]=(i,e,raw)
R=pd.DataFrame(out); T=R[R.status=='tested'].copy()
ps=T.p.values; o_=np.argsort(ps); n=len(ps); bh=np.zeros(n,bool); th=ps[o_]<=0.05*np.arange(1,n+1)/n
if th.any(): bh[o_[:np.where(th)[0].max()+1]]=True
T['bh']=bh; T['yes_gt50']=T.yes_rate>0.5
T['nsame']=[sum((c=='+')==(sd=='long') for c in s if c!='.') for s,sd in zip(T.signs,T.side)]
T['pass_core']=T.bh&((T.lo95>0)|(T.hi95<0))&(T.win_after_fee>0.5)&(T.nsame>=4)&~T.yes_gt50
# robustness for core passes
for k in T.index[T.pass_core]:
    i,e,raw=keep[(T.at[k,'row'],T.at[k,'h'])]; sg=1 if T.at[k,'side']=='long' else -1
    j=cl[i]>=2; m,se=stat(i[j],e[j],raw[j]); T.at[k,'ge2_resid']=m; T.at[k,'ge2_lo']=m-1.96*se; T.at[k,'ge2_hi']=m+1.96*se
    T.at[k,'ge2_win']=(((sg*raw[j])-FEE)>0).mean()
    pt=pd.Series(e).groupby(tk[i]).mean(); sd=pt.std()/np.sqrt(len(pt)); T.at[k,'tkeq_resid']=pt.mean(); T.at[k,'tkeq_lo']=pt.mean()-1.96*sd; T.at[k,'tkeq_hi']=pt.mean()+1.96*sd
    # first event per ticker
    f=pd.Series(np.arange(len(i))).groupby(tk[i]).first().values; T.at[k,'first_resid']=e[f].mean(); T.at[k,'first_lo']=e[f].mean()-1.96*e[f].std()/np.sqrt(len(f))
    T.at[k,'first_hi']=e[f].mean()+1.96*e[f].std()/np.sqrt(len(f))
    top=pt.reindex(pd.Series(tk[i]).value_counts().index[:10]).index; jj=~np.isin(tk[i],top); m,se=stat(i[jj],e[jj],raw[jj]); T.at[k,'drop10_resid']=m; T.at[k,'drop10_lo']=m-1.96*se; T.at[k,'drop10_hi']=m+1.96*se
def clears(lo,hi,side): return (lo>0) if side=='long' else (hi<0)
if T.pass_core.any():
    P=T[T.pass_core]; T['pass_all']=False
    T.loc[P.index,'pass_all']=[clears(r.ge2_lo,r.ge2_hi,r.side) and r.ge2_win>0.5 and clears(r.tkeq_lo,r.tkeq_hi,r.side) and clears(r.drop10_lo,r.drop10_hi,r.side) and clears(r.first_lo,r.first_hi,r.side) for r in P.itertuples()]
R=pd.concat([T,R[R.status!='tested']]); R.to_csv('../2020_24_ohlcv_score.csv',index=False,float_format='%.5f')
print('trials',len(T),'bh',T.bh.sum(),'core',T.pass_core.sum(),'all',T.get('pass_all',pd.Series()).eq(True).sum())
