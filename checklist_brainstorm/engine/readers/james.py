"""James checklist v5.5f answer engine (point-in-time, data known by 09:25 ET on D).
answer(ticker, date) -> list of dicts: row_id,ticker,date,answer(YES/NO/NOT_READY),reason,data_as_of
Daily bars used are strictly < D (last completed session = D-1). Fetched series are cached
under engine/cache/ (first fetch wins) so reruns are byte-identical."""
import os, re, json, math, time, datetime as dt, io, csv, sys
import numpy as np, pandas as pd, requests
HERE=os.path.dirname(os.path.realpath(__file__)); ROOT=os.path.dirname(os.path.dirname(HERE))
ROWS=os.path.join(ROOT,'v8src','James-v5.5f.csv'); CACHE=os.path.join(os.path.dirname(HERE),'cache')
UA={'User-Agent':'Mozilla/5.0'}
HELD_SOURCES=('SOFR','reverse repo','TreasuryDirect','fiscaldata','yield curve')  # new sources: 2 clean nightly pulls pending
_mem={}
# Theme Radar D-1 Finviz universe for PIT stock->SPDR sector map
sys.path.insert(0, HERE)
from _theme_radar_universe import universe as _tr_universe

# Finviz Sector (and common aliases) -> Select Sector SPDR ticker.
# Limitation: for answer date D we take a single PIT assignment from universe(D)
# (snapshot_date < D) and apply that SPDR to the whole Yahoo price history — we do
# not reconstruct multi-year membership-change history.
SECTOR_TO_SPDR = {
    'Technology': 'XLK',
    'Financial': 'XLF', 'Financials': 'XLF',
    'Health Care': 'XLV', 'Healthcare': 'XLV',
    'Energy': 'XLE',
    'Consumer Discretionary': 'XLY', 'Consumer Cyclical': 'XLY',
    'Consumer Staples': 'XLP', 'Consumer Defensive': 'XLP',
    'Industrials': 'XLI',
    'Materials': 'XLB', 'Basic Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
    'Communication Services': 'XLC',
}
def _get(u):
    e=None
    for i in range(4):
        try:
            r=requests.get(u,headers=UA,timeout=40)
            if r.status_code==429: time.sleep(5*(i+1)); continue
            r.raise_for_status(); return r
        except Exception as x: e=x; time.sleep(2)
    raise RuntimeError(f'fetch failed {u}: {e}')
def series(sym):
    """daily OHLCV DataFrame indexed by date (session date). cached forever."""
    if sym in _mem:
        if isinstance(_mem[sym],Exception): raise _mem[sym]
        return _mem[sym]
    f=os.path.join(CACHE,re.sub(r'[^A-Za-z0-9=._-]','_',sym)+'.csv')
    if os.path.exists(f):
        df=pd.read_csv(f,index_col=0,parse_dates=True)
    else:
        if sym.startswith('FRED:'):
            df=_fred_via_treasury(sym[5:])
            for c in ('open','high','low'): df[c]=df.close   # candle = close-to-close per row definition
            df['volume']=np.nan
        elif sym.startswith('CB:'):  # Coinbase Exchange public candles, 00:00 UTC bars
            out=[]; end=pd.Timestamp.now('UTC').normalize(); start=pd.Timestamp('2015-07-20',tz='UTC')
            while end>start:
                s=max(start,end-pd.Timedelta(days=299))
                j=_get(f'https://api.exchange.coinbase.com/products/{sym[3:]}/candles?granularity=86400&start={s.isoformat()}&end={end.isoformat()}').json()
                out+=j; end=s-pd.Timedelta(days=1); time.sleep(0.4)
            d=pd.DataFrame(out,columns=['t','low','high','open','close','volume']).drop_duplicates('t')
            d['date']=pd.to_datetime(d.t,unit='s'); df=d.set_index('date')[['open','high','low','close','volume']].sort_index()
        else:
          try:
            j=_get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2=9999999999&interval=1d&events=split').json()
            r=j['chart']['result'][0]; q=r['indicators']['quote'][0]
            idx=pd.to_datetime(pd.Series(r['timestamp'])+r['meta'].get('gmtoffset',0),unit='s').dt.normalize()
            df=pd.DataFrame({k:q[k] for k in ('open','high','low','close','volume')},index=idx).dropna(subset=['close'])
            df=df[~df.index.duplicated(keep='last')]
          except Exception as e:
            err=NR(f'data_source_gap: Yahoo has no chart for {sym} (delisted/renamed?)'); _mem[sym]=err; raise err
        df.index.name='date'; df=df.sort_index(); df.to_csv(f)
    _mem[sym]=df; return df
def pit(sym,D):
    df=series(sym)
    # Asian cash sessions on D close before 09:25 ET on D (Tokyo/Taipei/Seoul/HK close 01:30-04:10 ET)
    df=df[df.index<=pd.Timestamp(D)] if sym in ('^N225','^TWII','^KS11','^HSI') else df[df.index<pd.Timestamp(D)]
    if sym.startswith('CB:'): df=df[df.index<=pd.Timestamp(D)-pd.Timedelta(days=1)]  # bar for D-1 UTC closes 20:00 ET D-1
    return df
class NR(Exception): pass
def spdr_for(ticker, D):
    """Point-in-time SPDR sector ETF for ticker on answer date D via theme-radar universe(D)."""
    d = pd.Timestamp(D).strftime('%Y-%m-%d')
    u = _tr_universe(d)
    if u is None: raise NR('no_universe_snapshot')
    if ticker not in u.index: raise NR('ticker_not_in_universe')
    sector = str(u.loc[ticker, 'Sector'] if 'Sector' in u.columns else '').strip()
    if not sector or sector.lower() in ('nan', 'none', ''): raise NR('ticker_missing_from_universe')
    etf = SECTOR_TO_SPDR.get(sector)
    if not etf: raise NR(f'no_spdr_for_sector: {sector}')
    return etf
