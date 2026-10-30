"""Authenticate row-0 price composition; fail closed on missing world proofs.

Reads published metadata and asset inventories. Does not rerun the protected
producer, rewrite results, or treat metadata as a full numeric/answer leak proof.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path

from ci.compact_world_build import complete_input_parts
from ci.release_assets import asset_index,download_asset,gh_retry,publish_assets
from ci.terminal_price_recovery import compose,inventory_fingerprint

ROOT=Path(__file__).resolve().parents[1]
CP_COLUMNS=('cp_mid_slope_up','cp_gr_body20','cp_pctB','cp_dip_atr','cp_days_since_h20',
            'cp_dd_vs_run','cp_redgreen_vol10','cp_hard_all','lower_highs10')


def checked(binding,root):
    file=download_asset(binding['release'],binding['asset'],root/binding['release'])
    if hashlib.sha256(file.read_bytes()).hexdigest()!=binding['sha256']:
        raise ValueError('row-0 public source digest differs: '+binding['asset'])
    return json.loads(file.read_bytes())


def reconcile(original,base,addon,full,recovery,composition,new_plan,registry):
    """Exact source-part/name/row reconciliation; no partial success verdict."""
    current=json.loads((ROOT/'ci/COMPACT_WORLD_BUILD_REQUEST.json').read_text(encoding='utf-8'))
    if new_plan['request']!=current:raise ValueError('fresh plan is not the current guarded build request')
    status=dict(inputs_tag=original['request']['inputs_tag'],accepted_tickers=original['accepted_tickers'],parts=original['parts'])
    parts,added=complete_input_parts(status,full,current['full_raw_source'])
    if (new_plan['parts']!=parts or new_plan['accepted_tickers']!=8447
        or new_plan['source_input_extension']['incremental_tickers']!=added or len(added)!=131
        or len(original['parts'])!=173 or original['accepted_tickers']!=8316):
        raise ValueError('fresh full build input membership differs')
    prior=current['prior_timeout_ledger']['tickers']
    dispositions=new_plan['prior_timeout_dispositions']
    if (len(dispositions)!=5 or {r['ticker'] for r in dispositions}!=set(prior)
        or any(r['prior_reason']!='STOCK_TIMEOUT' or r['disposition']!='GUARDED_RECIPE_RETRY_WITH_BOUNDED_WORKER' for r in dispositions)):
        raise ValueError('timeout ledger dispositions differ')
    if (recovery['status']!='TERMINAL_PRICE_55_RECOVERED_NOT_WORLD' or recovery['errors'] or recovery['excluded']
        or len(recovery['completed'])!=55 or {r['ticker'] for r in recovery['completed']}!={r['ticker'] for r in base['excluded']}):
        raise ValueError('all55 original omissions must be recovered exactly')
    expected=compose(base,addon,full,recovery['completed'],{})
    if (composition['completed']!=expected['completed'] or composition['query_stock_days']!=12560808
        or composition['completed_tickers']!=8447 or len({r['ticker'] for r in addon['completed']})!=131
        or {r['ticker'] for r in addon['completed']}!=set(added)):
        raise ValueError('published full composition differs')
    by_name={r['ticker']:r for r in composition['completed']}
    coverage=[dict(index=i,source_release=p['release'],source_part=p['part'],expected=len(p['tickers']),
                   covered=sum(t in by_name for t in p['tickers'])) for i,p in enumerate(original['parts'])]
    if any(r['expected']!=r['covered'] for r in coverage):raise ValueError('original source part remains incomplete')
    recovered={r['ticker']:r for r in recovery['completed']};old={r['ticker']:r for r in base['excluded']}
    ledger=[dict(ticker=t,original_reason=old[t]['reason'],resolution=recovered[t]['origin_kind'],
                 recipe_fingerprint=recovered[t]['recipe_fingerprint'],release=recovered[t]['release'],
                 asset=recovered[t]['asset'],sha256=recovered[t]['answer_container_sha256']) for t in sorted(old)]
    if Counter(r['resolution'] for r in ledger)!=dict(EXACT_DRAFT_CHECKPOINT_COPY=24,EXISTING_VERIFIED_GUARDED_SAMPLE=1,NEW_GUARDED_TERMINAL_CALCULATION=30):
        raise ValueError('55-name resolution accounting differs')
    last=original['parts'][172]['tickers']
    if len(last)!=50 or not set(last)<=set(recovered):raise ValueError('part172 is not fully recovered')
    questions=[q for rows in registry.values() for q in rows]
    ids=[q['question_id'] for q in questions]
    if len(ids)!=len(set(ids)) or len(ids)!=68904:raise ValueError('diagnostic registry identity differs')
    observed={q.split(':',1)[0] for q in ids};missing_cp=sorted(set(CP_COLUMNS)-observed)
    # A hash-authenticated diagnostic is not a complete binary/native world.
    checks={
        'all_pinned_price_calculations':'FAIL_MISSING:'+','.join(missing_cp) if missing_cp else 'NOT_PROVEN_ALL_PRICE_SETTINGS',
        'complete_binary_price_answer_layer':'NOT_PROVEN_DIAGNOSTIC_REGISTRY_IS_NOT_CANONICAL_BINARY_MASTER',
        'all_price_column_and_question_prefix_leak_proof':composition['comprehensive_leak_gate'],
        'historical_tradeable_and_nominal_100M_mask':composition['historical_tradeability_gate'],
        'exact_price_state_and_dependency_retention':composition['portable_exact_recomputation_gate'],
    }
    report=dict(format='ROW0_PRICE_WORLD_GATE_V1',source_part_name_coverage='173/173',
        original_run_job_completion='172/173_UNCHANGED',part172_recovered_names=50,
        input_tickers=8447,incremental_input_tickers=131,original_omissions_resolved=55,
        prior_timeouts_in_guarded_inputs=5,query_stock_days=12560808,
        diagnostic_membership_gate='PASS',price_world_gate='PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL',price_world_checks=checks,
        full_world_gate='NOT_PROVEN',scoring_gate='CLOSED',
        measured_payload_bodies='NOT_REREAD_NO_FULL_NUMERIC_OR_ANSWER_PREFIX_RECOMPUTATION',
        full_measured_coverage_check='CANNOT_RUN_COMPLETE_NATIVE_PRICE_NUMERIC_AND_BINARY_WORLD_ARTIFACT_NOT_AVAILABLE',
        original_run_mutations='NONE',new_market_computations=0)
    return report,ledger,coverage


def write_csv(file,rows):
    with file.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def run(root,new_plan_path,new_plan_release):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    request=json.loads((ROOT/'ci/TERMINAL_PRICE_RECOVERY_REQUEST.json').read_text(encoding='utf-8'))
    binding=json.loads((ROOT/'docs/COMPOSED_PRICE_DIAGNOSTIC_BINDING_V1.json').read_text(encoding='utf-8'))
    readback=json.loads((ROOT/'docs/TERMINAL_PRICE_RECOVERY_PUBLIC_READBACK_V1.json').read_text(encoding='utf-8'))
    sources={key:checked(request[key],root/'sources') for key in ('base_plan','base_measurement','raw_addon','full_raw_source')}
    final_release=binding['release']
    recovery=checked(dict(release=final_release,asset='TERMINAL_PRICE_RECOVERY_MEASURED_V1.json',sha256=readback['report_sha256']),root/'sources')
    composition=checked(binding,root/'sources')
    registry=checked(dict(release=request['base_plan']['release'],asset='DIAGNOSTIC_REGISTRIES.json',
        sha256=sources['base_plan']['request']['registry_sha256']),root/'sources')
    new_plan_path=Path(new_plan_path);new_plan=json.loads(new_plan_path.read_bytes())
    report,ledger,coverage=reconcile(sources['base_plan'],sources['base_measurement'],sources['raw_addon'],
        sources['full_raw_source'],recovery,composition,new_plan,registry)
    report.update(source_commit=os.environ['GITHUB_SHA'],run=int(os.environ['GITHUB_RUN_ID']),new_inputs_release=new_plan_release,
        new_plan_sha256=hashlib.sha256(new_plan_path.read_bytes()).hexdigest(),recovery_run=binding['run'],recovery_producer=binding['producer'])
    repository=os.environ['GITHUB_REPOSITORY']
    protected=json.loads(gh_retry('api',f'repos/{repository}/actions/runs/40621517496'))
    draft=json.loads(gh_retry('api',f"repos/{repository}/releases/{request['draft_release_id']}"))
    if (protected['status']!='completed' or protected['head_sha']!=request['base_producer'] or protected['run_attempt']!=1
        or draft['id']!=427402982 or not draft['draft'] or draft['target_commitish']!=request['base_producer']
        or inventory_fingerprint(draft)!=request['draft_inventory_sha256']):
        raise ValueError('protected source run/draft identity or inventory changed')
    report['protected_source_run_and_draft_unchanged']=True
    # Verify every payload's current public asset digest/size, without fetching
    # ~GB payload bodies or calling this a semantic/roundtrip/PIT proof.
    inventories={};verified=0
    for row in composition['completed']:
        tag=row['release']
        if tag not in inventories:inventories[tag]=asset_index(tag)
        asset=inventories[tag][row['asset']]
        if (asset['digest']!='sha256:'+row['answer_container_sha256'] or asset['size']!=row['answer_container_bytes']
            or asset['state']!='uploaded' or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
            raise ValueError('current payload asset metadata differs: '+row['ticker'])
        verified+=1
        if verified%1000==0:print('ROW0_PAYLOAD_METADATA',verified,flush=True)
    report['payload_asset_metadata_verified']=verified
    write_csv(root/'ROW0_ORIGINAL_55_RESOLUTION_V1.csv',ledger)
    write_csv(root/'ROW0_ORIGINAL_PART_COVERAGE_V1.csv',coverage)
    report_file=root/'ROW0_PRICE_WORLD_GATE_V1.json';report_file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"row0-price-world-gate-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',tag,
        '--notes','Fresh guarded full-source input plan and complete price diagnostic name/asset-metadata audit. Price WORLD GATE FAIL; scoring CLOSED. No protected producer mutation or new market computation.')
    publish_assets(tag,report_file,root/'ROW0_ORIGINAL_55_RESOLUTION_V1.csv',root/'ROW0_ORIGINAL_PART_COVERAGE_V1.csv')
    gh_retry('release','edit',tag,'--draft=false')
    print('ROW0_PRICE_WORLD_GATE',report['price_world_gate'],'MEMBERSHIP',report['diagnostic_membership_gate'],
          'SOURCE_PARTS',report['source_part_name_coverage'],'RELEASE',tag,flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    parser.add_argument('--new-plan',required=True);parser.add_argument('--new-inputs-release',required=True)
    args=parser.parse_args();result=run(args.directory,args.new_plan,args.new_inputs_release)
    raise SystemExit(0 if result['price_world_gate']=='PASS' else 1)
