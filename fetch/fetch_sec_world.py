"""Acquire all structured SEC company facts and filing metadata with bounded checkpoints."""
import argparse,collections,gzip,hashlib,json,math,os,re,subprocess,tarfile
from pathlib import Path
import pandas as pd
from fetch.sec_client import get_json,SEC_HEADERS

FACT_COLUMNS=['cik','taxonomy','metric','unit','period_start','period_end','filed','accn','form','frame','val']

def numeric_facts(cik,payload):
    if int(payload.get('cik',-1))!=int(cik):raise ValueError('Companyfacts CIK identity mismatch')
    rows=[]
    for taxonomy,concepts in payload.get('facts',{}).items():
        for metric,concept in concepts.items():
            for unit,items in concept.get('units',{}).items():
                for item in items:
                    value=item.get('val')
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):continue
                    if not all(item.get(k) for k in ('filed','end','accn')):continue
                    rows.append(dict(cik=int(cik),taxonomy=taxonomy,metric=metric,unit=unit,period_start=item.get('start'),period_end=item['end'],filed=item['filed'],accn=item['accn'],form=item.get('form'),frame=item.get('frame'),val=float(value)))
    return pd.DataFrame(rows,columns=FACT_COLUMNS).drop_duplicates()

def identities(universe,historical,current):
    names=sorted(set(universe.ticker.astype(str)));lookup=collections.defaultdict(lambda:collections.defaultdict(set))
    for row in historical.dropna(subset=['cik']).itertuples():
        lookup[str(row.ticker).upper().replace('-','.')][int(row.cik)].add('frozen_sec_shares_filed')
    for row in current.values():
        lookup[str(row['ticker']).upper().replace('-','.')][int(row['cik_str'])].add('current_sec_ticker_map')
    records=[]
    for ticker in names:
        candidates=lookup[ticker.upper().replace('-','.')]
        records.append(dict(ticker=ticker,candidates=[dict(cik=cik,sources=sorted(sources)) for cik,sources in sorted(candidates.items())],status='UNIQUE_CIK' if len(candidates)==1 else 'AMBIGUOUS_CIK' if candidates else 'NO_CIK'))
    return records

def write_json_gz(file,payload):
    with gzip.open(file,'wt',encoding='utf8') as stream:json.dump(payload,stream,separators=(',',':'))

def publish_part(root,files,report,tag,shard,part):
    prefix=f'sec_world_shard_{shard:03d}_attempt_{os.environ.get("GITHUB_RUN_ATTEMPT","1")}_part_{part:03d}'
    archive=root.parent/(prefix+'.tar');manifest=root.parent/(prefix+'.json')
    members=[dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    with tarfile.open(archive,'w') as tar:
        for p in files:tar.add(p,arcname=p.name,recursive=False)
    payload=dict(source_commit=os.environ['GITHUB_SHA'],shard=shard,part=part,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),members=members,report=report,scope='Raw source checkpoint; no full-universe snapshot approval')
    manifest.write_text(json.dumps(payload,indent=2))
    subprocess.run(['gh','release','upload',tag,str(archive),str(manifest)],check=True)
    # The successful immutable upload is the checkpoint; retain only the next bounded batch locally.
    for p in files:
        if p.resolve().parent!=root.resolve():raise ValueError('Unsafe checkpoint path')
        p.unlink()
    archive.unlink();manifest.unlink()
    print('SEC_WORLD_CHECKPOINT_UPLOADED',prefix,len(members),flush=True)

def prepare(args):
    universe=pd.read_parquet(args.universe,columns=['ticker'])
    historical=pd.read_parquet(args.cik_map)
    if not {'ticker','cik'}<=set(historical):raise ValueError('Unrecognized frozen CIK map')
    try:
        current=get_json('https://www.sec.gov/files/company_tickers.json')
        current_map_status=dict(status='FETCHED')
    except Exception as exc:
        current={};current_map_status=dict(status='BLOCKED_OR_ERROR',evidence=getattr(exc,'evidence',dict(error_type=type(exc).__name__,message=str(exc))))
        print('SEC_CURRENT_IDENTITY_MAP_UNAVAILABLE',json.dumps(current_map_status),flush=True)
    records=identities(universe,historical,current)
    ciks=sorted({v['cik'] for r in records for v in r['candidates']})
    root=Path(args.out);root.mkdir(parents=True,exist_ok=True)
    (root/'SEC_WORLD_IDENTITIES.json').write_text(json.dumps(dict(current_map_status=current_map_status,records=records,ciks=ciks,universe_count=len(records),statuses=dict(collections.Counter(r['status'] for r in records)),source_commit=os.environ.get('GITHUB_SHA'),point_in_time_note='Identity evidence only; current mapping does not prove historical ticker validity'),indent=2))
    print('SEC_WORLD_IDENTITIES',len(records),len(ciks),dict(collections.Counter(r['status'] for r in records)),flush=True)

