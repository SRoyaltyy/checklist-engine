"""Additional causal recipes, using the explicit dictionary definitions."""
import numpy as np
import pandas as pd
from world_bar_statistics import ema

EXTRA_IDS=frozenset({"I042","I043","I044","I048","I056","I062","I064","I065","I067","I073","I076","I077","I092"})

def _ratio(a,b):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    return np.divide(a,b,out=np.full(a.shape,np.nan),where=b!=0)

def confirmed_zigzag(h,l,threshold,percent=None):
    """Thresholds are price distances frozen when a running extreme is set.

    Same-bar ambiguity has a fixed causal rule: update the extreme, then test
    reversal; at most one pivot is confirmed per candle. Emit at confirmation.
    """
    n=len(h);ph=np.full(n,np.nan);pl=ph.copy()
    valid=np.flatnonzero(np.isfinite(threshold)&(threshold>0))
    if not len(valid):return ph,pl
    first=valid[0];direction=1;extreme=h[first];distance=abs(extreme)*percent/100 if percent is not None else threshold[first]
    for i in range(first+1,n):
        if direction>0:
            if h[i]>=extreme:extreme=h[i];distance=abs(extreme)*percent/100 if percent is not None else threshold[i]
            if extreme-l[i]>=distance:
                ph[i]=extreme;direction=-1;extreme=l[i];distance=abs(extreme)*percent/100 if percent is not None else threshold[i]
        else:
            if l[i]<=extreme:extreme=l[i];distance=abs(extreme)*percent/100 if percent is not None else threshold[i]
            if h[i]-extreme>=distance:
                pl[i]=extreme;direction=1;extreme=h[i];distance=abs(extreme)*percent/100 if percent is not None else threshold[i]
    return ph,pl

