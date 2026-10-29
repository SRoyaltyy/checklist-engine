"""Recover only audited terminal omissions in a separate immutable run.

The protected producer and checkpoint ledger are never changed or resumed.
The adapter delegates computation to the existing exact worker and adds only
periodic diagnostic traces and a larger wall-clock allowance.
"""
import argparse
import copy
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

from ci.release_assets import asset_index, download_asset, gh_retry, publish_assets

REQUEST=Path('ci/PRICE_TIMEOUT_ADDON_REQUEST.json')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def make_plan(original,audit,request):
    if (audit['producer_commit']!=request['base_producer']
            or audit['inputs_release']!=request['base_inputs_release']
            or audit['plan_sha256']!=request['base_plan_sha256']
            or audit['recipe_fingerprint']!=original['request']['corrected_recipe_fingerprint']):
        raise ValueError('recovery parent identity differs')
    names=request['tickers']
    if not names or len(names)!=len(set(names)):
        raise ValueError('recovery names must be unique and nonempty')
    exclusions=audit['exclusions']
    if ({r['ticker'] for r in exclusions}!=set(names) or len(exclusions)!=len(names)
            or any(r['reason']!='STOCK_TIMEOUT' for r in exclusions)):
        raise ValueError('recovery must retain all and only audited terminal timeouts')
    if not original['request']['stock_timeout_seconds']<request['stock_timeout_seconds']<=1800:
        raise ValueError('recovery wall allowance must be larger and bounded')
    parts=[];origins=[]
    for ticker in names:
        row=next(r for r in exclusions if r['ticker']==ticker)
        index=row['index']
        if index not in {s['index'] for s in audit['shards']}:
            raise ValueError('recovery source shard is not audited final')
        source=original['parts'][index]
        if ticker not in source['tickers']:
            raise ValueError('recovery stock absent from original source part')
        part=copy.deepcopy(source);part['tickers']=[ticker];parts.append(part)
        summary=next(s for s in audit['shards'] if s['index']==index)
        origins.append(dict(ticker=ticker,base_index=index,base_release=summary['release'],
                            summary_sha256=summary['summary_sha256'],reason='STOCK_TIMEOUT'))
    runtime=copy.deepcopy(original['request'])
    runtime.update(stock_timeout_seconds=request['stock_timeout_seconds'],shard_budget_seconds=3600)
    return dict(request=runtime,parts=parts,origins=origins,addon_request=request,
                recovery_tickers=len(parts),original_universe=original['original_universe'],
                original_source_accepted_tickers=original['accepted_tickers'],
                source_stitch_sha256=original['source_stitch_sha256'],
                price_answer_per_ticker_limit=original['price_answer_per_ticker_limit'],
                per_ticker_budget_policy='DIAGNOSTIC_AVERAGE_ONLY_NEVER_EXCLUDE_FOR_SIZE',
                full_world_acceptance='TIMEOUT_ADDON_ONLY_NOT_FULL_WORLD',scoring_gate='CLOSED')


def prepare(root,request):
    from ci import compact_world_build as base
    if set(request['compute_sha256'])!={'ci/compact_world_storage_budget.py','world_answer_cache.py'}:
        raise ValueError('recovery compute code pins incomplete')
    for name,expected in request['compute_sha256'].items():
        if sha(Path(name).read_bytes())!=expected:raise ValueError('recovery compute changed from protected producer: '+name)
    root.mkdir(parents=True,exist_ok=True)
    file=download_asset(request['base_inputs_release'],'COMPACT_WORLD_BUILD_PLAN.json',root/'base')
    if sha(file.read_bytes())!=request['base_plan_sha256']:raise ValueError('base plan bytes differ')
    original=json.loads(file.read_text(encoding='utf-8'))
    url='https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/'+request['audit_commit']+'/docs/COMPACT_WORLD_COMPLETED_SHARD_AUDIT_V2.json'
    with urllib.request.urlopen(url,timeout=90) as response:raw=response.read(2000001)
    if len(raw)>2000000 or sha(raw)!=request['audit_sha256']:raise ValueError('base audit bytes differ')
    audit=json.loads(raw);plan=make_plan(original,audit,request)
    # Authenticate each terminal omission again before scheduling any worker.
    for origin in plan['origins']:
        file=download_asset(origin['base_release'],'COMPACT_WORLD_SHARD.json',root/'base'/str(origin['base_index']))
        if sha(file.read_bytes())!=origin['summary_sha256']:raise ValueError('base terminal summary differs')
        state=json.loads(file.read_text(encoding='utf-8'))
        base.validate_shard(state,original['parts'][origin['base_index']])
        if (state['status']!='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'
                or state['source_commit']!=request['base_producer']
                or state['recipe_fingerprint']!=original['request']['corrected_recipe_fingerprint']
                or state['inputs_release']!=request['base_inputs_release']
                or any(r['ticker']==origin['ticker'] for r in state['completed'])
                or not any(r['ticker']==origin['ticker'] and r['reason']=='STOCK_TIMEOUT' for r in state['excluded'])):
            raise ValueError('recovery target is not a terminal omission')
    registry=download_asset(request['base_inputs_release'],'DIAGNOSTIC_REGISTRIES.json',root)
    if sha(registry.read_bytes())!=original['request']['registry_sha256']:raise ValueError('base registry differs')
    file=root/'COMPACT_WORLD_BUILD_PLAN.json'
    file.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    tag=f"price-timeout-addon-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','Five authenticated terminal omissions only; original protected run and ledger untouched; exact math unchanged.')
    publish_assets(tag,file,registry,REQUEST);gh_retry('release','edit',tag,'--draft=false')
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
        stream.write('matrix='+json.dumps(list(range(len(plan['parts']))))+'\ninputs_release='+tag+'\nplan_sha256='+sha(file.read_bytes())+'\n')
    print('TIMEOUT_ADDON_PREPARED',tag,len(plan['parts']),flush=True)


