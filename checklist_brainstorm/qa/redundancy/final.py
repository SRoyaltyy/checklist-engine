import pandas as pd,numpy as np,re,pickle
from scipy.optimize import curve_fit
d=pd.read_pickle('tagged.pkl')
J=pd.read_csv('/workspace/james_row_sources.csv').set_index('id')
def jroot(p,rs):
    p=str(p); rs=str(rs).lower()
    if re.search(r'put/call|\$cpc|\^vix|vvix|ovx|\^move|skew',rs): return 'Options-implied (VIX family, put/call)'
    if re.search(r'\bism\b|cpi|bls|nfp|payroll',rs) and 'calendar' not in rs[:20]: return 'Official macro releases / Fed'
    if p.startswith('Treasury'): return 'Treasury yields (home.treasury.gov)'
    if p=='CBOE': return 'Options-implied (VIX family, put/call)'
    if p=='Coinbase': return 'Futures/commodities/FX/crypto bars'
    if p=='Stockcharts': return 'Breadth (constituent OHLC)'
    if p=='CFTC': return 'CFTC COT'
    if p in('BLS','Fed (federalreserve.gov)'): return 'Official macro releases / Fed'
    if p in('Nasdaq','Calendar (NYSE/Fed/BLS)'): return 'Calendar/event dates'
    if 'futures' in p.lower() or re.search(r'=f|=x|dx-y|\^n225|\^hsi|\^stoxx|\^gdaxi|\^ftse|\^ks11|\^twii|fedwatch|zq',rs): 
        return 'Fed funds futures (FedWatch/ZQ)' if ('fedwatch' in rs or 'zq' in rs) else 'Futures/commodities/FX/crypto bars'
    return 'Price/volume (stock/ETF OHLCV)'
isj=d.merge_owner=='james'
d.loc[isj,'root']=[jroot(J.provider.get(i),J.raw_series.get(i)) for i in d.id[isj]]
d['root']=d.root.replace({'Treasury yields (FRED)':'Treasury yields (home.treasury.gov)'})
d['james_provider']=d.id.map(J.provider); d['james_raw_series']=d.id.map(J.raw_series)
# price/volume families
def fam(r):
    if not r.root.startswith('Price/volume'): return ''
    s=(str(r.data_type)+' | '+str(r.variant)).lower()
    rules=[('candle patterns',r'cdl|candle pattern|candlestick|engulf|hammer|doji|body|wick|inside day'),
      ('big-move/outlier candles',r'outlier'),('gaps',r'gap'),('returns vs market/sector',r'relative|vs spy|vs sector|sector rs|rotation|style/size|beta|sector-future|minus sector|minus industry|vs industry|stock perf'),
      ('volume/money flow',r'volume|money flow|obv|mfi|vwap|dollar vol|trades'),('volatility/Bollinger/ATR',r'volatil|bollinger|atr|squeeze|range'),
      ('momentum/RSI/oscillators',r'momentum|rsi|overbought|stoch|macd|cci|oscillat|williams'),('streaks/exhaustion',r'streak|exhaust|stretch|consecutive|days since|tired'),
      ('trend/moving averages',r'trend|moving average|sma|ema|overlap|^ma\b|ma \||cross|cycle'),('position in range/52w/ATH',r'position|52|ath|atl|50d|high|low|fib|pivot'),
      ('earnings-anchored',r'earn'),('breadth',r'breadth'),('statistics',r'statistic'),('performance windows',r'perf|return|change')]
    for n,p in rules:
        if re.search(p,s): return n
    return 'other price-derived'
