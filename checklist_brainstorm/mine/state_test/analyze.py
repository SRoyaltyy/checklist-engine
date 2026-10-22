import pandas as pd, numpy as np
A=pd.read_parquet('states_2024.parquet'); A=A.dropna(subset=['r1'])
qs=lambda c,q: A[c].quantile(q).values
lq=qs('lean',[.2,.4,.6,.8]); A['L']=np.digitize(A.lean,lq)+1
A['AST']=np.select([A.ast_stk==0,A.ast_stk<18],['ast0','ast_lo'],'ast_hi')
t=qs('qw',[1/3,2/3]); A['QW']=np.select([A.qw<t[0],A.qw<t[1]],['qw_lo','qw_mid'],'qw_hi')
t=qs('qw_div',[1/3,2/3]); A['QWD']=np.select([A.qw_div<t[0],A.qw_div<t[1]],['div_lo','div_mid'],'div_hi')
t=qs('lb',[1/3,2/3]); A['LB']=np.select([A.lb<t[0],A.lb<t[1]],['lb_lo','lb_mid'],'lb_hi')
for h in ('r1','r5'): A['x'+h[1]]=A[h]-A.groupby('date')[h].transform('mean')
def stat(d,y):
    d=d.dropna(subset=[y]); n=len(d); 
    if n==0: return np.nan,np.nan,0
    m=d[y].mean(); e=(d[y]-m).groupby(d.date).sum(); se=np.sqrt((e**2).sum())/n
    return m,se,d.date.nunique()
rows=[]
def add(name,mask):
    d=A[mask]; r={'state':name,'n_obs':len(d)}
    for y in ('r1','r5','x1','x5'):
        m,se,nd=stat(d,y); r[f'{y}_mean']=m; r[f'{y}_se']=se
    r['n_dates']=d.date.nunique(); r['hit1']=(d.r1>0).mean(); r['hit5']=(d.r5>0).mean()
    r['avg_abs5']=d.r5.abs().mean(); rows.append(r)
add('ALL',A.L>0)
for l in range(1,6): add(f'L{l}',A.L==l)
for k in ('AST','QW','QWD','LB'):
    for v in sorted(A[k].unique()): add(v,A[k]==v)
for l in (1,5):
  for k in ('AST','QW','QWD','LB'):
    for v in sorted(A[k].unique()): add(f'L{l}&{v}',(A.L==l)&(A[k]==v))
  for a in sorted(A.AST.unique()):
    for q in sorted(A.QW.unique()): add(f'L{l}&{a}&{q}',(A.L==l)&(A.AST==a)&(A.QW==q))
  for a in sorted(A.AST.unique()):
    for q in sorted(A.QWD.unique()): add(f'L{l}&{a}&{q}',(A.L==l)&(A.AST==a)&(A.QWD==q))
R=pd.DataFrame(rows)
for y in ('r1','r5','x1','x5'): R[f'{y}_lo95']=R[f'{y}_mean']-1.96*R[f'{y}_se']; R[f'{y}_hi95']=R[f'{y}_mean']+1.96*R[f'{y}_se']
R['enough_dates']=R.n_dates>=30
R.to_csv('2024_state_table.csv',index=False,float_format='%.5f')
# paired date diffs: within L5, qw_lo vs qw_hi, div_lo vs div_hi
def pdiff(m1,m2,y):
    a=A[m1].groupby('date')[y].mean(); b=A[m2].groupby('date')[y].mean(); d=(a-b).dropna()
    return d.mean(),d.std()/np.sqrt(len(d)),len(d)
P=[]
for l in (5,1):
  for lo,hi,k in (('qw_lo','qw_hi','QW'),('div_lo','div_hi','QWD'),('ast0','ast_hi','AST'),('lb_lo','lb_hi','LB')):
    for y in ('r1','r5'):
      m,se,n=pdiff((A.L==l)&(A[k]==lo),(A.L==l)&(A[k]==hi),y); P.append(dict(lean=f'L{l}',compare=f'{lo} minus {hi}',h=y,diff=m,se=se,n_dates=n,lo95=m-1.96*se,hi95=m+1.96*se))
P=pd.DataFrame(P); P.to_csv('2024_quietwarning_paired.csv',index=False,float_format='%.5f')
# rally length: L5 entries -> trading days until lean<0.5 or lb_hi
A=A.sort_values(['ticker','date']); A['bear']=(A.lean<0.5)|(A.LB=='lb_hi')
A['i']=A.groupby('ticker').cumcount()
nb=A[A.bear][['ticker','i']].rename(columns={'i':'bi'})
e=A[(A.L==5)&(~A.bear)][['ticker','i','QW','AST']]
e=pd.merge_asof(e.sort_values('i'),nb.sort_values('bi'),left_on='i',right_on='bi',by='ticker',direction='forward')
e['len']=e.bi-e.i
RL=e.groupby(['AST','QW']).len.agg(['median','mean','count']); RL.to_csv('2024_rally_length.csv')
# market-wide vs IWM
M=pd.read_parquet('/workspace/checklist_brainstorm/engine/universe/chunks/2024__COUNTS2_MKT.parquet')
ys=lambda m:M[[c for c in M.columns if f'|{m}|yes' in c]].sum(axis=1)
M['bull']=ys('bullish');M['qw']=ys('quiet_warning');M['lb']=ys('loud_bearish'); M['lean']=M.bull/(M.bull+M.qw+M.lb)
M['qw_div']=M[[c for c in M.columns if '|quiet_warning|yes' in c and 'iverg' in c.lower()]].sum(axis=1)
E=pd.read_parquet('/workspace/pricehist/etf_2015.parquet'); E=E[(E.ticker.astype(str)=='IWM')&(E.date>='2024-01-01')&(E.date<'2025-01-01')].sort_values('date')
o1=E.open.shift(-1); E['r1']=E.close.shift(-1)/o1-1-.002; E['r5']=E.close.shift(-5)/o1-1-.002; E['date']=E.date.dt.strftime('%Y-%m-%d')
M=M[['date','lean','qw','qw_div','lb']].merge(E[['date','r1','r5']],on='date').dropna()
M['Lm']=pd.qcut(M.lean,3,labels=['mkt_bear','mkt_mid','mkt_bull']); M['QWm']=pd.qcut(M.qw_div.rank(method='first'),2,labels=['mdiv_lo','mdiv_hi'])
MR=[]
for keys in (['Lm'],['QWm'],['Lm','QWm']):
  for k,d in M.groupby(keys,observed=True):
    r={'state':'&'.join(map(str,k if isinstance(k,tuple) else (k,))),'n_dates':len(d)}
    for y in ('r1','r5'): r[y+'_mean']=d[y].mean(); r[y+'_se']=d[y].std()/np.sqrt(len(d)); r[y+'_hit']=(d[y]>0).mean()
    MR.append(r)
r={'state':'IWM_all','n_dates':len(M)}
for y in ('r1','r5'): r[y+'_mean']=M[y].mean(); r[y+'_se']=M[y].std()/np.sqrt(len(M)); r[y+'_hit']=(M[y]>0).mean()
MR.append(r); pd.DataFrame(MR).to_csv('2024_market_states_iwm.csv',index=False,float_format='%.5f')
print('lean cuts',lq)
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(R[['state','n_dates','n_obs','r1_mean','x1_mean','x1_lo95','x1_hi95','r5_mean','x5_mean','x5_lo95','x5_hi95','hit5']].round(4).to_string())
print(P.round(4).to_string()); print(RL); print(pd.DataFrame(MR).round(4).to_string())
