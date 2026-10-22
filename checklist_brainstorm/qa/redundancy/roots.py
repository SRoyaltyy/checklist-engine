import pandas as pd,re
d=pd.read_csv('../../merged_draft_v7.csv',low_memory=False)
S=lambda r:(str(r.source)+' || '+str(r.variant)+' || '+str(r.data_type)+' || '+str(r.strict_definition)).lower()
FV_PRICE=r'sma|perf|52w|52-week|all-time|50-day|change %|change from open|gap %|volatility [wm]|rel volume|avg volume|price x volume|trades|^volume|rsi|atr|beta|after-hours|prior close|intraday'
FV_FUND=r'p/e|pe\b|p/s|peg|ev/|eps|sales|margin|debt|ratio|dividend|payout|roa|roe|return on|book|cash|employees|income|market cap|enterprise|recom|target|analyst|insider|inst |inst own|inst trans|float|short|shares out|expense|holdings|net asset|net flows|return \d|since inception|earnings date|index|optionable|shortable|sector|industry|country'
def root(r):
    s=S(r); src=str(r.source).lower(); v=str(r.variant).lower(); dt=str(r.data_type).lower()
    if 'cftc' in s or 'cot ' in s: return 'CFTC COT'
    if 'regsho' in s or 'finra' in s or 'short sale vol' in s or 'short volume' in s: return 'FINRA/RegSHO short volume'
    if 'fails-to-deliver' in s or ' ftd' in s or 'sec ftd' in s: return 'SEC FTD'
    if 'halt' in s: return 'Nasdaq halts feed'
    if 'upgrades_downgrades' in s or 'analyst rating change' in dt: return 'Analyst rating actions (Yahoo)'
    if 'theme radar' in src or 'finviz' in src:
        if 'after-hours' in s: return 'Finviz after-hours snapshot'
        if re.search(r'sma|perf|52w|50-day|all-time|change %|change from open|gap %|volatility [wm]|rel volume|avg volume|price x volume|trades|: volume|rsi|atr|beta|stock vs|prior close|intraday|ohlc|ipo date',src): return 'Price/volume (Finviz restatement of OHLCV)'
        if 'vix' in v: return 'Options-implied (VIX family, put/call)'
        if 'earnings' in v or 'earnings' in src: return 'Price/volume + earnings dates'
        if re.search(r'groups: sector',src) or re.search(r'52-week|^gap|overbought|tug of war|^volume|^ma$|performance|^position$|volatility|relative strength|outlier anchor|exhaustion|^50d|^52w|^ath|^atl|intraday|prior close|^sector$|^industry$',dt) or re.search(r'rsi|streak|gap|52w|all-time|sma|relative volume|change from open|outlier',v): return 'Price/volume (Finviz restatement of OHLCV)'
        return 'Finviz snapshot: fundamentals/analyst/ownership'
    if 'fedwatch' in s or 'zq=f' in s or 'fed funds fut' in s: return 'Fed funds futures (FedWatch/ZQ)'
    if 'bls' in src or 'ism' in src or 'cpi' in src or 'econ calendar' in src or 'fomc' in src or 'federalreserve' in src: return 'Official macro releases / Fed'
    if 'fred' in src and re.search(r'dgs|t10y|dfii|treasury|yield',src+v): return 'Treasury yields (FRED)'
    if 'fred' in src: return 'Treasury yields (FRED)'
    if re.search(r'vix|vvix|ovx|\^move|\$cpc|put/call|cboe|skew|option',src): return 'Options-implied (VIX family, put/call)'
    if 'stockcharts' in src or 'breadth' in dt or 'constituents' in src or '$ny' in src or '$spx' in src: return 'Breadth (constituent OHLC)'
    if re.search(r'dividend calendar|ipo calendar|expiry dates|holiday|rebalance|calendar',src) and 'ohlc' not in src and 'yahoo daily' not in src: return 'Calendar/event dates'
    if 'earnings' in src and ('ohlc' in src or 'yahoo' in src): return 'Price/volume + earnings dates'
    if re.search(r'=f|cl futures|gc futures|hg futures|cme|dx futures|dcoilwtico|globex|eurex|cfe',src): return 'Futures/commodities/FX/crypto bars'
    if re.search(r'=x|btc|coinbase|dx-y|dxy|\^n225|\^hsi|\^stoxx|\^gdaxi|\^ftse|\^ks11|\^twii',src): return 'Futures/commodities/FX/crypto bars'
    if 'yahoo' in src or 'ohlc' in src or 'spdr' in src or src in('nan',''): return 'Price/volume (stock/ETF OHLCV)'
    return 'Calendar/event dates' if 'session' in src or 'calendar' in src else 'OTHER'
d['root']=d.apply(root,axis=1)
d.to_pickle('tagged.pkl')
print(d.root.value_counts().to_string())
print(pd.crosstab(d.root,d.merge_owner,margins=True).to_string())
print(d[d.root=='OTHER'].source.value_counts().head(30))
