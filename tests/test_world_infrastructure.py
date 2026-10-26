import io,json,subprocess,sys,urllib.error
from unittest.mock import patch
import pytest
from ci.world_pipeline import stage,publish
from ci.world_source_evidence import collect,verified_blocker
from ci.source_fetch_status import assess
from fetch.sec_client import get_json,SEC_HEADERS


def blocked_record():
    return dict(url='https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json',http_status=403,
        response_excerpt='Request blocked by SEC fair-access controls',attempts=4,
        request_spacing_seconds=1.,user_agent=SEC_HEADERS['User-Agent'],accept_encoding='gzip')


def test_bad_import_prevents_fetch_and_all_downstream_commands(tmp_path,capsys):
    state=tmp_path/'stages.json'
    command=[sys.executable,'-m','ci.world_pipeline','imports','definitely_missing_world_module']
    assert stage(state,'imports',command)!=0
    marker=tmp_path/'should_never_exist'
    for name in ('fetch','leak','coverage','publish'):
        assert stage(state,name,[sys.executable,'-c',f'open({str(marker)!r},"w").write("bad")'],['imports'])!=0
    assert not marker.exists()
    data=json.loads(state.read_text())
    assert data['imports']['command']==command and data['imports']['exit_code']!=0
    assert 'ModuleNotFoundError' in data['imports']['log_excerpt']
    assert all(data[n]['upstream_failure']==data['imports'] for n in ('fetch','leak','coverage','publish'))
    assert 'BLOCKED_UPSTREAM' in capsys.readouterr().out


def test_original_build_exit_code_and_excerpt_reach_every_downstream_stage(tmp_path):
    state=tmp_path/'stages.json'
    command=[sys.executable,'-c','print("real upstream failure");raise SystemExit(23)']
    assert stage(state,'build',command)==23
    for name in ('leak','coverage','publish'):assert stage(state,name,[sys.executable,'-c','raise SystemExit(99)'],['build'])==1
    result=json.loads(state.read_text())
    for name in ('leak','coverage','publish'):
        failure=result[name]['upstream_failure']
        assert failure['command']==command and failure['exit_code']==23
        assert 'real upstream failure' in failure['log_excerpt']


def test_empty_release_regression_never_calls_github(tmp_path):
    with patch('ci.world_pipeline.subprocess.run') as github:
        with pytest.raises(SystemExit,match='empty provisional release'):publish(tmp_path,'test','sha')
    github.assert_not_called()


def test_zero_uploaded_assets_never_make_a_release_public(tmp_path):
    (tmp_path/'proof.json').write_text('{}')
    with patch('ci.world_pipeline.subprocess.run',side_effect=[
        subprocess.CompletedProcess([],0),subprocess.CompletedProcess([],0,stdout='0')]) as github:
        with pytest.raises(SystemExit,match='zero uploaded assets'):publish(tmp_path,'test','sha')
    assert github.call_count==2
    assert all('edit' not in c.args[0] for c in github.call_args_list)


def test_sec_request_headers_throttle_retries_and_response_excerpt():
    calls=[]
    def blocked(request,**kwargs):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url,403,'Forbidden',{},io.BytesIO(b'<html>SEC request blocked</html>'))
    with patch('urllib.request.urlopen',side_effect=blocked),patch('time.sleep') as delay:
        with pytest.raises(urllib.error.HTTPError) as caught:get_json('https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json')
    record=caught.value.evidence
    assert verified_blocker(record) and record['attempts']==4 and record['response_excerpt']=='SEC request blocked'
    assert len(calls)==4 and sum(c.args==(1.0,) for c in delay.call_args_list)>=4
    assert calls[0].get_header('User-agent')=='checklist-engine research cyrus-checklist@users.noreply.github.com'
    assert calls[0].get_header('Accept-encoding')=='gzip'


def test_verified_sec_block_is_bound_to_source_dependent_items(tmp_path):
    report=dict(rows=0,errors={'MSFT':blocked_record()},done={},requested=1)
    (tmp_path/'xbrl_shard_000.progress.json').write_text(json.dumps(report))
    assert assess(tmp_path)['status']=='BLOCKED'
    evidence=collect(tmp_path)
    assert set(evidence)=={'I192','I193','I194'}
    assert all(e['status']=='BLOCKED' and 'HTTP 403' in e['reason'] for e in evidence.values())


