#!/usr/bin/env python3
"""Vectorized re-run of screen_singles.screen() rules on Grok 20x60 preburn panel (PILOT, first-look).
Same rules: YES only, select dates<=2026-06-30, first half dates=train, second half=test,
clear = test n>=30, win>55% after 0.20% RT, mean_aft>0 (o2o). Labels NOT dividend-adjusted -> promote nothing.
Luck correction (pilot): Bonferroni over family count from twin_families/families.csv (r>=0.9)."""
import json, numpy as np, pandas as pd
from scipy import stats as ss
from screen_singles import FEE_RT, MIN_N, MIN_WIN, SELECT_END
P='/workspace/checklist_brainstorm/engine/out/pilot_matrix/preburn/panel_yesno_preburn_james_grok.parquet'
F='/workspace/checklist_brainstorm/engine/out/twin_families/families.csv'
p=pd.read_parquet(P,columns=['row_id','owner','ticker','date','answer','ret_open_next_open','ret_open_close'])
nq=p.row_id.nunique(); p=p[p.answer=='YES'].copy()
for c in ['row_id','owner','date']: p[c]=p[c].astype(str)
p=p[p.date<=SELECT_END]; dates=sorted(p.date.unique()); dates_all=dates
mid=len(dates)//2; tr=set(dates[:mid]); p['half']=np.where(p.date.isin(tr),'train','test')
p['aft']=p.ret_open_next_open-FEE_RT; p['aftc']=p.ret_open_close-FEE_RT
def agg(g): 
    return pd.DataFrame({'n':g.aft.count(),'win':g.aft.apply(lambda x:(x>0).mean()),'mean_aft':g.aft.mean(),'sd':g.aft.std(),'n_dates':g.date.nunique()})
te=p[p.half=='test'].dropna(subset=['aft']); trn=p[p.half=='train'].dropna(subset=['aft'])
gt=te.groupby('row_id'); s=agg(gt); s.columns=[c+'_test' for c in s.columns]
s['mean_aft_test_o2c']=gt.aftc.mean()
g2=trn.groupby('row_id'); s2=agg(g2); s2.columns=[c+'_train' for c in s2.columns]
s=s2.join(s,how='outer'); s['owner']=p.groupby('row_id').owner.first()
s['clear_test']=(s.n_test>=MIN_N)&(s.win_test>MIN_WIN)&(s.mean_aft_test>0)
s['clear_train']=(s.n_train>=MIN_N)&(s.win_train>MIN_WIN)&(s.mean_aft_train>0)
s['t_test']=s.mean_aft_test/(s.sd_test/np.sqrt(s.n_test)); s['p_test']=ss.t.sf(s.t_test,s.n_test-1)
f=pd.read_csv(F); fam=f.set_index('question_id').family_id
s['family_id']=s.index.map(fam); 
nfam=f.family_id.nunique()+int(s.family_id.isna().sum())  # non-varying YES questions = own family
alpha=0.05/nfam; s['clear_bonf']=s.clear_test&(s.p_test<alpha)
s=s.sort_values(['clear_test','mean_aft_test'],ascending=[False,False])
out='reports/first_screen_singles_preburn_20x60.csv'; s.to_csv(out)
c=s[s.clear_test]; cf=c.dropna(subset=['family_id']).family_id.nunique()+int(c.family_id.isna().sum())
m=dict(panel=P,questions=nq,yes_rows=len(p),train=[dates[0],dates[mid-1]],test=[dates[mid],dates[-1]],scored=len(s),
 clear_test=int(c.shape[0]),clear_families=int(cf),clear_both_halves=int((s.clear_test&s.clear_train).sum()),
 n_families_luck=nfam,bonf_alpha=alpha,clear_bonf=int(s.clear_bonf.sum()),label='pilot; labels not dividend-adjusted; first-look, promote nothing')
json.dump(m,open('reports/preburn_20x60_meta.json','w'),indent=1,default=str); print(json.dumps(m,indent=1,default=str))
print(c.head(10)[['owner','family_id','n_train','win_train','mean_aft_train','n_test','n_dates_test','win_test','mean_aft_test','mean_aft_test_o2c','t_test','p_test','clear_bonf']].to_string())
# date-clustered robustness: 20 stocks on one date are not independent
dm=te.groupby(['row_id','date']).aft.mean().groupby('row_id')
cl=pd.DataFrame({'nd':dm.count(),'m':dm.mean(),'sd':dm.std()}); cl['t_date']=cl.m/(cl.sd/np.sqrt(cl.nd)); cl['p_date']=ss.t.sf(cl.t_date,cl.nd-1)
s=s.join(cl[['t_date','p_date']]); s['clear_bonf_date']=s.clear_test&(s.n_dates_test>=10)&(s.p_date<alpha)
s.to_csv(out); c=s[s.clear_test]
print('clear_test with >=10 test dates:',int((c.n_dates_test>=10).sum()),' bonf date-clustered:',int(s.clear_bonf_date.sum()))
m['clear_test_ge10dates']=int((c.n_dates_test>=10).sum()); m['clear_bonf_date_clustered']=int(s.clear_bonf_date.sum())
json.dump(m,open('reports/preburn_20x60_meta.json','w'),indent=1,default=str)
print(c[c.n_dates_test>=10].head(10)[['owner','family_id','n_train','win_train','mean_aft_train','n_test','n_dates_test','win_test','mean_aft_test','t_date','p_date']].to_string())
