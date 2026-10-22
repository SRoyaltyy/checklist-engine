import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; FEE=0.002; LCUT=0.6205
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
TAG=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/theme-radar_si_tags.csv')
# map tag row_id -> chunk id (chunk uses |N suffix; POS windows differ from tag N column)
j=json.load(open(C+'2024__SI__Energy.json')); all_ids=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids'])
cmap={}
for rid in TAG.row_id:
    hits=[i for i in all_ids if i==rid or i.startswith(rid+'|')]
    assert len(hits)==1, (rid,hits); cmap[rid]=hits[0]
W=list(cmap.values()); print('mapped',len(W), W[:3], W[-3:], flush=True)
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close','volume'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str); dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d')
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=px.merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open); A=A.sort_values(['ticker','date']).reset_index(drop=True)
g=A.groupby('ticker',sort=False); A['cd']=g['div'].cumsum(); o=g.open; cd=A.groupby('ticker',sort=False).cd; pc=g.close.shift(1)
g0=(o.shift(-6)+cd.shift(-6)-cd.shift(-1))/o.shift(-1)-1; A['f']=g0-FEE; A['f30']=g0-0.006; A.loc[g0.abs()>2,['f','f30']]=np.nan
tr=np.maximum(A.high,pc.fillna(A.high))-np.minimum(A.low,pc.fillna(A.low))
A['atrp']=tr.groupby(A.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/A.close
A['r1']=A.close/pc-1; A['px']=A.close; A['r5']=A.close/g.close.shift(5)-1
A['dv20']=(A.close*A.volume).groupby(A.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=10).mean())
A=A[A.date>='2020-01-01'].dropna(subset=['f'])[['ticker','date','f','f30','atrp','px','r1','r5','dv20']]
A['ex']=A.f-A.groupby('date').f.transform('mean')
for col,q,nm in [('atrp',5,'b_atr'),('px',5,'b_px'),('r1',10,'b_r1'),('r5',10,'b_r5'),('dv20',3,'b_dv')]:
    A[nm]=A.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
A=A.drop(columns=['atrp','r1','r5','dv20']); gc.collect()
X=[]
for y in range(2020,2025):
    st=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']); st['ticker']=st.ticker.astype(str); st['date']=st.date.astype(str).str[:10]
    P=[]
    for f in sorted(glob.glob(C+f'{y}__SI__*.parquet')):
        j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids']); ix=[fid.index(w) for w in W]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=W)],axis=1)); del D
    X.append(pd.concat(P).merge(st.drop_duplicates(['ticker','date']),on=['ticker','date'],how='left')); print(y,flush=True); gc.collect()
M=pd.concat(X).merge(A,on=['ticker','date']); del A,X; gc.collect()
M=M.sort_values(['ticker','date']).reset_index(drop=True)
M['L5']=M.lean>=LCUT; M['year']=M.date.str[:4]
M.to_parquet('tr_si_frame.parquet'); print('saved',len(M),flush=True)
# analyze
rev={v:k for k,v in cmap.items()}; meaning=dict(zip(TAG.row_id,TAG.meaning)); bucket=dict(zip(TAG.row_id,TAG.bucket))
def cl(r,d):
    n=len(r)
    if n<2: return np.nan,np.nan,np.nan
    m=r.mean(); e=pd.Series(r-m).groupby(d).sum(); se=np.sqrt((e**2).sum())/n; return m,m-1.96*se,m+1.96*se
def events(mask):
    prev=mask.groupby(M.ticker,sort=False).shift(1,fill_value=False); return int((mask&~prev).sum())
def signs(r,yrs):
    s=pd.Series(r).groupby(yrs).mean(); return ''.join(('+' if s[str(y)]>0 else '-') if str(y) in s.index else '.' for y in range(2020,2025))
def do_match(d, ret, keys):
    c=d[d['_c']==1].groupby(keys)[ret].mean().rename('cm').reset_index(); Y=d[d['_c']==2].merge(c,on=keys)
    if len(Y)<2: return dict(resid=np.nan,lo=np.nan,hi=np.nan,dates=0,obs=0,signs='')
    res=(Y[ret]-Y.cm).values; m,lo,hi=cl(res,Y.date.values); return dict(resid=m,lo=lo,hi=hi,dates=int(Y.date.nunique()),obs=len(Y),signs=signs(res,Y.year.values))
