# FROZEN PRE-REGISTERED TEST (PRELOCK_ADDENDUM_00051.md), v5: sealed 2025-26 F4TR path + sha checks + early-run guards. Do not edit.
# Rule unchanged from v2 (PIT earn lookback + close>=$5). Window cut to signal dates ..2026-03-31 is by COVER_END NR (v4).
import os, sys, datetime as dt
LOCK=dt.datetime(2026,10,23,15,0,tzinfo=dt.timezone.utc)   # Fri 2026-10-23 23:00 HKT
if 'PRELOCK_YEARS' not in os.environ: sys.exit('HARD FAIL: set PRELOCK_YEARS (2020,2021,2022,2023,2024 = dry run; 2025,2026 = the locked test)')
YEARS=sorted(int(y) for y in os.environ['PRELOCK_YEARS'].split(','))
SEALED=any(y>=2025 for y in YEARS)
if SEALED and dt.datetime.now(dt.timezone.utc)<LOCK: sys.exit('HARD FAIL: 2025-26 is sealed until 2026-10-23 23:00 HKT')
if SEALED and YEARS!=[2025,2026]: sys.exit('HARD FAIL: locked test must be PRELOCK_YEARS=2025,2026')
import pandas as pd, numpy as np, pyarrow.parquet as pq, json, glob, gc, ast, hashlib
C='/workspace/checklist_brainstorm/engine/universe/chunks/'; W='OWN-TR-00051-C'
assert hashlib.sha256(open('/workspace/checklist_brainstorm/engine/out/tags/new-bot_earn_tags.csv','rb').read()).hexdigest().startswith('08f15079')
# v5 (2026-10-22): 2025-26 F4TR MUST come from Theme Radar's sealed tar, NOT engine/universe/chunks/ 2025/2026 F4TR.
SEALDIR='/workspace/data/f4tr/sealed_2025_26/'
SEAL_TAR=SEALDIR+'f4tr_chunks_2025_26.tar'
SEAL_TAR_SHA='d8ed17c3da40680831ea24e2a67d655e1e94e11e588a09550ed02c64f099b628'
F4TRDIR=C
if SEALED:
    import tarfile
    def _sha(f):
        h=hashlib.sha256()
        with open(f,'rb') as fh:
            for b in iter(lambda: fh.read(1<<20), b''): h.update(b)
        return h.hexdigest()
    if 'F4TRDIR' in os.environ: sys.exit('HARD FAIL: F4TRDIR override not allowed for the locked test; sealed set only')
    if not os.path.isfile(SEAL_TAR): sys.exit('HARD FAIL: sealed F4TR tar missing at '+SEAL_TAR)
    if _sha(SEAL_TAR)!=SEAL_TAR_SHA: sys.exit('HARD FAIL: sealed F4TR tar sha mismatch')
    XD=SEALDIR+'extracted/'
    if not os.path.isdir(XD):
        os.makedirs(XD); tarfile.open(SEAL_TAR).extractall(XD)
    ps=glob.glob(XD+'**/202[56]__F4TR__*.parquet',recursive=True)
    ds={os.path.dirname(x) for x in ps}
    if len(ds)!=1: sys.exit(f'HARD FAIL: sealed F4TR parquet not in one folder ({len(ds)})')
    F4TRDIR=ds.pop()+'/'
    # Refuse the older 2025/2026 F4TR sitting in the main chunks folder.
    if os.path.samefile(F4TRDIR, C) or F4TRDIR.rstrip('/')==C.rstrip('/'):
        sys.exit('HARD FAIL: sealed F4TR resolved to main chunks/; refusing older 2025/2026 F4TR')
    print('sealed F4TR set verified (tar sha); F4TRDIR =',F4TRDIR)
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
def load(kind,ids,base=None):
    root = (F4TRDIR if kind=='F4TR' and base is None else (base or C))
    X=[]
    for y in YEARS:
        for f in sorted(glob.glob(root+f'{y}__{kind}__*.parquet')):
            j=json.load(open(f[:-8]+'.json')); fid=j['ids'] if isinstance(j['ids'],list) else ast.literal_eval(j['ids']); ix=[fid.index(w) for w in ids]
            D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert str(min(YEARS))<=D.date.min()[:4] and D.date.max()<'2027-01-01'
            cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
            D['sector']=f.split('__')[-1][:-8]; X.append(pd.concat([D[['ticker','date','sector']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=ids)],axis=1))
    if not X: sys.exit(f'HARD FAIL: no {kind} chunks for YEARS={YEARS} under {root}')
    return pd.concat(X)
