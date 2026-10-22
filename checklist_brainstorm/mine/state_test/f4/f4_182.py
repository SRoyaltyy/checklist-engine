import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; FEE=0.002; LCUT=0.6205; W=['SEC-JA-F4-182']
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
# reuse price features from f4_frame if possible — join answers onto it
base=pd.read_parquet('f4_frame.parquet',columns=['ticker','date','year','ex','f','f30','L5','px','b_atr','b_px','b_r1','b_r5','b_dv'])
X=[]
for y in range(2020,2025):
    P=[]
    for f in sorted(glob.glob(C+f'{y}__JA_F4X__*.parquet')):
        j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids']); assert fid==W
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),1)
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=W)],axis=1)); del D
    X.append(pd.concat(P)); print(y,flush=True)
A=pd.concat(X); M=base.merge(A,on=['ticker','date']); del base,A,X; gc.collect(); M=M.sort_values(['ticker','date']).reset_index(drop=True)
w=W[0]
def cl(r,d):
    n=len(r); m=r.mean(); e=pd.Series(r-m).groupby(d).sum(); se=np.sqrt((e**2).sum())/n; return m,m-1.96*se,m+1.96*se
def events(mask):
    prev=mask.groupby(M.ticker,sort=False).shift(1,fill_value=False); return int((mask&~prev).sum())
def signs(r,yrs):
    s=pd.Series(r).groupby(yrs).mean(); return ''.join(('+' if s[str(y)]>0 else '-') if str(y) in s.index else '.' for y in range(2020,2025))
def do_match(d, ret, keys):
    c=d[d['_c']==1].groupby(keys)[ret].mean().rename('cm').reset_index(); Y=d[d['_c']==2].merge(c,on=keys)
    res=(Y[ret]-Y.cm).values; m,lo,hi=cl(res,Y.date.values); return m,lo,hi,int(Y.date.nunique()),len(Y),signs(res,Y.year.values), float((res>0).mean())
yes=M[w]==2; d=M[yes]; nd=int(d.date.nunique()); yr=yes.sum()/(M[w]>0).sum()
m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
rows=[dict(id=w,meaning='bullish',yes_rate=yr,ex5=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)),n_dates=nd,n_events=events(yes),n_obs=len(d),signs=signs(d.ex.values,d.year.values),
           win10=float((d.f>0).mean()),win30=float((d.f30>0).mean()))]
l=d[d.L5]; lb=M[M.L5].ex.mean(); lm,llo,lhi=cl(l.ex.values,l.date.values); rows[0].update(L5_minus_L5all=lm-lb,L5_lo95=llo-lb,L5_hi95=lhi-lb,L5_dates=int(l.date.nunique()),L5_events=events(yes&M.L5))
base=M[M[w]>0].copy(); base['_c']=base[w]
MATCH=[]
for nm,keys in [('atr_px',['b_atr','b_px']),('atr_px_r1',['b_atr','b_px','b_r1']),('r1_dv',['b_r1','b_dv'])]:
    d0=base.dropna(subset=keys)
    for ret,fee in [('f','10bp'),('f30','30bp')]:
        for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.values),('px2',(d0.px>=2).values)]:
            m_,lo_,hi_,nd_,no_,sg,wr=do_match(d0[mask],ret,['date']+keys)
            MATCH.append(dict(id=w,control=nm,fee=fee,scope=sc,resid=m_,lo=lo_,hi=hi_,dates=nd_,obs=no_,signs=sg,win_rate=wr))
R=pd.DataFrame(rows); MR=pd.DataFrame(MATCH)
R.to_csv('../2020_24_f4_182_score.csv',index=False,float_format='%.6f'); MR.to_csv('../2020_24_f4_182_matched.csv',index=False,float_format='%.6f')
pd.set_option('display.width',250); print(R.round(5).to_string()); print(MR.round(5).to_string())
