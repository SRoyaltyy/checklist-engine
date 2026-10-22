"""NB adapter v1: decode NB/NBX/NBW/SI packed chunks -> one 2020-24 tag table for the 682 New Bot map rows.
Rules: years 2020-2024 only (2025/26 files never globbed), survivors-only universe as in source chunks,
drop (ticker,date) pairs in drop_list_v2.csv, codes 0=NR 1=NO 2=YES (binary, PIT: answer for D uses data < D)."""
import pandas as pd, numpy as np, json, glob, sys, hashlib
sys.path.insert(0,'/workspace/data/nb_wire_v1'); from nb_wire_year import pack, unpack
M=pd.read_csv('map_coverage.csv',low_memory=False); M=M[M.row_id.str.startswith('nb')]
SRC=[('NBW','chunks/{y}__NBW__*.parquet'),('NBX','/workspace/data/nb_v2/chunks/{y}__NBX__*.parquet'),
     ('SI','/workspace/checklist_brainstorm/engine/universe/chunks/{y}__SI__*.parquet'),('NB','/workspace/data/nb_v2/chunks/{y}__NB__*.parquet')]
DROP=pd.read_csv('/workspace/state_test/bf_v2/drop_list_v2.csv',parse_dates=['date']); DROP['k']=1
want=set(M.row_id); owner={}
for tag,p in SRC:
    for i in json.load(open(sorted(glob.glob(p.format(y=2023).replace('.parquet','.json')))[0]))['ids']:
        if i in want and i not in owner: owner[i]=tag
IDS=sorted(owner); pos={i:k for k,i in enumerate(IDS)}
cov=[]
for y in [int(a) for a in sys.argv[1:]] or range(2020,2025):
    assert 2020<=y<=2024
    frames={}
    for tag,p in SRC:
        for f in sorted(glob.glob(p.format(y=y))):
            assert f'/{y}__' in f
            ids=json.load(open(f.replace('.parquet','.json')))['ids']; d=pd.read_parquet(f)
            C=unpack(np.frombuffer(b''.join(d.packed.values),np.uint8).reshape(len(d),-1),len(ids))
            cols=[(j,pos[i]) for j,i in enumerate(ids) if owner.get(i)==tag]
            key=list(zip(d.ticker,pd.to_datetime(d.date)))
            sub=np.zeros((len(d),len(IDS)),np.uint8); 
            for j,k in cols: sub[:,k]=C[:,j]
            frames.setdefault(tag,[]).append((pd.MultiIndex.from_tuples(key,names=['ticker','date']),sub))
    idx=None; out=None
    allk=pd.MultiIndex.from_tuples(sorted(set().union(*[set(ix) for fr in frames.values() for ix,_ in fr])),names=['ticker','date'])
    out=np.zeros((len(allk),len(IDS)),np.uint8)
    for fr in frames.values():
        for ix,sub in fr:
            r=allk.get_indexer(ix); out[r]=np.maximum(out[r],sub)
    df=allk.to_frame(index=False); keep=df.merge(DROP,how='left',on=['ticker','date']).k.isna().values
    df=df[keep].reset_index(drop=True); out=out[keep]
    P=pack(out); df['packed']=[r.tobytes() for r in P]; fn=f'tags/nb_tags_{y}.parquet'; df.to_parquet(fn,index=False)
    for k,i in enumerate(IDS): cov.append((y,i,owner[i],*(int((out[:,k]==v).sum()) for v in (0,1,2))))
    print(y,len(df),(~keep).sum(),flush=True)
    pd.DataFrame([c for c in cov if c[0]==y],columns=['year','row_id','src','nr','no','yes']).to_csv(f'tags/nb_tags_coverage_{y}.csv',index=False); del frames,out,df,allk
json.dump({'ids':IDS,'owner':owner,'codes':{'0':'NR','1':'NO','2':'YES'},'pack':'2-bit, 4 per byte along ids (nb_year.pack)','years':[2020,2024],
           'drop_list_v2_sha256':'5a6cb756b7b71c1658b89524a6c2349136ad6132c642a88d8e91be4566963239'},open('tags/nb_tags_ids.json','w'),indent=1)
