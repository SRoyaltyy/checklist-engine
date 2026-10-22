"""Trading Bot Taskforce reader. answer(ticker, date) -> list of dicts
{row_id, ticker, date, answer (YES/NO/NOT_READY), reason, data_as_of} for every Taskforce row:
v8.1 compact ids (PV-TFC-*) first, then the 224 timeframe rows (PV-TFX-*), then the v10.5 full file (PV-TF-*).
Point in time: only daily bars dated < D (last = D-1 close, known 16:00 ET D-1, before the 09:25 ET cutoff);
splits with ex-date <= D applied (tf/adjust.py). Data: Yahoo chart API (cached in engine/cache/taskforce/)."""
import os, sys, json, re, time, datetime as dt, urllib.request, csv
import numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,'/workspace/tf')
import importlib; I=importlib.import_module('_tf_ind'); from adjust import adjust
ROOT=os.path.dirname(os.path.dirname(HERE)); INBOX=os.path.join(ROOT,'inbox'); CACHE=os.path.join(os.path.dirname(HERE),'cache','taskforce')
os.makedirs(CACHE,exist_ok=True)
FULL=os.path.join(INBOX,'trading-bot-taskforce.csv'); COMP=os.path.join(INBOX,'trading-bot-taskforce.compact.csv'); TFX=os.path.join(INBOX,'trading-bot-taskforce-timeframes.csv')
SECT={'Technology':'XLK','Financial Services':'XLF','Healthcare':'XLV','Consumer Cyclical':'XLY','Consumer Defensive':'XLP','Energy':'XLE','Industrials':'XLI','Basic Materials':'XLB','Utilities':'XLU','Real Estate':'XLRE','Communication Services':'XLC'}
SECT_START={'XLRE':'2015-10-08','XLC':'2018-06-19'}
_ROWS=None
def rows():
    global _ROWS
    if _ROWS is None:
        f=pd.read_csv(FULL,dtype=str,keep_default_na=False); x=pd.read_csv(TFX,dtype=str,keep_default_na=False); c=pd.read_csv(COMP,dtype=str,keep_default_na=False)
        c['folded']=c.notes.str.extract(r'folded ids [^(]*\(([^)]*)\)')[0].fillna('')
        _ROWS=(f,x,c)
    return _ROWS
# ---------------- data ----------------
def _get(url):
    for k in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30))
        except Exception as e:
            err=e; time.sleep(2**k)
    raise err
def _et_now(): return pd.Timestamp.now(tz='America/New_York')
def raw_bars(sym,D):
    """Raw as-traded daily bars + split list. Cache refetched only if it was fetched before D (so fixed inputs -> fixed output)."""
    fn=os.path.join(CACHE,f'y_{sym.replace("^","_")}.json')
    need=True
    if os.path.exists(fn):
        j=json.load(open(fn)); need=pd.Timestamp(j['fetched_et'][:10])<pd.Timestamp(D)
    if need:
        try:
            d=_get(f'https://query2.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2={int(time.time())}&interval=1d&events=splits')
            j={'fetched_et':str(_et_now()),'chart':d}; json.dump(j,open(fn,'w'))
        except Exception as e:
            if not os.path.exists(fn): return None,None,f'fetch_failed:{type(e).__name__}'
            j=json.load(open(fn))
    r=(j['chart'].get('chart',{}).get('result') or [None])[0]
    if not r or 'timestamp' not in r: return None,None,'no_yahoo_history'
    q=r['indicators']['quote'][0]
    idx=pd.to_datetime(r['timestamp'],unit='s',utc=True).tz_convert('America/New_York').normalize().tz_localize(None)
    df=pd.DataFrame({k.capitalize():q[k] for k in ('open','high','low','close','volume')},index=idx).dropna(subset=['Open','High','Low','Close'])
    df=df[~df.index.duplicated(keep='last')].astype(float); df['Volume']=df['Volume'].fillna(0)
    fet=pd.Timestamp(j['fetched_et']); 
    if fet.hour*60+fet.minute<16*60+15: df=df[df.index<fet.tz_localize(None).normalize()]  # drop an unfinished live bar
    sp=sorted((pd.Timestamp(v['date'],unit='s').normalize(),v['numerator']/v['denominator']) for v in r.get('events',{}).get('splits',{}).values())
    raw=df.copy()
    for ex,ratio in sp:
        m=raw.index<ex; raw.loc[m,['Open','High','Low','Close']]*=ratio; raw.loc[m,'Volume']/=ratio
    return raw,sp,None
