from copy import deepcopy
import hashlib
import json
import pytest
from ci import price_recovery_composition as module
from ci.price_recovery_composition import COMPLETE,compose,encoded


def row(ticker,release):
    return dict(ticker=ticker,release=release,asset=ticker.encode().hex()+'.diagnostic_answers.tar.zst',
        answer_container_bytes=3,answer_container_sha256='a'*64,shared_registry_sha256='b'*64,
        diagnostic_questions=68904,roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT')


@pytest.fixture
def inputs():
    old='compact-world-build-v1-123-1-001';saved='compact-world-build-preserved-v1-999-1-001'
    new='compact-world-build-v1-999-1-000';fixed='compact-world-build-recovered-part-v1-999-1-001'
    incoming='compact-world-build-recovery-v1-999-1-inputs'
    part=dict(tickers=['B','C'],release='raw',archive_sha256='c'*64)
    plan=dict(parts=[dict(tickers=['A']),part],accepted_tickers=3,original_universe=5,
        raw_dependency_bytes=5,full_world_acceptance='NOT_PROVEN',
        request=dict(corrected_recipe_fingerprint='d'*64,registry_sha256='b'*64,
                     answer_budget_bytes=100000,hard_world_cap_bytes=1000000))
    probe=dict(index=1,source_run=123,source_commit='e'*40,source_release=old,part=deepcopy(part),
        source_plan=dict(release='original-inputs',sha256='f'*64),
        source_checkpoint=dict(release=old,asset='checkpoint.json',sha256='1'*64),
        recipe_fingerprint='d'*64,shared_registry_sha256='b'*64,completed=[row('B',old)])
    parent=dict(status='PRICE_ANSWER_BUILD_MEASURED_NOT_FULL_WORLD',inputs_release='original-inputs',
        original_universe=5,raw_dependency_bytes=5,price_reservation_bytes=100000,hard_world_cap_bytes=1000000,
        world_gate='NOT_PROVEN',scoring_gate='CLOSED',completed=[row('A','unrelated')],
        excluded=[dict(ticker=t,reason='SHARD_RESULT_UNVERIFIED') for t in ('B','C')],
        shard_errors=[dict(index=1,error='missing final manifest')],completed_tickers=1,build_excluded_tickers=2,
        answer_and_checkpoint_bytes=30,shared_and_bound_input_bytes=10,source_excluded_tickers=2,
        remaining=['complete numeric retention and comprehensive leak proof'])
    replacement=dict(source_part=deepcopy(part),inputs_release='original-inputs',source_commit='2'*40,
        recipe_fingerprint='d'*64,status=COMPLETE,world_gate='NOT_PROVEN',scoring_gate='CLOSED',
        completed=[dict(probe['completed'][0],release=saved),row('C',new)],excluded=[],
        recovery_provenance=dict(original_run=123,original_index=1,original_source_commit='e'*40,
            original_checkpoint=probe['source_checkpoint'],preserved_release=saved,preserved_count=1,
            recovery_inputs_release=incoming,calculated_count=1,remaining_count=0))
    bindings=dict(source_run=123,source_commit='e'*40,recovery_run=999,recovery_source_commit='2'*40,
        failed_release_id=789,failed_release=old,plan=probe['source_plan'],
        parent=dict(release='compact-world-build-measured-v1-123-1'),
        replacement=dict(release=fixed),probe=dict(release='public-probe'))
    ledger=[]
    for i,(tag,role,size) in enumerate(((old,'output',4),(saved,'output',3),(new,'output',3),
                                      (fixed,'output',20),(incoming,'shared',10),('public-probe','shared',10))):
        assets=[dict(id=i+1,name='asset',size=size,state='uploaded',digest='sha256:'+'a'*64)]
        ledger.append(dict(release=tag,role=role,bytes=size,assets=assets,
                           inventory_sha256=hashlib.sha256(encoded(assets)).hexdigest()))
    return dict(plan=plan,parent=parent,replacement=replacement,probe=probe,ledger=ledger,
                bindings=bindings,parent_bytes=100,request_bytes=50)


def test_only_failed_part_changes_and_all_other_metadata_is_preserved(inputs):
    before=deepcopy(inputs);result,raw=compose(**inputs)
    assert inputs==before
    assert result['completed'][0]==inputs['parent']['completed'][0]
    assert result['completed'][1:]==inputs['replacement']['completed']
    assert result['excluded']==[] and result['shard_errors']==[]
    assert result['completed_tickers']==3 and result['completed_percent_original']==60
    assert result['source_excluded_tickers']==2 and result['remaining']==before['parent']['remaining']
    assert result['world_gate']=='NOT_PROVEN' and result['scoring_gate']=='CLOSED'
    assert result['storage_gate']=='PASS_PRICE_RESERVATION_ONLY_NOT_WORLD'
    assert raw==encoded(result) and json.loads(raw)==result


def test_exact_receipt_and_all_new_dependency_bytes_are_included(inputs):
    result,raw=compose(**inputs)
    assert result['composition']['receipt_bytes']==len(raw)
    assert result['answer_and_checkpoint_bytes']==30+30+50+len(raw)
    assert result['shared_and_bound_input_bytes']==10+20+100
    assert result['measured_price_dependency_bytes']==result['answer_and_checkpoint_bytes']+130+5
    assert result['composition']['bound_inputs']==inputs['bindings']


@pytest.mark.parametrize('field',['answer_budget_bytes','hard_world_cap_bytes'])
def test_storage_failure_retains_values_and_publishes_an_exactly_counted_receipt(inputs,field):
    inputs['plan']['request'][field]=1
    mapped={'answer_budget_bytes':'price_reservation_bytes','hard_world_cap_bytes':'hard_world_cap_bytes'}
    inputs['parent'][mapped[field]]=1
    result,raw=compose(**inputs)
    assert result['storage_gate']=='FAIL_PRICE_RESERVATION_ONLY_NOT_WORLD'
    assert result['composition']['receipt_bytes']==len(raw)
    assert len(result['completed'])==3 and not result['excluded']


@pytest.mark.parametrize('mutation',[
    lambda d:d['replacement']['completed'].pop(),
    lambda d:d['replacement']['completed'].append(deepcopy(d['replacement']['completed'][0])),
    lambda d:d['replacement']['completed'][0].update(answer_container_sha256='wrong'),
    lambda d:d['replacement'].update(recipe_fingerprint='wrong'),
    lambda d:d['replacement'].update(scoring_gate='OPEN'),
    lambda d:d['replacement'].update(world_gate='PASS'),
    lambda d:d['parent'].update(scoring_gate='OPEN'),
    lambda d:d['parent'].update(completed_tickers=2),
    lambda d:d['parent']['shard_errors'].clear(),
    lambda d:d['parent']['excluded'][0].update(reason='ANSWER_STORAGE_BUDGET'),
    lambda d:d['ledger'].pop(),
    lambda d:d['ledger'].append(deepcopy(d['ledger'][0])),
    lambda d:d['ledger'][0].update(bytes=1),
    lambda d:d['ledger'][1].update(inventory_sha256='wrong'),
    lambda d:d['bindings'].update(failed_release_id=427402982),
    lambda d:d['probe'].update(source_run=40621517496),
])
def test_incomplete_forged_or_protected_composition_is_rejected(inputs,mutation):
    mutation(inputs)
    with pytest.raises(ValueError):compose(**inputs)


def test_a_remaining_failure_is_explicit_never_silently_turned_into_an_answer(inputs):
    r=inputs['replacement'];r['completed'].pop();r['excluded']=[dict(ticker='C',reason='STOCK_ERROR')]
    r['recovery_provenance'].update(calculated_count=0,remaining_count=1)
    result,_=compose(**inputs)
    assert [r['ticker'] for r in result['completed']]==['A','B']
    assert result['excluded']==[dict(ticker='C',reason='STOCK_ERROR')]
    assert result['composition']['remaining_count']==1


def test_incomplete_original_upload_is_retained_and_counted_not_used_as_an_answer(inputs):
    entry=inputs['ledger'][0];entry['assets'][0].update(state='starter',digest=None)
    entry['inventory_sha256']=hashlib.sha256(encoded(entry['assets'])).hexdigest()
    result,_=compose(**inputs)
    assert result['composition']['dependency_byte_ledger'][0]['bytes']==4
    assert len(result['completed'])==3
    entry=inputs['ledger'][1];entry['assets'][0].update(state='starter',digest=None)
    entry['inventory_sha256']=hashlib.sha256(encoded(entry['assets'])).hexdigest()
    with pytest.raises(ValueError):compose(**inputs)


def test_unknown_or_excluded_name_cannot_enter_the_retained_cohort(inputs):
    inputs['replacement']['completed'][1]['ticker']='OUTSIDE'
    with pytest.raises(ValueError):compose(**inputs)


def test_disabled_request_aborts_before_remote_access(tmp_path,monkeypatch):
    from ci import release_assets as io
    (tmp_path/'ci').mkdir();(tmp_path/'ci'/'PRICE_RECOVERY_COMPOSITION_REQUEST.json').write_text('{"execute":false}')
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(io,'gh_retry',lambda *args:pytest.fail('disabled request must not access GitHub'))
    with pytest.raises(ValueError,match='not enabled'):module.run(tmp_path/'output')


@pytest.mark.parametrize('failure',[None,'wrong_hash','live_producer'])
def test_orchestration_authenticates_and_publishes_only_a_new_receipt(inputs,tmp_path,monkeypatch,failure):
    from ci import release_assets as io
    d=deepcopy(inputs);request=d['bindings'];request['execute']=True
    inventories={e['release']:{a['name']:deepcopy(a) for a in e['assets']} for e in d['ledger']}
    files={};published={};mutations=[]
    def bind(name,tag,asset,value):
        raw=encoded(value);files[tag,asset]=raw
        request[name]=dict(release=tag,asset=asset,sha256=hashlib.sha256(raw).hexdigest())
        inventories.setdefault(tag,{})[asset]=dict(id=50+len(files),name=asset,size=len(raw),state='uploaded',
                                                   digest='sha256:'+hashlib.sha256(raw).hexdigest())
    bind('plan','original-inputs','PLAN.json',d['plan'])
    d['probe']['source_plan']=request['plan']
    bind('parent',request['parent']['release'],'PARENT.json',d['parent'])
    bind('probe','public-probe','PROBE.json',d['probe'])
    bind('replacement',request['replacement']['release'],'REPLACEMENT.json',d['replacement'])
    for saved in d['replacement']['completed']:
        inventories[saved['release']]={saved['asset']:dict(id=100,name=saved['asset'],size=3,state='uploaded',digest='sha256:'+'a'*64)}
    if failure=='wrong_hash':request['parent']['sha256']='0'*64
    (tmp_path/'ci').mkdir();request_file=tmp_path/'ci'/'PRICE_RECOVERY_COMPOSITION_REQUEST.json'
    request_file.write_bytes(encoded(request));monkeypatch.setattr(module,'ROOT',tmp_path)
    for key,value in dict(GITHUB_REPOSITORY='SRoyaltyy/checklist-engine',GITHUB_RUN_ID='1111',
                          GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='3'*40).items():monkeypatch.setenv(key,value)
    monkeypatch.setattr(io,'_RELEASE_IDS',{})
    def gh(*args):
        if args[0]=='api':
            if '/actions/runs/' in args[1]:
                commit='e'*40 if args[1].endswith('/123') else '2'*40
                return json.dumps(dict(status='in_progress' if failure=='live_producer' else 'completed',
                                       head_sha=commit,run_attempt=1))
            assert args[1].endswith('/releases/789')
            return json.dumps(dict(id=789,tag_name=request['failed_release']))
        assert args[:2] in (('release','create'),('release','edit'))
        assert args[2]=='compact-world-build-composed-v1-1111-1'
        mutations.append(args);return '{}'
    def download(tag,name,directory):
        directory.mkdir(parents=True,exist_ok=True);file=directory/name;file.write_bytes(files[tag,name]);return file
    def publish(tag,*paths):
        assert tag=='compact-world-build-composed-v1-1111-1'
        for path in paths:published[path.name]=path.read_bytes()
    monkeypatch.setattr(io,'gh_retry',gh);monkeypatch.setattr(io,'download_asset',download)
    monkeypatch.setattr(io,'asset_index',lambda tag:inventories[tag]);monkeypatch.setattr(io,'publish_assets',publish)
    if failure:
        with pytest.raises(ValueError):module.run(tmp_path/'out')
        assert not published and not mutations
    else:
        module.run(tmp_path/'out')
        raw=published['COMPACT_WORLD_BUILD_COMPOSED.json'];result=json.loads(raw)
        assert result['composition']['receipt_bytes']==len(raw)
        assert result['completed'][0]==d['parent']['completed'][0]
        assert result['completed_tickers']==3 and not result['excluded']
        assert result['composition']['bound_inputs']==request
        assert published[request_file.name]==request_file.read_bytes()
        assert [m[1] for m in mutations]==['create','edit']
