import pandas as pd,re
v=pd.read_csv('merged_draft_v8.1.csv').fillna('')
m=pd.read_csv('inbox/tradingview_master.csv')
for mid,item,grp in [('M295',"Another symbol's own chart (candles/indicators on a non-stock symbol)",'chart feature'),('M296','Breadth symbols (S5FI/S5TH/S5TW, new highs minus lows)','breadth')]:
    if mid not in set(m.id): m=pd.concat([m,pd.DataFrame([dict(id=mid,item=item,group=grp,status='proposed (not yet in master)',kind='raw')])])
tag={};raw={};conf={};extra={}
# theme radar: strip -C suffix, match folded first id
tr=pd.read_csv('inbox/tags/theme_radar_tv_tags.csv').set_index('id')
for i in v[v.merge_owner=='theme-radar'].id:
    k=re.sub(r'-C$','',i)
    if k in tr.index:
        tag[i]=tr.at[k,'tv_master_id'];raw[i]='raw' if tr.at[k,'data_kind']=='raw_data' else 'math';conf[i]='owner tag'
        st=str(tr.at[k,'second_tag']) if 'second_tag' in tr.columns else ''
        if st not in ('','nan'): extra.setdefault(i,set()).update(x.strip() for x in st.replace(';',',').split(',') if x.strip())
nb=pd.read_csv('inbox/tags/new-bot_tradingview_tags.csv').sort_values('in_compact',ascending=False).drop_duplicates('row_id').set_index('row_id')
for i in v[v.merge_owner=='new-bot'].id:
    if i in nb.index: tag[i]=nb.at[i,'master_id'];raw[i]=nb.at[i,'raw_or_math'];conf[i]='owner tag'
ja=pd.read_csv('inbox/tags/james_tv_tags.csv').set_index('id')
jm=pd.read_csv('/workspace/james_tradingview_map.csv').set_index('id')
for i in v[v.merge_owner=='james'].id:
    if i in ja.index:
        t=ja.at[i,'master_id']; s=str(jm.at[i,'tv_symbol_or_indicator']) if i in jm.index else ''
        tag[i]=t;raw[i]=ja.at[i,'raw_or_math'];conf[i]='owner tag'
# grok
for _,r in v[v.merge_owner=='grok-bot'].iterrows():
    i=r.id;dt=r.data_type
    if dt=='estimate revision': t='M010';rw='math'
    elif dt.startswith('analyst'): t='M134' if re.search('target',r.variant,re.I) else 'M010';rw='raw'
    elif 'CFTC' in dt: t='off-chart';rw='raw'
    elif dt=='sector-future vs stock': t='M294';rw='math'
    else: t='M295';rw='raw' if re.fullmatch(r'VIX9D|VIX3M|VIX',r.variant.split(' ')[0]) else 'math'
    tag[i]=t;raw[i]=rw;conf[i]='Grok tag'
