"""Named moving-average grids from I001-I023, evaluated on native candles."""
import numpy as np
import pandas as pd

MATH_RECIPE_VERSION = 2


def hull_mean(values,period):
    """Registered convention: floor half length, nearest integer root length."""
    import talib
    if type(period) is not int or period<4:raise ValueError("Hull period must be an integer >=4")
    values=np.asarray(values,dtype=np.float64)
    root=int(np.floor(np.sqrt(period)+.5))
    return talib.WMA(2*talib.WMA(values,timeperiod=period//2)-talib.WMA(values,timeperiod=period),timeperiod=root)


def mcginley_mean(values,period):
    """SMA seed after period consecutive finite bars, including after a gap."""
    values=np.asarray(values,dtype=np.float64)
    if type(period) is not int or period<1:raise ValueError("McGinley period must be a positive integer")
    out=np.full(len(values),np.nan);seed=[];prior=np.nan
    for i,value in enumerate(values):
        if not np.isfinite(value):seed=[];prior=np.nan;continue
        if not np.isfinite(prior) or prior==0:
            seed.append(value)
            if len(seed)>=period:
                prior=float(np.mean(seed[-period:]));out[i]=prior;seed=[]
            continue
        with np.errstate(divide="ignore",invalid="ignore",over="ignore"):
            current=prior+(value-prior)/(period*(value/prior)**4)
        if not np.isfinite(current):seed=[];prior=np.nan;continue
        prior=current;out[i]=current
    return out

def wilder_mean(values,period):
    out=np.full(len(values),np.nan);seed=[];prior=np.nan
    for i,value in enumerate(values):
        if not np.isfinite(value):seed=[];prior=np.nan
        elif not np.isfinite(prior):
            seed.append(value)
            if len(seed)==period:prior=float(np.mean(seed));out[i]=prior
        else:prior=(prior*(period-1)+value)/period;out[i]=prior
    return out

def extra_moving_averages(o,h,l,c,v):
    import talib
    c=np.asarray(c,dtype=float);v=np.asarray(v,dtype=float);out={}
    for n in (9,20,50,100,200):
        out[f"RMA{n}"]=wilder_mean(c,n)
        out[f"HMA{n}"]=hull_mean(c,n)
        weights=np.exp(-((np.arange(n)-.85*(n-1))**2)/(2*(n/6.)**2));weights/=weights.sum()
        alma=np.full(len(c),np.nan)
        if len(c)>=n:alma[n-1:]=np.correlate(c,weights,mode="valid")
        out[f"ALMA{n}_0p85_6"]=alma
        num=pd.Series(c*v).rolling(n).sum().to_numpy();den=pd.Series(v).rolling(n).sum().to_numpy()
        with np.errstate(divide="ignore",invalid="ignore"):out[f"VWMA{n}_inf"]=num/den
        out[f"MCGINLEY{n}"]=mcginley_mean(c,n)
        out[f"MEDIAN{n}"]=pd.Series(c).rolling(n).median().to_numpy()
    atr=talib.ATR(h,l,c,timeperiod=14)
    for label,periods in (("legacy",(5,10,20,30)),("named",(10,20,50,200))):
        means=np.vstack([talib.SMA(c,timeperiod=n) for n in periods])
        valid=np.isfinite(means).all(axis=0);up=(means[:-1]>means[1:]).sum(axis=0);down=(means[:-1]<means[1:]).sum(axis=0)
        state=np.select([up==3,down==3,up>=2,down>=2],[2.,-2.,1.,-1.],default=0.)
        out[f"I021_{label}_stack"]=np.where(valid,state,np.nan)
        with np.errstate(divide="ignore",invalid="ignore"):
            out[f"I021_{label}_spread_atr_inf"]=np.where(valid,(means.max(axis=0)-means.min(axis=0))/atr,np.nan)
    for fast,slow in ((5,20),(10,50),(20,50),(50,200)):
        difference=talib.SMA(c,timeperiod=fast)-talib.SMA(c,timeperiod=slow)
        previous=np.r_[np.nan,difference[:-1]];valid=np.isfinite(difference)&np.isfinite(previous)
        out[f"I023_{fast}_{slow}_cross"]=np.where(valid,np.where((previous<0)&(difference>0),1.,np.where((previous>0)&(difference<0),-1.,0.)),np.nan)
        out[f"I023_{fast}_{slow}_state"]=np.where(np.isfinite(difference),np.sign(difference),np.nan)
    ribbon=np.vstack([talib.SMA(c,timeperiod=n) for n in range(20,91,10)])
    valid=np.isfinite(ribbon).all(axis=0)
    out["I023_ribbon_bull_pairs"]=np.where(valid,(ribbon[:-1]>ribbon[1:]).sum(axis=0),np.nan)
    out["I023_ribbon_bear_pairs"]=np.where(valid,(ribbon[:-1]<ribbon[1:]).sum(axis=0),np.nan)
    return {k:np.asarray(value,dtype=np.float64) for k,value in out.items()}