A=load('F4TR',[W]); YEARS0=YEARS
if os.path.exists(C+f'{min(YEARS)-1}__EARN__Technology.parquet'): YEARS=[min(YEARS)-1]+YEARS  # lookback warm-up only (prior-year earn calendar, no outcomes)
E=load('EARN',['nbx-EARN-POST1'],base=C).drop(columns='sector').sort_values(['ticker','date']); YEARS=YEARS0
# PIT (Manager): count reports on sessions D-29..D-1 only. POST1 YES on session t <=> report on session t-1 (any timing), so rolling 29 sessions of POST1 ending D.
# Signal-day reports excluded entirely: chunks cannot separate BMO from unknown on D (TODAY-BMOUNK mixes them) and AMC on D is not public by close.
E['rep30']=E.groupby('ticker')['nbx-EARN-POST1'].transform(lambda x:(x==2).astype(int).rolling(29,min_periods=1).max()); E=E[E.date>=str(min(YEARS))].drop(columns=['nbx-EARN-POST1']); J=load('JA_F4X',['SEC-JA-F4-182'],base=C).drop(columns='sector')
M=A.merge(E,on=['ticker','date'],how='left').merge(J,on=['ticker','date'],how='left')
F=pd.read_parquet('f4tr_frame_tmp.parquet') if False else None
R=pd.read_parquet('../multi_h_rets.parquet',columns=['ticker','date','f5_30','f20_30','f60_30'])
# Price window: dry-run ends before 2025; sealed warm-up from 2024-11-01, end before 2026-07-01 (v4: exits may run into early Apr 2026).
PX0,PX1=('2024-11-01','2026-07-01') if SEALED else ('2019-11-01','2025-01-01')
PXCUT='2025-01-01' if SEALED else '2020-01-01'
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','high','low','close','volume'],filters=[('date','>=',pd.Timestamp(PX0)),('date','<',pd.Timestamp(PX1))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d'); px=px.sort_values(['ticker','date']); g=px.groupby('ticker',sort=False); pc=g.close.shift(1)
tr=np.maximum(px.high,pc.fillna(px.high))-np.minimum(px.low,pc.fillna(px.low))
px['atrp']=tr.groupby(px.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=15).mean())/px.close; px['r1']=px.close/pc-1; px['dv']=(px.close*px.volume).groupby(px.ticker,sort=False).transform(lambda x:x.rolling(20,min_periods=10).mean().shift(1))
px=px[px.date>=PXCUT][['ticker','date','atrp','close','r1','dv']]
M=M.merge(px,on=['ticker','date']).merge(R,on=['ticker','date']); del px,R,A,E; gc.collect()
for col,q,nm in [('atrp',5,'ba'),('close',5,'bp'),('r1',10,'br')]:
    M[nm]=M.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
M=M[M[W]>0].dropna(subset=['ba','bp','br']).sort_values(['ticker','date']).reset_index(drop=True)
y=M[W]==2; M['start']=y&~y.groupby(M.ticker).shift(1,fill_value=False)
M['dvt']=M.groupby('date').dv.transform(lambda v: pd.qcut(v.rank(method='first'),3,labels=False) if v.notna().sum()>=9 else np.nan); M['j182']=M['SEC-JA-F4-182']==2
M['year']=M.date.str[:4]
K=['date','ba','bp','br']
def res(sel,col):
    c=M[M[W]==1].groupby(K)[col].mean().rename('cm').reset_index()
    Y=M[sel&M[col].notna()].merge(c,on=K)
    if len(Y)<5: return dict(n=len(Y))
    r=Y[col]-Y.cm; m=r.mean(); e=(r-m).groupby(Y.date).sum(); se=np.sqrt((e**2).sum())/len(r)
    s=r.groupby(Y.year).mean(); yrs=range(YEARS[0],YEARS[-1]+1)
    return dict(n=len(Y),tickers=Y.ticker.nunique(),dates=Y.date.nunique(),resid=m,lo=m-1.96*se,hi=m+1.96*se,win=(r>0).mean(),signs=''.join('+' if s.get(str(k),0)>0 else ('-' if str(k) in s.index else '.') for k in yrs))
ev=M[M.start]; first=ev.groupby('ticker').head(1).index
top10=ev.ticker.value_counts().head(10)
print('YES days',int(y.sum()),'events',len(ev),'distinct tickers',ev.ticker.nunique()); print('top10',top10.to_dict())
# FROZEN PRE-REGISTERED TEST (PRELOCK_ADDENDUM_00051.md). Do not edit.
sel=M.start&(M.rep30==1)&(M.close>=5)
d=res(pd.Series(sel,index=M.index),'f5_30')
d['PASS']=bool(d.get('win',0)>0.5 and d.get('resid',0)>0 and d.get('lo',-1)>0)
print(d); pd.DataFrame([d]).to_csv('prelock_00051_result_'+'_'.join(map(str,YEARS))+'.csv',index=False)
