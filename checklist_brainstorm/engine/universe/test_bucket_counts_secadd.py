# Self-test: fake STK + SECADD + MKT + FRED + SI in a temp dir; real map read-only. Never touches chunks/ or tags.
import os, sys, subprocess, tempfile, pandas as pd, numpy as np, json
M=pd.read_csv('six_bucket_map.csv',dtype=str).fillna('')
j=M[(M.source=='james')&(M.bucket=='1')].iloc[0]
g=f"stk|james|{j.lens or 'none'}|{j.existing_tag.replace('asterisk','context')}"
T=tempfile.mkdtemp(); env=dict(os.environ,BUCKET_CHUNKS=T)
stk=pd.DataFrame({'ticker':['AAA','BBB','CCC'],'date':['2024-01-02']*3,g+'|yes':[0,0,0],g+'|ready':[0,0,0]})
stk.to_parquet(f'{T}/2024__COUNTS2_STK__Energy.parquet',index=False)
run=lambda: subprocess.run([sys.executable,'bucket_counts.py','2024'],env=env,check=True,capture_output=True,text=True)
# 1) no add-ons -> NOT_READY
run(); o=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
assert (o.secadd_status=='NOT_READY_NO_FILE').all() and (o.mkt_status=='NOT_READY_NO_FILE').all() and (o.si_status=='NOT_READY_NO_FILE').all()
# 2) SECADD
pd.DataFrame({'ticker':['AAA','BBB','ZZZ'],'date':['2024-01-02','2024-01-02','2025-01-02'],g+'|yes':[2,0,9],g+'|ready':[2,3,9]}).to_parquet(f'{T}/2024__COUNTS2_SECADD_ALL.parquet',index=False)
pd.DataFrame({'ticker':['AAA'],'date':['2024-01-02'],g+'|yes':[5],g+'|ready':[5]}).to_parquet(f'{T}/2024__COUNTS2_SECADD_SP500.parquet',index=False)
run(); o=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet').set_index('ticker')
assert list(o.secadd_status)==['JOINED','JOINED','NOT_READY_NO_ROW']
assert (o.b1_yes.tolist(),o.b1_ready.tolist())==([2,0,0],[2,3,0])
print('PASS group',g)
# 3) MKT one vote
mj=M[(M.source=='grok')&(M.bucket=='3')].iloc[0]; mg=f"mkt|grok|{mj.lens or 'none'}|{mj.existing_tag.replace('asterisk','context')}"
stk2=pd.concat([stk,stk.assign(date='2024-01-03')]); stk2.to_parquet(f'{T}/2024__COUNTS2_STK__Energy.parquet',index=False)
pd.DataFrame({'date':['2024-01-02','2025-01-02'],mg+'|yes':[1500,9],mg+'|ready':[1680,9]}).to_parquet(f'{T}/2024__COUNTS2_MKT.parquet',index=False)
run(); o=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
a=o[o.date=='2024-01-02']; n=o[o.date=='2024-01-03']
assert (a.mkt_status=='JOINED').all() and (n.mkt_status=='NOT_READY_NO_ROW').all()
assert (a.b3_ready.values - n.b3_ready.values == 1).all() and (a.b3_yes.values - n.b3_yes.values == 1).all()
print('PASS mkt',mg)
# 4) FRED
sys.path.insert(0,'.'); import engine_year as E
fid=M[M.row_id.str.startswith('CAL-JA')&M.bucket.isin(['1','2','4'])].iloc[0]; fb=fid.bucket
pk=lambda codes: bytes([codes[0]|(codes[1]<<2)])
pd.DataFrame({'date':['2024-01-02','2024-01-03'],'packed':[pk([2,0]),pk([1,0])]}).to_parquet(f'{T}/2024__JA_FRED_MKT.parquet',index=False)
json.dump({'ids':[fid.row_id,'NOT-IN-MAP-XYZ']},open(f'{T}/2024__JA_FRED_MKT.json','w'))
p=run(); assert 'NOT-IN-MAP-XYZ' in p.stdout
o2=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
a2=o2[o2.date=='2024-01-02']; n2=o2[o2.date=='2024-01-03']
assert (a2[f'b{fb}_ready'].values-a[f'b{fb}_ready'].values==1).all()
print('PASS fred',fid.row_id,'bucket',fb)
# 5) SI New Bot + TR with |N strip; pending PV skipped
sids=['nbx-SI-ABS-DTC-HI','nbx-SI-B7-SQZ-FUEL','OWN-TR-00793-C|1','POS-TR-F0121-C|20','PV-TFC-0921|1']
pk5=lambda c: bytes([c[0]|(c[1]<<2)|(c[2]<<4)|(c[3]<<6)])+bytes([c[4]])
pd.DataFrame({'ticker':['AAA','BBB'],'date':['2024-01-02']*2,'packed':[pk5([2,2,2,2,2]),pk5([1,0,1,0,2])]}).to_parquet(f'{T}/2024__SI__Energy.parquet',index=False)
json.dump({'ids':sids},open(f'{T}/2024__SI__Energy.json','w'))
# clean STK so we measure SI-only deltas from a known base (still has mkt/fred/secadd from files)
base=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
run(); o3=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
B=o3[(o3.date=='2024-01-02')].set_index('ticker'); A=base[(base.date=='2024-01-02')].set_index('ticker')
d=lambda c: (B[c]-A[c]).tolist()
# AAA: nbx HI(b2+b7) + SQZ(b7) + OWN793(b3+b7) + POS121(b3+b7) = b2+1, b3+2, b7+4; BBB: HI ready-only(b2+b7), SQZ NR, OWN NO(b3+b7 ready), POS NR, PV skip
assert d('b7_ready')[:2]==[4,2] and d('b7_yes')[:2]==[4,0], (d('b7_ready'),d('b7_yes'))
assert d('b2_ready')[:2]==[1,1] and d('b2_yes')[:2]==[1,0]
assert d('b3_ready')[:2]==[2,1] and d('b3_yes')[:2]==[2,0]
assert B.si_status.tolist()[:3]==['JOINED','JOINED','NOT_READY_NO_ROW']
print('PASS si + tr |N strip (pending PV skipped)')
print('ALL PASS')
# ATTN wide: SPIKE15 (b3) YES, DORMANT (none, no Q7) YES shouldn't add b7; missing CCC -> NOT_READY
base=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
pd.DataFrame({
  'ticker':['AAA','BBB'],'date':['2024-01-02']*2,
  'theme-radar-attn|tr-attn-01-SPIKE15':[2,1],
  'theme-radar-attn|tr-attn-09-DORMANT':[2,2],
}).to_parquet(f'{T}/2024__ATTN__Energy.parquet',index=False)
run(); o5=pd.read_parquet(f'{T}/2024__BUCKETS7_STK__Energy.parquet')
B=o5[o5.date=='2024-01-02'].set_index('ticker'); A=base[base.date=='2024-01-02'].set_index('ticker')
d=lambda c:(B[c]-A[c]).tolist()
assert B.attn_status.tolist()[:3]==['JOINED','JOINED','NOT_READY_NO_ROW']
assert d('b3_ready')[:2]==[1,1] and d('b3_yes')[:2]==[1,0]
assert d('b7_ready')[:2]==[0,0]  # DORMANT has no Q7 flag
print('PASS attn')
print('ALL PASS v4')
