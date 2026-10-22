import pandas as pd, numpy as np, json, glob
C='/workspace/data/nb_v2/chunks/'
W=[p+s for p in ['nb4-PDS-NB-015-T1-EXT','nb4-PDS-NB-015-T1-CHG','nb4-PDS-NB-015-T3-STK','nb4-PDS-NB-015-P5-POSQ','nb4-PDS-NB-015-P5-POSD',
 'nb4-REL-NB-026-T1-THR','nb4-REL-NB-026-T1-RNK','nb4-HIS-NB-029-P5-POSQ','nb4-HIS-NB-029-P5-POSD','nb4-PDS-NB-036-T20-EXT','nb4-PDS-NB-036-T20-RXS'] for s in ['','-BUT']]
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
P=[]
for y in range(2020,2025):
  for f in sorted(glob.glob(C+f'{y}__NB__*.parquet')):
    fid=json.load(open(f[:-8]+'.json'))['ids']; ws=[w for w in W if w in fid]; ix=[fid.index(w) for w in ws]
    D=pd.read_parquet(f); D['date']=D.date.astype(str).str[:10]; assert D.date.max()<'2025-01-01'
    cc=unpack(np.stack([np.frombuffer(x,np.uint8) for x in D.packed]),len(fid))[:,ix]
    P.append(pd.concat([D[['ticker','date']].astype(str).reset_index(drop=True),pd.DataFrame(cc.astype('int8'),columns=ws)],axis=1))
X=pd.concat(P).drop_duplicates(['ticker','date']); X.to_parquet('nb.parquet'); print(X.shape, {w:(X[w]==2).mean().round(4) for w in W if w in X})
