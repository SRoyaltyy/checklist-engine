import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; LCUT=0.6205
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
TAG=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/new-bot_earn_tags.csv')
# AMC-YDAY all NR — skip; use POST1 for post-print
W=[r for r in TAG.row_id if r!='nbx-EARN-AMC-YDAY']
assert open('/workspace/checklist_brainstorm/engine/out/tags/new-bot_earn_tags.csv.sha256').read().split()[0]=='08f1507923fd2e5289bd0d427c737168b543687306bee82f7e6fe2b80ebe42cc' or True
sha=__import__('hashlib').sha256(open('/workspace/checklist_brainstorm/engine/out/tags/new-bot_earn_tags.csv','rb').read()).hexdigest()
assert sha=='08f1507923fd2e5289bd0d427c737168b543687306bee82f7e6fe2b80ebe42cc', sha
print('tags_ok',sha,flush=True)
# load earn answers
X=[]
for y in range(2020,2025):
    P=[]
    for f in sorted(glob.glob(C+f'{y}__EARN__*.parquet')):
        j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids'])
        ix=[fid.index(w) for w in W]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=W)],axis=1)); del D
    X.append(pd.concat(P)); print('earn',y,flush=True); gc.collect()
E=pd.concat(X); del X; gc.collect()
# b3/b4 across sources
B=[]
for y in range(2020,2025):
    parts=[]
    for src in ['STK','TR','NB','NBX']:
        fs=sorted(glob.glob(C+f'{y}__BUCKETS7_{src}__*.parquet'))
        for f in fs:
            try:
                if __import__('os').path.getsize(f)<100: continue
                parts.append(pd.read_parquet(f,columns=['ticker','date','b3_yes','b4_yes']))
            except Exception as e:
                print('skip',f,e,flush=True)
    if not parts:
        print('no b3',y,flush=True); continue
    b=pd.concat(parts); b['ticker']=b.ticker.astype(str); b['date']=b.date.astype(str).str[:10]
    b=b.groupby(['ticker','date'],as_index=False).agg(b3_yes=('b3_yes','sum'),b4_yes=('b4_yes','sum'))
    b['b3']=b.b3_yes>0; b['b4']=b.b4_yes>0; B.append(b[['ticker','date','b3','b4']])
    print('b',y,flush=True); del parts,b; gc.collect()
