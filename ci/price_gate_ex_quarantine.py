"""Re-state the price gate under Cyrus's explicit eight-name quarantine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from ci.release_assets import asset_index,download_asset,gh_retry,publish_assets
from world_replay_quarantine import load_policy,excluded_names,filter_parts,POLICY_PATH,POLICY_SHA256

ROOT=Path(__file__).resolve().parents[1]


def restate(composition,replay,prior,plan,policy):
    denied={r['ticker'] for r in policy['records']};rows=composition['completed'];names=[r['ticker'] for r in rows]
    raw=[t for p in plan['raw_source_parts'] for t in p['tickers']]
    active=[t for p in plan['parts'] for t in p['tickers']]
    expected,_=filter_parts(plan['raw_source_parts'],policy)
    if (len(names)!=len(set(names)) or len(names)!=8447 or len(raw)!=len(set(raw)) or set(raw)!=set(names)
        or plan['parts']!=expected or len(active)!=len(set(active)) or set(active)!=set(names)-denied
        or plan['accepted_tickers']!=8439 or plan['replay_quarantine']!=policy['records']
        or plan['raw_source_excluded_tickers']!=280 or plan['source_excluded_tickers']!=288):
        raise ValueError('ex-quarantine source/work/name accounting differs')
    remaining=[r for r in rows if r['ticker'] not in denied];quarantined=[r for r in rows if r['ticker'] in denied]
    if (sum(r['query_rows'] for r in remaining)!=policy['v1_stock_days']
        or sum(r['query_rows'] for r in quarantined)!=policy['quarantined_stock_days']):raise ValueError('ex-quarantine stock-day accounting differs')
    changed={r['ticker'] for r in replay['results'] if r['mismatched_cells']}
    if changed!=denied or sum(r['mismatched_cells'] for r in replay['results'])!=166:
        raise ValueError('quarantine does not cover every known replay counterexample')
    source_checks=prior['price_world_checks']
    genuine={
        'required_price_field_families':source_checks['all_pinned_price_calculations'],
        'comprehensive_price_prefix_PIT_proof':source_checks['all_price_column_and_question_prefix_leak_proof'],
        'historical_tradeable_nominal_100M_eligibility':source_checks['historical_tradeable_and_nominal_100M_mask'],
        'complete_measured_native_price_world':'NOT_PROVEN_REQUIRED_WORLD_ARTIFACT_NOT_AVAILABLE',
    }
    verdict='PASS' if all(v=='PASS' for v in genuine.values()) else 'FAIL'
    return dict(format='PRICE_GATE_EX_QUARANTINE_V1',authority_commit='91a593a',
        original_universe=8727,raw_source_names=8447,raw_source_excluded_names=280,quarantined_names=8,v1_names=8439,
        v1_pct_original_names=100*8439/8727,quarantined_stock_days=13520,v1_stock_days=12547288,
        quarantine_pct_raw_source_rows=100*13520/12560808,source_coverage_gate='PASS_AT_LEAST_95_PERCENT',
        known_replay_mismatch_gate='PASS_ALL_KNOWN_MISMATCH_NAMES_EXCLUDED',
        replay_diagnosis='OPTIONAL_NONBLOCKING_BACKGROUND',original_bits_edited=False,
        genuine_price_world_checks=genuine,price_world_gate=verdict,
        binary_answer_layer='DOWNSTREAM_INCOMPLETE_NOT_A_RAW_BUILD_PREREQUISITE',
        historical_eligibility_other_names='NOT_PROVEN_QUARANTINE_IS_NOT_A_PIT_PROOF',
        full_world_gate='NOT_PROVEN',scoring_gate='CLOSED',
        rebuild_handoff='REQUEST_TASKFORCE_IF_PASS' if verdict=='PASS' else 'NOT_REQUESTED_GENUINE_GATES_REMAIN')


def checked(binding,root):
    file=download_asset(binding['release'],binding['asset'],root/binding['release'])
    if hashlib.sha256(file.read_bytes()).hexdigest()!=binding['sha256']:raise ValueError('ex-quarantine source digest differs')
    return json.loads(file.read_bytes())


def run(root,plan_path,inputs_release):
    root.mkdir(parents=True,exist_ok=True);policy=load_policy()
    binding=json.loads((ROOT/'docs/COMPOSED_PRICE_DIAGNOSTIC_BINDING_V1.json').read_text(encoding='utf-8'))
    composition=checked(binding,root/'sources')
    replay=checked(dict(release='row0-part172-replay-measured-v1-41059646552-1',asset='ROW0_PART172_REPLAY_V1.json',
        sha256=policy['replay_report_sha256']),root/'sources')
    prior=checked(dict(release='row0-price-world-gate-v1-41058023781-1',asset='ROW0_PRICE_WORLD_GATE_V1.json',
        sha256='2100a0296b6dc857a206c110bc14ca4ef96379ec7f4c3ddc101e68bf7cb20e64'),root/'sources')
    plan=json.loads(plan_path.read_bytes());result=restate(composition,replay,prior,plan,policy)
    current=json.loads((ROOT/'ci/COMPACT_WORLD_BUILD_REQUEST.json').read_text(encoding='utf-8'))
    if plan['request']!=current or current['replay_quarantine']['lf_sha256']!=POLICY_SHA256:raise ValueError('current exclusion binding differs')
    inventories={};verified=0
    for row in composition['completed']:
        if row['ticker'] in excluded_names():continue
        tag=row['release']
        if tag not in inventories:inventories[tag]=asset_index(tag)
        asset=inventories[tag][row['asset']]
        if asset['digest']!='sha256:'+row['answer_container_sha256'] or asset['size']!=row['answer_container_bytes'] or asset['state']!='uploaded':
            raise ValueError('active price payload asset differs')
        verified+=1
    result.update(run=int(os.environ['GITHUB_RUN_ID']),source_commit=os.environ['GITHUB_SHA'],inputs_release=inputs_release,
        actual_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),policy_lf_sha256=POLICY_SHA256,
        active_payload_asset_metadata_verified=verified)
    file=root/'PRICE_GATE_EX_QUARANTINE_V1.json';file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    tag=f"price-gate-ex-quarantine-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
        '--notes','Owner-approved eight-name exclusion enforced. Replay discrepancy diagnosis is OPTIONAL and non-blocking. Read remaining genuine gate verdict; no edited bits or scoring approval.')
    publish_assets(tag,file,ROOT/POLICY_PATH,ROOT/'docs/REPLAY_QUARANTINE_V1.csv',ROOT/'docs/BLOCKERS_GENUINE_VS_OPTIONAL_V1.md')
    gh_retry('release','edit',tag,'--draft=false');print('PRICE_GATE_EX_QUARANTINE',result['price_world_gate'],8439,verified,flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--plan',required=True);parser.add_argument('--inputs-release',required=True)
    args=parser.parse_args();result=run(Path(args.directory),Path(args.plan),args.inputs_release)
    raise SystemExit(0 if result['price_world_gate']=='PASS' else 1)