def _align_close(a, b):
    c, e = a.close.align(b.close, join='inner')
    both = pd.concat([c.rename('a'), e.rename('b')], axis=1).dropna()
    return both['a'], both['b']
def sector_measure_from_cond(cond, ticker, D):
    """Build a .close measure series for slow_meta from an inlined sector-row parent condition."""
    etf = spdr_for(ticker, D)
    st, se = pit(ticker, D), pit(etf, D)
    m = re.search(r"stock (\d+)-session return minus its SPDR sector ETF (\d+)-session return", cond)
    if m:
        N = int(m.group(1))
        c, e = _align_close(st, se)
        meas = (c.pct_change(N) - e.pct_change(N)) * 100
        return pd.DataFrame({'close': meas}).dropna()
    m = re.search(r"stock's SPDR sector ETF (\d+)-session return minus SPY (\d+)-session return", cond)
    if m:
        N = int(m.group(1)); spy = pit('SPY', D)
        e, s = _align_close(se, spy)
        meas = (e.pct_change(N) - s.pct_change(N)) * 100
        return pd.DataFrame({'close': meas}).dropna()
    if re.search(r'stock/sector\s*ETF ratio', cond, re.I):
        c, e = _align_close(st, se)
        return pd.DataFrame({'close': (c / e)}).dropna()
    m = re.search(r'(\d+)d corr\(stock, sector ETF\)', cond)
    if m:
        N = int(m.group(1))
        c, e = _align_close(st, se)
        corr = c.pct_change().rolling(N).corr(e.pct_change())
        return pd.DataFrame({'close': corr}).dropna()
    raise NR('no_evaluator: sector-row parent measure not implemented: '+cond[:80])
def sector_row_measure(defn, ticker, D):
    m = re.search(r'sector-row [\w-]+ \((.*)\) ranks in the', defn)
    if not m: raise NR('code_bug: sector-row parent parse failed')
    return sector_measure_from_cond(m.group(1), ticker, D)
