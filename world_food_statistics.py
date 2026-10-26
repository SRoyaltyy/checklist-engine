"""The additional numeric bar families requested at 16:35 HKT.

Research presets are explicit; these do not claim vendor-default equivalence.
All periods count completed native candles. Peer membership is a PIT input.
"""
import numpy as np
import pandas as pd
from world_bar_statistics import ema,wilder_atr

def _wilder_mean(values,n):
    out=np.full(len(values),np.nan);seed=[];last=np.nan
    for i,x in enumerate(values):
        if not np.isfinite(x):seed=[];last=np.nan
        elif not np.isfinite(last):
            seed.append(x)
            if len(seed)==n:last=float(np.mean(seed));out[i]=last
        else:last=(last*(n-1)+x)/n;out[i]=last
    return out

def _ratio(a,b):
    return np.divide(a,b,out=np.full(len(a),np.nan),where=np.asarray(b)!=0)

def _stochastic(values,n):
    x=pd.Series(values);lo=x.rolling(n).min();hi=x.rolling(n).max()
    return (100*(x-lo)/(hi-lo).where(hi>lo)).to_numpy()

def regression_statistics(close,period):
    c=np.asarray(close,dtype=float)
    names=("slope","intercept","residual_standard_error","slope_standard_error","intercept_standard_error")
    out={k:np.full(len(c),np.nan) for k in names}
    if len(c)<period:return out
    windows=np.lib.stride_tricks.sliding_window_view(c,period)
    x=np.arange(period,dtype=float);xmean=x.mean();xc=x-xmean;sxx=np.dot(xc,xc)
    mean=windows.mean(axis=1);centered=windows-mean[:,None]
    slope=np.einsum("ij,j->i",centered,xc)/sxx
    intercept=mean-slope*xmean;residual=centered-slope[:,None]*xc
    error=np.sqrt(np.einsum("ij,ij->i",residual,residual)/(period-2))
    values=(slope,intercept,error,error/np.sqrt(sxx),error*np.sqrt(1/period+xmean*xmean/sxx))
    for key,value in zip(names,values):out[key][period-1:]=value
    return out

def additional_bar_statistics(o,h,l,c,v):
    import talib
    o,h,l,c,v=map(lambda x:np.asarray(x,dtype=float),(o,h,l,c,v))
    out={};delta_hist=None
    for label,period in (("short",7),("default",13),("long",26)):
        mean=ema(c,period);_,_,hist=talib.MACD(c,fastperiod=12,slowperiod=26,signalperiod=9)
        dm=np.r_[np.nan,np.diff(mean)];dh=np.r_[np.nan,np.diff(hist)]
        valid=np.isfinite(dm)&np.isfinite(dh)
        out["I221_"+label+"_impulse"]=np.where(valid,np.where((dm>0)&(dh>0),1.,np.where((dm<0)&(dh<0),-1.,0.)),np.nan)
        out["I221_"+label+"_ema_change"]=dm
        out["I221_"+label+"_histogram_change"]=dh
    previous=np.r_[np.nan,c[:-1]]
    true_high=np.maximum(h,previous);true_low=np.minimum(l,previous)
    flow=_ratio(2*c-true_high-true_low,true_high-true_low)*v
    for label,n in (("short",10),("default",21),("long",42)):
        out["I222_"+label+"_value"]=_ratio(_wilder_mean(flow,n),_wilder_mean(np.where(np.isfinite(flow),v,np.nan),n))
    for label,n,atr,mult in (("short",10,7,1.5),("default",20,14,2.),("long",40,28,2.5)):
        center=pd.Series(c).rolling(n).mean().to_numpy();spread=mult*wilder_atr(h,l,c,atr)
        out["I223_"+label+"_mid"]=center;out["I223_"+label+"_upper"]=center+spread;out["I223_"+label+"_lower"]=center-spread
    for n in (20,60,120,200):
        out.update({f"I224_{n}_"+key:value for key,value in regression_statistics(c,n).items()})
    for label,fast,slow,cycle,smooth in (("short",12,26,5,3),("default",23,50,10,3),("long",46,100,20,3)):
        macd=ema(c,fast)-ema(c,slow)
        first=ema(_stochastic(macd,cycle),smooth)
        out["I226_"+label+"_value"]=ema(_stochastic(first,cycle),smooth)
    return {key:np.asarray(value,dtype=np.float32) for key,value in out.items()}

def peer_correlations(returns,target,eligible_peers,period):
    """One column per named peer, masked by membership known at query time.

    The caller supplies returns on the same native candle intervals. No
    current-sector backfill, automatic peer substitution, or self-correlation.
    """
    if target not in returns:raise ValueError("target absent")
    if returns.columns.duplicated().any() or returns.index.duplicated().any():
        raise ValueError("duplicate return axes")
    if not returns.index.equals(eligible_peers.index):
        raise ValueError("peer membership dates differ")
    if eligible_peers.isna().any().any():raise ValueError("unknown peer membership")
    if any(peer not in returns for peer in eligible_peers):
        raise ValueError("peer has no aligned return series")
    if target in eligible_peers and eligible_peers[target].any():
        raise ValueError("self is not a peer")
    result={}
    for peer in eligible_peers:
        if peer==target:continue
        result[peer]=returns[target].rolling(period).corr(returns[peer]).where(eligible_peers[peer].astype(bool))
    return pd.DataFrame(result,index=returns.index)
