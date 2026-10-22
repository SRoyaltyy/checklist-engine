import json,glob,os,re,collections
import pyarrow.parquet as pq, pyarrow.compute as pc
C='chunks/';out=collections.defaultdict(dict)
def sec(f,pre):
    s=re.sub(r'\.(parquet|json)$','',os.path.basename(f).split(pre,1)[1]);return re.sub(r'_part\d+$','',s)
def pqt(files):
    t=set();r=0
    for f in files:
        x=pq.read_table(f,columns=['ticker']);r+=x.num_rows;t|=set(x.column(0).unique().to_pylist())
    return t,r
rows=[]
for y in range(2020,2027):
    secs=sorted({re.sub(r'_part\d+$','',os.path.basename(f)[6:-5]) for f in glob.glob(f'{C}{y}__*.json') if os.path.basename(f).count('__')==1})
    for s in secs:
        rec={'year':y,'sector':s}
        js=[json.load(open(f)) for f in glob.glob(f'{C}{y}__{s}.json')+glob.glob(f'{C}{y}__{s}_part*.json')]
        rec['STK']=(len(js),sum(j.get('tickers_with_bars_in_year',j.get('n_tickers',0)) for j in js),sum(j.get('n_cells',0) for j in js))
        tj=[json.load(open(f)) for f in glob.glob(f'{C}{y}__TR__{s}.json')+glob.glob(f'{C}{y}__TR__{s}_part*.json')]
        rec['TR']=(len(tj),sum(j.get('n_tickers',0) for j in tj),sum(j.get('n_rows',0) for j in tj))
        for k in ['COUNTS2_STK','COUNTS2_TR','FRESH']:
            fs=glob.glob(f'{C}{y}__{k}__{s}.parquet')+glob.glob(f'{C}{y}__{k}__{s}_part*.parquet')
            t,r=pqt(fs) if fs else (set(),0);rec[k]=(len(fs),len(t),r)
        rec['FRESH_MKT_ADDON']=os.path.exists(f'{C}{y}__FRESH_MKT_ADDON.parquet')
        rows.append(rec);print(rec,flush=True)
L=['# Coverage matrix (Grok Bot) - per year x sector','Cells: files / tickers / rows. STK tickers = tickers with bars in the year (from chunk json). FRESH_MKT_ADDON is market-wide (one file per year, all sectors).','','| year | sector | STK | TR | COUNTS2 (STK) | COUNTS2_TR | FRESH | FRESH_MKT_ADDON |','|---|---|---|---|---|---|---|---|']
f=lambda v:'MISSING' if v[0]==0 else f'{v[0]}f / {v[1]:,} tk / {v[2]:,} r'
for r in rows: L.append(f"| {r['year']} | {r['sector']} | {f(r['STK'])} | {f(r['TR'])} | {f(r['COUNTS2_STK'])} | {f(r['COUNTS2_TR'])} | {f(r['FRESH'])} | {'yes' if r['FRESH_MKT_ADDON'] else 'MISSING'} |")
open('coverage_matrix.md','w').write('\n'.join(L)+'\n')
