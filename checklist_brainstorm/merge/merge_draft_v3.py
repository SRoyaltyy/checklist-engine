import csv,re,collections,os
I='in/'
def ser(v): return re.sub(r'\s+',' ',re.sub(r'\(?\s*but( mirror| snap-back)?\s*\)?','',v,flags=re.I)).strip().lower()
def ser_ck(v): return re.sub(r'\s+',' ',re.sub(r'\(?\s*but( mirror)?\s*\)?','',v,flags=re.I)).strip().lower()
owners=[('taskforce','taskforce.csv',['fp_taskforce.csv']),('james','james.csv',['fp_james.csv']),
 ('new-bot','newbot.csv',['fp_newbot.csv']),
 ('theme-radar','theme.csv',['fp_theme.csv']),('manager-bot','manager.csv',['fp_manager.csv']),
 ('grok-bot','grok.csv',['fp_grok.csv']),('grok-bot','grokr.csv',['fp_grokr.csv'])]
COLS=['id','data_type','variant','lens','timeframe','strict_definition','yes_means','source','history_start','known_before_open?','added_by','notes']
def g(r,k):
    for kk in r:
        if kk and kk.lower().startswith(k.split(' ')[0].rstrip('?')): return (r[kk] or '').strip()
    return ''
J0925={'es move to 09:25 et','nq move to 09:25 et','rty move to 09:25 et','btc move prior 16:00 et to 09:25 et'};jrem=[];out=[];stats=collections.defaultdict(collections.Counter);proof={}
for o,f,fps in owners:
    for fp in fps:
        for p in csv.DictReader(open(I+fp,encoding='utf-8-sig')):
            proof[(o,ser_ck(p['series']))]=p
    for r in csv.DictReader(open(I+f,encoding='utf-8-sig')):
        stats[o]['in']+=1
        row={k:g(r,k) for k in COLS}; row['owner']=o
        p=proof.get((o,ser_ck(row['variant']))) or proof.get((o,ser(row['variant'])))
        st=(p['status'].strip().lower() if p else 'missing')
        if st not in('works','save_nightly'): stats[o]['drop_'+st]+=1; continue
        if o=='james' and ser(row['variant']) in J0925:
            stats[o]['drop_no_0925_snapshot_file']+=1; jrem.append(row); continue
        if o=='grok-bot' and row['data_type']=='overnight futures' and row['variant'] in('ES','NQ','RTY','BTC'):
            stats[o]['drop_james_0925_futures']+=1; continue
        if o=='theme-radar' and ser(row['variant']) in('atr14 % of price','rsi14'):
            stats[o]['drop_manager_dup_list']+=1; continue
        row['fetch_status']=st; out.append(row)
def n(s): return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9<>=.%+\-]',' ',s.lower())).strip()
seen={};final=[];dups=[]
for row in out:  # already in priority order
    k=tuple(n(row[c]) for c in('data_type','variant','lens','timeframe','strict_definition'))
    if k in seen and seen[k]!=row['owner']: stats[row['owner']]['drop_exact_dup_vs_'+seen[k]]+=1; dups.append(row); continue
    seen.setdefault(k,row['owner']); final.append(row)
for r in final: stats[r['owner']]['kept']+=1; stats[r['owner']]['kept_'+r['fetch_status']]+=1
H=['owner','fetch_status']+COLS
w=csv.DictWriter(open('draft_merged_v3.csv','w',newline=''),H);w.writeheader();w.writerows(final)
keys=sorted({k for c in stats.values() for k in c})
with open('draft_v3_owner_counts.csv','w',newline='') as fh:
    cw=csv.writer(fh);cw.writerow(['owner']+keys)
    for o in stats: cw.writerow([o]+[stats[o][k] for k in keys])
    cw.writerow(['TOTAL']+[sum(stats[o][k] for o in stats) for k in keys])
print(open('draft_v3_owner_counts.csv').read())
import shutil
T='/tmp/mergeroot3'; shutil.rmtree(T,ignore_errors=True); os.makedirs(T+'/inbox'); os.makedirs(T+'/qa/src')
by=collections.defaultdict(list)
for r in final: by[r['owner']].append(r)
for o,rs in by.items():
    w=csv.DictWriter(open(f'{T}/inbox/{o}.csv','w',newline=''),H);w.writeheader();w.writerows(rs)
with open('draft_v3_dups_dropped.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,H);w.writeheader();w.writerows(dups)

R0='no snapshot file yet; job starts 2026-10-22 09:25 ET at /home/box/james_snapshots/futures_0925/'
w=csv.DictWriter(open('removed_v3_james_0925.csv','w',newline=''),H+['removed_reason']);w.writeheader()
for r in jrem: r['removed_reason']=R0; w.writerow(r)
print('james 0925 cut',len(jrem))
