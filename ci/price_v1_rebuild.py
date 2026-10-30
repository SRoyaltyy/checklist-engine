"""Authorize a new rebuild only from the published owner-scoped sample PASS."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def validate(gate,plan,binding,request,policy):
    fields={f:'DEFERRED_V2_FIELD' for f in policy['deferred_fields']}
    if (gate['format']!='ROW0_PRICE_WORLD_GATE_V2' or gate['price_v1_gate']!='PASS'
        or gate['authority_commit']!=policy['authority_commit'] or plan['scope']!=policy
        or gate['plan_sha256']!=binding['sample_plan']['sha256']
        or gate['source_commit']!=plan['source_commit'] or plan['request']!=request
        or gate['retained_names']!=8439 or plan['original_universe']!=8727
        or gate['source_coverage_pct']!=plan['source_coverage_pct'] or gate['source_coverage_pct']<95
        or gate['sample_names']!=plan['sample'] or len(set(plan['sample']))!=100
        or gate['sample_stocks']!=100 or len(gate['stock_bindings'])!=100
        or {r['ticker'] for r in gate['stock_bindings']}!=set(plan['sample'])
        or len(plan['price_fields'])!=1044 or gate['price_columns_per_timeframe']!=1044
        or gate['native_timeframes']!=22 or len(plan['timeframes'])!=22
        or gate['cut_checks']!=4400 or gate['compared_cells']<=0
        or gate['prefix_mismatch_blocks']!=0 or gate['prefix_failures']
        or gate['deferred_fields']!=fields or gate['scoring_gate']!='CLOSED'
        or gate['protected_source_mutations']!='NONE'):
        raise ValueError('published price-v1 PASS does not authorize this rebuild')
    return dict(format='PRICE_V1_REBUILD_AUTHORIZATION_V1',authority_commit=policy['authority_commit'],
        measured_gate=binding['gate'],sample_plan=binding['sample_plan'],retained_names=8439,
        recipe_fingerprint=request['corrected_recipe_fingerprint'],deferred_fields=fields,
        quarantine=request['replay_quarantine'],price_v1_row0_gate='PASS_SAMPLE_ONLY',
        scope='New original173-source-part lineage plus131-name extension; all176 current work parts. No protected producer or draft mutation.',
        full_world_and_scoring='NOT_APPROVED_BY_SAMPLE_GATE',max_parallel=20)


def prepare(root):
    from ci.price_v1_sample_gate import checked,scope
    from ci.compact_world_build import prepare as fresh_prepare
    from ci.release_assets import publish_assets
    binding=json.loads((ROOT/'ci/PRICE_V1_REBUILD_REQUEST.json').read_text(encoding='utf-8'))
    gate=json.loads(checked(binding['gate'],root/'gate').read_bytes())
    plan=json.loads(checked(binding['sample_plan'],root/'plan').read_bytes())
    request=json.loads((ROOT/'ci/COMPACT_WORLD_BUILD_REQUEST.json').read_text(encoding='utf-8'))
    report=validate(gate,plan,binding,request,scope())
    report.update(run=int(os.environ['GITHUB_RUN_ID']),source_commit=os.environ['GITHUB_SHA'],
        build_request_lf_sha256=hashlib.sha256((ROOT/'ci/COMPACT_WORLD_BUILD_REQUEST.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest())
    fresh_prepare(root,request)
    file=root/'PRICE_V1_REBUILD_AUTHORIZATION_V1.json';file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    publish_assets(tag,file,ROOT/'ci/PRICE_V1_REBUILD_REQUEST.json',ROOT/'dictionary/PRICE_V1_SCOPE_V1.json')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);args=parser.parse_args()
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True);prepare(root)
