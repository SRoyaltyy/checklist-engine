import pandas as pd, numpy as np, json, glob, gc, ast
from scipy.stats import norm
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
TAG=pd.read_csv('/workspace/checklist_brainstorm/engine/out/tags/james_f4_tags.csv')
W=list(TAG.row_id); meaning=dict(zip(TAG.row_id,TAG.meaning)); lens=dict(zip(TAG.row_id,TAG.lens))
PRIORITY=['SEC-JA-166','SEC-JA-166-BUT','SEC-JA-167','SEC-JA-167-BUT','SEC-JA-168','SEC-JA-168-BUT','SEC-JA-169','SEC-JA-169-BUT','SEC-JA-F4-182']
BUY=['SEC-JA-166','SEC-JA-167','SEC-JA-168','SEC-JA-169','SEC-JA-F4-182']
# load answers from existing frame + F4X
M=pd.read_parquet('f4/f4_frame.parquet', columns=['ticker','date','year','L5','px','b_atr','b_px','b_r1']+list(TAG.row_id))
# attach 182
X=[]
for y in range(2020,2025):
    P=[]
    for f in sorted(glob.glob(C+f'{y}__JA_F4X__*.parquet')):
        D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
        cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),1)
        P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=['SEC-JA-F4-182'])],axis=1)); del D
    X.append(pd.concat(P)); print('182',y,flush=True)
A182=pd.concat(X); M=M.merge(A182,on=['ticker','date'],how='left'); M['SEC-JA-F4-182']=M['SEC-JA-F4-182'].fillna(0).astype('int8'); del A182,X; gc.collect()
# bucket3 yes across sources
B3=[]
for y in range(2020,2025):
    parts=[]
    for src in ['STK','TR','NB','NBX']:
        fs=sorted(glob.glob(C+f'{y}__BUCKETS7_{src}__*.parquet'))
        if not fs: continue
        parts.append(pd.concat([pd.read_parquet(f,columns=['ticker','date','b3_yes']) for f in fs]))
    if not parts: continue
    b=pd.concat(parts); b['ticker']=b.ticker.astype(str); b['date']=b.date.astype(str).str[:10]
    b=b.groupby(['ticker','date'],as_index=False).b3_yes.sum(); b['b3']=b.b3_yes>0; B3.append(b[['ticker','date','b3']])
    print('b3',y,flush=True); del parts,b; gc.collect()
B3=pd.concat(B3); M=M.merge(B3,on=['ticker','date'],how='left'); M['b3']=M.b3.fillna(False); del B3; gc.collect()
Rets=pd.read_parquet('multi_h_rets.parquet'); M=M.merge(Rets,on=['ticker','date']); del Rets; gc.collect()
M=M.sort_values(['ticker','date']).reset_index(drop=True)
print('frame',M.shape,flush=True)

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

HS=(5,20,60); FEES=(10,30)
rows=[]; MATCH=[]
# score each row × horizon × fee (raw same-date edge uses exH which is 10bp-demeaned; for 30bp adjust)
ALL=W+['SEC-JA-F4-182']
for w in ALL:
    rd=M[w]>0; yes=M[w]==2; nd=int(M.loc[yes,'date'].nunique()); yr=yes.sum()/rd.sum() if rd.sum() else np.nan
    base=dict(id=w,meaning=meaning.get(w,'bullish'),lens=lens.get(w,'Timeframe'),yes_rate=yr,non_separating=bool(yr>0.5) if rd.sum() else False,
              n_dates=nd,n_events=events(yes),n_obs=int(yes.sum()),years=''.join(str(y)[-1] if ((M.year==str(y))&(M[w]>0)).any() else '.' for y in range(2020,2025)))
    for H in HS:
        d=M[yes & M[f'f{H}_10'].notna()]
        if d.date.nunique()<30:
            rows.append({**base, 'H':H,'fee':10,'status':'too_few_dates'}); continue
        for fee in FEES:
            col=f'f{H}_{fee}'; # same-date edge: ret minus date mean of same fee-adjusted return
            ex=d[col]-d.groupby('date')[col].transform('mean')  # wait d is only YES — need full date mean
        # redo properly using precomputed ex for 10bp; for 30bp compute from full M
    print('raw',w,nd,flush=True)

