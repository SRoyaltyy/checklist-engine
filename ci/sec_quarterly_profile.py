"""Immutable official quarterly source/schema acquisition; no feature calculations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

from ci import release_assets as releases
from ci.sec_bulk_retained import Publisher,digest,now,wait_seconds
from ci.sec_quarterly_core import PAGES,source_catalog,table_members
from ci.sec_runner_access import relay_configuration
from scripts.nai import common

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'ci/SEC_QUARTERLY_PROFILE_REQUEST.json'


def validate_request(value):
    if (type(value.get('execute')) is not bool
            or value!=dict(version=1,scope='SEC_QUARTERLY_OFFICIAL_SOURCE_PROFILE_2020_LATEST',
                           start_year=2020,execute=value.get('execute'))):
        raise ValueError('quarterly source profile scope differs')
    return value


def download(url,path,max_bytes):
    started=now();limits=[]
    for attempt in range(2):
        try:
            common.get(url,str(path),max_bytes=max_bytes,timeout=1800,tries=3);break
        except common.SourceError as exc:
            if exc.evidence.get('http_status')!=429:raise
            delay=max(601,exc.evidence.get('retry_after_seconds') or 0)
            limits.append(dict(observed_at=now(),evidence=exc.evidence.copy(),wait_seconds=delay))
            if attempt or delay>3605:
                exc.evidence['rate_limit_history']=limits;raise
            wait_seconds(delay)
    return dict(url=url,bytes=path.stat().st_size,sha256=digest(path),started_at=started,
                finished_at=now(),rate_limit_history=limits)


def profile_zip(path):
    tables=[];non_tabular=[]
    with zipfile.ZipFile(path) as archive:
        members=table_members(archive)
        for stem,member in sorted(members.items()):
            with archive.open(member) as stream:
                first=stream.readline(1024*1024+1)
                if len(first)>1024*1024:raise ValueError('SEC source table header exceeds one MiB')
                if b'\t' not in first:
                    non_tabular.append(member.filename);continue
                columns=first.decode('utf-8-sig').rstrip('\r\n').split('\t')
                signature=hashlib.sha256(first);rows=0;ragged=0;examples=[]
                while True:
                    line=stream.readline(32*1024*1024+1)
                    if not line:break
                    if len(line)>32*1024*1024:raise ValueError('SEC source line exceeds bounded profiling buffer')
                    rows+=1;signature.update(line)
                    width=len(line.rstrip(b'\r\n').split(b'\t'))
                    if width!=len(columns):
                        ragged+=1
                        if len(examples)<20:examples.append(dict(source_row=rows,actual_cells=width,
                            bytes=len(line),sha256=hashlib.sha256(line).hexdigest()))
                tables.append(dict(table=stem,source_member=member.filename,columns=columns,
                    duplicate_or_blank_header=len(set(columns))!=len(columns) or '' in columns,
                    rows=rows,ragged_rows=ragged,ragged_row_examples=examples,
                    uncompressed_bytes=member.file_size,crc32=member.CRC,sha256=signature.hexdigest()))
    if not tables or not any(t['rows'] for t in tables):raise ValueError('ZIP has no populated structured tables')
    return dict(tables=tables,non_tabular_members=non_tabular,
        raw_source_only=True,point_in_time_join='NOT_RUN',free_text_features=False)


def acquire(kind,root):
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='SRoyaltyy/checklist-engine':
        raise ValueError('quarterly source downloads run only on the authorized GitHub runner')
    request=validate_request(json.loads(REQUEST.read_bytes()))
    if not request['execute']:raise ValueError('quarterly source profile disabled')
    if kind not in PAGES:raise ValueError('unsupported quarterly source kind')
    if not relay_configuration()['matches_inspected_production_worker']:raise ValueError('relay differs')
    root.mkdir(parents=True,exist_ok=True)
    tag=f"sec-quarterly-profile-v2-{kind}-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    publisher=Publisher(root,tag)
    report=dict(format='SEC_QUARTERLY_SOURCE_PROFILE_V2',status='FAIL_PARTIAL_SOURCE_CATALOG',kind=kind,
        actual_run_id=os.environ['GITHUB_RUN_ID'],actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
        source_commit=os.environ['GITHUB_SHA'],release=tag,started_at=now(),windows=[],
        scope='OFFICIAL_RAW_SOURCES_AND_SCHEMA_ONLY_NOT_FIXED_FIELD_PARQUET_OR_PIT_JOIN',
        world_gate='NOT_PROVEN',scoring_gate='CLOSED',free_text_features=False)
    try:
        report['active_stage']='official_index'
        path=root/(kind+'_official_index.html');report['index']=download(PAGES[kind],path,10000000)
        catalog=source_catalog(path.read_text(encoding='utf-8'),kind,start_year=request['start_year'])
        report['published_catalog']=catalog;publisher.emit(path,'official_source_index')
        for window in catalog:
            report['active_stage']=window['name'];path=root/window['name']
            available=shutil.disk_usage(root).free-2*1024**3
            if available<1024**3:raise ValueError('insufficient disk reserve for quarterly ZIP')
            source=download(window['url'],path,min(available,2*1024**3-1))
            publisher.json(window['name']+'.source.json',
                dict(window=window,source=source,source_commit=report['source_commit']),
                'quarterly_source_acquisition_receipt')
            try:profile=profile_zip(path)
            except Exception:
                # Source stays public and recoverable even when parsing fails.
                publisher.emit(path,'official_source_zip_with_profile_failure',source_window=window['label'])
                raise
            publisher.emit(path,'official_unfiltered_source_zip',source_window=window['label'])
            receipt=dict(window=window,source=source,profile=profile,source_commit=report['source_commit'])
            publisher.json(window['name']+'.json',receipt,'quarterly_source_schema_receipt')
            report['windows'].append(receipt)
            releases.gh_retry('release','edit',tag,'--draft=false','--notes',
                'INCOMPLETE quarterly raw source catalog; wait for final profile receipt. Not parquet or PIT coverage. Scoring CLOSED.')
        report['active_stage']='complete';report['status']='PASS_PUBLISHED_SOURCE_CATALOG_ONLY'
    except Exception as exc:
        report['error']=getattr(exc,'evidence',dict(type=type(exc).__name__,message=common.redact(exc)));raise
    finally:
        report['finished_at']=now();report['assets']=publisher.assets.copy()
        path=root/'SEC_QUARTERLY_SOURCE_PROFILE_V2.json'
        path.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        releases.publish_assets(tag,path)
        releases.gh_retry('release','edit',tag,'--draft=false','--notes',report['status']+'; source/schema only, scoring CLOSED.')
        print('SEC_QUARTERLY_PROFILE_FINAL',kind,report['status'],len(report['windows']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=list(PAGES),required=True)
    parser.add_argument('--directory',type=Path,default=Path('sec-quarterly-profile-output'))
    args=parser.parse_args();acquire(args.kind,args.directory)
