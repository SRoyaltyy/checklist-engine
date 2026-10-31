"""Preserve a failed NEW shard's verified outputs; calculate only missing names."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMPLETE='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'


def recovery_plan(plan,probe):
    if probe['source_run']==40621517496:
        raise ValueError('protected producer cannot be a recovery target')
    part=plan['parts'][probe['index']]
    done=[r['ticker'] for r in probe['completed']]
    missing=[t for t in part['tickers'] if t not in set(done)]
    if (probe['part']!=part or len(done)!=len(set(done))
        or not set(done)<=set(part['tickers']) or not missing
        or probe['missing_names']!=missing or probe['verified_completed_names']!=len(done)
        or probe['expected_names']!=len(part['tickers'])
        or probe['recipe_fingerprint']!=plan['request']['corrected_recipe_fingerprint']
        or probe['shared_registry_sha256']!=plan['request']['registry_sha256']):
        raise ValueError('recovery membership or frozen identity differs')
    subset=copy.deepcopy(part);subset['tickers']=missing
    return dict(format='PRICE_PARTIAL_RECOVERY_PLAN_V1',scope='ONLY_MISSING_NAMES_OF_ONE_FAILED_NEW_SHARD',
        request=copy.deepcopy(plan['request']),parts=[subset],accepted_tickers=len(missing),
        price_answer_per_ticker_limit=plan['price_answer_per_ticker_limit'],
        full_world_acceptance=plan['full_world_acceptance'],
        recovery=dict(source_run=probe['source_run'],source_job=probe['source_job'],
            source_plan=probe['source_plan'],source_checkpoint=probe['source_checkpoint'],
            original_index=probe['index'],preserved_names=done,calculate_names=missing))


def composed_state(plan,probe,calculated,inputs_release,preserved_release):
    from ci.compact_world_build import validate_shard
    scoped=recovery_plan(plan,probe)
    validate_shard(calculated,scoped['parts'][0])
    if (calculated['inputs_release']!=inputs_release or calculated['status']!=COMPLETE
        or calculated['recipe_fingerprint']!=probe['recipe_fingerprint']
        or calculated['world_gate']!=plan['full_world_acceptance']
        or calculated['scoring_gate']!='CLOSED'):
        raise ValueError('recovery output provenance or status differs')
    rows=[dict(row,release=preserved_release) for row in probe['completed']]
    state=copy.deepcopy(calculated)
    state.update(source_part=copy.deepcopy(probe['part']),inputs_release=probe['source_plan']['release'],
        completed=rows+copy.deepcopy(calculated['completed']),
        answer_bytes=sum(r['answer_container_bytes'] for r in rows+calculated['completed']),
        recovery_provenance=dict(original_run=probe['source_run'],original_job=probe['source_job'],
            original_index=probe['index'],original_source_commit=probe['source_commit'],
            original_checkpoint=probe['source_checkpoint'],preserved_release=preserved_release,
            preserved_count=len(rows),recovery_inputs_release=inputs_release,
            recovery_source_commit=calculated['source_commit'],
            calculated_count=len(calculated['completed']),remaining_count=len(calculated['excluded']),
            requires_explicit_parent_composition=True))
    validate_shard(state,probe['part'])
    return state


def verify_payload_rows(rows,registry,inventory):
    assets={a['name']:a for a in inventory['assets']}
    if len(assets)!=len(inventory['assets']):raise ValueError('duplicate payload asset name')
    for row in rows:
        asset=assets[row['asset']]
        if (row['release']!=inventory['tag_name'] or row['diagnostic_questions']!=68904
            or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'
            or row['shared_registry_sha256']!=registry or asset['state']!='uploaded'
            or asset['size']!=row['answer_container_bytes']
            or asset['digest']!='sha256:'+row['answer_container_sha256']
            or row['asset']!=row['ticker'].encode().hex()+'.diagnostic_answers.tar.zst'):
            raise ValueError('recovery payload identity differs')


def run(root):
    from ci import release_assets as io
    from ci.compact_world_build import build
    from ci.rebuild_checkpoint_probe import reconcile
    request_file=ROOT/'ci/REBUILD_PARTIAL_RECOVERY_REQUEST.json'
    request=json.loads(request_file.read_bytes())
    if request.get('execute') is not True:raise ValueError('recovery execution is not enabled')
    if request['run']==40621517496 or request['release_id']==427402982:
        raise ValueError('protected producer/draft forbidden')
    repository=os.environ['GITHUB_REPOSITORY']
    if repository.lower()!='sroyaltyy/checklist-engine':raise ValueError('wrong repository')
    root.mkdir(parents=True,exist_ok=True)
    def checked(binding):
        path=io.download_asset(binding['release'],binding['asset'],root/'sources'/binding['release'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=binding['sha256']:
            raise ValueError('immutable recovery source bytes differ')
        return path
    def write(name,data):
        path=root/name;path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');return path
    def create(tag,notes):
        io.gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],'--notes',notes)
    def publish(tag,*files):
        io.publish_assets(tag,*files);io.gh_retry('release','edit',tag,'--draft=false')
    def inventory(tag):return dict(tag_name=tag,assets=list(io.asset_index(tag).values()))
    job=json.loads(io.gh_retry('api',f"repos/{repository}/actions/jobs/{request['job']}"))
    if job['run_id']!=request['run'] or job['status']!='completed' or job['conclusion']!='failure':
        raise ValueError('source job is not the pinned terminal failure')
    source=json.loads(io.gh_retry('api',f"repos/{repository}/releases/{request['release_id']}"))
    if source['id']!=request['release_id'] or source['tag_name']!=request['checkpoint']['release']:
        raise ValueError('source draft identity differs')
    io._RELEASE_IDS[(repository,source['tag_name'])]=source['id']
    plan=json.loads(checked(request['plan']).read_bytes())
    checkpoint=json.loads(checked(request['checkpoint']).read_bytes())
    probe_file=checked(request['probe']);probe=json.loads(probe_file.read_bytes())
    expected=reconcile(plan,checkpoint,source,request)
    if any(probe.get(key)!=value for key,value in expected.items()):
        raise ValueError('published probe differs from freshly reconciled checkpoint')
    scoped=recovery_plan(plan,probe)
    stem=f"{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    preserved=f"compact-world-build-preserved-v1-{stem}-{request['index']:03d}"
    # Copy authenticated old bytes BEFORE calculation, without changing any
    # original release, visibility, checkpoint, or answer. Never recalculate them.
    verify_payload_rows(probe['completed'],probe['shared_registry_sha256'],source)
    create(preserved,'Unchanged verified payloads from a failed NEW rebuild shard; original release untouched.')
    preserved_rows=[]
    for row in probe['completed']:
        file=checked(dict(release=row['release'],asset=row['asset'],sha256=row['answer_container_sha256']))
        if file.stat().st_size!=row['answer_container_bytes']:raise ValueError('preserved payload size differs')
        io.publish_assets(preserved,file);preserved_rows.append(dict(row,release=preserved))
    preserved_file=write('PRESERVED_PARTIAL_OUTPUTS_V1.json',dict(source_probe=request['probe'],
        original_source_commit=probe['source_commit'],completed=preserved_rows,
        unchanged_payload_bytes=sum(r['answer_container_bytes'] for r in preserved_rows),
        world_gate='NOT_PROVEN',scoring_gate='CLOSED'))
    publish(preserved,preserved_file,probe_file,request_file)
    verify_payload_rows(preserved_rows,probe['shared_registry_sha256'],inventory(preserved))
    inputs=f'compact-world-build-recovery-v1-{stem}-inputs'
    plan_file=write('COMPACT_WORLD_BUILD_PLAN.json',scoped)
    create(inputs,'Only missing names from the authenticated failed new shard; parent source and frozen recipe retained.')
    publish(inputs,plan_file,probe_file,request_file)
    print('RECOVERY_SCOPE',json.dumps(dict(preserved_release=preserved,preserved_names=[r['ticker'] for r in preserved_rows],
        inputs_release=inputs,calculate_names=scoped['parts'][0]['tickers'])),flush=True)
    build(root/'build',inputs,0)
    calculated=json.loads((root/'build'/'COMPACT_WORLD_SHARD.json').read_bytes())
    shard=f'compact-world-build-v1-{stem}-000'
    if calculated['source_commit']!=os.environ['GITHUB_SHA']:raise ValueError('new shard source commit differs')
    verify_payload_rows(calculated['completed'],probe['shared_registry_sha256'],inventory(shard))
    state=composed_state(plan,probe,calculated,inputs,preserved)
    file=write('COMPACT_WORLD_SHARD.json',state)
    tag=f"compact-world-build-recovered-part-v1-{stem}-{request['index']:03d}"
    create(tag,'Explicit replacement manifest for one failed NEW part. Per-row releases are authoritative; requires a new parent composition, not a rerun. Full-world/scoring unapproved.')
    publish(tag,file,preserved_file,probe_file,request_file)
    print('RECOVERED_PART_JSON',json.dumps(dict(release=tag,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        **state['recovery_provenance'])),flush=True)
    if state['excluded']:raise ValueError('remaining recovery gaps published; require another bounded add-on')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);args=parser.parse_args()
    try:run(Path(args.directory))
    except Exception as exc:
        from ci.release_assets import describe_failure
        print('PARTIAL_RECOVERY_FAILURE',describe_failure(exc),flush=True);raise
