"""Retain the exact failing official ZIP and inspect all retained member headers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

from ci import release_assets as releases
from ci.sec_bulk_retained import Publisher,downloaded,load_cohort,now,reused_identity
from ci.sec_bulk_retained_core import cik_number,decode_source,live_candidates,members_by_cik,resolve_identities
from ci.sec_runner_access import relay_configuration
from scripts.nai.common import redact

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'ci/SEC_COMPANYFACTS_DIAGNOSTIC_REQUEST.json'
EXPECTED_SHA='dfb8896a994040bccf5be76a9e65a3fb009453389cbe9268ab3d28629cc06bec'


def validate_request(value):
    if (type(value.get('execute')) is not bool
            or value!=dict(version=1,execute=value.get('execute'),source_sha256=EXPECTED_SHA)):
        raise ValueError('source diagnostic scope changed')
    return value


def inspect_archive(path,selected,invalid_member):
    members=[]
    with zipfile.ZipFile(path) as archive:
        grouped=members_by_cik(archive.namelist(),selected,'companyfacts')
        if not grouped:raise ValueError('no selected companyfacts members')
        for cik,names in sorted(grouped.items()):
            for name in names:
                raw=archive.read(name);reason=None
                try:payload=decode_source(raw)
                except (json.JSONDecodeError,UnicodeDecodeError):payload=None;reason='INVALID_JSON'
                if reason:pass
                elif not isinstance(payload,dict):reason='NON_OBJECT_PAYLOAD'
                elif not payload:reason='EMPTY_OBJECT_NO_BODY_IDENTITY_OR_FACTS'
                elif 'cik' not in payload:reason='MISSING_BODY_CIK_NONEMPTY_PAYLOAD'
                else:
                    try:body_cik=cik_number(payload['cik'])
                    except ValueError:reason='INVALID_BODY_CIK'
                    else:
                        if body_cik!=cik:reason='MISMATCHED_BODY_CIK'
                if reason is None and not isinstance(payload.get('facts',{}),dict):reason='INVALID_FACTS_CONTAINER'
                entry=dict(cik=cik,zip_member=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                    status=reason or 'BODY_IDENTITY_VERIFIED',
                    top_level_keys=sorted(payload) if isinstance(payload,dict) else None,
                    facts_container_present=isinstance(payload,dict) and 'facts' in payload,
                    facts_empty=isinstance(payload,dict) and payload.get('facts')=={})
                members.append(entry)
                if reason:invalid_member(entry,raw)
    return dict(selected_ciks=len(selected),archive_ciks=len(grouped),
        missing_archive_ciks=sorted(set(selected)-set(grouped)),members=members,
        status_counts={s:sum(m['status']==s for m in members) for s in sorted({m['status'] for m in members})})


def run(root):
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='SRoyaltyy/checklist-engine':
        raise ValueError('official source diagnostic runs only on the authorized runner')
    request=validate_request(json.loads(REQUEST.read_bytes()))
    if not request['execute']:raise ValueError('source diagnostic disabled')
    if not relay_configuration()['matches_inspected_production_worker']:raise ValueError('relay differs')
    root.mkdir(parents=True,exist_ok=True)
    tag=f"sec-companyfacts-source-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    publisher=Publisher(root,tag)
    report=dict(format='SEC_COMPANYFACTS_SOURCE_DIAGNOSTIC_V1',status='FAIL',actual_run_id=os.environ['GITHUB_RUN_ID'],
        actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],source_commit=os.environ['GITHUB_SHA'],release=tag,
        started_at=now(),expected_source_sha256=EXPECTED_SHA,scoring_gate='CLOSED',world_gate='NOT_PROVEN')
    try:
        maps=[]
        for kind in ('tickers','exchanges'):
            path,receipt=reused_identity(kind,root);maps.append(json.loads(path.read_bytes()));path.unlink()
        identities=resolve_identities(load_cohort(),live_candidates(*maps))
        selected={c for row in identities for c in row['candidate_ciks']}
        free=shutil.disk_usage(root).free
        path,source=downloaded('companyfacts',root,min(free-2*1024**3,2*1024**3-1))
        report['source']=source
        if source['sha256']!=EXPECTED_SHA:raise ValueError('official ZIP changed; diagnostic cannot reproduce the failed source')
        def retain(entry,raw):
            member_path=root/f"companyfacts_exception_CIK{entry['cik']:010d}.json"
            member_path.write_bytes(raw)
            publisher.emit(member_path,'source_member_diagnostic',cik=entry['cik'],
                           zip_member=entry['zip_member'],source_status=entry['status'])
        report['diagnostic']=inspect_archive(path,selected,retain)
        publisher.emit(path,'official_unfiltered_source_zip')
        report['status']='PASS_EXACT_SOURCE_DIAGNOSTIC_NOT_DATA_EXTRACTION'
    except Exception as exc:
        report['error']=getattr(exc,'evidence',dict(type=type(exc).__name__,message=redact(exc)));raise
    finally:
        report['finished_at']=now();report['assets']=publisher.assets.copy()
        receipt=root/'SEC_COMPANYFACTS_SOURCE_DIAGNOSTIC_V1.json'
        receipt.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        releases.publish_assets(tag,receipt)
        releases.gh_retry('release','edit',tag,'--draft=false','--notes',report['status']+'; source evidence only. Scoring CLOSED.')
        print('SEC_SOURCE_DIAGNOSTIC_FINAL',report['status'],tag,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('sec-companyfacts-diagnostic-output'))
    run(parser.parse_args().directory)
