# v2.7.2.1 review pass over CUTOFF_GRID_v2.7.2: drop structural/noise rows, merge same-concept cutoffs into shared ids
import csv,re,json,math,collections,sys
G=sys.argv[1] if len(sys.argv)>1 else '/workspace/v272/pkg/CUTOFF_GRID_v2.7.2.csv'
TREE=sys.argv[2] if len(sys.argv)>2 else '/workspace/v271/tree/QUESTION_TREE_v2.7.1.csv'
rows=list(csv.DictReader(open(G)))
def V(r): return float(r['current_default'])
def loc(r): c=r['context']; return c[-75:]
# ---- DROP rules (structural / identity / derived bin edges) ----
DROP=[
 (r'[123]-bar pattern', None, 'pattern size = facet identity'),
 (r'needs up to 756', None, 'data-availability requirement, not a cutoff'),
 (r'26 bars', 26.0, 'Ichimoku displacement = indicator identity'),
 (r'\(9\)', None, 'count of start->end pairs (descriptive)'),
 (r'Top-3', None, 'facet identity (top-3 days)'),
 (r'SMA5,10,20,30|4 MAs|all 4 MAs|≥2 adjacent', None, 'MA set membership (identity)'),
 (r'N/3|thirds|floor\(N/3\)', 3.0, 'thirds split = structural'),
 (r'N/4', 4.0, 'pole length as share of window = structural split'),
 (r'N//2|max\(10,N', None, 'MA length tied to window = structural'),
 (r'last 2 pivot|2 pivot (lows|highs)|≥2 pivot', 2.0, 'two pivots = minimum to define a swing (structural)'),
 (r'last 3 phases|phase_seq3|Labels of the last 3', 3.0, 'seq length = facet identity'),
 (r'\|Δ3\|/\|Δ1\|', 3.0, 'thirds index (structural)'),
 (r'Fib only|23\.6,38\.2', None, 'Fibonacci level identities'),
 (r'middle 80%', None, 'interior-extreme guard (structural)'),
 (r'new touch = after >=1 bar', 1.0, 'touch separation 1 bar = structural'),
 (r'3-ATR leg rule|no 3-ATR move|ATR at leg start', 3.0, 'restates leg_atr (merged)'),
]
# ---- MERGE rules: concept_id, regex on local context, unit set, value ----
M=[
 ('flat_base_atr',r'\(max H-min L\) ≤2 ATR',{'atr'},2),
 ('leg_atr',r'leg|pole|reverses|pump|phase',{'atr'},3),
 ('base_range_atr',r'flat stretch|range <=3|range ≤3|base',{'atr'},3),
 ('base_min_bars',r'>=10 bars|≥10 bars|≥15 bars|over >=10',{'bars','scalar'},None),
 ('leg_min_bars',r'and >=5 bars|>=5 bars\)',{'bars'},5),
 ('shock_max_bars',r'in <=3 bars',{'bars'},3),
 ('shock_atr',r'shock|\|dX\| > 3|range>3 ATR|capitulation',{'atr'},3),
 ('retest_tol_atr',r'within 0\.5|touch|retest|±0\.5|within 0.5 ATR',{'atr'},0.5),
 ('break_atr',r'break|beyond|close >1 AT|below the base|fell',{'atr'},None),
 ('flat_atr',r'flat|max-min >= 1|interior|net move|tight<',{'atr'},1),
 ('squeeze_release_atr',r'squeeze high|squeeze low',{'atr'},0.5),
 ('squeeze_width_pct',r'20th pct|squeeze',{'scalar','pct'},20),
 ('baseline_bars',r'own|prior|baseline|before W|percentile|median|values|mean|Listed|range\)|usual',{'bars','scalar'},250),
 ('long_history_bars',r'500',{'bars'},500),
 ('osc_zone_high',r'zone|MFI|RSI|percentile|>80|80/20|>=80',{'scalar'},80),
 ('osc_zone_low',r'zone|MFI|RSI|percentile|<20|80/20|<=20',{'scalar'},20),
 ('rsi_extreme_high',r'>70|RSI',{'scalar'},70),
 ('rsi_extreme_low',r'<30|RSI',{'scalar'},30),
 ('trend_t_stat',r'\|t\|>2',{'scalar'},2),
 ('ratio_band_1p5',r'1\.5/0\.67|>1\.5|<0\.67|ratio',{'scalar'},None),
 ('ratio_band_1p3',r'1\.3|0\.7\b|0\.77',{'scalar','mult'},None),
 ('ratio_band_1p25',r'1\.25|0\.8\b|1\.2x',{'scalar','mult'},None),
 ('vol_spike_mult',r'RVOL>3|>3x|3x 50',{'scalar','mult'},3),
 ('age_recent_bars',r'<5,5-20|age<=5|<=5,6-20|<5 ,5-20',{'scalar','bars'},5),
 ('age_old_bars',r'<5,5-20|5-20,>20|6-20,>20|>20',{'scalar','bars'},20),
 ('majority_share_pct',r'>60% rule|mostly',{'pct'},60),
 ('count_many',r'\{0,1,2\+\}|2\+|fails_0,1,2\+|2 or more',{'scalar'},2),
 ('pivot_k_divisor',r'N//10',{'scalar'},10),
 ('pivot_k_min',r'k=max\(2',{'scalar'},2),
 ('stage_slope_atr',r'unit/bar|slope\(M',{'atr','scalar'},0.05),
 ('partial_low_share',r'< 0\.25|retraced share|recovered share',{'scalar'},0.25),
 ('partial_high_share',r'> 0\.75',{'scalar'},0.75),
 ('cluster_window_bars',r'within 5 bars',{'bars'},5),
]
GRID={}
kept=[];dropped=[];merged=collections.OrderedDict();concept_of={}
# derived integer bin edges: drop c where c-1 is another integer edge of the same answer set (e.g. {1-2,3-5,6+} -> drop 3,6)
def bin_edges(ctx):
  m=re.search(r'\{[^}]*\}',ctx); return m.group(0) if m else ''
