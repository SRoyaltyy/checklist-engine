"""Compose a failed NEW price part without recalculating other parts."""
import argparse
import copy
import hashlib
import json
import os
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMPLETE='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'


def encoded(value):return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()


def partition(completed,excluded,expected):
    names=[r['ticker'] for r in completed+excluded]
    if len(names)!=len(set(names)) or set(names)!=set(expected):
        raise ValueError('completion/exclusion membership differs')


def compose(plan,parent,replacement,probe,ledger,*,bindings,parent_bytes,request_bytes):
    """Authenticated inputs enter here; no source value or answer is modified."""
    index=probe['index'];part=plan['parts'][index];request=plan['request']
    if probe['source_run']==40621517496 or bindings['failed_release_id']==427402982:
        raise ValueError('protected producer forbidden')
    all_names=[t for p in plan['parts'] for t in p['tickers']]
    if (type(plan['accepted_tickers']) is not int or not 0<plan['accepted_tickers']<=plan['original_universe']
        or len(all_names)!=len(set(all_names)) or len(all_names)!=plan['accepted_tickers']):
        raise ValueError('parent plan cohort differs')
    partition(parent['completed'],parent['excluded'],all_names)
    partition(replacement['completed'],replacement['excluded'],part['tickers'])
    failed={r['index'] for r in parent['shard_errors']}
    affected=set(part['tickers'])
    if (parent['status']!='PRICE_ANSWER_BUILD_MEASURED_NOT_FULL_WORLD'
        or index not in failed or any(r['ticker'] in affected for r in parent['completed'])
        or any(r.get('reason')!='SHARD_RESULT_UNVERIFIED' for r in parent['excluded'] if r['ticker'] in affected)
        or parent['inputs_release']!=probe['source_plan']['release']
        or parent['original_universe']!=plan['original_universe']
        or parent['raw_dependency_bytes']!=plan['raw_dependency_bytes']
        or parent['price_reservation_bytes']!=request['answer_budget_bytes']
        or parent['hard_world_cap_bytes']!=request['hard_world_cap_bytes']
        or parent['completed_tickers']!=len(parent['completed'])
        or parent['build_excluded_tickers']!=len(parent['excluded'])
        or parent['world_gate']!='NOT_PROVEN' or parent['scoring_gate']!='CLOSED'):
        raise ValueError('only the explicitly failed parent part may be replaced')
    provenance=replacement['recovery_provenance']
    stem=f"{bindings['recovery_run']}-1"
    expected_roles={probe['source_release']:'output',provenance['preserved_release']:'output',
        f'compact-world-build-v1-{stem}-000':'output',bindings['replacement']['release']:'output',
        provenance['recovery_inputs_release']:'shared',bindings['probe']['release']:'shared'}
    if (bindings['source_run']!=probe['source_run'] or bindings['source_commit']!=probe['source_commit']
        or bindings['recovery_source_commit']!=replacement['source_commit']
        or bindings['failed_release']!=probe['source_release'] or bindings['plan']!=probe['source_plan']
        or bindings['parent']['release']!=f"compact-world-build-measured-v1-{probe['source_run']}-1"
        or bindings['replacement']['release']!=f'compact-world-build-recovered-part-v1-{stem}-{index:03d}'
        or provenance['preserved_release']!=f'compact-world-build-preserved-v1-{stem}-{index:03d}'
        or provenance['recovery_inputs_release']!=f'compact-world-build-recovery-v1-{stem}-inputs'
        or len(expected_roles)!=6):
        raise ValueError('composition release/input identity differs')
    if (replacement['source_part']!=part or probe['part']!=part
        or replacement['inputs_release']!=parent['inputs_release']
        or replacement['recipe_fingerprint']!=request['corrected_recipe_fingerprint']
        or probe['recipe_fingerprint']!=replacement['recipe_fingerprint']
        or probe['shared_registry_sha256']!=request['registry_sha256']
        or replacement['status']!=COMPLETE or replacement['scoring_gate']!='CLOSED'
        or replacement['world_gate']!=plan['full_world_acceptance']
        or provenance['original_run']!=probe['source_run'] or provenance['original_index']!=index
        or provenance['original_source_commit']!=probe['source_commit']
        or provenance['original_checkpoint']!=probe['source_checkpoint']):
        raise ValueError('replacement provenance or gates differ')
    preserved={r['ticker']:r for r in probe['completed']}
    replacement_rows={r['ticker']:r for r in replacement['completed']}
    for ticker,row in preserved.items():
        if replacement_rows.get(ticker)!=dict(row,release=provenance['preserved_release']):
            raise ValueError('a verified original payload was changed or lost')
    if (provenance['preserved_count']!=len(preserved)
        or provenance['calculated_count']!=len(replacement['completed'])-len(preserved)
        or provenance['remaining_count']!=len(replacement['excluded'])):
        raise ValueError('replacement accounting differs')
    seen=set();extra={'output':0,'shared':0}
    for entry in ledger:
        if (entry['release'] in seen or entry['role'] not in extra
            or type(entry['bytes']) is not int or entry['bytes']<0):
            raise ValueError('duplicate or invalid dependency byte ledger')
        seen.add(entry['release']);extra[entry['role']]+=entry['bytes']
        assets=entry['assets']
        if (len({a['name'] for a in assets})!=len(assets)
            or any(type(a['size']) is not int or a['size']<0 for a in assets)
            or sum(a['size'] for a in assets)!=entry['bytes']
            or hashlib.sha256(encoded(assets)).hexdigest()!=entry['inventory_sha256']):
            raise ValueError('dependency inventory bytes or digest differ')
        if entry['release']!=probe['source_release'] and any(
            a['state']!='uploaded' or not re.fullmatch(r'sha256:[0-9a-f]{64}',str(a['digest'])) for a in assets):
            raise ValueError('new dependency contains an unverified asset')
    if {e['release']:e['role'] for e in ledger}!=expected_roles:
        raise ValueError('dependency ledger is incomplete or has wrong roles')
    if any(type(n) is not int or n<0 for n in (parent_bytes,request_bytes)):
        raise ValueError('invalid receipt/input byte count')
    result=copy.deepcopy(parent)
    result['completed']=[r for r in result['completed'] if r['ticker'] not in affected]+copy.deepcopy(replacement['completed'])
    result['excluded']=[r for r in result['excluded'] if r['ticker'] not in affected]+copy.deepcopy(replacement['excluded'])
    result['shard_errors']=[r for r in result['shard_errors'] if r['index']!=index]
    partition(result['completed'],result['excluded'],all_names)
    result.update(status='PRICE_ANSWER_BUILD_COMPOSED_WITH_FAILED_PART_RECOVERY_NOT_FULL_WORLD',
        completed_tickers=len(result['completed']),build_excluded_tickers=len(result['excluded']),
        completed_percent_original=100*len(result['completed'])/plan['original_universe'],
        above_average_budget_stocks=sum(bool(r.get('over_average_price_budget')) for r in result['completed']),
        legacy_size_exclusions_requiring_recovery=[r['ticker'] for r in result['excluded'] if r.get('reason')=='ANSWER_STORAGE_BUDGET'],
        price_answer_coverage_gate='AT_LEAST_95_PERCENT' if 100*len(result['completed'])>=95*plan['original_universe'] else 'BELOW_95_PERCENT_REQUIRES_ADDON',
        composition=dict(replaced_index=index,original_run=probe['source_run'],preserved_count=len(preserved),
            calculated_count=provenance['calculated_count'],remaining_count=provenance['remaining_count'],
            dependency_byte_ledger=copy.deepcopy(ledger),parent_measured_input_bytes=parent_bytes,
            bound_inputs=copy.deepcopy(bindings),
            published_request_bytes=request_bytes,receipt_bytes=0,
            accounting='PARENT_PLUS_ALL_NEW_RELEASES_AND_RETAINED_FAILED_SOURCE;NO_UNRELATED_PART_RECALCULATED',
            source_values_and_answers='UNCHANGED'))
    # Include this receipt and its published request in the price footprint.
    # PASS/FAIL have equal lengths, so the exact byte-count fixed point cannot
    # oscillate when a boundary changes the storage verdict.
    for _ in range(16):
        output=parent['answer_and_checkpoint_bytes']+extra['output']+request_bytes+result['composition']['receipt_bytes']
        shared=parent['shared_and_bound_input_bytes']+extra['shared']+parent_bytes
        actual=output+shared+plan['raw_dependency_bytes']
        checks=dict(price_reservation=int(output>request['answer_budget_bytes']),
            hard_world_cap=int(actual>request['hard_world_cap_bytes']),
            legacy_size_exclusions=int(bool(result['legacy_size_exclusions_requiring_recovery'])))
        result.update(answer_and_checkpoint_bytes=output,shared_and_bound_input_bytes=shared,
            measured_price_dependency_bytes=actual,composition_storage_failures=checks,
            storage_gate=('FAIL' if any(checks.values()) else 'PASS')+'_PRICE_RESERVATION_ONLY_NOT_WORLD')
        raw=encoded(result)
        if len(raw)==result['composition']['receipt_bytes']:return result,raw
        result['composition']['receipt_bytes']=len(raw)
    raise ValueError('receipt byte accounting did not converge')