def traced_command(command):
    if command[:3]!=[sys.executable,'-m','ci.compact_world_storage_budget'] or '--worker' not in command:
        raise ValueError('unexpected recovery worker command')
    return [*command[:2],'ci.price_timeout_addon',*command[3:]]


def recover(root,inputs_release,index,expected_sha):
    from ci import compact_world_build as base
    file=download_asset(inputs_release,'COMPACT_WORLD_BUILD_PLAN.json',root)
    if sha(file.read_bytes())!=expected_sha:raise ValueError('recovery plan differs from prepare output')
    plan=json.loads(file.read_text(encoding='utf-8'))
    for name,expected in plan['addon_request']['compute_sha256'].items():
        if sha(Path(name).read_bytes())!=expected:raise ValueError('recovery compute code differs')
    if not 0<=index<len(plan['parts']) or len(plan['parts'][index]['tickers'])!=1:
        raise ValueError('recovery must isolate exactly one audited omission')
    # This adapter exists only in this isolated CLI process. Base files and all
    # protected processes are untouched; the compute function remains identical.
    original=base.limited_process
    def traced(command,directory,seconds):
        return original(traced_command(command),directory,seconds)
    try:
        base.limited_process=traced
        base.build(root,inputs_release,index)
    finally:
        base.limited_process=original


def worker(root,recipe):
    from ci.compact_world_storage_budget import worker as exact_worker
    faulthandler.enable();faulthandler.dump_traceback_later(300,repeat=True)
    try:exact_worker(root,recipe)
    finally:faulthandler.cancel_dump_traceback_later()


def finalize(root,inputs_release,expected_sha):
    from ci import compact_world_build as base
    root.mkdir(parents=True,exist_ok=True)
    file=download_asset(inputs_release,'COMPACT_WORLD_BUILD_PLAN.json',root)
    if sha(file.read_bytes())!=expected_sha:raise ValueError('recovery finalizer plan differs')
    plan=json.loads(file.read_text(encoding='utf-8'));done=[];excluded=[];errors=[];receipts=[]
    for index,part in enumerate(plan['parts']):
        tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
        try:
            file=download_asset(tag,'COMPACT_WORLD_SHARD.json',root/str(index));raw=file.read_bytes()
            state=json.loads(raw);base.validate_shard(state,part)
            if (state['status']!='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'
                    or state['source_commit']!=os.environ['GITHUB_SHA'] or state['inputs_release']!=inputs_release
                    or state['recipe_fingerprint']!=plan['request']['corrected_recipe_fingerprint']):
                raise ValueError('recovery result identity differs')
            inventory=asset_index(tag)
            for row in state['completed']:
                asset=inventory[row['asset']]
                if (row['release']!=tag or row['asset']!=row['ticker'].encode().hex()+'.diagnostic_answers.tar.zst'
                        or asset['digest']!='sha256:'+row['answer_container_sha256']
                        or asset['size']!=row['answer_container_bytes']
                        or row['shared_registry_sha256']!=plan['request']['registry_sha256']
                        or row['diagnostic_questions']!=68904 or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
                    raise ValueError('recovery payload identity differs')
            done.extend(state['completed']);excluded.extend(state['excluded'])
            receipts.append(dict(index=index,release=tag,summary_sha256=sha(raw),published_bytes=sum(a['size'] for a in inventory.values())))
        except Exception as exc:errors.append(dict(index=index,tickers=part['tickers'],error=str(exc)[-2000:]))
    accounted=[r['ticker'] for r in done+excluded]+[t for row in errors for t in row['tickers']]
    if len(accounted)!=len(set(accounted)) or set(accounted)!=set(plan['addon_request']['tickers']):
        raise ValueError('recovery output membership differs')
    report=dict(status='TIMEOUT_ADDON_COMPLETE_NOT_WORLD' if not excluded and not errors else 'TIMEOUT_ADDON_INCOMPLETE',
                source_commit=os.environ['GITHUB_SHA'],inputs_release=inputs_release,plan_sha256=expected_sha,
                base_run=40621517496,original_ledger_unchanged=True,origins=plan['origins'],request=plan['addon_request'],
                completed=done,excluded=excluded,errors=errors,releases=receipts,
                global_coverage_gate='NOT_COMPOSED_WITH_ALL_BASE_SHARDS',world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    file=root/'PRICE_TIMEOUT_ADDON_MEASURED_V1.json';file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"price-timeout-addon-measured-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    print('TIMEOUT_ADDON_MEASURED',len(done),len(excluded),len(errors),flush=True)
    if excluded or errors:raise ValueError('timeout recovery incomplete; immutable evidence retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',nargs='?',choices=('prepare','recover','finalize'))
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--inputs-release')
    parser.add_argument('--index',type=int);parser.add_argument('--plan-sha256')
    parser.add_argument('--worker',action='store_true');parser.add_argument('--recipe',type=Path)
    args=parser.parse_args()
    if args.worker:worker(args.directory,args.recipe)
    elif args.operation=='prepare':prepare(args.directory,json.loads(REQUEST.read_text(encoding='utf-8')))
    elif args.operation=='recover':recover(args.directory,args.inputs_release,args.index,args.plan_sha256)
    elif args.operation=='finalize':finalize(args.directory,args.inputs_release,args.plan_sha256)
    else:parser.error('operation or --worker required')
