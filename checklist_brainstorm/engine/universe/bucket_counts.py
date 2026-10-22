# Adds 7-bucket yes/ready/frac per stock-day from existing COUNTS2 group columns. No re-tagging. 2020-24 only.
import pandas as pd, numpy as np, glob, sys, os
CH=os.environ.get('BUCKET_CHUNKS','chunks')
def load_secadd(y):
    # Sector add-on (James sector-ETF rows). ALL first, SP500 fills ticker+date pairs not in ALL (no double count).
    fs=[f'{CH}/{y}__COUNTS2_SECADD_{n}.parquet' for n in ('ALL','SP500')]
    ds=[pd.read_parquet(f) for f in fs if os.path.exists(f)]
    if not ds: return None
    a=pd.concat(ds,ignore_index=True).drop_duplicates(['ticker','date'],keep='first')
    a=a[a.date.astype(str)<'2025-01-01']
    keep=['ticker','date']+[c for c in a.columns if c.startswith('stk|') and (c.endswith('|yes') or c.endswith('|ready'))]
    return a[keep]
def row_buckets(ids,C):
    # Per-row map lookup -> per-bucket yes/ready arrays. Ids not in map (pending owners, '|N' ids) are skipped and returned.
    MI=M.set_index('row_id')
    def mid(i):
        if i in MI.index: return i
        import re; b=re.sub(r'\|\d+$','',i); return b if b in MI.index else None
    mapped=[(k,mid(i)) for k,i in enumerate(ids)]; un=[ids[k] for k,m in mapped if m is None]; out={}
    for b in ['1','2','3','4','5','7']:
        if b=='7': J=[k for k,m in mapped if m and MI.at[m,'b7_squeeze_takeprofit']=='yes']
        else: J=[k for k,m in mapped if m and MI.at[m,'bucket']==b]
        out[b]=((C[:,J]==2).sum(1).astype('int16') if J else np.zeros(len(C),'int16'), (C[:,J]>0).sum(1).astype('int16') if J else np.zeros(len(C),'int16'))
    return out,un
def load_si(y,sector):
    f=f'{CH}/{y}__SI__{sector}.parquet'; fj=f[:-8]+'.json'
    if not (os.path.exists(f) and os.path.exists(fj)): return None
    import json; sys.path.insert(0,'.'); import engine_year as E
    ids=json.load(open(fj))['ids']; s=pd.read_parquet(f); s=s[s.date.astype(str)<'2025-01-01'].drop_duplicates(['ticker','date'])
    C=E.unpack(np.stack([np.frombuffer(x,np.uint8) for x in s.packed]),len(ids)); rb,un=row_buckets(ids,C)
    o=s[['ticker','date']].copy()
    for b,(Y,R) in rb.items(): o[f'sib|{b}|yes']=Y; o[f'sib|{b}|ready']=R
    o.attrs['unmapped']=len(un); return o
def add_si(d,si):
    if si is None: d['si_status']='NOT_READY_NO_FILE'; return d
    m=d[['ticker','date']].merge(si.assign(_hit=1),on=['ticker','date'],how='left')
    for c in si.columns:
        if c.startswith('sib|'): d[c]=m[c].fillna(0).values.astype('int16')
    d['si_status']=np.where(m['_hit'].notna().values,'JOINED','NOT_READY_NO_ROW'); print('  si join',int(m['_hit'].notna().sum()),'/',len(m),f"({m['_hit'].notna().mean():.1%})",flush=True); return d
def load_attn(y,sector):
    # Wide ATTN: ticker,date + theme-radar-attn|<id> codes 0=NR 1=NO 2=YES. Exact sector name (Financial_partN files exist).
    f=f'{CH}/{y}__ATTN__{sector}.parquet'
    if not os.path.exists(f): return None
    a=pd.read_parquet(f); a=a[a.date.astype(str)<'2025-01-01'].drop_duplicates(['ticker','date'])
    cols=[c for c in a.columns if c.startswith('theme-radar-attn|')]
    if not cols: return None
    ids=[c.split('|',1)[1] for c in cols]
    C=np.stack([a[c].fillna(0).astype('int8').values for c in cols],1)
    rb,un=row_buckets(ids,C)
    if un: print('  ATTN unmapped (skipped):',un,flush=True)
    o=a[['ticker','date']].copy()
    for b,(Y,R) in rb.items(): o[f'attnb|{b}|yes']=Y; o[f'attnb|{b}|ready']=R
    return o
