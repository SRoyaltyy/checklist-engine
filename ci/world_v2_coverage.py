"""Measured item x timeframe coverage. Missing/empty outputs FAIL the gate.
No default-period alias may stand in for a separately named indicator setting.
"""
import argparse,csv,json,re
from collections import Counter
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from world_timeframes import TIMEFRAMES
ROOT=Path(__file__).resolve().parents[1]


def read_csv(file):
    with open(file,encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def measure(files):
    totals={};rows=0;date_min=None;date_max=None
    for file in files:
        for batch in pq.ParquetFile(file).iter_batches(batch_size=2048):
            table=pa.Table.from_batches([batch]);rows+=table.num_rows
            date=table['date']
            lo=pc.min(date).as_py();hi=pc.max(date).as_py()
            date_min=lo if date_min is None else min(date_min,lo)
            date_max=hi if date_max is None else max(date_max,hi)
            for name in table.column_names:
                if name in ('date','ticker'):continue
                values=table[name];valid=pc.is_valid(values)
                if pa.types.is_floating(values.type):valid=pc.and_(valid,pc.invert(pc.fill_null(pc.is_nan(values),True)))
                n=pc.sum(pc.cast(valid,pa.int64())).as_py() or 0
                rec=totals.setdefault(name,dict(non_null_rows=0,first_date=None,last_date=None))
                rec['non_null_rows']+=n
                if n:
                    observed=pc.filter(date,valid)
                    first=pc.min(observed).as_py();last=pc.max(observed).as_py()
                    rec['first_date']=first if rec['first_date'] is None else min(first,rec['first_date'])
                    rec['last_date']=last if rec['last_date'] is None else max(last,rec['last_date'])
    for rec in totals.values():
        rec['non_null_pct']=100*rec['non_null_rows']/rows if rows else 0
        rec['first_date']=str(rec['first_date'])[:10] if rec['first_date'] else ''
        rec['last_date']=str(rec['last_date'])[:10] if rec['last_date'] else ''
    return dict(rows=rows,date_min=str(date_min)[:10],date_max=str(date_max)[:10],columns=totals,files=[str(p) for p in files])


def mappings():
    existing={r['item_id']:r for r in read_csv(ROOT/'dictionary/world_coverage_map.csv')}
    # Exact, documented settings; generic function defaults do not satisfy SMA5.
    explicit={
      'I028':['STOCH14_3_3_k','STOCH14_3_3_d'],'I029':['WILLR14'],
      'I030':['MACD_macd','MACD_macdsignal','MACD_macdhist'],
      'I034':['ADX14','PLUS_DI14','MINUS_DI14'],'I036':['CCI20'],
      'I079':['volume'],'I080':['RVOL20'],'I082':['OBV'],'I083':['AD'],
      'I084':['MFI14'],'I097':['ATR14'],
      'I098':['BBANDS20_upper','BBANDS20_mid','BBANDS20_lower'],
      'I108':None,
    }
    for i,n in enumerate((5,10,20,30,50,100,200),1):explicit[f'I{i:03d}']=[f'SMA{n}']
    explicit['I008']=['EMA21'];explicit['I009']=['EMA20']
    for i,n in enumerate((6,12,14,24),24):explicit[f'I{i:03d}']=[f'RSI{n}']
    for i,n in enumerate((5,20,60),31):explicit[f'I{i:03d}']=[f'ROC{n}']
    return existing,explicit


def build(measured,root=ROOT):
    existing,explicit=mappings()
    observed=measured['columns'];daily=[c[:-4] for c in observed if c.endswith('__1d')]
    patterns=sorted(c for c in daily if c.startswith('CDL'))
    output=[];failures=[]
    sources=read_csv(root/'dictionary/DATA_SOURCES.csv')
    master=read_csv(root/'docs/TV_COVERAGE.csv')
    for namespace,items in (('dictionary',sources),('tradingview',master)):
        for item in items:
            iid=item.get('id') or item['item_id'];name=item.get('item','')
            mapping=existing.get(iid,{}) if namespace=='dictionary' else item
            status=mapping.get('status','PENDING');reason=mapping.get('note') or mapping.get('reason','')
            base=[x for x in mapping.get('snapshot_columns','').split('|') if x and x!='(definitional)']
            if namespace=='dictionary' and iid in explicit:
                base=patterns if iid=='I108' else explicit[iid]
                status='WIRED'
            # A name matching an actual column is evidence of that exact name,
            # never a substring match or a silently substituted default period.
            normalized=re.sub('[^A-Z0-9]','',name.upper())
            if namespace=='dictionary' and normalized in daily:
                base=[normalized];status='WIRED'
            incomplete={
                'I180':'market breadth bundle still lacks verified new-high/new-low and all required A/D outputs',
                'I187':'filing-date counts are not open-market insider P/S trades, shares and roles',
                'I192':'full numeric XBRL tag coverage and source availability are not yet established',
                'I193':'shares outstanding and float are distinct; full PIT float is not established',
                'I194':'Altman Z / Piotroski F / Beneish M not yet implemented and measured',
                'I197':'upgrade/downgrade counts do not cover the required price-target history',
                'I199':'filing mentions are not verified fund holdings and share quantities',
                'I200':'mention counts alone do not cover the required news tone',
                'I201':'complete market-wide options/term-structure bundle is not yet joined',
            }
            if namespace=='dictionary' and iid in incomplete:
                status='PENDING';reason=incomplete[iid]
            for tf in TIMEFRAMES:
                columns=[c+'__'+tf for c in base]
                missing=[c for c in columns if c not in observed]
                empty=[c for c in columns if observed.get(c,{}).get('non_null_rows',0)==0]
                valid=columns and not missing and not empty
                if status=='WIRED' and not valid:
                    status_out='PENDING'
                    why='required output missing or empty: '+','.join(missing or empty or ['no exact column mapping'])
                else:status_out=status;why=reason
                # Exemptions require concrete evidence, never a blank reason.
                if status_out not in ('WIRED','BLOCKED_SECRET','NOT_AVAILABLE_FREE','EXCLUDED_FREE_TEXT','EXCLUDED_LIVE_ONLY') or (status_out!='WIRED' and not why):
                    failures.append(namespace+':'+iid+'__'+tf)
                if status_out=='NOT_AVAILABLE_FREE' and not re.search(r'https?://|HTTP|tested|error',why,re.I):
                    failures.append(namespace+':'+iid+'__'+tf+':no tested-source evidence')
                pcts=[observed[c]['non_null_pct'] for c in columns if c in observed]
                first=[observed[c]['first_date'] for c in columns if c in observed and observed[c]['first_date']]
                output.append(dict(namespace=namespace,item_id=iid,item=name,timeframe=tf,block=item.get('block',''),
                    snapshot_columns='|'.join(columns),non_null_pct_2020_2026=min(pcts) if len(pcts)==len(columns) and columns else '',
                    first_date_available=max(first) if len(first)==len(columns) and columns else '',
                    status=status_out,reason=why,column_measurements=json.dumps({c:observed.get(c) for c in columns},sort_keys=True)))
    if measured['rows']==0:failures.append('zero snapshot rows')
    if measured['date_max']<'2026-01-01':failures.append('snapshot has no 2025-2026 coverage: end='+measured['date_max'])
    return output,sorted(set(failures))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--shards',nargs='+',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--gate',action='store_true');args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    measured=measure(args.shards);rows,failures=build(measured)
    (out/'WORLD_COLUMN_MEASUREMENTS.json').write_text(json.dumps(measured,indent=2))
    with open(out/'WORLD_COVERAGE.csv','w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(status='FAIL' if failures else 'PASS',rows=len(rows),snapshot_rows=measured['rows'],
        columns=len(measured['columns']),date_min=measured['date_min'],date_max=measured['date_max'],
        status_counts=dict(Counter(r['status'] for r in rows)),failures=failures)
    (out/'WORLD_COVERAGE_SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='failures'}),flush=True)
    if args.gate and failures:raise SystemExit(1)

if __name__=='__main__':main()
