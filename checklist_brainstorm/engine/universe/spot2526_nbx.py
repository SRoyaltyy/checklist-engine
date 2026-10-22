import sys
import json,glob,random,sys,numpy as np,pandas as pd
Y=sys.argv[1] if len(sys.argv)>1 else '2025'
sys.path.insert(0,'.'); import nb_year as NB
D='/workspace/checklist_brainstorm/data/'
random.seed(7); fs=sorted(glob.glob('chunks/'+Y+'__NBX__*.parquet'))
meta=json.load(open(fs[0].replace('.parquet','.json'))); ids=meta['ids']
H=pd.read_parquet(D+'halts_regsho/nasdaq_halts_2020_2026.parquet'); H['d']=pd.to_datetime(H.halt_date,format='%m/%d/%Y')
T=pd.read_parquet(D+'halts_regsho/nasdaq_regsho_threshold_2020_2026.parquet')
F=pd.concat([pd.read_parquet(D+f'finra_shvol/finra_shvol_{y}.parquet') for y in (int(Y)-2,int(Y)-1,int(Y))])
want=['nb4-PDS-NB-039-W0-EVT','nb4-PDS-NB-039-T20-CNT','nb4-BRW-NB-056-W0-EVT','nb4-BRW-NB-056-T20-CNT']+[i for i in ids if 'FINRA' in i]
cells=[]; df=pd.concat([pd.read_parquet(f) for f in random.sample(fs,4)])
# bias toward interesting: tickers with halts / regsho
hot=set(H[H.d.dt.year==int(Y)].symbol)&set(df.ticker); hotT=set(T[T.date.dt.year==int(Y)].symbol)&set(df.ticker)
for k,rid in enumerate(want[::4][:5] if True else want):
    pool=df[df.ticker.isin(hotT if 'NB-056' in rid else hot if 'NB-039' in rid else df.ticker)]
    for tr in range(500):
        r=pool.sample(1,random_state=k*1000+tr).iloc[0]; C=NB.unpack(np.frombuffer(r.packed,np.uint8)[None],len(ids))[0]
        if C[ids.index(rid)]>0 and (tr>200 or C[ids.index(rid)]==2 or k%2): break
    cells.append((r.ticker,r.date,rid,int(C[ids.index(rid)])))
cur=pd.read_csv(NB.SECT,usecols=['Ticker','Exchange']).set_index('Ticker').Exchange
ok=0
for t,d,rid,code in cells:
    px=pd.read_parquet(NB.PX,columns=['ticker','date','close'],filters=[('ticker','==',t)]).sort_values('date')
    px=px[px.date<pd.Timestamp(d)]; bars=list(px.date); b=bars[-1]; prev20=bars[-20:]
    sym=t.replace('-','.')
    if 'NB-039' in rid:
        hd=set(H[H.symbol.isin([t,sym])].d)
        exp = (b in hd) if 'W0' in rid else (sum(x in hd for x in prev20)>=2)
    elif 'NB-056' in rid:
        td=set(T[T.symbol.isin([t,sym])].date)
        exp = None if cur.get(t)!='NASD' else ((b in td) if 'W0' in rid else (sum(x in td for x in prev20)>=2))
    else:
        f=F[F.symbol.isin([t,t.replace('-','/')])].sort_values('date'); f=f[f.date<=b]; sr=f.short_ratio.values.astype(float); x=sr[-1] if len(f) and f.date.iloc[-1]==b else np.nan
        n=rid.split('FS-')[1]
        if np.isnan(x): exp=None
        elif n=='ABS-HI': exp=x>=.6
        elif n=='ABS-LO': exp=x<=.3
        elif n[:3] in('Z20','Z60','OUT'):
            w=20 if n.startswith('Z20') else 60; h=sr[-w-1:-1]; z=(x-h.mean())/h.std(ddof=1)
            exp={'Z20-HI':z>=1,'Z20-LO':z<=-1,'Z60-HI':z>=1,'Z60-LO':z<=-1,'OUT2-HI':z>=2,'OUT2-LO':z<=-2,'OUT3-HI':z>=3,'OUT3-LO':z<=-3}[n]
        elif n.startswith('PCT'):
            h=sr[-253:-1]; p=(h<=x).mean(); exp={'PCT-HI':p>=.95,'PCT-LO':p<=.05,'PCT-UPPER':p>=.8}[n]
        elif n.startswith('DIV'):
            c=px.close.values; up=c[-1]>c[-6]; dn=c[-1]<c[-6]; r5=sr[-5:].mean()>sr[-10:-5].mean(); f5=sr[-5:].mean()<sr[-10:-5].mean()
            exp=(up and r5) if n=='DIV-UP' else (dn and f5)
        elif n=='THR-SVSPIKE': sv=f.short_volume.values.astype(float); exp=sv[-1]>=2*sv[-21:-1].mean()
        elif n=='THR-X50': exp=(sr[-2]<.5)&(x>=.5)
        elif n=='THR-EXEMPT': exp=f.short_exempt_volume.iloc[-1]/f.short_volume.iloc[-1]>=.05
    e=0 if exp is None else 2 if exp else 1; m=e==code; ok+=m
    print(f"{t:6} D={d} bar={b.date()} {rid.split('-',1)[1]:24} engine={code} hand={e} {'OK' if m else 'MISMATCH'}")
print(f"{ok}/{len(cells)} match")