def extra_recipe(ident,p,o,h,l,c,v,dates):
    import talib as ta
    n=p.get("period");cs=pd.Series(c)
    def sma(x,k):return pd.Series(x).rolling(k).mean().to_numpy()
    def rma(x,k):
        x=np.asarray(x,dtype=float);out=np.full(len(x),np.nan);seed=[];prior=np.nan
        for i,value in enumerate(x):
            if not np.isfinite(value):seed=[];prior=np.nan
            elif not np.isfinite(prior):
                seed.append(value)
                if len(seed)==k:prior=float(np.mean(seed));out[i]=prior
            else:prior=(prior*(k-1)+value)/k;out[i]=prior
        return out
    if ident=="I042":
        # Causal dictionary alternative, no centered future values.
        return {"value":c-pd.Series(sma(c,n)).shift(n//2+1).to_numpy()}
    if ident=="I043":
        mid=pd.Series((h+l)/2);lo=mid.rolling(n).min();hi=mid.rolling(n).max()
        position=((mid-lo)/(hi-lo).replace(0,np.nan)).to_numpy()
        state=0.;out=np.full(len(c),np.nan)
        for i,x in enumerate(position):
            if np.isfinite(x):
                state=np.clip(.66*(x-.5)+.67*state,-.999,.999)
                out[i]=.5*np.log((1+state)/(1-state))
        return {"value":out}
    if ident=="I044":
        parts=[weight*sma(ta.ROC(c,timeperiod=p[f"roc{i}"]),p[f"sma{i}"])
               for i,weight in enumerate((1,2,3,4),1)]
        line=sum(parts);return {"line":line,"signal":sma(line,p["signal"])}
    if ident=="I048":
        def sym(x):
            s=pd.Series(x);return (s+2*s.shift(1)+2*s.shift(2)+s.shift(3)).to_numpy()/6
        line=_ratio(sma(sym(c-o),n),sma(sym(h-l),n))
        return {"line":line,"signal":sym(line)}
    if ident=="I056":
        streak=np.zeros(len(c))
        for i in range(1,len(c)):
            if c[i]>c[i-1]:streak[i]=max(0,streak[i-1])+1
            elif c[i]<c[i-1]:streak[i]=min(0,streak[i-1])-1
        roc=ta.ROC(c,timeperiod=1);rank=np.full(len(c),np.nan);w=p["rank"]
        for i in range(w+1,len(c)):
            previous=roc[i-w:i]
            if np.isfinite(previous).all():rank[i]=100*np.mean(previous<roc[i])
        return {"value":(ta.RSI(c,timeperiod=p["price_rsi"])+ta.RSI(streak,timeperiod=p["streak_rsi"])+rank)/3}
    if ident=="I062":
        atr=ta.ATR(h,l,c,timeperiod=p["atr_period"])
        up=(h+l)/2+p["multiplier"]*atr;down=(h+l)/2-p["multiplier"]*atr
        line=np.full(len(c),np.nan);direction=np.full(len(c),np.nan)
        for i in range(len(c)):
            if not np.isfinite(atr[i]):continue
            if i==0 or not np.isfinite(line[i-1]):
                direction[i]=1 if c[i]>=(h[i]+l[i])/2 else -1
            else:
                up[i]=up[i] if up[i]<up[i-1] or c[i-1]>up[i-1] else up[i-1]
                down[i]=down[i] if down[i]>down[i-1] or c[i-1]<down[i-1] else down[i-1]
                if direction[i-1]>0:direction[i]=-1 if c[i]<down[i] else 1
                else:direction[i]=1 if c[i]>up[i] else -1
            line[i]=down[i] if direction[i]>0 else up[i]
        return {"value":line,"direction":direction}
    if ident=="I064":
        atr=ta.ATR(h,l,c,timeperiod=n);line=np.full(len(c),np.nan);direction=line.copy()
        high_close=low_close=np.nan
        for i in range(len(c)):
            if not np.isfinite(atr[i]):continue
            if i==0 or not np.isfinite(line[i-1]):
                high_close=low_close=c[i];direction[i]=1;line[i]=c[i]-p["multiplier"]*atr[i];continue
            high_close=max(high_close,c[i]);low_close=min(low_close,c[i])
            bullish=direction[i-1]>0
            candidate=high_close-p["multiplier"]*atr[i] if bullish else low_close+p["multiplier"]*atr[i]
            line[i]=max(line[i-1],candidate) if bullish else min(line[i-1],candidate)
            direction[i]=1 if bullish else -1
            if (bullish and c[i]<line[i]) or (not bullish and c[i]>line[i]):
                direction[i]=-direction[i];high_close=low_close=c[i]
                line[i]=c[i]-direction[i]*p["multiplier"]*atr[i]
        return {"value":line,"direction":direction}
    if ident=="I065":
        result={}
        for label in ("jaw","teeth","lips"):
            result[label]=pd.Series(rma((h+l)/2,p[label])).shift(p[label+"_shift"]).to_numpy()
        return result
    if ident in ("I067","I076"):
        threshold=abs(c)*p["reversal_percent"]/100 if ident=="I067" else p["reversal_atr"]*ta.ATR(h,l,c,timeperiod=p["atr_period"])
        ph,pl=confirmed_zigzag(h,l,threshold,percent=p.get("reversal_percent"))
        result={"confirmed_high":ph,"confirmed_low":pl}
        if ident=="I076":
            # The last completed leg needs two confirmed opposite pivots.
            last=None;levels={r:np.full(len(c),np.nan) for r in (.236,.382,.5,.618,.786)}
            current={}
            for i in range(len(c)):
                value=ph[i] if np.isfinite(ph[i]) else pl[i]
                if np.isfinite(value):
                    if last is not None:
                        current={r:last+r*(value-last) for r in levels}
                    last=value
                for r in levels:
                    if r in current:levels[r][i]=current[r]
            result.update({"level_"+str(r).replace(".","p"):a for r,a in levels.items()})
        return result
    if ident=="I073":
        if dates is None:raise ValueError("performance calendar YTD requires candle dates")
        dt=pd.DatetimeIndex(dates);year_last=cs.groupby(dt.year).last()
        prior=np.array([year_last.get(year-1,np.nan) for year in dt.year])
        return {"value":c/cs.shift(n).to_numpy()-1,"calendar_ytd":_ratio(c,prior)-1}
    if ident=="I077":
        left,right,k=p["pivot_left"],p["pivot_right"],p["last_pivots"]
        ph=[];pl=[];upper=np.full(len(c),np.nan);lower=upper.copy()
        for t in range(len(c)):
            i=t-right
            if i>=left:
                if h[i]>max(h[i-left:i]) and h[i]>max(h[i+1:t+1]):ph.append(h[i])
                if l[i]<min(l[i-left:i]) and l[i]<min(l[i+1:t+1]):pl.append(l[i])
            if len(ph)>=k:upper[t]=np.mean(ph[-k:])
            if len(pl)>=k:lower[t]=np.mean(pl[-k:])
        return {"resistance":upper,"support":lower}
    if ident=="I092":
        # TradingView official Klinger formula (support/solutions/43000589157).
        dm=h-l;trend=np.full(len(c),-1.)
        if len(c)>1:trend[1:]=np.where(np.diff(h+l+c)>0,1.,-1.)
        cm=np.full(len(c),np.nan)
        if len(c):cm[0]=dm[0]
        for i in range(1,len(c)):cm[i]=(cm[i-1] if trend[i]==trend[i-1] else dm[i-1])+dm[i]
        force=v*2*(_ratio(dm,cm)-1)*trend*100
        line=ema(force,p["fast"])-ema(force,p["slow"]);signal=ema(line,p["signal"])
        return {"line":line,"signal":signal,"histogram":line-signal}
    raise ValueError("unknown additional recipe: "+ident)
