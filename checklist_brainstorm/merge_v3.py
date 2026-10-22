import csv,re,collections,json
H=['owner_file?','id','data_type','variant','lens','timeframe','strict_definition','yes_means (bullish/bearish)','source','history_start','known_before_open?','added_by','notes']
def load(f):
    rows=list(csv.DictReader(open(f,newline='',encoding='utf-8-sig')))
    out=[]
    for x in rows:
        if 'yes_means' in x and 'yes_means (bullish/bearish)' not in x: x['yes_means (bullish/bearish)']=x.pop('yes_means')
        extra=[f'{k}={v}' for k,v in x.items() if k not in H and k and v]
        if extra: x['notes']=(x.get('notes','')+' | '+'; '.join(extra)).strip(' |')
        out.append(x)
    return out
log=collections.OrderedDict()
src={'Grok Bot':load('grok.csv'),'Theme Radar':load('theme.csv'),'Taskforce':load('taskforce.csv'),'Manager Bot':load('manager.csv')}
NB=load('newbot.csv'); log['New Bot v4 raw']=len(NB)
spyf=lambda x: x['variant']=='SPY futures pre-market change'
log['New Bot SPY/ES pre-open futures rows (James v4 covers)']=sum(map(spyf,NB))
dtc=lambda x: 'days-to-cover' in x['variant'].lower()
log['New Bot days-to-cover rows (dup of Taskforce short interest)']=sum(map(dtc,NB))
log['New Bot FINRA short-volume rows kept']=sum('FINRA' in x['variant'] for x in NB)
NB=[x for x in NB if not spyf(x) and not dtc(x)]
J=load('james.csv'); log['James v3 raw']=len(J)
# boilerplate
bp=lambda x: 'stock-specific' in x['strict_definition'] and 'override' in x['strict_definition']
log['James boilerplate twins']=sum(map(bp,J)); J=[x for x in J if not bp(x)]
# outliers
o=[x for x in J if x['data_type']=='Outlier']; nono=[x for x in J if x['data_type']!='Outlier']
o1=[x for x in o if re.search(r' (3x|top1)\b',x['variant'])]
log['James outlier rows not 3x/top1']=len(o)-len(o1)
yl=lambda x: x['variant'].startswith(('10y','2y')) and (x['lens']=='Outlier gap' or re.search(r'\b(high|low|gap)\b',x['strict_definition'],re.I))
o2=[x for x in o1 if not yl(x)]; log['James 10y/2y high/low/gap outlier rows']=len(o1)-len(o2)
log['James outlier rows kept']=len(o2)
J=nono+o2
# clash with Grok
def lc(l):
    l=l.lower().replace(' (but)','')
    for a,b in [('threshold','thr'),('timeframe','thr'),('extreme','ext'),('streak','streak'),('change','chg'),('cross','cross'),('divergence','div'),('rank','rank'),('position','pos')]:
        if a in l: return b
    return l
def tf(t):
    t=t.lower()
    if 'overnight' in t: return 'on'
    if 'prev bar' in t or t=='1d' or 'snapshot' in t and t.startswith('1'): return '1'
    if 'release day' in t or 'last print' in t: return 'r1'
    m=re.match(r'last (\d+) releases',t)
    if m: return 'r'+m.group(1)
    m=re.match(r'(\d+)d',t); return m.group(1) if m else t
FUT={'ZN':'10y','BTC':'BTC','CL':'CL','ES':'ES','GC':'GC','HG':'HG','NQ':'NQ','RTY':'RTY'}
ECO={'CPI MoM':'CPI','Core CPI':'core CPI','Nonfarm':'NFP','Jobless':'jobless claims','Retail':'retail sales'}
def gkey(x):
    t=x['data_type']; v=x['variant']; L=lc(x['lens'])
    if t=='overnight futures': c,i='fut',v
    elif t=='finviz groups':
        c='grp'; i='sector rank' if v.startswith('sector rank') else 'industry rank' if v.startswith('industry rank') else 'industry relvol' if 'relative volume' in v else v
    elif t=='economic surprise': c,i='eco',v
    else: return None
    return (c,i,L,'*' if L=='streak' else tf(x['timeframe']))
def jkey(x):
    t=x['data_type']; v=x['variant']; L=lc(x['lens'])
    if t=='Finviz Futures':
        m=re.search(r'\((\w+)\)',v); i=FUT.get(m.group(1)) if m else None; c='fut'
    elif t=='Finviz Groups':
        c='grp'; i='sector rank' if 'sector rank' in v else 'industry rank' if 'industry rank' in v else 'industry relvol' if 'industry relative volume' in v else None
    elif t=='Finviz Econ Calendar':
        c='eco'; i=next((b for a,b in ECO.items() if a in v and not (a=='CPI MoM' and 'Core' in v)),None)
    else: return None
    if not i: return None
    return (c,i,L,'*' if L=='streak' or tf(x['timeframe'])=='consecutive' else tf(x['timeframe']))
G={gkey(x) for x in src['Grok Bot']}-{None}
fin=lambda x: 'finviz' in x['source'].lower() and x['data_type']!='Outlier'
log['James Finviz Elite (non-outlier) rows']=sum(map(fin,J))
cl=[x for x in J if jkey(x) and (jkey(x) in G or (jkey(x)[0],jkey(x)[1],jkey(x)[2],'*') in G)]
cid={id(x) for x in cl}; log['James Finviz rows clashing with Grok']=len(cl)
src['James']=[x for x in J if id(x) not in cid]
src['New Bot']=NB
# merge dedupe
out=[];seen_k=set();seen_id=set();d=collections.Counter()
for o,rows in src.items():
    for x in rows:
        key=tuple(re.sub(r'\s+',' ',x.get(c,'').strip().lower()) for c in ['variant','lens','timeframe','strict_definition'])
        if key in seen_k: d[o+' dup content']+=1; continue
        if x['id'] in seen_id: d[o+' dup id']+=1; continue
        seen_k.add(key); seen_id.add(x['id']); x['owner_file?']=o
        out.append({h:x.get(h,'') for h in H})
w=csv.DictWriter(open('/workspace/checklist_brainstorm/merged_v3.csv','w',newline='',encoding='utf-8'),H); w.writeheader(); w.writerows(out)
log.update(d); log['per owner']=collections.Counter(x['owner_file?'] for x in out); log['raw']={k:len(v) for k,v in src.items()}; log['total']=len(out)
print(json.dumps(log,indent=1,default=dict))
