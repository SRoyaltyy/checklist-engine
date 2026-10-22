import pandas as pd, numpy as np
def add2(D, by=None):
    """D has Open,High,Low,Close,Volume; by=group key series or None."""
    G=(lambda s: s.groupby(by,sort=False)) if by is not None else (lambda s: s)
    def roll(s,n,f,mp=None):
        if by is None: return getattr(s.rolling(n,min_periods=mp or n),f)()
        return s.groupby(by,sort=False).transform(lambda x:getattr(x.rolling(n,min_periods=mp or n),f)())
    sh=lambda s,k=1: G(s).shift(k)
    O,H,L,C,V=D.Open,D.High,D.Low,D.Close,D.Volume
    b=(C-O)/O; gb=b.clip(lower=0); rb=(-b).clip(lower=0)
    for n in (10,20): D[f'gr_body{n}']=roll(gb,n,'sum')/roll(rb,n,'sum').replace(0,np.nan)
    m20=roll(C,20,'mean'); s20=roll(C,20,'std'); m50=roll(C,50,'mean')
    D['pctB']=(C-(m20-2*s20))/(4*s20).replace(0,np.nan)
    D['slope20']=m20/sh(m20,5)-1; D['slope50']=m50/sh(m50,10)-1; D['vs50']=C/m50-1
    pc=sh(C); tr=np.maximum(H,pc.fillna(H))-np.minimum(L,pc.fillna(L)); atr=roll(tr,14,'mean')
    h20=roll(H,20,'max'); l20=roll(L,20,'min')
    D['dip_atr']=(h20-C)/atr; D['pos20']=(C-l20)/(h20-l20).replace(0,np.nan)
    D['ext20']=C/m20-1; D['up5']=C/sh(C,5)-1; D['bb_mid']=m20; D['bb_up']=m20+2*s20; D['bb_lo']=m20-2*s20
    D['d52h']=C/roll(H,252,'max',200)-1
    return D

def add3(D, by=None):
    def roll(s,n,f,mp=None):
        if by is None: return getattr(s.rolling(n,min_periods=mp or n),f)()
        return s.groupby(by,sort=False).transform(lambda x:getattr(x.rolling(n,min_periods=mp or n),f)())
    sh=(lambda s,k=1: s.groupby(by,sort=False).shift(k)) if by is not None else (lambda s,k=1: s.shift(k))
    H,L,C,O,V=D.High,D.Low,D.Close,D.Open,D.Volume
    am=lambda x: x.rolling(20).apply(lambda a: 19-a.argmax(),raw=True)
    D['days_since_h20']=(H.groupby(by,sort=False).transform(am) if by is not None else am(H))
    below=(C<D.bb_mid).astype(int)
    grp=(below!=sh(below)).cumsum() if by is None else ((below!=sh(below))|(by!=by.shift())).cumsum()
    D['days_below_mid']=below.groupby(grp).cumsum()*below
    D['mid_slope_up']=(D.slope20>0).astype(int)
    lh=(H<sh(H)).astype(int); D['lower_highs10']=roll(lh,10,'sum')
    gv=V.where(C>O,0); rv=V.where(C<O,0); D['redgreen_vol10']=roll(rv,10,'sum')/roll(gv,10,'sum').replace(0,np.nan)
    l40=roll(L,40,'min'); h20=roll(H,20,'max'); D['dd_vs_run']=(h20-C)/(h20-l40).replace(0,np.nan)
    return D