def run(root):
    from ci import release_assets as io
    from ci.rebuild_partial_recovery import verify_payload_rows
    request_file=ROOT/'ci/PRICE_RECOVERY_COMPOSITION_REQUEST.json';raw_request=request_file.read_bytes()
    request=json.loads(raw_request)
    if request.get('execute') is not True:raise ValueError('composition is not enabled')
    if request['source_run']==40621517496 or request['failed_release_id']==427402982:
        raise ValueError('protected source forbidden')
    repository=os.environ['GITHUB_REPOSITORY']
    if repository.lower()!='sroyaltyy/checklist-engine':raise ValueError('wrong repository')
    root.mkdir(parents=True,exist_ok=True)
    for run_id,commit in ((request['source_run'],request['source_commit']),
                          (request['recovery_run'],request['recovery_source_commit'])):
        run=json.loads(io.gh_retry('api',f'repos/{repository}/actions/runs/{run_id}'))
        if run['status']!='completed' or run['head_sha']!=commit or run['run_attempt']!=1:
            raise ValueError('producer must be the pinned completed first attempt')
    source=json.loads(io.gh_retry('api',f"repos/{repository}/releases/{request['failed_release_id']}"))
    if source['id']!=request['failed_release_id'] or source['tag_name']!=request['failed_release']:
        raise ValueError('failed release identity differs')
    io._RELEASE_IDS[(repository,source['tag_name'])]=source['id']
    def checked(binding):
        path=io.download_asset(binding['release'],binding['asset'],root/'sources'/binding['release'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=binding['sha256']:
            raise ValueError('bound composition input bytes differ')
        return path
    files={name:checked(request[name]) for name in ('plan','parent','replacement','probe')}
    values={name:json.loads(file.read_bytes()) for name,file in files.items()}
    plan,parent,replacement,probe=(values[n] for n in ('plan','parent','replacement','probe'))
    if (probe['source_run']!=request['source_run'] or probe['source_commit']!=request['source_commit']
        or probe['source_release']!=request['failed_release']
        or probe['source_plan']!=request['plan'] or replacement['source_commit']!=request['recovery_source_commit']):
        raise ValueError('producer binding differs')
    provenance=replacement['recovery_provenance']
    stem=f"{request['recovery_run']}-1"
    output_tags=[request['failed_release'],provenance['preserved_release'],
                 f'compact-world-build-v1-{stem}-000',request['replacement']['release']]
    shared_tags=[provenance['recovery_inputs_release'],request['probe']['release']]
    expected_outputs=set(output_tags);expected_shared=set(shared_tags)
    if len(expected_outputs)!=4 or len(expected_shared)!=2 or expected_outputs&expected_shared:
        raise ValueError('dependency roles overlap')
    inventories={};ledger=[]
    for role,tags in (('output',output_tags),('shared',shared_tags)):
        for tag in tags:
            inventory=io.asset_index(tag);assets=sorted(inventory.values(),key=lambda a:a['name'])
            inventories[tag]=dict(tag_name=tag,assets=assets)
            # Hash stable asset fields, not download counts. Retain/count any
            # unfinished original-source upload without treating it as an answer.
            summary=[{key:a.get(key) for key in ('id','name','size','state','digest')} for a in assets]
            ledger.append(dict(role=role,release=tag,bytes=sum(a['size'] for a in summary),assets=summary,
                inventory_sha256=hashlib.sha256(encoded(summary)).hexdigest()))
    for tag in {r['release'] for r in replacement['completed']}:
        if tag not in expected_outputs:raise ValueError('payload references an uncounted release')
        verify_payload_rows([r for r in replacement['completed'] if r['release']==tag],
                            plan['request']['registry_sha256'],inventories[tag])
    result,raw=compose(plan,parent,replacement,probe,ledger,bindings=request,
                       parent_bytes=files['parent'].stat().st_size,request_bytes=len(raw_request))
    file=root/'COMPACT_WORLD_BUILD_COMPOSED.json';file.write_bytes(raw)
    tag=f"compact-world-build-composed-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    io.gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
        '--notes','Explicit failed-new-part composition. Unrelated answers unchanged; all additional retained release/receipt bytes counted. Price reservation only; full world/scoring unapproved.')
    io.publish_assets(tag,file,request_file);io.gh_retry('release','edit',tag,'--draft=false')
    print('PRICE_RECOVERY_COMPOSED',tag,hashlib.sha256(raw).hexdigest(),result['completed_tickers'],
          result['build_excluded_tickers'],result['storage_gate'],flush=True)
    if result['storage_gate'].startswith('FAIL'):raise ValueError('storage acceptance failed; all values retained and evidence published')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);args=parser.parse_args()
    try:run(Path(args.directory))
    except Exception as exc:
        from ci.release_assets import describe_failure
        print('PRICE_COMPOSITION_FAILURE',describe_failure(exc),flush=True);raise
