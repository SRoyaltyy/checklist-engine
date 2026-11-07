"""No-AI SEC bulk acquisition, immutable retained-cohort source snapshots on GHA."""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path,PurePosixPath
import shutil
import tarfile
import time
import zipfile

from ci import release_assets as releases
from ci.price_join_contract import IDENTITY_SHA
from ci.sec_bulk_retained_core import (decode_source,entity_row,companyfact_rows,
    live_candidates,members_by_cik,annotate_filing_observations,resolve_identities,submission_rows,QUARANTINED_CIKS)
from ci.sec_runner_access import relay_configuration
from scripts.nai import common

ROOT=Path(__file__).resolve().parents[1]
KEYS_SHA='5e6d83f56bdb2a765ad5a9bf76219f82fdbe76ff2b93acd3f9ca12fa2e3233e2'
REQUEST=ROOT/'ci/SEC_BULK_RETAINED_REQUEST.json'
URLS=dict(tickers='https://www.sec.gov/files/company_tickers.json',
    exchanges='https://www.sec.gov/files/company_tickers_exchange.json',
    submissions='https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip',
    companyfacts='https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip')
IDENTITY_INPUT_RELEASE='nai-sec-bulk-v2-42264090366-1'
IDENTITY_INPUT_COMMIT='f0c11a24066a0182f14a8f5883d1d9bed8d55d55'
IDENTITY_INPUT_PINS=dict(
    tickers=('76b4b2abb9f7dd0e9cff38e2f20336952bb41806057b2dd1033e244f3e1faec2',
             '006c98eee722d8c2722ca6084cd5aeec94e3e4f7acef41464ebeb7176e863de3'),
    exchanges=('224330f2c44f5d173395e427dbac3c6981acdb1f57e3658832d315c3e96f6522',
               '738374c24b0b5cb7cd12c3376e3460cb1767b452bc8b83ab808a1bb2e04af1b3'))


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def validate_request(value):
    expected=dict(version=2,scope='SEC_BULK_RETAINED_8439_SOURCE_ONLY',
                  retained_names=8439,identity_map_lf_sha256=IDENTITY_SHA,join_keys_lf_sha256=KEYS_SHA)
    controls={'execute','reuse_identity_inputs','not_before_utc'}
    if (type(value.get('execute')) is not bool or type(value.get('reuse_identity_inputs')) is not bool
            or {k:v for k,v in value.items() if k not in controls}!=expected
            or not controls<=set(value)):
        raise ValueError('SEC bulk request changes the bound retained cohort')
    if value['not_before_utc'] is not None:
        deadline=datetime.fromisoformat(value['not_before_utc'].replace('Z','+00:00'))
        if deadline.tzinfo is None or deadline.utcoffset().total_seconds()!=0:
            raise ValueError('SEC cooldown boundary must be UTC')
    return value


def wait_seconds(seconds):
    seconds=math.ceil(seconds)
    if seconds<0 or seconds>3605:
        raise ValueError('SEC cooldown exceeds the bounded one-hour wait')
    while seconds:
        step=min(60,seconds)
        print('SEC_PROVIDER_COOLDOWN',step,'remaining',seconds,flush=True)
        time.sleep(step);seconds-=step


def wait_before_requests(boundary):
    if boundary is None:return
    deadline=datetime.fromisoformat(boundary.replace('Z','+00:00'))
    wait_seconds(max(0,(deadline-datetime.now(timezone.utc)).total_seconds()))


def load_cohort():
    raw=(ROOT/'docs/SEC_RETAINED_IDENTITY_MAP_V1.json').read_bytes().replace(b'\r\n',b'\n')
    keys=(ROOT/'dictionary/PRICE_WORLD_JOIN_KEYS_V1.csv').read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(raw).hexdigest()!=IDENTITY_SHA or hashlib.sha256(keys).hexdigest()!=KEYS_SHA:
        raise ValueError('retained identity/join source differs')
    records=json.loads(raw)['records']
    tickers=[r['price_ticker'] for r in csv.DictReader(io.StringIO(keys.decode()))]
    if len(records)!=8439 or len(tickers)!=8439 or len(set(tickers))!=8439 or set(tickers)!={r['ticker'] for r in records}:
        raise ValueError('retained cohort membership differs')
    return records


