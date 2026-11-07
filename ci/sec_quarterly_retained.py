"""Versioned fixed-field SEC quarterly acquisition; source data, never scoring."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil

from ci import release_assets as releases
from ci.sec_bulk_retained import Publisher,now
from ci.sec_quarterly_core import PAGES,source_catalog
from ci.sec_quarterly_extract import extract_zip
from ci.sec_quarterly_profile import bulk_prerequisite,download,profile_zip,validate_request as profile_request
from ci.sec_quarterly_sources import ProfileCache,retained_ciks
from ci.sec_runner_access import relay_configuration
from scripts.nai.common import redact

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'ci/SEC_QUARTERLY_RETAINED_REQUEST.json'


def validate_request(value):
    if (set(value)!= {'version','scope','execute','bulk_readback','profile_sources'}
            or value['version']!=2 or value['scope']!='SEC_QUARTERLY_FIXED_FIELDS_2020_LATEST'
            or type(value['execute']) is not bool):raise ValueError('quarterly fixed-field request scope differs')
    profile_request(dict(version=1,scope='SEC_QUARTERLY_OFFICIAL_SOURCE_PROFILE_2020_LATEST',start_year=2020,
                         execute=value['execute'],bulk_readback=value['bulk_readback']))
    sources=value['profile_sources']
    if not isinstance(sources,dict) or not set(sources)<=set(PAGES):raise ValueError('invalid quarterly cache kinds')
    for spec in sources.values():
        if (set(spec)!= {'run','attempt','commit','receipt_sha256'}
                or not all(re.fullmatch(r'[1-9][0-9]*',str(spec[k])) for k in ('run','attempt'))
                or not re.fullmatch(r'[0-9a-f]{40}',spec['commit'])
                or not re.fullmatch(r'[0-9a-f]{64}',spec['receipt_sha256'])):
            raise ValueError('quarterly source cache anchor differs')
    return value


def run(kind,root):
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='SRoyaltyy/checklist-engine':
        raise ValueError('quarterly source acquisition runs only on the authorized runner')
    request=validate_request(json.loads(REQUEST.read_bytes()))
    event=os.environ.get('GITHUB_EVENT_NAME')
    if event=='push' and not request['execute']:raise ValueError('quarterly one-shot acquisition disabled')
    if request['bulk_readback'] is None:raise ValueError('quarterly bulk prerequisite is not bound')
    if kind not in PAGES:raise ValueError('unknown quarterly dataset')
    root.mkdir(parents=True,exist_ok=True)
    prerequisite=bulk_prerequisite(request['bulk_readback'],root)
    selected,identity_source=retained_ciks(prerequisite,root)
    spec=request['profile_sources'].get(kind) if event=='push' else None
    if spec:
        cache=ProfileCache(kind,spec,root);windows=[r['window'] for r in cache.windows]
    else:
        if not relay_configuration()['matches_inspected_production_worker']:raise ValueError('quarterly relay differs')
        cache=None
    tag=f"nai-sec-quarterly-v2-{kind}-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    publisher=Publisher(root,tag)
    report=dict(format='SEC_QUARTERLY_FIXED_FIELDS_V2',status='FAIL_PARTIAL_QUARTERLY_FIXED_FIELDS',kind=kind,
        actual_run_id=os.environ['GITHUB_RUN_ID'],actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
        source_commit=os.environ['GITHUB_SHA'],release=tag,started_at=now(),windows=[],active_stage='source_catalog',
        bulk_prerequisite=prerequisite,identity_source=identity_source,profile_source=spec,
        scope='ALL_FIXED_SOURCE_ROWS_NOT_A_HISTORICAL_TICKER_OR_STOCK_DATE_JOIN',
        free_text_features=False,scoring_gate='CLOSED',world_gate='NOT_PROVEN')
    try:
        if cache:
            report['index']=cache.report['index']
            report['index_lineage']=dict(release=cache.tag,receipt_sha256=spec['receipt_sha256'],source_commit=spec['commit'])
        else:
            path=root/(kind+'_official_index.html');report['index']=download(PAGES[kind],path,10000000)
            windows=source_catalog(path.read_text(encoding='utf-8'),kind,start_year=2020)
            publisher.emit(path,'official_source_index')
        report['published_catalog']=windows
        for index,window in enumerate(windows):
            report['active_stage']=window['name'];path=None
            if cache:path,source,profile=cache.get(cache.windows[index])
            else:
                available=shutil.disk_usage(root).free-2*1024**3
                if available<1024**3:raise ValueError('insufficient quarterly source disk reserve')
                path=root/window['name'];source=download(window['url'],path,min(available,2*1024**3-1))
                profile=None
            publisher.json(window['name']+'.source.json',dict(window=window,source=source,
                source_commit=report['source_commit']),'quarterly_source_acquisition_receipt')
            try:
                if profile is None:profile=profile_zip(path)
                extraction=extract_zip(path,kind,window['label'],publisher,selected)
                measured={r['table']:r['rows'] for r in profile['tables']}
                if any(t['output_rows']!=measured[name] for name,t in extraction['tables'].items()):
                    raise ValueError('fixed-field output counts differ from source profile')
            except Exception:
                if cache is None and path.exists():publisher.emit(path,'official_source_zip_with_extraction_failure')
                raise
            if cache:path.unlink()
            else:publisher.emit(path,'official_unfiltered_source_zip')
            receipt=dict(window=window,source=source,profile=profile,extraction=extraction,
                         source_commit=report['source_commit'])
            publisher.json(window['name']+'.fixed.json',receipt,'quarterly_fixed_field_receipt')
            report['windows'].append(receipt)
            releases.gh_retry('release','edit',tag,'--draft=false','--notes',
                'INCOMPLETE quarterly fixed fields; wait for final receipt. Historical ticker joins unproven. Scoring CLOSED.')
        report['active_stage']='complete';report['status']='PASS_ALL_PUBLISHED_QUARTERLY_FIXED_FIELDS_SOURCE_ONLY'
    except Exception as exc:
        report['failed_stage']=report['active_stage']
        report['error']=getattr(exc,'evidence',dict(type=type(exc).__name__,message=redact(exc)));raise
    finally:
        report['finished_at']=now();report['assets']=publisher.assets.copy()
        path=root/'SEC_QUARTERLY_FIXED_FIELDS_V2.json'
        path.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        releases.publish_assets(tag,path)
        releases.gh_retry('release','edit',tag,'--draft=false','--notes',report['status']+'; scoring CLOSED, historical joins NOT_PROVEN.')
        print('SEC_QUARTERLY_FIXED_FINAL',kind,report['status'],len(report['windows']),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=list(PAGES));parser.add_argument('--directory',type=Path,default=Path('sec-quarterly-fixed-output'))
    args=parser.parse_args();run(args.kind,args.directory)


if __name__=='__main__':main()
