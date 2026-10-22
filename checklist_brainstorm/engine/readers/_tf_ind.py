"""Taskforce indicator library: every function maps split-adjusted daily bars (index < D) to a daily Series X_t
(value as of the close of bar t). Nothing here looks past the last bar it is given."""
import numpy as np, pandas as pd, talib as ta
def sma(s,n): return s.rolling(n).mean()
def ema(s,n): return s.ewm(span=n,adjust=False).mean()
def rma(s,n): return s.ewm(alpha=1/n,adjust=False).mean()
def wma_w(s,w):
    w=np.asarray(w,float); w=w/w.sum(); return s.rolling(len(w)).apply(lambda a:float(np.dot(a,w)),raw=True)
def consec(b):
    b=pd.Series(b).fillna(False).astype(int); g=(b!=b.shift()).cumsum(); return b.groupby(g).cumsum()*b
def A(s): return s.to_numpy(float)
def build(b,spy=None):
    o,h,l,c,v=[b[k].astype(float) for k in ('Open','High','Low','Close','Volume')]
    O,H,L,C,V=map(A,(o,h,l,c,v)); S=lambda a:pd.Series(a,index=c.index)
    atr=S(ta.ATR(H,L,C,14)); rng=(h-l).replace(0,np.nan); r=c.pct_change(); hl2=(h+l)/2; tp=(h+l+c)/3
    sp=spy.reindex(c.index) if spy is not None else None
    rsi14=S(ta.RSI(C,14)); bbm=sma(c,20); bbs=c.rolling(20).std(); ub=bbm+2*bbs; lb=bbm-2*bbs
    tr=S(ta.TRANGE(H,L,C)); idx=pd.Series(np.arange(len(c),dtype=float),index=c.index)
    def ao_(): return sma(hl2,5)-sma(hl2,34)
    def smi():
        mid=(h.rolling(10).max()+l.rolling(10).min())/2; d=ema(ema(c-mid,3),3); rr=ema(ema(h.rolling(10).max()-l.rolling(10).min(),3),3); return 100*d/(0.5*rr)
    def stochrsi():
        mn=rsi14.rolling(14).min(); mx=rsi14.rolling(14).max(); return sma(100*(rsi14-mn)/(mx-mn),3)
    def tsi():
        d=c.diff(); return 100*ema(ema(d,25),13)/ema(ema(d.abs(),25),13)
    def vortex():
        vp=(h-l.shift()).abs().rolling(14).sum(); vm=(l-h.shift()).abs().rolling(14).sum(); t=tr.rolling(14).sum(); return (vp-vm)/t
    def wad():
        c1=c.shift(); trh=np.maximum(h,c1); trl=np.minimum(l,c1); ad=np.where(c>c1,c-trl,np.where(c<c1,c-trh,0.)); return S(ad).cumsum()
    def accb():
        k=4*(h-l)/(h+l); up=sma(h*(1+k),20); lo=sma(l*(1-k),20); return (c-lo)/(up-lo)
    def hma(n=20): return S(ta.WMA(A(2*S(ta.WMA(C,n//2))-S(ta.WMA(C,n))),int(np.sqrt(n))))
    def zlema(n=20): lag=(n-1)//2; return ema(c+(c-c.shift(lag)),n)
    def alma(n=9,off=0.85,sig=6):
        m=off*(n-1); s=n/sig; w=np.exp(-((np.arange(n)-m)**2)/(2*s*s)); return wma_w(c,w)
    def fib_w(n):
        f=[1,1]; [f.append(f[-1]+f[-2]) for _ in range(n-2)]; return f[:n]
    def pascal(n):
        from math import comb; return [comb(n-1,i) for i in range(n)]
    def mcgd(n=10):
        out=np.full(len(C),np.nan); 
        for i in range(len(C)):
            if i==0 or np.isnan(out[i-1]): out[i]=C[i]; continue
            p=out[i-1]; out[i]=p+(C[i]-p)/(n*(C[i]/p)**4)
        return S(out)
    def ssf(n=10):
        a=np.exp(-1.414*np.pi/n); b=2*a*np.cos(1.414*np.pi/n); c2=b; c3=-a*a; c1=1-c2-c3; out=C.copy()
        for i in range(2,len(C)): out[i]=c1*(C[i]+C[i-1])/2+c2*out[i-1]+c3*out[i-2]
        return S(out)
    def vidya(n=14):
        d=c.diff(); up=d.clip(lower=0).rolling(9).sum(); dn=(-d.clip(upper=0)).rolling(9).sum(); k=(abs(up-dn)/(up+dn)).to_numpy(); al=2/(n+1); out=np.full(len(C),np.nan)
        for i in range(len(C)):
            if np.isnan(k[i]): continue
            p=out[i-1] if i>0 and not np.isnan(out[i-1]) else C[i]; out[i]=al*k[i]*C[i]+(1-al*k[i])*p
        return S(out)
    def supertrend(n=10,m=3):
        at=S(ta.ATR(H,L,C,n)).to_numpy(); m2=(H+L)/2; ub=m2+m*at; lb=m2-m*at; fu=ub.copy(); fl=lb.copy(); st=np.full(len(C),np.nan); up=True
        for i in range(1,len(C)):
            if np.isnan(at[i]): continue
            fu[i]=ub[i] if (np.isnan(fu[i-1]) or ub[i]<fu[i-1] or C[i-1]>fu[i-1]) else fu[i-1]
            fl[i]=lb[i] if (np.isnan(fl[i-1]) or lb[i]>fl[i-1] or C[i-1]<fl[i-1]) else fl[i-1]
            if up and C[i]<fl[i]: up=False
            elif (not up) and C[i]>fu[i]: up=True
            st[i]=fl[i] if up else fu[i]
        return S(st)
    def ichimoku():
        t=(h.rolling(9).max()+l.rolling(9).min())/2; k=(h.rolling(26).max()+l.rolling(26).min())/2
        sa=((t+k)/2).shift(26); sb=((h.rolling(52).max()+l.rolling(52).min())/2).shift(26); top=np.maximum(sa,sb); bot=np.minimum(sa,sb)
        x=np.where(c>top,(c-top)/atr,np.where(c<bot,(c-bot)/atr,0.)); return S(x).where(top.notna()&atr.notna())
    def entropy(n=10):
        p=c/c.rolling(n).sum(); return (-(p*np.log2(p))).rolling(n).sum()
    def stdevall():
        n=idx+1; sx=idx.cumsum(); sy=c.cumsum(); sxx=(idx**2).cumsum(); sxy=(idx*c).cumsum(); syy=(c**2).cumsum()
        bta=(n*sxy-sx*sy)/(n*sxx-sx**2); al=(sy-bta*sx)/n; fit=al+bta*idx
        res=(syy-2*al*sy-2*bta*sxy+n*al**2+2*al*bta*sx+bta**2*sxx)/n; return ((c-fit)/np.sqrt(res.clip(lower=0))).where(n>=20)
    def rvi():
        sd=c.rolling(10).std(); d=c.diff(); u=rma(sd.where(d>0,0.),14); dn=rma(sd.where(d<0,0.),14); return 100*u/(u+dn)
    def nvi(pos=False):
        rr=r.fillna(0).to_numpy(); vv=V; out=np.ones(len(C))*1000.
        for i in range(1,len(C)):
            cond=(vv[i]>vv[i-1]) if pos else (vv[i]<vv[i-1]); out[i]=out[i-1]*(1+rr[i]) if cond else out[i-1]
        s=S(out); return s/ema(s,255)-1
    def crsi():
        st=np.zeros(len(C))
        for i in range(1,len(C)): st[i]=(st[i-1]+1 if st[i-1]>=0 else 1) if C[i]>C[i-1] else ((st[i-1]-1 if st[i-1]<=0 else -1) if C[i]<C[i-1] else 0)
        pr=r.rolling(101).apply(lambda a:(a[:-1]<a[-1]).mean()*100,raw=True)
        return (S(ta.RSI(C,3))+S(ta.RSI(st,2))+pr)/3
    def exhc():
        up=consec(c>c.shift(4)); dn=consec(c<c.shift(4)); return np.minimum(up,9)-np.minimum(dn,9)
    def fisher(n=9):
        hh=hl2.rolling(n).max(); ll=hl2.rolling(n).min(); x=(2*((hl2-ll)/(hh-ll))-1).to_numpy(); v_=np.zeros(len(C)); f=np.full(len(C),np.nan)
        for i in range(len(C)):
            if np.isnan(x[i]): continue
            pv=v_[i-1] if i else 0; v_[i]=np.clip(0.66*x[i]+0.67*pv,-0.999,0.999); pf=f[i-1] if i and not np.isnan(f[i-1]) else 0
            f[i]=0.5*np.log((1+v_[i])/(1-v_[i]))+0.5*pf
        return S(f)
    def kst():
        rc=lambda n:c.pct_change(n)*100; k=sma(rc(10),10)+2*sma(rc(15),10)+3*sma(rc(20),10)+4*sma(rc(30),15); return k-sma(k,9)
    def rvgi(n=14):
        num=wma_w(c-o,[1,2,2,1]); den=wma_w(h-l,[1,2,2,1]); rv=sma(num,n)/sma(den,n); return rv-wma_w(rv,[1,2,2,1])
    def runs(sign):
        e1=ema(c,10); e2=ema(c,20); 
        return ((e1>e1.shift(2))&(e2>e2.shift(2))) if sign>0 else ((e1<e1.shift(2))&(e2<e2.shift(2)))
    def amat():
        f=ema(c,8); s=ema(c,21); lr=(f>s)&(f>f.shift(2))&(s>s.shift(2)); sr=(f<s)&(f<f.shift(2))&(s<s.shift(2)); return lr.astype(float)-sr.astype(float)
    def rwi(n=14):
        hi=(h-l.shift(n))/(atr*np.sqrt(n)); lo=(h.shift(n)-l)/(atr*np.sqrt(n)); return hi-lo
    def ha():
        hc=(O+H+L+C)/4; ho=np.empty(len(C)); ho[0]=(O[0]+C[0])/2
        for i in range(1,len(C)): ho[i]=(ho[i-1]+hc[i-1])/2
        g=S(hc>ho); return consec(g)-consec(~g)
    def zigzag():
        import sys,os; sys.path.insert(0,'/workspace/tf'); from repaint_safe import zigzag_confirmed
        piv=zigzag_confirmed(list(C)); out=np.full(len(C),np.nan); j=0; last=None
        for i in range(len(C)):
            while j<len(piv) and piv[j][2]<=i: last=piv[j]; j+=1
            if last: out[i]=(i-last[2]) if last[1]=='L' else -(i-last[2])
        return S(out)
    def fractal():
        lw=(l.shift(2)<l.shift(4))&(l.shift(2)<l.shift(3))&(l.shift(2)<l.shift(1))&(l.shift(2)<l)
        hg=(h.shift(2)>h.shift(4))&(h.shift(2)>h.shift(3))&(h.shift(2)>h.shift(1))&(h.shift(2)>h)
        return (lw.astype(float)-hg.astype(float)).where(l.shift(4).notna())
    def squeeze_pro():
        e=ema(c,20); a20=S(ta.ATR(H,L,C,20)); return sum(((ub<e+k*a20)&(lb>e-k*a20)).astype(float) for k in (1,1.5,2))
    def thermo():
        t=np.maximum(h-h.shift(),l.shift()-l); return t/ema(t,22)
    def cg(n=10):
        w=np.arange(1,n+1)[::-1]
        g=c.rolling(n).apply(lambda a:-np.dot(np.arange(1,n+1),a[::-1])/a.sum(),raw=True); return g-g.shift()
    def eom():
        br=(v/1e6)/(h-l).replace(0,np.nan); return sma((hl2-hl2.shift())/br,14)/c
    def pvr():
        pu=c>=c.shift(); vu=v>=v.shift(); return np.select([pu&vu,pu&~vu,~pu&~vu,~pu&vu],[1,2,3,4],np.nan)*pd.Series(1.,index=c.index)
    M={
    # ---- base taskforce variants
    'Body % of range':lambda:(c-o).abs()/rng,
    'Signed body % (close location)':lambda:(c-l)/rng,
    'Lower wick share (pushback)':lambda:(np.minimum(o,c)-l)/rng,
    'Upper wick share':lambda:(h-np.maximum(o,c))/rng,
    'Range vs ATR14':lambda:(h-l)/atr.shift(),
    'Giant red no-pushback candle':lambda:((c<o)&((c-o)/o<=-0.05)&((h-l)>=2*atr)&((np.minimum(o,c)-l)<0.1*(h-l))).astype(float).where(atr.notna()),
    'Hammer':lambda:(((np.minimum(o,c)-l)>=2*(c-o).abs())&((h-np.maximum(o,c))<=0.1*(h-l))&(c/c.shift(5)<0.97)).astype(float).where(c.shift(5).notna()),
    'Bearish engulfing':lambda:((c<o)&(c.shift()>o.shift())&(o>=c.shift())&(c<=o.shift())).astype(float).where(c.shift().notna()),
    'Bullish engulfing':lambda:((c>o)&(c.shift()<o.shift())&(o<=c.shift())&(c>=o.shift())).astype(float).where(c.shift().notna()),
    'Daily return':lambda:r,
    'Overnight gap % (completed, D-1)':lambda:o/c.shift()-1,
    'Gap fill status':lambda:(((o>c.shift())&(l<=c.shift()))|((o<c.shift())&(h>=c.shift()))).astype(float).where(c.shift().notna()),
    'Change from open (Finviz)':lambda:c/o-1,
    'Close vs SMA20':lambda:c/sma(c,20)-1,'Close vs SMA50':lambda:c/sma(c,50)-1,'Close vs SMA200':lambda:c/sma(c,200)-1,
    'SMA20 vs SMA50 spread':lambda:sma(c,20)/sma(c,50)-1,'SMA20 slope':lambda:sma(c,20)/sma(c,20).shift(5)-1,'EMA9 vs EMA21':lambda:ema(c,9)/ema(c,21)-1,
    'RSI14':lambda:rsi14,'RSI2':lambda:S(ta.RSI(C,2)),'Stochastic %K(14,3)':lambda:S(ta.STOCH(H,L,C,14,3,0,3,0)[0]),
    'Williams %R(14)':lambda:S(ta.WILLR(H,L,C,14)),'MACD histogram (12,26,9)':lambda:S(ta.MACD(C)[2]),'CCI20':lambda:S(ta.CCI(H,L,C,20)),
    'Bollinger %B(20,2)':lambda:(c-lb)/(ub-lb),'Bollinger bandwidth':lambda:(ub-lb)/bbm,'ATR14 % of price':lambda:atr/c,
    'Realized vol 10d vs 60d':lambda:r.rolling(10).std()/r.rolling(60).std(),
    'Distance from 52w high':lambda:c/h.rolling(252).max()-1,'Distance from 52w low':lambda:c/l.rolling(252).min()-1,'Distance from all-time high':lambda:c/h.cummax()-1,
    'New 52w high event':lambda:(h>=h.shift().rolling(252).max()).astype(float).where(h.shift(252).notna()),
    'New 52w low event':lambda:(l<=l.shift().rolling(252).min()).astype(float).where(l.shift(252).notna()),
    'Relative volume (V/SMA50, own bars)':lambda:v/sma(v,50),'Up-volume share':lambda:None,'Dollar volume (C*V, own bars)':lambda:c*v,
    'MFI14':lambda:S(ta.MFI(H,L,C,V,14)),'Chaikin Money Flow 20':lambda:((((c-l)-(h-c))/rng).fillna(0)*v).rolling(20).sum()/v.rolling(20).sum(),
    'SSR triggered flag (Rule 201)':lambda:(l<=0.9*c.shift()).astype(float).where(c.shift().notna()),
    'Prior-day range position':lambda:(c-l.shift())/(h.shift()-l.shift()).replace(0,np.nan),
    'RSI14 position in own 20d range':lambda:(rsi14-rsi14.rolling(20).min())/(rsi14.rolling(20).max()-rsi14.rolling(20).min()),
    'RSI14 position in own 60d range':lambda:(rsi14-rsi14.rolling(60).min())/(rsi14.rolling(60).max()-rsi14.rolling(60).min()),
    'Stacked MAs':lambda:pd.Series(np.select([(c>sma(c,20))&(sma(c,20)>sma(c,50))&(sma(c,50)>sma(c,200)),(c<sma(c,20))&(sma(c,20)<sma(c,50))&(sma(c,50)<sma(c,200))],[1.,-1.],0.),index=c.index).where(sma(c,200).notna()),
    'Position in all-time range':lambda:(c-l.cummin())/(h.cummax()-l.cummin()),
    'Keltner channel position (EMA20, 2xATR10)':lambda:(c-(ema(c,20)-2*S(ta.ATR(H,L,C,10))))/(4*S(ta.ATR(H,L,C,10))),
    'Donchian 55d channel position':lambda:(c-l.rolling(55).min())/(h.rolling(55).max()-l.rolling(55).min()),
    'Distance from 52w high in ATR units':lambda:(c-h.rolling(252).max())/atr,'Distance from 52w low in ATR units':lambda:(c-l.rolling(252).min())/atr,
    'Distance from ATH in ATR units':lambda:(c-h.cummax())/atr,
    'Consecutive green closes':lambda:consec(c>c.shift()).astype(float),'Consecutive red closes':lambda:consec(c<c.shift()).astype(float),
    'Consecutive higher highs':lambda:consec(h>h.shift()).astype(float),'Consecutive lower lows':lambda:consec(l<l.shift()).astype(float),
    'Days outside upper Bollinger (20,2)':lambda:consec(c>ub).astype(float).where(ub.notna()),'Days outside lower Bollinger (20,2)':lambda:consec(c<lb).astype(float).where(lb.notna()),
    'Days above SMA20':lambda:consec(c>sma(c,20)).astype(float).where(sma(c,20).notna()),'Days below SMA20':lambda:consec(c<sma(c,20)).astype(float).where(sma(c,20).notna()),
    'Days above SMA50':lambda:consec(c>sma(c,50)).astype(float).where(sma(c,50).notna()),'Days below SMA50':lambda:consec(c<sma(c,50)).astype(float).where(sma(c,50).notna()),
    'Days RSI14 above 70':lambda:consec(rsi14>70).astype(float).where(rsi14.notna()),'Days RSI14 below 30':lambda:consec(rsi14<30).astype(float).where(rsi14.notna()),
    'Days since last 3% pullback':lambda:consec(~(r<=-0.03)).astype(float),'Days since last 3% bounce':lambda:consec(~(r>=0.03)).astype(float),
    'Stretch: SMA20 distance in ATR, own percentile':lambda:((c-sma(c,20))/atr).rolling(252).apply(lambda a:(a<=a[-1]).mean()*100,raw=True),
    'Tired run: up streak on shrinking volume':lambda:((consec(c>c.shift())>=3)&(v<v.shift())&(v.shift()<v.shift(2))&(v.shift(2)<v.shift(3))).astype(float),
    'Tired run: down streak on shrinking volume':lambda:((consec(c<c.shift())>=3)&(v<v.shift())&(v.shift()<v.shift(2))&(v.shift(2)<v.shift(3))).astype(float),
    'Tired run: new high without RSI high':lambda:((c>=c.rolling(20).max())&(rsi14<rsi14.shift().rolling(19).max())).astype(float).where(rsi14.shift(20).notna()),
    'Tired run: new low without RSI low':lambda:((c<=c.rolling(20).min())&(rsi14>rsi14.shift().rolling(19).min())).astype(float).where(rsi14.shift(20).notna()),
    'Tired run: shrinking bodies on up streak':lambda:(lambda bd:((consec(c>c.shift())>=3)&(bd<bd.shift())&(bd.shift()<bd.shift(2))&(bd.shift(2)<bd.shift(3))).astype(float))((c-o).abs()),
    'Tired run: shrinking bodies on down streak':lambda:(lambda bd:((consec(c<c.shift())>=3)&(bd<bd.shift())&(bd.shift()<bd.shift(2))&(bd.shift(2)<bd.shift(3))).astype(float))((c-o).abs()),
    'Tired run: growing upper wick on up streak':lambda:(lambda w:((consec(c>c.shift())>=3)&(w>w.shift())&(w.shift()>w.shift(2))&(w.shift(2)>w.shift(3))).astype(float))((h-np.maximum(o,c))/rng),
    'Cumulative streak move in ATR':lambda:None,
    # ---- TA audit variants
    'Accelerator oscillator':lambda:(ao_()-sma(ao_(),5))/c,'ADX14 trend strength':lambda:S(ta.ADX(H,L,C,14)),'ADXR14':lambda:S(ta.ADXR(H,L,C,14)),
    '+DI minus -DI (14)':lambda:S(ta.PLUS_DI(H,L,C,14)-ta.MINUS_DI(H,L,C,14)),'+DM minus -DM (14) / ATR14':lambda:S(ta.PLUS_DM(H,L,14)-ta.MINUS_DM(H,L,14))/atr,
    'DX14':lambda:S(ta.DX(H,L,C,14)),'Awesome oscillator / C':lambda:ao_()/c,'APO(12,26) / C':lambda:S(ta.APO(C,12,26,1))/c,
    'PPO(12,26,9) histogram':lambda:(lambda p:p-ema(p,9))(100*(ema(c,12)-ema(c,26))/ema(c,26)),
    'Aroon up minus down (25)':lambda:S(ta.AROONOSC(H,L,25)),'Balance of power (SMA14)':lambda:sma((c-o)/rng,14),'Chande momentum oscillator 14':lambda:S(ta.CMO(C,14)),
    'Coppock curve':lambda:S(ta.WMA(A(c.pct_change(14)*100+c.pct_change(11)*100),10)),'Detrended price oscillator 20 / C':lambda:(c.shift(11)-sma(c,20))/c,
    'Kaufman efficiency ratio 10':lambda:(c-c.shift(10)).abs()/c.diff().abs().rolling(10).sum(),'Elder ray bull-bear power / ATR':lambda:((h-ema(c,13))+(l-ema(c,13)))/atr,
    'Forecast oscillator 14':lambda:100*(c-S(ta.TSF(C,14)).shift())/c,'Williams fractal (5-bar)':fractal,
    'Intraday momentum index 14':lambda:100*(c-o).clip(lower=0).rolling(14).sum()/(c-o).abs().rolling(14).sum(),
    'KDJ J line (9,3,3)':lambda:(lambda k,d:3*S(k)-2*S(d))(*ta.STOCH(H,L,C,9,3,0,3,0)),'Momentum 10 / C':lambda:c/c.shift(10)-1,
    'Qstick 10 / ATR':lambda:sma(c-o,10)/atr,'Rate of change 20':lambda:c/c.shift(20)-1,'Stochastic momentum index (10,3,3)':smi,
    'Fast stochastic %K(5,3)':lambda:S(ta.STOCHF(H,L,C,5,3,0)[0]),'StochRSI(14,14,3,3) %K':stochrsi,'TRIX 15':lambda:S(ta.TRIX(C,15)),
    'True strength index (25,13)':tsi,'Ultimate oscillator (7,14,28)':lambda:S(ta.ULTOSC(H,L,C)),
    'Vertical horizontal filter 28':lambda:(c.rolling(28).max()-c.rolling(28).min())/c.diff().abs().rolling(28).sum(),'Vortex VI+ minus VI- (14)':vortex,
    'Acceleration bands position (20)':accb,'Close vs DEMA20':lambda:c/S(ta.DEMA(C,20))-1,'Close vs TEMA20':lambda:c/S(ta.TEMA(C,20))-1,'Close vs HMA20':lambda:c/hma()-1,
    'Close vs KAMA(10,2,30)':lambda:c/S(ta.KAMA(C,10))-1,'Close vs T3(5,0.7)':lambda:c/S(ta.T3(C,5,0.7))-1,'Close vs TRIMA20':lambda:c/S(ta.TRIMA(C,20))-1,
    'Close vs WMA20':lambda:c/S(ta.WMA(C,20))-1,'Close vs ZLEMA20':lambda:c/zlema()-1,'Close vs VWMA20':lambda:c/((c*v).rolling(20).sum()/v.rolling(20).sum())-1,
    'Close vs RMA (Wilder MA) 14':lambda:c/rma(c,14)-1,'MAMA vs FAMA spread':lambda:(lambda m,f:S(m)/S(f)-1)(*ta.MAMA(C,0.5,0.05)),
    'Close vs midpoint 14':lambda:c/S(ta.MIDPOINT(C,14))-1,'Close vs midprice 14':lambda:c/S(ta.MIDPRICE(H,L,14))-1,'Parabolic SAR side':lambda:(c-S(ta.SAR(H,L,0.02,0.2)))/atr,
    'Supertrend (10,3) side':lambda:(c-supertrend())/atr,'Close vs Hilbert instantaneous trendline':lambda:c/S(ta.HT_TRENDLINE(C))-1,'Close vs ALMA(9,0.85,6)':lambda:c/alma()-1,
    'Close vs Fibonacci WMA 10':lambda:c/wma_w(c,fib_w(10))-1,'Close vs McGinley dynamic 10':mcgd and (lambda:c/mcgd()-1),'Close vs Pascal WMA 10':lambda:c/wma_w(c,pascal(10))-1,
    'Close vs sine WMA 14':lambda:c/wma_w(c,np.sin(np.pi*np.arange(1,15)/15))-1,'Close vs smoothed MA 7':lambda:c/rma(c,7)-1,'Close vs Ehlers super smoother 10':lambda:c/ssf()-1,
    'Close vs symmetric WMA 10':lambda:c/wma_w(c,[1,2,3,4,5,5,4,3,2,1])-1,'Close vs VIDYA 14':lambda:c/vidya()-1,
    'Williams alligator spread':lambda:(rma(hl2,5).shift(3)-rma(hl2,13).shift(8))/atr,
    'Gann HiLo activator side':lambda:pd.Series(np.select([c>sma(h,13).shift(),c<sma(l,21).shift()],[1.,-1.],0.),index=c.index).where(sma(l,21).shift().notna()),
    'Ichimoku cloud position':ichimoku,'Linear regression slope 20 / C':lambda:S(ta.LINEARREG_SLOPE(C,20))/c,
    'Linear regression R2 20':lambda:S(ta.CORREL(A(idx),C,20))**2,'Linear regression angle 20':lambda:S(ta.LINEARREG_ANGLE(A(c/c.shift(20)*100),20)),
    'Close vs linear regression line 20':lambda:(c-S(ta.LINEARREG(C,20)))/atr,'Close vs time series forecast 14':lambda:c/S(ta.TSF(C,14)).shift()-1,
    'Beta vs SPY 60d':lambda:None if sp is None else r.rolling(60).cov(sp.pct_change())/sp.pct_change().rolling(60).var(),
    'Correlation vs SPY 60d':lambda:None if sp is None else r.rolling(60).corr(sp.pct_change()),
    'Return variance 20 (annualised)':lambda:r.rolling(20).var()*252,'Close z-score 20':lambda:(c-bbm)/bbs,'Return skew 20':lambda:r.rolling(20).skew(),
    'Return kurtosis 20':lambda:r.rolling(20).kurt(),'Return entropy 10':entropy,'Mean absolute deviation 30 / C':lambda:c.rolling(30).apply(lambda a:np.abs(a-a.mean()).mean(),raw=True)/c,
    'Close vs rolling median 30':lambda:c/c.rolling(30).median()-1,'Close vs rolling 50% quantile 30':lambda:c.rolling(30).apply(lambda a:(a<=a[-1]).mean(),raw=True),
    'Close vs regression stdev channel (all data to D-1)':stdevall,'Choppiness index 14':lambda:100*np.log10(tr.rolling(14).sum()/(h.rolling(14).max()-l.rolling(14).min()))/np.log10(14),
    'Hilbert dominant cycle period':lambda:S(ta.HT_DCPERIOD(C)),'Hilbert dominant cycle phase':lambda:S(ta.HT_DCPHASE(C)),
    'Hilbert phasor in-phase minus quadrature / C':lambda:(lambda i,q:(S(i)-S(q))/c)(*ta.HT_PHASOR(C)),'Hilbert sine vs lead sine':lambda:(lambda s,ls:S(s)-S(ls))(*ta.HT_SINE(C)),
    'Hilbert trend vs cycle mode':lambda:S(ta.HT_TRENDMODE(C).astype(float)),'Average daily range % 20':lambda:sma((h-l)/c,20),
    'Chaikin volatility 10':lambda:ema(h-l,10)/ema(h-l,10).shift(10)-1,'Mass index (9,25)':lambda:(ema(h-l,9)/ema(ema(h-l,9),9)).rolling(25).sum(),
    'Relative volatility index 14':rvi,'NATR14':lambda:S(ta.NATR(H,L,C,14)),'Historical vol 20 (close-to-close, annualised)':lambda:np.log(c).diff().rolling(20).std()*np.sqrt(252),
    'Parkinson vol 20':lambda:np.sqrt((np.log(h/l)**2).rolling(20).mean()/(4*np.log(2))*252),
    'Garman-Klass vol 20':lambda:np.sqrt(252*(0.5*np.log(h/l)**2-(2*np.log(2)-1)*np.log(c/o)**2).rolling(20).mean()),
    'Ulcer index 14':lambda:np.sqrt(((100*(c/c.rolling(14).max()-1))**2).rolling(14).mean()),
    'Aberration band position':lambda:(lambda a5:(c-(sma(tp,5)-a5))/(2*a5))(S(ta.ATR(H,L,C,5))),
    'Chandelier exit side (22,3)':lambda:(lambda a22:(c-(h.rolling(22).max()-3*a22))/a22)(S(ta.ATR(H,L,C,22))),
    'Price distance / C':lambda:(2*(h-l)-(c-o).abs()+(o-c.shift()).abs())/c,'Elder thermometer ratio':thermo,
    'TTM squeeze on':lambda:(lambda e,a:((ub<e+1.5*a)&(lb>e-1.5*a)).astype(float).where(ub.notna()&a.notna()))(ema(c,20),S(ta.ATR(H,L,C,20))),
    'Squeeze pro tightness':squeeze_pro,'Chaikin oscillator (3,10) / avg V':lambda:S(ta.ADOSC(H,L,C,V,3,10))/sma(v,20),
    'Force index 13 / dollar vol':lambda:ema(c.diff()*v,13)/sma(c*v,20),'Ease of movement 14':eom,
    'Market facilitation index vs own avg':lambda:((h-l)/v.replace(0,np.nan))/sma((h-l)/v.replace(0,np.nan),20),
    'Negative volume index vs EMA255':lambda:nvi(False),'Positive volume index vs EMA255':lambda:nvi(True),
    'Percentage volume oscillator (12,26)':lambda:100*(ema(v,12)-ema(v,26))/ema(v,26),
    'Archer OBV fast-slow':lambda:(lambda ob:(ema(ob,4)-ema(ob,12))/sma(v,20))(S(ta.OBV(C,V))),'Price-volume (C*V) vs own avg':lambda:c*v/sma(c*v,20),
    'Price-volume rank':pvr,'Time segmented volume / avg V':lambda:(c.diff()*v).rolling(18).sum()/(c*sma(v,20)),
    'Volume heatmap z':lambda:(v-sma(v,610))/v.rolling(610).std(),'Bias vs SMA26':lambda:c/sma(c,26)-1,'BRAR AR(26)':lambda:100*(h-o).rolling(26).sum()/(o-l).rolling(26).sum(),
    'Chande forecast oscillator 9':lambda:100*(c-S(ta.LINEARREG(C,9)))/c,'Center of gravity 10':cg,'Connors RSI (3,2,100)':crsi,
    'Correlation trend indicator 12':lambda:S(ta.CORREL(C,A(idx),12)),'Exhaustion count (TD-style 9)':lambda:exhc().astype(float),'Fisher transform 9':fisher,
    'KST minus signal':kst,'Pretty good oscillator 14':lambda:(c-sma(c,14))/ema(tr,14),'Psychological line 12':lambda:100*(c>c.shift()).rolling(12).sum()/12,
    'Relative vigor index minus signal':rvgi,'Price slope 1 (normalised)':lambda:c.diff()/atr,'Archer MA trend (8,21)':amat,
    'Long run (fast & slow MA rising)':lambda:runs(1).astype(float).where(c.shift(21).notna()),'Short run (fast & slow MA falling)':lambda:runs(-1).astype(float).where(c.shift(21).notna()),
    'Random walk index high minus low 14':rwi,'ZigZag 5% leg direction and age':zigzag,'Heikin-Ashi colour streak':lambda:ha().astype(float),
    'Candle z-score (body z vs 30d)':lambda:(lambda bd:(bd-bd.rolling(30).mean())/bd.rolling(30).std())((c-o).abs()),
    'MACD (EMA 5,35,5) histogram / C':lambda:(lambda m:(m-ema(m,5))/c)(ema(c,5)-ema(c,35)),
    'Chande momentum (up-only smoothing) 14':lambda:(lambda d:100*(rma(d.clip(lower=0),14)-rma(-d.clip(upper=0),14))/(rma(d.clip(lower=0),14)+rma(-d.clip(upper=0),14)))(c.diff()),
    }
    for k in (10,20,50,100,200):
        M[f'Close vs SMA{k} in ATR units']=(lambda k=k:(c-sma(c,k))/atr); M[f'Close vs EMA{k} in ATR units']=(lambda k=k:(c-ema(c,k))/atr)
    for k in (5,10,20,60,252):
        M[f'Position in {k}d high-low range']=(lambda k=k:(c-l.rolling(k).min())/(h.rolling(k).max()-l.rolling(k).min()))
    for k in (10,20,60,252):
        M[f'Fibonacci zone of {k}d swing']=(lambda k=k:(c-l.rolling(k).min())/(h.rolling(k).max()-l.rolling(k).min()))
    for p in (20,50):
        m_=sma(c,p); s_=c.rolling(p).std()
        M[f'Bollinger %B ({p},2) quartile']=(lambda m_=m_,s_=s_:(c-(m_-2*s_))/(4*s_))
        M[f'Outside Bollinger band ({p},2)']=(lambda m_=m_,s_=s_:pd.Series(np.select([c>m_+2*s_,c<m_-2*s_],[1.,-1.],0.),index=c.index).where(s_.notna()))
    P=(h+l+c).shift()/3; hs,ls=h.shift(),l.shift()
    for lv,f in (('R1',2*P-ls),('R2',P+(hs-ls)),('S1',2*P-hs),('S2',P-(hs-ls))): M[f'Close vs classic pivot {lv}']=(lambda f=f:(c-f)/atr)
    # volume profile & anchored VWAP (computed on last 800 bars only; older values NaN)
    def vp(n,kind):
        out=np.full(len(C),np.nan)
        for i in range(max(n-1,len(C)-800),len(C)):
            hh,ll=H[i-n+1:i+1],L[i-n+1:i+1]; vv=V[i-n+1:i+1]; lo,hi=ll.min(),hh.max()
            if hi<=lo: continue
            ed=np.linspace(lo,hi,51); vol=np.zeros(50)
            for a,b_,x in zip(ll,hh,vv):
                if b_<=a: j=min(int((a-lo)/(hi-lo)*50),49); vol[j]+=x; continue
                ov=np.clip(np.minimum(ed[1:],b_)-np.maximum(ed[:-1],a),0,None); vol+=x*ov/(b_-a)
            pk=int(vol.argmax()); mid=(ed[pk]+ed[pk+1])/2
            if kind=='poc': out[i]=C[i]/mid-1; continue
            lo_i=hi_i=pk; tot=vol[pk]
            while tot<0.7*vol.sum():
                a=vol[lo_i-1] if lo_i>0 else -1; b_=vol[hi_i+1] if hi_i<49 else -1
                if b_>=a: hi_i+=1; tot+=b_
                else: lo_i-=1; tot+=a
            val,vah=ed[lo_i],ed[hi_i+1]; out[i]=(C[i]-val)/(vah-val)
        return S(out)
    M['Close vs volume-profile POC 20d']=lambda:vp(20,'poc'); M['Close vs volume-profile POC 60d']=lambda:vp(60,'poc')
    M['Position in value area 20d']=lambda:vp(20,'va'); M['Position in value area 60d']=lambda:vp(60,'va')
    TPV=np.cumsum(A(tp)*V); CV=np.cumsum(V)
    def avwap(anchor):
        out=np.full(len(C),np.nan)
        for i in range(max(0,len(C)-800),len(C)):
            a=anchor(i)
            if a is None: continue
            tv=TPV[i]-(TPV[a-1] if a else 0); vv=CV[i]-(CV[a-1] if a else 0)
            if vv>0: out[i]=C[i]/(tv/vv)-1
        return S(out)
    def a52(i,hi): 
        if i<251: return None
        w=H[i-251:i+1] if hi else L[i-251:i+1]; return i-251+int(np.argmax(w) if hi else np.argmin(w))
    def apiv(i):
        for t in range(i-2,max(i-300,2),-1):
            if (L[t]<min(L[t-2],L[t-1],L[t+1],L[t+2])) or (H[t]>max(H[t-2],H[t-1],H[t+1],H[t+2])): return t
        return None
    M['Close vs anchored VWAP from last 52w low']=lambda:avwap(lambda i:a52(i,False)); M['Close vs anchored VWAP from last 52w high']=lambda:avwap(lambda i:a52(i,True))
    M['Close vs anchored VWAP from last 5-bar swing pivot']=lambda:avwap(apiv)
    def rally_age():
        fr=[t for t in range(2,len(C)-2) if L[t]<min(L[t-2],L[t-1],L[t+1],L[t+2])]; out=np.full(len(C),np.nan); j=-1; ages=[]
        cur=None; frs=set(fr); conf={t+2:t for t in fr}
        hist=np.full(len(C),np.nan)
        for i in range(len(C)):
            if i in conf: cur=conf[i]
            if cur is not None: hist[i]=i-cur
        for i in range(len(C)):
            w=hist[max(0,i-756):i]; w=w[~np.isnan(w)]
            # completed swing-up lengths = the age just before each reset
            if len(w)>1:
                ends=[w[k] for k in range(len(w)-1) if w[k+1]<w[k]]
                if ends and not np.isnan(hist[i]): out[i]=hist[i]/np.median(ends)
        return S(out)
    M['Rally age vs own median']=rally_age
    def cum_streak():
        g=consec(c>c.shift()); rd=consec(c<c.shift()); n=(g+rd).astype(int).to_numpy(); out=np.full(len(C),np.nan); at=A(atr)
        for i in range(len(C)):
            k=n[i]
            if k>0 and i-k>=0: out[i]=(C[i]-C[i-k])/at[i]
            elif k==0: out[i]=0.
        return S(out)
    M['Cumulative streak move in ATR']=cum_streak
    M['Up-volume share']=None
    return M,dict(o=o,h=h,l=l,c=c,v=v,atr=atr,r=r,rsi=rsi14)
N_DEP={'Up-volume share','OBV change','Accumulation/Distribution line change','Williams accumulation/distribution change','Price volume trend change / avg V','Strictly decreasing over N','Strictly increasing over N','Green:red candle ratio','Return vs sector ETF','Return vs SPY'}
def ndep(name,ctx,N,bench=None):
    """Variants whose X is defined over the row's own window N. Returns X_N as a Series."""
    c,o,h,l,v,atr=[ctx[k] for k in ('c','o','h','l','v','atr')]; C,H,L,V=A(c),A(h),A(l),A(v)
    if name=='Up-volume share': return (v*(c>c.shift())).rolling(N).sum()/v.rolling(N).sum()
    if name=='OBV change': ob=pd.Series(ta.OBV(C,V),index=c.index); return (ob-ob.shift(N))/v.rolling(N).sum()
    if name=='Accumulation/Distribution line change': ad=pd.Series(ta.AD(H,L,C,V),index=c.index); return (ad-ad.shift(N))/v.rolling(N).sum()
    if name=='Williams accumulation/distribution change':
        c1=c.shift(); wad=pd.Series(np.where(c>c1,c-np.minimum(l,c1),np.where(c<c1,c-np.maximum(h,c1),0.)),index=c.index).cumsum(); return (wad-wad.shift(N))/atr
    if name=='Price volume trend change / avg V': pvt=(c.pct_change()*v).cumsum(); return (pvt-pvt.shift(N))/v.rolling(20).mean()
    if name=='Strictly decreasing over N': return (c.diff()<0).rolling(N).sum().eq(N).astype(float).where(c.shift(N).notna())
    if name=='Strictly increasing over N': return (c.diff()>0).rolling(N).sum().eq(N).astype(float).where(c.shift(N).notna())
    if name=='Green:red candle ratio':
        g=(c>o).rolling(N).sum(); rd=(c<o).rolling(N).sum(); return (g/rd.replace(0,np.nan)).fillna(float(N)).where(c.shift(N-1).notna())
    if name in ('Return vs sector ETF','Return vs SPY'):
        if bench is None: return None
        b=bench.reindex(c.index); return c.pct_change(N)-b.pct_change(N)
    return None
