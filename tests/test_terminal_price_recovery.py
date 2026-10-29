import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ci.terminal_price_recovery import BASE_FINGERPRINT,compose,inventory_fingerprint,make_plan,verify_code


def fixture():
    tickers=[f'N{n:03d}' for n in range(50)];timeouts=['EQLT','WKSP','ABVC','NXTS','SU'];draft='protected-draft'
    part=dict(part='base_last',release='raw',tickers=tickers,archive_sha256='a'*64)
    original=dict(parts=[copy.deepcopy(part)]+[dict(part=t,release='raw',tickers=[t]) for t in timeouts],
                  request=dict(corrected_recipe_fingerprint=BASE_FINGERPRINT,registry_sha256='b'*64),
                  source_stitch_sha256='c'*64,price_answer_per_ticker_limit=1234)
    measured=dict(status='PRICE_ANSWER_BUILD_MEASURED_NOT_FULL_WORLD',inputs_release='inputs',
                  completed=[dict(ticker=f'B{n}') for n in range(8261)],completed_tickers=8261,build_excluded_tickers=55,
                  excluded=[dict(ticker=t,reason='SHARD_RESULT_UNVERIFIED') for t in tickers]+[dict(ticker=t,reason='STOCK_TIMEOUT') for t in timeouts])
    done=[];assets=[]
    for ticker in tickers[:24]:
        name=ticker.encode().hex()+'.diagnostic_answers.tar.zst'
        done.append(dict(ticker=ticker,asset=name,release=draft,answer_container_sha256='d'*64,answer_container_bytes=100,
                         diagnostic_questions=68904,roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT',shared_registry_sha256='b'*64))
        assets.append(dict(name=name,size=100,digest='sha256:'+'d'*64,state='uploaded'))
    inventory=dict(id=123,tag_name=draft,draft=True,target_commitish='base',assets=assets)
    checkpoint=dict(status='BUILDING_PRICE_ANSWER_STAGE_NOT_FULL_WORLD',source_part=copy.deepcopy(part),source_commit='base',
                    inputs_release='inputs',recipe_fingerprint=BASE_FINGERPRINT,completed=done,excluded=[],answer_bytes=2400)
    timeout=dict(status='TIMEOUT_ADDON_INCOMPLETE',completed=[],errors=[],excluded=[dict(ticker=t,reason='STOCK_TIMEOUT') for t in timeouts])
    proof=dict(status='RENKO_GUARD_SAMPLE_EXACT_WITH_NEW_TARGET_ONLY',errors=[],candidate_fingerprint='e'*64,base_fingerprint=BASE_FINGERPRINT,
               results=[{} for _ in range(9)],original_reference_numeric_cells=51008796,
               guarded_answer_result=dict(samples=[dict(ticker='EQLT',query_rows=1712,diagnostic_questions=68904,
                                                        roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT')]))
    request=dict(base_plan=dict(release='inputs'),failed_index=0,draft_release_id=123,draft_tag=draft,base_producer='base',
                 draft_inventory_sha256=inventory_fingerprint(inventory),candidate_fingerprint='e'*64,guard_proof=dict(release='guarded-proof'))
    return original,measured,checkpoint,inventory,timeout,proof,request


def test_plan_retains24_reuses_eqlt_computes_only_other30_without_mutating_inputs():
    args=fixture();before=json.dumps(args,sort_keys=True);plan=make_plan(*args)
    assert json.dumps(args,sort_keys=True)==before
    assert len(plan['reused'])==25 and len(plan['parts'])==10
    fresh=[t for p in plan['parts'] for t in p['tickers']]
    assert len(fresh)==len(set(fresh))==30 and 'EQLT' not in fresh
    assert not set(fresh)&{r['ticker'] for r in plan['reused']}
    assert all(1<=len(p['tickers'])<=5 for p in plan['parts'])
    assert plan['request']['corrected_recipe_fingerprint']=='e'*64
    assert {r['recipe_fingerprint'] for r in plan['reused']}=={BASE_FINGERPRINT,'e'*64}


@pytest.mark.parametrize('change',['inventory_digest','inventory_state','draft_id','draft_target','checkpoint_recipe','checkpoint_bytes',
                                  'duplicate_payload','orphan_payload','partial_checkpoint','old_timeout_still_missing','guard_error','eqlt_shape','base_count'])
def test_every_source_and_accounting_failure_is_rejected(change):
    args=list(fixture());original,measured,checkpoint,inventory,timeout,proof,request=args
    if change=='inventory_digest':inventory['assets'][0]['digest']='sha256:'+'f'*64
    elif change=='inventory_state':inventory['assets'][0]['state']='starter'
    elif change=='draft_id':inventory['id']+=1
    elif change=='draft_target':inventory['target_commitish']='other'
    elif change=='checkpoint_recipe':checkpoint['recipe_fingerprint']='f'*64
    elif change=='checkpoint_bytes':checkpoint['answer_bytes']+=1
    elif change=='duplicate_payload':checkpoint['completed'][-1]=copy.deepcopy(checkpoint['completed'][0])
    elif change=='orphan_payload':inventory['assets'].append(dict(name='orphan.diagnostic_answers.tar.zst',size=100,digest='sha256:'+'d'*64,state='uploaded'));request['draft_inventory_sha256']=inventory_fingerprint(inventory)
    elif change=='partial_checkpoint':checkpoint['completed'].pop()
    elif change=='old_timeout_still_missing':timeout['excluded'].pop()
    elif change=='guard_error':proof['errors']=[dict(reason='mismatch')]
    elif change=='eqlt_shape':proof['guarded_answer_result']['samples'][0]['query_rows']-=1
    elif change=='base_count':measured['completed_tickers']+=1
    with pytest.raises(ValueError):make_plan(*args)


def test_module_import_does_not_cache_math_before_bound_worker_path():
    subprocess.run([sys.executable,'-c','import sys; import ci.terminal_price_recovery; assert not {"facets_world","world_timeframes","ci.compact_world_build"}.intersection(sys.modules)'],check=True,timeout=10)


def test_missing_code_pins_cannot_pass():
    with pytest.raises(ValueError,match='pins incomplete'):verify_code(dict(compute_sha256={}))


def test_derived_snapshot_adapter_is_process_local_and_restored_on_worker_failure(tmp_path,monkeypatch):
    from ci import compact_world_build as base
    from ci import terminal_price_recovery as recovery
    plan=dict(request=dict(corrected_recipe_fingerprint='e'*64),runtime={},recovery_request={},
              parts=[dict(release='source',part='part')],raw_manifests=[dict(release='source',asset='part.json')])
    plan_file=tmp_path/'plan.json';plan_file.write_text(json.dumps(plan));source=tmp_path/'part.json';source.write_text('{}')
    monkeypatch.setattr(recovery,'checked',lambda binding,root:plan_file if binding['asset']=='COMPACT_WORLD_BUILD_PLAN.json' else source)
    monkeypatch.setattr(recovery,'verify_code',lambda request:None);monkeypatch.setattr(recovery,'runtime',lambda:{})
    recipe=tmp_path/'bound'/'recipe';recipe.mkdir(parents=True)
    (recipe.parent/'BUILD_INPUTS.json').write_text(json.dumps(dict(recipe_files=['facets_world.py'])))
    (recipe/'facets_world.py').write_bytes(b'original')
    observed=[]
    def original(directory,request):
        observed.append(request['corrected_recipe_fingerprint']);return recipe,tmp_path/'calendar'
    monkeypatch.setattr(base,'snapshot',original)
    monkeypatch.setattr(recovery,'derive',lambda files:dict(files,**{'facets_world.py':b'guarded'}))
    monkeypatch.setattr(recovery,'fingerprint',lambda files:'e'*64)
    def failed_build(root,release,index):
        base.snapshot(recipe.parent,plan['request'])
        assert (recipe/'facets_world.py').read_bytes()==b'guarded'
        raise RuntimeError('simulated worker failure')
    monkeypatch.setattr(base,'build',failed_build)
    with pytest.raises(RuntimeError,match='simulated worker'):recovery.build(tmp_path,'new-inputs',0,'pinned')
    assert base.snapshot is original and observed==[BASE_FINGERPRINT]


def test_real_request_preserves_protected_and_pretested_recipe_identities():
    request=json.loads(Path('ci/TERMINAL_PRICE_RECOVERY_REQUEST.json').read_text(encoding='utf-8'))
    assert request['base_producer']=='49043dd375387bddad0d446c56f942f0711b28ed'
    assert request['base_plan']['sha256']=='a58db5e64fb59158caee44f5f637b48592f2137b01146bc31a1aec59c189f02a'
    assert request['draft_release_id']==427402982 and request['failed_index']==172
    assert request['candidate_fingerprint']=='40ea182cf6fb377d12710ccbfccd7ab2b5f17b9e6e6f07df08cf4399956ca0c3'


@pytest.mark.parametrize('change',['pass','duplicate','stock_days','source_membership','raw_missing'])
def test_global_price_component_requires_exact_full_raw_union_and_stock_days(change):
    rows=[dict(ticker=f'T{n}',query_rows=1) for n in range(8447)]
    rows[0]['query_rows']+=12560808-8447
    base=dict(completed=copy.deepcopy(rows[:8261]));addon=dict(status='RAW_INCREMENTAL_PRICE_ANSWERS_COMPLETE_NOT_WORLD',completed=copy.deepcopy(rows[8261:8392]),errors=[],excluded=[])
    recovered=copy.deepcopy(rows[8392:]);full=dict(parts=[dict(tickers=[r['ticker'] for r in rows])])
    if change=='duplicate':recovered[0]['ticker']=rows[0]['ticker']
    elif change=='stock_days':recovered[0]['query_rows']+=1
    elif change=='source_membership':full['parts'][0]['tickers'][0]='OTHER'
    elif change=='raw_missing':addon['completed'].pop()
    if change=='pass':
        result=compose(base,addon,full,recovered,{})
        assert result['completed_tickers']==8447 and result['query_stock_days']==12560808
        assert result['full_world_gate']=='NOT_PROVEN' and result['scoring_gate']=='CLOSED'
    else:
        with pytest.raises(ValueError,match='composition differs'):compose(base,addon,full,recovered,{})