def test_incomplete_source_cannot_be_waived_as_whole_source_block(tmp_path):
    report=dict(rows=10,errors={'MSFT':blocked_record()},done={'AAPL':'OK'},requested=2)
    (tmp_path/'xbrl_shard_000.progress.json').write_text(json.dumps(report))
    assert collect(tmp_path)=={}
    with pytest.raises(ValueError,match='incomplete'):assess(tmp_path)


@pytest.mark.parametrize('field',['url','response_excerpt','attempts','request_spacing_seconds','user_agent','accept_encoding'])
def test_source_exemption_requires_each_piece_of_evidence(field):
    record=blocked_record();record.pop(field)
    assert not verified_blocker(record)


@pytest.mark.parametrize('ticker',['MSFT','NVDA'])
def test_merge_failure_key_types_normalize_in_one_helper(ticker):
    import pandas as pd
    from world_dates import normalize_dates
    dates=pd.to_datetime(['2020-01-02','2020-01-03'])
    left=pd.DataFrame(dict(ticker=ticker,date=dates.as_unit('ns')))
    right=pd.DataFrame(dict(date=dates.as_unit('us'),value=[1.,2.]))
    with pytest.raises(pd.errors.MergeError):pd.merge_asof(left,right,on='date')
    result=pd.merge_asof(normalize_dates(left),normalize_dates(right),on='date')
    assert list(result.value)==[1.,2.]


def test_workflow_dependency_stops_sources_after_import_failure():
    import yaml
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    for filename in ('world_v2.yml','world_v2_ci.yml'):
        workflow=yaml.safe_load((root/'.github/workflows'/filename).read_text())
        names=('supplemental-prices','fred','companyfacts') if filename=='world_v2.yml' else ('sec-source-evidence','fred-source')
        for name in names:
            needs=workflow['jobs'][name].get('needs',[])
            assert 'verify' in ([needs] if isinstance(needs,str) else needs)


def test_measured_coverage_uses_verified_blocker_for_every_timeframe(tmp_path,monkeypatch):
    import ci.world_v2_coverage as gate
    (tmp_path/'dictionary').mkdir();(tmp_path/'docs').mkdir()
    (tmp_path/'dictionary/DATA_SOURCES.csv').write_text('id,item,block\nI192,Numeric financials,N\n')
    (tmp_path/'docs/TV_COVERAGE.csv').write_text('item_id,item,block,status,reason\n')
    monkeypatch.setattr(gate,'mappings',lambda:({},{}))
    measured=dict(rows=1,date_max='2026-10-23',columns={})
    evidence={'I192':dict(status='BLOCKED',reason='HTTP 403 after retries',evidence=[blocked_record()])}
    rows,failures=gate.build(measured,root=tmp_path,source_evidence=evidence)
    assert len(rows)==22 and not failures
    assert all(r['status']=='BLOCKED' and 'companyfacts' in r['source_evidence'] for r in rows)
    assert all(not r['snapshot_columns'] for r in rows)


def test_stage_cli_preserves_failure_and_blocks_next_command(tmp_path):
    state=tmp_path/'cli.json'
    base=[sys.executable,'-m','ci.world_pipeline','run','--state',str(state)]
    first=subprocess.run(base+['--stage','build','--',sys.executable,'-c','raise SystemExit(23)'],capture_output=True,text=True)
    assert first.returncode==23
    second=subprocess.run(base+['--stage','leak','--requires','build','--',sys.executable,'-c','print(123)'],capture_output=True,text=True)
    assert second.returncode==1 and 'BLOCKED_UPSTREAM' in second.stdout
    assert json.loads(state.read_text())['leak']['upstream_failure']['exit_code']==23


def test_unattempted_tickers_cannot_hide_behind_a_source_exemption(tmp_path):
    report=dict(rows=0,errors={'MSFT':blocked_record()},done={},requested=2)
    (tmp_path/'xbrl_shard_000.progress.json').write_text(json.dumps(report))
    assert collect(tmp_path)=={}
    with pytest.raises(ValueError,match='incomplete'):assess(tmp_path)