# taskforce by name
R=[('CDL','pat'),(r'Heikin','M216'),(r'MACD','M114'),(r'StochRSI','M164'),(r'Connors RSI','M042'),(r'RSI','M142'),(r'Stoch','M162'),(r'Williams %R','M205'),(r'CCI','M041'),(r'Bollinger.*(bandwidth|squeeze)','M031'),(r'Bollinger','M030'),(r'Keltner','M078'),(r'Donchian','M052'),(r'ATR trailing|Volatility stop','M197'),(r'Chandelier','M038'),(r'Chande Kroll','M036'),(r'ATR|NATR|Range vs ATR','M022'),(r'Ichimoku','M075'),(r'Supertrend','M166'),(r'Parabolic SAR','M124'),(r'anchored VWAP','M203'),(r'VWMA','M201'),(r'VWAP','M200'),(r'POC|value area','M270'),(r'classic pivot','M129'),(r'Fibonacci zone','M015'),(r'ADX|\+DI|DX14|\+DM','M020'),(r'Aroon','M012'),(r'Awesome','M023'),(r'Balance of power','M024'),(r'Elder ray','M033'),(r'Chande momentum','M037'),(r'Coppock','M043'),(r'Correlation','M044'),(r'Detrended','M048'),(r'Fisher','M067'),(r'Hull|HMA','M074'),(r'KAMA','M077'),(r'KST','M080'),(r'Linear regression|regression','M084'),(r'Mass index','M090'),(r'McGinley','M091'),(r'median','M102'),(r'Momentum 10','M111'),(r'MFI','M112'),(r'OBV','M122'),(r'Negative volume','M120'),(r'Positive volume','M130'),(r'Price volume trend','M135'),(r'Percentage volume','M126'),(r'PPO','M125'),(r'Rate of change','M138'),(r'Relative vigor','M143'),(r'Relative volatility','M144'),(r'Stochastic momentum','M163'),(r'TEMA','M187'),(r'TRIX','M188'),(r'True strength','M189'),(r'Ulcer','M190'),(r'Ultimate','M191'),(r'Vortex','M202'),(r'WMA','M204'),(r'alligator','M206'),(r'fractal','M207'),(r'ZigZag','M209'),(r'DEMA','M053'),(r'ALMA','M011'),(r'smoothed MA|RMA','M159'),(r'Choppiness','M040'),(r'Average daily range','M019'),(r'Historical vol|Realized vol|Parkinson|Garman','M073'),(r'Chaikin oscillator','M035'),(r'Chaikin Money','M034'),(r'Accumulation/Distribution','M003'),(r'Ease of movement','M054'),(r'Force index','M056'),(r'Klinger','M079'),(r'EMA\d|vs EMA','M066'),(r'SMA|Stacked MAs|Days (above|below) SMA','M156'),(r'vs SPY|vs sector','M294'),(r'Short|Days to cover|SSR','M293'),(r'earnings','M275'),(r'Halt','off-chart'),(r'VIX','M295'),(r'52w|all-time|ATH','M127'),(r'Up-volume','M193'),(r'Relative volume|Dollar volume|volume','M198'),(r'Hammer|engulf','pat'),(r'gap','M211'),(r'outlier|Body|wick|candle|Daily return|Change from open|range|green|red|streak|Consecutive','M211')]
pat={'CDL2CROWS':None}
mi=m.set_index('id')
def patm(s):
    s=s.upper().replace('CDL','')
    P=[(idx,re.sub(r'[^A-Z]','',it.split(' - ')[0].upper())) for idx,it in mi[mi.group=='patterns']['item'].items()]
    al={'RISEFALLMETHODS':'RISINGTHREEMETHODS','TASUKIGAP':'UPSIDETASUKIGAP','BLACKCROWS':'THREEBLACKCROWS','WHITESOLDIERS':'THREEWHITESOLDIERS','CLOSINGMARUBOZU':'MARUBOZUWHITE','MARUBOZU':'MARUBOZUWHITE','INNECK':'XX','SPINNINGTOP':'SPINNINGTOPWHITE'}
    s=re.sub(r'^3','',s); s=al.get(s,s)
    for idx,k in P:
        if k==s: return idx
    return None
tfraw=r'Short|Days to cover|SSR|Halt|earnings'
tf0=pd.read_csv('v8src/tf-v10.4.tags.csv');tf0=tf0[tf0.file=='compact']
for rid,gp in tf0[tf0.match=='second_tag'].groupby('row_id'):
    extra.setdefault(rid,set()).update(x if o=='yes' else 'off-chart' for x,o in zip(gp.master_id,gp.on_chart))
tf=tf0[tf0.match!='second_tag'].drop_duplicates('row_id').set_index('row_id')
for i in v[v.merge_owner=='taskforce'].id:
    if i in tf.index:
        x=tf.loc[i];t=x.master_id if x.on_chart=='yes' else 'off-chart'
        tag[i]=t;raw[i]='raw' if x.raw_or_derived=='raw' else 'math';conf[i]='owner tag ('+str(x.match)+')'