def bars_at(sym,D,trunc=None):
    raw,sp,err=raw_bars(sym,D)
    if err: return None,err
    if trunc is not None: raw=raw[raw.index<=pd.Timestamp(trunc)]
    b=adjust(raw,sp,D)
    return (b if len(b) else None),(None if len(b) else 'no_history_before_date')
def sector_etf(t):
    fn=os.path.join(CACHE,'sectors.json'); m=json.load(open(fn)) if os.path.exists(fn) else {}
    if t not in m:
        try:
            q=_get(f'https://query2.finance.yahoo.com/v1/finance/search?q={t}&quotesCount=3&newsCount=0')['quotes']
            q=[x for x in q if x.get('symbol')==t]; m[t]=q[0].get('sector','') if q else ''
        except Exception: return None
        json.dump(m,open(fn,'w'),sort_keys=True)
    return SECT.get(m[t])
# ---------------- helpers ----------------
def pr(s,n=252):
    """percentile rank (0..100) of the last value within its own last n values (incl. itself)."""
    w=s.iloc[-n:].to_numpy(float)
    if len(w)<n or np.isnan(w).any(): return np.nan
    return (w<=w[-1]).mean()*100
def pr_series(s,n=252,k=1): return [pr(s.iloc[:len(s)-j] if j else s,n) for j in range(k)]
NR=lambda r:('NOT_READY',r)
def yn(b, reason):
    if not reason or not str(reason).strip():
        raise ValueError('yn requires non-empty reason')
    return ('YES' if b else 'NO', str(reason).strip())
def num_thr(defn):
    m=re.findall(r'YES if X_N\s*(>=|<=)\s*([-+0-9.e]+)',defn); return (m[-1][0],float(m[-1][1])) if m else None
N_RE=re.compile(r'window N=(\d+)')
# ---------------- engine ----------------
class Ctx:
    def __init__(s,t,D,trunc=None):
        s.t=t; s.D=D; s.trunc=trunc; s.b,s.err=bars_at(t,D,trunc); s.X={}; s.XS={}
        s.spy,_=bars_at('SPY',D,trunc)
        if s.b is not None:
            s.M,s.ctx=I.build(s.b,None if s.spy is None else s.spy.Close)
            s.asof=str(s.b.index[-1].date())
        else: s.asof=''
        s._sec=None
    def sec(s):
        if s._sec is None:
            e=sector_etf(s.t); s._sec=('err','sector_unknown')
            if e:
                if s.D<SECT_START.get(e,'1998-12-22'): s._sec=('err',f'sector_etf_{e}_not_trading_yet')
                else:
                    b,err=bars_at(e,s.D,s.trunc); s._sec=('err',err) if b is None else (e,b)
        return s._sec
    def series(s,v,bars=None):
        key=(v,id(bars)); cache=s.X
        if key in cache: return cache[key]
        if bars is None: M=s.M
        else: M,_=I.build(bars,None if s.spy is None else s.spy.Close)
        f=M.get(v); x=None
        if callable(f):
            try: x=f()
            except Exception as e: x=None
            if x is not None: x=pd.Series(x,dtype=float).replace([np.inf,-np.inf],np.nan)
        if v.startswith('CDL'):
            import talib as ta; b=bars if bars is not None else s.b
            x=pd.Series(getattr(ta,v)(*[b[k].to_numpy(float) for k in ('Open','High','Low','Close')]),index=b.index).astype(float)
        cache[key]=x; return x
def market_series(ctx,v):
    if v=='VIX level': b,e=bars_at('^VIX',ctx.D,ctx.trunc); return (None,e) if b is None else (b.Close,None)
    if v=='VIX term structure':
        a,e=bars_at('^VIX',ctx.D,ctx.trunc); b,e2=bars_at('^VIX3M',ctx.D,ctx.trunc)
        if a is None or b is None: return None,e or e2
        x=(a.Close/b.Close.reindex(a.index)).dropna(); return (x if len(x) else None),'vix3m_not_published_yet'
    return None,None