rows=[]
for w in W:
    rid=rev[w]; rd=M[w]>0; yes=M[w]==2; d=M[yes]; nd=int(d.date.nunique()); yr=yes.sum()/rd.sum() if rd.sum() else np.nan
    r=dict(id=rid,chunk_id=w,meaning=meaning[rid],bucket=bucket[rid],ready_obs=int(rd.sum()),yes_rate=yr,n_obs=len(d),n_dates=nd,n_events=events(yes),non_separating=bool(yr>0.5) if rd.sum() else False)
    if nd>=30:
        m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92; r.update(ex5=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
        l=d[d.L5]; lb=M[M.L5].ex.mean()
        if l.date.nunique()>=2:
            lm,llo,lhi=cl(l.ex.values,l.date.values); r.update(L5_minus_L5all=lm-lb,L5_lo95=llo-lb,L5_hi95=lhi-lb,L5_dates=int(l.date.nunique()),L5_events=events(yes&M.L5),L5_signs=signs(l.ex.values,l.year.values))
    rows.append(r); print('raw',rid,nd,flush=True)
R=pd.DataFrame(rows); R['status']=np.where(R.ready_obs==0,'NOT_READY_all',np.where(R.n_dates<30,'too_few_dates','tested'))
T=R.status=='tested'; p=R.loc[T,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05; k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0
bh=np.zeros(mt,bool); bh[o[:k]]=True; R['bh']=False; R.loc[T,'bh']=bh
print('tested',mt,'clear',int((R.p<.05).sum()),'BH',k,flush=True)
CTRLS={'atr_px_r1':['b_atr','b_px','b_r1'],'atr_px':['b_atr','b_px'],'r1_dv':['b_r1','b_dv']}
MATCH=[]
for i in R.index[R.bh|(R.status=='tested')]:  # match all tested (only 34)
    w=R.chunk_id[i]; base=M[M[w]>0][['date','year','f','f30','L5','px','b_atr','b_px','b_r1','b_dv']].copy(); base['_c']=M.loc[base.index,w].values
    for nm,keys in CTRLS.items():
        d0=base.dropna(subset=keys)
        for ret,fee in [('f','10bp'),('f30','30bp')]:
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.values),('px2',(d0.px>=2).values)]:
                m=do_match(d0[mask],ret,['date']+keys); MATCH.append(dict(id=R.id[i],control=nm,fee=fee,scope=sc,**{f'm_{k}':v for k,v in m.items()}))
    print('match',R.id[i],flush=True)
MR=pd.DataFrame(MATCH); MR.to_csv('../2020_24_tr_si_matched.csv',index=False,float_format='%.6f')
for i in R.index[R.bh|(R.status=='tested')]:
    rid=R.id[i]
    for nm,pref in [('atr_px_r1','match'),('atr_px','match_ap')]:
        for fee,sfx in [('10bp',''),('30bp','_30')]:
            for sc in ['all','L5','px2']:
                m=MR[(MR.id==rid)&(MR.control==nm)&(MR.fee==fee)&(MR.scope==sc)].iloc[0]
                R.loc[i,f'{pref}{sfx}_{sc}']=m.m_resid; R.loc[i,f'{pref}{sfx}_{sc}_lo']=m.m_lo; R.loc[i,f'{pref}{sfx}_{sc}_hi']=m.m_hi
                R.loc[i,f'{pref}{sfx}_{sc}_dates']=m.m_dates; R.loc[i,f'{pref}{sfx}_{sc}_signs']=m.m_signs
R.sort_values('p').to_csv('../2020_24_tr_si_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280)
c=['id','meaning','bucket','yes_rate','non_separating','ex5','lo95','hi95','n_dates','n_events','p','bh','signs','L5_minus_L5all','L5_dates',
   'match_all','match_all_lo','match_all_hi','match_all_signs','match_30_all','match_30_all_lo','match_30_all_hi','match_30_all_signs','match_L5','match_30_L5','match_px2','match_30_px2']
print(R.sort_values('p')[[x for x in c if x in R.columns]].round(5).to_string())