def collect(args):
    identity=json.loads(Path(args.identities).read_text());ciks=identity['ciks'][args.shard::args.shards]
    root=Path(args.out);root.mkdir(parents=True,exist_ok=True);files=[];part=0
    report=dict(requested=ciks,completed={},errors={},headers=SEC_HEADERS,source_commit=os.environ['GITHUB_SHA'])
    for i,cik in enumerate(ciks):
        prefix=f'CIK{cik:010d}';record=dict(cik=cik);company_files=[]
        try:
            url=f'https://data.sec.gov/api/xbrl/companyfacts/{prefix}.json'
            facts=get_json(url,allow_404=True)
            if facts is None:record.update(facts_status='NO_COMPANYFACTS_404',facts_url=url,fact_rows=0)
            else:
                numeric=numeric_facts(cik,facts)
                raw=root/(prefix+'.companyfacts.json.gz');write_json_gz(raw,facts);company_files.append(raw)
                target=root/(prefix+'.facts.parquet');numeric.to_parquet(target,index=False);company_files.append(target)
                record.update(facts_status='FETCHED',facts_url=url,fact_rows=len(numeric),metrics=int(numeric[['taxonomy','metric']].drop_duplicates().shape[0]),first_filed=str(numeric.filed.min()) if len(numeric) else None,last_filed=str(numeric.filed.max()) if len(numeric) else None)
            submissions=get_json(f'https://data.sec.gov/submissions/{prefix}.json',allow_404=True)
            if submissions is None:record.update(submissions_status='NO_SUBMISSIONS_404',submission_files=0)
            else:
                if int(submissions.get('cik',-1))!=cik:raise ValueError('Submission CIK identity mismatch')
                target=root/(prefix+'.submissions.json.gz');write_json_gz(target,submissions);company_files.append(target)
                count=1
                for descriptor in submissions.get('filings',{}).get('files',[]):
                    if descriptor.get('filingTo','')<'2018-01-01':continue
                    filename=descriptor.get('name','')
                    if not re.fullmatch(r'CIK\d+-submissions-\d+\.json',filename):raise ValueError('Invalid historical submissions filename')
                    older=get_json('https://data.sec.gov/submissions/'+filename)
                    target=root/(filename+'.gz');write_json_gz(target,older);company_files.append(target);count+=1
                record.update(submissions_status='FETCHED',submission_files=count)
            report['completed'][str(cik)]=record
            print('SEC_WORLD_COMPANY',json.dumps(record),flush=True)
        except Exception as exc:
            report['errors'][str(cik)]=getattr(exc,'evidence',dict(error_type=type(exc).__name__,message=str(exc)))
            print('SEC_WORLD_SOURCE_ERROR',cik,json.dumps(report['errors'][str(cik)]),flush=True)
        files.extend(company_files)
        (root/'SEC_WORLD_PROGRESS.json').write_text(json.dumps(report,indent=2))
        if (i+1)%args.checkpoint_every==0 or i==len(ciks)-1:
            if args.tag:publish_part(root,files,report,args.tag,args.shard,part)
            files=[];part+=1
    if not ciks or report['errors'] or len(report['completed'])!=len(ciks):raise SystemExit(1)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['prepare','collect'])
    ap.add_argument('--universe');ap.add_argument('--cik-map');ap.add_argument('--identities');ap.add_argument('--out',required=True)
    ap.add_argument('--shard',type=int,default=0);ap.add_argument('--shards',type=int,default=16);ap.add_argument('--tag',default='');ap.add_argument('--checkpoint-every',type=int,default=20)
    args=ap.parse_args()
    if args.operation=='prepare':prepare(args)
    else:collect(args)
if __name__=='__main__':main()