d['pv_family']=d.apply(fam,axis=1)
# structural duplicates
norm=lambda s:re.sub(r'\[BUT twin[^\]]*\]|BUT mirror:?','',str(s)).strip()
nd=d.strict_definition.map(norm); m=dict(zip(d.id,nd))
d['dup_BUT_twin_identical']=[(i.endswith('-BUT') and i[:-4] in m and m[i]==m[i[:-4]]) or ('BUT twin of the same condition' in str(s)) for i,s in zip(d.id,d.strict_definition)]
s=d.strict_definition.astype(str)
d['impossible_rule']=s.str.contains('occurred exactly 1 session ago')&(s.str.contains("yesterday's close < the outlier candle's low",regex=False)|s.str.contains("yesterday's close > the outlier candle's high",regex=False))
g=d.groupby(nd).id.transform('size'); d['dup_identical_text_group']=g>1
cols=['id','merge_owner','root','pv_family','data_type','lens','variant','source','james_provider','james_raw_series','dup_BUT_twin_identical','impossible_rule','dup_identical_text_group']
d[cols].to_csv('rows_by_root.csv',index=False)
d.to_pickle('tagged_final.pkl')
print(pd.crosstab(d.root,d.merge_owner,margins=True).to_string())
print(d[d.pv_family!=''].groupby('pv_family').size().sort_values(ascending=False).to_string())
print(pd.crosstab(d[d.pv_family!=''].pv_family,d[d.pv_family!=''].merge_owner).to_string())
print('BUT identical',d.dup_BUT_twin_identical.sum(),d[d.dup_BUT_twin_identical].merge_owner.value_counts().to_dict())
print('impossible',d.impossible_rule.sum())
# clusters.csv from R
R=pd.read_pickle('R.pkl').reset_index(drop=True); R['root']=R.id.map(d.drop_duplicates('id').set_index('id').root); R['pv_family']=R.id.map(d.drop_duplicates('id').set_index('id').pv_family)
R[['id','merge_owner','root','pv_family','data_type','lens','variant','yes_rate','dead','cl_kappa80','rep_kappa80','cl_phi70','cc_kappa80','cc_phi70','strict_definition']].sort_values(['cl_kappa80','id']).to_csv('clusters.csv',index=False)
# per root views & independent (sample)
Z=np.load('pairs.npz',allow_pickle=True); P=Z['phi']; live=np.where(~R.dead.values)[0]
from scipy.cluster.hierarchy import linkage,fcluster
from scipy.spatial.distance import squareform
def effn(S):
    w=np.clip(np.linalg.eigvalsh((S+S.T)/2),0,None);return w.sum()**2/(w**2).sum()
def ncl(S,t):
    if len(S)<2: return len(S)
    D=1-np.clip(np.abs(S),0,1);np.fill_diagonal(D,0);D=(D+D.T)/2
    return len(set(fcluster(linkage(squareform(D,checks=False),'complete'),1-t,'distance')))
K=np.nan_to_num(Z['kappa'])
out=[]
Rl=R.iloc[live].reset_index(drop=True); Pl=P[np.ix_(live,live)]; Kl=K[np.ix_(live,live)]
for r,gg in Rl.groupby('root'):
    ix=gg.index.values
    out.append(dict(root=r,rows_in_sheet=(d.root==r).sum(),sampled=len(ix),clusters_kappa80=ncl(Kl[np.ix_(ix,ix)],0.8),clusters_phi70=ncl(Pl[np.ix_(ix,ix)],0.7),clusters_phi30=ncl(Pl[np.ix_(ix,ix)],0.3),eff_n=round(effn(Pl[np.ix_(ix,ix)]),1)))
T=pd.DataFrame(out); T.to_csv('per_root_sample.csv',index=False); print(T.to_string())
ks=np.array([50,100,200,300,400,459]); ys=[]
rng=np.random.default_rng(0)
for k in ks: ys.append(np.mean([effn(Pl[np.ix_(s,s)]) for s in [rng.choice(len(live),k,replace=False) for _ in range(8)]]))
f=lambda k,a,b:a*k/(b+k); (a,b),_=curve_fit(f,ks,ys,p0=[200,200]); print('saturation fit asymptote',round(a),'b',round(b),'pred@21308',round(f(21308,a,b)))
# raw sample data for recheck
SIG=pickle.load(open('signals.pkl','rb'))
long=pd.concat({k:v.stack(future_stack=True) for k,v in SIG.items()},axis=1)
long.index.names=['date','ticker']; long.astype('float32').to_parquet('raw_sample_signals.parquet')
print(long.shape)
