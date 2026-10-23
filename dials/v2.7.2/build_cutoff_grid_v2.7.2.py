# v2.7.2: extract EVERY hard-coded number from DIAL_TABLE_v2.7.1 dial rows + HISTORY_BUCKETS_v2.7.1 rules -> CUTOFF_GRID
import csv,re,json,math,collections,sys
SRC=sys.argv[1] if len(sys.argv)>1 else '/workspace/v271/out'
TREE=sys.argv[2] if len(sys.argv)>2 else '/workspace/v271/tree/QUESTION_TREE_v2.7.1.csv'
NUM=re.compile(r'(?<![A-Za-z_#\d.\[])([<>≤≥=±+\-]{0,2})(\$?)(\d+(?:\.\d+)?)(\s*)(%|σ|x(?![A-Za-z])|ATR|unit|-?bars?|-?bar\b|y\b|Δ)?')
SKIP_CTX=re.compile(r'case_chart\d*|taskforce\w*|merged #\d+|#\d+|[A-Za-z]+\d+(?:[/_.]\d+)+|\b(?:19|20)\d\d(?:-\d\d)?\b|\$1/5/10/50/100|127/161\.8|61\.8|\b\d+(?:\.\d+)?\s*(?:y|year)s?\b|1y|2y|3y')
# skipped by design: data publication lags (business days, leak rules), indicator periods (RSI6/12/24 etc = variants), calendar years in data notes, Fibonacci level identities, round-number level list, 1y/2y/3y horizons (facet identity)
OSC=re.compile(r'RSI|MFI|Stoch|W%R|Williams|zone|ADX|%B')
def unit_of(u,ctx):
  u=(u or '').strip('-')
  if u in('ATR','unit'): return 'atr'
  if u.startswith('bar'): return 'bars'
  if u=='%': return 'pct'
  if u=='σ': return 'sigma'
  if u=='x': return 'mult'
  if u=='y': return 'years'
  return 'scalar'
def grid(d,unit,ctx=''):
  if unit=='scalar' and 10<=d<=90 and OSC.search(ctx):
    return sorted({d-10,d-5,d,d+5,d+10})
  if unit in('bars','years') or (unit=='scalar' and d==int(d) and d>1):
    d=int(d)
    if d<=5: g=list(range(max(1,d-1),d+3))
    else: g=sorted({max(1,int(round(d*m))) for m in(0.5,0.75,1,1.5,2)})
  elif unit=='scalar' and 0<d<1:
    g=sorted({round(min(0.99,d*m),3) for m in(0.5,0.75,1,1.25,1.5)})
  elif unit=='scalar' and d in(0,1):
    return [d]   # structural 0/1 (sign, index) - not a tunable cutoff
  else:
    g=sorted({round(d*m,3) for m in(0.5,0.75,1,1.5,2)})
    if unit=='pct' and d<=100: g=sorted({min(100,x) for x in g})
  return g
occ=[]
def scan(scope,key,text):
  raw=text
  text=re.sub(r'[≤≈~]?\s*\d+\s*business days','',text)
  text=SKIP_CTX.sub(' ',text)
  seen=set()
  for m in NUM.finditer(text):
    sign,dol,v,sp,u=m.groups();d=float(v)
    if text[m.end(3):m.end(3)+1].isalpha() and not u: continue
    unit='dollar' if dol else unit_of(u,text)
    g=grid(d,unit,raw) if unit!='dollar' else sorted({round(d*k,2) for k in(0.5,1,2)})
    if len(g)<2: continue
    k=(d,unit)
    if k in seen: continue
    seen.add(k)
    a=max(0,m.start()-40);occ.append(dict(scope=scope,key=key,default=(int(d) if d==int(d) else d),unit=unit,grid=g,context=text[a:m.end()+20].replace('\n',' '),mirror=('-' in sign or '±' in sign or bool(re.search(r'mirror|bull|bear|up|down|high|low',text)))))
