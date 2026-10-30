"""New isolated part172 replay; original producer/draft/results stay immutable."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

from ci import compact_world_build as build
from ci.release_assets import download_asset,gh_retry,publish_assets
from ci.terminal_price_recovery import runtime

ROOT=Path(__file__).resolve().parents[1]
NEW_INPUTS=dict(release='compact-world-build-v1-41058023781-1-inputs',asset='COMPACT_WORLD_BUILD_PLAN.json',
    sha256='92a327dd424589bf8a7e1b748feac5fecd6475b73bbd893b191ced93e6a9f18a')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def checked(binding,root):
    file=download_asset(binding['release'],binding['asset'],root)
    if sha(file.read_bytes())!=binding['sha256']:raise ValueError('replay source digest differs: '+binding['asset'])
    return file


def make_plan(original,current,composition):
    part=original['parts'][172];names=part['tickers']
    matches=[p for p in current['parts'] if (p['release'],p['part'])==(part['release'],part['part'])]
    if len(names)!=len(set(names)) or len(names)!=50 or matches!=[part]:raise ValueError('original part172 source differs')
    request=current['request']
    if (request['recipe_transform']!='RENKO_ZERO_STEP_V1'
        or request['corrected_recipe_fingerprint']!='40ea182cf6fb377d12710ccbfccd7ab2b5f17b9e6e6f07df08cf4399956ca0c3'):
        raise ValueError('replay requires the already proved default guarded recipe')
    refs=[r for r in composition['completed'] if r['ticker'] in names]
    if len(refs)!=50 or {r['ticker'] for r in refs}!=set(names):raise ValueError('retained part172 references incomplete')
    parts=[]
    for start in range(0,50,5):
        own=copy.deepcopy(part);own['tickers']=names[start:start+5];parts.append(own)
    return dict(request=dict(request,shard_budget_seconds=5400),parts=parts,references=refs,
        expected_tickers=sorted(names),source_part172=part,runtime=runtime(),
        price_answer_per_ticker_limit=current['price_answer_per_ticker_limit'],
        full_world_acceptance='ISOLATED_PART172_REPLAY_ONLY_NOT_WORLD',scoring_gate='CLOSED')


def prepare(root):
    root.mkdir(parents=True,exist_ok=True)
    old=json.loads((ROOT/'ci/TERMINAL_PRICE_RECOVERY_REQUEST.json').read_text(encoding='utf-8'))
    binding=json.loads((ROOT/'docs/COMPOSED_PRICE_DIAGNOSTIC_BINDING_V1.json').read_text(encoding='utf-8'))
    original=json.loads(checked(old['base_plan'],root/'old').read_bytes())
    current=json.loads(checked(NEW_INPUTS,root/'current').read_bytes())
    composition=json.loads(checked(binding,root/'reference').read_bytes())
    plan=make_plan(original,current,composition)
    registry_binding=dict(release=NEW_INPUTS['release'],asset='DIAGNOSTIC_REGISTRIES.json',sha256=plan['request']['registry_sha256'])
    registry=checked(registry_binding,root);plan['registry_binding']=registry_binding
    file=root/'COMPACT_WORLD_BUILD_PLAN.json';file.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    tag=f"row0-part172-replay-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',tag,
        '--notes','New isolated50-name replay through the guarded default build path, max10 workers; compare every diagnostic bitplane with authenticated retained outputs. Original producer/draft unchanged; no full-world or scoring approval.')
    publish_assets(tag,file,registry);gh_retry('release','edit',tag,'--draft=false')
    with open(os.environ['GITHUB_OUTPUT'],'a') as stream:
        stream.write('inputs_release='+tag+'\nplan_sha256='+sha(file.read_bytes())+'\nmatrix='+json.dumps(list(range(10)))+'\n')


def members(blob):
    import pyarrow as pa
    with pa.CompressedInputStream(pa.BufferReader(blob),'zstd') as stream:expanded=stream.read(100000001)
    if len(expanded)>100000000:raise ValueError('replay container expansion exceeds bound')
    result={}
    with tarfile.open(fileobj=io.BytesIO(expanded)) as archive:
        for item in archive:
            if not item.isfile() or item.name in result or item.size>1000000 or '/' in item.name:
                raise ValueError('invalid or duplicate replay container member')
            result[item.name]=archive.extractfile(item).read()
    return result


def compare_payloads(old_blob,new_blob,registry,expected_rows,old_recipe,new_recipe):
    import numpy as np
    import pyarrow as pa
    from world_answer_cache import registry_bytes
    left=members(old_blob);right=members(new_blob)
    if set(left)!=set(right) or not left:raise ValueError('replay container members differ')
    stems=sorted(name[:-5] for name in left if name.endswith('.json'))
    if set(left)!={s+suffix for s in stems for suffix in ('.json','.zst')}:raise ValueError('unexpected replay members')
    differences=0;missing_differences=0;cells=0;ids=set()
    for stem in stems:
        metadata=[json.loads(side[stem+'.json']) for side in (left,right)];raws=[];schemas=[]
        for side,meta,recipe in zip((left,right),metadata,(old_recipe,new_recipe)):
            schema=registry[meta['registry_sha256']];schemas.append(schema)
            if (sha(registry_bytes(schema))!=meta['registry_sha256'] or meta['rows']!=expected_rows
                or meta['format']!='REGISTERED_ANSWER_BITPLANES_V1' or meta['missing_code']!=0
                or meta['bitorder']!='little' or meta['codec']!='zstd' or meta['provenance']['recipe_fingerprint']!=recipe
                or any(q['outcomes']!=[0,1] for q in schema)):
                raise ValueError('replay chunk schema/provenance differs')
            chunk=side[stem+'.zst'];stride=(expected_rows+7)//8
            if (meta['raw_bytes']!=len(schema)*2*stride or meta['raw_bytes']>1000000
                or len(chunk)!=meta['compressed_bytes'] or sha(chunk)!=meta['compressed_sha256']):
                raise ValueError('replay compressed bitplane shape/hash differs')
            raw=bytes(pa.Codec('zstd').decompress(chunk,meta['raw_bytes']))
            if sha(raw)!=meta['raw_sha256']:raise ValueError('replay raw bitplane digest differs')
            planes=np.frombuffer(raw,dtype=np.uint8).reshape(len(schema),2,stride)
            if (planes[:,0]&planes[:,1]).any():raise ValueError('invalid binary answer code')
            if expected_rows%8 and (planes[:,:,-1]& (255-((1<<(expected_rows%8))-1))).any():
                raise ValueError('nonzero replay padding')
            raws.append(planes)
        a,b=metadata;pa0=dict(a['provenance']);pb0=dict(b['provenance']);pa0.pop('recipe_fingerprint');pb0.pop('recipe_fingerprint')
        if schemas[0]!=schemas[1] or pa0!=pb0:raise ValueError('replay row/input/mask or question binding differs')
        own=[q['question_id'] for q in schemas[0]]
        if ids.intersection(own):raise ValueError('duplicate replay question')
        ids.update(own);cells+=expected_rows*len(own)
        changed=(raws[0][:,0]^raws[1][:,0])|(raws[0][:,1]^raws[1][:,1])
        known_changed=(raws[0][:,0]|raws[0][:,1])^(raws[1][:,0]|raws[1][:,1])
        differences+=int(np.unpackbits(changed,axis=1,bitorder='little')[:,:expected_rows].sum())
        missing_differences+=int(np.unpackbits(known_changed,axis=1,bitorder='little')[:,:expected_rows].sum())
    return dict(chunks=len(stems),questions=len(ids),compared_cells=cells,mismatched_cells=differences,
                known_missing_mismatches=missing_differences)


def replay(root,inputs_release,index,pin):
    file=checked(dict(release=inputs_release,asset='COMPACT_WORLD_BUILD_PLAN.json',sha256=pin),root)
    plan=json.loads(file.read_bytes())
    if runtime()!=plan['runtime']:raise ValueError('replay runtime differs from prepared runtime')
    build.build(root,inputs_release,index)
    state=json.loads((root/'COMPACT_WORLD_SHARD.json').read_bytes());build.validate_shard(state,plan['parts'][index])
    if state['excluded']:raise ValueError('replay stock exclusions remain explicit in shard report')
    registry=json.loads(checked(plan['registry_binding'],root/'registry').read_bytes());refs={r['ticker']:r for r in plan['references']};results=[]
    for row in state['completed']:
        old=refs[row['ticker']];folder=root/'compare'/row['ticker'].encode().hex()
        old_file=checked(dict(release=old['release'],asset=old['asset'],sha256=old['answer_container_sha256']),folder/'old')
        new_file=checked(dict(release=row['release'],asset=row['asset'],sha256=row['answer_container_sha256']),folder/'new')
        result=compare_payloads(old_file.read_bytes(),new_file.read_bytes(),registry,row['query_rows'],
            old['recipe_fingerprint'],plan['request']['corrected_recipe_fingerprint'])
        if result['chunks']!=550 or result['questions']!=68904:raise ValueError('incomplete replay diagnostic grid')
        results.append(dict(ticker=row['ticker'],reference_sha256=old['answer_container_sha256'],replay_sha256=row['answer_container_sha256'],**result))
    report=dict(status='PASS_ALL_PART_CHUNK_BITS_EXACT' if not any(r['mismatched_cells'] for r in results) else 'FAIL_DIAGNOSTIC_REPLAY_MISMATCH',
        source_commit=os.environ['GITHUB_SHA'],index=index,inputs_release=inputs_release,plan_sha256=pin,results=results,
        protected_original_run_unchanged=40621517496,scoring_gate='CLOSED',full_world_gate='NOT_PROVEN')
    output=root/'ROW0_PART172_REPLAY_CHUNK_V1.json';output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
    publish_assets(tag,output)
    if report['status']!='PASS_ALL_PART_CHUNK_BITS_EXACT':raise ValueError('diagnostic replay changed retained bits; failure evidence published')


def finalize(root,inputs_release,pin):
    root.mkdir(parents=True,exist_ok=True)
    plan=json.loads(checked(dict(release=inputs_release,asset='COMPACT_WORLD_BUILD_PLAN.json',sha256=pin),root).read_bytes())
    rows=[];errors=[]
    for index,part in enumerate(plan['parts']):
        tag=f"compact-world-build-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
        try:
            state=json.loads(download_asset(tag,'COMPACT_WORLD_SHARD.json',root/str(index)).read_bytes());build.validate_shard(state,part)
            report=json.loads(download_asset(tag,'ROW0_PART172_REPLAY_CHUNK_V1.json',root/str(index)).read_bytes())
            if (state['source_commit']!=os.environ['GITHUB_SHA'] or state['inputs_release']!=inputs_release or state['excluded']
                or report['source_commit']!=os.environ['GITHUB_SHA'] or report['plan_sha256']!=pin or report['index']!=index
                or report['status'] not in ('PASS_ALL_PART_CHUNK_BITS_EXACT','FAIL_DIAGNOSTIC_REPLAY_MISMATCH')
                or len(report['results'])!=len(part['tickers']) or {r['ticker'] for r in report['results']}!=set(part['tickers'])
                or any(r['questions']!=68904 or r['chunks']!=550 or r['compared_cells']<=0 or r['mismatched_cells']<0 for r in report['results'])):
                raise ValueError('replay result source/membership differs')
            rows.extend(report['results'])
        except Exception as exc:errors.append(dict(index=index,error=str(exc)))
    names=[r['ticker'] for r in rows];complete=len(names)==len(set(names))==50 and set(names)==set(plan['expected_tickers'])
    mismatch=sum(r['mismatched_cells'] for r in rows)
    result=dict(status='PASS_PART172_50_REPLAY_BITS_EXACT' if complete and not errors and mismatch==0 else 'FAIL_PART172_REPLAY',
        source_commit=os.environ['GITHUB_SHA'],run=int(os.environ['GITHUB_RUN_ID']),inputs_release=inputs_release,plan_sha256=pin,
        completed=len(rows),expected=50,compared_cells=sum(r['compared_cells'] for r in rows),mismatched_cells=mismatch,
        errors=errors,results=rows,original_run_job_completion='172/173_UNCHANGED',full_world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    file=root/'ROW0_PART172_REPLAY_V1.json';file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    tag=f"row0-part172-replay-measured-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',tag);publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    print('ROW0_PART172_REPLAY',result['status'],len(rows),mismatch,flush=True)
    if result['status']!='PASS_PART172_50_REPLAY_BITS_EXACT':raise ValueError('part172 replay is not proven; evidence retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('prepare','replay','finalize'))
    parser.add_argument('--directory',required=True);parser.add_argument('--inputs-release');parser.add_argument('--index',type=int);parser.add_argument('--plan-sha256')
    args=parser.parse_args();root=Path(args.directory)
    if args.operation=='prepare':prepare(root)
    elif args.operation=='replay':replay(root,args.inputs_release,args.index,args.plan_sha256)
    else:finalize(root,args.inputs_release,args.plan_sha256)
