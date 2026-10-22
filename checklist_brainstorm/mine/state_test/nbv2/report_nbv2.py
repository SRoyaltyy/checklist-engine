import numpy as np, pandas as pd
from scipy.stats import norm
Z=np.load('acc.npz',allow_pickle=True); S,N,SL,NL=Z['S'],Z['N'],Z['SL'],Z['NL']; dates=Z['dates']; ids=list(Z['ids']); yr=np.array([d[:4] for d in dates])
def cl(s,n):
    T=n.sum(); 
    if T<2: return np.nan,np.nan,np.nan,0,0
    m=s.sum()/T; e=s-m*n; se=np.sqrt((e**2).sum())/T; return m,m-1.96*se,m+1.96*se,int((n>0).sum()),int(T)
blm=Z['BL_S'].sum()/Z['BL_N'].sum()
rows=[]
for i,nm in enumerate(ids):
    m,lo,hi,nd,n=cl(S[i],N[i]); yes=Z['YES'][i].sum(); rdy=Z['RDY'][i].sum()
    r=dict(id=nm,src='NBX' if (nm.startswith('nbx') or '-039-' in nm or '-056-' in nm) else 'NB',is_but=nm.endswith('-BUT'),yes_rate=yes/rdy if rdy else np.nan,ready_obs=int(rdy),yes_obs=int(yes),
           ex5=m,lo95=lo,hi95=hi,n_dates=nd,n_obs=n,p=2*norm.sf(abs(m/((hi-lo)/3.92))) if nd>=2 and hi>lo else np.nan)
    for y in range(2020,2025):
        k=yr==str(y); r[f'ex5_{y}']=S[i][k].sum()/N[i][k].sum() if N[i][k].sum() else np.nan
    lm,llo,lhi,lnd,ln=cl(SL[i],NL[i]); r.update(L5yes_ex5=lm,L5yes_minus_L5all=lm-blm if ln else np.nan,L5_lo95=llo-blm if ln else np.nan,L5_hi95=lhi-blm if ln else np.nan,L5_n_dates=lnd,L5_n_obs=ln)
    rows.append(r)
D=pd.DataFrame(rows)
D['near_always_yes']=D.yes_rate>0.9
D['status']=np.where(D.ready_obs==0,'NOT_READY_all',np.where(D.n_dates<30,'too_few_dates(<30)','tested'))
T=D.status=='tested'; p=D.loc[T,'p'].values; o=np.argsort(p); mt=len(p)
thr=(np.arange(1,mt+1)/mt)*0.05; ok=p[o]<=thr; kmax=np.max(np.where(ok)[0])+1 if ok.any() else 0
bh=np.zeros(mt,bool); bh[o[:kmax]]=True; D['bh_survivor']=False; D.loc[T,'bh_survivor']=bh
D['clears_5pct']=T&(D.p<0.05)
D['signs_2020_24']=D[[f'ex5_{y}' for y in range(2020,2025)]].apply(lambda r:''.join('+' if v>0 else '-' if v<0 else '.' for v in r),axis=1)
D.sort_values('p').to_csv('../2020_24_nb_v2_score.csv',index=False,float_format='%.6f')
print('baseline L5 all ex5',blm,'ids',len(D)); print(D.status.value_counts()); print('tested',mt,'clear5%',D.clears_5pct.sum(),'chance',0.05*mt,'BH',kmax)
print('clear5 informative (not near-always)',(D.clears_5pct&~D.near_always_yes).sum(),'BH informative',(D.bh_survivor&~D.near_always_yes).sum())
pd.set_option('display.width',250); c=['id','yes_rate','ex5','lo95','hi95','n_dates','n_obs','p','signs_2020_24','near_always_yes','L5yes_minus_L5all','L5_lo95','L5_hi95','L5_n_dates']
print(D[D.bh_survivor].sort_values('p')[c].to_string())
