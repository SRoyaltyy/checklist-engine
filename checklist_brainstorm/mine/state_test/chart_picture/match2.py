# 2020-24 ONLY, survivors universe. Feature re-match + whole-shape kNN vs ARQT 2026-10-07.
import pandas as pd, numpy as np, pyarrow.parquet as pq
from feats import feats; from feats2 import add2,add3
FEE=0.006; W=25
R=add3(add2(feats(pd.read_csv('ARQT.csv',index_col=0,parse_dates=True))))
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close','volume'],
  filters=[('date','>=',pd.Timestamp('2019-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
assert px.date.max()<pd.Timestamp('2025-01-01')
px['ticker']=px.ticker.astype(str); px=px.drop_duplicates(['ticker','date']).sort_values(['ticker','date']).reset_index(drop=True)
px.columns=['ticker','date','Open','High','Low','Close','Volume']
for c in ['Open','High','Low','Close','Volume']: px[c]=px[c].astype('float64')
A=add3(add2(px,by=px.ticker),by=px.ticker); print('add2 done',flush=True)
T=A.ticker; C=A.Close; pc=C.groupby(T).shift(); tr=np.maximum(A.High,pc.fillna(A.High))-np.minimum(A.Low,pc.fillna(A.Low))
A['atr14']=tr.groupby(T).transform(lambda x:x.rolling(14).mean())
A['v50']=A.Volume.groupby(T).transform(lambda x:x.rolling(50,min_periods=40).mean().shift())
A['date']=A.date.dt.strftime('%Y-%m-%d')
F=pd.read_parquet('/workspace/checklist_brainstorm/mine/state_test/ohlcv/feat.parquet',columns=['ticker','date','r5','r20','rsi14','mfi','rvol','b_atr','b_px','b_r1'])
F=F[F.r20.notna()&F.b_atr.notna()&F.b_r1.notna()].copy()
F['ctrl20']=F.groupby(['date','b_px','b_atr','b_r1']).r20.transform('mean')
A=A.reset_index(drop=True); A['row']=np.arange(len(A))
M=A.merge(F,on=['ticker','date'],how='inner'); print('merged',M.shape,flush=True)
M=M[(M.Close>=5)&(M.Volume*M.Close>1e6)]
K=['days_since_h20','days_below_mid','mid_slope_up','lower_highs10','redgreen_vol10','dd_vs_run','gr_body10','gr_body20','pctB','slope20','slope50','vs50','dip_atr','pos20','rsi14','mfi','rvol','ext20','up5','d52h']
ref=R.loc['2026-10-07']; print(ref[K].round(3).to_string())
def summ(x,name):
    r=x.r20.values; e=r-x.ctrl20.values
    return dict(set=name,n=len(x),tickers=x.ticker.nunique(),share_ge20=(r>=.2).mean(),share_up10=(r>=.1).mean(),share_fell=(r<0).mean(),share_le_m10=(r<=-.1).mean(),
      win_after_fee=(r-FEE>0).mean(),mean_after_fee=r.mean()-FEE,median_after_fee=np.median(r)-FEE,mean_vs_ctrl=e.mean(),median_vs_ctrl=np.median(e))
tol=dict(gr_body10=(.15,.75),gr_body20=(.9,1.5),pctB=(.12,.38),mid_slope_up=(1,1),slope50=(-.035,.005),vs50=(-.10,-.02),days_since_h20=(7,15),
  dip_atr=(2.3,4.2),pos20=(.08,.35),dd_vs_run=(.55,1.0),lower_highs10=(5,9),redgreen_vol10=(.6,1.8),rsi14=(36,48),mfi=(10,35),rvol=(.5,1.4),up5=(-.14,-.04),d52h=(-.4,-.08))
CS=lambda X:(X.gr_body20>=.9)&(X.mid_slope_up==1)&(X.dip_atr<=4.2)&(X.pctB>=.12)&(X.dd_vs_run>=.5)&X.days_since_h20.between(5,18)
m=np.ones(len(M),bool)
for k,(a,b) in tol.items(): m&=M[k].between(a,b).values
FM=M[m]; out=[summ(FM,'feature_match_tight'),summ(M,'all_liquid')]
FM[['ticker','date','Close','r20','ctrl20']+K].to_csv('feature_match_tight.csv',index=False,float_format='%.4f')
pre=M[M.pctB.between(-.1,.6)&M.up5.between(-.2,0)&M.ext20.between(-.15,.02)&M.slope50.between(-.06,.02)&M.atr14.notna()&M.v50.notna()]
print('prefilter',len(pre),flush=True)
O,H,L,Cc,V,PB,V50=[A[c].values for c in ['Open','High','Low','Close','Volume','pctB','v50']]
def vec(rows,atr):
    idx=rows[:,None]+np.arange(-W+1,1)[None,:]
    o,h,l,c=O[idx],H[idx],L[idx],Cc[idx]; a=atr[:,None]
    body=(c-o)/a; uw=(h-np.maximum(o,c))/a; lw=(np.minimum(o,c)-l)/a
    cz=(c-c.mean(1,keepdims=True))/c.std(1,keepdims=True).clip(1e-9)
    pb=np.clip(PB[idx],-.5,1.5); lv=np.clip(np.log(V[idx]/V50[idx]),-2,2)
    return np.hstack([body,uw,lw,cz,pb,lv])
Rv=R.copy(); Rv['v50']=Rv.Volume.rolling(50,min_periods=40).mean().shift(); pcr=Rv.Close.shift()
Rv['atr14']=(np.maximum(Rv.High,pcr.fillna(Rv.High))-np.minimum(Rv.Low,pcr.fillna(Rv.Low))).rolling(14).mean()
j=Rv.index.get_loc(pd.Timestamp('2026-10-07')); w=Rv.iloc[j-W+1:j+1]; a=Rv.atr14.iloc[j]
rb=np.hstack([(w.Close-w.Open)/a,(w.High-np.maximum(w.Open,w.Close))/a,(np.minimum(w.Open,w.Close)-w.Low)/a,(w.Close-w.Close.mean())/w.Close.std(ddof=0),
   np.clip(w.pctB,-.5,1.5),np.clip(np.log(w.Volume/w.v50),-2,2)]).astype(float)
rows=pre.row.values; ok=(rows>=W)&(A.ticker.values[np.maximum(rows-W+1,0)]==pre.ticker.values)
pre=pre[ok]; rows=rows[ok]
D=np.empty(len(pre))
for s in range(0,len(pre),50000):
    X=vec(rows[s:s+50000],pre.atr14.values[s:s+50000]); D[s:s+50000]=np.sqrt(np.nanmean((X-rb)**2,1))
pre=pre.assign(dist=D).sort_values('dist')
pre['ym']=pd.to_datetime(pre.date).dt.to_period('M')
nn0=pre.drop_duplicates(['ticker','ym']); nn=nn0[CS(nn0)]
print('AAPL 2022-09-01 in raw kNN rank:', (nn0.reset_index(drop=True).query("ticker=='AAPL' and date=='2022-09-01'").index.tolist()), 'in gated:', len(nn.query("ticker=='AAPL' and date=='2022-09-01'")), 'in featmatch:', len(FM.query("ticker=='AAPL' and date=='2022-09-01'")))
for k in (100,300): out.append(summ(nn0.head(k),f'shape_ungated_top{k}')|dict(dist_cutoff=nn0.dist.iloc[k-1],mean_dist=nn0.dist.head(k).mean()))
print('random-pair typical dist (median prefilter):',np.median(D))
for k in (25,50,100,200,300,400,500,750,1000,2000):
    out.append(summ(nn.head(k),f'shape_top{k}')|dict(dist_cutoff=nn.dist.iloc[k-1],mean_dist=nn.dist.head(k).mean()))
nn.head(2000)[['ticker','date','row','dist','Close','r20','ctrl20']+K].to_csv('shape_knn_top2000.csv',index=False,float_format='%.4f')
S=pd.DataFrame(out); S.to_csv('base_rate_v2_2020_24.csv',index=False,float_format='%.4f')
pd.set_option('display.width',250); print(S.round(4).to_string())
print(nn.head(30)[['ticker','date','dist','Close','r20']].to_string()); print(FM[['ticker','date','Close','r20']].to_string())
