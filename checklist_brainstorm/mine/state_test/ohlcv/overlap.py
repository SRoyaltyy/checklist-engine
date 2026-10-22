import pandas as pd, numpy as np
A=pd.read_parquet('feat.parquet',columns=['ticker','date','close','rv','rvol','r1','gap','mfi']); assert A.date.max()<'2025-01-01'
nb=pd.read_parquet('nb.parquet',columns=['ticker','date','nb4-REL-NB-026-T1-THR','nb4-HIS-NB-029-P5-POSQ'])
A=A.merge(nb,on=['ticker','date'],how='left').sort_values(['ticker','date']).reset_index(drop=True)
S=[]
for y in range(2020,2025):
    s=pd.read_parquet(f'../states_{y}_v5.parquet',columns=['ticker','date','lean','jumpz']); s['ticker']=s.ticker.astype(str); s['date']=s.date.astype(str).str[:10]; S.append(s)
S=pd.concat(S).drop_duplicates(['ticker','date']); A=A.merge(S,on=['ticker','date'],how='left')
cal={d:i for i,d in enumerate(sorted(A.date.unique()))}; A['si']=A.date.map(cal)
R={'VOLJUMP_RV10_60>2':A.rv>2,'RVOL>=5':A.rvol>=5,'UP10_DAY':A.r1>=.10,'NB026_T1THR':A['nb4-REL-NB-026-T1-THR']==2,
   'NB029_P5POSQ':A['nb4-HIS-NB-029-P5-POSQ']==2,'GAPDOWN<=-5%':A.gap<=-.05,'MFI>80':A.mfi>80,'WARNSPIKE_L5_QWz>=1.5':(A.lean>=0.6205)&(A.jumpz>=1.5)}
g=A.ticker; ok=A.close>=2
E={}
for k,m in R.items():
    m=m.fillna(False).astype(bool); st=m&~m.groupby(g).shift(1,fill_value=False)&ok
    E[k]=A.loc[st,['ticker','si']]
def near(a,b):
    keys=set(zip(b.ticker,b.si)); return np.mean([any((t,i+d) in keys for d in range(-2,3)) for t,i in zip(a.ticker,a.si)])
names=list(E); M=pd.DataFrame(index=names,columns=names,dtype=float)
for a in names:
    for b in names: M.loc[a,b]=np.nan if a==b else near(E[a],E[b])*100
M['n_event_starts']=[len(E[k]) for k in names]
M.round(1).to_csv('../prelock/ohlcv7_overlap_2020_24.csv'); print(M.round(1).to_markdown())
