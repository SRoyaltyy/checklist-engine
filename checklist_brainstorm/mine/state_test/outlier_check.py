import sys; sys.path.insert(0,'/workspace/checklist_brainstorm/engine/universe')
import numpy as np, pandas as pd, glob, pyarrow.parquet as pq
from engine_year import unpack
TD='/workspace/checklist_brainstorm/engine/out/tags/'
J=pd.read_csv(TD+'james_tags.csv',dtype=str); print(J.lens.value_counts().to_string())
oi=J[J.lens.fillna('').str.contains('Outlier|Interaction')]
print('james Outlier/Interaction tag rows',len(oi), oi.groupby(['lens','meaning']).size().to_string())
C='/workspace/checklist_brainstorm/engine/universe/chunks/'
# 1) COUNTS2 columns all-zero?
res=[]
for f in sorted(glob.glob(C+'2024__COUNTS2_STK__*.parquet'))+[C+'2024__COUNTS2_MKT.parquet']:
    n=[c for c in pq.ParquetFile(f).schema.names if '|james|' in c and ('Outlier' in c or 'Interaction' in c) and c.endswith(('|yes','|ready'))]
    if n: d=pd.read_parquet(f,columns=n); res+= [(f.split('/')[-1],c,int(d[c].sum())) for c in n]
R=pd.DataFrame(res,columns=['file','col','sum']); print(R.groupby('col')['sum'].sum().to_string())
# 2) raw answers SMCI
z=np.load(C+'2024__Technology.npz'); tk=list(z['tickers']); ds=list(z['dates']); ids=list(z['ids'])
codes=unpack(z['packed'],len(ids)); i=tk.index('SMCI'); X=codes[i*len(ds):(i+1)*len(ds)]
base=[q.split('|')[0] for q in ids]; sel=[k for k,b in enumerate(base) if b in set(oi.row_id)]
print('Outlier/Interaction ids present in raw stock chunk:',len(sel),'of',len(set(oi.row_id)))
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',filters=[('ticker','=','SMCI')]).to_pandas()
px=px[(px.date>='2023-12-01')&(px.date<'2025-01-01')].sort_values('date'); px['ret']=px.close.pct_change(); px['date']=px.date.dt.strftime('%Y-%m-%d')
big=px[px.date>='2024-01-01'].reindex(px[px.date>='2024-01-01'].ret.abs().sort_values(ascending=False).index[:8])
dd=[d[:10] for d in ds]
for _,r in big.iterrows():
    # morning after the big move
    j=[k for k,d in enumerate(dd) if d>r.date][:1]
    if not j: continue
    row=X[j[0],sel]; print(r.date,f'{r.ret:+.1%}','next morning',dd[j[0]],'YES',int((row==2).sum()),'NO',int((row==1).sum()),'NR',int((row==0).sum()))
if sel: print('whole-year SMCI codes on these ids:',np.bincount(X[:,sel].ravel(),minlength=3))
sh=np.load(C+'2024__SHARED.npz'); sid=[q.split('|')[0] for q in sh['ids']]; print('in SHARED (mkt):',sum(b in set(oi.row_id) for b in sid))