dial=list(csv.DictReader(open(f'{SRC}/DIAL_TABLE_v2.7.1.csv')))
for r in dial:
  scan('dial',f"{r['lever1_type']}|{r['variant']}|{r['facet']}",' ; '.join(r[c] for c in('definition','answer_set','formula','notes')))
hb=list(csv.DictReader(open(f'{SRC}/HISTORY_BUCKETS_v2.7.1.csv')))
byh=collections.defaultdict(list)
for r in hb: byh[r['history_value']].append(r['bucket']+': '+r['rule'])
for h,rs in byh.items(): scan('history',h,' ; '.join(rs))
CONV="W = last B bars; k = max(1,N//10); thirds = floor(N/3) bars; baseline 250 bars before W; ATR14 unit"
scan('history_convention','ALL_HISTORY',CONV)
# ids: group identical (key-type, unit, default) within a scope key
rows=[];cnt=collections.Counter()
for o in occ:
  base=o['key'].split('|')[-1]
  stem=f"{base}__{o['unit']}{str(o['default']).replace('.','p')}"
  cnt[stem]+=1
  rows.append(o|{'stem':stem})
# merge same stem across dial rows (same facet name + same number) -> one cutoff, many where_used
merged=collections.OrderedDict()
for o in rows:
  c=merged.setdefault(o['stem'],dict(o,where=[]))
  c['where'].append(f"{o['scope']}:{o['key']}")
out=[]
for i,(stem,c) in enumerate(merged.items(),1):
  cid=f"C{i:03d}_{stem}"
  out.append(dict(cutoff_id=cid,scope=c['scope'],where_used=';'.join(c['where']),unit=c['unit'],current_default=c['default'],grid_values='|'.join(str(int(x) if x==int(x) else x) for x in c['grid']),grid_size=len(c['grid']),bull_bear_mirror='yes (applied as ±value / mirror side)' if c['mirror'] else 'n/a (non-directional)',context=c['context']))
with open('CUTOFF_GRID_v2.7.2.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]),lineterminator='\n');w.writeheader();w.writerows(out)
# question tagging
use=collections.defaultdict(list)
for c in out:
  for wu in c['where_used'].split(';'):
    use[wu].append(c)
q=list(csv.DictReader(open(TREE)))
tot_q=len(q);ota=0;full=0;tagged=0;maxfull=0
with open('QUESTION_CUTOFFS_v2.7.2.csv','w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['question_id','default_tags','n_cutoffs','versions_one_at_a_time','versions_full_cross'])
  for r in q:
    if r['part']=='base': cs=use.get(f"dial:{r['L1_type']}|{r['L3_derivative']}|{r['L4_analysis']}",[])
    else: cs=use.get(f"history:{r['L4_analysis']}",[])+use.get('history_convention:ALL_HISTORY',[])
    o=1+sum(c['grid_size']-1 for c in cs);fc=math.prod(c['grid_size'] for c in cs)
    ota+=o;full+=fc;tagged+=bool(cs);maxfull=max(maxfull,fc)
    w.writerow([r['question_id'],';'.join(f"{c['cutoff_id']}={c['current_default']}" for c in cs),len(cs),o,fc])
gs=collections.Counter(c['grid_size'] for c in out)
S=dict(n_cutoffs=len(out),by_scope=dict(collections.Counter(c['scope'] for c in out)),by_unit=dict(collections.Counter(c['unit'] for c in out)),grid_size_hist=dict(sorted(gs.items())),sum_grid_values=sum(c['grid_size'] for c in out),
 questions=tot_q,questions_with_cutoffs=tagged,total_one_at_a_time=ota,mult_one_at_a_time=round(ota/tot_q,3),total_full_cross=full,mult_full_cross="10^%.2f"%math.log10(full/tot_q),max_versions_one_question_full_cross=maxfull,
 global_full_cross_all_cutoffs="10^%.1f"%sum(math.log10(c["grid_size"]) for c in out))
json.dump(S,open('cutoff_counts_v2.7.2.json','w'),indent=1);print(json.dumps(S,indent=1))
