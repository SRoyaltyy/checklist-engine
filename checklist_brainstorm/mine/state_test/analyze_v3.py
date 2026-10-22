import pandas as pd, numpy as np, pyarrow.parquet as pq
FEE=0.002
A=pd.concat([pd.read_parquet(f'states_{y}_v3.parquet') for y in range(2020,2025)])
A['ticker']=A.ticker.astype(str); A=A[A.tr_joined].copy()  # 2020-23 Financial has no TR file -> dropped for comparability
px=pq.read_table('/workspace/pricehist/universe_2020_survivors.parquet',columns=['ticker','date','open'],
   filters=[('date','>=',pd.Timestamp('2020-01-01')),('date','<',pd.Timestamp('2025-01-01'))]).to_pandas()
px['ticker']=px.ticker.astype(str); px['date']=px.date.dt.strftime('%Y-%m-%d')
dv=pd.read_parquet('/workspace/pricehist/dividends_2020.parquet'); dv['ticker']=dv.ticker.astype(str)
dv=dv[dv.ex_date<'2025-01-01']; dv['date']=dv.ex_date.dt.strftime('%Y-%m-%d'); dv=dv.groupby(['ticker','date']).amount.sum().rename('div').reset_index()
A=A.merge(px,on=['ticker','date'],how='left').merge(dv,on=['ticker','date'],how='left'); del px
A['div']=np.minimum(A['div'].fillna(0),0.2*A.open)
A=A.sort_values(['ticker','date']).reset_index(drop=True); A['year']=A.date.str[:4]
lq=A.lean.quantile([.2,.4,.6,.8]).values; A['L']=np.digitize(A.lean,lq)+1
g=A.groupby('ticker'); A['cumdiv']=g['div'].cumsum(); A['pos']=g.cumcount(); A['n']=g.pos.transform('size')
op=A.open.values; cd=A.cumdiv.values; pos=A.pos.values; nn=A.n.values; idx=np.arange(len(A))
def ret(i,e): return (op[e]+(cd[e]-cd[i+1]))/op[i+1]-1-FEE
for h,c in ((1,'r1'),(5,'fix5')):
    v=np.full(len(A),np.nan); m=pos+h+1<nn; ii=idx[m]; v[ii]=(op[ii+h+1]+cd[ii+h+1]-cd[ii+1])/op[ii+1]-1-FEE; A[c]=v
    A.loc[A[c].abs()>2,c]=np.nan
A['ex1']=A.r1-A.groupby('date').r1.transform('mean'); A['ex5']=A.fix5-A.groupby('date').fix5.transform('mean')
A['FQ']=A.groupby('year').fresh.transform(lambda s: pd.qcut(s.rank(method='first'),3,labels=['fresh_lo','fresh_mid','fresh_hi'])).astype(object).fillna('fresh_blank')
A['J']=np.where(A.jumpz.isna(),'jump_blank',np.where(A.jumpz>=1.5,'jump','no_jump'))
A['AST']=np.select([A.ast==0,A.ast<18],['ast0','ast_lo'],'ast_hi')
def cl(d,y):
    d=d.dropna(subset=[y]); n=len(d)
    if n<2: return np.nan,np.nan,d.date.nunique(),n
    m=d[y].mean(); e=(d[y]-m).groupby(d.date).sum(); return m,np.sqrt((e**2).sum())/n,d.date.nunique(),n
rows=[]
states={'ALL':lambda D:D.L>0,'L5':lambda D:D.L==5,'L5&ast0':lambda D:(D.L==5)&(D.AST=='ast0'),'L5&ast_hi':lambda D:(D.L==5)&(D.AST=='ast_hi'),'L1':lambda D:D.L==1,
 'L5&fresh_hi':lambda D:(D.L==5)&(D.FQ=='fresh_hi'),'L5&fresh_lo':lambda D:(D.L==5)&(D.FQ=='fresh_lo'),
 'L5&jump':lambda D:(D.L==5)&(D.J=='jump'),'L5&no_jump':lambda D:(D.L==5)&(D.J=='no_jump'),
 'L5&ast0&fresh_lo':lambda D:(D.L==5)&(D.AST=='ast0')&(D.FQ=='fresh_lo'),'L5&ast0&jump':lambda D:(D.L==5)&(D.AST=='ast0')&(D.J=='jump')}