NOSRC={'Halt code':'source_not_wired:nasdaq_trader_halts_feed','Earnings':'source_not_wired:finviz_elite_earnings','Short volume':'source_not_wired:finra_regsho_daily_files'}
NOSRC_V={'Days to cover':'source_not_wired:finra_short_interest','Short % of float':'source_not_wired:finra_short_interest_and_float','Short interest change':'source_not_wired:finra_short_interest',
 'Fails-to-deliver % of float':'source_not_wired:sec_ftd_files','Halted (any code)':'source_not_wired:nasdaq_trader_halts_feed'}
NOT_IMPL={'Close vs Holt-Winter MA','Close vs Jurik MA 7','Holt-Winter channel position','Hurst exponent 100','Even better sinewave (40,10)','Ehlers reflex 20','Ehlers trendflex 20','ATR trailing stop side',
 'Klinger volume oscillator / avg V','Inertia (RVI 14 linreg 20)','QQE line minus signal','Jurik RSX 14','Smart money concept: order-block side','Schaff trend cycle (10,23,50)','True momentum oscillator 14',
 'AlphaTrend side','Chande Kroll stop side','Linear decay of signal 5'}
def eval_grid(ctx,r):
    v=r['variant']; L=r['lens']; but='(BUT)' in L; L=L.replace(' (BUT)',''); defn=r['strict_definition']; t=r['data_type']
    if L in ('rank_sector','rank_market'): return NR('needs_cross_section_universe:'+L)
    m=N_RE.search(defn); N=int(m.group(1)) if m else 1
    event=defn.startswith('event:') or ('K=count of events' in defn)
    if v in I.N_DEP:
        bench=None
        if v=='Return vs SPY': bench=None if ctx.spy is None else ctx.spy.Close
        if v=='Return vs sector ETF':
            e,b=ctx.sec(); 
            if e=='err': return NR(b)
            bench=b.Close
        Xn=I.ndep(v,ctx.ctx,N,bench); X=I.ndep(v,ctx.ctx,1,bench) if v not in ('Strictly decreasing over N','Strictly increasing over N') else Xn
        if Xn is None: return NR('not_implemented:'+v)
    else:
        if t=='Market shock':
            X,e=market_series(ctx,v)
            if X is None: return NR(e or 'no_data')
            if L in ('div_sector','div_volume'): return NR('not_applicable:market_series_has_no_'+L[4:])
            X=X.reindex(ctx.b.index).ffill() if ctx.b is not None else X
        else:
            if v in NOT_IMPL: return NR('not_implemented:'+v)
            X=ctx.series(v)
            if X is None: return NR('not_implemented:'+v)
        if event: X=(X!=0).astype(float).where(X.notna())
        Xn=X if N==1 else (X.rolling(N).sum() if event else X.rolling(N).mean())
    B=Xn if event else X          # series the change/cross/streak/div lenses read
    if len(Xn)<2 or np.isnan(Xn.iloc[-1]): return NR('insufficient_history')
    x=Xn.iloc[-1]
    if L=='level':
        if event: return yn(x==0, f'BUT {v} count==0') if but else yn(x>=1, f'{v} count>=1')
        th=num_thr(defn)
        if not th: return NR('rule_unparsed')
        op,val=th; return yn(x>=val if op=='>=' else x<=val, (f'BUT {v}{op}{val}' if but else f'{v}{op}{val}'))
    if L=='extreme':
        w=Xn.iloc[-252:]
        if len(w)<252 or w.isna().any(): return NR('insufficient_history:252d')
        p5,p95=np.percentile(w,5),np.percentile(w,95)
        # tie rule: on a flat/degenerate distribution (p5==p95) a value can't be both top and bottom, so require x strictly off the other tail
        if but: return yn(x<=p5 and x<p95, f'BUT {v}<=p5')
        return yn(x>=p95 and x>p5 and (x>=1 if event else True), f'{v}>=p95')
    if L=='change':
        ch=B-B.shift(N); w=ch.iloc[-252:]
        if len(w)<252 or w.isna().any(): return NR('insufficient_history:252d')
        d=ch.iloc[-1]; big=abs(d)>=0.5*w.std()
        return yn(d<0 and big, f'BUT {v} down_big N={N}') if but else yn(d>0 and big, f'{v} up_big N={N}')
    if L=='cross':
        if event:
            mu=Xn.rolling(60).mean().iloc[-1]; a,b_=Xn.iloc[-2],Xn.iloc[-1]
            if np.isnan(mu) or np.isnan(a): return NR('insufficient_history:60d')
            return yn(a>=mu and b_<mu, f'BUT {v} cross_below_ma60') if but else yn(a<=mu and b_>mu, f'{v} cross_above_ma60')
        sm=X.rolling(N).mean(); a,b_,ma,mb=X.iloc[-2],X.iloc[-1],sm.iloc[-2],sm.iloc[-1]
        if np.isnan([a,b_,ma,mb]).any(): return NR('insufficient_history')
        return yn(a>=ma and b_<mb, f'BUT {v} cross_below_sma{N}') if but else yn(a<=ma and b_>mb, f'{v} cross_above_sma{N}')
    if L=='streak':
        d=B.diff().iloc[-N:]
        if len(d)<N or d.isna().any(): return NR('insufficient_history')
        f=(d<0) if but else (d>0); return yn(f.all() if N<=10 else f.mean()>=0.8, f'BUT {v} down_streak N={N}' if but else f'{v} up_streak N={N}')
    if L in ('div_price','div_volume','div_sector'):
        if len(B)<=N or np.isnan(B.iloc[-1-N]): return NR('insufficient_history')
        dX=B.iloc[-1]-B.iloc[-1-N]
        if L=='div_price':
            c=ctx.ctx['c']; ret=c.iloc[-1]/c.iloc[-1-N]-1; return yn(dX<0 and ret>0, f'BUT {v} div_price') if but else yn(dX>0 and ret<0, f'{v} div_price')
        if L=='div_volume':
            vv=ctx.ctx['v']; rv=vv.iloc[-N:].mean()/vv.iloc[-50:].mean()
            if len(vv)<50 or not np.isfinite(rv): return NR('insufficient_history:50d_volume')
            return yn(dX>0 and rv>=1.5, f'BUT {v} div_vol_high') if but else yn(dX>0 and rv<0.8, f'{v} div_vol_low')
        e,sb=ctx.sec()
        if e=='err': return NR(sb)
        if v in I.N_DEP: return NR('not_applicable:relative_variant_on_sector_etf')
        XS=ctx.series(v,sb)
        if XS is None: return NR('not_implemented:'+v)
        if event: XS=(XS!=0).astype(float).where(XS.notna())
        XSn=XS if N==1 else (XS.rolling(N).sum() if event else XS.rolling(N).mean())
        SB=XSn if event else XS
        if len(SB)<=N or np.isnan(SB.iloc[-1]) or np.isnan(SB.iloc[-1-N]): return NR('insufficient_history:sector_etf')
        dS=SB.iloc[-1]-SB.iloc[-1-N]; return yn(dX<0 and dS>0, f'BUT {v} div_sector') if but else yn(dX>0 and dS<0, f'{v} div_sector')
    return NR('lens_not_implemented:'+L)
