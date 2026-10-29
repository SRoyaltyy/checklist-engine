"""Build only the 131 newly available raw names, preserving the base ledger."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path

from ci.release_assets import asset_index, download_asset, gh_retry, publish_assets

REQUEST=Path('ci/PRICE_RAW_ADDON_REQUEST.json')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def runtime_spec():
    return dict(python=platform.python_version(),machine=platform.machine(),
                packages={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','TA-Lib','exchange_calendars')})


def checked(tag,name,fingerprint,directory):
    file=download_asset(tag,name,directory)
    if sha(file.read_bytes())!=fingerprint:raise ValueError('incremental source differs: '+name)
    return file


def verify_compute(request):
    if set(request['compute_sha256'])!={'ci/compact_world_storage_budget.py','world_answer_cache.py'}:
        raise ValueError('incremental compute code pins incomplete')
    for name,expected in request['compute_sha256'].items():
        if sha(Path(name).read_bytes())!=expected:raise ValueError('incremental compute changed: '+name)


def make_plan(original,full,request):
    if (full['status']!='FULL_ACCEPTED_PRICE_BASE_ONLY_NOT_WORLD'
            or full['inputs_tag']!=original['request']['inputs_tag']
            or full['stock_day_weights_sha256']!=request['source_weights_sha256']):
        raise ValueError('incremental source identity differs')
    def indexed(parts):
        result={};names=[]
        for part in parts:
            key=(part['release'],part['part'])
            if key in result:raise ValueError('duplicate release-aware source part')
            result[key]=part;names.extend(part['tickers'])
        if len(names)!=len(set(names)):raise ValueError('duplicate source stock')
        return result,set(names)
    old,old_names=indexed(original['parts']);new,new_names=indexed(full['parts'])
    if (len(old_names)!=original['accepted_tickers'] or len(old_names)!=request['expected_base_names']
            or len(new_names)!=full['selected_tickers'] or len(new_names)!=request['expected_full_names']):
        raise ValueError('incremental source stock totals differ')
    # Every original part, including tickers and all hashes, must be identical.
    # A newer source cannot silently replace an already running stock's input.
    if any(new.get(key)!=part for key,part in old.items()):
        raise ValueError('incremental source rewrites or loses an original part')
    wanted=new_names-old_names
    if len(wanted)!=request['expected_incremental_names'] or not wanted:
        raise ValueError('incremental stock count differs')
    limit=request['max_names_per_job']
    if type(limit) is not int or not 1<=limit<=10:raise ValueError('incremental chunk limit invalid')
    parts=[];origins=[]
    for key,part in new.items():
        tickers=[ticker for ticker in part['tickers'] if ticker in wanted]
        if not tickers:continue
        origins.append(copy.deepcopy(part))
        for start in range(0,len(tickers),limit):
            own=copy.deepcopy(part);own['tickers']=tickers[start:start+limit];parts.append(own)
    selected=[ticker for part in parts for ticker in part['tickers']]
    if len(selected)!=len(wanted) or set(selected)!=wanted:raise ValueError('incremental work partition differs')
    runtime=copy.deepcopy(original['request']);runtime.update(shard_budget_seconds=10000)
    return dict(request=runtime,parts=parts,addon_request=request,origins=origins,
                incremental_tickers=sorted(wanted),original_universe=original['original_universe'],
                base_accepted_tickers=len(old_names),source_full_tickers=len(new_names),
                source_stitch_sha256=original['source_stitch_sha256'],
                price_answer_per_ticker_limit=original['price_answer_per_ticker_limit'],
                per_ticker_budget_policy='DIAGNOSTIC_AVERAGE_ONLY_NEVER_EXCLUDE_FOR_SIZE',
                full_world_acceptance='RAW_INCREMENTAL_PRICE_ANSWERS_ONLY_NOT_WORLD',scoring_gate='CLOSED')


def incremental_weights(full,base):
    import pandas as pd
    from world_context_store import checked_weights
    full_dates,full_counts=checked_weights(full);base_dates,base_counts=checked_weights(base)
    full_series=pd.Series(full_counts,index=full_dates);base_series=pd.Series(base_counts,index=base_dates)
    if not base_dates.isin(full_dates).all():raise ValueError('incremental weights lose original dates')
    difference=full_series-base_series.reindex(full_dates,fill_value=0)
    if (difference<0).any():raise ValueError('incremental weights remove original stock days')
    return pd.DataFrame(dict(date=full_dates,stock_days=difference.to_numpy(dtype='int64')))


def prepare(root,request):
    import pandas as pd
    verify_compute(request);root.mkdir(parents=True,exist_ok=True)
    original_file=checked(request['base_inputs_release'],'COMPACT_WORLD_BUILD_PLAN.json',request['base_plan_sha256'],root/'base')
    status_file=checked(request['source_release'],'NATIVE_PRICE_BASE_STATUS_V1.json',request['source_status_sha256'],root/'source')
    original=json.loads(original_file.read_text(encoding='utf-8'));full=json.loads(status_file.read_text(encoding='utf-8'))
    plan=make_plan(original,full,request);plan['runtime']=runtime_spec()
    base_weights=checked(request['base_stock_release'],'ACCEPTED_PRICE_STOCK_DAYS.csv',request['base_weights_sha256'],root/'base')
    full_weights=checked(request['source_release'],'PRICE_BASE_STOCK_DAY_WEIGHTS_V1.csv',request['source_weights_sha256'],root/'source')
    weights=incremental_weights(pd.read_csv(full_weights),pd.read_csv(base_weights))
    if (int(pd.read_csv(base_weights).stock_days.sum())!=request['expected_base_stock_days']
            or int(weights.stock_days.sum())!=request['expected_incremental_stock_days']
            or int(pd.read_csv(full_weights).stock_days.sum())!=full['query_rows']):
        raise ValueError('incremental stock-day totals differ')
    plan['incremental_stock_days']=int(weights.stock_days.sum())
    inventories={};source_assets=[]
    for part in plan['origins']:
        if part['release'] not in inventories:inventories[part['release']]=asset_index(part['release'])
        inventory=inventories[part['release']]
        for suffix,fingerprint in (('.tar','archive_sha256'),('.coverage.csv','coverage_sha256'),('.stock_days.csv','stock_days_sha256'),('.json',None)):
            asset=inventory[part['part']+suffix]
            if fingerprint is not None and asset['digest']!='sha256:'+part[fingerprint]:raise ValueError('incremental source inventory differs')
            if not asset['digest'].startswith('sha256:') or len(asset['digest'])!=71:raise ValueError('incremental source asset digest missing')
            source_assets.append(dict(release=part['release'],asset=part['part']+suffix,bytes=asset['size'],sha256=asset['digest'][7:]))
    plan['unique_raw_source_assets']=source_assets
    plan['unique_raw_source_bytes']=sum(r['bytes'] for r in source_assets)
    registry=checked(request['base_inputs_release'],'DIAGNOSTIC_REGISTRIES.json',original['request']['registry_sha256'],root)
    file=root/'COMPACT_WORLD_BUILD_PLAN.json';file.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    weights_file=root/'INCREMENTAL_STOCK_DAY_WEIGHTS_V1.csv';weights.to_csv(weights_file,index=False)
    tag=f"price-raw-addon-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','131 newly available raw names only; every original source binding and protected build ledger preserved; not full-world approval.')
    publish_assets(tag,file,registry,weights_file,REQUEST);gh_retry('release','edit',tag,'--draft=false')
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
        stream.write('matrix='+json.dumps(list(range(len(plan['parts']))))+'\ninputs_release='+tag+'\nplan_sha256='+sha(file.read_bytes())+'\n')
    print('RAW_ADDON_PREPARED',tag,len(plan['parts']),len(plan['incremental_tickers']),plan['incremental_stock_days'],flush=True)


def build(root,inputs_release,index,expected_sha):
    from ci import compact_world_build as base
    file=checked(inputs_release,'COMPACT_WORLD_BUILD_PLAN.json',expected_sha,root)
    plan=json.loads(file.read_text(encoding='utf-8'));verify_compute(plan['addon_request'])
    if runtime_spec()!=plan['runtime']:raise ValueError('incremental runtime differs from prepared recipe')
    if not 0<=index<len(plan['parts']):raise ValueError('incremental part unknown')
    part=plan['parts'][index]
    binding=next(r for r in plan['unique_raw_source_assets'] if r['release']==part['release'] and r['asset']==part['part']+'.json')
    checked(part['release'],binding['asset'],binding['sha256'],root/'source')
    base.build(root,inputs_release,index)


def finalize(root,inputs_release,expected_sha):
    from ci import compact_world_build as base
    root.mkdir(parents=True,exist_ok=True)
    file=checked(inputs_release,'COMPACT_WORLD_BUILD_PLAN.json',expected_sha,root)
    plan=json.loads(file.read_text(encoding='utf-8'));done=[];excluded=[];errors=[];receipts=[]
    for index,part in enumerate(plan['parts']):
        tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
        try:
            file=download_asset(tag,'COMPACT_WORLD_SHARD.json',root/str(index));raw=file.read_bytes();state=json.loads(raw)
            base.validate_shard(state,part)
            if (state['status']!='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'
                    or state['source_commit']!=os.environ['GITHUB_SHA'] or state['inputs_release']!=inputs_release
                    or state['recipe_fingerprint']!=plan['request']['corrected_recipe_fingerprint']):
                raise ValueError('incremental result source differs')
            inventory=asset_index(tag)
            for row in state['completed']:
                asset=inventory[row['asset']]
                if (row['release']!=tag or row['asset']!=row['ticker'].encode().hex()+'.diagnostic_answers.tar.zst'
                        or asset['digest']!='sha256:'+row['answer_container_sha256'] or asset['size']!=row['answer_container_bytes']
                        or row['shared_registry_sha256']!=plan['request']['registry_sha256'] or row['diagnostic_questions']!=68904
                        or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
                    raise ValueError('incremental payload differs')
            done.extend(state['completed']);excluded.extend(state['excluded'])
            receipts.append(dict(index=index,release=tag,summary_sha256=sha(raw),published_bytes=sum(a['size'] for a in inventory.values())))
        except Exception as exc:errors.append(dict(index=index,tickers=part['tickers'],error=str(exc)[-2000:]))
    names=[r['ticker'] for r in done+excluded]+[t for row in errors for t in row['tickers']]
    if len(names)!=len(set(names)) or set(names)!=set(plan['incremental_tickers']):raise ValueError('incremental output membership differs')
    stock_days=sum(r['query_rows'] for r in done)
    totals_match=not excluded and not errors and stock_days==plan['incremental_stock_days']
    report=dict(status='RAW_INCREMENTAL_PRICE_ANSWERS_COMPLETE_NOT_WORLD' if totals_match else 'RAW_INCREMENTAL_PRICE_ANSWERS_INCOMPLETE',
                source_commit=os.environ['GITHUB_SHA'],inputs_release=inputs_release,plan_sha256=expected_sha,request=plan['addon_request'],runtime=plan['runtime'],
                base_run=40621517496,original_ledger_unchanged=True,completed=done,excluded=excluded,errors=errors,releases=receipts,
                completed_stock_days=stock_days,expected_incremental_stock_days=plan['incremental_stock_days'],
                unique_raw_source_assets=plan['unique_raw_source_assets'],unique_raw_source_bytes=plan['unique_raw_source_bytes'],
                global_coverage_gate='NOT_COMPOSED_WITH_BASE_AND_TIMEOUT_RECOVERY',historical_tradeability_gate='NOT_PROVEN',
                full_dependency_budget_gate='NOT_PROVEN',world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    file=root/'PRICE_RAW_ADDON_MEASURED_V1.json';file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"price-raw-addon-measured-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    print('RAW_ADDON_MEASURED',len(done),len(excluded),len(errors),stock_days,flush=True)
    if not totals_match:raise ValueError('incremental price answers incomplete; all evidence retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('prepare','build','finalize'))
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--inputs-release')
    parser.add_argument('--index',type=int);parser.add_argument('--plan-sha256');args=parser.parse_args()
    if args.operation=='prepare':prepare(args.directory,json.loads(REQUEST.read_text(encoding='utf-8')))
    elif args.operation=='build':build(args.directory,args.inputs_release,args.index,args.plan_sha256)
    else:finalize(args.directory,args.inputs_release,args.plan_sha256)
