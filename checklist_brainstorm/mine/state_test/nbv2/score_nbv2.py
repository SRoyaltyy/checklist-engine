import pandas as pd, numpy as np, json, glob, gc, sys
C='/workspace/data/nb_v2/chunks/'; LCUT=0.6205
def unpack(b,k): return np.stack([(b>>s)&3 for s in (0,2,4,6)],-1).reshape(b.shape[0],-1)[:,:k]
R=pd.read_parquet('ret_2020_24.parquet'); dates=np.array(sorted(R.date.unique())); di={d:i for i,d in enumerate(dates)}; ND=len(dates)
ids=[]; idx={}
def gid(i):
    if i not in idx: idx[i]=len(ids); ids.append(i)
    return idx[i]
K=800; S=np.zeros((K,ND)); N=np.zeros((K,ND)); SL=np.zeros((K,ND)); NL=np.zeros((K,ND))
YES=np.zeros((K,5)); RDY=np.zeros((K,5)); BL_S=np.zeros(ND); BL_N=np.zeros(ND)
for yi,y in enumerate(range(2020,2025)):
    Ry=R[R.date.str[:4]==str(y)]
    st=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean']); st['ticker']=st.ticker.astype(str); st['date']=st.date.astype(str).str[:10]
    Ry=Ry.merge(st.drop_duplicates(['ticker','date']),on=['ticker','date'],how='left'); del st
    Ry['L5']=Ry.lean>=LCUT; Ry['di']=Ry.date.map(di)
    b=Ry[Ry.L5]; np.add.at(BL_S,b.di.values,b.ex5.values); np.add.at(BL_N,b.di.values,1)
    nbx_ids=set()
    for kind in ['NBX','NB']:
        for f in sorted(glob.glob(C+f'{y}__{kind}__*.parquet')):
            meta=json.load(open(f[:-8]+'.json')); fid=meta['ids']
            if kind=='NBX': nbx_ids|=set(fid)
            use=[j for j,i in enumerate(fid) if not (kind=='NB' and i in nbx_ids)]; gi=np.array([gid(fid[j]) for j in use])
            D=pd.read_parquet(f); D['ticker']=D.ticker.astype(str); D['date']=D.date.astype(str).str[:10]
            assert D.date.max()<'2025-01-01'
            for a in range(0,len(D),40000):
                d=D.iloc[a:a+40000]; c=unpack(np.stack([np.frombuffer(x,np.uint8) for x in d.packed]),len(fid))[:,use]
                YES[gi,yi]+=(c==2).sum(0); RDY[gi,yi]+=(c>0).sum(0)
                m=d[['ticker','date']].reset_index(drop=True).merge(Ry[['ticker','date','ex5','di','L5']],on=['ticker','date'],how='left')
                ok=m.ex5.notna().values; c=c[ok]; ex=m.ex5.values[ok]; dd=m.di.values[ok].astype(int); l5=m.L5.values[ok].astype(bool)
                for col in range(c.shape[1]):
                    yv=c[:,col]==2
                    if not yv.any(): continue
                    np.add.at(S[gi[col]],dd[yv],ex[yv]); np.add.at(N[gi[col]],dd[yv],1)
                    yl=yv&l5
                    if yl.any(): np.add.at(SL[gi[col]],dd[yl],ex[yl]); np.add.at(NL[gi[col]],dd[yl],1)
            print(y,kind,f.split('__')[-1],len(D),flush=True); del D; gc.collect()
    del Ry; gc.collect()
k=len(ids); np.savez('acc.npz',S=S[:k],N=N[:k],SL=SL[:k],NL=NL[:k],YES=YES[:k],RDY=RDY[:k],BL_S=BL_S,BL_N=BL_N,dates=dates,ids=np.array(ids))