def add_attn(d,at):
    if at is None: d['attn_status']='NOT_READY_NO_FILE'; return d
    m=d[['ticker','date']].merge(at.assign(_hit=1),on=['ticker','date'],how='left')
    for c in at.columns:
        if c.startswith('attnb|'): d[c]=m[c].fillna(0).values.astype('int16')
    d['attn_status']=np.where(m['_hit'].notna().values,'JOINED','NOT_READY_NO_ROW')
    print('  attn join',int(m['_hit'].notna().sum()),'/',len(m),f"({m['_hit'].notna().mean():.1%})",flush=True); return d
def load_mkt(y):
    # Market-wide rows (date only). One vote per market group per date: ready=1 if group answered, yes=1 if majority yes.
    f=f'{CH}/{y}__COUNTS2_MKT.parquet'; o=None
    m=pd.read_parquet(f) if os.path.exists(f) else pd.DataFrame(columns=['date'])
    m=m[m.date.astype(str)<'2025-01-01'].drop_duplicates('date')
    if len(m): o=m[['date']].copy()
    for c in (m.columns if len(m) else []):
        if c.startswith('mkt|') and c.endswith('|ready'):
            b=c[:-6]; r=m[c].fillna(0).values; yv=m.get(b+'|yes',pd.Series(0,index=m.index)).fillna(0).values
            o[b+'|ready']=(r>0).astype('int16'); o[b+'|yes']=((r>0)&(2*yv>r)).astype('int16')
    ff=f'{CH}/{y}__JA_FRED_MKT.parquet'; fj=ff[:-8]+'.json'
    if os.path.exists(ff) and os.path.exists(fj):
        import json; sys.path.insert(0,'.'); import engine_year as E
        ids=json.load(open(fj))['ids']; fr=pd.read_parquet(ff); fr=fr[fr.date.astype(str)<'2025-01-01'].drop_duplicates('date')
        C=E.unpack(np.stack([np.frombuffer(x,np.uint8) for x in fr.packed]),len(ids))
        rb,un=row_buckets(ids,C)
        if un: print('FRED unmapped (skipped, not guessed):',un,flush=True)
        F=fr[['date']].copy()
        for b,(Y,R) in rb.items(): F[f'fredb|{b}|yes']=Y; F[f'fredb|{b}|ready']=R
        o=F if o is None else o.merge(F,on='date',how='outer')
    return o
def add_mkt(d,mk):
    if mk is None: d['mkt_status']='NOT_READY_NO_FILE'; return d
    cols=[c for c in mk.columns if c!='date']
    m=d[['date']].merge(mk.assign(_hit=1),on='date',how='left')
    d=pd.concat([d,pd.DataFrame({c:m[c].fillna(0).values.astype('int16') for c in cols},index=d.index)],axis=1)
    d['mkt_status']=np.where(m['_hit'].notna().values,'JOINED','NOT_READY_NO_ROW'); return d
def add_secadd(d,sa):
    # Join on ticker+date; add yes/ready into same group columns. Missing file or missing pair => NOT_READY (ready stays 0, frac NaN), never zero-YES.
    if sa is None:
        d['secadd_status']='NOT_READY_NO_FILE'; return d
    cols=[c for c in sa.columns if c not in('ticker','date')]
    m=d[['ticker','date']].merge(sa.assign(_hit=1).rename(columns={c:'__sa__'+c for c in cols}),on=['ticker','date'],how='left')
    hit=m['_hit'].notna().values
    for c in cols:
        v=m['__sa__'+c].fillna(0).values
        d[c]=(d[c].fillna(0).values if c in d.columns else 0)+v
    d['secadd_status']=np.where(hit,'JOINED','NOT_READY_NO_ROW'); return d