def schemas():
    import pyarrow as pa
    strings=lambda names:[(n,pa.string()) for n in names]
    return dict(identity=pa.schema([('ticker',pa.string()),('cik',pa.int64()),('status',pa.string()),
        ('candidate_ciks',pa.list_(pa.int64())),('withheld_ciks',pa.list_(pa.int64())),
        *strings(['observed_first_filed','observed_last_filed','valid_from','valid_to_exclusive']),
        ('historical_join_allowed',pa.bool_())]),
        filings=pa.schema([('cik',pa.int64()),*strings(['accession_number','filing_date','report_date',
            'acceptance_datetime','form','primary_document','is_xbrl','is_inline_xbrl','source_member']),
            ('source_row',pa.int64()),('conflict_fields',pa.list_(pa.string()))]),
        entities=pa.schema([('cik',pa.int64()),('sic',pa.int64()),('current_tickers',pa.list_(pa.string())),
            ('current_exchanges',pa.list_(pa.string())),*strings(['state_of_incorporation','identity_scope'])]),
        facts=pa.schema([('cik',pa.int64()),*strings(['taxonomy','concept','unit','start','end','val_text']),
            ('val_float64',pa.float64()),('float64_exact',pa.bool_()),('accession_number',pa.string()),
            ('fiscal_year',pa.int64()),*strings(['fiscal_period','form','filed','frame']),('source_sequence',pa.int64())]))


class Publisher:
    def __init__(self,root,tag):
        self.root=root;self.tag=tag;self.assets=[]
        root.mkdir(parents=True,exist_ok=True)
        releases.gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],
            '--title',tag,'--notes','Versioned SEC retained-cohort source snapshot. Current identity candidates are not historical ownership. Scoring CLOSED.')

    def emit(self,path,kind,**metadata):
        binding=dict(name=path.name,bytes=path.stat().st_size,sha256=digest(path),kind=kind,**metadata)
        releases.publish_assets(self.tag,path)
        self.assets.append(binding)
        path.unlink()
        print('SEC_BULK_DURABLE',path.name,binding['bytes'],flush=True)
        return binding

    def json(self,name,value,kind):
        path=self.root/name;path.write_bytes(encoded(value))
        return self.emit(path,kind)


class ParquetSink:
    def __init__(self,publisher,name,schema,allowed,limit=500000):
        self.publisher=publisher;self.name=name;self.schema=schema;self.allowed=set(allowed)
        self.limit=limit;self.writer=None;self.part=0;self.rows=0;self.ciks=set();self.total=0

    def write(self,rows):
        import pyarrow as pa
        import pyarrow.parquet as pq
        if not rows:return
        if any(r.get('cik') is not None and r['cik'] not in self.allowed for r in rows):
            raise ValueError('output contains a CIK outside the retained retrieval set')
        table=pa.Table.from_pylist(rows,schema=self.schema)
        if self.writer is None:
            self.path=self.publisher.root/f'{self.name}-{self.part:05d}.parquet'
            self.writer=pq.ParquetWriter(self.path,self.schema,compression='zstd')
        self.writer.write_table(table)
        self.rows+=len(rows);self.total+=len(rows);self.ciks.update(r['cik'] for r in rows if r.get('cik') is not None)
        if self.rows>=self.limit:self.close()

    def close(self):
        import pyarrow.parquet as pq
        if self.writer is None:return
        self.writer.close();self.writer=None
        file=pq.ParquetFile(self.path)
        actual=set()
        for batch in file.iter_batches(columns=['cik'],batch_size=100000):
            actual.update(v for v in batch.column(0).to_pylist() if v is not None)
        if file.metadata.num_rows!=self.rows or actual!=self.ciks or not actual<=self.allowed:
            file.close()
            raise ValueError('actual parquet row count or CIK membership differs')
        schema_sha=hashlib.sha256(str(file.schema_arrow).encode()).hexdigest()
        file.close()
        self.publisher.emit(self.path,'parquet',rows=self.rows,ciks=sorted(actual),
            schema_sha256=schema_sha)
        self.part+=1;self.rows=0;self.ciks=set()

    def abort(self):
        if self.writer is not None:
            self.writer.close();self.writer=None
            self.path.unlink(missing_ok=True)


