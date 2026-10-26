"""Execute explicitly named indicator settings on native completed candles.

The registry also includes pending recipes. Unsupported recipes are reported by
the audit and never counted as implemented merely because a config exists.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from world_bar_statistics import ema
from world_indicator_extra import EXTRA_IDS,extra_recipe

SUPPORTED_IDS = frozenset({
"I028","I029","I030","I034","I036","I037","I038","I039","I040","I041",
"I045","I046","I047","I049","I050","I051","I052","I053","I054","I055",
"I057","I058","I059","I060","I061","I063","I066","I068","I070","I071","I072",
"I075","I080","I084","I088","I089","I090","I091","I093","I094","I095","I096",
"I098","I099","I101",
}) | EXTRA_IDS

def load_settings():
    return json.loads((Path(__file__).resolve().parent/"dictionary/INDICATOR_SETTINGS.json").read_text(encoding="utf-8"))

def _ratio(a,b):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    return np.divide(a,b,out=np.full(a.shape,np.nan),where=b!=0)

def configured_indicators(o,h,l,c,v,dates=None):
    import talib as ta
    o,h,l,c,v=map(lambda a:np.asarray(a,dtype=float),(o,h,l,c,v))
    out={};cs=pd.Series(c);vs=pd.Series(v);hl=(h+l)/2
    tr=np.full(len(c),np.nan)
    if len(c)>1:tr[1:]=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    def sma(x,n):return pd.Series(x).rolling(n).mean().to_numpy()
    def rma(x,n):
        # Wilder's EMA with an SMA seed, allowing leading NaN warmup.
        x=np.asarray(x,dtype=float);result=np.full(len(x),np.nan);seed=[];prior=np.nan
        for i,value in enumerate(x):
            if not np.isfinite(value):seed=[];prior=np.nan
            elif not np.isfinite(prior):
                seed.append(value)
                if len(seed)==n:prior=float(np.mean(seed));result[i]=prior
            else:prior=(prior*(n-1)+value)/n;result[i]=prior
        return result
    def tsi(long,short):
        delta=np.r_[np.nan,np.diff(c)]
        return 100*_ratio(ema(ema(delta,long),short),ema(ema(abs(delta),long),short))
    def ad():return np.cumsum(np.nan_to_num(_ratio(2*c-h-l,h-l))*v)
    for ident,item in load_settings()["items"].items():
        if ident not in SUPPORTED_IDS:continue
        for setting in item["settings"]:
            p=setting["parameters"]; name=ident+"_"+setting["name"]; result={}
            n=p.get("period")
            if ident in EXTRA_IDS:
                result=extra_recipe(ident,p,o,h,l,c,v,dates)
            elif ident=="I028":
                k,d=ta.STOCH(h,l,c,fastk_period=p["fastk"],slowk_period=p["slowk"],
                    slowd_period=p["slowd"],slowk_matype=0,slowd_matype=0)
                result={"k":k,"d":d}
            elif ident=="I029":result={"value":ta.WILLR(h,l,c,timeperiod=n)}
            elif ident=="I030":
                a,b,d=ta.MACD(c,fastperiod=p["fast"],slowperiod=p["slow"],signalperiod=p["signal"])
                result={"line":a,"signal":b,"histogram":d}
            elif ident=="I034":
                result={label:getattr(ta,fn)(h,l,c,timeperiod=n)
                        for label,fn in (("adx","ADX"),("plus_di","PLUS_DI"),("minus_di","MINUS_DI"))}
            elif ident=="I036":result={"value":ta.CCI(h,l,c,timeperiod=n)}
            elif ident=="I037":result={"value":ta.CMO(c,timeperiod=n)}
            elif ident=="I038":result={"value":sma(hl,p["fast"])-sma(hl,p["slow"])}
            elif ident=="I039":
                raw=ta.BOP(o,h,l,c);result={"value":sma(raw,p["mean_period"]),"raw":raw}
            elif ident=="I040":
                base=ema(c,p["ema_period"]);bull=h-base;bear=l-base
                result={"bull":bull,"bear":bear,"value":bull+bear}
            elif ident=="I041":
                down,up=ta.AROON(h,l,timeperiod=n)
                result={"up":up,"down":down,"oscillator":up-down}
            elif ident=="I045":result={"value":ta.WMA(ta.ROC(c,timeperiod=p["roc1"])+ta.ROC(c,timeperiod=p["roc2"]),timeperiod=p["wma"])}
            elif ident in ("I046","I095"):
                x=c if ident=="I046" else v
                a,b=ema(x,p["fast"]),ema(x,p["slow"])
                line=100*_ratio(a-b,b);signal=ema(line,p["signal"])
                result={"line":line,"signal":signal,"histogram":line-signal}
            elif ident=="I047":result={"value":ta.MOM(c,timeperiod=n)}
            elif ident=="I049":
                sd=cs.rolling(p["std_period"]).std(ddof=0).to_numpy()
                change=np.r_[np.nan,np.diff(c)]
                up=np.where(change>0,sd,0.);down=np.where(change<0,sd,0.)
                up[~np.isfinite(sd)|~np.isfinite(change)]=np.nan
                down[~np.isfinite(sd)|~np.isfinite(change)]=np.nan
                a,b=rma(up,p["rma_period"]),rma(down,p["rma_period"])
                result={"value":100*_ratio(a,a+b)}
            elif ident=="I050":
                line=tsi(p["long"],p["short"]);signal=ema(line,p["signal"])
                result={"line":line,"signal":signal,"histogram":line-signal}
            elif ident=="I051":
                high=pd.Series(h).rolling(p["range_period"]).max().to_numpy()
                low=pd.Series(l).rolling(p["range_period"]).min().to_numpy()
                smooth=lambda x:ema(ema(x,p["smooth1"]),p["smooth2"])
                result={"value":100*_ratio(smooth(c-(high+low)/2),.5*smooth(high-low))}
            elif ident=="I052":
                rsi=pd.Series(ta.RSI(c,timeperiod=p["rsi"]))
                raw=100*(rsi-rsi.rolling(p["stoch"]).min())/(rsi.rolling(p["stoch"]).max()-rsi.rolling(p["stoch"]).min()).replace(0,np.nan)
                k=raw.rolling(p["k"]).mean();d=k.rolling(p["d"]).mean()
                result={"k":k.to_numpy(),"d":d.to_numpy()}
            elif ident=="I053":result={"value":ta.TRIX(c,timeperiod=n)}
            elif ident=="I054":result={"value":tsi(p["long"],p["short"])}
            elif ident=="I055":result={"value":ta.ULTOSC(h,l,c,timeperiod1=p["period1"],timeperiod2=p["period2"],timeperiod3=p["period3"])}
            elif ident=="I057":
                upper=pd.Series(h).rolling(p["atr_period"]).max()-p["multiplier"]*ta.ATR(h,l,c,timeperiod=p["atr_period"])
                lower=pd.Series(l).rolling(p["atr_period"]).min()+p["multiplier"]*ta.ATR(h,l,c,timeperiod=p["atr_period"])
                result={"long":upper.rolling(p["stop_period"]).max().to_numpy(),"short":lower.rolling(p["stop_period"]).min().to_numpy()}
            elif ident=="I058":
                span=pd.Series(h).rolling(n).max()-pd.Series(l).rolling(n).min()
                result={"value":100*np.log10(pd.Series(tr).rolling(n).sum()/span.replace(0,np.nan)).to_numpy()/np.log10(n)}
            elif ident=="I059":
                a=ema(h-l,p["ema_period"]);b=ema(a,p["ema_period"])
                result={"value":pd.Series(_ratio(a,b)).rolling(p["sum_period"]).sum().to_numpy()}
            elif ident=="I060":
                plus=np.r_[np.nan,abs(h[1:]-l[:-1])];minus=np.r_[np.nan,abs(l[1:]-h[:-1])]
                den=pd.Series(tr).rolling(n).sum().to_numpy()
                result={"plus":_ratio(pd.Series(plus).rolling(n).sum(),den),"minus":_ratio(pd.Series(minus).rolling(n).sum(),den)}
            elif ident=="I061":result={"value":ta.SAR(h,l,acceleration=p["acceleration"],maximum=p["maximum"])}
            elif ident=="I063":
                atr=ta.ATR(h,l,c,timeperiod=n)*p["multiplier"]
                result={"long":pd.Series(h).rolling(n).max().to_numpy()-atr,
                        "short":pd.Series(l).rolling(n).min().to_numpy()+atr}
            elif ident in ("I066","I075"):
                left,right=p["left"],p["right"];ph=np.full(len(c),np.nan);pl=ph.copy()
                for i in range(left,len(c)-right):
                    if h[i]>max(h[i-left:i]) and h[i]>max(h[i+1:i+right+1]):ph[i+right]=h[i]
                    if l[i]<min(l[i-left:i]) and l[i]<min(l[i+1:i+right+1]):pl[i+right]=l[i]
                result={"confirmed_high":ph,"confirmed_low":pl}
            elif ident=="I068":
                result={"endpoint":ta.LINEARREG(c,timeperiod=n),"slope":ta.LINEARREG_SLOPE(c,timeperiod=n)}
            elif ident=="I070":
                # Annualization belongs to bar_statistics where timeframe is known.
                logret=np.log(cs.where(cs>0)/cs.shift(1).where(cs.shift(1)>0))
                sigma=logret.rolling(n).std(ddof=1).to_numpy()
                result={"per_candle_sigma":sigma if setting["kind"]=="native" else ema(sigma,p["ema_period"])}
            elif ident=="I071":
                peak=cs.rolling(n).max();dd=100*(cs/peak-1)
                result={"value":np.sqrt(dd.pow(2).rolling(n).mean()).to_numpy()}
            elif ident=="I072":result={"value":100*_ratio(sma(h-l,n),c)}
            elif ident=="I080":
                # Registered core C22 excludes today's volume from its baseline.
                result={"value":_ratio(v,vs.shift(1).rolling(n).mean())}
            elif ident=="I084":result={"value":ta.MFI(h,l,c,v,timeperiod=n)}
            elif ident=="I088":
                m=_ratio(2*c-h-l,h-l)*v
                result={"value":_ratio(pd.Series(m).rolling(n).sum(),vs.rolling(n).sum())}
            elif ident=="I089":
                x=ad();result={"value":ema(x,p["fast"])-ema(x,p["slow"])}
            elif ident=="I090":
                mid=pd.Series(hl);box=_ratio(v,h-l)
                result={"value":sma(_ratio(mid.diff().to_numpy(),box),n)}
            elif ident=="I091":
                force=np.r_[np.nan,np.diff(c)]*v
                result={"value":ema(force,p["ema_period"])}
            elif ident in ("I093","I096"):
                if ident=="I093":
                    indices=[]
                    for increase in (False,True):
                        raw=np.full(len(c),np.nan)
                        if len(c):raw[0]=1000.
                        for i in range(1,len(c)):
                            active=(v[i]>v[i-1]) if increase else (v[i]<v[i-1])
                            raw[i]=raw[i-1]*(c[i]/c[i-1] if active and c[i-1]!=0 else 1.)
                        indices.append(raw)
                    for label,raw in zip(("nvi","pvi"),indices):
                        result[label]=raw if setting["kind"]=="raw" else ema(raw,p["ema_period"])
                else:
                    raw=np.cumsum(np.nan_to_num(np.r_[np.nan,np.diff(c)/np.where(c[:-1]!=0,c[:-1],np.nan)]*v))
                    result={"value":raw if setting["kind"]=="raw" else ema(raw,p["ema_period"])}
            elif ident=="I094":
                raw=v*np.sign(np.r_[np.nan,np.diff(c)])
                result={"value":raw if setting["kind"]=="raw" else pd.Series(raw).rolling(p["sum_period"]).sum().to_numpy()}
            elif ident=="I098":
                a,b,d=ta.BBANDS(c,timeperiod=n,nbdevup=float(p["deviation"]),nbdevdn=float(p["deviation"]),matype=0)
                result={"upper":a,"mid":b,"lower":d,"position":_ratio(c-d,a-d),"width":_ratio(a-d,b)}
            elif ident=="I099":
                mid=ema(c,p["ema_period"]);spread=p["multiplier"]*ta.ATR(h,l,c,timeperiod=p["atr_period"])
                result={"upper":mid+spread,"mid":mid,"lower":mid-spread}
            elif ident=="I101":
                result={"upper":pd.Series(h).shift(1).rolling(n).max().to_numpy(),
                        "lower":pd.Series(l).shift(1).rolling(n).min().to_numpy()}
            if not result:raise RuntimeError("declared recipe produced no columns: "+ident)
            out.update({name+"_"+key:np.asarray(value,dtype=np.float32) for key,value in result.items()})
    return out
