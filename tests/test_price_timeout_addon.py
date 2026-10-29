import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ci import price_timeout_addon as addon


def fixture():
    request=dict(base_producer='producer',base_inputs_release='base-inputs',base_plan_sha256='plan',
                 tickers=['A','B'],stock_timeout_seconds=1800)
    original=dict(request=dict(corrected_recipe_fingerprint='recipe',stock_timeout_seconds=900,registry_sha256='registry'),
                  parts=[dict(tickers=['A','C'],release='source',part='p0'),dict(tickers=['B'],release='source',part='p1')],
                  original_universe=8727,accepted_tickers=8316,source_stitch_sha256='stitch',price_answer_per_ticker_limit=10)
    audit=dict(producer_commit='producer',inputs_release='base-inputs',plan_sha256='plan',recipe_fingerprint='recipe',
               exclusions=[dict(ticker='A',index=0,reason='STOCK_TIMEOUT'),dict(ticker='B',index=1,reason='STOCK_TIMEOUT')],
               shards=[dict(index=0,release='base-000',summary_sha256='summary0'),dict(index=1,release='base-001',summary_sha256='summary1')])
    return original,audit,request


def test_plan_isolates_all_terminal_omissions_and_never_mutates_original_inputs():
    original,audit,request=fixture();before=copy.deepcopy(original)
    plan=addon.make_plan(original,audit,request)
    assert original==before
    assert [p['tickers'] for p in plan['parts']]==[['A'],['B']]
    assert plan['request']['corrected_recipe_fingerprint']=='recipe'
    assert plan['request']['stock_timeout_seconds']==1800 and original['request']['stock_timeout_seconds']==900
    assert plan['recovery_tickers']==2 and 'accepted_tickers' not in plan
    assert plan['full_world_acceptance']=='TIMEOUT_ADDON_ONLY_NOT_FULL_WORLD'


@pytest.mark.parametrize('problem',['drop','duplicate','foreign','nonterminal','source','identity','limit'])
def test_unsafe_or_incomplete_recovery_selection_fails(problem):
    original,audit,request=fixture()
    if problem=='drop':request['tickers']=['A']
    elif problem=='duplicate':request['tickers']=['A','A','B']
    elif problem=='foreign':request['tickers']=['A','X']
    elif problem=='nonterminal':audit['exclusions'][0]['reason']='SHARD_RESULT_UNVERIFIED'
    elif problem=='source':original['parts'][0]['tickers']=['C']
    elif problem=='identity':audit['producer_commit']='different'
    elif problem=='limit':request['stock_timeout_seconds']=7200
    with pytest.raises(ValueError):addon.make_plan(original,audit,request)


def test_trace_adapter_changes_only_module_and_keeps_all_worker_arguments():
    command=[sys.executable,'-m','ci.compact_world_storage_budget','--directory','stock','--worker','--recipe','pinned']
    changed=addon.traced_command(command)
    assert changed[:3]==[sys.executable,'-m','ci.price_timeout_addon']
    assert changed[3:]==command[3:]
    with pytest.raises(ValueError):addon.traced_command([sys.executable,'-c','different'])


def test_trace_worker_import_does_not_preload_math_before_the_bound_recipe():
    # The legacy base orchestrator imports world_timeframes. Importing it at
    # module scope here would silently bypass the later recipe sys.path pin.
    subprocess.run([sys.executable,'-c',
        "import ci.price_timeout_addon,sys; assert not ({'world_timeframes','facets_world','world_bar_statistics'} & set(sys.modules))"],check=True)


def test_recovery_restores_process_adapter_on_failure(tmp_path,monkeypatch):
    from ci import compact_world_build as base
    plan=dict(parts=[dict(tickers=['A'])],addon_request=dict(compute_sha256={}))
    raw=json.dumps(plan).encode();file=tmp_path/'plan.json';file.write_bytes(raw)
    monkeypatch.setattr(addon,'download_asset',lambda *a:file)
    original=base.limited_process
    def fail(*args):
        assert base.limited_process is not original
        raise RuntimeError('worker failure')
    monkeypatch.setattr(base,'build',fail)
    with pytest.raises(RuntimeError):addon.recover(tmp_path,'new-inputs',0,addon.sha(raw))
    assert base.limited_process is original
    with pytest.raises(ValueError,match='plan differs'):addon.recover(tmp_path,'new-inputs',0,'changed')


@pytest.mark.parametrize('corrupt',[False,True])
def test_finalizer_publishes_explicit_partial_evidence_instead_of_false_completion(tmp_path,monkeypatch,corrupt):
    original,audit,request=fixture();plan=addon.make_plan(original,audit,request)
    raw=json.dumps(plan).encode();plan_file=tmp_path/'plan.json';plan_file.write_bytes(raw)
    monkeypatch.setenv('GITHUB_RUN_ID','900');monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1');monkeypatch.setenv('GITHUB_SHA','new-commit')
    def download(tag,name,directory):
        if name=='COMPACT_WORLD_BUILD_PLAN.json':return plan_file
        index=int(tag.rsplit('-',1)[1]);ticker=plan['parts'][index]['tickers'][0]
        state=dict(status='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD',source_part=plan['parts'][index],
                   source_commit='new-commit',inputs_release='new-inputs',recipe_fingerprint='recipe',excluded=[],
                   completed=[dict(ticker=ticker,release=tag,asset=ticker.encode().hex()+'.diagnostic_answers.tar.zst',
                                   answer_container_sha256='payload',answer_container_bytes=7,shared_registry_sha256='registry',
                                   diagnostic_questions=68904,roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT')])
        directory=Path(directory);directory.mkdir(exist_ok=True);file=directory/name;file.write_text(json.dumps(state));return file
    def inventory(tag):
        index=int(tag.rsplit('-',1)[1]);ticker=plan['parts'][index]['tickers'][0]
        return {ticker.encode().hex()+'.diagnostic_answers.tar.zst':dict(size=7,digest='sha256:'+('wrong' if corrupt and index==0 else 'payload'))}
    monkeypatch.setattr(addon,'download_asset',download);monkeypatch.setattr(addon,'asset_index',inventory)
    calls=[];monkeypatch.setattr(addon,'gh_retry',lambda *a:calls.append(a))
    published=[];monkeypatch.setattr(addon,'publish_assets',lambda tag,*files:published.extend(p.name for p in files))
    if corrupt:
        with pytest.raises(ValueError,match='incomplete'):addon.finalize(tmp_path,'new-inputs',addon.sha(raw))
    else:addon.finalize(tmp_path,'new-inputs',addon.sha(raw))
    report=json.loads((tmp_path/'PRICE_TIMEOUT_ADDON_MEASURED_V1.json').read_text())
    assert len(report['completed'])==(1 if corrupt else 2) and len(report['errors'])==int(corrupt)
    assert report['status']==('TIMEOUT_ADDON_INCOMPLETE' if corrupt else 'TIMEOUT_ADDON_COMPLETE_NOT_WORLD')
    assert report['world_gate']=='NOT_PROVEN' and report['original_ledger_unchanged'] is True
    assert published==['PRICE_TIMEOUT_ADDON_MEASURED_V1.json']
