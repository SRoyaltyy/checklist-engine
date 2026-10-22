# FROZEN PRE-REGISTERED TEST (PRELOCK_ADDENDUM_OHLCV6.md), v6.1: sealed 2025-26 NB path + sha checks only. Do not edit. Supersedes prelock_ohlcv7.py (NB-026 T1-THR merged into UP10_DAY per Manager 2026-10-22).
# 6 skip/trim warnings, event start, entry open D+1, exit open D+21 (20-session hold), 30bp/side, close>=$2,
# matched control = ready-NO stock-days in the same date x price quintile x ATR% quintile x prior-1d decile.
# PASS per row: BH(q=0.05, these 6) significant AND mean<0 AND 95% CI high<0. Judged once.
import os, sys, json, glob, datetime as dt
LOCK=dt.datetime(2026,10,23,15,0,tzinfo=dt.timezone.utc)   # Fri 2026-10-23 23:00 HKT
if 'PRELOCK_YEARS' not in os.environ: sys.exit('HARD FAIL: set PRELOCK_YEARS (2020,2021,2022,2023,2024 = dry run; 2025,2026 = the locked test)')
YEARS=sorted(int(y) for y in os.environ['PRELOCK_YEARS'].split(','))
SEALED=any(y>=2025 for y in YEARS)
if SEALED and dt.datetime.now(dt.timezone.utc)<LOCK: sys.exit('HARD FAIL: 2025-26 is sealed until 2026-10-23 23:00 HKT')
if SEALED and YEARS!=[2025,2026]: sys.exit('HARD FAIL: locked test must be PRELOCK_YEARS=2025,2026')
import pandas as pd, numpy as np
from scipy.stats import norm
PRICE=os.environ.get('PRICE','/workspace/pricehist/universe_2020_survivors.parquet')
DIVS=os.environ.get('DIVS','/workspace/pricehist/dividends_2020.parquet')
NBDIR=os.environ.get('NBDIR','/workspace/data/nb_v2/chunks/')
# v6.1 (2026-10-22): 2025-26 NB MUST come from New Bot's sealed set, NOT /workspace/data/nb_v2/chunks/ (2025/2026 files there were built to 10-21).
SEALDIR='/workspace/data/nb_v2/sealed_2025_2026H1/'
SEAL_TAR=SEALDIR+'nb_sealed_2025_2026H1.tar.xz'
SEAL_TAR_SHA='e53a896047f13284652eefb6251a5964b6d754103110980ecb592a7d1a3d7506'
SEAL_MANIFEST='MANIFEST_nb_sealed_2025_2026H1.sha256'
SEAL_MANIFEST_SHA='784e00ac3cfa6513958ab65bce4ffb71ec59b1d1c334e0d0f8ac2ab0420b6e45'
if SEALED:
    import hashlib, tarfile, subprocess
    def _sha(f):
        h=hashlib.sha256()
        with open(f,'rb') as fh:
            for b in iter(lambda: fh.read(1<<20), b''): h.update(b)
        return h.hexdigest()
    if 'NBDIR' in os.environ: sys.exit('HARD FAIL: NBDIR override not allowed for the locked test; sealed set only')
    if _sha(SEAL_TAR)!=SEAL_TAR_SHA: sys.exit('HARD FAIL: sealed NB tar sha mismatch')
    XD=SEALDIR+'extracted/'
    if not os.path.isdir(XD):
        os.makedirs(XD); tarfile.open(SEAL_TAR).extractall(XD)
    ms=glob.glob(XD+'**/'+SEAL_MANIFEST,recursive=True)
    if len(ms)!=1: sys.exit(f'HARD FAIL: expected exactly 1 {SEAL_MANIFEST} in sealed set, found {len(ms)}')
    if _sha(ms[0])!=SEAL_MANIFEST_SHA: sys.exit('HARD FAIL: sealed NB manifest sha mismatch')
    MD=os.path.dirname(ms[0])
    r=subprocess.run(['sha256sum','--check','--strict','--quiet',SEAL_MANIFEST],cwd=MD)
    if r.returncode!=0: sys.exit('HARD FAIL: sealed NB files do not match manifest')
    ps=glob.glob(XD+'**/202[56]__NB__*.parquet',recursive=True)
    ds={os.path.dirname(x) for x in ps}
    if len(ds)!=1: sys.exit(f'HARD FAIL: sealed NB parquet not in one folder ({len(ds)})')
    NBDIR=ds.pop()+'/'
    print('sealed NB set verified (tar + manifest + files); NBDIR =',NBDIR,'(NB-026 rows ignored)')
