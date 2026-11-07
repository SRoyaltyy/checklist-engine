"""Read every public SEC retained raw/parquet asset on a separate GitHub runner."""
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import re
import tarfile

from ci import release_assets as releases
from ci.sec_bulk_readback_core import FIELDS,RawAudit,RowDigests,check,identities

ROOT=Path(__file__).resolve().parents[1]
IDENTITY_SHA='50323efcd9855061501d88010d8e812371fda7c9dd48d3a54c0f5f19cdad97ce'
KEYS_SHA='5e6d83f56bdb2a765ad5a9bf76219f82fdbe76ff2b93acd3f9ca12fa2e3233e2'
REQUEST=ROOT/'ci/SEC_BULK_READBACK_REQUEST.json'
FINAL='SEC_BULK_COVERAGE_V2.json'
SOURCE_URLS=dict(tickers='https://www.sec.gov/files/company_tickers.json',
    exchanges='https://www.sec.gov/files/company_tickers_exchange.json',
    submissions='https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip',
    companyfacts='https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip')


def sha(path):return releases._digest(path).removeprefix('sha256:')


def json_bytes(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def validate_request(value):
    check(set(value)=={'version','execute','source'},'readback request fields differ')
    check(value['version']==1 and type(value['execute']) is bool,'readback request version/boolean differs')
    source=value['source']
    if source is None:
        check(not value['execute'],'enabled readback requires frozen source');return value
    check(set(source)=={'run','attempt','commit','receipt_sha256'},'source bindings differ')
    for key in ('run','attempt'):check(bool(re.fullmatch(r'[1-9][0-9]*',str(source[key]))),'invalid source '+key)
    for key,n in (('commit',40),('receipt_sha256',64)):
        check(bool(re.fullmatch('[0-9a-f]{'+str(n)+'}',source[key])),'invalid source '+key)
    return value


def api(endpoint):return json.loads(releases._read('api',endpoint))


def schema(kind):
    import pyarrow as pa
    types={k:pa.string() for k in FIELDS[kind]}
    for k in ('cik','sic','source_row','source_sequence','fiscal_year'):
        if k in types:types[k]=pa.int64()
    for k in ('candidate_ciks','withheld_ciks'):
        if k in types:types[k]=pa.list_(pa.int64())
    for k in ('current_tickers','current_exchanges','conflict_fields'):
        if k in types:types[k]=pa.list_(pa.string())
    for k in ('historical_join_allowed','float64_exact'):
        if k in types:types[k]=pa.bool_()
    if kind=='facts':types['val_float64']=pa.float64()
    return pa.schema([(k,types[k]) for k in FIELDS[kind]])


class Bundle:
    def __init__(self,root,source):
        self.root=root;self.source=source;self.tag=f"nai-sec-bulk-v2-{source['run']}-{source['attempt']}"
        self.repo=os.environ['GITHUB_REPOSITORY'];self.checked=set()
        run=api(f"repos/{self.repo}/actions/runs/{source['run']}/attempts/{source['attempt']}")
        check(run['status']=='completed' and run['conclusion']=='success','source run is not successful')
        check(run['head_sha']==source['commit'] and run['path']=='.github/workflows/nai_sec_bulk.yml',
              'source run commit/workflow differs')
        self.release=releases.release_info(self.tag)
        check(not self.release['draft'] and self.release['target_commitish']==source['commit'],
              'source release is not public or targets another commit')
        assets=[];page=1
        while True:
            batch=api(f"repos/{self.repo}/releases/{self.release['id']}/assets?per_page=100&page={page}")
            assets.extend(batch)
            if len(batch)<100:break
            page+=1
        self.inventory={a['name']:a for a in assets}
        check(len(self.inventory)==len(assets),'duplicate public asset names')
        releases._DOWNLOAD_INVENTORIES[(self.repo,self.tag)]=self.inventory
        self.report=self.json(FINAL)
        check(sha(root/FINAL)==source['receipt_sha256'],'final receipt differs from frozen fingerprint')
        report=self.report
        check(report['actual_run_id']==str(source['run']) and report['actual_attempt']==str(source['attempt'])
            and report['source_commit']==source['commit'] and report['release']==self.tag,'receipt run anchors differ')
        check(report['status']=='PASS_BOTH_BULK_SOURCES_RETAINED_EXTRACTION' and not report['identity_only'],
              'source is not a complete two-archive result')
        check(report['scoring_gate']=='CLOSED' and report['world_gate']=='NOT_PROVEN'
            and not report['free_text_features'],'source gate semantics differ')
        check(report['identity_map_lf_sha256']==IDENTITY_SHA and report['join_keys_lf_sha256']==KEYS_SHA
            and report['retained_names']==8439,'source cohort anchors differ')
        check(report['filing_record_model']=='SOURCE_OBSERVATIONS_NOT_CANONICAL_ACCESSIONS'
            and report['historical_ownership']=='NOT_PROVEN_CURRENT_CANDIDATES_ONLY','source identity/observation model differs')
        self.bindings={b['name']:b for b in report['assets']}
        check(len(self.bindings)==len(report['assets']),'duplicate manifest bindings')
        check(set(self.inventory)==set(self.bindings)|{FINAL},'unbound or absent release assets')
        for name,binding in self.bindings.items():
            asset=self.inventory[name]
            check(asset['state']=='uploaded' and asset['size']==binding['bytes']
                and asset['digest']=='sha256:'+binding['sha256'],'public asset fingerprint differs: '+name)

    def get(self,name):
        path=releases.download_asset(self.tag,name,self.root)
        self.checked.add(name)
        print('SEC_READBACK_ASSET',name,path.stat().st_size,flush=True)
        return path

    def json(self,name):
        path=self.get(name);value=json.loads(path.read_bytes())
        if name!=FINAL:path.unlink()
        return value

    def identity_lineage(self,kind,name,source):
        lineage=source.get('reused_from')
        if lineage is None:return None
        check(lineage['asset']==name and lineage['receipt']==f'SEC_{kind.upper()}_SOURCE_V2.json'
            and lineage['sha256']==source['sha256'],'reused identity lineage fields differ')
        release=releases.release_info(lineage['release'])
        check(not release['draft'] and release['target_commitish']==lineage['source_commit'],
              'original identity release commit differs')
        directory=self.root/'identity-lineage'/kind
        raw=releases.download_asset(lineage['release'],name,directory)
        receipt=releases.download_asset(lineage['release'],lineage['receipt'],directory)
        check(sha(raw)==source['sha256'] and raw.stat().st_size==source['bytes']
            and sha(receipt)==lineage['receipt_sha256'],'original identity bytes/receipt differ')
        metadata=json.loads(receipt.read_bytes())
        check(metadata==dict(kind=kind,source={k:v for k,v in source.items() if k!='reused_from'},
            source_commit=lineage['source_commit']),'original identity acquisition metadata differs')
        raw.unlink();receipt.unlink()
        return dict(lineage,independently_downloaded=True)

    def parquet(self,kind):
        import pyarrow.parquet as pq
        prefixes=dict(identity='sec_identity_map_v2-',filings='sec_submissions_filings_retained-',
            entities='sec_submissions_entities_retained-',facts='sec_companyfacts_retained-')
        names=sorted(n for n in self.bindings if n.startswith(prefixes[kind]) and n.endswith('.parquet'))
        check(bool(names),'missing parquet dataset '+kind)
        for name in names:
            path=self.get(name);binding=self.bindings[name];ciks=set();count=0
            with pq.ParquetFile(path) as file:
                check(file.schema_arrow.equals(schema(kind)),'parquet schema differs: '+name)
                check(hashlib.sha256(str(file.schema_arrow).encode()).hexdigest()==binding['schema_sha256'],
                      'parquet schema fingerprint differs: '+name)
                for batch in file.iter_batches(batch_size=50000):
                    for row in batch.to_pylist():
                        count+=1
                        if row['cik'] is not None:ciks.add(row['cik'])
                        yield row
                check(count==file.metadata.num_rows==binding['rows'] and sorted(ciks)==binding['ciks'],
                      'parquet actual rows/CIKs differ: '+name)
            path.unlink()

    def raw(self,kind,audit,selected):
        names=sorted(n for n in self.bindings if n.startswith(f'sec_{kind}_raw-') and n.endswith('.tar.gz'))
        check(bool(names),'missing raw source '+kind)
        seen=set()
        for name in names:
            ledger=self.json(name.removesuffix('.tar.gz')+'.json')
            check(ledger['archive']==self.bindings[name] and ledger['source_kind']==kind,'raw ledger binding differs')
            members=ledger['members'];check(len(members)==self.bindings[name]['members'],'raw member count differs')
            path=self.get(name);count=0
            with tarfile.open(path,'r|gz') as archive:
                for member in archive:
                    check(count<len(members),'extra tar member')
                    entry=members[count];count+=1;cik=entry['cik'];zip_name=entry['zip_member']
                    check(cik in selected and cik!=1790169 and member.isfile(),'invalid raw member CIK/type')
                    zip_path=PurePosixPath(zip_name)
                    check(not zip_path.is_absolute() and '..' not in zip_path.parts and '\\' not in zip_name,'unsafe raw ZIP name')
                    check(bool(re.fullmatch(r'CIK'+str(cik).zfill(10)+r'(-submissions-\d+)?\.json',zip_path.name)),
                          'raw filename CIK differs')
                    if kind=='companyfacts':check('-submissions-' not in zip_path.name,'unexpected facts history member')
                    check(zip_path.name not in seen,'duplicate raw member basename');seen.add(zip_path.name)
                    expected=str(cik).zfill(10)+'/'+zip_path.name
                    check(member.name==entry['member']==expected and member.size==entry['bytes'],'raw member name/size differs')
                    raw=archive.extractfile(member).read()
                    check(hashlib.sha256(raw).hexdigest()==entry['sha256'],'raw member SHA differs')
                    audit.member(cik,zip_name,raw)
            check(count==len(members),'missing tar members');path.unlink()


def audit_bundle(bundle):
    archived=(ROOT/'docs/SEC_RETAINED_IDENTITY_MAP_V1.json').read_bytes().replace(b'\r\n',b'\n')
    keys=(ROOT/'dictionary/PRICE_WORLD_JOIN_KEYS_V1.csv').read_bytes().replace(b'\r\n',b'\n')
    check(hashlib.sha256(archived).hexdigest()==IDENTITY_SHA and hashlib.sha256(keys).hexdigest()==KEYS_SHA,
          'reader cohort metadata differs')
    archived=json.loads(archived)['records']
    price_tickers=[r['price_ticker'] for r in csv.DictReader(io.StringIO(keys.decode()))]
    check(len(archived)==len(price_tickers)==len(set(price_tickers))==8439
        and set(price_tickers)=={r['ticker'] for r in archived},'reader retained cohort differs')
    maps=[bundle.json('company_tickers.json'),bundle.json('company_tickers_exchange.json')]
    expected=identities(archived,*maps);actual=list(bundle.parquet('identity'))
    check(actual==expected,'full identity rows differ')
    selected={c for r in expected for c in r['candidate_ciks']}
    check(1790169 not in selected and bool(selected),'retrieval quarantine differs')
    coverage=dict(retained_names=8439,with_unique_cik=sum(r['cik'] is not None for r in expected),
        with_retrieval_candidates=sum(bool(r['candidate_ciks']) for r in expected),retrieval_ciks=len(selected),
        unique_cik_percent=round(100*sum(r['cik'] is not None for r in expected)/8439,2),
        archived_unique_baseline=sum(r['status']=='UNIQUE_CIK' for r in archived),
        new_current_only=sum(r['status']=='CURRENT_ONLY_CANDIDATE' for r in expected),
        historical_ownership_intervals=0,status_counts=dict(Counter(r['status'] for r in expected)))
    identity_coverage=bundle.json('SEC_IDENTITY_COVERAGE_V2.json')
    check(identity_coverage==coverage,'identity coverage receipt differs')
    results={}
    for kind in ('submissions','companyfacts'):
        audit=RawAudit(kind);bundle.raw(kind,audit,selected);stage=audit.finish(selected)
        check(stage==bundle.report['stages'][kind],'raw-derived full stage differs: '+kind)
        pairs=[('filings',audit.rows),('entities',audit.entities)] if kind=='submissions' else [('facts',audit.rows)]
        row_summaries={}
        for dataset,raw_rows in pairs:
            actual_rows=RowDigests(dataset)
            for row in bundle.parquet(dataset):
                check(row['cik'] in selected,'parquet CIK outside retrieval set');actual_rows.add(row)
            check(actual_rows.summary()==raw_rows.summary(),'full raw/parquet row values differ: '+dataset)
            row_summaries[dataset]=actual_rows.summary()
        populated=set(stage['populated_ciks'])
        coverage[kind+'_unique_ticker_matches']=sum(r['cik'] in populated for r in expected if r['cik'] is not None)
        coverage[kind+'_candidate_ticker_matches']=sum(bool(set(r['candidate_ciks'])&populated) for r in expected)
        extraction=bundle.json(f'SEC_{kind.upper()}_EXTRACTION_V2.json')
        check(extraction==dict(kind=kind,source=bundle.report['inputs'][kind],result=stage,
            source_commit=bundle.source['commit'],identity_map_lf_sha256=IDENTITY_SHA),'extraction receipt differs')
        results[kind]=dict(stage=stage,row_digests=row_summaries)
    check(coverage==bundle.report['coverage'],'full coverage differs')
    identity_lineage={}
    for kind in ('tickers','exchanges','submissions','companyfacts'):
        receipt=bundle.json(f'SEC_{kind.upper()}_SOURCE_V2.json')
        check(receipt==dict(kind=kind,source=bundle.report['inputs'][kind],source_commit=bundle.source['commit']),
              'input receipt differs: '+kind)
        check(receipt['source']['url']==SOURCE_URLS[kind] and receipt['source']['bytes']>0,
              'unexpected source URL/size')
        if kind in ('tickers','exchanges'):
            name='company_tickers.json' if kind=='tickers' else 'company_tickers_exchange.json'
            check(receipt['source']['sha256']==bundle.bindings[name]['sha256']
                and receipt['source']['bytes']==bundle.bindings[name]['bytes'],'raw identity source binding differs')
            identity_lineage[kind]=bundle.identity_lineage(kind,name,receipt['source'])
    check(bundle.checked==set(bundle.inventory),'not every public asset was read')
    return dict(coverage=coverage,stages=results,assets_checked=len(bundle.checked),identity_input_lineage=identity_lineage,
        verification_scope='ALL_PUBLISHED_RETAINED_RAW_MEMBERS_AND_ALL_PARQUET_ROW_VALUES',
        full_unfiltered_zip_readback=False,historical_ownership='NOT_PROVEN_CURRENT_CANDIDATES_ONLY',
        scoring_gate='CLOSED',world_gate='NOT_PROVEN')


def run(root):
    check(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='SRoyaltyy/checklist-engine',
          'public bulk audit runs only on the authorized GitHub runner')
    request=validate_request(json.loads(REQUEST.read_bytes()));check(request['execute'],'readback disabled')
    root.mkdir(parents=True,exist_ok=True)
    report=dict(format='SEC_BULK_PUBLIC_READBACK_V1',status='FAIL',source=request['source'],
        actual_run_id=os.environ['GITHUB_RUN_ID'],actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
        reader_commit=os.environ['GITHUB_SHA'],started_at=datetime.now(timezone.utc).isoformat())
    try:
        bundle=Bundle(root,request['source']);report.update(audit_bundle(bundle));report['status']='PASS'
    except Exception as exc:
        report['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        path=root/'SEC_BULK_PUBLIC_READBACK_V1.json';path.write_bytes(json_bytes(report))
        tag=f"sec-bulk-readback-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
        releases.gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],
            '--title',tag,'--notes',report['status']+' independent retained-source readback. Scoring CLOSED.')
        releases.publish_assets(tag,path)
        releases.gh_retry('release','edit',tag,'--draft=false')
        print('SEC_BULK_READBACK_FINAL',report['status'],tag,flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('sec-bulk-readback-output'))
    run(parser.parse_args().directory)
