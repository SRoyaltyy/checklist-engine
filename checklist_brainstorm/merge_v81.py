import pandas as pd
v8=pd.read_csv('merged_draft_v8.csv',low_memory=False)
COLS=list(v8.columns)+['signal_group','flag','block','low_info']
B=pd.read_csv('qa/beta_and_ratio_ids.csv')
parts=[]
def add(df,owner,src,note=''):
    df=df.copy();df['merge_owner']=owner;df['merge_src']=src;df['merge_note']=note
    if 'yes_means' in df and 'yes_means (bullish/bearish)' not in df: df=df.rename(columns={'yes_means':'yes_means (bullish/bearish)'})
    parts.append(df)
j=pd.read_csv('v8src/James-v5.5e.csv');rm=pd.read_csv('v8src/James-removed-v5.5e.csv')
j=j[~j.id.isin(rm.id)];add(j,'james','James-v5.5e.csv')
g=pd.read_csv('out_v3f/grok-bot-checklist-v3f-fetch.csv').drop(columns='owner_file?');add(g,'grok-bot','grok-bot-checklist-v3f-fetch.csv')
r=pd.read_csv('out_v3e/grok-bot-ratings-v3e.csv').drop(columns='owner_file?');add(r,'grok-bot','grok-bot-ratings-v3e.csv')
vt=pd.read_csv('inbox/grok-bot-vix-term.csv');add(vt,'grok-bot','grok-bot-vix-term.csv','MKT-JA check: identical (id/variant/definition) to James VIX term rows in James-removed-v5.5d.csv (handoff) -> owner Grok')
nb=pd.read_csv('inbox/new-bot-v4.4g.compact.csv');add(nb,'new-bot','new-bot-v4.4g.compact.csv')
t=pd.read_csv('v8src/tf-v10.5.compact.csv')  # Taskforce v10.5 (Drive 1YjNmJTqGYQdxr4VLFp0vfpwNwJ0kW90G)
drop=pd.read_csv('v8src/tf-v10.4.dropped.csv');assert not t.id.isin(drop.id).any();assert not t.id.duplicated().any()
ftd=t.id.between('PV-TFC-1001','PV-TFC-1020');assert ftd.sum()==20
t=t[~ftd];assert t.low_info.notna().sum()==35;add(t,'taskforce','tf-v10.5.compact.csv')
tf=pd.read_csv('inbox/trading-bot-taskforce-timeframes.csv')
assert len(tf)==224 and not tf.id.duplicated().any()
isb=tf.lens.str.endswith('(BUT)');base=tf.id.where(~isb).ffill();assert (tf.lens[isb].str.replace(' (BUT)','').values==tf.lens.shift()[isb].values).all()
tf['signal_group']=base;tf['block']='timeframe_pilot'
add(tf,'taskforce','trading-bot-taskforce-timeframes.csv','timeframe_pilot block; Manager Bot retest passed 2026-10-22 (SMA20-vs-SMA50 rows and twin thresholds not checked)')
tr=pd.read_csv('inbox/theme-radar.compact.csv');add(tr,'theme-radar','theme-radar.compact.csv')
m=pd.concat(parts,ignore_index=True)
for c in COLS:
    if c not in m: m[c]=''
m=m[COLS].fillna('')
m['signal_group']=m.signal_group.where(m.signal_group!='',m.id)
fin=m.id.between('PV-TFC-0881','PV-TFC-0900')&(m.merge_owner=='taskforce');assert fin.sum()==20
m.loc[fin,'flag']='FLAGGED: FINRA short volume, needs 2 clean nightly GitHub pulls'
hold=pd.Series('',index=m.index)
hold[m.id.isin(B[B.set=='theme_radar_mcap_ratio'].id)&(m.merge_owner=='theme-radar')]='ON HOLD: market-cap-derived ratio (qa/beta_and_ratio_ids.csv)'
hold[(m.merge_owner=='grok-bot')&m.notes.str.startswith('HOLD=no_nightly_archive')]='ON HOLD: no nightly archive yet'
hold[m.notes.str.contains('newroots',case=False)|m.source.str.contains('newroots',case=False)]='ON HOLD: newroots, needs 2 clean nightly runs'
js=(m.merge_owner=='james')&(m.source+' '+m.notes+' '+m.strict_definition).str.contains('newyorkfed|NY Fed|New York Fed|SOFR|reverse repo|treasurydirect|auction|fiscaldata|cash balance|treasury.gov|daily treasury par yield',case=False)
hold[js]='ON HOLD: James new source, needs 2 clean nightly GitHub pulls';print('james new-source held',js.sum())
m['hold']=hold
d=m.id[m.id.duplicated()];assert len(d)==0,d.tolist()
m.to_csv('merged_draft_v8.1.csv',index=False)
print(len(m));print(m.merge_owner.value_counts());print('hold',(m.hold!='').sum(),m.groupby('merge_owner').hold.apply(lambda s:(s!='').sum()).to_dict(),'flag',(m.flag!='').sum())
assert (m.merge_owner=='taskforce').sum()==len(t)+224
assert not m.id.isin(drop.id).any()
print('FTD present',m.id.between('PV-TFC-1001','PV-TFC-1020').sum(),'FINRA flagged',(m.flag!='').sum())
print('BUT',m.id.str.endswith('-BUT').sum(),'groups',m.signal_group.nunique())
but=m[m.lens.str.endswith('(BUT)')|m.id.str.endswith('-BUT')]
nob=but[~but.signal_group.isin(m.id[~m.index.isin(but.index)])]
print('BUT rows',len(but),'BUT without base',len(nob),'empty signal_group',(m.signal_group=='').sum())
print('pulled/math');print(m.groupby('merge_owner').size())