SNAP='/workspace/snap_2026-09-29.csv'
FEE=0.006; H=20; MINPX=2.0
W0,W1=('2025-01-01','2026-06-30') if SEALED else (f'{YEARS[0]}-01-01',f'{YEARS[-1]}-12-31')
RD0=f'{int(W0[:4])-1}-09-01'; RD1='2026-08-15' if SEALED else f'{YEARS[-1]+1}-01-01'
snap=pd.read_csv(SNAP,usecols=['Ticker','Industry'])
funds=set(snap.Ticker[snap.Industry.fillna('').str.match(r'^(Exchange Traded Fund|Closed-End Fund|Shell Companies)')])
import pyarrow.parquet as pq
A=pq.read_table(PRICE,columns=['ticker','date','open','high','low','close','volume'],filters=[('date','>=',pd.Timestamp(RD0)),('date','<',pd.Timestamp(RD1))]).to_pandas()
A['ticker']=A.ticker.astype(str); A=A[~A.ticker.isin(funds)]; A['date']=A.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet(DIVS); dv['ticker']=dv.ticker.astype(str); dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d'); dv=dv[(dv.date>=RD0)&(dv.date<RD1)]
dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=A.merge(dv,on=['ticker','date'],how='left').drop_duplicates(['ticker','date']).sort_values(['ticker','date']).reset_index(drop=True)
for c in ['open','high','low','close','volume']: A[c]=A[c].astype('float64')
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open)
T=A.ticker; g=A.groupby('ticker',sort=False); O,Hh,L,C,V=A.open,A.high,A.low,A.close,A.volume
A['cd']=g['div'].cumsum(); cdg=A.groupby('ticker',sort=False).cd
r=(g.open.shift(-(1+H))+cdg.shift(-(1+H))-cdg.shift(-1))/g.open.shift(-1)-1; r[r.abs()>2]=np.nan; A['ret']=r
def sh(s,k=1): return s.groupby(T,sort=False).shift(k)
def roll(s,n,f,mp=None): return s.groupby(T,sort=False).transform(lambda x:getattr(x.rolling(n,min_periods=mp or n),f)())
pc=sh(C); tr=np.maximum(Hh,pc.fillna(Hh))-np.minimum(L,pc.fillna(L))
A['atrp']=roll(tr,20,'mean',15)/C; A['r1']=C/pc-1
lr=np.log(C/pc); A['rv']=roll(lr,10,'std')/roll(lr,60,'std')
A['rvol']=V/sh(roll(V,50,'mean',40)); A['gap']=O/pc-1
tp=(Hh+L+C)/3; mf=tp*V; pos=mf.where(tp>sh(tp),0); neg=mf.where(tp<sh(tp),0)
A['mfi']=100*roll(pos,14,'sum')/(roll(pos,14,'sum')+roll(neg,14,'sum')).replace(0,np.nan)
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
NBW=['nb4-HIS-NB-029-P5-POSQ']; P=[]
for y in YEARS:
    fs=sorted(glob.glob(NBDIR+f'{y}__NB__*.parquet'))
    if not fs: sys.exit(f'HARD FAIL: no NB chunks for {y} in {NBDIR}')
    for f in fs:
        fid=json.load(open(f[:-8]+'.json'))['ids']; ix=[fid.index(w) for w in NBW]
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=NBW)],axis=1))
A=A.merge(pd.concat(P).drop_duplicates(['ticker','date']),on=['ticker','date'],how='left')
A=A.sort_values(['ticker','date']).reset_index(drop=True); T=A.ticker
def ready(c): return A[c].notna()
ROWS={'VOLJUMP_RV10_60>2':(A.rv>2,ready('rv')),'RVOL>=5':(A.rvol>=5,ready('rvol')),'UP10_DAY':(A.r1>=.10,ready('r1')),
 'NB-029-P5-POSQ':(A[NBW[0]]==2,A[NBW[0]].isin([1,2])),
 'GAPDOWN<=-5%':(A.gap<=-.05,ready('gap')),'MFI>80':(A.mfi>80,ready('mfi'))}
A=A[(A.date>=W0)&(A.date<=W1)].copy()
def bk(col,q): return A.groupby('date')[col].transform(lambda s: pd.qcut(s.rank(method='first'),q,labels=False) if s.notna().sum()>=q*3 else np.nan)
A['b_px']=bk('close',5); A['b_atr']=bk('atrp',5); A['b_r1']=bk('r1',10)
idx=A.index; okc=A[['b_px','b_atr','b_r1']].notna().all(1)&A.ret.notna()
cell=A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values; nc=cell.max()+1
out=[]
for k,(y,rd) in ROWS.items():
    y_full=y.fillna(False).astype(bool); start=y_full&~y_full.groupby(T).shift(1,fill_value=False)
    y=y_full.loc[idx].values; rd=rd.loc[idx].values&okc.values; st=start.loc[idx].values
    no=rd&~y; ret=A.ret.values; s=np.bincount(cell[no],ret[no],nc); n=np.bincount(cell[no],minlength=nc)
    sel=st&rd&(A.close.values>=MINPX)&(n[cell]>0); i=np.where(sel)[0]
    e=ret[i]-s[cell[i]]/n[cell[i]]; m=e.mean(); d_=pd.Series(e-m).groupby(A.date.values[i]).sum(); se=np.sqrt((d_**2).sum())/len(e)
    out.append(dict(row=k,n_events=len(i),n_dates=len(np.unique(A.date.values[i])),n_tickers=len(np.unique(A.ticker.values[i])),mean=m,lo95=m-1.96*se,hi95=m+1.96*se,p=2*norm.sf(abs(m/se)),
        win_short_after_fee=((-ret[i]-FEE)>0).mean()))
R=pd.DataFrame(out); p=R.p.values; o=np.argsort(p); th=p[o]<=0.05*np.arange(1,len(p)+1)/len(p); bh=np.zeros(len(p),bool)
if th.any(): bh[o[:np.where(th)[0].max()+1]]=True
R['bh']=bh; R['PASS']=R.bh&(R['mean']<0)&(R.hi95<0)
tag='2025_26' if SEALED else 'dryrun_'+'_'.join(map(str,YEARS))
R.to_csv(f'prelock_ohlcv6_result_{tag}.csv',index=False,float_format='%.6f'); print(R.to_string())
