import copy
import hashlib
import json
import pytest
from ci.audit_completed_price_shards import FINAL,audit


def fixture():
    parts=[dict(tickers=['A','B'],part='p0'),dict(tickers=['C'],part='p1')]
    plan=dict(parts=parts,accepted_tickers=3,source_excluded_tickers=1,original_universe=4,
              source_stitch_sha256='stitch',request=dict(corrected_recipe_fingerprint='recipe',registry_sha256='registry'))
    state=dict(status=FINAL,source_commit='producer',recipe_fingerprint='recipe',inputs_release='build-inputs',source_part=parts[0],answer_bytes=10,
               completed=[dict(ticker='A',release='build-000',asset='41.diagnostic_answers.tar.zst',answer_container_bytes=10,
                   answer_container_sha256='answer',shared_registry_sha256='registry',diagnostic_questions=68904,
                   roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT')],excluded=[dict(ticker='B',reason='STOCK_TIMEOUT',error='')])
    raw=json.dumps(state).encode()
    inventory=dict(tag='build-000',draft=False,assets=[dict(name='41.diagnostic_answers.tar.zst',size=10,digest='sha256:answer',state='uploaded'),
                    dict(name='COMPACT_WORLD_SHARD.json',size=len(raw),digest='sha256:'+hashlib.sha256(raw).hexdigest(),state='uploaded')])
    return plan,state,{0:inventory}


def call(plan,state,inventories):
    raw=json.dumps(state).encode();inventories=copy.deepcopy(inventories)
    meta=inventories[0]['assets'][1];meta.update(size=len(raw),digest='sha256:'+hashlib.sha256(raw).hexdigest())
    plan_raw=json.dumps(plan).encode()
    return audit(plan_raw,{0:raw},inventories,'build-inputs','producer',hashlib.sha256(plan_raw).hexdigest())


def test_partial_audit_retains_timeout_and_does_not_call_it_size_or_full_world_pass():
    plan,state,inventory=fixture();report=call(plan,state,inventory)
    assert report['completed_tickers']==1 and report['build_excluded_tickers']==1
    assert report['exclusions'][0]['reason']=='STOCK_TIMEOUT' and report['legacy_size_exclusions_requiring_recovery']==[]
    assert report['price_coverage_gate']=='PENDING_UNFINISHED_SHARDS' and report['world_gate']=='NOT_PROVEN'


def test_size_exclusions_are_distinct_recovery_requirements():
    plan,state,inventory=fixture();state['excluded'][0]['reason']='ANSWER_STORAGE_BUDGET'
    report=call(plan,state,inventory)
    assert report['legacy_size_exclusions_requiring_recovery']==['B'] and report['storage_policy'].startswith('FAIL_')


@pytest.mark.parametrize('bad',['producer','source_part','ticker','registry','payload','orphan','missing_reason'])
def test_corrupt_metadata_cannot_become_verified_completion(bad):
    plan,state,inventory=fixture()
    if bad=='producer':state['source_commit']='other'
    elif bad=='source_part':state['source_part']={'tickers':['A','B'],'part':'different'}
    elif bad=='ticker':state['completed'][0]['ticker']='B'
    elif bad=='registry':state['completed'][0]['shared_registry_sha256']='other'
    elif bad=='payload':inventory[0]['assets'][0]['digest']='sha256:wrong'
    elif bad=='orphan':inventory[0]['assets'].append(dict(name='43.diagnostic_answers.tar.zst',size=10,digest='sha256:other',state='uploaded'))
    else:state['excluded'][0]['reason']=''
    with pytest.raises(ValueError):call(plan,state,inventory)


def test_complete_coverage_uses_original_denominator_and_keeps_budget_open():
    plan,state,inventory=fixture();plan.update(parts=plan['parts'][:1],accepted_tickers=2,source_excluded_tickers=2)
    report=call(plan,state,inventory)
    assert report['price_coverage_gate']=='FAIL_BELOW_95_PERCENT_ORIGINAL'
    assert report['price_budget_gate']=='NOT_MEASURED_FULL_DEPENDENCY_CLOSURE_REQUIRED'


def test_plan_must_match_an_independently_pinned_asset_fingerprint():
    plan,state,inventories=fixture()
    with pytest.raises(ValueError,match='pinned plan'):
        audit(json.dumps(plan).encode(),{0:json.dumps(state).encode()},inventories,'build-inputs','producer','wrong')
