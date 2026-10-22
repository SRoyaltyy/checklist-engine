import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; LCUT=0.6205
TAG=pd.read_csv('/workspace/checklist_brainstorm/engine/out/attention/attention_tags.csv')
sha=__import__('hashlib').sha256(open('/workspace/checklist_brainstorm/engine/out/attention/attention_tags.csv','rb').read()).hexdigest()
assert sha=='5ae130fb854880bfac91755e78771ceaf87986361cab681bb42032f0b4bbdf9a', sha
print('tags_ok',sha,flush=True)
COLS=['theme-radar-attn|'+i for i in TAG.id]; IDS=list(TAG.id)
# load ATTN (wide int cols, not packed)
X=[]
for y in range(2020,2025):
    P=[]
    for f in sorted(glob.glob(C+f'{y}__ATTN__*.parquet')):
        D=pd.read_parquet(f,columns=['ticker','date']+COLS); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        D['ticker']=D.ticker.astype(str); P.append(D)
    X.append(pd.concat(P)); print('attn',y,len(X[-1]),flush=True); del P; gc.collect()
A=pd.concat(X); A=A.rename(columns={c:i for c,i in zip(COLS,IDS)}); del X; gc.collect()
# earn calendar days for combo
EW=['nbx-EARN-TODAY-BMOUNK','nbx-EARN-POST1','nbx-EARN-NEXT5','nbx-EARN-LAST5']
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
EX=[]
for y in range(2020,2025):
    P=[]; 
    for f in sorted(glob.glob(C+f'{y}__EARN__*.parquet')):
        j=json.load(open(f[:-8]+'.json')); fid=j['ids']; ix=[fid.index(w) for w in EW]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=EW)],axis=1)); del D
    EX.append(pd.concat(P)); print('earn',y,flush=True)
E=pd.concat(EX); del EX; gc.collect()
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
Rets=pd.read_parquet('../multi_h_rets.parquet')
# features for match
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','high','low','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
px=px.sort_values(['ticker','date']); g=px.groupby('ticker',sort=False); pc=g.close.shift(1)
tr=np.maximum(px.high,pc.fillna(px.high))-np.minimum(px.low,pc.fillna(px.low))
px['atrp']=tr.groupby(px.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/px.close
px['r1']=px.close/pc-1; px['px']=px.close
px=px[px.date>='2020-01-01'][['ticker','date','atrp','px','r1']]
ST=pd.concat([pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']).assign(ticker=lambda d:d.ticker.astype(str),date=lambda d:d.date.astype(str).str[:10]) for y in range(2020,2025)]).drop_duplicates(['ticker','date'])
M=A.merge(E,on=['ticker','date'],how='left').merge(px,on=['ticker','date'],how='left').merge(ST,on=['ticker','date'],how='left').merge(Rets,on=['ticker','date'])
del A,E,px,ST,Rets; gc.collect()
M['L5']=M.lean>=LCUT; M['year']=M.date.str[:4]
for col,q,nm in [('atrp',5,'b_atr'),('px',5,'b_px'),('r1',10,'b_r1')]:
    M[nm]=M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
# combos: attention spike (b3/b1 spike rows) INTO earn days
SPIKE=['tr-attn-01-SPIKE15','tr-attn-02-SPIKE30','tr-attn-03-SURGE3D','tr-attn-05-PCTL252']  # b3/b1 spike-ish
M['earn_day']=(M[EW]==2).any(axis=1)
for s in SPIKE:
    M[f'{s}|EARN']=(M[s]==2)&M.earn_day
M=M.sort_values(['ticker','date']).reset_index(drop=True)
M.to_parquet('attn_frame.parquet'); print('saved',M.shape,flush=True)
meaning=dict(zip(TAG.id,TAG.meaning)); bucket=dict(zip(TAG.id,TAG.bucket))
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
signals=[]
for i in IDS:
    yes=M[i]==2; ready=M[i]>0; signals.append((i,'row',yes,ready,meaning[i]))
for s in SPIKE:
    sid=f'{s}|EARN'; yes=M[sid]; ready=M.earn_day | (M[s]>0); signals.append((sid,'combo',yes,ready,'quiet_warning'))
for sid,kind,yes,ready,mean in signals:
    nev=events(yes); yr=yes.sum()/ready.sum() if ready.sum() else np.nan
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'; dm=M.groupby('date')[col].transform('mean')
            d=M.loc[yes & M[col].notna(), ['date','year','L5',col]].copy(); d['ex']=d[col]-dm.loc[d.index]
            nd=int(d.date.nunique())
            r=dict(id=sid,kind=kind,meaning=mean,H=H,fee=fee,yes_rate=yr,n_dates=nd,n_events=nev,n_obs=len(d),win_rate=float((d[col]>0).mean()) if len(d) else np.nan)
            if nd<30: r['status']='too_few_dates'; rows.append(r); continue
            m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
            r.update(status='tested',ex=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values)); rows.append(r)
    print('scored',sid,int(yes.sum()),nev,flush=True)
R=pd.DataFrame(rows); R['bh']=False
for (H,fee),idx in R[R.status=='tested'].groupby(['H','fee']).groups.items():
    p=R.loc[idx,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05
    k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0; bh=np.zeros(mt,bool); bh[o[:k]]=True; R.loc[idx,'bh']=bh
    print(f'BH H={H} fee={fee} tested={mt} BH={k}',flush=True)
for sid,kind,yes,ready,mean in signals:
    base=M[ready][['date','year','L5','px','b_atr','b_px','b_r1']+[f'f{H}_{fee}' for H in HS for fee in FEES]].copy()
    base['_c']=np.where(yes.loc[base.index],2,1)
    d0=base.dropna(subset=['b_atr','b_px','b_r1'])
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.fillna(False).values)]:
                m=do_match(d0[mask].dropna(subset=[col]),col,['date','b_atr','b_px','b_r1']); MATCH.append(dict(id=sid,H=H,fee=fee,scope=sc,**m))
    print('match',sid,flush=True)
MR=pd.DataFrame(MATCH); MR.to_csv('../2020_24_attn_matched.csv',index=False,float_format='%.6f')
for i in R.index[R.status=='tested']:
    m=MR[(MR.id==R.id[i])&(MR.H==R.H[i])&(MR.fee==R.fee[i])&(MR.scope=='all')]
    if len(m):
        m=m.iloc[0]; R.loc[i,'match_resid']=m.resid; R.loc[i,'match_lo']=m.lo; R.loc[i,'match_hi']=m.hi; R.loc[i,'match_win']=m.win; R.loc[i,'match_signs']=m.signs; R.loc[i,'match_dates']=m.dates
def pass_row(r):
    if r.status!='tested' or r.fee!=30 or pd.isna(r.get('match_win',np.nan)): return False
    if not (r.match_win>0.5): return False
    if r.meaning in ('quiet_warning','loud_bearish') or str(r.id).endswith('|EARN'): return bool(r.match_hi<0)
    if r.meaning=='bullish': return bool(r.match_lo>0)
    return False
R['pass_bar']=R.apply(pass_row,axis=1)
R.to_csv('../2020_24_attn_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280)
print(R.sort_values(['kind','H','fee','p'])[['id','kind','meaning','H','fee','ex','lo95','hi95','n_dates','n_events','win_rate','bh','signs','match_resid','match_lo','match_hi','match_win','pass_bar']].round(5).to_string())
print('PASS',R[R.pass_bar][['id','H','fee','match_resid','match_win','n_dates','n_events']].to_string())
