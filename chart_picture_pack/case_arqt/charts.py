import pandas as pd, numpy as np, pyarrow.parquet as pq, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from feats import feats; from feats2 import add2,add3
K=['gr_body10','gr_body20','pctB','ext20','days_below_mid','mid_slope_up','slope50','vs50','days_since_h20','dip_atr','pos20','dd_vs_run','lower_highs10','redgreen_vol10','rsi14','mfi','rvol','up5','d52h']
def load(t,d):
    if t=='ARQT': p=pd.read_csv('ARQT.csv',index_col=0,parse_dates=True)
    else:
        d0=pd.Timestamp(d); p=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',filters=[('ticker','==',t),('date','>=',d0-pd.Timedelta(days=500)),('date','<',min(d0+pd.Timedelta(days=60),pd.Timestamp('2025-01-01')))]).to_pandas().drop_duplicates('date').set_index('date').sort_index().rename(columns=str.capitalize)
    return add3(add2(feats(p)))
def chart(t,d,D,tag):
    i=D.index.get_loc(pd.Timestamp(d)); w=D.iloc[max(i-30,0):i+21]; x=np.arange(len(w)); s=i-max(i-30,0)
    fig,(ax,av)=plt.subplots(2,1,figsize=(9,5),sharex=True,gridspec_kw={'height_ratios':[3,1]})
    for k,(o,h,l,c) in enumerate(zip(w.Open,w.High,w.Low,w.Close)):
        col='g' if c>=o else 'r'; ax.vlines(k,l,h,color=col,lw=.8); ax.add_patch(plt.Rectangle((k-.3,min(o,c)),.6,max(abs(c-o),1e-6),color=col))
    ax.plot(x,w.bb_mid,'b-',lw=1,label='BB mid (20)'); ax.plot(x,w.bb_up,'b--',lw=.7); ax.plot(x,w.bb_lo,'b--',lw=.7,label='BB ±2σ')
    ax.axvline(s,color='orange',ls='--',label=f'match day {d}'); ax.legend(fontsize=7,loc='best'); ax.set_title(f'{t} {d} — {tag}')
    av.bar(x,w.Volume,color=['g' if c>=o else 'r' for o,c in zip(w.Open,w.Close)]); av.set_xticks(x[::5]); av.set_xticklabels([str(z)[:10] for z in w.index[::5]],rotation=30,fontsize=7)
    fig.tight_layout(); fn=f'chart_{t}_{d}.png'; fig.savefig(fn,dpi=85); plt.close(fig); return fn
rows={}
for t,d,tag in [('ARQT','2026-10-07','reference'),('ALDX','2021-11-18','nearest failed'),('MXCT','2022-04-08','nearest failed'),('CWEN','2024-04-18','nearest rallied'),('API','2020-12-29','nearest rallied')]:
    D=load(t,d); fn=chart(t,d,D,tag); i=D.index.get_loc(pd.Timestamp(d)); r=D.iloc[i][K].to_dict()
    if t!='ARQT':
        e=D.Open.iloc[i+1]; f=D.iloc[i+1:i+21]
        r|=dict(entry=e,d5=f.Close.iloc[4]/e-1,d10=f.Close.iloc[9]/e-1,d20=f.Close.iloc[19]/e-1,maxup=f.High.max()/e-1,maxdn=f.Low.min()/e-1)
    rows[f'{t} {d}']=r; print(fn)
T=pd.DataFrame(rows); T.to_csv('twins_table.csv',float_format='%.3f'); print(T.round(3).to_string())
