import pandas as pd, numpy as np
def feats(df):
    D=df.copy(); O,H,L,C,V=[D[c].astype(float) for c in ['Open','High','Low','Close','Volume']]
    pc=C.shift(); D['r1']=C/pc-1; d=C.diff()
    up=d.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean(); dn=(-d).clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    D['rsi14']=100-100/(1+up/dn.replace(0,np.nan))
    tp=(H+L+C)/3; mf=tp*V; p=mf.where(tp>tp.shift(),0).rolling(14).sum(); n=mf.where(tp<tp.shift(),0).rolling(14).sum()
    D['mfi']=100*p/(p+n); D['ext20']=C/C.rolling(20).mean()-1; D['rvol']=V/V.rolling(50,min_periods=40).mean().shift()
    g=(C>O).astype(int); D['grn']=g
    s=[];k=0
    for x in g: k=k+1 if x else 0; s.append(k)
    D['gstreak']=s
    for N in (5,10):
        D[f'gratio{N}']=g.rolling(N).mean()
    u=D.r1.clip(lower=0); w=(-D.r1).clip(lower=0)
    D['run5']=C/C.shift(5)-1; D['maxdn5']=D.r1.rolling(5).min(); D['ddspan5']=C.rolling(5).min()/C.rolling(5).max()-1
    D['up_dn5']=u.rolling(5).sum()/w.rolling(5).sum().clip(lower=1e-9)
    green=(D.gratio5>=.7)&(D.up_dn5>=2)&(D.run5>0)
    push=(D.run5>.005)&(-D.maxdn5<=D.run5/3)&(-D.ddspan5<=D.run5/3)
    nob=(D.rsi14<=70)&(D.mfi<=80)&(D.ext20<=.10); fr=D.gstreak.between(2,5)
    D['sig_FRESH_FULL_N5']=green&push&nob&fr; D['sig_green_N5']=green; D['sig_pushback_N5']=push; D['sig_notOB']=nob; D['sig_fresh2_5']=fr
    D['sig_RSI>70']=D.rsi14>70; D['sig_MFI>80']=D.mfi>80; D['sig_EXT20>10%']=D.ext20>.1
    D['sig_UP10_DAY']=D.r1>=.1; D['sig_RVOL>=3']=D.rvol>=3; D['sig_RVOL>=5']=D.rvol>=5
    D['d52h']=C/H.rolling(252,min_periods=100).max()-1
    return D