for yr in ['2020-24']+sorted(A.year.unique()):
    D=A if yr=='2020-24' else A[A.year==yr]
    for nm,f in states.items():
        d=D[f(D)]; r={'period':yr,'state':nm,'fresh_src':'/'.join(sorted(d.fresh_src.unique()))}
        for y in ('ex1','ex5','fix5'):
            m,se,nd,n=cl(d,y); r.update({y:m,y+'_lo':m-1.96*se,y+'_hi':m+1.96*se})
        r['n_dates']=nd; r['n_obs']=n; r['hit5']=(d.fix5.dropna()>0).mean(); r['enough_dates']=nd>=30; rows.append(r)
R=pd.DataFrame(rows); R.to_csv('2020_24_state_table.csv',index=False,float_format='%.5f')
# paired ast0 - ast_hi within L5 (1d,5d), and exit test
P=[];E=[]
jump=(A.jumpz>=1.5).values; bear=(A.lean<0.5).values
def exitrule(flag,i):
    for k in range(1,11):
        if flag[i+k]: return ret(i,i+k+1),k
    return ret(i,i+11),10
for yr in ['2020-24']+sorted(A.year.unique()):
    D=A if yr=='2020-24' else A[A.year==yr]
    for y in ('ex1','ex5'):
        a=D[(D.L==5)&(D.AST=='ast0')].groupby('date')[y].mean(); b=D[(D.L==5)&(D.AST=='ast_hi')].groupby('date')[y].mean(); d=(a-b).dropna()
        m,se=d.mean(),d.std()/np.sqrt(len(d)); P.append(dict(period=yr,h=y,diff_ast0_minus_asthi=m,lo=m-1.96*se,hi=m+1.96*se,n_dates=len(d)))
    for nm,mk in (('L5&ast0',(D.L==5)&(D.AST=='ast0')),('L5_all',D.L==5)):
        ii=D.index[mk & (D.pos+12<D.n)].values
        if nm=='L5_all' and len(ii)>60000: ii=np.sort(np.random.default_rng(0).choice(ii,60000,replace=False))
        d=A.loc[ii,['date','fix5']].copy(); j=[exitrule(jump,i) for i in ii]; b=[exitrule(bear,i) for i in ii]
        d['jump_exit']=[x[0] for x in j]; d['bear_exit']=[x[0] for x in b]; d['jd']=[x[1] for x in j]
        for c in ('fix5','jump_exit','bear_exit'): d.loc[d[c].abs()>2,c]=np.nan
        d['jump_minus_fix5']=d.jump_exit-d.fix5; d['bear_minus_fix5']=d.bear_exit-d.fix5
        for y in ('fix5','jump_exit','bear_exit','jump_minus_fix5','bear_minus_fix5'):
            m,se,nd,n=cl(d,y); E.append(dict(period=yr,entry=nm,metric=y,mean=m,lo=m-1.96*se,hi=m+1.96*se,n_dates=nd,n_obs=n,median_jump_days=d.jd.median()))
pd.DataFrame(P).to_csv('2020_24_paired_ast.csv',index=False,float_format='%.5f'); pd.DataFrame(E).to_csv('2020_24_exit_test.csv',index=False,float_format='%.5f')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300)
print('lean cuts',lq)
print(R[['period','state','fresh_src','n_dates','n_obs','ex1','ex1_lo','ex1_hi','ex5','ex5_lo','ex5_hi','fix5','hit5']].round(4).to_string())
print(pd.DataFrame(P).round(4).to_string()); print(pd.DataFrame(E).round(4).to_string())
