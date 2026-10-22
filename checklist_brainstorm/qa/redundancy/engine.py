import sys;sys.path.insert(0,'.')
from feats import *
from feats import _consec,_sma,_ema
D0,D1='2019-01-01','2025-12-31'
CACHE={}
def stockbars():
    if 'sb' not in CACHE: CACHE['sb']={t:bars(t) for t in STK}
    return CACHE['sb']
def ctx(t): return {'spy':bars('SPY').Close,'sec':bars(SECT[t]).Close}
def panel(fn):  # fn(ticker)->Series bool on bar dates (as of that close) -> shift to next session
    P=pd.DataFrame({t:fn(t) for t in STK}).reindex(IDX)
    return P.shift(1).loc[D0:D1]   # known at D-1 close -> usable at D open
def mkt(s):   # market-level series (as of close) -> broadcast
    s=s.reindex(IDX,method='ffill').shift(1).loc[D0:D1]
    return pd.DataFrame({t:s for t in STK})
def thr(defn):
    m=re.findall(r'YES if (?:X_N|K)\s*(>=|<=)\s*([-+0-9.e]+)',defn)
    return m[-1] if m else None
def lens_apply(X,lens,defn,t,Xsec=None):
    b='(BUT)' in lens; L=lens.replace(' (BUT)','')
    dX=X.diff()
    if L=='level':
        op,v=thr(defn); v=float(v); return (X>=v) if op=='>=' else (X<=v)
    if L=='extreme':
        q=X.rolling(252).quantile(0.05 if b else 0.95).shift(1); return (X<=q) if b else (X>=q)
    if L=='change':
        s=dX.rolling(252).std(); return ((dX<0) if b else (dX>0))&(dX.abs()>=0.5*s)
    if L=='div_price':
        r=CACHE['ret'][t]; return (dX<0)&(r>0) if b else (dX>0)&(r<0)
    if L=='div_volume':
        rv=CACHE['rv'][t]; return (dX>0)&(rv>=1.5) if b else (dX>0)&(rv<0.8)
    if L=='div_sector':
        dS=Xsec.diff(); return (dX<0)&(dS>0) if b else (dX>0)&(dS<0)
    if L=='cross':
        m=X.rolling(3).mean(); return ((X.shift()>=m.shift())&(X<m)) if b else ((X.shift()<=m.shift())&(X>m))
    if L=='streak':
        return (dX<0).rolling(3).sum().eq(3) if b else (dX>0).rolling(3).sum().eq(3)
    return None
def prep():
    sb=stockbars(); CACHE['ret']={t:sb[t].Close.pct_change() for t in STK}; CACHE['rv']={t:sb[t].Volume/sb[t].Volume.rolling(50).mean() for t in STK}
ONE_SIDED={}  # variant -> True if every non-zero print across the sample is +100
def _onesided(v):
    if v not in ONE_SIDED:
        vals=pd.concat([TFX(v,stockbars()[t],ctx(t)) for t in STK]); nz=vals[vals!=0].dropna()
        ONE_SIDED[v]=bool(len(nz)==0 or (nz==100).all())
    return ONE_SIDED[v]
def tf_signal(r):
    L=r.lens.replace(' (BUT)','')
    if L.startswith('rank_market'):
        Xs=pd.DataFrame({t:TFX(r.variant,stockbars()[t],ctx(t)) for t in STK}).reindex(IDX)
        if Xs.isna().all().all(): return None
        pr=Xs.rank(axis=1,pct=True); P=(pr<=0.1) if '(BUT)' in r.lens else (pr>0.9)
        return P.where(Xs.notna()).shift(1).loc[D0:D1]
    if r.variant.startswith('CDL'):
        if L!='level': return None
        _onesided(r.variant)
        def f(t):
            X=TFX(r.variant,stockbars()[t],ctx(t))
            if '(BUT)' not in r.lens: return (X!=0)
            # BUT mirror = 'YES if no pattern' (K==0). Patterns that only ever print +100
            # (TA-Lib one-sided, e.g. MATHOLD/TAKURI/3WHITESOLDIERS) fire when X != +100.
            # Old test used X<0, which can never be true for +100-only patterns.
            if ONE_SIDED.get(r.variant,True): return (X!=100).astype(float).where(X.notna())
            return (X==0).astype(float).where(X.notna())
        return panel(f)
    def f(t):
        X=TFX(r.variant,stockbars()[t],ctx(t))
        if X is None: raise KeyError
        Xs=TFX(r.variant,bars(SECT[t]),ctx(t)) if L=='div_sector' else None
        y=lens_apply(X,r.lens,r.strict_definition,t,Xs); 
        if y is None: raise KeyError
        return y.astype(float).where(X.notna())
    try: return panel(f)
    except (KeyError,TypeError): return None
# ---------- James ----------
def jbars_for(inst,t=None):
    if inst=="stock's SPDR sector ETF": return bars(SECT[t])
    return ibars(INSTR[inst])