class RawSink:
    def __init__(self,publisher,kind,limit=256*1024*1024):
        self.publisher=publisher;self.kind=kind;self.limit=limit;self.part=0;self.archive=None
        self.members=[];self.size=0

    def add(self,cik,name,raw):
        if self.archive is None:
            self.path=self.publisher.root/f'sec_{self.kind}_raw-{self.part:05d}.tar.gz'
            self.archive=tarfile.open(self.path,'w:gz')
        member=str(cik).zfill(10)+'/'+PurePosixPath(name).name
        info=tarfile.TarInfo(member);info.size=len(raw);info.mtime=0
        self.archive.addfile(info,io.BytesIO(raw))
        self.members.append(dict(cik=cik,member=member,zip_member=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        self.size+=len(raw)
        if self.size>=self.limit:self.close()

    def close(self):
        if self.archive is None:return
        self.archive.close();self.archive=None
        binding=self.publisher.emit(self.path,'retained_raw_archive',members=len(self.members))
        self.publisher.json(f'sec_{self.kind}_raw-{self.part:05d}.json',
            dict(archive=binding,members=self.members,source_kind=self.kind),'raw_member_ledger')
        self.part+=1;self.members=[];self.size=0

    def abort(self):
        if self.archive is not None:
            self.archive.close();self.archive=None
            self.path.unlink(missing_ok=True)


def downloaded(kind,root,max_bytes):
    path=root/URLS[kind].rsplit('/',1)[1]
    started=now();limits=[]
    for attempt in range(2):
        try:
            common.get(URLS[kind],str(path),tries=3,timeout=1800,max_bytes=max_bytes)
            break
        except common.SourceError as exc:
            if exc.evidence.get('http_status')!=429:raise
            delay=max(601,exc.evidence.get('retry_after_seconds') or 0)
            limits.append(dict(observed_at=now(),wait_seconds=delay,evidence=exc.evidence.copy()))
            if attempt==1 or delay>3605:
                exc.evidence['rate_limit_history']=limits
                raise
            wait_seconds(delay)
    return path,dict(url=URLS[kind],bytes=path.stat().st_size,sha256=digest(path),started_at=started,
                     finished_at=now(),rate_limit_history=limits)


def reused_identity(kind,root):
    raw_sha,receipt_sha=IDENTITY_INPUT_PINS[kind]
    name=URLS[kind].rsplit('/',1)[1]
    receipt_name=f'SEC_{kind.upper()}_SOURCE_V2.json'
    cached=root/'reused-identity'
    source=releases.download_asset(IDENTITY_INPUT_RELEASE,name,cached)
    receipt=releases.download_asset(IDENTITY_INPUT_RELEASE,receipt_name,cached)
    if digest(source)!=raw_sha or digest(receipt)!=receipt_sha:
        raise ValueError('reused identity snapshot differs from authenticated source')
    metadata=json.loads(receipt.read_bytes())
    if (metadata['kind']!=kind or metadata['source_commit']!=IDENTITY_INPUT_COMMIT
            or metadata['source']['sha256']!=raw_sha or metadata['source']['url']!=URLS[kind]):
        raise ValueError('reused identity lineage differs')
    destination=root/name;shutil.copyfile(source,destination)
    return destination,dict(metadata['source'],reused_from=dict(release=IDENTITY_INPUT_RELEASE,
        asset=name,sha256=raw_sha,receipt=receipt_name,receipt_sha256=receipt_sha,source_commit=IDENTITY_INPUT_COMMIT))


def process_archive(kind,path,selected,publisher):
    sinks=schemas();raw_sink=RawSink(publisher,kind)
    first=ParquetSink(publisher,'sec_submissions_filings_retained' if kind=='submissions' else 'sec_companyfacts_retained',
        sinks['filings' if kind=='submissions' else 'facts'],selected)
    entities=ParquetSink(publisher,'sec_submissions_entities_retained',sinks['entities'],selected) if kind=='submissions' else None
    try:
        return extract_archive(kind,path,selected,raw_sink,first,entities)
    finally:
        first.abort()
        if entities:entities.abort()
        raw_sink.abort()


def extract_archive(kind,path,selected,raw_sink,first,entities):
    counters=dict(source_members=0,distinct_accessions=0,duplicate_accession_observations=0,
                  exact_duplicate_observations=0,accessions_with_conflicting_metadata=0,
                  source_fact_values=0,non_numeric_fact_values=0,
                  numeric_facts_without_filed_date=0,filings_without_filed_date=0,
                  filings_without_acceptance_timestamp=0)
    populated=set();filed_dates=[];conflict_examples=[]
    with zipfile.ZipFile(path) as archive:
        grouped=members_by_cik(archive.namelist(),selected,kind)
        if not grouped:raise ValueError('bulk archive has no retained CIK members')
        for cik,names in sorted(grouped.items()):
            filings={};before=first.total
            for name in names:
                raw=archive.read(name) # ZipFile verifies this retained member's CRC.
                raw_sink.add(cik,name,raw);counters['source_members']+=1
                payload=decode_source(raw)
                if kind=='submissions':
                    if 'filings' in payload:entities.write([entity_row(payload,cik)])
                    for index,row in enumerate(submission_rows(payload,cik),1):
                        filings.setdefault(row['accession_number'],[]).append(dict(row,source_member=name,source_row=index))
                else:
                    batch=[]
                    for row in companyfact_rows(payload,cik,counters):
                        batch.append(row)
                        if row['filed']:filed_dates.append(row['filed'])
                        if len(batch)>=100000:first.write(batch);batch=[]
                    first.write(batch)
                del payload,raw
            if kind=='submissions':
                rows,filing_counts,examples=annotate_filing_observations(filings)
                for key,value in filing_counts.items():counters[key]+=value
                conflict_examples.extend(examples[:max(0,20-len(conflict_examples))])
                counters['filings_without_filed_date']+=sum(r['filing_date'] is None for r in rows)
                counters['filings_without_acceptance_timestamp']+=sum(r['acceptance_datetime'] is None for r in rows)
                filed_dates.extend(r['filing_date'] for r in rows if r['filing_date'])
                for i in range(0,len(rows),100000):first.write(rows[i:i+100000])
            # At most two dates survive each CIK; never retain one date per fact.
            if filed_dates:filed_dates=[min(filed_dates),max(filed_dates)]
            if first.total>before:populated.add(cik)
            print('SEC_BULK_CIK',kind,cik,first.total,flush=True)
    first.close()
    if entities:entities.close()
    raw_sink.close()
    if first.total<1:raise ValueError('no populated structured rows in selected bulk members')
    return dict(status='PASS_RETAINED_SOURCE_EXTRACTION',rows=first.total,entity_rows=entities.total if entities else None,
        archive_ciks=len(grouped),populated_ciks=sorted(populated),missing_archive_ciks=sorted(set(selected)-set(grouped)),
        ciks_without_output_rows=sorted(set(grouped)-populated),
        filing_record_model='SOURCE_OBSERVATIONS_WITH_CONFLICT_FIELDS' if kind=='submissions' else None,
        conflict_examples=conflict_examples,
        first_filed_date=min(filed_dates) if filed_dates else None,
        last_filed_date=max(filed_dates) if filed_dates else None,**counters)


def run(root,identity_only=False):
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='SRoyaltyy/checklist-engine':
        raise ValueError('SEC source acquisition runs only on the authorized GitHub runner')
    request=validate_request(json.loads(REQUEST.read_bytes()))
    event=os.environ.get('GITHUB_EVENT_NAME','')
    if event=='push' and not request['execute']:
        raise ValueError('one-shot bulk acquisition is disabled')
    if not relay_configuration()['matches_inspected_production_worker']:
        raise ValueError('configured relay differs from the verified production Worker')
    wait_before_requests(request.get('not_before_utc'))
    records=load_cohort();root.mkdir(parents=True,exist_ok=True)
    tag=f"nai-sec-bulk-v2-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    publisher=Publisher(root,tag)
    report=dict(format='SEC_BULK_RETAINED_V2',status='INCOMPLETE',actual_run_id=os.environ['GITHUB_RUN_ID'],
        actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],source_commit=os.environ['GITHUB_SHA'],release=tag,
        identity_only=identity_only,retained_names=8439,identity_map_lf_sha256=IDENTITY_SHA,join_keys_lf_sha256=KEYS_SHA,
        started_at=now(),active_stage='identity',inputs={},stages={},scoring_gate='CLOSED',world_gate='NOT_PROVEN',
        historical_ownership='NOT_PROVEN_CURRENT_CANDIDATES_ONLY',free_text_features=False)
    report['filing_record_model']='SOURCE_OBSERVATIONS_NOT_CANONICAL_ACCESSIONS'
    report['request']=request
    report['identity_inputs_reused']=event=='push' and request.get('reuse_identity_inputs',False)
    try:
        maps={}
        for kind in ('tickers','exchanges'):
            path,receipt=(reused_identity(kind,root) if report['identity_inputs_reused'] else downloaded(kind,root,10000000))
            report['inputs'][kind]=receipt
            publisher.json(f'SEC_{kind.upper()}_SOURCE_V2.json',dict(kind=kind,source=receipt,
                source_commit=report['source_commit']),'source_input_receipt')
            maps[kind]=json.loads(path.read_bytes());publisher.emit(path,'official_current_identity_source')
        current=live_candidates(maps['tickers'],maps['exchanges'])
        rows=resolve_identities(records,current)
        selected=set(c for r in rows for c in r['candidate_ciks'])
        if not selected or selected&QUARANTINED_CIKS:
            raise ValueError('retrieval candidate set is empty or integrity-quarantined')
        identity=ParquetSink(publisher,'sec_identity_map_v2',schemas()['identity'],selected,limit=100000)
        identity.write(rows);identity.close()
        statuses={s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}
        report['coverage']=dict(retained_names=len(rows),with_unique_cik=sum(r['cik'] is not None for r in rows),
            with_retrieval_candidates=sum(bool(r['candidate_ciks']) for r in rows),retrieval_ciks=len(selected),
            unique_cik_percent=round(100*sum(r['cik'] is not None for r in rows)/len(rows),2),
            archived_unique_baseline=sum(r['status']=='UNIQUE_CIK' for r in records),
            new_current_only=sum(r['status']=='CURRENT_ONLY_CANDIDATE' for r in rows),
            historical_ownership_intervals=0,status_counts=statuses)
        publisher.json('SEC_IDENTITY_COVERAGE_V2.json',report['coverage'],'identity_coverage')
        releases.gh_retry('release','edit',tag,'--draft=false','--notes',
            'INCOMPLETE source snapshot: identity data published; wait for SEC_BULK_COVERAGE_V2.json for final status. Scoring CLOSED.')
        if not identity_only:
            for kind in ('submissions','companyfacts'):
                report['active_stage']=kind+'_download'
                free=shutil.disk_usage(root).free
                if free<5*1024**3:raise ValueError('insufficient runner disk for the next SEC bulk source')
                path,receipt=downloaded(kind,root,free-2*1024**3)
                report['inputs'][kind]=receipt
                publisher.json(f'SEC_{kind.upper()}_SOURCE_V2.json',dict(kind=kind,source=receipt,
                    source_commit=report['source_commit']),'source_input_receipt')
                report['active_stage']=kind+'_extract'
                report['stages'][kind]=process_archive(kind,path,selected,publisher)
                populated=set(report['stages'][kind]['populated_ciks'])
                report['coverage'][kind+'_unique_ticker_matches']=sum(r['cik'] in populated for r in rows if r['cik'] is not None)
                report['coverage'][kind+'_candidate_ticker_matches']=sum(bool(set(r['candidate_ciks'])&populated) for r in rows)
                publisher.json(f'SEC_{kind.upper()}_EXTRACTION_V2.json',dict(kind=kind,source=receipt,
                    result=report['stages'][kind],source_commit=report['source_commit'],
                    identity_map_lf_sha256=IDENTITY_SHA),'source_extraction_receipt')
                path.unlink()
        report['status']='PASS_IDENTITY_SNAPSHOT_ONLY' if identity_only else 'PASS_BOTH_BULK_SOURCES_RETAINED_EXTRACTION'
        report['active_stage']='complete'
    except Exception as exc:
        report['status']='FAIL_PARTIAL_SOURCE_SNAPSHOT'
        report['failed_stage']=report['active_stage']
        report['error']=getattr(exc,'evidence',dict(error_type=type(exc).__name__,message=common.redact(exc)))
        raise
    finally:
        report['finished_at']=now();report['assets']=publisher.assets.copy()
        path=root/'SEC_BULK_COVERAGE_V2.json';path.write_bytes(encoded(report))
        releases.publish_assets(tag,path)
        releases.gh_retry('release','edit',tag,'--draft=false','--notes',
            report['status']+'; exact coverage and asset bindings in SEC_BULK_COVERAGE_V2.json. Historical ownership NOT_PROVEN; scoring CLOSED.')
        print('SEC_BULK_FINAL',report['status'],tag,flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('sec-bulk-output'))
    parser.add_argument('--identity-only',action='store_true')
    args=parser.parse_args()
    value=os.environ.get('IDENTITY_ONLY','').strip().lower()
    if value not in ('','0','1','false','true','no','yes'):
        raise ValueError('IDENTITY_ONLY must be an explicit boolean')
    run(args.directory,args.identity_only or value in ('1','true','yes'))


if __name__=='__main__':main()
