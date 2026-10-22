import pandas as pd, numpy as np
from scipy.stats import norm
TAG=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/theme-radar_si_tags.csv')
M=pd.read_parquet('tr_si/tr_si_frame.parquet')  # has answers + L5 + buckets + f/f30 5d only
# remap chunk cols: frame uses chunk ids
import json,ast
j=json.load(open('/workspace/checklist_brainstorm/engine/universe/chunks/2024__SI__Energy.json'))
all_ids=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids'])
cmap={}; 
for rid in TAG.row_id:
    hits=[i for i in all_ids if i==rid or i.startswith(rid+'|')]; assert len(hits)==1; cmap[rid]=hits[0]
W=list(cmap.values()); rev={v:k for k,v in cmap.items()}; meaning=dict(zip(TAG.row_id,TAG.meaning))
Rets=pd.read_parquet('multi_h_rets.parquet')
# drop old f columns to save mem
keep=['ticker','date','year','L5','px','b_atr','b_px','b_r1']+W
M=M[keep].merge(Rets,on=['ticker','date']); del Rets
M=M.sort_values(['ticker','date']).reset_index(drop=True)
print('frame',M.shape,flush=True)
HS=(5,10,20); FEES=(10,30)
def cl(r,d):
    n=len(r)
    if n<2: return np.nan,np.nan,np.nan
    m=r.mean(); e=pd.Series(r-m).groupby(d).sum(); se=np.sqrt((e**2).sum())/n; return m,m-1.96*se,m+1.96*se
def events(mask):
    prev=mask.groupby(M.ticker,sort=False).shift(1,fill_value=False); return int((mask&~prev).sum())
def signs(r,yrs):
    s=pd.Series(r).groupby(yrs).mean(); return ''.join(('+' if s[str(y)]>0 else '-') if str(y) in s.index else '.' for y in range(2020,2025))
def do_match(d, retcol, keys):
    c=d[d['_c']==1].groupby(keys)[retcol].mean().rename('cm').reset_index(); Y=d[d['_c']==2].merge(c,on=keys)
    if len(Y)<2: return dict(resid=np.nan,lo=np.nan,hi=np.nan,dates=0,obs=0,signs='',win=np.nan)
    res=(Y[retcol]-Y.cm).values; m,lo,hi=cl(res,Y.date.values)
    return dict(resid=m,lo=lo,hi=hi,dates=int(Y.date.nunique()),obs=len(Y),signs=signs(res,Y.year.values),win=float((res>0).mean()))
rows=[]; MATCH=[]
for w in W:
    rid=rev[w]; rd=M[w]>0; yes=M[w]==2; yr=yes.sum()/rd.sum() if rd.sum() else np.nan; nev=events(yes)
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'; dm=M.groupby('date')[col].transform('mean')
            d=M.loc[yes & M[col].notna(), ['ticker','date','year','L5','px','b_atr','b_px','b_r1',col]].copy(); d['ex']=d[col]-dm.loc[d.index]
            nd=int(d.date.nunique())
            r=dict(id=rid,chunk_id=w,meaning=meaning[rid],H=H,fee=fee,yes_rate=yr,non_separating=bool(yr>0.5) if rd.sum() else False,
                   n_dates=nd,n_events=nev,n_obs=len(d),win_rate=float((d[col]>0).mean()) if len(d) else np.nan)
            if nd<30: r['status']='too_few_dates'; rows.append(r); continue
            m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
            r.update(status='tested',ex=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
            rows.append(r)
    print('scored',rid,flush=True)
R=pd.DataFrame(rows); R['bh']=False
for (H,fee),idx in R[R.status=='tested'].groupby(['H','fee']).groups.items():
    p=R.loc[idx,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05
    k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0; bh=np.zeros(mt,bool); bh[o[:k]]=True; R.loc[idx,'bh']=bh
    print(f'BH H={H} fee={fee} tested={mt} BH={k}',flush=True)
need=set(R.id[R.bh|(R.status=='tested')])  # all tested, only 34
for rid in need:
    w=cmap[rid]; base=M[M[w]>0][['date','year','L5','px','b_atr','b_px','b_r1']+[f'f{H}_{fee}' for H in HS for fee in FEES]].copy(); base['_c']=M.loc[base.index,w].values
    d0=base.dropna(subset=['b_atr','b_px','b_r1'])
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.values),('px2',(d0.px>=2).values)]:
                m=do_match(d0[mask].dropna(subset=[col]),col,['date','b_atr','b_px','b_r1'])
                MATCH.append(dict(id=rid,H=H,fee=fee,scope=sc,control='atr_px_r1',**m))
    print('match',rid,flush=True)
MR=pd.DataFrame(MATCH); MR.to_csv('2020_24_tr_si_matched_multi.csv',index=False,float_format='%.6f')
for i in R.index[R.status=='tested']:
    m=MR[(MR.id==R.id[i])&(MR.H==R.H[i])&(MR.fee==R.fee[i])&(MR.scope=='all')&(MR.control=='atr_px_r1')]
    if len(m):
        m=m.iloc[0]; R.loc[i,'match_resid']=m.resid; R.loc[i,'match_lo']=m.lo; R.loc[i,'match_hi']=m.hi; R.loc[i,'match_win']=m.win; R.loc[i,'match_signs']=m.signs; R.loc[i,'match_dates']=m.dates
def pass_row(r):
    if r.status!='tested' or r.fee!=30 or pd.isna(r.get('match_win',np.nan)): return False
    if not (r.match_win>0.5): return False
    bull=str(r.meaning)=='bullish'
    if bull: return bool(r.match_lo>0)
    if r.meaning in ('loud_bearish','quiet_warning'): return bool(r.match_hi<0)
    return False  # context rows don't pass as directional
R['pass_bar']=R.apply(pass_row,axis=1)
R.to_csv('2020_24_tr_si_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280)
print(R.sort_values(['H','fee','p'])[['id','meaning','H','fee','yes_rate','ex','lo95','hi95','n_dates','n_events','win_rate','p','bh','signs','match_resid','match_lo','match_hi','match_win','pass_bar']].round(5).to_string())
print('PASS',R[R.pass_bar][['id','H','fee','match_resid','match_win','n_dates','n_events']].to_string())
