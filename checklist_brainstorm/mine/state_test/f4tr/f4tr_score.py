import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast, os
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
LCUT=0.6205; HS=(5,20,60); FEES=(10,30)
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
T=pd.read_csv('theme-radar_f4tr_tags.csv')
sha=__import__('hashlib').sha256(open('theme-radar_f4tr_tags.csv','rb').read()).hexdigest()
assert sha.startswith('201f39f3') and sha.endswith('fe02'), sha
# score: net-buy $, exclude rank vs theme
W=list(T[(T.subtype=='form4_net_ps_usd')&(~T.lens.str.contains('rank vs theme',case=False,na=False))].row_id)
meta=T.set_index('row_id').loc[W]
print('scoring',len(W),'rows; tags',sha,flush=True)
# load answers year by year into sparse-ish frame: only keep ticker,date + codes via concat
X=[]
for y in range(2020,2025):
    P=[]
    for f in sorted(glob.glob(C+f'{y}__F4TR__*.parquet')):
        j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids'])
        ix=[fid.index(w) for w in W]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=W)],axis=1)); del D
    X.append(pd.concat(P)); print('ans',y,len(X[-1]),flush=True); del P; gc.collect()
A=pd.concat(X); del X; gc.collect()
# features + returns
Rets=pd.read_parquet('../multi_h_rets.parquet')
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','high','low','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
px=px.sort_values(['ticker','date']); g=px.groupby('ticker',sort=False); pc=g.close.shift(1)
tr=np.maximum(px.high,pc.fillna(px.high))-np.minimum(px.low,pc.fillna(px.low))
px['atrp']=tr.groupby(px.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/px.close
px['r1']=px.close/pc-1; px['px']=px.close
px=px[px.date>='2020-01-01'][['ticker','date','atrp','px','r1']]
ST=pd.concat([pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']).assign(
    ticker=lambda d:d.ticker.astype(str), date=lambda d:d.date.astype(str).str[:10]) for y in range(2020,2025)]).drop_duplicates(['ticker','date'])
M=A.merge(px,on=['ticker','date'],how='inner').merge(ST,on=['ticker','date'],how='left').merge(Rets,on=['ticker','date'])
del A,px,ST,Rets; gc.collect()
M['L5']=M.lean>=LCUT; M['year']=M.date.str[:4]
for col,q,nm in [('atrp',5,'b_atr'),('px',5,'b_px'),('r1',10,'b_r1')]:
    M[nm]=M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
M=M.sort_values(['ticker','date']).reset_index(drop=True)
print('frame',M.shape,flush=True)
# free atrp etc
M.drop(columns=[c for c in ['atrp','r1','lean'] if c in M.columns], inplace=True, errors='ignore'); gc.collect()

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
for wi,w in enumerate(W):
    yes=M[w]==2; ready=M[w]>0; yr=yes.sum()/ready.sum() if ready.sum() else np.nan; nev=events(yes)
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'; dm=M.groupby('date')[col].transform('mean')
            d=M.loc[yes & M[col].notna(), ['date','year','L5',col]].copy(); d['ex']=d[col]-dm.loc[d.index]
            nd=int(d.date.nunique())
            r=dict(id=w,meaning=meta.loc[w,'meaning'],lens=meta.loc[w,'lens'],N=meta.loc[w,'N'],bucket=meta.loc[w,'bucket'],
                   H=H,fee=fee,yes_rate=yr,non_separating=bool(yr>0.5) if ready.sum() else False,
                   n_dates=nd,n_events=nev,n_obs=len(d),win_rate=float((d[col]>0).mean()) if len(d) else np.nan)
            if nd<30:
                r['status']='too_few_dates'; rows.append(r); continue
            m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
            r.update(status='tested',ex=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
            rows.append(r)
    if wi%20==0: print('scored',wi,w,int(yes.sum()),nev,flush=True)
print('raw done',len(rows),flush=True)
R=pd.DataFrame(rows); R['bh']=False
for (H,fee),idx in R[R.status=='tested'].groupby(['H','fee']).groups.items():
    p=R.loc[idx,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05
    k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0; bh=np.zeros(mt,bool); bh[o[:k]]=True; R.loc[idx,'bh']=bh
    print(f'BH H={H} fee={fee} tested={mt} clear={int((R.loc[idx,"p"]<.05).sum())} BH={k}',flush=True)

# match BH survivors + all priority-ish (tested with p small) — match all tested to be safe but memory: only BH + top by |ex|
need=set(R.id[R.bh | ((R.status=='tested')&(R.fee==30)&(R.H==5))])  # at least all 5d-30bp tested for pass bar; expand to all BH any H
need |= set(R.id[R.bh])
# also match all tested at 30bp for pass bar evaluation
need |= set(R.id[(R.status=='tested')&(R.fee==30)])
print('match need',len(need),flush=True)
for w in need:
    base=M[M[w]>0][['date','year','L5','px','b_atr','b_px','b_r1']+[f'f{H}_{fee}' for H in HS for fee in FEES]].copy()
    base['_c']=M.loc[base.index,w].values
    d0=base.dropna(subset=['b_atr','b_px','b_r1'])
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.fillna(False).values)]:
                m=do_match(d0[mask].dropna(subset=[col]),col,['date','b_atr','b_px','b_r1'])
                MATCH.append(dict(id=w,H=H,fee=fee,scope=sc,control='atr_px_r1',**m))
    print('match',w,flush=True)

MR=pd.DataFrame(MATCH); MR.to_csv('../2020_24_f4tr_matched.csv',index=False,float_format='%.6f')
for i in R.index[R.status=='tested']:
    m=MR[(MR.id==R.id[i])&(MR.H==R.H[i])&(MR.fee==R.fee[i])&(MR.scope=='all')]
    if len(m):
        m=m.iloc[0]; R.loc[i,'match_resid']=m.resid; R.loc[i,'match_lo']=m.lo; R.loc[i,'match_hi']=m.hi
        R.loc[i,'match_win']=m.win; R.loc[i,'match_signs']=m.signs; R.loc[i,'match_dates']=m.dates
def pass_row(r):
    if r.status!='tested' or r.fee!=30 or pd.isna(r.get('match_win',np.nan)): return False
    if not (r.match_win>0.5): return False
    if r.meaning in ('loud_bearish','quiet_warning'): return bool(r.match_hi<0)
    if r.meaning=='bullish': return bool(r.match_lo>0)
    return False
R['pass_bar']=R.apply(pass_row,axis=1)
R.to_csv('../2020_24_f4tr_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280)
print('PASS',R.pass_bar.sum())
print(R[R.pass_bar][['id','lens','H','fee','ex','match_resid','match_lo','match_hi','match_win','n_dates','n_events','signs']].round(5).to_string())
print(R[(R.bh)&(R.fee==30)].sort_values(['H','p'])[['id','meaning','lens','H','ex','n_dates','n_events','win_rate','signs','match_resid','match_win','pass_bar']].round(5).head(40).to_string())
print(R.status.value_counts()); print('non_sep',R[(R.H==5)&(R.fee==10)&R.non_separating].id.tolist())
