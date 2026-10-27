"""Causal statistics on one entity's completed native OHLCV candles.

No day-D shift here: world_timeframes exposes these only after candle completion.
Volatility annualization follows candle duration. No intraday OHLC is invented.
"""
import numpy as np
import pandas as pd

def ema(values, period):
    """SMA-seeded EMA; a missing value resets its warmup."""
    x=np.asarray(values,dtype=float); out=np.full(len(x),np.nan)
    seed=[]; prior=np.nan; alpha=2.0/(period+1)
    for i,value in enumerate(x):
        if not np.isfinite(value):
            seed=[]; prior=np.nan
        elif not np.isfinite(prior):
            seed.append(value)
            if len(seed)==period:
                prior=float(np.mean(seed));out[i]=prior
        else:
            prior += alpha*(value-prior);out[i]=prior
    return out

def wilder_atr(high,low,close,period):
    h,l,c=map(lambda a:np.asarray(a,dtype=float),(high,low,close))
    tr=np.full(len(c),np.nan)
    if len(c)>1:
        tr[1:]=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    out=np.full(len(c),np.nan);seed=[];prior=np.nan
    for i,value in enumerate(tr):
        if not np.isfinite(value):
            seed=[];prior=np.nan
        elif not np.isfinite(prior):
            seed.append(value)
            if len(seed)==period:prior=float(np.mean(seed));out[i]=prior
        else:
            prior=(prior*(period-1)+value)/period;out[i]=prior
    return out

def _rs_hurst(values):
    """Single-window rescaled-range estimate log(R/S)/log(N), on log returns."""
    x=np.asarray(values); sd=x.std(ddof=1)
    if sd<=0:return np.nan
    path=np.r_[0.,np.cumsum(x-x.mean())];span=np.ptp(path)
    return np.log(span/sd)/np.log(len(x)) if span>0 else np.nan

def _r_squared(values):
    x=np.arange(len(values),dtype=float);x-=x.mean()
    y=values-values.mean();den=np.dot(x,x)*np.dot(y,y)
    return np.dot(x,y)**2/den if den>0 else np.nan

def _autocorrelation(values):
    a,b=values[:-1],values[1:];a=a-a.mean();b=b-b.mean()
    den=np.sqrt(np.dot(a,a)*np.dot(b,b))
    return np.dot(a,b)/den if den>0 else np.nan

