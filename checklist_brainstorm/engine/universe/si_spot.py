import json,glob,random,sys,numpy as np,pandas as pd
sys.path.insert(0,'.'); import nb_year as NB
SID='/workspace/checklist_brainstorm/data/short_interest/'
random.seed(11); y=2024; fs=sorted(glob.glob(f'chunks/{y}__SI__*.parquet'))
ids=json.load(open(fs[0].replace('.parquet','.json')))['ids']
S=pd.concat([pd.read_parquet(SID+f'finra_si_{k}.parquet') for k in (2022,2023,2024)]); S['t']=S.symbol.astype(str).str.replace(r'[./ ]','-',regex=True)
sess=NB.sessions_all().index
want=['nbx-SI-ABS-DTC-HI','PV-TFC-0921|1','PV-TFC-0941|1','nbx-SI-THR-DN20','OWN-TR-00817-C|1','nbx-SI-EXT-HI','nbx-SI-EXT-HI-BUT','POS-TR-F0121-C|20','OWN-TR-00793-C|1','PV-TFC-0922|1']
def val(t,D):
    x=S[(S.t==t)&(S.publication_date<D)].sort_values('settlement_date')
    if not len(x): return None
    r=x.iloc[-1]; return None if (D-r.settlement_date).days>45 else r
rows=[]
for k,rid in enumerate(want):
    f=random.choice(fs); df=pd.read_parquet(f); j=ids.index(rid)
    for tr in range(3000):
        r=df.iloc[random.randrange(len(df))]; c=int(NB.unpack(np.frombuffer(r.packed,np.uint8)[None],len(ids))[0][j])
        if c>0 and (c==2 or tr>300): break
    D=pd.Timestamp(r.date); v=val(r.ticker,D); exp=None
    if v is not None:
        si,ps,adv,dtc=float(v.current_short_qty),float(v.previous_short_qty),float(v.avg_daily_volume),float(v.days_to_cover)
        if rid=='nbx-SI-ABS-DTC-HI': exp=dtc>=7
        elif rid=='OWN-TR-00793-C|1': exp=dtc>=7
        elif rid=='PV-TFC-0921|1': exp=si/adv>=8
        elif rid=='PV-TFC-0922|1': exp=si/adv<=1
        elif rid=='PV-TFC-0941|1': exp=si/ps-1>=0.2
        elif rid=='nbx-SI-THR-DN20': exp=si/ps-1<=-0.2
        else:
            i=sess.get_loc(D); hist=[]
            for d in sess[i-252:i+1]:
                w=val(r.ticker,d); hist.append(np.nan if w is None else float(w.days_to_cover))
            h=np.array(hist); cur=h[-1]
            if rid=='OWN-TR-00817-C|1': exp=cur/h[-2]-1>=0.10
            elif rid=='POS-TR-F0121-C|20':
                w=h[-20:]; exp=(cur-w.min())/(w.max()-w.min())>=0.75
            else:
                p95=np.nanquantile(h[:-1],.95); p05=np.nanquantile(h[:-1],.05); main=cur>0 and cur>=p95
                exp=main if rid=='nbx-SI-EXT-HI' else (cur<=p05 and not main)
    rows.append(dict(ticker=r.ticker,date=r.date,row=rid,engine={0:'NR',1:'NO',2:'YES'}[c],raw=('NR' if exp is None else 'YES' if exp else 'NO'),dtc=None if v is None else float(v.days_to_cover),report_settle=None if v is None else str(v.settlement_date.date()),published=None if v is None else str(v.publication_date.date())))
o=pd.DataFrame(rows); o['match']=o.engine==o.raw; print(o.to_string()); print('MATCH',o.match.sum(),'/',len(o)); o.to_csv(f'chunks/{y}__SI_spotcheck.csv',index=False)
