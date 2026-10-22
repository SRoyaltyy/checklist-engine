import pandas as pd, numpy as np
A=pd.read_parquet('states_2024_v2.parquet'); FEE=0.002
A=A.sort_values(['ticker','date']).reset_index(drop=True)
lq=A.lean.quantile([.2,.4,.6,.8]).values; A['L']=np.digitize(A.lean,lq)+1
# per-ticker arrays for exits
A['cumdiv']=A.groupby('ticker')['div'].cumsum().fillna(0)
A['pos']=A.groupby('ticker').cumcount(); A['n']=A.groupby('ticker').pos.transform('size')
op=A.open.values; cd=A.cumdiv.values; dv=A['div'].fillna(0).values; pos=A.pos.values; nn=A.n.values
jump=(A.jumpz>=1.5).values; bear=(A.lean<0.5).values
def ret(i,e):  # entry open row i+1, exit open row e ; dividends with ex-date in (i+1, e]
    return (op[e]+(cd[e]-cd[i+1]))/op[i+1]-1-FEE
idx=np.arange(len(A)); ok=(pos+11<nn)  # need up to open of d+11
A['fix5']=np.nan; A.loc[pos+6<nn,'fix5']=[ret(i,i+6) for i in idx[pos+6<nn]]
def exitrule(flag,i):
    for k in range(1,11):         # signal mornings d+1..d+10 (entry open d+1 happens same morning; signal seen pre-open → exit next open)
        if flag[i+k]: return ret(i,i+k+1),k
    return ret(i,i+11),10
A['ex5']=A.fix5-A.groupby('date').fix5.transform('mean')
A['fqt']=pd.qcut(A.fresh.rank(method='first'),3,labels=['fresh_lo','fresh_mid','fresh_hi']).astype(object).fillna('blank')
A['fdt']=pd.qcut(A.fresh_div.rank(method='first'),3,labels=['fdiv_lo','fdiv_mid','fdiv_hi']).astype(object).fillna('blank')
A['J']=np.where(A.jumpz.isna(),'jump_blank',np.where(A.jumpz>=1.5,'jump','no_jump'))
def cl(d,y):
    d=d.dropna(subset=[y]); n=len(d)
    if n<2: return np.nan,np.nan,d.date.nunique(),n
    m=d[y].mean(); e=(d[y]-m).groupby(d.date).sum(); return m,np.sqrt((e**2).sum())/n,d.date.nunique(),n
rows=[]
def add(nm,mk):
    d=A[mk]; r={'state':nm}
    for y in ('fix5','ex5'):
        m,se,nd,n=cl(d,y); r.update({y+'_mean':m,y+'_lo95':m-1.96*se,y+'_hi95':m+1.96*se}); r['n_dates']=nd; r['n_obs']=n
    r['hit5']=(d.fix5.dropna()>0).mean(); rows.append(r)
add('ALL_nonfund',A.L>0); add('L5',A.L==5); add('L5&ast0',(A.L==5)&(A.ast==0))
for k in ('fqt','fdt','J'):
    for v in sorted(A[k].unique()):
        add(f'L5&{v}',(A.L==5)&(A[k]==v)); add(f'L5&ast0&{v}',(A.L==5)&(A.ast==0)&(A[k]==v))
R=pd.DataFrame(rows); R['enough_dates']=R.n_dates>=30; R.to_csv('2024_v2_fresh_jump_states.csv',index=False,float_format='%.5f')
# exit test
E=[]
for nm,mk in (('L5&ast0',(A.L==5)&(A.ast==0)),('L5_all',A.L==5)):
    ii=idx[mk.values&ok]; d=A.iloc[ii][['date','fix5']].copy()
    j=[exitrule(jump,i) for i in ii]; b=[exitrule(bear,i) for i in ii]
    d['jump_exit']=[x[0] for x in j]; d['jump_days']=[x[1] for x in j]; d['bear_exit']=[x[0] for x in b]; d['bear_days']=[x[1] for x in b]
    d['jump_minus_fix5']=d.jump_exit-d.fix5; d['bear_minus_fix5']=d.bear_exit-d.fix5
    for y in ('fix5','jump_exit','bear_exit','jump_minus_fix5','bear_minus_fix5'):
        m,se,nd,n=cl(d,y); E.append(dict(entry=nm,metric=y,mean=m,lo95=m-1.96*se,hi95=m+1.96*se,n_dates=nd,n_obs=n,hit=(d[y]>0).mean()))
    E.append(dict(entry=nm,metric='jump_days_median',mean=d.jump_days.median())); E.append(dict(entry=nm,metric='bear_days_median',mean=d.bear_days.median()))
    E.append(dict(entry=nm,metric='share_jump_before_cap',mean=(d.jump_days<10).mean()))
E=pd.DataFrame(E); E.to_csv('2024_v2_exit_test.csv',index=False,float_format='%.5f')
pd.set_option('display.width',250); print(R.round(4).to_string()); print(E.round(4).to_string()); print('lean cuts',lq, 'ast0 share L5',((A.L==5)&(A.ast==0)).sum())
