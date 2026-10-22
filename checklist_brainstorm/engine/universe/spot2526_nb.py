import json,glob,random,sys,numpy as np,pandas as pd
sys.path.insert(0,'.'); import nb_year as NB
D='/workspace/checklist_brainstorm/data/'; Y=int(sys.argv[1])
H=pd.read_parquet(D+'halts_regsho/nasdaq_halts_2020_2026.parquet'); H['d']=pd.to_datetime(H.halt_date,format='%m/%d/%Y')
def cells(kind,rids,n,seed):
    fs=sorted(glob.glob(f'chunks/{Y}__{kind}__*.parquet')); ids=json.load(open(fs[0].replace('.parquet','.json')))['ids']
    df=pd.concat([pd.read_parquet(f) for f in random.Random(seed).sample(fs,3)]); out=[]; rng=np.random.default_rng(seed)
    for k in range(n):
        rid=rids[k%len(rids)]; want=[2,1,2,2,1][k%5]
        for t in range(3000):
            r=df.iloc[rng.integers(len(df))]; c=NB.unpack(np.frombuffer(r.packed,np.uint8)[None],len(ids))[0]
            if c[ids.index(rid)]==want or t==2999: break
        out.append((r.ticker,r.date,rid,int(c[ids.index(rid)]),int(c[ids.index(rid.replace('-BUT','') if rid.endswith('BUT') else rid+'-BUT')])))
    return out
def hand(t,d,rid):
    px=pd.read_parquet(NB.PX,columns=['ticker','date','close','low'],filters=[('ticker','==',t)]).sort_values('date').reset_index(drop=True)
    px=px[px.date<pd.Timestamp(d)].reset_index(drop=True); c=px.close.values; pc=np.r_[np.nan,c[:-1]]
    if 'NB-075' in rid: e=(c/pc-1)>=0.20
    elif 'NB-057' in rid: e=px.low.values<=0.9*pc
    else: hd=set(H[H.symbol.isin([t,t.replace('-','.')])].d); e=px.date.isin(hd).values
    ef=np.where(np.isnan(pc),np.nan,e.astype(float)); cnt=pd.Series(ef).rolling(20,min_periods=20).sum()
    q95=cnt.expanding(250).quantile(.95).iloc[-1]; q05=cnt.expanding(250).quantile(.05).iloc[-1]; x=cnt.iloc[-1]
    if np.isnan(q95): return 0,x,q95,q05
    main=(x>0)&(x>=q95)
    y=((x<=q05)&~main) if rid.endswith('BUT') else main
    return (2 if y else 1),x,q95,q05
C=cells('NB',['nb4-EVT-NB-075-T20-EXT','nb4-BRW-NB-057-T20-EXT-BUT'],5,1)
ok=0
for t,d,rid,code,mirror in C:
    h,x,q95,q05=hand(t,d,rid); m=h==code; ok+=m
    print(f"{t:6} {d} {rid.split('-',2)[2]:20} cnt20={x} p95={q95:.2f} p05={q05:.2f} engine={code} mirror={mirror} hand={h} {'OK' if m else 'MISMATCH'}{'  BOTH-YES!' if code==2 and mirror==2 else ''}")
print(f"{ok}/{len(C)} match")
