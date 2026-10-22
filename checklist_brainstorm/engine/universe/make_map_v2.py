import pandas as pd
M=pd.read_csv('six_bucket_map_v1.csv',dtype=str,keep_default_na=False); cols=list(M.columns); ch=[]
def setr(ids,**kw):
    for i in ids:
        m=M.row_id==i; assert m.sum()==1,i
        old=M.loc[m,['bucket','b7_squeeze_takeprofit']].values[0].tolist()
        for k,v in kw.items(): M.loc[m,k]=v
        ch.append((i,old,[M.loc[m,'bucket'].item(),M.loc[m,'b7_squeeze_takeprofit'].item()]))
setr(['nb4-PDS-NB-039-W0-EVT','nb4-PDS-NB-039-W0-EVT-BUT'],bucket='2',b7_squeeze_takeprofit='',notes='v2 room change: halt-in-last-day -> primary 2 (reversal), no Q7')
setr(['nb4-BRW-NB-056-W0-EVT','nb4-BRW-NB-056-W0-EVT-BUT'],bucket='4',b7_squeeze_takeprofit='',notes='v2 room change: Reg SHO new listing -> primary 4, Q7 removed')
setr(['nb4-BRW-NB-056-T20-CNT','nb4-BRW-NB-056-T20-CNT-BUT'],bucket='excluded',b7_squeeze_takeprofit='',notes='v2 room change: excluded, dropped from lock: zero inside top bullish fifth')
T=pd.read_csv('../out/tags/new-bot_si_tags.csv',dtype=str,keep_default_na=False)
P={'nbx-SI-ABS-DTC-HI':('2','meaning wins: loud_bearish -> 2 (rule a)'),'nbx-SI-ABS-DTC-LO':('3','bullish, position/threshold/extreme lens (rule b)'),
'nbx-SI-REL-RANK-HI':('2','meaning wins: loud_bearish -> 2 (rule a)'),'nbx-SI-REL-RANK-LO':('1','bullish, trend lens: rank'),
'nbx-SI-EXT-HI':('2','meaning wins: loud_bearish -> 2 (rule a)'),'nbx-SI-EXT-HI-BUT':('5','bullish, outlier lens (rule c)'),
'nbx-SI-DIV-ADD-INTO-RALLY':('none','context row: no 1-5 meaning (rule f); Q7 secondary only'),'nbx-SI-DIV-COVER-RALLY':('4','meaning wins: quiet_warning -> 4 (rule a)'),
'nbx-SI-THR-UP20':('2','meaning wins: loud_bearish -> 2 (rule a)'),'nbx-SI-THR-DN20':('3','bullish, position/threshold/extreme lens (rule b)'),
'nbx-SI-POS-HI':('2','meaning wins: loud_bearish -> 2 (rule a)'),'nbx-SI-POS-LO':('3','bullish, position/threshold/extreme lens (rule b)'),
'nbx-SI-B7-SQZ-FUEL':('none','context row: no 1-5 meaning (rule f); Q7 secondary only'),'nbx-SI-B7-TP-FUEL':('4','meaning wins: quiet_warning -> 4 (rule a)')}
assert set(T.row_id)==set(P),set(T.row_id)^set(P)
rows=[dict(row_id=r.row_id,source='new-bot-si',existing_tag=r.meaning,lens=r.lens,lens6=r.lens6,indicator=r.indicator,bucket=P[r.row_id][0],b7_squeeze_takeprofit='yes',in_engine_counts='SI chunks',notes='v2: '+P[r.row_id][1]) for r in T.itertuples()]
M=pd.concat([M,pd.DataFrame(rows)[cols]],ignore_index=True); M.to_csv('six_bucket_map.csv',index=False)
for c in ch: print(c)
for r in rows: print(r['row_id'],r['existing_tag'],r['lens'],'->',r['bucket'])
md=open('six_bucket_map_v1.md').read()+"""

## v2 changes (2026-10-22, pre-lock, room-agreed)
- Halt in last day (nb4-PDS-NB-039-W0-EVT and its BUT twin): primary 2 (reversal), no Q7 flag.
- Reg SHO new listing (nb4-BRW-NB-056-W0-EVT and its BUT twin): primary 4, Q7 flag removed.
- Reg SHO 20-day count (nb4-BRW-NB-056-T20-CNT and its BUT twin): excluded, dropped from lock (zero inside top bullish fifth).
- Added 14 New Bot nbx-SI-* rows (source new-bot-si, counted per row from chunks/{y}__SI__<sector>), all with the Q7 flag; primary buckets by rules a-f:
""" + "\n".join(f"  - {r['row_id']} ({r['existing_tag']}, {r['lens']}): {r['bucket']}" for r in rows) + """
- Pending, not mapped yet (await owners' tags): Taskforce PV-TFC-0921..0960, Theme Radar Short Ratio / POS-TR-F0121..F0127 (plus OWN-TR-*|1 ids in SI chunks). Their SI-chunk answers are skipped.
- v1 kept read-only as six_bucket_map_v1.csv / .md.
"""
open('six_bucket_map.md','w').write(md)