def sector_eval(defn, ticker, D):
    """YES/NO for stock+SPDR relative-strength / divergence / ATR rows."""
    etf = spdr_for(ticker, D)
    # Membership / breadth / rotation attributes we cannot answer with SPDR alone
    if re.search(r'constituent|% members|% of stock.s sector|sector top-\d|Russell|IWF/IWD', defn, re.I):
        raise NR('data_source_gap: needs PIT sector-constituent or index-membership history')
    if re.search(r'stock mcap|mcap <', defn, re.I):
        u = _tr_universe(pd.Timestamp(D).strftime('%Y-%m-%d'))
        if u is None or ticker not in u.index: raise NR('ticker_not_in_universe')
        raw = str(u.loc[ticker].get('Market Cap', '')).strip().replace(',','')
        if not raw: raise NR('field_empty: Market Cap')
        mcap_m = float(raw)  # Finviz Market Cap is in millions USD
        m = re.search(r'IWM/SPY (\d+)d change > \+?([\d.]+)% AND stock mcap < \$(\d+)B', defn)
        if not m: raise NR('no_evaluator: mcap rotation template')
        N, thr, bil = int(m.group(1)), float(m.group(2)), float(m.group(3))
        spy, iwm = pit('SPY', D), pit('IWM', D)
        s, i = _align_close(spy, iwm)
        ratio = i / s
        if len(ratio) < N+1: raise NR('no_history_yet')
        ch = (ratio.iloc[-1]/ratio.iloc[-1-N] - 1) * 100
        return bool(ch > thr and mcap_m < bil * 1000)
    if re.search(r'stock in tech', defn, re.I):
        u = _tr_universe(pd.Timestamp(D).strftime('%Y-%m-%d'))
        if u is None or ticker not in u.index: raise NR('ticker_not_in_universe')
        in_tech = str(u.loc[ticker, 'Sector']).strip() == 'Technology'
        m = re.search(r'SMH/SPY (\d+)d change > \+?([\d.]+)%', defn)
        if not m: raise NR('no_evaluator: tech rotation template')
        N, thr = int(m.group(1)), float(m.group(2))
        spy, smh = pit('SPY', D), pit('SMH', D)
        s, h = _align_close(spy, smh)
        ratio = h / s
        if len(ratio) < N+1: raise NR('no_history_yet')
        ch = (ratio.iloc[-1]/ratio.iloc[-1-N] - 1) * 100
        return bool(ch > thr and in_tech)
    st, se = pit(ticker, D), pit(etf, D)
    # stock N-session return minus SPDR N-session return >= +X pp
    m = re.search(r'stock (\d+)-session return minus its SPDR sector ETF (\d+)-session return >= \+?([\d.]+) percentage points', defn)
    if m:
        N, thr = int(m.group(1)), float(m.group(3))
        c, e = _align_close(st, se)
        if len(c) < N+1: raise NR(f'no_history_yet: need {N}+1 sessions')
        v = (c.iloc[-1]/c.iloc[-1-N] - e.iloc[-1]/e.iloc[-1-N]) * 100
        return bool(v >= thr)
    m = re.search(r"stock's SPDR sector ETF (\d+)-session return minus SPY (\d+)-session return >= \+?([\d.]+) percentage points", defn)
    if m:
        N, thr = int(m.group(1)), float(m.group(3)); spy = pit('SPY', D)
        e, s = _align_close(se, spy)
        if len(e) < N+1: raise NR(f'no_history_yet: need {N}+1 sessions')
        v = (e.iloc[-1]/e.iloc[-1-N] - s.iloc[-1]/s.iloc[-1-N]) * 100
        return bool(v >= thr)
    # prior day stock return < -2% while sector ETF > +0.5%
    m = re.search(r'prior day stock return < ([+-]?[\d.]+)% while sector ETF > ([+-]?[\d.]+)%', defn)
    if m:
        c, e = _align_close(st, se)
        if len(c) < 2: raise NR('no_history_yet')
        sr, er = (c.iloc[-1]/c.iloc[-2]-1)*100, (e.iloc[-1]/e.iloc[-2]-1)*100
        return bool(sr < float(m.group(1)) and er > float(m.group(2)))
    m = re.search(r'prior day stock > \+?([\d.]+)% while sector ETF < ([+-]?[\d.]+)%', defn)
    if m:
        c, e = _align_close(st, se)
        if len(c) < 2: raise NR('no_history_yet')
        sr, er = (c.iloc[-1]/c.iloc[-2]-1)*100, (e.iloc[-1]/e.iloc[-2]-1)*100
        return bool(sr > float(m.group(1)) and er < float(m.group(2)))
    # stock Nd > +X% AND sector ETF Nd < -Y%
    m = re.search(r'stock (\d+)d > \+?([\d.]+)% AND sector ETF (\d+)d < ([+-]?[\d.]+)%', defn)
    if m:
        N, hi, lo = int(m.group(1)), float(m.group(2)), float(m.group(4))
        c, e = _align_close(st, se)
        if len(c) < N+1: raise NR('no_history_yet')
        sr = (c.iloc[-1]/c.iloc[-1-N]-1)*100; er = (e.iloc[-1]/e.iloc[-1-N]-1)*100
        return bool(sr > hi and er < lo)
    m = re.search(r'stock (\d+)d < ([+-]?[\d.]+)% AND sector ETF (\d+)d > \+?([\d.]+)%', defn)
    if m:
        N, lo, hi = int(m.group(1)), float(m.group(2)), float(m.group(4))
        c, e = _align_close(st, se)
        if len(c) < N+1: raise NR('no_history_yet')
        sr = (c.iloc[-1]/c.iloc[-1-N]-1)*100; er = (e.iloc[-1]/e.iloc[-1-N]-1)*100
        return bool(sr < lo and er > hi)
    # stock/sector 1d <= -2% AND stock/sector 20d >= +5%
    m = re.search(r'stock/sector (\d+)d (<=|>=) ([+-]?[\d.]+)% AND stock/sector (\d+)d (<=|>=) ([+-]?[\d.]+)%', defn)
    if m:
        c, e = _align_close(st, se); ratio = c/e
        def leg(n, op, thr):
            if len(ratio) < n+1: raise NR('no_history_yet')
            v = (ratio.iloc[-1]/ratio.iloc[-1-n]-1)*100
            return v <= thr if op == '<=' else v >= thr
        return bool(leg(int(m.group(1)), m.group(2), float(m.group(3))) and leg(int(m.group(4)), m.group(5), float(m.group(6))))
    # sector ETF ATR(14)/ATR(14) 20d ago > 1.5
    if re.search(r'sector ETF ATR\(14\)/ATR\(14\) 20d ago > ([\d.]+)', defn):
        thr = float(re.search(r'> ([\d.]+)', defn).group(1))
        df = bars(etf, D, 50)
        prev = df.close.shift(1)
        tr = pd.concat([(df.high-df.low), (df.high-prev).abs(), (df.low-prev).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        if len(atr.dropna()) < 21: raise NR('no_history_yet')
        return bool(atr.iloc[-1] / atr.iloc[-21] > thr)
    raise NR('no_evaluator: stock+SPDR definition template not implemented: '+defn[:80])
def _ust(kind):
    k='ust_'+kind
    if k in _mem: return _mem[k]
    f=os.path.join(CACHE,k+'.csv')
    if os.path.exists(f): d=pd.read_csv(f,index_col=0,parse_dates=True)
    else:
        parts=[]
        for y in range(1990 if kind=='nominal' else 2003, pd.Timestamp.now().year+1):
            u=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all?type=daily_treasury_{"yield" if kind=="nominal" else "real_yield"}_curve&field_tdr_date_value={y}&page&_format=csv'
            parts.append(pd.read_csv(io.StringIO(_get(u).text)))
        d=pd.concat(parts); d['Date']=pd.to_datetime(d.Date,format='%m/%d/%Y'); d=d.set_index('Date').sort_index()
        d=d[~d.index.duplicated()]; d.to_csv(f)
    _mem[k]=d; return d
def _fred_via_treasury(code):
    # FRED is unreachable from the box; same H.15-equivalent numbers from Treasury's official par/real curves
    n=_ust('nominal')
    m={'DGS10':n['10 Yr'],'DGS2':n['2 Yr'],'DGS30':n['30 Yr'],'T10Y2Y':n['10 Yr']-n['2 Yr'],'T10Y3M':n['10 Yr']-n['3 Mo']}
    if code in ('DFII10','T10YIE'):
        r=_ust('real')['10 YR' if '10 YR' in _ust('real') else '10 Yr']
        m['DFII10']=r; m['T10YIE']=(n['10 Yr']-r)
    if code not in m: raise NR('data_source_gap: FRED '+code+' unreachable and no Treasury substitute')
    s=pd.to_numeric(m[code],errors='coerce').dropna()
    df=pd.DataFrame({'close':s}); df.index.name='date'
    for c in ('open','high','low'): df[c]=df.close
    df['volume']=np.nan; return df
# ---------- symbol resolution ----------
NAMEMAP={'WTI crude':'CL=F','Gold':'GC=F','Copper':'HG=F','Natural gas':'NG=F','Silver':'SI=F','DXY':'DX-Y.NYB',
 '10y yield':'FRED:DGS10','2y yield':'FRED:DGS2','10y treasury yield':'FRED:DGS10','2y treasury yield':'FRED:DGS2','30y treasury yield':'FRED:DGS30',
 'VIX':'^VIX','BTC':'CB:BTC-USD','Bitcoin':'CB:BTC-USD','ETH':'CB:ETH-USD','HYG':'HYG','SPY':'SPY','QQQ':'QQQ','IWM':'IWM'}
def resolve(src,ticker,D=None):
    s=src
    if re.search(r'Stockcharts|\$NY|\$SPXA|\$NAHL|\$TRIN',s): raise NR('data_source_gap: Stockcharts breadth is not a free official feed; constituent rebuild not built')
    if re.search(r'FedWatch|CFE|Eurex|CBOE daily market statistics|constituents',s): raise NR('data_source_gap: no free official archived history wired ('+s[:40]+')')
    # SPDR / sector sources: resolved with PIT map from theme-radar universe(D)
    if 'constituent' in s.lower() and 'SPDR' in s:
        raise NR('data_source_gap: sector-constituent breadth needs full PIT sector membership history')
    if D is None and ('XLK/XLF' in s or 'SPDR sector ETF' in s or 'stock + SPDR' in s or s.startswith('SPDR')):
        raise NR('code_bug: SPDR resolve called without date')
    if 'SPDR sector ETF / SPY' in s:
        return ('RATIO', spdr_for(ticker, D), 'SPY')
    if 'stock + SPDR' in s:
        return ('STOCK_SPDR', spdr_for(ticker, D))
    if 'XLK/XLF' in s or s.startswith('SPDR') or 'SPDR sector ETF' in s:
        return spdr_for(ticker, D)
    m=re.search(r'(\^?[A-Z0-9=.\-]+)\s*/\s*(\^?[A-Z0-9=.\-]+)',s.replace('Yahoo ','')) if '/' in s and 'FRED' not in s and 'CME' not in s and 'ICE' not in s and 'DXY' not in s and 'futures' not in s else None
    if m and m.group(1) not in ('BTC-USD',) and 'Coinbase' not in s: return ('RATIO',m.group(1),m.group(2))
    m=re.search(r'FRED (\w+)',s)
    if m: return 'FRED:'+m.group(1)
    m=re.search(r'Coinbase (\w+-\w+)',s)
    if m: return 'CB:'+m.group(1)
    if 'DCOILWTICO' in s or 'CL futures' in s or 'CME CL' in s: return 'CL=F'
    if 'GC futures' in s or 'CME GC' in s: return 'GC=F'
    if 'HG futures' in s or 'CME HG' in s: return 'HG=F'
    if 'DXY' in s or 'DX-Y' in s: return 'DX-Y.NYB'
    m=re.search(r'(\^[A-Z0-9]+)',s)
    if m and ',' not in s and '+' not in s: return m.group(1)
    m=re.search(r'Yahoo ([A-Z0-9=.\-^]+)(?: daily OHLC)?(?: \(prior close\))?$',s)
    if m and m.group(1)!='daily': return m.group(1)
    m=re.search(r'Yahoo (\w+=F)',s)
    if m: return m.group(1)
    raise NR('data_source_gap: multi-source/composite row, no evaluator for source "'+s[:50]+'"')
def bars(sym,D,need):
    if isinstance(sym,tuple):
        a=pit(sym[1],D); b=pit(sym[2],D); c=(a.close/b.close).dropna(); df=pd.DataFrame({'close':c}); 
        for k in ('open','high','low'): df[k]=df.close
        df['volume']=np.nan
    else: df=pit(sym,D)
    tot=len(series(sym)) if isinstance(sym,str) else need
    if tot<need: raise NR(f'data_source_gap: {sym} feed returns only {tot} bars in total')
    if len(df)<need: raise NR(f'no_history_yet: {len(df)} sessions before D, need {need}')
    lag=(pd.Timestamp(D)-df.index[-1]).days
    if lag>7: raise NR(f'no_history_yet: last bar {df.index[-1].date()} is {lag}d before D (delisted/not listed)')
    return df
# ---------- evaluators ----------
num=lambda x: float(x)
def outlier(defn,df):
    c=df.close.values;o=df.open.values;h=df.high.values;l=df.low.values;n=len(c)
    A=int(re.search(r'A(\d+) = mean',defn).group(1))
    mv=np.r_[np.nan,np.diff(c)]; am=np.abs(mv)
    avg=pd.Series(am).shift(1).rolling(A).mean().values
    mm=re.search(r'>= ([\d.]+) x A\d+',defn); pm=re.search(r'ranks in top ([\d.]+)% of the prior (\d+) sessions',defn)
    if pm:
        P,W=num(pm.group(1)),int(pm.group(2))
        thr=pd.Series(am).shift(1).rolling(W).quantile(1-P/100).values; big=am>=thr
    else: big=am>=num(mm.group(1))*avg
    big=np.where(np.isnan(avg),False,big)
    red=big&(mv<0); grn=big&(mv>0)
    y=n-1  # yesterday index
    if 'printed two' in defn or 'followed later' in defn:
        L=int(re.search(r'within the last (\d+) sessions',defn).group(1)); w=range(y-L+1,y+1)
        if 'printed two' in defn:
            s=red if 'two red' in defn else grn; k=[i for i in w if s[i]]; return len(k)>=2 and k[-1]-k[0]>=1
        a,b=(red,grn) if re.search(r'a red candle .* followed later by a green',defn) else (grn,red)
        ia=[i for i in w if a[i]]; return bool(ia) and any(b[i] for i in range(ia[0]+1,y+1))
    if 'opened with a gap' in defn:
        L=int(re.search(r'within the last (\d+) sessions',defn).group(1)); col='red' if 'recent red' in defn else 'green'
        s=red if col=='red' else grn; k=[i for i in range(y-L+1,y+1) if s[i]]
        if not k: return False
        i=k[-1]
        gap=o[i]<l[i-1] if col=='red' else o[i]>h[i-1]
        if not gap: return False
        lvl=l[i-1] if col=='red' else h[i-1]
        later=range(i+1,y+1)
        touched=any((h[t]>=lvl) if col=='red' else (l[t]<=lvl) for t in later)
        return touched if 'gap filled' in defn else not touched
    m=re.search(r'occurred (?:exactly (\d+) session|(\d+) to (\d+) sessions)',defn)
    lo,hi=(int(m.group(1)),int(m.group(1))) if m.group(1) else (int(m.group(2)),int(m.group(3)))
    s=red if 'a red candle' in defn else grn
    # 'exactly 1 session ago (yesterday)' => index y ; 'k sessions before yesterday' => y-k
    cand=[y-k+ (1 if m.group(1) else 0) for k in range(lo,hi+1)] if m.group(1) else [y-k for k in range(lo,hi+1)]
    k=[i for i in cand if 0<i<=y and s[i]]
    if not k: return False
    i=max(k); yc=c[y]; mid=(h[i]+l[i])/2
    if "close < the outlier candle's low" in defn: return yc<l[i]
    if "close > the outlier candle's high" in defn: return yc>h[i]
    if 'outlier low <= ' in defn: return l[i]<=yc<mid
    if 'outlier midpoint <= ' in defn: return mid<=yc<=h[i]
    raise NR('code_bug: unparsed outlier location')
def streak_len(c):
    d=np.sign(np.diff(c)); 
    if len(d)==0 or d[-1]==0: return 0,0
    s=d[-1]; k=0
    for x in d[::-1]:
        if x==s: k+=1
        else: break
    return int(s),k
def generic(defn,df,D):
    c=df.close; cv=c.values
    if re.search(r'09:00 ET|16:00->09:00|overnight|Fri16:00',defn): raise NR('data_source_gap: needs intraday 09:00 ET snapshot; no archived official intraday history')
    if re.search(r'stock has|stock is semiconductor|for XLE members|corr to',defn): raise NR('data_source_gap: needs stock attribute (revenue mix/industry/corr) with no PIT official feed')
    m=re.search(r'5-session change has the opposite sign to SPY 5-session change and \|.*\| >= ([\d.]+) x its (\d+)-session stdev of 5d changes \(sign of .* change (>|<) 0\)',defn)
    if m:
        sp=pit('SPY',D).close; k,W=num(m.group(1)),int(m.group(2)); ch=(c.diff(5) if _isrates(defn) else c.pct_change(5)).dropna()
        if len(ch)<W+1: raise NR('no_history_yet')
        v=ch.iloc[-1]; s5=sp.iloc[-1]/sp.iloc[-6]-1; sd=ch.iloc[-W-1:-1].std()
        return bool(np.sign(v)==-np.sign(s5) and abs(v)>=k*sd and (v>0 if m.group(3)=='>' else v<0))
    m=re.search(r'prior-day % change (>=|<=) ([+-]?[\d.]+) std of (?:its )?(\d+)d daily returns',defn)
    if m:
        r=c.pct_change(); W=int(m.group(3)); sd=r.iloc[-W-1:-1].std(); v=r.iloc[-1]; return eval(f'v{m.group(1)}{num(m.group(2))}*sd')
    m=re.search(r'session (?:return )?(>=|<=) ([+-]?[\d.]+)%$',defn.strip())
    if m:
        r=(cv[-1]/cv[-2]-1)*100; return eval(f'r{m.group(1)}{num(m.group(2))}')
    if 'indication' in defn or 'pre-09:25' in defn and 'extends' in defn: raise NR('data_source_gap: pre-09:25 ET indication history not archived')
    m=re.search(r'closed (up|down) exactly (\d+) consecutive',defn) or re.search(r'\b(up|down) exactly (\d+) consecutive',defn)
    if m:
        s,k=streak_len(cv); return s==(1 if m.group(1)=='up' else -1) and k==int(m.group(2))
    m=re.search(r'(?:closed |)(up|down) (\d+)\+ consecutive sessions',defn)
    if m and 'AND' not in defn:
        s_,k=streak_len(cv); return s_==(1 if m.group(1)=='up' else -1) and k>=int(m.group(2))
    m=re.search(r'closed (above|below) (?:its|the) (upper|lower) (?:Bollinger Band \((\d+), ([\d.]+)\)|BB\((\d+),([\d.]+)\)) for >= (\d+) consecutive sessions',defn)
    if m:
        W=int(m.group(3) or m.group(5)); K=num(m.group(4) or m.group(6)); n=int(m.group(7))
        mu=c.rolling(W).mean(); sd=c.rolling(W).std(ddof=0); up=mu+K*sd; lo=mu-K*sd
        if np.isnan(mu.iloc[-n-1]): raise NR('no_history_yet')
        ok=all((cv[-i]>up.iloc[-i]) if m.group(1)=='above' else (cv[-i]<lo.iloc[-i]) for i in range(1,n+1))
        if 'BB width expanded' in defn:
            p=num(re.search(r'expanded >= ([\d.]+)%',defn).group(1)); bw=(up-lo)/mu
            ok=ok and bw.iloc[-1]>=bw.iloc[-n-1]*(1+p/100)
        return ok
    m=re.search(r'%B(?:\((\d+),([\d.]+)\))? (>=|<=) ([\d.]+) for >= (\d+)',defn)
    if m:
        W=20;K=2.0;n=int(m.group(5)); mu=c.rolling(W).mean(); sd=c.rolling(W).std(ddof=0); pb=(c-(mu-K*sd))/(2*K*sd); t=num(m.group(4))
        if np.isnan(pb.iloc[-n]): raise NR('no_history_yet')
        ok=all((pb.iloc[-i]>=t) if m.group(3)=='>=' else (pb.iloc[-i]<=t) for i in range(1,n+1))
        if 'SMA slope' in defn:
            sl=mu.iloc[-1]-mu.iloc[-6]; ok=ok and (sl>0 if m.group(3)=='>=' else sl<0)
        return ok
    m=re.search(r'gone >= (\d+) sessions without (?:printing )?a new (\d+)-session closing (low|high)',defn)
    if m:
        n,W=int(m.group(1)),int(m.group(2)); f=(c<=c.rolling(W).min()) if m.group(3)=='low' else (c>=c.rolling(W).max())
        ok=not f.iloc[-n:].any()
        mm=re.search(r'made a new (\d+)-session closing (high|low) in the last (\d+) sessions',defn)
        if mm:
            W2,L=int(mm.group(1)),int(mm.group(3)); g=(c>=c.rolling(W2).max()) if mm.group(2)=='high' else (c<=c.rolling(W2).min()); ok=ok and g.iloc[-L:].any()
        return bool(ok)
    m=re.search(r'>= (\d+) sessions since a ([\d.]+)% pullback AND .* closed at a (\d+)-session high yesterday',defn)
    if m:
        rh=c.cummax().shift(1); dd=np.where(((c/rh-1)<=-num(m.group(2))/100).values)[0]
        if not len(dd): raise NR('no_history_yet')
        return (len(c)-1-dd[-1])>=int(m.group(1)) and cv[-1]>=c.iloc[-int(m.group(3)):].max()
    m=re.search(r'prior (?:day|session) (?:return )?(<=|>=) ([+-]?[\d.]+)%',defn)
    if m and ' AND ' not in defn:
        r=(cv[-1]/cv[-2]-1)*100; return eval(f'r{m.group(1)}{num(m.group(2))}')
    m=re.search(r'RSI\((\d+)\) (<|>) ([\d.]+)$',defn.strip())
    if m:
        N=int(m.group(1)); d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/N,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/N,adjust=False).mean()
        rsi=100-100/(1+up/dn); v=rsi.iloc[-1]; return eval(f'v{m.group(2)}{num(m.group(3))}')
    m=re.search(r'(\d+)d realized vol (>|<) ([\d.]+)%',defn)
    if m:
        v=np.log(c).diff().iloc[-int(m.group(1)):].std()*math.sqrt(252)*100; return eval(f'v{m.group(2)}{num(m.group(3))}')
    m=re.search(r'(\d+)d change (>|<) ([+-]?[\d.]+)%$',defn.strip())
    if m:
        v=(cv[-1]/cv[-1-int(m.group(1))]-1)*100; return eval(f'v{m.group(2)}{num(m.group(3))}')
    m=re.search(r"current (up|down) streak length is >= (\d+)th percentile AND the streak's cumulative move is <= its median streak move",defn)
    if m:
        want=1 if m.group(1)=='up' else -1; x=c[c.index>=pd.Timestamp(D)-pd.DateOffset(years=10)].values
        d=np.sign(np.diff(x)); L=[];M=[];k=0;st=0
        for i,v in enumerate(d):
            if v==want:
                if k==0: st=i
                k+=1
            else:
                if k: L.append(k);M.append(abs(x[st+k]/x[st]-1))
                k=0
        s_,cur=streak_len(cv)
        if s_!=want or not L: return False
        mv=abs(cv[-1]/cv[-1-cur]-1); return cur>=np.percentile(L,int(m.group(2))) and mv<=np.median(M)
    m=re.search(r'(?:has risen|rose on >=) (\d+)\+? consecutive',defn) or re.search(r'has fallen (\d+)\+? consecutive|fell on >= (\d+) consecutive',defn)
    if m:
        k=int([g for g in m.groups() if g][0]); s,L=streak_len(cv); return s==(1 if ('risen' in defn or 'rose' in defn) else -1) and L>=k
    m=re.search(r'current (up|down) close streak length of .* >= the (\d+)th percentile of all \w+ streak lengths over the prior (\d+) years',defn)
    if m:
        want=1 if m.group(1)=='up' else -1; s,L=streak_len(cv)
        start=pd.Timestamp(D)-pd.DateOffset(years=int(m.group(3))); x=c[c.index>=start].values
        if len(c[c.index<start])==0 and len(x)<252*int(m.group(3))*0.9: raise NR('no_history_yet: <10y history for streak distribution')
        d=np.sign(np.diff(x)); ls=[];k=0;p=0
        for v in d:
            if v==want: k+=1
            else:
                if k: ls.append(k)
                k=0
        if not ls: return False
        return s==want and L>=np.percentile(ls,int(m.group(2)))
    m=re.search(r'>= (\d+) sessions since .* last closed >= ([\d.]+)% below its prior running closing high',defn)
    if m:
        rh=c.cummax().shift(1); dd=(c/rh-1)<=-num(m.group(2))/100; idx=np.where(dd.values)[0]
        if not len(idx): raise NR('no_history_yet: never had such a drawdown')
        return (len(c)-1-idx[-1])>=int(m.group(1))
    m=re.search(r'(\d+)-session change in .*? (>=|<=) ([+-]?[\d.]+) x stdev of (?:its )?rolling \d+-session changes over prior (\d+) sessions',defn)
    if m:
        N,W=int(m.group(1)),int(m.group(4)); ch=c.diff(N) if _isrates(defn) else c.pct_change(N)
        if len(ch.dropna())<W+1: raise NR(f'no_history_yet: need {W}+{N} sessions')
        sd=ch.iloc[-W-1:-1].std(); v=ch.iloc[-1]; k=num(m.group(3))
        return v>=k*sd if m.group(2)=='>=' else v<=k*sd
    m=re.search(r'latest .* (?:level is above|value >) its (\d+)-session median',defn)
    if m:
        W=int(m.group(1)); 
        if len(c)<W+1: raise NR('no_history_yet')
        return cv[-1]>np.median(cv[-W-1:-1])
    m=re.search(r'level is in (top|bottom) (\d+)% of its (\d+)-session range',defn) or re.search(r'value has percentile rank (>=|<=) (\d+) within prior (\d+) sessions',defn)
    if m:
        W=int(m.group(3))
        if len(c)<W+1: raise NR('no_history_yet')
        pr=(cv[-W-1:-1]<cv[-1]).mean()*100; P=int(m.group(2))
        top=m.group(1) in ('top','>=') 
        if m.group(1)=='top': return pr>=100-P
        if m.group(1)=='bottom': return pr<=P
        return pr>=P if top else pr<=P
    m=re.search(r'(\d+)-session change in .* is in (top|bottom) (\d+)% of its (\d+)-session distribution',defn)
    if m:
        N,P,W=int(m.group(1)),int(m.group(3)),int(m.group(4)); ch=(c.diff(N) if _isrates(defn) else c.pct_change(N)).dropna()
        if len(ch)<W+1: raise NR('no_history_yet')
        q=np.percentile(ch.iloc[-W-1:-1],100-P if m.group(2)=='top' else P); v=ch.iloc[-1]
        return v>=q if m.group(2)=='top' else v<=q
    if re.search(r'latest 1-session change in .* is (UP|DOWN)',defn):
        d=np.diff(cv)[-2:]; up='is UP' in defn
        return (d[1]>0 and d[0]<0 if up else d[1]<0 and d[0]>0) and abs(d[1])>abs(d[0])
    m=re.search(r'(\d+)-session change in .* (>|<) the preceding non-overlapping',defn)
    if m:
        N=int(m.group(1)); a=cv[-1]-cv[-1-N]; b=cv[-1-N]-cv[-1-2*N]; return a>b if m.group(2)=='>' else a<b
    m=re.search(r'crossed (above|below) its (\d+)-session SMA at yesterday',defn)
    if m:
        W=int(m.group(2)); sma=c.rolling(W).mean().values
        if np.isnan(sma[-2]): raise NR('no_history_yet')
        return (cv[-1]>sma[-1] and cv[-2]<=sma[-2]) if m.group(1)=='above' else (cv[-1]<sma[-1] and cv[-2]>=sma[-2])
    m=re.search(r'prior(?:-day)? close (>|<|>=|<=) ([\d.]+)\b',defn)
    if m:
        v=cv[-1];t=num(m.group(2));return eval(f'v{m.group(1)}t')
    m=re.search(r'prior-day change (<=|>=) ([+-]?[\d.]+)bp',defn)
    if m:
        v=(cv[-1]-cv[-2])*100;t=num(m.group(2));return eval(f'v{m.group(1)}t')
    raise NR('no_evaluator: definition template not implemented in engine yet')
def _isrates(defn): return bool(re.search(r'yield|spread|T10Y|DGS|breakeven|real yield|VIX',defn))
BUTRE=re.compile(r"BUT stock's own prior-session return (?:moved >= ([\d.]+)% against the YES direction|(<=|>=) ([+-]?[\d.]+)%) (?:on|with) volume >= ([\d.]+)x its (\d+)-session average")
def stock_but(defn,ticker,D,bull):
    m=BUTRE.search(defn)
    if not m: return None
    df=bars(ticker,D,int(m.group(5))+2); r=df.close.pct_change().iloc[-1]*100
    va=df.volume.iloc[-int(m.group(5))-1:-1].mean(); vok=df.volume.iloc[-1]>=num(m.group(4))*va
    if m.group(1): ok=(r<=-num(m.group(1))) if bull else (r>=num(m.group(1)))
    else: ok=eval(f'r{m.group(2)}{num(m.group(3))}')
    return bool(ok and vok), df.index[-1]

def slow_meta(defn, df):
    """Slow-series outlier of an inlined measure: YES if a day-to-day change of df.close,
    signed toward the parent condition, ranked in the top/bottom P% of its trailing ~10y
    distribution, within the last N sessions ending at D-1. No look-ahead."""
    mN=re.search(r'within the last (\d+) sessions', defn)
    mP=re.search(r'ranks in the (top|bottom) ([\d.]+)%', defn)
    if not mN or not mP: raise NR('code_bug: slow-outlier parse failed')
    N=int(mN.group(1)); side=mP.group(1); P=float(mP.group(2))
    paren=re.search(r'\(([^()]*(?:>=|<=|>|<)[^()]*)\)', defn)
    cond=paren.group(1) if paren else ''
    if re.search(r'<=|-\d|down|fall|drop|below|against', cond, re.I) and not re.search(r'>=|\+\d', cond):
        sign=-1
    else:
        sign=+1
    signed=(df.close.astype(float).diff()*sign)
    W=min(2520, max(252, len(signed)-1))
    # prior-only trailing window: shift(1) so today's value is not in its own history
    hist=signed.shift(1)
    if side=='top':
        thr=hist.rolling(W, min_periods=200).quantile(1-P/100)
        hit=(signed>=thr)
    else:
        thr=hist.rolling(W, min_periods=200).quantile(P/100)
        hit=(signed<=thr)
    return bool(hit.iloc[-N:].fillna(False).any())


CAL=('Calendar','Calendar label','Macro','Fed')
def _rows():
    j=pd.read_csv(ROWS); rm=os.path.join(ROOT,'v8src','James-removed-v5.5f.csv')
    if os.path.exists(rm): j=j[~j.id.isin(pd.read_csv(rm).id)]
    return j
def answer(ticker,date):
    D=pd.Timestamp(date).normalize(); out=[]
    for _,r in _rows().iterrows():
        defn=str(r.strict_definition); res=dict(row_id=r.id,ticker=ticker,date=D.strftime('%Y-%m-%d'))
        try:
            wd=re.match(r'YES if today is (Monday|Tuesday|Wednesday|Thursday|Friday) \(',defn)
            if wd:
                v=D.day_name()==wd.group(1); asof=D
                if ' BUT ' in defn:
                    b=stock_but(defn,ticker,D,str(r['yes_means (bullish/bearish)']).startswith('Bull')); v=bool(v and b[0]); asof=b[1]
                res.update(answer='YES' if v else 'NO',reason='computed weekday of D',data_as_of=asof.strftime('%Y-%m-%d')); out.append(res); continue
            if r.data_type in CAL or 'calendar' in str(r.source).lower() or 'FOMC' in str(r.source):
                raise NR('held/to_cut_review: calendar/macro event row; needs official archived event history wired (Manager Bot calendar audit)')
            if any(h in str(r.source) for h in HELD_SOURCES): raise NR('held: new source, needs 2 clean nightly GitHub pulls')
            if 'release/value change of the measure' in defn:
                # parent measure is inlined in the definition; evaluate on this row's source series
                if 'sector-row' in defn:
                    df=sector_row_measure(defn,ticker,D); label='sector-row/'+spdr_for(ticker,D)
                else:
                    sym=resolve(str(r.source),ticker,D)
                    if isinstance(sym,tuple) and sym and sym[0]=='STOCK_SPDR':
                        raise NR('no_evaluator: slow-meta parent measure not sector-row / not wired for stock+SPDR source')
                    if isinstance(sym,tuple):
                        df=bars(sym,D,300); label='/'.join(sym[1:])
                    else:
                        df=pit(sym,D); label=sym
                        if len(df)<300: raise NR(f'no_history_yet: {len(df)} sessions before D, need 300')
                v=slow_meta(defn,df)
                asof=df.index[-1]
                if ' BUT ' in defn and "stock's own" in defn:
                    b=stock_but(defn,ticker,D,str(r['yes_means (bullish/bearish)']).startswith('Bull'))
                    if b is None: raise NR('code_bug: BUT clause not parsed')
                    v=bool(v and b[0]); asof=min(asof,b[1])
                elif ' BUT ' in defn: raise NR('no_evaluator: non-stock BUT clause')
                res.update(answer='YES' if v else 'NO',reason='computed slow-meta '+label,data_as_of=asof.strftime('%Y-%m-%d')); out.append(res); continue
            sym=resolve(str(r.source),ticker,D)
            if str(r.source)=='Yahoo ^N225 / ^TWII': sym='^TWII' if 'TAIEX' in defn else '^N225'
            if isinstance(sym,tuple) and sym and sym[0]=='STOCK_SPDR':
                v=sector_eval(defn,ticker,D)
                asof=pit(ticker,D).index[-1]
                if ' BUT ' in defn and "stock's own" in defn:
                    b=stock_but(defn,ticker,D,str(r['yes_means (bullish/bearish)']).startswith('Bull'))
                    if b is None: raise NR('code_bug: BUT clause not parsed')
                    v=bool(v and b[0]); asof=min(asof,b[1])
                elif ' BUT ' in defn: raise NR('no_evaluator: non-stock BUT clause')
                res.update(answer='YES' if v else 'NO',reason='computed stock/'+sym[1],data_as_of=asof.strftime('%Y-%m-%d')); out.append(res); continue
            need=300 if '252' in defn else 60
            df=bars(sym,D,need)
            v=outlier(defn,df) if r.data_type=='Outlier' else generic(defn,df,D)
            asof=df.index[-1]
            if ' BUT ' in defn and "stock's own" in defn:
                b=stock_but(defn,ticker,D,str(r['yes_means (bullish/bearish)']).startswith('Bull'))
                if b is None: raise NR('code_bug: BUT clause not parsed')
                v=bool(v and b[0]); asof=min(asof,b[1])
            elif ' BUT ' in defn: raise NR('no_evaluator: non-stock BUT clause')
            res.update(answer='YES' if v else 'NO',reason='computed '+(sym if isinstance(sym,str) else '/'.join(sym[1:])),data_as_of=asof.strftime('%Y-%m-%d'))
        except NR as e: res.update(answer='NOT_READY',reason=str(e),data_as_of='')
        except RuntimeError as e: res.update(answer='NOT_READY',reason='data_source_gap: '+str(e)[:120],data_as_of='')
        except Exception as e: res.update(answer='NOT_READY',reason=f'code_bug: {type(e).__name__}: {str(e)[:80]}',data_as_of='')
        out.append(res)
    return out
COLS=['row_id','ticker','date','answer','reason','data_as_of']
if __name__=='__main__':
    import argparse,sys
    a=argparse.ArgumentParser(); a.add_argument('--ticker',required=True); a.add_argument('--date',required=True); a.add_argument('--out')
    x=a.parse_args(); rows=answer(x.ticker,x.date)
    f=open(x.out,'w',newline='') if x.out else sys.stdout
    w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); w.writerows(rows)