def eval_position(ctx,r):
    v=r['variant']; L=r['lens']; but='(BUT)' in L; L=L.replace(' (BUT)',''); defn=r['strict_definition']
    if L in ('level','extreme','change','cross','streak','div_price','div_sector','div_volume','rank_sector','rank_market'): return eval_grid(ctx,r)
    m=re.search(r'X_N = mean of last (\d+)',defn); N=int(m.group(1)) if m else 1
    X=ctx.series(v)
    if X is None: return NR('not_implemented:'+v)
    Xn=X if N==1 else X.rolling(N).mean()
    if L in ('quartile','quintile','decile','pct own 1y'):
        p=pr(Xn)
        if np.isnan(p): return NR('insufficient_history:252d')
        q={'quartile':75,'quintile':80,'decile':90,'pct own 1y':80}[L]; return yn(p<=100-q, f'BUT {v} {L}<={100-q}') if but else yn(p>=q, f'{v} {L}>={q}')
    if L=='quartile change':
        p1=pr(Xn); p2=pr(Xn.iloc[:-1])
        if np.isnan(p1) or np.isnan(p2): return NR('insufficient_history:252d')
        q1,q2=min(int(p1//25),3),min(int(p2//25),3); return yn(q1<q2, f'BUT {v} quartile_down') if but else yn(q1>q2, f'{v} quartile_up')
    if L=='div RSI position':
        k=max(N,5); rs=ctx.ctx['rsi']; rp=(rs-rs.rolling(k).min())/(rs.rolling(k).max()-rs.rolling(k).min())
        if len(Xn)<=N or np.isnan([Xn.iloc[-1],Xn.iloc[-1-N],rp.iloc[-1],rp.iloc[-1-N]]).any(): return NR('insufficient_history')
        dx=Xn.iloc[-1]-Xn.iloc[-1-N]; dr=rp.iloc[-1]-rp.iloc[-1-N]; return yn(dx>0 and dr<0, f'BUT {v} div_RSI') if but else yn(dx<0 and dr>0, f'{v} div_RSI')
    if L=='days in zone':
        ps=[pr(Xn.iloc[:len(Xn)-j] if j else Xn) for j in range(N)]
        if np.isnan(ps).any(): return NR('insufficient_history:252d')
        return yn(all(p<=25 for p in ps), f'BUT {v} days_in_bottom N={N}') if but else yn(all(p>=75 for p in ps), f'{v} days_in_top N={N}')
    return NR('lens_not_implemented:'+L)
def eval_streak(ctx,r):
    v=r['variant']; L=r['lens'].replace(' (BUT)','')   # BUT rows here share the trigger (hypothesis B) -> same answer
    X=ctx.series(v)
    if not L.startswith(('streak length','pct own')): return NR('needs_cross_section_universe:'+L) if L=='pct vs sector' else eval_grid(ctx,r)
    if X is None or np.isnan(X.iloc[-1]): return NR('insufficient_history')
    k=X.iloc[-1]
    if L.startswith('streak length'):
        K=L.split()[-1]; return yn(k>=10, f'{v} streak>=10') if K=='10+' else yn(k==int(K), f'{v} streak=={K}')
    n=252 if '1y' in L else 756; w=X.iloc[-n-1:-1].to_numpy()
    if len(w)<n: return NR(f'insufficient_history:{n}d')
    ends=[w[i] for i in range(len(w)-1) if w[i]>0 and w[i+1]==0]
    if not ends: return NR('no_completed_streaks_in_window')
    return yn(k>=np.percentile(ends,90) and k>0, f'{v} streak_top10pct')
def outliers(ctx,col,lens_metric):
    b=ctx.b; o,h,l,c,v,atr=[ctx.ctx[k] for k in ('o','h','l','c','v','atr')]
    m=lens_metric
    if m.startswith('move >'):
        k=float(m.split('>')[1].split()[0]); big=(c-c.shift()).abs()>k*atr.shift()
    else:
        met,_,p=m.split(); p=float(p.rstrip('%')); s={'body':(c-o).abs(),'range':h-l,'move':(c/c.shift()-1).abs(),'volume':v}[met]
        q=s.shift().rolling(252).quantile(1-p/100); big=(s>=q)&q.notna()
    colm=(c>o) if col=='green' else (c<o); return (big&colm).to_numpy()
def eval_outlier(ctx,r):
    v=r['variant']; lens=r['lens'].replace(' (BUT)',''); tfm=r['timeframe']; col='green' if 'green' in v else 'red'
    metric=lens.split(';')[0].strip(); zone=lens.split(';')[1].strip() if ';' in lens else ''
    if len(ctx.b)<260: return NR('insufficient_history:252d')
    try: ob=outliers(ctx,col,metric)
    except Exception as e: return NR('rule_unparsed')
    n=len(ob); H,L,C,O,V=[ctx.b[k].to_numpy(float) for k in ('High','Low','Close','Open','Volume')]
    idx=[i for i in range(max(0,n-20),n) if ob[i]]; last=idx[-1] if idx else None; since=list(range(last+1,n)) if last is not None else []
    if 'within last N days' in v:
        Lw=int(re.search(r'last (\d+)d',tfm).group(1)); return yn(ob[n-Lw:].any(), f'{col} outlier within_{Lw}d')
    if v.startswith('days since'):
        a,b_=map(int,re.search(r'(\d+)-(\d+)d',zone).groups()); return yn(last is not None and a<=n-1-last<=b_, f'days_since_{col}_outlier {a}-{b_}')
    if last is None: return yn(False, f'no_{col}_outlier_20d')
    Ho,Lo=H[last],L[last]; mid=(Ho+Lo)/2; c1=C[-1]
    if 'close vs' in v:
        z={'above its high':c1>Ho,'top half':mid<=c1<=Ho,'below midpoint':Lo<=c1<mid,'below its low':c1<Lo}[zone]; return yn(z, f'{col} close_{zone.replace(" ","_")}')
    if 'level retested' in v:
        x={'high':Ho,'low':Lo,'mid':mid}[zone]; return yn(any(L[i]<=x<=H[i] for i in since), f'{col} level_retested_{zone}')
    if 'gap unfilled' in v:
        if last==0: return NR('insufficient_history')
        pc=C[last-1]; g=O[last]/pc-1; gapped=g>=0.01 if col=='green' else g<=-0.01
        filled=any((L[i]<=pc) if col=='green' else (H[i]>=pc) for i in since); return yn(gapped and not filled, f'{col} gap_unfilled')
    if 'follow-through' in v:
        Lw=int(re.search(r'within (\d+)d',tfm).group(1)); rec=[i for i in range(n-Lw,n) if ob[i]]
        if not rec: return yn(False, f'no_{col}_outlier_followthrough')
        lt=rec[-1]; s=list(range(lt+1,n))
        if len(s)<2: return yn(False, f'{col} followthrough_lt2bars')
        dirn=[(C[i]>C[i-1]) if col=='green' else (C[i]<C[i-1]) for i in s]; return yn(np.mean(dirn)>=0.6, f'{col} followthrough')
    if 'cluster' in v:
        Lw=int(re.search(r'last (\d+)d',tfm).group(1)); return yn(ob[n-Lw:].sum()>=2, f'{col} outlier_cluster_{Lw}d')
    if 'volume since' in v:
        if not since: return yn(False, f'no_bars_since_{col}_outlier')
        mv=np.mean([V[i] for i in since]); return yn(mv<=0.5*V[last], f'{col} volume_fading') if 'fading' in zone else yn(mv>=V[last], f'{col} volume_holding')
    return NR('rule_unparsed')
def eval_tug(ctx,r):
    v=r['variant']; cn=r['lens'].replace(' (BUT)','').replace('context: ','')
    if cn.startswith('mcap'): return NR('source_not_wired:point_in_time_market_cap')
    c,o,h,l,vv,atr=[ctx.ctx[k] for k in ('c','o','h','l','v','atr')]
    if len(c)<260: return NR('insufficient_history')
    ret=c.pct_change(); sd=ret.shift().rolling(60).std(); up=(ret>=2.5*sd); dn=(ret<=-2.5*sd)
    g=I.consec(c>c.shift()); rd=I.consec(c<c.shift()); vf=(vv<vv.shift()).iloc[-3:].all(); bf=((c-o).abs()<(c-o).abs().shift()).iloc[-3:].all()
    trig={'Up streak + up-outlier on rising volume':g.iloc[-1]>=4 and up.iloc[-1] and vv.iloc[-1]>vv.iloc[-2],
     'Up streak, no outlier, shrinking volume':g.iloc[-1]>=4 and not up.iloc[-3:].any() and vf,
     'Up streak, no outlier, shrinking bodies':g.iloc[-1]>=4 and not up.iloc[-3:].any() and bf,
     'Stretch >3 ATR + recent up-outlier':((c-I.sma(c,20))/atr).iloc[-1]>3 and up.iloc[-3:].any(),
     'Down streak + red outlier closing near low':rd.iloc[-1]>=4 and dn.iloc[-1] and (h.iloc[-1]>l.iloc[-1]) and (c.iloc[-1]-l.iloc[-1])/(h.iloc[-1]-l.iloc[-1])<=0.1,
     'Down streak, no outlier, shrinking volume':rd.iloc[-1]>=4 and not dn.iloc[-3:].any() and vf}[v]
    ap=(atr/c).iloc[-1]
    if cn=='all': cx=True
    elif cn.startswith('ATR%'): cx={'low':ap<0.02,'mid':0.02<=ap<0.04,'high':0.04<=ap<0.08,'extreme':ap>=0.08}[cn.split()[1]]
    elif 'SPY' in cn:
        s=ctx.spy.Close; ab=s.iloc[-1]>s.iloc[-50:].mean(); cx=ab if 'above' in cn else not ab
    else:
        ab=c.iloc[-1]>c.iloc[-200:].mean(); cx=ab if 'above' in cn else not ab
    return yn(bool(trig) and bool(cx), f'tug:{v}|{cn}')
def eval_squeeze(ctx,r):
    X=ctx.series('Bollinger bandwidth'); w=X.iloc[-253:-1]
    if len(w)<252 or w.isna().any() or np.isnan(X.iloc[-1]): return NR('insufficient_history:252d')
    p=(w<=X.iloc[-1]).mean()*100; return yn(p>=90, 'BUT bandwidth>=p90') if '(BUT)' in r['lens'] else yn(p<=10, 'bandwidth<=p10')
def eval_full(ctx,r):
    t=r['data_type']; v=r['variant']
    if ctx.b is None: return NR(ctx.err)
    if t in NOSRC: return NR(NOSRC[t])
    if v in NOSRC_V: return NR(NOSRC_V[v])
    if t=='Position': return eval_position(ctx,r)
    if t=='Stretch/exhaustion' and v.startswith('Consecutive'): return eval_streak(ctx,r)
    if t=='Outlier anchor': return eval_outlier(ctx,r)
    if t=='Tug of war': return eval_tug(ctx,r)
    if 'squeeze: bandwidth' in v: return eval_squeeze(ctx,r)
    return eval_grid(ctx,r)
# ---------------- timeframe (2D/3D/W/M) rows ----------------
def tf_bars(ctx,tf,mode):
    b=ctx.b; D=pd.Timestamp(ctx.D)
    if tf in ('2D','3D'):
        cal=ctx.spy.index; cal=cal[cal>=pd.Timestamp('1993-01-29')]; k=int(tf[0])
        b=b[b.index.isin(cal)]; pos=cal.get_indexer(b.index); ids=pos//k
        allc=cal.append(pd.DatetimeIndex([D])) if D not in cal else cal
        # period of D: D's position on the session calendar (D itself is not yet in the bars)
        dpos=len(cal[cal<D]); cur=dpos//k
    elif tf=='W': iso=b.index.isocalendar(); ids=(iso.year*100+iso.week).to_numpy(); ic=D.isocalendar(); cur=ic[0]*100+ic[1]
    else: ids=(b.index.year*100+b.index.month).to_numpy(); cur=D.year*100+D.month
    ids=np.asarray(ids); done=b[ids!=cur]; part=b[ids==cur]
    def agg(x,i):
        g=x.assign(end=x.index).groupby(i,sort=True)
        return pd.DataFrame({'Open':g.Open.first(),'High':g.High.max(),'Low':g.Low.min(),'Close':g.Close.last(),'end':g.end.last()}).set_index('end')
    out=agg(done,ids[ids!=cur])
    if mode=='ptd' and len(part): out=pd.concat([out,agg(part,ids[ids==cur])])
    return out
def eval_tfx(ctx,r):
    if ctx.b is None: return NR(ctx.err)
    sys.path.insert(0,'/workspace/tf/tfx'); import tfx as T
    tf,mode=r['chart_timeframe'],r['bar_mode']; key=('tf',tf,mode)
    if key not in ctx.XS: ctx.XS[key]=tf_bars(ctx,tf,mode)
    bb=ctx.XS[key]; c=bb.Close; v=r['variant']; L=r['lens']; but='(BUT)' in L; L=L.replace(' (BUT)',''); dfn=r['strict_definition']
    if v.startswith('RSI14'): X=T.rsi(c)
    elif v.startswith('MACD'): X=T.macd(c)
    elif v.startswith('Bollinger'): X=T.pctb(c)
    elif v.startswith('Close vs SMA20'): X=c/c.rolling(20).mean()-1
    elif v.startswith('Close vs SMA50'): X=c/c.rolling(50).mean()-1
    elif v.startswith('SMA20 vs SMA50'): X=c.rolling(20).mean()/c.rolling(50).mean()-1
    else: return NR('rule_unparsed')
    if len(X)<2 or np.isnan(X.iloc[-1]) or np.isnan(X.iloc[-2]): return NR(f'insufficient_history:{tf}_bars')
    a,b_=X.iloc[-2],X.iloc[-1]; rule=dfn.split('YES if ')[-1]
    if L=='level':
        m=re.search(r'X on the last bar (>=|<=|>|<)\s*([-0-9.]+)',rule); op,val=m.group(1),float(m.group(2))
        return yn({'>=':b_>=val,'<=':b_<=val,'>':b_>val,'<':b_<val}[op], f'{v} {op}{val}')
    if L=='change':
        m=re.search(r'(>=|<=)\s*(-?[0-9.]+) points',rule)
        if m: val=float(m.group(2)); return yn(b_-a>=val if m.group(1)=='>=' else b_-a<=val, f'{v} change{m.group(1)}{val}')
        return yn(b_<a, f'BUT {v} down') if but else yn(b_>a, f'{v} up')
    if L=='cross':
        m=re.search(r'crosses (above|below) ([0-9.]+)',rule)
        if m:
            val=float(m.group(2)); return yn(a<val<=b_, f'{v} cross_above_{val}') if m.group(1)=='above' else yn(a>=val>b_, f'{v} cross_below_{val}')
        return yn(a>=0 and b_<0, f'BUT {v} cross_below_0') if but else yn(a<=0 and b_>0, f'{v} cross_above_0')
    return NR('lens_not_implemented:'+L)
# ---------------- public API ----------------
TWIN_SAME=('Stretch/exhaustion','Outlier anchor','Tug of war')
def answer(ticker, date, rows_filter=None, _trunc=None):
    f,x,c=rows(); ctx=Ctx(ticker.upper(),date,_trunc); full={}
    for r in f.to_dict('records'):
        try: a,why=eval_full(ctx,r)
        except Exception as e: a,why='NOT_READY',f'engine_error:{type(e).__name__}'
        full[r['id']]=(a,why)
    out=[]
    def add(i,a,why): out.append({'row_id':i,'ticker':ticker.upper(),'date':date,'answer':a,'reason':why,'data_as_of':ctx.asof if a!='NOT_READY' or ctx.asof else ''})
    for r in c.to_dict('records'):
        ids=[s for s in r['folded'].split(',') if s]; ans=[full[i] for i in ids if i in full]
        if not ans: add(r['id'],'NOT_READY','removed_from_full_file'); continue
        if any(a=='YES' for a,_ in ans):
            why=next((w for a,w in ans if a=='YES' and w), 'folded_any_YES'); add(r['id'],'YES',why)
        elif all(a=='NO' for a,_ in ans):
            why=next((w for a,w in ans if w), 'folded_all_NO'); add(r['id'],'NO',why)
        else: add(r['id'],'NOT_READY','some_folded_timeframes_not_ready:'+sorted({w for a,w in ans if a=='NOT_READY'})[0])
    for r in x.to_dict('records'):
        try: a,why=eval_tfx(ctx,r)
        except Exception as e: a,why='NOT_READY',f'engine_error:{type(e).__name__}'
        add(r['id'],a,why)
    for i,(a,why) in full.items(): add(i,a,why)
    if rows_filter: out=[o for o in out if o['row_id'] in set(rows_filter)]
    check_twins(out)
    return out
def twin_pairs():
    f,x,c=rows(); P=[]
    for df in (f,x,c):
        ids=df.id.tolist(); lens=df.lens.tolist(); dd=df.strict_definition.tolist()
        for k in range(len(ids)-1):
            if '(BUT)' not in lens[k] and lens[k+1]==lens[k]+' (BUT)': P.append((ids[k],ids[k+1],'same trigger' in dd[k+1]))
    return P
TWIN_STATS={}
def check_twins(out):
    A={o['row_id']:o['answer'] for o in out}; s={'pairs':0,'both_yes':0,'opposite':0,'both_no':0,'same_trigger_equal':0}
    for a,b,same in twin_pairs():
        x,y=A.get(a),A.get(b)
        if x not in ('YES','NO') or y not in ('YES','NO'): continue
        s['pairs']+=1
        if same:
            s['same_trigger_equal']+=x==y
            if x!=y: s.setdefault('violations',[]).append((a,b,x,y))
            continue
        if a.startswith('PV-TFC'):  # compact rows OR over timeframes, so both can be YES on different N
            s['opposite']+=x!=y; s['both_no']+=x==y=='NO'; s['both_yes']+=x==y=='YES'; continue
        if x==y=='YES': s.setdefault('violations',[]).append((a,b,x,y))
        s['opposite']+=x!=y; s['both_no']+=x==y=='NO'
    TWIN_STATS.clear(); TWIN_STATS.update(s)
