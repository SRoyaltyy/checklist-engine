import pandas as pd, numpy as np
from scipy.stats import norm
TAG=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/james_f4_tags.csv')
W=list(TAG.row_id); meaning=dict(zip(TAG.row_id,TAG.meaning)); lens=dict(zip(TAG.row_id,TAG.lens))
FIRST=['SEC-JA-166','SEC-JA-166-BUT','SEC-JA-167','SEC-JA-167-BUT','SEC-JA-168','SEC-JA-168-BUT','SEC-JA-169','SEC-JA-169-BUT']
M=pd.read_parquet('f4_frame.parquet')
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
    rd=M[w]>0; yes=M[w]==2; d=M[yes]; nd=int(d.date.nunique()); yr=yes.sum()/rd.sum() if rd.sum() else np.nan
    r=dict(id=w,meaning=meaning[w],lens=lens[w],ready_obs=int(rd.sum()),yes_rate=yr,n_obs=len(d),n_dates=nd,n_events=events(yes),
           non_separating=bool(yr>0.5) if rd.sum() else False,
           years=''.join(str(y)[-1] if ((M.year==str(y))&(M[w]>0)).any() else '.' for y in range(2020,2025)))
    if nd>=30:
        m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92; r.update(ex5=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
        l=d[d.L5]; lb=M[M.L5].ex.mean()
        if l.date.nunique()>=2:
            lm,llo,lhi=cl(l.ex.values,l.date.values); r.update(L5_minus_L5all=lm-lb,L5_lo95=llo-lb,L5_hi95=lhi-lb,L5_dates=int(l.date.nunique()),L5_events=events(yes&M.L5),L5_signs=signs(l.ex.values,l.year.values))
    rows.append(r); print('raw',w,nd,flush=True)
R=pd.DataFrame(rows); R['status']=np.where(R.ready_obs==0,'NOT_READY_all',np.where(R.n_dates<30,'too_few_dates','tested'))
T=R.status=='tested'; p=R.loc[T,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05; k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0
bh=np.zeros(mt,bool); bh[o[:k]]=True; R['bh']=False; R.loc[T,'bh']=bh
print('tested',mt,'clear',int((R.p<.05).sum()),'BH',k,flush=True)
CTRLS={'raw':[],'r1_dv':['b_r1','b_dv'],'r5_dv':['b_r5','b_dv'],'atr_px':['b_atr','b_px'],'atr_px_r1':['b_atr','b_px','b_r1']}
need=set(R.id[R.bh|R.id.isin(FIRST)])
MATCH=[]
for w in need:
    base=M[M[w]>0][['ticker','date','year','f','f30','L5','px']+[c for c in ['b_atr','b_px','b_r1','b_r5','b_dv']]].copy(); base['_c']=M.loc[base.index,w].values
    for nm,keys in CTRLS.items():
        d0=base.dropna(subset=keys) if keys else base
        for ret,fee in [('f','10bp'),('f30','30bp')]:
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.values),('px2',(d0.px>=2).values)]:
                dd=d0[mask]; m=do_match(dd,ret,['date']+keys)
                MATCH.append(dict(id=w,control=nm,fee=fee,scope=sc,**{f'm_{k}':v for k,v in m.items()}))
    print('match',w,flush=True)
MR=pd.DataFrame(MATCH); MR.to_csv('../2020_24_f4_matched.csv',index=False,float_format='%.6f')
for i in R.index[R.id.isin(need)]:
    w=R.id[i]
    for nm,pref in [('atr_px_r1','match'),('atr_px','match_ap'),('r1_dv','match_rd')]:
        for fee,sfx in [('10bp',''),('30bp','_30')]:
            for sc in ['all','L5','px2']:
                m=MR[(MR.id==w)&(MR.control==nm)&(MR.fee==fee)&(MR.scope==sc)].iloc[0]
                R.loc[i,f'{pref}{sfx}_{sc}']=m.m_resid; R.loc[i,f'{pref}{sfx}_{sc}_lo']=m.m_lo; R.loc[i,f'{pref}{sfx}_{sc}_hi']=m.m_hi
                R.loc[i,f'{pref}{sfx}_{sc}_dates']=m.m_dates; R.loc[i,f'{pref}{sfx}_{sc}_signs']=m.m_signs
R['priority']=R.id.isin(FIRST)
R.sort_values(['priority','p'],ascending=[False,True]).to_csv('../2020_24_f4_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280); pd.set_option('display.max_columns',40)
c=['id','meaning','lens','yes_rate','non_separating','ex5','lo95','hi95','n_dates','n_events','p','bh','signs','years','L5_minus_L5all','L5_dates','L5_events',
   'match_all','match_all_lo','match_all_hi','match_all_signs','match_30_all','match_30_all_lo','match_30_all_hi','match_30_all_signs','match_L5','match_30_L5','match_px2','match_30_px2']
print('=== FIRST 166-169 ==='); print(R[R.priority].sort_values('p')[[x for x in c if x in R.columns]].round(5).to_string())
print('=== BH ==='); print(R[R.bh].sort_values('p')[[x for x in c if x in R.columns]].round(5).to_string())
print('=== REST ==='); print(R[(~R.bh)&(R.status=='tested')&~R.priority].sort_values('p')[['id','meaning','yes_rate','ex5','n_dates','n_events','p','signs']].round(5).to_string())
print(MR[MR.id.isin(FIRST)&MR.control.isin(['atr_px','atr_px_r1','r1_dv'])&MR.scope.isin(['all','L5','px2'])][['id','control','fee','scope','m_resid','m_lo','m_hi','m_dates','m_signs']].round(5).to_string())
