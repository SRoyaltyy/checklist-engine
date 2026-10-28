import json
import hashlib
from pathlib import Path
import sys
import pytest
from ci.compact_world_build import limited_process,validate_shard,REQUEST


def test_hung_stock_is_killed_and_next_stock_can_complete(tmp_path):
    first=limited_process([sys.executable,'-c','import time;time.sleep(60)'],tmp_path/'hung',.1)
    second=limited_process([sys.executable,'-c','print("NEXT_STOCK_COMPLETED")'],tmp_path/'next',10)
    assert first['reason']=='STOCK_TIMEOUT' and first['returncode']!=0
    assert second['reason'] is None and 'NEXT_STOCK_COMPLETED' in second['log_tail']


def test_process_error_remains_an_explicit_exclusion(tmp_path):
    result=limited_process([sys.executable,'-c','raise ValueError("bad stock")'],tmp_path,10)
    assert result['reason']=='STOCK_PROCESS_ERROR' and 'bad stock' in result['log_tail']


@pytest.mark.parametrize('done,excluded',[(['a','a'],[]),(['a'],[]),(['a'],['a']),(['a'],['foreign'])])
def test_exclusion_ledger_cannot_hide_missing_duplicate_or_foreign_stock(done,excluded):
    part={'tickers':['a','b']}
    with pytest.raises(ValueError,match='membership'):
        validate_shard({'source_part':part,'completed':[{'ticker':t} for t in done],
                        'excluded':[{'ticker':t} for t in excluded]},part)


def test_good_and_excluded_stock_partition_the_source_exactly():
    part={'tickers':['a','b']}
    assert validate_shard({'source_part':part,'completed':[{'ticker':'a'}],
                           'excluded':[{'ticker':'b','reason':'STOCK_TIMEOUT'}]},part)==['a']


def test_production_limits_preserve_owner_cap_and_process_timeout():
    request=json.loads(REQUEST.read_text())
    assert request['max_parallel']<=20
    assert 0<request['stock_timeout_seconds']<request['shard_budget_seconds']<300*60
    assert request['answer_budget_bytes']+request['raw_source_budget_bytes']<request['hard_world_cap_bytes']==100000000000


@pytest.mark.parametrize('answer_budget,world_cap,legacy_size_skip',[(10,100,False),(100,50,False),(1000,1000,True)])
def test_above_average_stock_is_retained_and_budget_failure_publishes_full_evidence(tmp_path,monkeypatch,answer_budget,world_cap,legacy_size_skip):
    from ci import compact_world_build as build
    payload=b'preserve-every-byte'
    archive=b'archive'
    registry=b'{}'
    part=dict(release='raw',part='base_0000',tickers=['A'],archive_sha256=hashlib.sha256(archive).hexdigest())
    request=dict(inputs_tag='raw-inputs',inputs_sha256='b'*64,corrected_recipe_fingerprint='a'*64,
        registry_sha256=hashlib.sha256(registry).hexdigest(),stock_timeout_seconds=900,
        shard_budget_seconds=17100,answer_budget_bytes=answer_budget,hard_world_cap_bytes=world_cap)
    plan=dict(request=request,parts=[part],price_answer_per_ticker_limit=10,
        full_world_acceptance='NOT_PROVEN',accepted_tickers=1,original_universe=8727,
        source_excluded_tickers=8726,raw_dependency_bytes=20,shared_registry_bytes=2,bound_input_bytes=5)
    own=tmp_path/'build';published=[]
    def download(tag,name,directory):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);file=directory/name
        if name=='COMPACT_WORLD_BUILD_PLAN.json':file.write_text(json.dumps(plan))
        elif name=='base_0000.json':file.write_text(json.dumps(dict(inputs_tag='raw-inputs',archive_sha256=part['archive_sha256'])))
        elif name=='base_0000.tar':file.write_bytes(archive)
        elif name=='COMPACT_WORLD_SHARD.json':file.write_bytes((own/name).read_bytes())
        else:raise AssertionError((tag,name))
        return file
    monkeypatch.setattr(build,'download_asset',download)
    calendar=tmp_path/'calendar.parquet';calendar.write_bytes(b'calendar')
    recipe=tmp_path/'recipe';recipe.mkdir()
    monkeypatch.setattr(build,'snapshot',lambda *args:(recipe,calendar))
    monkeypatch.setattr(build,'read_member',lambda *args:b'raw-bars')
    def worker(command,directory,seconds):
        (directory/'DIAGNOSTIC_REGISTRIES.json').write_bytes(registry)
        (directory/'41.diagnostic_answers.tar.zst').write_bytes(payload)
        result=dict(samples=[dict(ticker='A',seconds=.01,query_rows=1,answer_container_bytes=len(payload),
            answer_container_sha256=hashlib.sha256(payload).hexdigest())],peak_rss_bytes=123)
        (directory/'COMPACT_STORAGE_WORKER.json').write_text(json.dumps(result))
        return {'reason':None}
    monkeypatch.setattr(build,'limited_process',worker)
    monkeypatch.setattr(build,'gh_retry',lambda *args:None)
    def publish(tag,*files):
        published.extend((file.name,file.read_bytes()) for file in files)
    monkeypatch.setattr(build,'publish_assets',publish)
    for key,value in [('GITHUB_SHA','commit'),('GITHUB_RUN_ID','7'),('GITHUB_RUN_ATTEMPT','1')]:monkeypatch.setenv(key,value)
    build.build(own,'inputs',0)
    state=json.loads((own/'COMPACT_WORLD_SHARD.json').read_text())
    assert state['excluded']==[] and state['completed'][0]['over_average_price_budget'] is True
    assert ('41.diagnostic_answers.tar.zst',payload) in published
    if legacy_size_skip:
        part['tickers'].append('B');plan['accepted_tickers']=2;plan['source_excluded_tickers']=8725
        state['source_part']=part
        state['excluded'].append(dict(ticker='B',reason='ANSWER_STORAGE_BUDGET',error='legacy producer artificial allowance'))
        (own/'COMPACT_WORLD_SHARD.json').write_text(json.dumps(state))
    def inventory(tag):
        if tag=='inputs':return {'registry.json':{'size':20}}
        return {'41.diagnostic_answers.tar.zst':{'size':len(payload),'digest':'sha256:'+hashlib.sha256(payload).hexdigest()},
                'checkpoint_0001.json':{'size':5}}
    monkeypatch.setattr(build,'asset_index',inventory)
    result=tmp_path/'measured'
    with pytest.raises(ValueError,match='full evidence published'):
        build.merge(result,'inputs')
    report=json.loads((result/'COMPACT_WORLD_BUILD_MEASURED.json').read_text())
    assert report['completed_tickers']==1 and report['build_excluded_tickers']==int(legacy_size_skip)
    assert report['storage_gate']==('FAIL_LEGACY_SIZE_EXCLUSIONS_REQUIRE_RECOVERY' if legacy_size_skip else 'FAIL_RETAIN_VALUES_IMPROVE_LOSSLESS_ENCODING')
    assert report['legacy_size_exclusions_requiring_recovery']==(['B'] if legacy_size_skip else [])
    assert report['above_average_budget_stocks']==1 and report['world_gate']=='NOT_PROVEN'
    assert any(name=='COMPACT_WORLD_BUILD_MEASURED.json' for name,raw in published)