B=pd.concat(B)
# lean + prior 20d return for rally
snap=pd.read_csv('/workspace/snap_2026-09-29.csv',usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px=px[~px.ticker.isin(funds)]; px['date']=px.date.dt.strftime('%Y-%m-%d')
px=px.sort_values(['ticker','date']); px['prior20']=px.groupby('ticker').close.pct_change(20)
px=px[px.date>='2020-01-01'][['ticker','date','prior20','close']]
# states lean
ST=[]
for y in range(2020,2025):
    st=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']); st['ticker']=st.ticker.astype(str); st['date']=st.date.astype(str).str[:10]
    ST.append(st)
ST=pd.concat(ST).drop_duplicates(['ticker','date'])
Rets=pd.read_parquet('../multi_h_rets.parquet')
M=E.merge(B,on=['ticker','date'],how='left').merge(px,on=['ticker','date'],how='left').merge(ST,on=['ticker','date'],how='left').merge(Rets,on=['ticker','date'])
del E,B,px,ST,Rets; gc.collect()
M['b3']=M.b3.fillna(False); M['b4']=M.b4.fillna(False); M['L5']=M.lean>=LCUT; M['year']=M.date.str[:4]
# rally = prior 20d return in top same-date quintile
M['b_r20']=M.groupby('date').prior20.transform(lambda s: pd.qcut(s.rank(method='first'),5,labels=False) if s.notna().sum()>=15 else np.nan)
M['rally']=M.b_r20==4
# match buckets
for col,q,nm in [('atrp_dummy',5,'x')]: pass
# need atr/px/r1 for match — from multi path rebuild light
# use close-based proxies already in rets file? rebuild quick features
print('building match feats',flush=True)
px2=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open','high','low','close'],filters=[('date','>=',pd.Timestamp('2019-11-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px2['ticker']=px2.ticker.astype(str); px2=px2[~px2.ticker.isin(funds)]; px2['date']=px2.date.dt.strftime('%Y-%m-%d')
px2=px2.sort_values(['ticker','date']); g=px2.groupby('ticker',sort=False); pc=g.close.shift(1)
tr=np.maximum(px2.high,pc.fillna(px2.high))-np.minimum(px2.low,pc.fillna(px2.low))
px2['atrp']=tr.groupby(px2.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/px2.close
px2['r1']=px2.close/pc-1; px2['px']=px2.close
px2=px2[px2.date>='2020-01-01'][['ticker','date','atrp','px','r1']]
M=M.merge(px2,on=['ticker','date'],how='left'); del px2; gc.collect()
for col,q,nm in [('atrp',5,'b_atr'),('px',5,'b_px'),('r1',10,'b_r1')]:
    M[nm]=M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
M=M.sort_values(['ticker','date']).reset_index(drop=True)
# patterns
M['P1']=(M['nbx-EARN-NEXT5']==2)&M.rally&M.b3  # rally+overbought into earnings
M['P2']=(M['nbx-EARN-NEXT5']==2)&M.b3&M.b4      # overbought + momentum dying into earnings
# also TODAY-BMOUNK and POST1 variants of patterns? stick to NEXT5 as "before known earnings"
print(M[['P1','P2']].sum(), flush=True)
M.to_parquet('earn_frame.parquet'); print('saved',M.shape,flush=True)

meaning=dict(zip(TAG.row_id,TAG.meaning))
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
    # for patterns, control = same date/buckets but pattern false; for earn rows control = ready NO
    c=d[d['_c']==0].groupby(keys)[retcol].mean().rename('cm').reset_index() if d['_c'].isin([0,1]).all() else d[d['_c']==1].groupby(keys)[retcol].mean().rename('cm').reset_index()
    # unify: _c 2=yes/treat, 1=control pool (ready no or not-pattern)
    c=d[d['_c']==1].groupby(keys)[retcol].mean().rename('cm').reset_index(); Y=d[d['_c']==2].merge(c,on=keys)
    if len(Y)<2: return dict(resid=np.nan,lo=np.nan,hi=np.nan,dates=0,obs=0,signs='',win=np.nan)
    res=(Y[retcol]-Y.cm).values; m,lo,hi=cl(res,Y.date.values)
    return dict(resid=m,lo=lo,hi=hi,dates=int(Y.date.nunique()),obs=len(Y),signs=signs(res,Y.year.values),win=float((res>0).mean()))

rows=[]; MATCH=[]
signals=[(w,'row',M[w]==2,M[w]>0) for w in W]+[('NFLX-P1-rally-ob-into-earn','pattern',M.P1,M['nbx-EARN-NEXT5']>0),('NFLX-P2-ob-qw-into-earn','pattern',M.P2,M['nbx-EARN-NEXT5']>0)]
for sid,kind,yes,ready in signals:
    nev=events(yes); yr=yes.sum()/ready.sum() if ready.sum() else np.nan
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'; dm=M.groupby('date')[col].transform('mean')
            d=M.loc[yes & M[col].notna(), ['ticker','date','year','L5','px','b_atr','b_px','b_r1',col]].copy(); d['ex']=d[col]-dm.loc[d.index]
            nd=int(d.date.nunique())
            r=dict(id=sid,kind=kind,meaning=meaning.get(sid,'bearish' if 'P' in sid else ''),H=H,fee=fee,yes_rate=yr,n_dates=nd,n_events=nev,n_obs=len(d),
                   win_rate=float((d[col]>0).mean()) if len(d) else np.nan)
            if nd<30: r['status']='too_few_dates'; rows.append(r); continue
            m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
            r.update(status='tested',ex=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
            rows.append(r)
    print('scored',sid,int(yes.sum()),nev,flush=True)

R=pd.DataFrame(rows); R['bh']=False
for (H,fee),idx in R[R.status=='tested'].groupby(['H','fee']).groups.items():
    p=R.loc[idx,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05
    k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0; bh=np.zeros(mt,bool); bh[o[:k]]=True; R.loc[idx,'bh']=bh
    print(f'BH H={H} fee={fee} tested={mt} BH={k}',flush=True)

# matched for all tested
for sid,kind,yes,ready in signals:
    # control pool: ready & ~yes → code 1; yes → 2
    base=M[ready][['date','year','L5','px','b_atr','b_px','b_r1']+[f'f{H}_{fee}' for H in HS for fee in FEES]].copy()
    base['_c']=np.where(yes.loc[base.index],2,1)
    d0=base.dropna(subset=['b_atr','b_px','b_r1'])
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.values),('px2',(d0.px>=2).values)]:
                m=do_match(d0[mask].dropna(subset=[col]),col,['date','b_atr','b_px','b_r1'])
                MATCH.append(dict(id=sid,H=H,fee=fee,scope=sc,control='atr_px_r1',**m))
    print('match',sid,flush=True)

MR=pd.DataFrame(MATCH); MR.to_csv('../2020_24_earn_nflx_matched.csv',index=False,float_format='%.6f')
for i in R.index[R.status=='tested']:
    m=MR[(MR.id==R.id[i])&(MR.H==R.H[i])&(MR.fee==R.fee[i])&(MR.scope=='all')]
    if len(m):
        m=m.iloc[0]; R.loc[i,'match_resid']=m.resid; R.loc[i,'match_lo']=m.lo; R.loc[i,'match_hi']=m.hi; R.loc[i,'match_win']=m.win; R.loc[i,'match_signs']=m.signs; R.loc[i,'match_dates']=m.dates
def pass_row(r):
    if r.status!='tested' or r.fee!=30 or pd.isna(r.get('match_win',np.nan)): return False
    if not (r.match_win>0.5): return False
    # NFLX patterns tagged as tops/warnings → expect negative residual
    if str(r.id).startswith('NFLX') or r.meaning in ('quiet_warning','loud_bearish'):
        return bool(r.match_hi<0)
    if r.meaning=='bullish': return bool(r.match_lo>0)
    return False
R['pass_bar']=R.apply(pass_row,axis=1)
R.to_csv('../2020_24_earn_nflx_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280)
print(R.sort_values(['kind','H','fee','p'])[['id','kind','meaning','H','fee','ex','lo95','hi95','n_dates','n_events','win_rate','p','bh','signs','match_resid','match_lo','match_hi','match_win','pass_bar']].round(5).to_string())
print('PASS\n',R[R.pass_bar][['id','H','fee','match_resid','match_win','n_dates','n_events','signs']].to_string())
