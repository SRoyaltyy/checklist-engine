"""Authenticate a FAILED new-run checkpoint without restarting any producer."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def reconcile(plan,state,inventory,request):
    if request['run']==40621517496 or request['release_id']==427402982:
        raise ValueError('protected producer/draft cannot be a recovery target')
    part=plan['parts'][request['index']];done=state['completed'];excluded=state['excluded']
    names=[r['ticker'] for r in done+excluded]
    if (inventory['id']!=request['release_id'] or inventory['tag_name']!=request['checkpoint']['release']
        or state['source_part']!=part or state['inputs_release']!=request['plan']['release']
        or state['source_commit']!=request['source_commit']
        or state['recipe_fingerprint']!=plan['request']['corrected_recipe_fingerprint']
        or len(names)!=len(set(names)) or len(names)!=request['processed_checkpoint_rows']
        or not set(names)<=set(part['tickers'])):
        raise ValueError('partial checkpoint source/accounting differs')
    assets={a['name']:a for a in inventory['assets']}
    if len(assets)!=len(inventory['assets']):raise ValueError('duplicate partial asset name')
    for row in done:
        asset=assets[row['asset']]
        if (row['release']!=inventory['tag_name'] or row['diagnostic_questions']!=68904
            or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'
            or row['shared_registry_sha256']!=plan['request']['registry_sha256']
            or asset['state']!='uploaded' or asset['size']!=row['answer_container_bytes']
            or asset['digest']!='sha256:'+row['answer_container_sha256']):
            raise ValueError('durable partial payload binding differs')
    completed={r['ticker'] for r in done}
    return dict(format='NEW_REBUILD_PARTIAL_CHECKPOINT_V1',source_run=request['run'],source_job=request['job'],
        source_release=inventory['tag_name'],source_plan=request['plan'],source_checkpoint=request['checkpoint'],
        index=request['index'],part=part,source_commit=request['source_commit'],
        recipe_fingerprint=state['recipe_fingerprint'],shared_registry_sha256=plan['request']['registry_sha256'],
        expected_names=len(part['tickers']),verified_completed_names=len(done),completed=copy.deepcopy(done),
        checkpoint_excluded=copy.deepcopy(excluded),
        missing_names=[t for t in part['tickers'] if t not in completed],
        next_action='PRESERVE_VERIFIED_OUTPUTS_AND_CALCULATE_ONLY_MISSING_NAMES_IN_A_NEW_APPEND_ONLY_RUN',
        numerical_bad_stock_claim='NONE; checkpoint errors must be inspected, not inferred from failed upload',
        original_source_mutations='NONE',full_world_and_scoring='NOT_APPROVED')


def run(root):
    from ci import release_assets as io
    request=json.loads((ROOT/'ci/REBUILD_CHECKPOINT_PROBE_REQUEST.json').read_text(encoding='utf-8'))
    if request['run']==40621517496 or request['release_id']==427402982:raise ValueError('protected target forbidden')
    repository=os.environ['GITHUB_REPOSITORY']
    if repository.lower()!='sroyaltyy/checklist-engine':raise ValueError('wrong repository')
    job=json.loads(io.gh_retry('api',f"repos/{repository}/actions/jobs/{request['job']}"))
    if job['run_id']!=request['run'] or job['status']!='completed' or job['conclusion']!='failure':
        raise ValueError('source job is not the observed terminal failure; do not restart a live job')
    inventory=json.loads(io.gh_retry('api',f"repos/{repository}/releases/{request['release_id']}"))
    if inventory['id']!=request['release_id'] or inventory['tag_name']!=request['checkpoint']['release']:
        raise ValueError('observed draft identity differs')
    # Seed only the authenticated ID of this new failed-run draft. Avoid a
    # repository-wide draft scan; the normal downloader still verifies bytes.
    io._RELEASE_IDS[(repository,inventory['tag_name'])]=inventory['id']
    def checked(binding):
        file=io.download_asset(binding['release'],binding['asset'],root/'sources'/binding['release'])
        if sha(file.read_bytes())!=binding['sha256']:raise ValueError('probe source bytes differ')
        return file
    plan_file=checked(request['plan']);state_file=checked(request['checkpoint'])
    result=reconcile(json.loads(plan_file.read_bytes()),json.loads(state_file.read_bytes()),inventory,request)
    result.update(probe_run=int(os.environ['GITHUB_RUN_ID']),probe_source_commit=os.environ['GITHUB_SHA'],
        source_job_status={key:job.get(key) for key in ('id','name','status','conclusion','started_at','completed_at')})
    # Keep the authenticated audit visible even if release/artifact transport
    # fails again. No credentials are part of these source/checkpoint fields.
    print('REBUILD_PARTIAL_CHECKPOINT_JSON',json.dumps(result,separators=(',',':')),flush=True)
    file=root/'REBUILD_PARTIAL_CHECKPOINT_V1.json';file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    tag=f"rebuild-partial-checkpoint-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    io.gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
        '--notes','Read-only recovery audit of a failed NEW rebuild part. Preserved checkpoint bytes and verified completed payload metadata; only missing names need a new append-only calculation. No producer restarted or original draft changed.')
    io.publish_assets(tag,file,state_file,ROOT/'ci/REBUILD_CHECKPOINT_PROBE_REQUEST.json');io.gh_retry('release','edit',tag,'--draft=false')
    print('PARTIAL_CHECKPOINT_VERIFIED',result['verified_completed_names'],'MISSING',len(result['missing_names']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);args=parser.parse_args()
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    try:run(root)
    except Exception as exc:
        from ci.release_assets import describe_failure
        print('PARTIAL_CHECKPOINT_PROBE_FAILURE',describe_failure(exc),flush=True)
        raise
