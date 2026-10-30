"""Full accepted-universe compact build, checkpointed with per-stock isolation.

This launches real production-sized price work; nonprice/comparison joins and
the complete v3 quality/leak gates remain explicit, separate prerequisites.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from ci.native_price_blocks import read_member, sha, write_json
from ci.release_assets import asset_index, download_asset, gh_retry, publish_assets, describe_failure
from ci.renko_recipe import BASE_COMMIT, BASE_FINGERPRINT, derive as derive_renko_recipe, fingerprint as recipe_fingerprint

REQUEST=Path('ci/COMPACT_WORLD_BUILD_REQUEST.json')


def complete_input_parts(status, full, binding):
    """Extend the original source without replacing any original part/name."""
    def indexed(parts):
        result={};names=[]
        for part in parts:
            key=(part['release'],part['part'])
            if key in result:raise ValueError('duplicate release-aware input part')
            result[key]=part;names.extend(part['tickers'])
        if len(names)!=len(set(names)):raise ValueError('duplicate input ticker')
        return result,set(names)
    old,old_names=indexed(status['parts']);new,new_names=indexed(full['parts'])
    if (full['status']!='FULL_ACCEPTED_PRICE_BASE_ONLY_NOT_WORLD' or full['inputs_tag']!=status['inputs_tag']
        or full['selected_tickers']!=binding['expected_tickers'] or len(new_names)!=full['selected_tickers']
        or len(old_names)!=status['accepted_tickers'] or len(new_names-old_names)!=binding['expected_incremental_tickers']
        or not old_names<=new_names or any(new.get(key)!=part for key,part in old.items())
        or full['query_rows']!=binding['expected_stock_days']
        or full['stock_day_weights_sha256']!=binding['stock_day_weights_sha256']):
        raise ValueError('full input extension replaces or loses a source binding')
    return full['parts'],sorted(new_names-old_names)


def limited_process(command, directory, seconds):
    """Kill/reap one stock; always return a bounded log and explicit outcome."""
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'worker.log').open('wb') as stream:
        with subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT) as child:
            try:
                code=child.wait(timeout=seconds);reason=None if code==0 else 'STOCK_PROCESS_ERROR'
            except subprocess.TimeoutExpired:
                child.kill();child.wait();code=child.returncode;reason='STOCK_TIMEOUT'
    with (directory/'worker.log').open('rb') as stream:
        stream.seek(max(0,stream.seek(0,2)-4000));tail=stream.read().decode(errors='replace')
    return dict(returncode=code,reason=reason,log_tail=tail)


def prepare(root,request):
    root.mkdir(parents=True,exist_ok=True)
    status_file=download_asset(request['accepted_price_release'],'ACCEPTED_PRICE_STITCH.json',root)
    if request.get('accepted_price_stitch_sha256') and sha(status_file)!=request['accepted_price_stitch_sha256']:
        raise ValueError('original accepted-price source changed')
    status=json.loads(status_file.read_text())
    if (status['status']!='ACCEPTED_PRICE_BASE_WITH_LOGGED_EXCLUSIONS_NOT_WORLD'
        or status['original_universe']!=8727 or 100*status['accepted_tickers']/8727<95
        or status['accepted_tickers']+status['excluded_tickers']!=8727
        or status['accepted_percent']<95 or status['inputs_sha256']!=request['inputs_sha256']):
        raise ValueError('accepted new-price stitch is not ready')
    parts=status['parts'];accepted=status['accepted_tickers'];source_excluded=status['excluded_tickers'];extension={};extra_files=[]
    if request.get('full_raw_source'):
        binding=request['full_raw_source']
        file=download_asset(binding['release'],binding['asset'],root)
        if sha(file)!=binding['sha256']:raise ValueError('full raw input source changed')
        full=json.loads(file.read_text());parts,added=complete_input_parts(status,full,binding)
        accepted=full['selected_tickers'];source_excluded=status['original_universe']-accepted
        extension=dict(source=binding,incremental_tickers=added,incremental_count=len(added),base_parts_preserved=len(status['parts']))
        extra_files.append(file)
    timeout_dispositions=[]
    if request.get('prior_timeout_ledger'):
        binding=request['prior_timeout_ledger'];file=download_asset(binding['release'],binding['asset'],root)
        if sha(file)!=binding['sha256']:raise ValueError('prior timeout ledger changed')
        ledger=json.loads(file.read_text());names=[r['ticker'] for r in ledger['excluded']]
        if (ledger['status']!='TIMEOUT_ADDON_INCOMPLETE' or ledger['completed'] or ledger['errors']
            or len(names)!=len(set(names)) or set(names)!=set(binding['tickers'])
            or any(r['reason']!='STOCK_TIMEOUT' for r in ledger['excluded'])
            or not set(names)<={t for p in parts for t in p['tickers']}
            or request.get('recipe_transform')!='RENKO_ZERO_STEP_V1'):
            raise ValueError('prior timeout ledger is not fully covered by guarded inputs')
        timeout_dispositions=[dict(ticker=t,prior_reason='STOCK_TIMEOUT',disposition='GUARDED_RECIPE_RETRY_WITH_BOUNDED_WORKER') for t in sorted(names)]
        extra_files.append(file)
    if not 0<len(parts)<=256:raise ValueError('matrix must fit the Actions 256-job bound')
    inventories={};source_bytes=0
    for part in parts:
        if part['release'] not in inventories:inventories[part['release']]=asset_index(part['release'])
        item=inventories[part['release']][part['part']+'.tar']
        if item['digest']!='sha256:'+part['archive_sha256']:raise ValueError('raw source asset changed')
        source_bytes+=sum(inventories[part['release']][part['part']+suffix]['size']
                          for suffix in ('.tar','.json','.coverage.csv','.stock_days.csv'))
    if source_bytes>request['raw_source_budget_bytes']:raise ValueError('raw dependency closure exceeds reserved cap')
    # Reuse the exact measured shared registry, not an extra sample computation.
    raw=subprocess.check_output(['gh','api',f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/artifacts/{request['registry_artifact_id']}/zip"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        registry=archive.read('DIAGNOSTIC_REGISTRIES.json')
    if hashlib.sha256(registry).hexdigest()!=request['registry_sha256']:raise ValueError('shared registry changed')
    registry_file=root/'DIAGNOSTIC_REGISTRIES.json';registry_file.write_bytes(registry)
    recipe,calendar=snapshot(root/'bound-inputs',request)
    bound_input_bytes=sum(p.stat().st_size for p in recipe.rglob('*') if p.is_file())
    bound_input_bytes+=calendar.stat().st_size+(root/'bound-inputs'/'BUILD_INPUTS.json').stat().st_size
    plan=dict(request=request,source_stitch_sha256=sha(status_file),parts=parts,
              accepted_tickers=accepted,original_universe=status['original_universe'],
              source_excluded_tickers=source_excluded,raw_dependency_bytes=source_bytes,
              source_input_extension=extension,prior_timeout_dispositions=timeout_dispositions,
              shared_registry_bytes=len(registry),bound_input_bytes=bound_input_bytes,
              price_answer_per_ticker_limit=request['answer_budget_bytes']//status['original_universe'],
              per_ticker_budget_policy='DIAGNOSTIC_AVERAGE_ONLY_NEVER_EXCLUDE_FOR_SIZE',
              full_world_acceptance='NOT_PROVEN_NONPRICE_AND_COMPLETE_QUESTION_TREE_REQUIRED',scoring_gate='CLOSED')
    file=root/'COMPACT_WORLD_BUILD_PLAN.json';write_json(file,plan)
    tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','Owner-authorized full accepted-universe compact price-answer stage. Remaining world coverage is explicit.')
    publish_assets(tag,file,registry_file,status_file,REQUEST,*extra_files);gh_retry('release','edit',tag,'--draft=false')
    with open(os.environ['GITHUB_OUTPUT'],'a') as stream:
        stream.write('matrix='+json.dumps(list(range(len(parts))))+'\ninputs_release='+tag+'\n')
    print('COMPACT_WORLD_STARTED',tag,len(parts),accepted,flush=True)


def snapshot(root,request):
    inputs=json.loads(download_asset(request['inputs_tag'],'BUILD_INPUTS.json',root).read_text())
    if sha(root/'BUILD_INPUTS.json')!=request['inputs_sha256']:raise ValueError('frozen input digest differs')
    calendar=download_asset(request['inputs_tag'],'market_sessions.parquet',root)
    if sha(calendar)!=inputs['calendar_sha256']:raise ValueError('calendar differs')
    recipe=root/'recipe';files={}
    subprocess.run(['git','fetch','--depth=1','origin',request['corrected_commit']],check=True)
    for name in inputs['recipe_files']:
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('unsafe recipe path')
        raw=subprocess.check_output(['git','show',request['corrected_commit']+':'+name])
        files[name]=raw
    transform=request.get('recipe_transform')
    if transform is not None:
        if (transform!='RENKO_ZERO_STEP_V1' or request['corrected_commit']!=BASE_COMMIT
            or request.get('source_recipe_fingerprint')!=BASE_FINGERPRINT):
            raise ValueError('unknown or unbound recipe transform')
        files=derive_renko_recipe(files)
    if recipe_fingerprint(files)!=request['corrected_recipe_fingerprint']:
        raise ValueError('versioned math snapshot differs')
    for name,raw in files.items():
        file=recipe/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
    return recipe,calendar


def validate_shard(state,part):
    done=[r['ticker'] for r in state['completed']];excluded=[r['ticker'] for r in state['excluded']]
    if (state['source_part']!=part or len(done+excluded)!=len(set(done+excluded))
        or set(done+excluded)!=set(part['tickers'])):
        raise ValueError('shard completion/exclusion membership differs')
    return done


def build(root,inputs_release,index):
    root.mkdir(parents=True,exist_ok=True)
    plan=json.loads(download_asset(inputs_release,'COMPACT_WORLD_BUILD_PLAN.json',root).read_text())
    request=plan['request'];part=plan['parts'][index]
    recipe,calendar=snapshot(root,request)
    file=download_asset(part['release'],part['part']+'.json',root/'source');manifest=json.loads(file.read_text())
    if manifest['archive_sha256']!=part['archive_sha256'] or manifest['inputs_tag']!=request['inputs_tag']:
        raise ValueError('source part manifest differs')
    archive=download_asset(part['release'],part['part']+'.tar',root/'source')
    if sha(archive)!=part['archive_sha256']:raise ValueError('raw source archive differs')
    tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
    state=dict(status='BUILDING_PRICE_ANSWER_STAGE_NOT_FULL_WORLD',source_part=part,inputs_release=inputs_release,
        source_commit=os.environ['GITHUB_SHA'],recipe_fingerprint=request['corrected_recipe_fingerprint'],
        completed=[],excluded=[],answer_bytes=0,world_gate=plan['full_world_acceptance'],scoring_gate='CLOSED')
    state_file=root/'COMPACT_WORLD_SHARD.json';created=False;started=time.monotonic()
    for ticker in part['tickers']:
        own=root/'stocks'/ticker.encode().hex();own.mkdir(parents=True,exist_ok=True)
        reason=None;detail={}
        try:
            if time.monotonic()-started>request['shard_budget_seconds']-request['stock_timeout_seconds']:
                reason='SHARD_WALL_BUDGET';raise RuntimeError('remaining names excluded, durable checkpoints preserved')
            name=ticker.encode().hex()+'.bars.parquet';raw=read_member(archive,manifest,name);(own/name).write_bytes(raw)
            shutil.copyfile(calendar,own/'market_sessions.parquet')
            write_json(own/'PROBE_INPUTS.json',dict(samples=[dict(ticker=ticker,file=name,sha256=hashlib.sha256(raw).hexdigest())],
                inputs_sha256=request['inputs_sha256'],recipe_fingerprint=request['corrected_recipe_fingerprint'],
                restrict_query_to_source_sessions=True))
            detail=limited_process([sys.executable,'-m','ci.compact_world_storage_budget','--directory',str(own.resolve()),
                '--worker','--recipe',str(recipe.resolve())],own,request['stock_timeout_seconds'])
            if detail['reason']:reason=detail['reason'];raise RuntimeError(detail['log_tail'])
            if sha(own/'DIAGNOSTIC_REGISTRIES.json')!=request['registry_sha256']:
                reason='REGISTERED_SCHEMA_MISMATCH';raise ValueError('stock schema differs from shared registered question tree')
            measured=json.loads((own/'COMPACT_STORAGE_WORKER.json').read_text());row=measured['samples'][0]
            payload=own/(ticker.encode().hex()+'.diagnostic_answers.tar.zst')
            row['over_average_price_budget']=payload.stat().st_size+4096>plan['price_answer_per_ticker_limit']
            if row['over_average_price_budget']:
                print('COMPACT_WORLD_STOCK_ABOVE_AVERAGE_BUDGET_RETAINED',ticker,payload.stat().st_size,flush=True)
            if not created:
                gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
                    '--notes','Immutable compact answer checkpoints; excluded stocks logged; not full-world/PIT approval.');created=True
            publish_assets(tag,payload)
            row.update(release=tag,asset=payload.name,peak_rss_bytes=measured['peak_rss_bytes'],
                       shared_registry_sha256=request['registry_sha256'])
            state['completed'].append(row);state['answer_bytes']+=payload.stat().st_size
            print('COMPACT_WORLD_STOCK_COMPLETE',ticker,row['seconds'],payload.stat().st_size,flush=True)
        except Exception as exc:
            state['excluded'].append(dict(ticker=ticker,reason=reason or 'STOCK_ERROR',error=describe_failure(exc)[-4000:]))
            print('COMPACT_WORLD_STOCK_EXCLUDED',ticker,reason or 'STOCK_ERROR',flush=True)
        write_json(state_file,state)
        # Unique snapshots make every completed stock durable without overwrites.
        if not created:
            gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA']);created=True
        checkpoint=root/f"checkpoint_{len(state['completed'])+len(state['excluded']):04d}.json"
        write_json(checkpoint,state);publish_assets(tag,checkpoint)
        # Only delete this stock's generated local files; raw source remains once.
        for file in own.iterdir():
            if file.is_file():file.unlink()
        own.rmdir()
    archive.unlink();state['status']='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'
    write_json(state_file,state);publish_assets(tag,state_file);gh_retry('release','edit',tag,'--draft=false')
    print('COMPACT_WORLD_SHARD_COMPLETE',tag,len(state['completed']),len(state['excluded']),flush=True)


def merge(root,inputs_release):
    root.mkdir(parents=True,exist_ok=True)
    plan=json.loads(download_asset(inputs_release,'COMPACT_WORLD_BUILD_PLAN.json',root).read_text())
    request=plan['request'];completed=[];excluded=[];errors=[];output_bytes=0
    for index,part in enumerate(plan['parts']):
        tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
        try:
            state=json.loads(download_asset(tag,'COMPACT_WORLD_SHARD.json',root/str(index)).read_text())
            validate_shard(state,part)
            if (state['recipe_fingerprint']!=request['corrected_recipe_fingerprint'] or state['inputs_release']!=inputs_release
                or state['status']!='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'):
                raise ValueError('shard recipe/input/status differs')
            inventory=asset_index(tag)
            for row in state['completed']:
                asset=inventory[row['asset']]
                if (asset['digest']!='sha256:'+row['answer_container_sha256']
                    or asset['size']!=row['answer_container_bytes']
                    or row['shared_registry_sha256']!=request['registry_sha256']):
                    raise ValueError('published answer or registry digest differs')
            output_bytes+=sum(a['size'] for a in inventory.values())
            completed.extend(state['completed']);excluded.extend(state['excluded'])
        except Exception as exc:
            errors.append(dict(index=index,release=tag,error=describe_failure(exc)))
            excluded.extend(dict(ticker=t,reason='SHARD_RESULT_UNVERIFIED',error=describe_failure(exc)) for t in part['tickers'])
    names=[r['ticker'] for r in completed+excluded]
    if len(names)!=len(set(names)) or len(names)!=plan['accepted_tickers']:
        raise ValueError('global build completion/exclusion membership differs')
    shared_input_bytes=sum(a['size'] for a in asset_index(inputs_release).values())+plan['bound_input_bytes']
    actual_bytes=output_bytes+plan['raw_dependency_bytes']+shared_input_bytes
    within_budget=output_bytes<=request['answer_budget_bytes'] and actual_bytes<=request['hard_world_cap_bytes']
    legacy_size_exclusions=[row['ticker'] for row in excluded if row.get('reason')=='ANSWER_STORAGE_BUDGET']
    storage_gate=('FAIL_LEGACY_SIZE_EXCLUSIONS_REQUIRE_RECOVERY' if legacy_size_exclusions else
                  'PASS_PRICE_RESERVATION_ONLY_NOT_WORLD' if within_budget else 'FAIL_RETAIN_VALUES_IMPROVE_LOSSLESS_ENCODING')
    result=dict(status='PRICE_ANSWER_BUILD_MEASURED_NOT_FULL_WORLD',inputs_release=inputs_release,
        original_universe=plan['original_universe'],source_excluded_tickers=plan['source_excluded_tickers'],
        completed_tickers=len(completed),build_excluded_tickers=len(excluded),
        completed_percent_original=100*len(completed)/plan['original_universe'],
        answer_and_checkpoint_bytes=output_bytes,raw_dependency_bytes=plan['raw_dependency_bytes'],
        shared_registry_bytes=plan['shared_registry_bytes'],shared_and_bound_input_bytes=shared_input_bytes,
        measured_price_dependency_bytes=actual_bytes,
        price_reservation_bytes=request['answer_budget_bytes'],hard_world_cap_bytes=request['hard_world_cap_bytes'],
        storage_gate=storage_gate,legacy_size_exclusions_requiring_recovery=legacy_size_exclusions,
        price_answer_coverage_gate='AT_LEAST_95_PERCENT' if 100*len(completed)/plan['original_universe']>=95 else 'BELOW_95_PERCENT_REQUIRES_ADDON',
        above_average_budget_stocks=sum(bool(row.get('over_average_price_budget')) for row in completed),
        size_exclusion_policy='NO_STOCK_OR_COLUMN_EXCLUDED_TO_MEET_STORAGE_CAP',
        completed=completed,excluded=excluded,shard_errors=errors,
        remaining=['all nonprice/comparator question families','complete v3 quality gate','comprehensive leak proof','historical PIT eligibility',
                   'lossless numeric/intermediate-value retention and complete world dependency budget'],
        world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    file=root/'COMPACT_WORLD_BUILD_MEASURED.json';write_json(file,result)
    tag=f"compact-world-build-measured-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    print('COMPACT_WORLD_MEASURED',len(completed),len(excluded),actual_bytes,flush=True)
    if not within_budget or legacy_size_exclusions:
        raise ValueError('storage acceptance failed; full evidence published and all completed values retained; size exclusions require add-on recovery')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('prepare','build','merge'))
    parser.add_argument('--directory',required=True);parser.add_argument('--inputs-release');parser.add_argument('--index',type=int)
    args=parser.parse_args()
    if args.operation=='prepare':prepare(Path(args.directory),json.loads(REQUEST.read_text()))
    elif args.operation=='build':build(Path(args.directory),args.inputs_release,args.index)
    else:merge(Path(args.directory),args.inputs_release)
