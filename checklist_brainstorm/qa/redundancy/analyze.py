import pandas as pd,numpy as np,pickle
from scipy.cluster.hierarchy import linkage,fcluster
from scipy.sparse.csgraph import connected_components
from scipy.spatial.distance import squareform
SIG=pickle.load(open('signals.pkl','rb'))
d=pd.read_pickle('tagged.pkl').set_index('id',drop=False)
ids=list(SIG); A=np.column_stack([SIG[i].values.ravel() for i in ids])
M=(~np.isnan(A)).astype(np.float32); Y=np.nan_to_num(A).astype(np.float32)
rate=np.nansum(A,0)/M.sum(0)
dead=(rate==0)|(rate==1)|np.isnan(rate)
n=M.T@M; n11=Y.T@Y; na=Y.T@M; nb=M.T@Y
den=np.sqrt(na*(n-na)*nb*(n-nb)); phi=np.where(den>0,(n*n11-na*nb)/np.where(den>0,den,1),0)
union=na+nb-n11; jac=np.where(union>0,n11/np.where(union>0,union,1),0)
# mirror-overlap: A yes when B no (BUT twins that are opposites)
n10=na-n11; n01=nb-n11; n00=n-n11-n10-n01
agree=(n11+n00)/np.maximum(n,1)
# kappa = agreement beyond chance
pe=(na*nb+(n-na)*(n-nb))/np.maximum(n,1)**2; kappa=np.where(1-pe>0,(agree-pe)/(1-pe),0)
np.fill_diagonal(phi,1); np.fill_diagonal(jac,1); np.fill_diagonal(kappa,1)
live=np.where(~dead)[0]
def clus(S,thr,method='complete'):
    s=S[np.ix_(live,live)]; D=1-np.clip(np.abs(s),0,1); np.fill_diagonal(D,0); D=(D+D.T)/2
    Z=linkage(squareform(D,checks=False),method); lab=fcluster(Z,1-thr,'distance')
    cc=connected_components(np.abs(s)>=thr)[1]
    return lab,cc
labK,ccK=clus(kappa,0.8); labP,ccP=clus(phi,0.7); labJ,ccJ=clus(jac,0.8)
R=d.loc[ids,['id','merge_owner','root','data_type','lens','variant','strict_definition']].copy()
R['yes_rate']=rate; R['dead']=dead
for nm,lab,cc in [('kappa80',labK,ccK),('phi70',labP,ccP),('jacc80',labJ,ccJ)]:
    R[f'cl_{nm}']=-1; R.loc[np.array(ids)[live],f'cl_{nm}']=lab
    R[f'cc_{nm}']=-1; R.loc[np.array(ids)[live],f'cc_{nm}']=cc
# representative: highest mean kappa to its cluster mates, tie -> highest yes_rate closest to 0.1
R['rep_kappa80']=''
idpos={i:k for k,i in enumerate(ids)}
for c,g in R[~R.dead].groupby('cl_kappa80'):
    ix=[idpos[i] for i in g.id]; sc=kappa[np.ix_(ix,ix)].mean(1)
    R.loc[g.id,'rep_kappa80']=g.id.iloc[int(np.argmax(sc))]
R['family']=R.data_type
R.to_pickle('R.pkl'); np.savez_compressed('pairs.npz',ids=np.array(ids),phi=phi,kappa=kappa,jaccard=jac,agree=agree,n=n)
print('sampled',len(ids),'dead',dead.sum())
for nm in ['kappa80','phi70','jacc80']:
    print(nm,'complete-linkage clusters',R[~R.dead][f'cl_{nm}'].nunique(),'connected comps',R[~R.dead][f'cc_{nm}'].nunique())
print(R.groupby('merge_owner').size())
print(R[~R.dead].groupby('root').agg(rows=('id','size'),cl_k=('cl_kappa80','nunique'),cl_p=('cl_phi70','nunique'),cc_k=('cc_kappa80','nunique')))
