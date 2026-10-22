import pandas as pd
m=pd.read_csv('map_coverage.csv',low_memory=False); m=m[m.row_id.str.startswith('nb')].copy()
v=pd.read_csv('/workspace/checklist_brainstorm/map_v5/six_bucket_map_v5_1.csv',low_memory=False).set_index('row_id')
cov=pd.concat(pd.read_csv(f'tags/nb_tags_coverage_{y}.csv') for y in range(2020,2025)).groupby(['row_id','src'])[['nr','no','yes']].sum().reset_index().set_index('row_id')
m['base']=m.row_id.str.split('-').str[1:4].str.join('-'); m.loc[m.row_id.str.startswith('nbx-SI'),'base']='SI'; m.loc[m.row_id.str.contains('FINRA'),'base']='FINRA-FS'
FAM={'AHR':'after-hours','BRW':'borrow/RegSHO','CAC':'corporate action','DIL':'dilution','ERN':'earnings','EVT':'events','HIS':'history','IPO':'IPO','OPX':'options','PDS':'price/day structure','REL':'relative/cross-market','SI':'short interest','FINRA-FS':'FINRA short volume'}
NEED={'AHR':'after-hours bars (Finviz AH snapshots)','ERN-NB-023':'revenue consensus + actual','CAC':'dividend declaration dates','DIL':'PIT shares outstanding/float history',
'REL-NB-027':'foreign home-listing prices + FX','REL-NB-028':'index futures at 09:25 ET','PDS-NB-037':'$1 compliance inference','PDS-NB-038':'$1 compliance inference','IPO-NB-074':'IPO date/age inference',
'PDS-NB-014':'earnings dates + daily OHLCV (AVWAP)','ERN-NB-022':'EPS surprise %','ERN-NB-024':'earnings dates + daily closes','ERN-NB-091':'earnings dates + daily OHLC/ATR','PDS-NB-039':'trading halts','BRW-NB-056':'Reg SHO threshold list','SI':'FINRA short interest','FINRA-FS':'FINRA daily short volume'}
BLK={'AHR':'no 2020-24 after-hours history (Finviz AH snapshots start 2026-08; no free intraday ext-hours archive)',
'ERN-NB-023':'no free 2020-24 revenue consensus','CAC':'no dividend declaration dates in store (candidate: Nasdaq dividend-history declaration_date, not built)',
'DIL':'shares/float snapshot-only (candidate: SEC XBRL dei:EntityCommonStockSharesOutstanding by filing date, not built)',
'REL-NB-027':'no foreign home-listing price + FX history','REL-NB-028':'no 2020-24 09:25 futures prints'}
EX='excluded inference row ($1 compliance / IPO-age), no reader by design'
rows=[]
for r in m.itertuples():
    fam=r.base if r.base in('SI','FINRA-FS') else r.base.split('-')[0]; c=cov.loc[r.row_id] if r.row_id in cov.index else None
    if r.status=='TESTED': st,why='WIRED','already in James step-3 ranking (skip)'
    elif r.status=='BUILT_NOT_TESTED': st,why='WIRED','answers exist, not yet tested -> James'
    elif c is not None and (c.yes+c.no)>0:
        if c.yes==0 or c.no==0: st,why='WIRED_DEGENERATE',f'wired via {c.src} but constant on answered cells (yes={c.yes}, no={c.no})'
        else: st,why='WIREABLE',f'wired now via {c.src} chunks 2020-24'
    else:
        st='BLOCKED'; why=BLK.get(r.base) or BLK.get(fam) or EX
    rows.append(dict(row_id=r.row_id,name=v.indicator.get(r.row_id,r.indicator),source_family=f'{r.base} ({FAM[fam]})',needed_data=NEED.get(r.base) or NEED.get(fam) or 'daily OHLCV / existing chunk',
       status=st,reason=why,grok_status=r.status,chunk_src=c.src if c is not None else '',yes=int(c.yes) if c is not None else 0,no=int(c.no) if c is not None else 0,nr=int(c.nr) if c is not None else 0,side_row=r.row_id.startswith('nbx-')))
s=pd.DataFrame(rows); s.to_csv('nb_map_status_v1.csv',index=False)
print(pd.crosstab([s.side_row,s.grok_status],s.status)); print(s[s.status=='BLOCKED'].reason.value_counts().to_string())
print(s[s.status=='WIRED_DEGENERATE'][['row_id','yes','no']].to_string())
print(s[s.status=='WIREABLE'].source_family.value_counts())
