import csv,re,collections,sys
sys.path.insert(0,'.'); from check import norm_def, sim
rows=list(csv.DictReader(open('merged_v2.csv',encoding='utf-8')))
for r in rows:
    r['o']=r['owner_file?']; r['nd']=norm_def(r['strict_definition'] or ''); r['dir']=(r['yes_means (bullish/bearish)'] or '')[:7].lower()
    r['nn']=re.sub(r'[\d.]+','#',r['nd'])
b=collections.defaultdict(list)
for r in rows:
    toks=sorted(set(t for t in r['nd'].split() if len(t)>3 and not t.isdigit()))[:3]
    b[('t',tuple(toks),len(r['nd'])//20)].append(r)
    vk=' '.join(sorted(set(re.findall(r'[a-z0-9]+',(r['variant'] or '').lower()))))
    b[('v',vk)].append(r)
    b[('n',r['nn'])].append(r)
out=[];done=set()
for bk in b.values():
  for i in range(len(bk)):
    for j in range(i+1,len(bk)):
      x,y=bk[i],bk[j]
      if x['o']==y['o'] or not x['nd'] or (x['id'],y['id']) in done: continue
      done.add((x['id'],y['id']));done.add((y['id'],x['id']))
      if abs(len(x['nd'])-len(y['nd']))>0.25*len(x['nd']): continue
      s=sim(x['nd'],y['nd'])
      if s>=80:
        if x['o']>y['o']: x,y=y,x
        kind='exact' if x['nd']==y['nd'] else ('same_rule_diff_threshold' if x['nn']==y['nn'] else 'near')
        out.append(dict(owner_a=x['o'],id_a=x['id'],variant_a=x['variant'],owner_b=y['o'],id_b=y['id'],variant_b=y['variant'],similarity=round(s,1),kind=kind,same_direction=x['dir']==y['dir'],def_a=x['strict_definition'],def_b=y['strict_definition']))
out.sort(key=lambda d:(-d['similarity'],d['owner_a'],d['owner_b']))
w=csv.DictWriter(open('cross_owner_dups.csv','w',newline=''),fieldnames=list(out[0]));w.writeheader();w.writerows(out)
c=collections.Counter((d['owner_a'],d['owner_b'],d['kind']) for d in out)
for k,v in sorted(c.items()): print(k,v)
print(len(out))
rid=collections.defaultdict(set)
for d in out: rid[d['owner_a']].add(d['id_a']); rid[d['owner_b']].add(d['id_b'])
print({k:len(v) for k,v in rid.items()})
seen=set()
for d in out:
  k=(d['owner_a'],d['owner_b'])
  if k in seen: continue
  seen.add(k); print(k,d['similarity'],d['kind'],d['same_direction'],'|',d['id_a'],d['def_a'][:110],'||',d['id_b'],d['def_b'][:110])
