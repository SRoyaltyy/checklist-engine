"""Merge already completed raw recovery as an immutable add-on, no rebuild."""
import argparse
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
from ci import native_price_base as base
from ci.native_price_recovery import api
from ci.release_assets import download_asset,gh_retry

REQUEST=Path('ci/COMPACT_BASE_ADDON_REQUEST.json')


def verify_jobs(source,run,jobs):
    if (run['id'],run['head_sha'],run['run_attempt'])!=(source['run'],source['head'],1):
        raise ValueError('raw source run identity differs')
    selected={}
    for job in jobs:
        match=re.fullmatch(r'build \((\d+)\)',job['name'])
        if not match:continue
        shard=int(match[1])
        if shard in selected:raise ValueError('ambiguous raw source jobs')
        selected[shard]=job
    for shard in source['shards']:
        job=selected.get(shard,{})
        if job.get('status')!='completed' or job.get('conclusion')!='success':
            raise ValueError(f'raw source shard {shard} has not succeeded')
    return [dict(shard=n,job=selected[n]['id'],run=source['run']) for n in source['shards']]


def run(root,request):
    root.mkdir(parents=True,exist_ok=True);proof=[]
    for source in request['sources']:
        endpoint=f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{source['run']}"
        run=api(endpoint);jobs=api(endpoint+'/jobs?per_page=100')
        if len(jobs['jobs'])!=jobs['total_count']:raise ValueError('incomplete source jobs')
        proof+=verify_jobs(source,run,jobs['jobs'])
    routes={str(n):f"native-price-base-v1-{source['run']}-1-{n:03d}" for source in request['sources'] for n in source['shards']}
    if sorted(map(int,routes))!=list(range(16)):raise ValueError('raw add-on must route all 16 shards')
    file=root/'ADDON_ROUTES.json';file.write_text(json.dumps(routes,indent=2)+'\n')
    (root/'ADDON_SOURCE_JOBS.json').write_text(json.dumps(proof,indent=2)+'\n')
    original=base.download,base.gh
    base.download=download_asset;base.gh=gh_retry
    try:
        base.merge(SimpleNamespace(directory=str(root),inputs_tag=request['inputs_tag'],
            build_prefix='native-price-base-v1-40360947486-1',routes=str(file)))
    finally:base.download,base.gh=original


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    args=parser.parse_args();run(Path(args.directory),json.loads(REQUEST.read_text()))