for r in rows:
  c=loc(r);v=V(r);u=r['unit'];cid=r['cutoff_id']
  why=None
  for pat,val,w in DROP:
    if re.search(pat,c) and (val is None or abs(v-val)<1e-9): why=w;break
  if not why:
    b=bin_edges(r['context'])
    if b and v==int(v) and re.search(r'(?<![\d.])%d-%d(?![\d.])'%(v-1,v) ,b)==None and re.search(r'(?<![\d.])%d(?:,|-)'%(v-1),b) and re.search(r'%d-(?:\d|$)'%v+r'|,%d\+|%d\+'%(v,v),b) and re.search(r'(?:^|[{,])%d[-+]'%v,b):
      why='derived bin edge (= previous edge + 1)'
  if why: dropped.append(dict(cutoff_id=cid,where_used=r['where_used'],current_default=r['current_default'],reason=why));continue
  hit=None
  for k,pat,us,val in M:
    if u in us and (val is None or abs(v-val)<1e-9) and re.search(pat,c): hit=k;break
  if hit:
    key=hit if (hit.startswith('ratio_band') or dict((x[0],x[3]) for x in M)[hit] is not None) else f"{hit}_{r['current_default'].replace('.','p')}"
    m=merged.setdefault(key,dict(cutoff_id=key,scope=set(),where=[],unit=u,default=r['current_default'],grid=r['grid_values'],mirror=r['bull_bear_mirror'],ctx=r['context'],src=[]))
    # mirrored low side of a ratio band (e.g. 0.67 vs 1.5) -> folded into the same band; keep the >1 side as default
    if v>1 and float(m['default'])<1: m['default']=r['current_default'];m['grid']=r['grid_values']
    m['scope'].add(r['scope']);m['where']+=r['where_used'].split(';');m['src'].append(cid);concept_of[cid]=key
  else:
    kept.append(r);concept_of[cid]=cid
ADD={'osc_zone_high':'70|75|80|85|90','osc_zone_low':'10|15|20|25|30','rsi_extreme_high':'60|65|70|75|80','rsi_extreme_low':'20|25|30|35|40'}
for k in ADD:
  if k in merged: merged[k]['grid']=ADD[k]
out=[]
for k,m in merged.items():
  w=sorted(set(m['where']))
  note='applied as hi and 1/hi (mirror)' if k.startswith('ratio_band') else m['mirror']
  out.append(dict(cutoff_id='S_'+k,shared='yes',scope='|'.join(sorted(m['scope'])),where_used=';'.join(w),n_rows_using=len(w),unit=m['unit'],current_default=m['default'],grid_values=m['grid'],grid_size=len(m['grid'].split('|')),bull_bear_mirror=note,merged_from='|'.join(m['src']),context=m['ctx']))
for r in kept:
  out.append(dict(cutoff_id=r['cutoff_id'],shared='no',scope=r['scope'],where_used=r['where_used'],n_rows_using=len(r['where_used'].split(';')),unit=r['unit'],current_default=r['current_default'],grid_values=r['grid_values'],grid_size=r['grid_size'],bull_bear_mirror=r['bull_bear_mirror'],merged_from=r['cutoff_id'],context=r['context']))
with open('CUTOFF_GRID_v2.7.2.1.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]),lineterminator='\n');w.writeheader();w.writerows(out)
with open('CUTOFF_DROPPED_v2.7.2.1.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dropped[0]),lineterminator='\n');w.writeheader();w.writerows(dropped)
use=collections.defaultdict(list)
for c in out:
  for wu in c['where_used'].split(';'): use[wu].append(c)
q=list(csv.DictReader(open(TREE)));ota=full=tag=0;mx=0
with open('QUESTION_CUTOFFS_v2.7.2.1.csv','w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['question_id','default_tags','n_cutoffs','versions_one_at_a_time','versions_full_cross'])
  for r in q:
    if r['part']=='base': cs=use.get(f"dial:{r['L1_type']}|{r['L3_derivative']}|{r['L4_analysis']}",[])
    else: cs=use.get(f"history:{r['L4_analysis']}",[])+use.get('history_convention:ALL_HISTORY',[])
    cs=list({c['cutoff_id']:c for c in cs}.values())
    o=1+sum(int(c['grid_size'])-1 for c in cs);fc=math.prod(int(c['grid_size']) for c in cs)
    ota+=o;full+=fc;tag+=bool(cs);mx=max(mx,fc)
    w.writerow([r['question_id'],';'.join(f"{c['cutoff_id']}={c['current_default']}" for c in cs),len(cs),o,fc])
S=dict(v2_7_2_cutoffs=len(rows),dropped=len(dropped),merged_rows=sum(len(m['src']) for m in merged.values()),shared_cutoffs=len(merged),kept_unmerged=len(kept),n_cutoffs=len(out),
 drop_reasons=dict(collections.Counter(d['reason'] for d in dropped)),grid_size_hist=dict(sorted(collections.Counter(int(c['grid_size']) for c in out).items())),
 questions=len(q),questions_with_cutoffs=tag,total_one_at_a_time=ota,mult_one_at_a_time=round(ota/len(q),3),total_full_cross=full,max_versions_one_question_full_cross=mx,
 shared={c['cutoff_id']:(c['current_default'],c['grid_values'],c['n_rows_using']) for c in out if c['shared']=='yes'})
json.dump(S,open('cutoff_counts_v2.7.2.1.json','w'),indent=1);print(json.dumps(S,indent=1))
