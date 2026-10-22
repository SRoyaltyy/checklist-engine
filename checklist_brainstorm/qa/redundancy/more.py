import pandas as pd,numpy as np
from scipy.cluster.hierarchy import linkage,fcluster
from scipy.spatial.distance import squareform
R=pd.read_pickle('R.pkl'); Z=np.load('pairs.npz',allow_pickle=True); ids=list(Z['ids']); phi=Z['phi']; kap=Z['kappa']
live=np.where(~R.dead.values)[0]; P=phi[np.ix_(live,live)]; K=np.nan_to_num(kap[np.ix_(live,live)]); Rl=R.iloc[live].reset_index(drop=True)
def effn(S):
    w=np.linalg.eigvalsh((S+S.T)/2); w=np.clip(w,0,None); return w.sum()**2/(w**2).sum()
def ncl(S,t):
    D=1-np.clip(np.abs(S),0,1); np.fill_diagonal(D,0); D=(D+D.T)/2
    return len(set(fcluster(linkage(squareform(D,checks=False),'average'),1-t,'distance')))
print('effective N (eigen participation ratio) all',round(effn(P),1),'of',len(live))
for t in [0.8,0.7,0.5,0.3]: print('avg-linkage clusters |phi|>=',t,ncl(P,t),'  kappa>=',t,ncl(K,t))
nn=np.abs(P-np.eye(len(P))).max(1); print('nearest-neighbour |phi| quantiles',np.quantile(nn,[.1,.25,.5,.75,.9]).round(2))
out=[]
for r,g in Rl.groupby('root'):
    ix=g.index.values; S=P[np.ix_(ix,ix)]
    out.append(dict(root=r,sampled_live=len(ix),eff_n=round(effn(S),1),cl_phi70=ncl(S,0.7),cl_kappa80=ncl(K[np.ix_(ix,ix)],0.8),cl_phi50=ncl(S,0.5),cl_phi30=ncl(S,0.3)))
print(pd.DataFrame(out).to_string())
out=[]
for r,g in Rl.groupby('family'):
    ix=g.index.values
    if len(ix)<3: continue
    S=np.abs(P[np.ix_(ix,ix)]); m=S[np.triu_indices(len(ix),1)]
    out.append(dict(family=r,n=len(ix),mean_abs_phi=m.mean().round(3),share_pairs_gt50=(m>0.5).mean().round(3),eff_n=round(effn(P[np.ix_(ix,ix)]),1),cl50=ncl(P[np.ix_(ix,ix)],0.5)))
F=pd.DataFrame(out).sort_values('mean_abs_phi',ascending=False);print(F.to_string()); F.to_csv('family_overlap.csv',index=False)
# cross-owner pairs
iu=np.triu_indices(len(P),1); pr=pd.DataFrame({'a':Rl.id.values[iu[0]],'b':Rl.id.values[iu[1]],'phi':P[iu],'kappa':K[iu],'oa':Rl.merge_owner.values[iu[0]],'ob':Rl.merge_owner.values[iu[1]]})
pr['va']=Rl.variant.values[iu[0]];pr['vb']=Rl.variant.values[iu[1]];pr['la']=Rl.lens.values[iu[0]];pr['lb']=Rl.lens.values[iu[1]]
hp=pr[pr.phi.abs()>=0.5].sort_values('phi',key=abs,ascending=False); hp.to_csv('pairs_phi_ge_0.5.csv',index=False)
print(len(hp),(hp.phi.abs()>=0.7).sum());print(hp[hp.oa!=hp.ob].head(25).to_string())
print(hp.head(25).to_string())