def bar_statistics(open_,high,low,close,volume,timeframe):
    o,h,l,c,v=map(lambda a:np.asarray(a,dtype=float),(open_,high,low,close,volume))
    if timeframe=="monthly":annual=12.
    elif timeframe.endswith("d") and timeframe[:-1].isdigit() and 1<=int(timeframe[:-1])<=21:
        annual=252./int(timeframe[:-1])
    else:raise ValueError("unsupported candle duration")
    if not all(len(a)==len(c) for a in (o,h,l,v)):raise ValueError("unequal OHLCV lengths")
    cs=pd.Series(c);positive=cs.where(cs>0)
    returns=np.log(positive/positive.shift(1));out={}
    atr14=wilder_atr(h,l,c,14)
    for n in (7,14,28):
        out[f"NATR{n}"]=np.divide(100*wilder_atr(h,l,c,n),c,
                                out=np.full(len(c),np.nan),where=c!=0)
    for n in (20,50):
        sd=cs.rolling(n).std(ddof=0)
        out[f"PRICE_ZSCORE{n}"]=((cs-cs.rolling(n).mean())/sd.where(sd>0)).to_numpy()
    up=np.full(len(c),np.nan);down=up.copy()
    for i in range(1,len(c)):
        if not np.isfinite(c[i-1:i+1]).all():continue
        up[i]=(0 if i==1 or not np.isfinite(up[i-1]) else up[i-1])+1 if c[i]>c[i-1] else 0
        down[i]=(0 if i==1 or not np.isfinite(down[i-1]) else down[i-1])+1 if c[i]<c[i-1] else 0
    out.update(UP_STREAK=up,DOWN_STREAK=down)
    for n in (10,20,60,120):
        out[f"HV{n}"]=returns.rolling(n).std(ddof=1).to_numpy()*np.sqrt(annual)*100
    for short,long in ((10,60),(20,120)):
        a,b=out[f"HV{short}"],out[f"HV{long}"]
        out[f"HV_RATIO{short}_{long}"]=np.divide(a,b,out=np.full(len(c),np.nan),where=b>0)
    prev_atr=np.r_[np.nan,atr14[:-1]] if len(c) else atr14
    full_gap=np.full(len(c),np.nan);overnight=full_gap.copy()
    if len(c)>1:
        full_gap[1:]=np.where(o[1:]>h[:-1],o[1:]-h[:-1],
                             np.where(o[1:]<l[:-1],o[1:]-l[:-1],0.))
        overnight[1:]=o[1:]-c[:-1]
    for name,values in (("GAP_ATR14",full_gap),("OPEN_CLOSE_GAP_ATR14",overnight)):
        out[name]=np.divide(values,prev_atr,out=np.full(len(c),np.nan),where=prev_atr>0)
    for horizon in (5,20):
        # Fixed mature cohorts: a gap born at i enters the sample at i+horizon.
        # A quick fill is not counted early; unresolved gaps are not censored away.
        cohorts=np.full(len(c),np.nan);filled=cohorts.copy()
        for i in range(1,len(c)-horizon):
            if not np.isfinite(np.r_[o[i],h[i-1:i+horizon+1],l[i-1:i+horizon+1]]).all():continue
            cohorts[i+horizon]=float(full_gap[i]!=0)
            filled[i+horizon]=0.
            if full_gap[i]>0:
                filled[i+horizon]=float(np.any(l[i+1:i+horizon+1]<=h[i-1]))
            elif full_gap[i]<0:
                filled[i+horizon]=float(np.any(h[i+1:i+horizon+1]>=l[i-1]))
        for n in (20,60):
            den=pd.Series(cohorts).rolling(n).sum()
            out[f"GAP_FILL_RATE{n}_H{horizon}"]=(pd.Series(filled).rolling(n).sum()/den.where(den>0)).to_numpy()
    for n in (20,60):
        roll=returns.rolling(n)
        out[f"RETURN_SKEW{n}"]=roll.skew().to_numpy()
        out[f"RETURN_EXCESS_KURTOSIS{n}"]=roll.kurt().to_numpy()
        out[f"RETURN_AUTOCORR1_{n}"]=roll.apply(_autocorrelation,raw=True).to_numpy()
        out[f"HURST_RS{n}"]=roll.apply(_rs_hurst,raw=True).to_numpy()
    for n in (20,60,100):
        out[f"LINEARREG_R2_{n}"]=cs.rolling(n).apply(_r_squared,raw=True).to_numpy()
    for n in (5,10,20):
        smooth=pd.Series(ema(h-l,n))
        prior=smooth.shift(n)
        out[f"CHAIKIN_VOLATILITY{n}_{n}"]=(100*(smooth/prior.where(prior>0)-1)).to_numpy()
    return {key:np.asarray(value,dtype=np.float64) for key,value in out.items()}

def relative_statistics(stock,benchmark,role):
    """Compare exactly matching candle intervals, never as-of different buckets.

    Input columns candle_start/date/close. Caller must supply already-PIT
    completed candles and the same timeframe. Gaps fail rather than forward-fill.
    """
    if role not in ("spy","sector","industry"):raise ValueError("unknown benchmark role")
    keys=["candle_start","date"]
    if not stock[keys].reset_index(drop=True).equals(benchmark[keys].reset_index(drop=True)):
        raise ValueError("relative features require identical candle boundaries")
    a=pd.Series(stock.close.to_numpy(dtype=float));b=pd.Series(benchmark.close.to_numpy(dtype=float))
    ratio=(a/b.where(b>0)).where(a>0)
    ar=a.pct_change(fill_method=None);br=b.pct_change(fill_method=None);out={}
    for n in (20,60,120):
        out[f"MANSFIELD_{role}_{n}"]=100*(ratio/ratio.rolling(n).mean()-1)
        out[f"RELATIVE_CHANGE_{role}_{n}"]=a/a.shift(n)-b/b.shift(n)
        out[f"CORRELATION_{role}_{n}"]=ar.rolling(n).corr(br)
        variance=br.rolling(n).var(ddof=1)
        out[f"BETA_{role}_{n}"]=ar.rolling(n).cov(br)/variance.where(variance>0)
    return {key:value.to_numpy(np.float32) for key,value in out.items()}

def universe_rs_rank(close,eligible,period):
    """Cross-sectional percentile of N-candle price return, PIT eligible only.

    close and eligible have identical date/ticker axes, aligned candle boundaries.
    Ties receive average rank. Missing or ineligible values remain missing.
    """
    if not close.index.equals(eligible.index) or not close.columns.equals(eligible.columns):
        raise ValueError("eligible axes differ from price axes")
    if eligible.isna().any().any():raise ValueError("eligibility must be explicit")
    values=(close/close.shift(period)-1).where(eligible.astype(bool))
    return 100*values.rank(axis=1,pct=True,method="average")
