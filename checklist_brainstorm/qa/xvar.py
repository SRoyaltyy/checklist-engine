import csv,re,collections
from rapidfuzz import fuzz
rows=list(csv.DictReader(open('merged_v2.csv',encoding='utf-8')))
V=collections.defaultdict(lambda:{'n':0,'ids':[],'def':''})
syn={'average':'ma','moving':'','simple':'','exponential':'ema','sma':'ma','percent':'pct','%':'pct','relative':'rel','strength':'','index':'','ratio':'','the':'','of':'','vs':'','from':'','days':'d','day':'d'}
def nv(s):
    t=re.findall(r'[a-z0-9%]+',s.lower()); t=[syn.get(x,x) for x in t]; return ' '.join(sorted(x for x in t if x))
for r in rows:
    k=(r['owner_file?'],r['variant']); v=V[k]; v['n']+=1; v['ids'].append(r['id']); v['def']=v['def'] or r['strict_definition']; v['dt']=r['data_type']
keys=list(V); out=[]
for i in range(len(keys)):
  for j in range(i+1,len(keys)):
    a,b=keys[i],keys[j]
    if a[0]==b[0]: continue
    na,nb=nv(a[1]),nv(b[1])
    if not na or not nb: continue
    s=fuzz.token_set_ratio(na,nb) if min(len(na),len(nb))>6 else (100 if na==nb else 0)
    s2=fuzz.ratio(na,nb)
    if s2>=85 or (s>=95 and min(len(na.split()),len(nb.split()))>=2):
      if a[0]>b[0]: a,b=b,a
      out.append(dict(owner_a=a[0],variant_a=a[1],rows_a=V[a]['n'],ids_a=';'.join(V[a]['ids'][:5]),owner_b=b[0],variant_b=b[1],rows_b=V[b]['n'],ids_b=';'.join(V[b]['ids'][:5]),name_similarity=round(max(s,s2)),match='exact_name' if na==nb else 'near_name',def_a=V[a]['def'][:200],def_b=V[b]['def'][:200]))
out.sort(key=lambda d:(-d['name_similarity'],-(d['rows_a']+d['rows_b'])))
w=csv.DictWriter(open('cross_owner_dups.csv','w',newline=''),fieldnames=list(out[0]));w.writeheader();w.writerows(out)
c=collections.Counter((d['owner_a'],d['owner_b']) for d in out); ce=collections.Counter((d['owner_a'],d['owner_b']) for d in out if d['match']=='exact_name')
rw=collections.Counter()
for d in out: rw[(d['owner_a'],d['owner_b'])]+=min(d['rows_a'],d['rows_b'])
for k in sorted(c): print(k,c[k],ce[k],rw[k])
print(len(out))
for d in out[:40]: print(d['owner_a'],'|',d['variant_a'],d['rows_a'],'<>',d['owner_b'],'|',d['variant_b'],d['rows_b'],d['match'])