# ---------- James new sources (SOFR, ON RRP, auctions, TGA, UST curve): first-print reader ----------
# Nightly saves: theme-radar data/newroots/james/daily/<YYYY-MM-DD>.json, each holding the last 7 days under `latest`.
# A date's value = the value in the EARLIEST saved file that contains it (first print, never revised).
# Dates before the first nightly save fall back to the history backfill but stay NOT_READY until 2 clean nightly runs exist.
NEWROOTS_DIR=os.environ.get('JAMES_NEWROOTS_DIR','/workspace/theme-radar-repo/data/newroots/james/daily')
BACKFILL=os.path.join(ROOT,'qa','james_newroots','history')
def newroots_value(source,key,date):
    """returns (value, data_as_of) or raises NR. source in sofr|onrrp|auctions|tga|ust_curve."""
    files=sorted(f for f in os.listdir(NEWROOTS_DIR) if f.endswith('.json')) if os.path.isdir(NEWROOTS_DIR) else []
    clean=[f for f in files if json.load(open(os.path.join(NEWROOTS_DIR,f))).get('status','ok') in ('ok','READY')]
    D=pd.Timestamp(date).strftime('%Y-%m-%d')
    for f in files:
        if f[:10]>D: break   # file saved after D cannot be known at 09:25 ET on D
        j=json.load(open(os.path.join(NEWROOTS_DIR,f))); lat=j.get('latest',{}).get(source)
        recs=lat if isinstance(lat,list) else ([lat] if lat else [])
        for rec in recs:
            if str(rec.get('date',''))[:10]==key and len(clean)>=2: return rec.get(rec.get('field',''),rec), f[:10]
    if len(clean)<2: raise NR(f'building: needs 2 clean nightly runs ({len(clean)} so far); backfill in {BACKFILL} not counted')
    raise NR('no_history_yet: date not in any nightly save before D')