# cleaner loop
rows=[]; MATCH=[]
for w in ALL:
    rd=M[w]>0; yes=M[w]==2; nd0=int(M.loc[yes,'date'].nunique()); yr=yes.sum()/rd.sum() if rd.sum() else np.nan
    nev=events(yes)
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'
            # date mean over all stocks
            dm=M.groupby('date')[col].transform('mean')
            d=M.loc[yes & M[col].notna(), ['ticker','date','year','L5','px','b_atr','b_px','b_r1',col]].copy()
            d['ex']=d[col]-dm.loc[d.index]
            nd=int(d.date.nunique())
            r=dict(id=w,meaning=meaning.get(w,'bullish'),lens=lens.get(w,'Timeframe'),H=H,fee=fee,yes_rate=yr,non_separating=bool(yr>0.5) if rd.sum() else False,
                   n_dates=nd,n_events=nev,n_obs=len(d),win_rate=float((d[col]>0).mean()) if len(d) else np.nan)
            if nd<30:
                r['status']='too_few_dates'; rows.append(r); continue
            m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
            r.update(status='tested',ex=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
            l=d[d.L5]
            if l.date.nunique()>=2:
                # L5 baseline
                Lall=M.loc[M.L5 & M[col].notna(), ['date',col]].copy(); Lall['ex']=Lall[col]-M.groupby('date')[col].transform('mean').loc[Lall.index]
                lb=Lall.ex.mean(); lm,llo,lhi=cl(l.ex.values,l.date.values)
                r.update(L5_minus_L5all=lm-lb,L5_lo95=llo-lb,L5_hi95=lhi-lb,L5_dates=int(l.date.nunique()),L5_win=float((l[col]>0).mean()))
            rows.append(r)
    print('scored',w,flush=True)

# matched price×swing (atr×px×r1) for priority + BH survivors
need=set(PRIORITY)|set(ALL)
for w in need:
    base=M[M[w]>0][['date','year','L5','px','b_atr','b_px','b_r1']+[f'f{H}_{fee}' for H in HS for fee in FEES]].copy(); base['_c']=M.loc[base.index,w].values
    d0=base.dropna(subset=['b_atr','b_px','b_r1'])
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'
            for sc,mask in [('all',np.ones(len(d0),bool)),('L5',d0.L5.values),('px2',(d0.px>=2).values)]:
                m=do_match(d0[mask].dropna(subset=[col]), col, ['date','b_atr','b_px','b_r1'])
                MATCH.append(dict(id=w,H=H,fee=fee,scope=sc,control='atr_px_r1',**m))
    print('match',w,flush=True)

# combos: buy cluster AND b3
for w in BUY:
    yes=(M[w]==2)&M.b3
    for H in HS:
        for fee in FEES:
            col=f'f{H}_{fee}'; d=M.loc[yes & M[col].notna(), ['date','year','L5',col]].copy()
            dm=M.groupby('date')[col].transform('mean'); d['ex']=d[col]-dm.loc[d.index]
            nd=int(d.date.nunique())
            r=dict(id=f'{w}&b3',meaning='bullish_x_overbought',H=H,fee=fee,n_dates=nd,n_events=events(yes),n_obs=len(d),
                   win_rate=float((d[col]>0).mean()) if len(d) else np.nan)
            if nd<30: r['status']='too_few_dates'; rows.append(r); continue
            m,lo,hi=cl(d.ex.values,d.date.values); se=(hi-lo)/3.92
            r.update(status='tested',ex=m,lo95=lo,hi95=hi,p=2*norm.sf(abs(m/se)) if se>0 else np.nan,signs=signs(d.ex.values,d.year.values))
            # matched vs ready-NO of same row on b3 dates? use ready of w, b3 yes, control non-yes
            base=M[(M[w]>0)&M.b3][['date','year','L5','px','b_atr','b_px','b_r1',col]].dropna(subset=['b_atr','b_px','b_r1',col]).copy()
            base['_c']=M.loc[base.index,w].values
            mm=do_match(base,col,['date','b_atr','b_px','b_r1'])
            r.update({f'match_{k}':v for k,v in mm.items()})
            rows.append(r); MATCH.append(dict(id=f'{w}&b3',H=H,fee=fee,scope='all',control='atr_px_r1',**mm))
    print('combo',w,flush=True)

R=pd.DataFrame(rows); MR=pd.DataFrame(MATCH)
R['bh']=False
for (H,fee),idx in R[R.status=='tested'].groupby(['H','fee']).groups.items():
    p=R.loc[idx,'p'].fillna(1).values; mt=len(p); o=np.argsort(p); ok=p[o]<=(np.arange(1,mt+1)/mt)*0.05
    k=int(np.max(np.where(ok)[0])+1) if ok.any() else 0; bh=np.zeros(mt,bool); bh[o[:k]]=True; R.loc[idx,'bh']=bh
    print(f'BH H={H} fee={fee}: tested={mt} clear={int((R.loc[idx,"p"]<.05).sum())} BH={k}',flush=True)

# pass bar: win_rate>0.5 after 30bp, matched resid CI>0 (or <0 for bearish), BH or combo, any of H in 5/20/60
MR.to_csv('2020_24_f4_matched_multi.csv',index=False,float_format='%.6f')
# attach primary match to R
for i in R.index[R.id.isin(need)]:
    w=R.id[i]; H=R.H[i]; fee=R.fee[i]
    m=MR[(MR.id==w)&(MR.H==H)&(MR.fee==fee)&(MR.scope=='all')&(MR.control=='atr_px_r1')]
    if len(m):
        m=m.iloc[0]; R.loc[i,'match_resid']=m.resid; R.loc[i,'match_lo']=m.lo; R.loc[i,'match_hi']=m.hi; R.loc[i,'match_win']=m.win; R.loc[i,'match_signs']=m.signs; R.loc[i,'match_dates']=m.dates
def pass_row(r):
    if r.status!='tested' or r.fee!=30: return False
    wr=r.match_win if 'match_win' in r and pd.notna(r.match_win) else r.win_rate
    if not (wr>0.5): return False
    # matched residual must clear 0 in the tagged direction
    if 'match_lo' in r and pd.notna(r.match_lo):
        bull=str(r.meaning) in ('bullish','bullish_x_overbought')
        if bull and not (r.match_lo>0): return False
        if (not bull) and not (r.match_hi<0): return False
    elif pd.isna(r.ex): return False
    return True
R['pass_bar']=R.apply(pass_row,axis=1)
R.to_csv('2020_24_f4_score.csv',index=False,float_format='%.6f')
pd.set_option('display.width',280); pd.set_option('display.max_columns',40)
prio=R[R.id.isin(PRIORITY)|R.id.str.endswith('&b3')]
print('=== PRIORITY+combo ==='); print(prio.sort_values(['id','H','fee'])[['id','H','fee','yes_rate','ex','lo95','hi95','n_dates','n_events','win_rate','p','bh','signs','match_resid','match_lo','match_hi','match_win','match_signs','pass_bar']].round(5).to_string())
print('=== PASS BAR ==='); print(R[R.pass_bar][['id','H','fee','ex','match_resid','match_lo','match_hi','match_win','n_dates','n_events','signs','bh']].round(5).to_string())
print('=== BH survivors any H ==='); print(R[R.bh][['id','H','fee','ex','lo95','hi95','n_dates','n_events','win_rate','signs','match_resid','match_win','pass_bar']].round(5).to_string())
