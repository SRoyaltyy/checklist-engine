from copy import deepcopy
import subprocess
import pytest
from ci import release_assets as io
from ci.rebuild_partial_recovery import COMPLETE,recovery_plan,composed_state,verify_payload_rows


def row(ticker,release):
    return dict(ticker=ticker,release=release,asset=ticker.encode().hex()+'.diagnostic_answers.tar.zst',
        answer_container_bytes=3,answer_container_sha256='a'*64,diagnostic_questions=68904,
        roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT',shared_registry_sha256='b'*64)


@pytest.fixture
def inputs():
    part=dict(release='raw',part='part001',archive_sha256='c'*64,tickers=['A','B','C','D'])
    plan=dict(parts=[part],request=dict(corrected_recipe_fingerprint='d'*64,registry_sha256='b'*64),
        full_world_acceptance='NOT_PROVEN',price_answer_per_ticker_limit=10000)
    probe=dict(source_run=123,source_job=456,index=0,part=deepcopy(part),
        source_commit='e'*40,source_plan=dict(release='original-inputs',asset='plan.json',sha256='f'*64),
        source_checkpoint=dict(release='partial',asset='checkpoint.json',sha256='1'*64),
        completed=[row('A','partial'),row('B','partial')],missing_names=['C','D'],
        verified_completed_names=2,expected_names=4,recipe_fingerprint='d'*64,shared_registry_sha256='b'*64)
    return plan,probe


def calculated(plan,probe):
    return dict(source_part=recovery_plan(plan,probe)['parts'][0],inputs_release='recovery-inputs',
        status=COMPLETE,recipe_fingerprint='d'*64,world_gate='NOT_PROVEN',scoring_gate='CLOSED',
        source_commit='2'*40,completed=[row('C','new-shard'),row('D','new-shard')],excluded=[],answer_bytes=6)


def test_only_missing_names_are_calculated_and_original_sources_are_unchanged(inputs):
    plan,probe=inputs;before=deepcopy(inputs)
    scoped=recovery_plan(plan,probe)
    assert inputs==before
    assert scoped['parts'][0]==dict(plan['parts'][0],tickers=['C','D'])
    assert scoped['accepted_tickers']==2 and scoped['recovery']['preserved_names']==['A','B']
    assert scoped['request']==plan['request']
    assert scoped['full_world_acceptance']=='NOT_PROVEN'
    scoped['request']['registry_sha256']='changed'
    assert inputs==before


@pytest.mark.parametrize('change',[
    dict(missing_names=['A','C','D']),dict(missing_names=['D','C']),
    dict(verified_completed_names=3),dict(expected_names=5),
    dict(recipe_fingerprint='wrong'),dict(shared_registry_sha256='wrong'),
    dict(source_run=40621517496),
])
def test_malformed_or_protected_recovery_is_rejected(inputs,change):
    plan,probe=inputs;probe.update(change)
    with pytest.raises(ValueError):recovery_plan(plan,probe)


def test_duplicate_completed_name_cannot_displace_a_missing_name(inputs):
    plan,probe=inputs;probe['completed'][1]=deepcopy(probe['completed'][0])
    with pytest.raises(ValueError):recovery_plan(plan,probe)


def test_composition_preserves_old_payload_hashes_and_accounts_for_every_name(inputs):
    plan,probe=inputs;new=calculated(plan,probe);before=deepcopy((plan,probe,new))
    state=composed_state(plan,probe,new,'recovery-inputs','preserved-public')
    assert (plan,probe,new)==before
    assert [r['ticker'] for r in state['completed']]==['A','B','C','D']
    assert state['completed'][:2]==[dict(r,release='preserved-public') for r in probe['completed']]
    assert state['completed'][2:]==new['completed']
    assert state['answer_bytes']==12
    assert state['inputs_release']=='original-inputs' and state['source_part']==probe['part']
    assert state['recovery_provenance']['requires_explicit_parent_composition'] is True
    assert state['world_gate']=='NOT_PROVEN' and state['scoring_gate']=='CLOSED'


@pytest.mark.parametrize('change',[
    dict(inputs_release='wrong'),dict(recipe_fingerprint='wrong'),dict(status='BUILDING'),
    dict(world_gate='PASS'),dict(scoring_gate='OPEN'),dict(excluded=[dict(ticker='A')]),
])
def test_wrong_provenance_gate_or_duplicate_cross_scope_membership_cannot_compose(inputs,change):
    plan,probe=inputs;new=calculated(plan,probe);new.update(change)
    with pytest.raises(ValueError):composed_state(plan,probe,new,'recovery-inputs','preserved-public')


def test_new_failure_remains_explicit_and_never_erases_preserved_successes(inputs):
    plan,probe=inputs;new=calculated(plan,probe)
    new['completed']=new['completed'][1:];new['excluded']=[dict(ticker='C',reason='STOCK_ERROR')]
    state=composed_state(plan,probe,new,'recovery-inputs','preserved-public')
    assert [r['ticker'] for r in state['completed']]==['A','B','D']
    assert state['excluded']==new['excluded'] and state['recovery_provenance']['remaining_count']==1


def test_missing_name_cannot_silently_disappear_from_composition(inputs):
    plan,probe=inputs;new=calculated(plan,probe);new['completed'].pop()
    with pytest.raises(ValueError):composed_state(plan,probe,new,'recovery-inputs','preserved-public')


@pytest.mark.parametrize('change',[
    dict(size=4),dict(digest='sha256:'+'0'*64),dict(state='starter'),
])
def test_unverified_payload_metadata_is_rejected(change):
    saved=row('A','preserved');asset=dict(name=saved['asset'],size=3,digest='sha256:'+'a'*64,state='uploaded')
    inventory=dict(tag_name='preserved',assets=[asset])
    verify_payload_rows([saved],'b'*64,inventory)
    asset.update(change)
    with pytest.raises(ValueError):verify_payload_rows([saved],'b'*64,inventory)


@pytest.mark.parametrize('message',[
    'error connecting to api.github.com', 'error connecting to uploads.github.com',
    'getaddrinfo EAI_AGAIN productionresultssa10.blob.core.windows.net',
])
def test_observed_transport_errors_retry_with_the_existing_bound(monkeypatch,message):
    calls=[];waits=[]
    def run(*args):
        calls.append(args)
        if len(calls)==1:raise subprocess.CalledProcessError(1,['gh','api'],stderr=message)
        return 'verified response'
    monkeypatch.setattr(io,'_run',run)
    monkeypatch.setattr(io,'_wait_after',lambda exc,attempt:waits.append(attempt))
    assert io._read('api','repos/example/project/releases/1')=='verified response'
    assert len(calls)==2 and waits==[0]


def test_transport_retry_does_not_reclassify_permission_failure(monkeypatch):
    calls=[]
    def run(*args):
        calls.append(args);raise subprocess.CalledProcessError(1,['gh','api'],stderr='HTTP 403: Resource not accessible by integration')
    monkeypatch.setattr(io,'_run',run)
    monkeypatch.setattr(io,'_wait_after',lambda *args:pytest.fail('permission errors must not retry'))
    with pytest.raises(subprocess.CalledProcessError):io._read('api','repos/example/project/releases/1')
    assert len(calls)==1


@pytest.mark.parametrize('control',[
    dict(execute=False),dict(execute=True,run=40621517496,release_id=789),
    dict(execute=True,run=123,release_id=427402982),
])
def test_execution_controls_abort_before_any_remote_access(tmp_path,monkeypatch,control):
    import json
    from ci import rebuild_partial_recovery as recovery
    (tmp_path/'ci').mkdir();(tmp_path/'ci'/'REBUILD_PARTIAL_RECOVERY_REQUEST.json').write_text(json.dumps(control))
    monkeypatch.setattr(recovery,'ROOT',tmp_path)
    monkeypatch.setattr(io,'gh_retry',lambda *args:pytest.fail('guard must reject before remote access'))
    with pytest.raises(ValueError):recovery.run(tmp_path/'output')


def test_recovery_orchestration_preserves_bytes_and_calculates_only_missing_names(inputs,tmp_path,monkeypatch):
    import hashlib,json
    from ci import compact_world_build as producer,rebuild_partial_recovery as recovery
    from ci.rebuild_checkpoint_probe import reconcile
    plan,probe=inputs;digest=hashlib.sha256(b'abc').hexdigest()
    for saved in probe['completed']:saved['answer_container_sha256']=digest
    request=dict(execute=True,run=123,job=456,release_id=789,index=0,processed_checkpoint_rows=3,source_commit='e'*40)
    source=dict(id=789,tag_name='partial',draft=True,assets=[dict(name=r['asset'],size=3,
        digest='sha256:'+digest,state='uploaded') for r in probe['completed']])
    checkpoint=dict(source_part=deepcopy(probe['part']),inputs_release='original-inputs',source_commit='e'*40,
        recipe_fingerprint='d'*64,completed=deepcopy(probe['completed']),excluded=[dict(ticker='C',reason='STOCK_ERROR')])
    files={('partial',r['asset']):b'abc' for r in probe['completed']};releases={'partial':deepcopy(source)};edits=[]
    def bind(tag,name,data):
        raw=json.dumps(data).encode();files[tag,name]=raw
        return dict(release=tag,asset=name,sha256=hashlib.sha256(raw).hexdigest())
    request['plan']=bind('original-inputs','COMPACT_WORLD_BUILD_PLAN.json',plan)
    request['checkpoint']=bind('partial','checkpoint.json',checkpoint)
    published=reconcile(plan,checkpoint,source,request)
    request['probe']=bind('probe','REBUILD_PARTIAL_CHECKPOINT_V1.json',published)
    (tmp_path/'ci').mkdir();(tmp_path/'ci'/'REBUILD_PARTIAL_RECOVERY_REQUEST.json').write_text(json.dumps(request))
    monkeypatch.setattr(recovery,'ROOT',tmp_path)
    for key,value in dict(GITHUB_REPOSITORY='SRoyaltyy/checklist-engine',GITHUB_RUN_ID='999',
                          GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='2'*40).items():monkeypatch.setenv(key,value)
    monkeypatch.setattr(io,'_RELEASE_IDS',{})
    def gh(*args):
        if args==('api','repos/SRoyaltyy/checklist-engine/actions/jobs/456'):
            return json.dumps(dict(run_id=123,status='completed',conclusion='failure'))
        if args==('api','repos/SRoyaltyy/checklist-engine/releases/789'):return json.dumps(source)
        assert args[:2] in (('release','create'),('release','edit'))
        tag=args[2];assert tag!='partial'
        if args[1]=='create':
            assert tag not in releases;releases[tag]=dict(tag_name=tag,assets=[],draft=True)
        else:
            assert args[3:]==('--draft=false',);releases[tag]['draft']=False;edits.append(tag)
        return '{}'
    def download(tag,name,directory):
        directory.mkdir(parents=True,exist_ok=True);file=directory/name;file.write_bytes(files[tag,name]);return file
    def upload(tag,*paths):
        assert tag!='partial'
        for path in paths:
            raw=path.read_bytes();assert (tag,path.name) not in files or files[tag,path.name]==raw
            files[tag,path.name]=raw
            asset=dict(name=path.name,size=len(raw),digest='sha256:'+hashlib.sha256(raw).hexdigest(),state='uploaded')
            if asset not in releases[tag]['assets']:releases[tag]['assets'].append(asset)
    def build(directory,inputs_release,index):
        # Stand-in for expensive market calculation: observe the actual published
        # plan supplied to the unchanged producer, then emit its public contract.
        scoped=json.loads(files[inputs_release,'COMPACT_WORLD_BUILD_PLAN.json'])
        assert index==0 and scoped['parts'][0]['tickers']==['C','D']
        assert scoped['parts'][0]['archive_sha256']==plan['parts'][0]['archive_sha256']
        assert 'compact-world-build-preserved-v1-999-1-000' in edits
        state=calculated(plan,probe);state['inputs_release']=inputs_release
        tag='compact-world-build-v1-999-1-000';releases[tag]=dict(tag_name=tag,assets=[],draft=False)
        directory.mkdir(parents=True)
        for saved in state['completed']:
            saved.update(release=tag,answer_container_sha256=digest)
            file=directory/saved['asset'];file.write_bytes(b'abc');upload(tag,file)
        (directory/'COMPACT_WORLD_SHARD.json').write_text(json.dumps(state))
    monkeypatch.setattr(io,'gh_retry',gh);monkeypatch.setattr(io,'download_asset',download)
    monkeypatch.setattr(io,'publish_assets',upload)
    monkeypatch.setattr(io,'asset_index',lambda tag:{a['name']:a for a in releases[tag]['assets']})
    monkeypatch.setattr(producer,'build',build)
    recovery.run(tmp_path/'output')
    assert source==releases['partial']
    tag='compact-world-build-recovered-part-v1-999-1-000'
    state=json.loads(files[tag,'COMPACT_WORLD_SHARD.json'])
    assert len(state['completed'])==4 and state['excluded']==[]
    assert state['scoring_gate']=='CLOSED' and tag in edits
    for saved in state['completed']:
        assert files[saved['release'],saved['asset']]==b'abc'