M=pd.read_csv('six_bucket_map.csv',dtype=str).fillna('')
M['src']=M.source.replace({'new-bot-finra':'new-bot'})
M['mn']=M.existing_tag.replace({'asterisk':'context'})
M['ln']=M.lens.replace('', 'none')
G={}
for k,s in M.groupby(['src','ln','mn']):
    G[k]=(set(s.bucket), (s.b7_squeeze_takeprofit=='yes').all())
amb=[k for k,v in G.items() if len(v[0]-{'none','excluded'})>1]
print('ambiguous groups',amb)
log=[]
for y in sys.argv[1:]:
    assert int(y)<=2024
    mk=load_mkt(y); print(y,'mkt','MISSING -> NOT_READY' if mk is None else f'{len(mk)} dates',flush=True)
    sa=load_secadd(y); print(y,'secadd', 'MISSING -> NOT_READY' if sa is None else f'{len(sa)} rows',flush=True)
    for f in sorted(glob.glob(f'{CH}/{y}__COUNTS2_*__*.parquet')):
        if '__BUCKETS' in f or '__COUNTS2_SI__' in f: continue  # SI is read per-row from __SI__ into STK; skip group file to avoid double count
        d=pd.read_parquet(f)
        if '__COUNTS2_STK__' in f:
            import re; sec_raw=f.split('__COUNTS2_STK__')[1][:-8]; sec=re.sub(r'_part\d+$','',sec_raw)
            si=load_si(y,sec); at=load_attn(y,sec_raw)  # ATTN has Financial_partN files; SI has single Financial
            d=add_attn(add_si(add_mkt(add_secadd(d,sa),mk),si),at)
        out=d[['ticker','date']].copy()
        for sc in('secadd_status','mkt_status','si_status','attn_status'):
            if sc in d.columns: out[sc]=d[sc].values
        acc={b:[[],[]] for b in ['1','2','3','4','5','7']}; unk=0
        for c in d.columns:
            p=c.split('|')
            if p[0] not in('stk','mkt') or len(p)!=5 or p[4]!='yes': continue
            k=(p[1],p[2],p[3])
            if k not in G: unk+=1; continue
            bs,b7=G[k]; b=[x for x in bs if x not in('none','excluded')]
            r=c[:-3]+'ready'
            for x in b[:1]: acc[x][0].append(c); acc[x][1].append(r)
            if b7: acc['7'][0].append(c); acc['7'][1].append(r)
        for b,(ys,rs) in acc.items():
            Y=d[ys].fillna(0).sum(1).astype('int32') if ys else 0; R=d[rs].fillna(0).sum(1).astype('int32') if rs else 0
            out[f'b{b}_yes']=Y; out[f'b{b}_ready']=R
            out[f'b{b}_frac']=np.where(np.asarray(R)>0, np.asarray(Y)/np.maximum(np.asarray(R),1), np.nan).astype('float32')
        for b in acc:
          for pre in ('fredb','sib','attnb'):
            if f'{pre}|{b}|yes' in d.columns:
                out[f'b{b}_yes']=out[f'b{b}_yes']+d[f'{pre}|{b}|yes'].values; out[f'b{b}_ready']=out[f'b{b}_ready']+d[f'{pre}|{b}|ready'].values
                R=out[f'b{b}_ready'].values; out[f'b{b}_frac']=np.where(R>0,out[f'b{b}_yes'].values/np.maximum(R,1),np.nan).astype('float32')
        cx=[c for c in d.columns if c.startswith('ctx_opp|stk|')]
        out['b2_ctx_opp']=d[cx].fillna(0).sum(1).astype('int32') if cx else 0
        o=f.replace('__COUNTS2_','__BUCKETS7_'); out.to_parquet(o,index=False)
        log.append((o,len(out),unk)); print(o,len(out),'unmapped_groups',unk,flush=True)
