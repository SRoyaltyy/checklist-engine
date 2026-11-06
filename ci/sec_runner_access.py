"""Bounded official-source access proof on the authorized runner; no bulk download."""
import hashlib
import json
import os
from pathlib import Path
import sys

from fetch.sec_bulk import source_links
from scripts.nai import common

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT/'ci/SEC_RUNNER_ACCESS_REQUEST.json'
SOURCES = [
    ('tickers','https://www.sec.gov/files/company_tickers.json'),
    ('exchange_tickers','https://www.sec.gov/files/company_tickers_exchange.json'),
    ('form345_index','https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets'),
    ('form13f_index','https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets'),
    ('submissions','https://data.sec.gov/submissions/CIK0000320193.json'),
    ('numeric_concept','https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Assets.json'),
]


def validate_request(value):
    if type(value.get('execute')) is not bool or {k:v for k,v in value.items() if k!='execute'} != dict(version=1,scope='SIX_DECLARED_OFFICIAL_ENDPOINTS_ONLY',max_response_bytes=10000000,attempts_per_endpoint=1):
        raise ValueError('SEC access request changes the declared bounded scope')
    return value


def inspect(kind,raw,url):
    if kind.endswith('_index'):
        links=source_links(raw.decode('utf-8'),url,start=2020,end=2026)
        return dict(verified_official_zip_links=len(links),first_url=links[0],last_url=links[-1])
    value=json.loads(raw)
    if kind=='tickers':
        if not value or not all({'cik_str','ticker'}<=set(r) for r in value.values()):
            raise ValueError('ticker map schema is empty or invalid')
        return dict(rows=len(value))
    if kind=='exchange_tickers':
        if not {'cik','ticker','exchange'}<=set(value['fields']) or not value['data']:
            raise ValueError('exchange ticker map schema is empty or invalid')
        return dict(rows=len(value['data']))
    if int(value['cik']) != 320193:
        raise ValueError('sample CIK differs')
    if kind=='submissions':
        rows=len(value['filings']['recent']['accessionNumber'])
    else:
        rows=sum(len(v) for v in value['units'].values())
        if not all(type(f.get('val')) in (int,float) for facts in value['units'].values() for f in facts):
            raise ValueError('numeric concept has non-numeric values')
    if rows<1:
        raise ValueError('official sample is empty')
    return dict(rows=rows)


def main():
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='SRoyaltyy/checklist-engine':
        raise ValueError('SEC access probes run only on the authorized GitHub runner')
    request=validate_request(json.loads(REQUEST.read_bytes()))
    if not request['execute']:
        raise ValueError('SEC access proof is disabled')
    records=[]
    for kind,url in SOURCES:
        try:
            raw=common.get(url,tries=1,timeout=90,max_bytes=request['max_response_bytes'])
            detail=inspect(kind,raw,url)
            records.append(dict(kind=kind,url=url,status='PASS_SCHEMA_AND_NONEMPTY_BODY',
                bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),**detail))
        except Exception as exc:
            records.append(dict(kind=kind,url=url,status='FAIL',
                evidence=getattr(exc,'evidence',dict(error_type=type(exc).__name__,message=common.redact(exc)))))
        print('SEC_ACCESS_RESULT',json.dumps(records[-1],sort_keys=True),flush=True)
    passed=all(r['status']=='PASS_SCHEMA_AND_NONEMPTY_BODY' for r in records)
    report=dict(format='SEC_RUNNER_ACCESS_PROOF_V1',status='PASS_ALL_SIX_OFFICIAL_ENDPOINTS' if passed else 'BLOCKED_OFFICIAL_ENDPOINT_ACCESS',
        actual_run_id=os.environ['GITHUB_RUN_ID'],actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],source_commit=os.environ['GITHUB_SHA'],
        request=request,route='EXISTING_PRIMARY_ACTION_RELAY_ONLY',records=records,
        scope='Bounded source-access/schema proof only; no complete bulk downloads, identity extension or market calculation.',
        upstream_user_agent='NOT_OBSERVABLE_FROM_CLIENT; deployed relay configuration must preserve a declared contact identity',
        world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    root=ROOT/'sec-access-proof';root.mkdir(exist_ok=True)
    path=root/'SEC_RUNNER_ACCESS_PROOF_V1.json'
    path.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    publish_receipt(path,report)
    return 0 if passed else 1


def publish_receipt(path,report):
    tag='sec-runner-access-v1-'+report['actual_run_id']+'-'+report['actual_attempt']
    from ci.release_assets import gh_retry,publish_assets
    gh_retry('release','create',tag,'--draft','--target',report['source_commit'],'--title',tag,
             '--notes','Bounded official SEC source-access proof. Failed endpoints retained explicitly; scoring CLOSED.')
    publish_assets(tag,path)
    gh_retry('release','edit',tag,'--draft=false')


if __name__=='__main__':
    sys.exit(main())