INST_RE=r"(SPY|QQQ|IWM|HYG|VIX|Gold|WTI crude|Copper|Bitcoin|DXY|stock's SPDR sector ETF|10y yield|2y yield)"
def outlier_mask(x,color,kind,k):
    c=x.Close; d=c.diff(); a=d.abs(); A20=a.shift(1).rolling(20).mean()
    big=(a>=k*A20) if kind=='x' else (a>=a.shift(1).rolling(252).quantile(1-k/100))
    col=(d>0) if color=='green' else (d<0); return big&col
def james_outlier_loc(r,x):
    s=r.strict_definition
    m=re.search(r'YES if a (green|red) candle .*? on '+INST_RE+r'.*?with \|close-prior close\| (?:>= ([0-9.]+) x A20|ranks in top ([0-9]+)%)',s)
    if not m: return None
    color=m.group(1); kind,k=('x',float(m.group(3))) if m.group(3) else ('p',float(m.group(4)))
    w=re.search(r'occurred (exactly 1 session ago|(\d+) to (\d+) sessions before)',s)
    if not w: return None
    lo,hi=(1,1) if w.group(1).startswith('exactly') else (int(w.group(2))+0,int(w.group(3))+0)
    # most recent outlier age (sessions before yesterday's close; age 0 = yesterday's candle itself) 
    om=outlier_mask(x,color,kind,k); c=x.Close
    idx=np.arange(len(c)); last=pd.Series(np.where(om,idx,np.nan),index=c.index).ffill()
    age=idx-last  # 0 => candle was last close
    li=last.fillna(0).astype(int).values
    oh=pd.Series(x.High.values[li],index=c.index); ol=pd.Series(x.Low.values[li],index=c.index); mid=(oh+ol)/2
    ag=age+1 if 'exactly 1 session ago' in s else age   # 'exactly 1 session ago (i.e. yesterday)' = the D-1 candle
    win=(ag>=lo)&(ag<=hi)
    if "close < the outlier candle's low" in s: loc=c<ol
    elif "outlier low <= yesterday's close < outlier midpoint" in s: loc=(c>=ol)&(c<mid)
    elif "outlier midpoint <= yesterday's close <= outlier high" in s: loc=(c>=mid)&(c<=oh)
    elif "close > the outlier candle's high" in s: loc=c>oh
    else: return None
    return (win&loc&last.notna()).astype(float)
def james_simple(r,x):
    s=r.strict_definition; c=x.Close; d=c.diff()
    m=re.search(r'has closed (up|down) exactly (\d+) consecutive sessions \(close vs prior close\)',s)
    if m:
        st=_consec(d>0) if m.group(1)=='up' else _consec(d<0); return (st==int(m.group(2))).astype(float)
    m=re.search(r'has gone >= (\d+) sessions without printing a new 20-session closing high$',s.strip())
    if m:
        nh=c>=c.rolling(20).max(); return (_consec(~nh)>=int(m.group(1))).astype(float)
    m=re.search(r'closed (above|below) (?:its|the) (upper|lower) (?:Bollinger Band|BB)\s?\(20, ?2\) for >= (\d+) consecutive sessions$',s.strip())
    if m:
        mu=_sma(c,20);sd=c.rolling(20).std(); o=(c>mu+2*sd) if m.group(1)=='above' else (c<mu-2*sd)
        return (_consec(o)>=int(m.group(3))).astype(float)
    m=re.search(r'YES if (\d+)-session change in .*? (>=|<=) ([+-]?[0-9.]+) x stdev of (?:its )?rolling',s)
    if m:
        n=int(m.group(1)); ch=c.diff(n); sd=ch.rolling(252).std().shift(1); k=abs(float(m.group(3)))
        return ((ch>=k*sd) if m.group(2)=='>=' else (ch<=-k*sd)).astype(float)
    return None
def james_signal(r):
    s=r.strict_definition
    if 'Outlier location' in str(r.lens):
        m=re.search(r' on '+INST_RE+r' with',s)
        if not m: return None
        inst=m.group(1).replace(' yield','')
    else:
        m=re.search(r'change in (.+?) (?:\(latest|>=|<=)',s) or re.search(r'YES if (.+?) (?:has closed|has gone|closed (?:above|below))',s)
        if not m: return None
        inst=m.group(1).strip()
        for suf in [' yield',' price']:
            if inst.endswith(suf): inst=inst[:-len(suf)]
        if inst.lower()=="stock's spdr sector etf": inst="stock's SPDR sector ETF"
    if inst not in INSTR and inst!="stock's SPDR sector ETF": return None
    fn=james_outlier_loc if 'Outlier location' in str(r.lens) else james_simple
    if inst=="stock's SPDR sector ETF":
        def f(t):
            y=fn(r,bars(SECT[t])); 
            if y is None: raise KeyError
            return y
        try: return panel(f)
        except KeyError: return None
    try: x=jbars_for(inst)
    except Exception: return None
    y=fn(r,x)
    if y is None: return None
    P=mkt(y)
    if "BUT stock's own prior-session return moved" in s:
        bull=str(r['yes_means (bullish/bearish)']).lower().startswith('bull')
        def g(t):
            b=stockbars()[t]; rr=b.Close.pct_change(); vv=b.Volume/b.Volume.shift(1).rolling(20).mean()
            return (((rr<=-0.03) if bull else (rr>=0.03))&(vv>=2)).astype(float)
        P=P*panel(g)
    return P