v['tv_id']=v.id.map(tag).fillna('untagged').replace({'M293':'off-chart','M292':'off-chart','OFF':'off-chart','off':'off-chart'});v['raw_or_math']=v.id.map(raw).fillna('');v['tag_conf']=v.id.map(conf).fillna('')
_tf=pd.read_csv('inbox/trading-bot-taskforce-timeframes.csv').set_index('id')
_k=v.block=='timeframe_pilot';v.loc[_k,'tv_id']=v.id[_k].map(_tf.tradingview_id);v.loc[_k,'raw_or_math']='math';v.loc[_k,'tag_conf']='owner tag (timeframe file)'
import re as _r
txt=v.variant+' '+v.strict_definition+' '+v.source
def H(w,x,h0=''):
    out=[h0] if h0 else []
    if w in('theme-radar','new-bot') and _r.search(r'market cap|shares outstanding|float',x,_r.I): out.append('ON HOLD until Market Cap/Shares Outstanding checked vs Yahoo')
    if w=='theme-radar' and _r.search(r'volume',x,_r.I): out.append('skip 08-06 and 08-10 volume days')
    if w=='theme-radar' and _r.search(r'earnings date',x,_r.I): out.append('unchecked: Finviz Earnings Date')
    return '; '.join(dict.fromkeys(out))
v['hold']=[H(w,x,h) for w,x,h in zip(v.merge_owner,txt,v.hold)]
v['extra_tags']=[';'.join(sorted(extra.get(i,set())-{t})) for i,t in zip(v.id,v.tv_id)]
XT=v.extra_tags.str.split(';')
v[['id','merge_owner','hold','flag','low_info','block','extra_tags','variant','data_type','tv_id','raw_or_math','tag_conf']].to_csv('qa/tradingview/row_tags.csv',index=False)
FIX={'M286':'unchecked - failed Finviz self-consistency; ','M282':'market cap part unchecked - failed Finviz self-consistency; '}
NOTE={k:'near-copy only (Manager Bot)' for k in ['M186','M208','M057','M197','M237','M257']}

out=[]
for _,x in m.iterrows():
    s=v[(v.tv_id==x.id)|XT.apply(lambda L:x.id in L)];own=s.merge_owner.value_counts()
    out.append(dict(tv_id=x.id,tv_item=x['item'],tv_group=x.group,master_status=x.status,in_sheet='yes' if len(s) else 'no',row_count=len(s),owners='; '.join(f'{k}:{n}' for k,n in own.items()),cross_owner_duplicate='yes' if len(own)>1 else 'no',raw_rows=(s.raw_or_math=='raw').sum(),math_rows=(s.raw_or_math=='math').sum(),raw_vs_math=('raw' if (s.raw_or_math=='raw').all() else 'math' if (s.raw_or_math=='math').all() else 'mixed') if len(s) else x.kind,example_row_id=s.id.iloc[0] if len(s) else '',hold_rows=(s.hold!='').sum(),low_conf_rows=s.tag_conf.str.startswith('low').sum(),notes=FIX.get(x.id,'')+'; '.join(z for z in [NOTE.get(x.id,''),str(x.note_or_how_to_fetch) if False else ''] if z)))
c=pd.DataFrame(out);c.to_csv('qa/tradingview/coverage.csv',index=False)
print(v.tv_id.value_counts().head(8));print(v.groupby('merge_owner').tv_id.apply(lambda s:(s=='untagged').sum()))
st=c[c.master_status!='n/a-not-a-stock-chart']
print(len(st),pd.crosstab(st.master_status,st.in_sheet))
print('rows off',(v.tv_id.isin(['off-chart','not_on_chart'])).sum(),'untag',(v.tv_id=='untagged').sum(),'on',len(v)-(v.tv_id.isin(['off-chart','not_on_chart','untagged'])).sum())
print(v.raw_or_math.value_counts())
print(c[c.cross_owner_duplicate=='yes'][['tv_id','tv_item','owners']].to_string())
print(c[(c.master_status=='have')&(c.in_sheet=='no')][['tv_id','tv_item']].to_string())
print(c[(c.master_status!='have')&(c.in_sheet=='yes')][['tv_id','tv_item','master_status','owners']].to_string())
print(v.tag_conf.value_counts())
print(v[v.merge_owner=='grok-bot'].tv_id.value_counts())
