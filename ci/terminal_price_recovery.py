"""Append-only terminal recovery; preserve protected producer and draft assets."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

from ci.renko_recipe import BASE_FINGERPRINT,derive,fingerprint
from ci.release_assets import asset_index,download_asset,gh_retry,publish_assets,release_info

REQUEST=Path('ci/TERMINAL_PRICE_RECOVERY_REQUEST.json')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def inventory_fingerprint(inventory):
    rows=sorted((a['name'],a['size'],a['digest'],a['state']) for a in inventory['assets'])
    if len(rows)!=len({r[0] for r in rows}):raise ValueError('duplicate terminal draft asset')
    return sha(json.dumps(rows,separators=(',',':')).encode())


def checked(binding,root):
    file=download_asset(binding['release'],binding['asset'],root)
    if sha(file.read_bytes())!=binding['sha256']:raise ValueError('terminal source pin differs: '+binding['asset'])
    return file


def runtime():
    import importlib.metadata
    packages={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','TA-Lib','exchange_calendars')}
    return dict(python=platform.python_version(),machine=platform.machine(),packages=packages)


def verify_code(request):
    if set(request['compute_sha256'])!={'ci/compact_world_build.py','ci/compact_world_storage_budget.py','world_answer_cache.py','ci/renko_recipe.py'}:
        raise ValueError('terminal compute pins incomplete')
    for name,expected in request['compute_sha256'].items():
        if sha(Path(name).read_bytes())!=expected:raise ValueError('terminal compute code changed: '+name)


def make_plan(original,measured,checkpoint,inventory,timeout,proof,request):
    """Pure membership/provenance proof before publication or scheduling."""
    wanted=[r['ticker'] for r in measured['excluded']]
    if (measured['status']!='PRICE_ANSWER_BUILD_MEASURED_NOT_FULL_WORLD'
            or measured['inputs_release']!=request['base_plan']['release']
            or len(wanted)!=55 or len(set(wanted))!=55
            or len(measured['completed'])!=8261 or measured['completed_tickers']!=8261
            or measured['build_excluded_tickers']!=55):raise ValueError('terminal original measured membership differs')
    timeouts={r['ticker'] for r in measured['excluded'] if r['reason']=='STOCK_TIMEOUT'}
    unverified={r['ticker'] for r in measured['excluded'] if r['reason']=='SHARD_RESULT_UNVERIFIED'}
    if timeouts!={'EQLT','WKSP','ABVC','NXTS','SU'} or len(unverified)!=50:
        raise ValueError('terminal omission classes differ')
    index=request['failed_index'];part=original['parts'][index]
    if set(part['tickers'])!=unverified or original['request']['corrected_recipe_fingerprint']!=BASE_FINGERPRINT:
        raise ValueError('terminal failed original part differs')
    if (inventory['id']!=request['draft_release_id'] or not inventory['draft']
            or inventory['tag_name']!=request['draft_tag'] or inventory['target_commitish']!=request['base_producer']
            or inventory_fingerprint(inventory)!=request['draft_inventory_sha256']):
        raise ValueError('terminal draft inventory changed')
    if (checkpoint['status']!='BUILDING_PRICE_ANSWER_STAGE_NOT_FULL_WORLD'
            or checkpoint['source_part']!=part or checkpoint['source_commit']!=request['base_producer']
            or checkpoint['inputs_release']!=request['base_plan']['release']
            or checkpoint['recipe_fingerprint']!=BASE_FINGERPRINT or checkpoint['excluded']
            or len(checkpoint['completed'])!=24):raise ValueError('terminal checkpoint provenance differs')
    assets={a['name']:a for a in inventory['assets']};reused=[]
    for row in checkpoint['completed']:
        asset=assets.get(row['asset'],{})
        if (row['ticker'] not in unverified or row['release']!=request['draft_tag']
                or row['asset']!=row['ticker'].encode().hex()+'.diagnostic_answers.tar.zst'
                or asset.get('digest')!='sha256:'+row['answer_container_sha256']
                or asset.get('size')!=row['answer_container_bytes'] or asset.get('state')!='uploaded'
                or row['diagnostic_questions']!=68904 or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'
                or row['shared_registry_sha256']!=original['request']['registry_sha256']):
            raise ValueError('terminal checkpoint payload binding differs')
        reused.append(dict(row,recipe_fingerprint=BASE_FINGERPRINT,origin_release=row['release'],origin_kind='EXACT_DRAFT_CHECKPOINT_COPY'))
    reused_names=[r['ticker'] for r in reused]
    if len(set(reused_names))!=24 or {a for a in assets if a.endswith('.diagnostic_answers.tar.zst')}!={r['asset'] for r in reused}:
        raise ValueError('terminal duplicate or orphan checkpoint payload')
    if checkpoint['answer_bytes']!=sum(r['answer_container_bytes'] for r in reused):raise ValueError('terminal checkpoint byte total differs')
    if (timeout['status']!='TIMEOUT_ADDON_INCOMPLETE' or timeout['completed'] or timeout['errors']
            or len(timeout['excluded'])!=5 or {r['ticker'] for r in timeout['excluded']}!=timeouts
            or any(r['reason']!='STOCK_TIMEOUT' for r in timeout['excluded'])):
        raise ValueError('terminal old timeout run not fully accounted')
    if (proof['status']!='RENKO_GUARD_SAMPLE_EXACT_WITH_NEW_TARGET_ONLY' or proof['errors']
            or proof['candidate_fingerprint']!=request['candidate_fingerprint']
            or proof['base_fingerprint']!=BASE_FINGERPRINT or len(proof['results'])!=9
            or proof['original_reference_numeric_cells']!=51008796):raise ValueError('terminal guard proof not accepted')
    eqlt=proof['guarded_answer_result']['samples']
    if (len(eqlt)!=1 or eqlt[0]['ticker']!='EQLT' or eqlt[0]['query_rows']!=1712 or eqlt[0]['diagnostic_questions']!=68904
            or eqlt[0]['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
        raise ValueError('terminal existing EQLT result differs')
    eqlt=copy.deepcopy(eqlt[0]);eqlt.update(release=request['guard_proof']['release'],asset='45514c54.diagnostic_answers.tar.zst',
        shared_registry_sha256=original['request']['registry_sha256'],recipe_fingerprint=request['candidate_fingerprint'],
        origin_kind='EXISTING_VERIFIED_GUARDED_SAMPLE')
    reused.append(eqlt);fresh=set(wanted)-{r['ticker'] for r in reused};parts=[]
    for old in original['parts']:
        selected=[t for t in old['tickers'] if t in fresh]
        for start in range(0,len(selected),5):
            own=copy.deepcopy(old);own['tickers']=selected[start:start+5];parts.append(own)
    scheduled=[t for p in parts for t in p['tickers']]
    all_names=[r['ticker'] for r in reused]+scheduled
    if (len(scheduled)!=30 or len(set(scheduled))!=30 or len(all_names)!=55
            or len(set(all_names))!=55 or set(all_names)!=set(wanted)):
        raise ValueError('terminal recovery must reuse25 and compute exactly the other30')
    bound=copy.deepcopy(original['request']);bound.update(corrected_recipe_fingerprint=request['candidate_fingerprint'],shard_budget_seconds=5400)
    return dict(request=bound,parts=parts,reused=reused,expected_tickers=sorted(wanted),recovery_request=request,
                original_universe=8727,source_stitch_sha256=original['source_stitch_sha256'],
                price_answer_per_ticker_limit=original['price_answer_per_ticker_limit'],
                per_ticker_budget_policy='DIAGNOSTIC_AVERAGE_ONLY_NEVER_EXCLUDE_FOR_SIZE',
                full_world_acceptance='TERMINAL_PRICE_RECOVERY_ONLY_NOT_WORLD',scoring_gate='CLOSED')


def prepare(root,request):
    verify_code(request);root.mkdir(parents=True,exist_ok=True)
    repository=os.environ['GITHUB_REPOSITORY']
    for run,producer in ((40621517496,request['base_producer']),(40792865480,request['timeout_producer'])):
        state=json.loads(gh_retry('api',f'repos/{repository}/actions/runs/{run}'))
        if state['status']!='completed' or state['head_sha']!=producer or state['run_attempt']!=1:
            raise ValueError('recovery source run is not the bound terminal attempt')
    docs={key:json.loads(checked(request[key],root/'sources').read_text(encoding='utf-8'))
          for key in ('base_plan','base_measurement','timeout_measurement','guard_proof')}
    inventory=release_info(request['draft_tag'])
    checkpoint_file=checked(dict(release=request['draft_tag'],asset='checkpoint_0024.json',sha256=request['checkpoint_sha256']),root/'sources')
    plan=make_plan(docs['base_plan'],docs['base_measurement'],json.loads(checkpoint_file.read_text()),inventory,docs['timeout_measurement'],docs['guard_proof'],request)
    plan['runtime']=runtime();sources={}
    if {key:plan['runtime']['packages'][key] for key in docs['guard_proof']['runtime']}!=docs['guard_proof']['runtime']:
        raise ValueError('terminal runtime differs from exact guard sample')
    for part in plan['parts']:
        key=(part['release'],part['part'])
        if key in sources:continue
        asset=asset_index(part['release'])[part['part']+'.json']
        if not asset['digest'].startswith('sha256:'):raise ValueError('terminal raw manifest pin missing')
        sources[key]=dict(release=part['release'],asset=asset['name'],sha256=asset['digest'][7:])
    plan['raw_manifests']=list(sources.values())
    registry=checked(dict(release=request['base_plan']['release'],asset='DIAGNOSTIC_REGISTRIES.json',sha256=plan['request']['registry_sha256']),root)
    copies=[];tag=f"terminal-price-recovery-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    for row in plan['reused']:
        if row['origin_kind']!='EXACT_DRAFT_CHECKPOINT_COPY':continue
        copies.append(checked(dict(release=row['release'],asset=row['asset'],sha256=row['answer_container_sha256']),root/'retained'))
        row['release']=tag
    existing=next(r for r in plan['reused'] if r['ticker']=='EQLT')
    asset=asset_index(existing['release'])[existing['asset']]
    if asset['digest']!='sha256:'+existing['answer_container_sha256'] or asset['size']!=existing['answer_container_bytes']:
        raise ValueError('terminal existing EQLT public payload changed')
    evidence=root/'SOURCE_DRAFT_INVENTORY_V1.json'
    evidence.write_text(json.dumps(dict(id=inventory['id'],tag_name=inventory['tag_name'],draft=inventory['draft'],target_commitish=inventory['target_commitish'],
                                       assets=[{key:a[key] for key in ('name','size','digest','state')} for a in inventory['assets']]),indent=2)+'\n',encoding='utf-8')
    file=root/'COMPACT_WORLD_BUILD_PLAN.json';file.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','New immutable recovery plan plus exact copies of24 completed draft payloads. Protected source draft/run unchanged;25 reused and only30 new calculations.')
    publish_assets(tag,file,registry,checkpoint_file,evidence,REQUEST,*copies);gh_retry('release','edit',tag,'--draft=false')
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
        stream.write('matrix='+json.dumps(list(range(len(plan['parts']))))+'\ninputs_release='+tag+'\nplan_sha256='+sha(file.read_bytes())+'\n')
    print('TERMINAL_RECOVERY_PREPARED',tag,len(plan['reused']),sum(len(p['tickers']) for p in plan['parts']),flush=True)


def build(root,inputs_release,index,expected):
    from ci import compact_world_build as base
    file=checked(dict(release=inputs_release,asset='COMPACT_WORLD_BUILD_PLAN.json',sha256=expected),root)
    plan=json.loads(file.read_text());verify_code(plan['recovery_request'])
    if runtime()!=plan['runtime']:raise ValueError('terminal runtime package/platform identity differs')
    part=plan['parts'][index]
    binding=next(r for r in plan['raw_manifests'] if r['release']==part['release'] and r['asset']==part['part']+'.json')
    checked(binding,root/'source')
    original_snapshot=base.snapshot
    def guarded_snapshot(directory,request):
        old=dict(request,corrected_recipe_fingerprint=BASE_FINGERPRINT)
        recipe,calendar=original_snapshot(directory,old)
        inputs=json.loads((directory/'BUILD_INPUTS.json').read_text())
        files={name:(recipe/name).read_bytes() for name in inputs['recipe_files']};candidate=derive(files)
        if fingerprint(candidate)!=request['corrected_recipe_fingerprint']:raise ValueError('terminal candidate identity differs')
        for name,raw in candidate.items():(recipe/name).write_bytes(raw)
        return recipe,calendar
    # Only this disposable CLI parent is adapted. Every math worker starts clean.
    try:
        base.snapshot=guarded_snapshot;base.build(root,inputs_release,index)
    finally:base.snapshot=original_snapshot


def compose(base,addon,full,recovered,request):
    rows=[dict(r,recipe_fingerprint=BASE_FINGERPRINT) for r in base['completed']+addon['completed']]+recovered
    tickers=[r['ticker'] for r in rows];source_names=[t for p in full['parts'] for t in p['tickers']]
    if (addon['status']!='RAW_INCREMENTAL_PRICE_ANSWERS_COMPLETE_NOT_WORLD' or addon['errors'] or addon['excluded']
            or len(base['completed'])!=8261 or len(addon['completed'])!=131 or len(recovered)!=55
            or len(tickers)!=len(set(tickers)) or len(tickers)!=8447 or set(tickers)!=set(source_names)
            or len(source_names)!=8447 or sum(r['query_rows'] for r in rows)!=12560808):
        raise ValueError('terminal complete price composition differs')
    return dict(status='FULL_RAW_NAME_PRICE_DIAGNOSTIC_COMPOSITION_ONLY',original_universe=8727,
                completed_tickers=8447,completed_percent_original=100*8447/8727,query_stock_days=12560808,
                source_excluded_names=280,completed=rows,source_reports=request,
                mixed_version_rule='Existing published bits retained; new values use the separately proved guard. No original result is rewritten.',
                full_world_gate='NOT_PROVEN',full_question_gate='NOT_PROVEN',historical_tradeability_gate='NOT_PROVEN',
                comprehensive_leak_gate='NOT_PROVEN',portable_exact_recomputation_gate='NOT_PROVEN',full_dependency_budget_gate='NOT_PROVEN',scoring_gate='CLOSED')


def finalize(root,inputs_release,expected):
    from ci.compact_world_build import validate_shard
    root.mkdir(parents=True,exist_ok=True)
    file=checked(dict(release=inputs_release,asset='COMPACT_WORLD_BUILD_PLAN.json',sha256=expected),root)
    plan=json.loads(file.read_text());done=copy.deepcopy(plan['reused']);excluded=[];errors=[];receipts=[]
    for row in done:
        asset=asset_index(row['release'])[row['asset']]
        if asset['digest']!='sha256:'+row['answer_container_sha256'] or asset['size']!=row['answer_container_bytes']:
            raise ValueError('terminal reused output differs')
    for index,part in enumerate(plan['parts']):
        tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
        try:
            file=download_asset(tag,'COMPACT_WORLD_SHARD.json',root/str(index));raw=file.read_bytes();state=json.loads(raw)
            validate_shard(state,part)
            if (state['source_commit']!=os.environ['GITHUB_SHA'] or state['inputs_release']!=inputs_release
                    or state['recipe_fingerprint']!=plan['request']['corrected_recipe_fingerprint']
                    or state['status']!='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'):
                raise ValueError('terminal output provenance differs')
            inventory=asset_index(tag);validated=[]
            for row in state['completed']:
                asset=inventory[row['asset']]
                if (row['release']!=tag or row['asset']!=row['ticker'].encode().hex()+'.diagnostic_answers.tar.zst'
                        or asset['digest']!='sha256:'+row['answer_container_sha256'] or asset['size']!=row['answer_container_bytes']
                        or row['diagnostic_questions']!=68904 or row['shared_registry_sha256']!=plan['request']['registry_sha256']
                        or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
                    raise ValueError('terminal answer/schema binding differs')
                validated.append(dict(row,recipe_fingerprint=state['recipe_fingerprint'],origin_kind='NEW_GUARDED_TERMINAL_CALCULATION'))
            done.extend(validated);excluded.extend(state['excluded']);receipts.append(dict(index=index,release=tag,sha256=sha(raw)))
        except Exception as exc:errors.append(dict(index=index,tickers=part['tickers'],error=str(exc)[-2000:]))
    names=[r['ticker'] for r in done+excluded]+[t for e in errors for t in e['tickers']]
    if len(names)!=len(set(names)) or set(names)!=set(plan['expected_tickers']):raise ValueError('terminal final accounting differs')
    complete=not excluded and not errors and len(done)==55
    report=dict(status='TERMINAL_PRICE_55_RECOVERED_NOT_WORLD' if complete else 'TERMINAL_PRICE_RECOVERY_INCOMPLETE',
                source_commit=os.environ['GITHUB_SHA'],inputs_release=inputs_release,plan_sha256=expected,
                request=plan['recovery_request'],completed=done,excluded=excluded,errors=errors,releases=receipts,
                protected_run_untouched=40621517496,source_draft_untouched=plan['recovery_request']['draft_release_id'],
                reused_draft_payloads=24,reused_guarded_sample=1,new_calculations=30,
                portable_exact_recomputation_gate='NOT_PROVEN',full_world_gate='NOT_PROVEN',full_dependency_budget_gate='NOT_PROVEN',scoring_gate='CLOSED')
    file=root/'TERMINAL_PRICE_RECOVERY_MEASURED_V1.json';outputs=[file]
    if complete:
        try:
            req=plan['recovery_request'];base=json.loads(checked(req['base_measurement'],root/'sources').read_text())
            addon=json.loads(checked(req['raw_addon'],root/'sources').read_text());full=json.loads(checked(req['full_raw_source'],root/'sources').read_text())
            composed=compose(base,addon,full,done,req)
            own=root/'COMPOSED_PRICE_DIAGNOSTIC_V1.json';own.write_text(json.dumps(composed,indent=2)+'\n',encoding='utf-8');outputs.append(own)
        except Exception as exc:
            errors.append(dict(stage='composition',error=str(exc)[-2000:]));complete=False;report['status']='TERMINAL_PRICE_RECOVERY_INCOMPLETE'
    file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"terminal-price-recovery-measured-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA']);publish_assets(tag,*outputs);gh_retry('release','edit',tag,'--draft=false')
    print('TERMINAL_RECOVERY_MEASURED',len(done),len(excluded),len(errors),flush=True)
    if not complete:raise ValueError('terminal recovery incomplete; original artifacts unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('prepare','build','finalize'))
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--inputs-release');parser.add_argument('--index',type=int);parser.add_argument('--plan-sha256')
    args=parser.parse_args()
    if args.operation=='prepare':prepare(args.directory,json.loads(REQUEST.read_text()))
    elif args.operation=='build':build(args.directory,args.inputs_release,args.index,args.plan_sha256)
    else:finalize(args.directory,args.inputs_release,args.plan_sha256)