# ---------- Theme Radar Finviz restatements of OHLCV (recomputed from bars, % units) ----------
def TRX(var,x,t):
    c,h,l,o,v=x.Close,x.High,x.Low,x.Open,x.Volume; spy=bars('SPY').Close.reindex(c.index)
    m={'Opening gap %':lambda:100*(o/c.shift()-1),'Prior close change %':lambda:100*c.pct_change(),
     'Distance from 52w high %':lambda:100*(c/h.rolling(252).max()-1),'Distance from 52w low %':lambda:100*(c/l.rolling(252).min()-1),
     'Distance from 50d high %':lambda:100*(c/h.rolling(50).max()-1),'Distance from 50d low %':lambda:100*(c/l.rolling(50).min()-1),
     'Distance from SMA20 %':lambda:100*(c/_sma(c,20)-1),'Distance from SMA50 %':lambda:100*(c/_sma(c,50)-1),'Distance from SMA200 %':lambda:100*(c/_sma(c,200)-1),
     'Relative volume':lambda:v/_sma(v,63),'Volatility Week %':lambda:100*((h-l)/c).rolling(5).mean(),'Volatility Month %':lambda:100*((h-l)/c).rolling(21).mean(),
     'Perf Half Year %':lambda:100*c.pct_change(126),'Perf Year %':lambda:100*c.pct_change(252),'Perf % window':lambda:100*c.pct_change(5),
     'Prior-session change from open %':lambda:100*(c/o-1),
     'Beta':lambda:c.pct_change().rolling(252).cov(spy.pct_change())/spy.pct_change().rolling(252).var()}
    k=var.replace(' (BUT mirror)','')
    return m[k]() if k in m else None
def tr_signal(r):
    s=r.strict_definition; b='(BUT mirror)' in r.variant or '-BUT-' in r.id; L=r.lens
    def f(t):
        X=TRX(r.variant,stockbars()[t],t)
        if X is None: raise KeyError
        dX=X.diff()
        if L=='fixed threshold':
            m=re.search(r"' (>=|<=) ([-0-9.]+)",s); v=float(m.group(2)); y=(X>=v) if m.group(1)=='>=' else (X<=v)
        elif L=='extreme vs own history':
            q=X.shift(1).rolling(60).quantile(0.05 if b else 0.95); y=(X<=q) if b else (X>=q)
        elif L=='change since last value':
            m=re.search(r'by >= ([0-9.]+)',s); v=float(m.group(1)); y=(dX<=-v) if b else (dX>=v)
        elif L=='cross':
            m=re.search(r'crosses (?:above|below) ([-0-9.]+)',s); v=float(m.group(1)); y=((X.shift()>=v)&(X<v)) if b else ((X.shift()<v)&(X>=v))
        elif L=='streak': y=(dX<0) if b else (dX>0)
        elif L=='divergence vs price':
            r1=stockbars()[t].Close.diff(); y=((r1>0)&(dX<0)) if b else ((r1<0)&(dX>0))
        else: raise KeyError
        return y.astype(float).where(X.notna())
    try: return panel(f)
    except (KeyError,AttributeError): return None
# ---------- New Bot / Grok hand-coded (definitions quoted in clusters.csv) ----------
def nb_signal(r):
    v=r.variant; s=r.strict_definition
    def f(t):
        x=stockbars()[t]; c,o,h,l=x.Close,x.Open,x.High,x.Low; spy=bars('SPY').Close.reindex(c.index); atr=pd.Series(ta.ATR(h.values,l.values,c.values,14),index=c.index)
        if v=='Consecutive gap-ups': return (_consec(o>h.shift())>=3).astype(float)
        if v=='Up on SPY down day': return ((c.pct_change()>0)&(spy.pct_change()<=-0.01)).astype(float)
        if v=='SSR triggered': return (l<=0.9*c.shift()).astype(float)
        if v=='Inside day after big move': return ((h<h.shift())&(l>l.shift())&(c.pct_change().shift().abs()>=2*(atr/c).shift())).astype(float)
        if v=='Beta breakdown':
            rr=c.pct_change();sr=spy.pct_change();b20=rr.rolling(20).cov(sr)/sr.rolling(20).var();b250=rr.rolling(250).cov(sr)/sr.rolling(250).var()
            X=b20/b250; return ((X<=0.3) if 'BUT' in r.name else (X>=0.3)).astype(float)
        if v.startswith('beta-residual'):
            lr=np.log(c).diff();ls=np.log(spy).diff();beta=(lr.rolling(756).cov(ls)/ls.rolling(756).var()).shift(1)
            res=lr-beta*ls; z=res/res.rolling(252).std().shift(1)
            m=re.search(r'(<=|>=) ([+-]?[0-9.]+) SD',s); k=float(m.group(2))
            return ((z<=k) if m.group(1)=='<=' else (z>=k)).astype(float)
        raise KeyError
    try: return panel(f)
    except (KeyError,AttributeError): return None
