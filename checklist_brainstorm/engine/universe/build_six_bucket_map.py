import pandas as pd, re
T='/workspace/checklist_brainstorm/engine/out/tags/'
excl=set(pd.read_csv(T+'new-bot_excluded_inference.csv').row_id)
src=[]
g=pd.read_csv(T+'grok_tags.csv'); g['source']='grok'; src.append(g)
j=pd.read_csv(T+'james_tags.csv'); j['source']='james'; j['indicator']=''; src.append(j)
tr=pd.read_csv(T+'theme-radar_tags.csv'); tr['source']='theme-radar'
tr['row_id']=tr.row_id+tr.N.map(lambda n:'' if pd.isna(n) else f'|{int(n)}'); src.append(tr)
nb=pd.read_csv(T+'new-bot_tags.csv'); nb['source']='new-bot'; src.append(nb)
nf=pd.read_csv(T+'new-bot_finra_tags.csv'); nf['source']='new-bot-finra'; src.append(nf)
op=pd.read_csv(T+'options_tags.csv'); op['source']='grok-options'; src.append(op)
cols=['row_id','source','meaning','lens','indicator']
D=pd.concat([s.reindex(columns=cols+['lens6','tag_reason']) for s in src],ignore_index=True)
# indicator from sheet for james (bucket-7 text match only)
sh=pd.read_csv('/workspace/checklist_brainstorm/merged_draft_v8.2.csv',usecols=['id','variant','data_type']).drop_duplicates('id').set_index('id')
base=D.row_id.str.split('|').str[0]
D['indicator']=D.indicator.fillna('').astype(str)
miss=D.indicator.eq('')
D.loc[miss,'indicator']=base[miss].map(lambda i: (str(sh.at[i,'data_type'])+': '+str(sh.at[i,'variant'])) if i in sh.index else '')
assert not D.row_id.duplicated().any()

OUT=re.compile(r'outlier|rare vs own record',re.I)
POS=re.compile(r'extreme|percentile|position|quartile|decile|threshold|level|days-in-zone|range',re.I)
def bucket(r):
    m=r.meaning; l=str(r.lens); l6=str(r.lens6)
    if r.row_id in excl: return 'excluded','New Bot excluded inference row ($1 compliance / IPO-age)'
    if m in('context','neutral'): return 'none','context row: in no bucket (rule f)'
    if m=='asterisk': return 'none','asterisk = context at count time; feeds bucket 2 only via live ctx_opp contrary count'
    if m=='quiet_warning': return '4','meaning wins: quiet_warning -> 4 (rule a)'
    if m=='loud_bearish': return '2','meaning wins: loud_bearish -> 2 (rule a)'
    # bullish: lens decides
    if OUT.search(l) or l6=='outlier': return '5','bullish, outlier lens (rule c)'
    if POS.search(l) or l6 in('position','threshold'): return '3','bullish, position/threshold/extreme lens (rule b)'
    return '1','bullish, trend lens (streak/cross/change/rank/divergence/timeframe/relative)'
r=D.apply(bucket,axis=1,result_type='expand'); D['bucket']=r[0]; D['notes']=r[1]
S7=re.compile(r'money flow|\bMFI\b|short|reg sho|\bSSR\b|option|implied vol|\bIV\b|put/call|put-call|gamma|squeeze',re.I)
D['b7_squeeze_takeprofit']=D.indicator.str.contains(S7)|D.source.isin(['grok-options','new-bot-finra'])
D['b7_squeeze_takeprofit']=D.b7_squeeze_takeprofit.map({True:'yes',False:''})
D['in_engine_counts']=D.source.map({'grok':'yes','james':'yes','theme-radar':'yes','new-bot':'no (no reader port)','new-bot-finra':'NBX chunks','grok-options':'pending (DoltHub IV build)'})
D.rename(columns={'meaning':'existing_tag'})[['row_id','source','existing_tag','lens','lens6','indicator','bucket','b7_squeeze_takeprofit','in_engine_counts','notes']].to_csv('/workspace/checklist_brainstorm/engine/universe/six_bucket_map.csv',index=False)
print(D.bucket.value_counts()); print(pd.crosstab(D.source,D.bucket)); print('b7',(D.b7_squeeze_takeprofit=='yes').sum()); print(D[D.b7_squeeze_takeprofit=='yes'].groupby('source').size())
print(D[(D.bucket=='1')].lens.value_counts().head(30))
