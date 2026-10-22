import pandas as pd, numpy as np
from scipy.stats import norm
NBT=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/new-bot_si_tags.csv'); TFT=pd.read_csv('pv_tfc_si_tags.csv',keep_default_na=False)
tag={**{r.row_id:(r.polarity,'nb') for r in NBT.itertuples()},**{r.row_id:(r.meaning,f'b{r.bucket}') for r in TFT.itertuples()}}
W=list(tag)
M=pd.read_parquet('si_frame.parquet',columns=['ticker','date','year','ex','f','L5','spike','b_atr','b_px','b_r1']+W)
def cl(r,d):
    n=len(r)
    if n<2: return np.nan,np.nan,np.nan
    m=r.mean(); e=pd.Series(r-m).groupby(d).sum(); se=np.sqrt((e**2).sum())/n; return m,m-1.96*se,m+1.96*se
def events(mask):  # distinct events = YES runs per ticker (new event if previous row of same ticker was not YES)
    prev=mask.groupby(M.ticker,sort=False).shift(1,fill_value=False); return int((mask&~prev).sum())
def signs(r,yrs):
    s=pd.Series(r).groupby(yrs).mean(); return ''.join(('+' if s[str(y)]>0 else '-') if str(y) in s.index else '.' for y in range(2020,2025))
rows=[]
for w in W:
    rd=M[w]>0; yes=M[w]==2; d=M[yes]; nd=d.date.nunique()
    r=dict(id=w,meaning=tag[w][0],tag_src=tag[w][1],ready_obs=int(rd.sum()),yes_rate=yes.sum()/rd.sum() if rd.sum() else np.nan,n_obs=len(d),n_dates=nd,n_events=events(yes))
    if nd>=30:
        m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92; r.update(ex5=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)),signs=signs(d.ex.values,d.year.values))
        l=d[d.L5]; lb=M[M.L5].ex.mean(); lm,llo,lhi=cl(l.ex.values,l.date.values); r.update(L5_minus_L5all=lm-lb,L5_lo95=llo-lb,L5_hi95=lhi-lb,L5_dates=l.date.nunique(),L5_events=events(yes&M.L5))
    rows.append(r)
R=pd.DataFrame(rows); R['status']=np.where(R.ready_obs==0,'NOT_READY_all',np.where(R.n_dates<30,'too_few_dates','tested'))
T=R.status=='tested'; p=R.loc[T,'p'].values; mt=len(p); o=np.argsort(p); ok=p[o]<=np.arange(1,mt+1)/mt*0.05; k=np.max(np.where(ok)[0])+1 if ok.any() else 0
bh=np.zeros(mt,bool); bh[o[:k]]=True; R['bh']=False; R.loc[T,'bh']=bh; R['near_always_yes']=R.yes_rate>0.9
print('tested',mt,'p<.05',(R.p<.05).sum(),'chance',0.05*mt,'BH',k)
# matched for BH survivors
keys=['date','b_atr','b_px','b_r1']
for i in R.index[R.bh]:
    w=R.id[i]; d=M[(M[w]>0)].dropna(subset=keys[1:]); c=d[d[w]==1].groupby(keys).f.mean().rename('cm').reset_index(); Y=d[d[w]==2].merge(c,on=keys)
    for sc,yy in [('all',Y),('L5',Y[Y.L5])]:
        res=(yy.f-yy.cm).values; m,lo,hi=cl(res,yy.date.values); R.loc[i,f'match_{sc}']=m; R.loc[i,f'match_{sc}_lo']=lo; R.loc[i,f'match_{sc}_hi']=hi; R.loc[i,f'match_{sc}_dates']=yy.date.nunique(); R.loc[i,f'match_{sc}_signs']=signs(res,yy.year.values) if len(yy) else ''
R.sort_values('p').to_csv('../2020_24_si_score.csv',index=False,float_format='%.6f')
# combos
fuel=[w for w in ['nbx-SI-ABS-DTC-HI','nbx-SI-REL-RANK-HI','nbx-SI-EXT-HI','nbx-SI-POS-HI','nbx-SI-THR-UP20','nbx-SI-B7-SQZ-FUEL','PV-TFC-0921|1','PV-TFC-0923|1','PV-TFC-0935|1','PV-TFC-0941|1'] if w in W]
CB=[]
for w in fuel:
    rd=M[w]>0
    for nm,a,b in [('fuel & L5 vs L5 not-fuel (ready)',(M[w]==2)&M.L5,(M[w]==1)&M.L5),('fuel & L5 vs fuel not-L5',(M[w]==2)&M.L5,(M[w]==2)&~M.L5),
                   ('fuel & spike vs spike not-fuel (take-profit)',(M[w]==2)&M.spike,(M[w]==1)&M.spike),('fuel & spike vs fuel no-spike',(M[w]==2)&M.spike,(M[w]==2)&~M.spike.fillna(False))]:
        A_=M[a]; B_=M[b]
        if A_.date.nunique()<2: CB.append(dict(id=w,combo=nm,n_dates=A_.date.nunique(),n_events=events(a))); continue
        bm=B_.groupby('date').ex.mean().rename('bm'); A2=A_.join(bm,on='date').dropna(subset=['bm']); res=(A2.ex-A2.bm).values; m,lo,hi=cl(res,A2.date.values)
        CB.append(dict(id=w,combo=nm,diff=m,lo95=lo,hi95=hi,combo_ex5=A_.ex.mean(),combo_absmove=A_.f.abs().mean(),other_absmove=B_.f.abs().mean(),n_obs=len(A2),n_dates=A2.date.nunique(),n_events=events(a),signs=signs(res,A2.year.values)))
CB=pd.DataFrame(CB); CB.to_csv('../2020_24_si_combos.csv',index=False,float_format='%.6f')
pd.set_option('display.width',260); pd.set_option('display.max_columns',40)
print(R.sort_values('p')[['id','meaning','tag_src','status','yes_rate','ex5','lo95','hi95','n_dates','n_events','p','bh','signs','L5_minus_L5all','L5_lo95','L5_hi95','match_all','match_all_lo','match_all_hi','match_all_signs','match_L5','match_L5_lo','match_L5_hi']].round(5).to_string())
print(CB.round(5).to_string())
