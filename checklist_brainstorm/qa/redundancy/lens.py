import pandas as pd,numpy as np
R=pd.read_pickle('R.pkl');Z=np.load('pairs.npz',allow_pickle=True);P=Z['phi']
live=np.where(~R.dead.values)[0];P=np.abs(P[np.ix_(live,live)]);Rl=R.iloc[live].reset_index(drop=True)
t=Rl[Rl.merge_owner=='taskforce']; ix=t.index.values
L=t.lens.values; V=t.variant.values
iu=np.triu_indices(len(ix),1); a,b=ix[iu[0]],ix[iu[1]]; ph=P[a,b]
sl=L[iu[0]]==L[iu[1]]; sv=V[iu[0]]==V[iu[1]]
print('taskforce pairs: same lens/diff indicator mean|phi|',ph[sl&~sv].mean().round(3),'share>0.5',(ph[sl&~sv]>0.5).mean().round(3))
print('same indicator/diff lens',ph[sv&~sl].mean().round(3),(ph[sv&~sl]>0.5).mean().round(3))
print('diff both',ph[~sv&~sl].mean().round(3),(ph[~sv&~sl]>0.5).mean().round(3))
for l in sorted(set(L)):
    m=sl&~sv&(L[iu[0]]==l)
    if m.sum()>3: print(f'  lens {l:20s} pairs {m.sum():4d} mean|phi| {ph[m].mean():.2f} share>0.5 {(ph[m]>0.5).mean():.2f}')
def effn(S):
    w=np.clip(np.linalg.eigvalsh(S),0,None);return w.sum()**2/(w**2).sum()
S=Z['phi'][np.ix_(live,live)];rng=np.random.default_rng(0)
for k in [50,100,200,300,400,len(live)]:
    e=[effn(S[np.ix_(s,s)]) for s in [rng.choice(len(live),k,replace=False) for _ in range(5)]]
    print('subset',k,'effN',np.mean(e).round(1))
