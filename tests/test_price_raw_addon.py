import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from ci import price_raw_addon as addon


def fixture():
    original=dict(request=dict(inputs_tag='frozen',corrected_recipe_fingerprint='corrected',stock_timeout_seconds=900,registry_sha256='registry'),
                  parts=[dict(release='old',part='same_name',tickers=['A','B'],archive_sha256='old-archive')],
                  accepted_tickers=2,original_universe=10,source_stitch_sha256='stitch',price_answer_per_ticker_limit=10)
    full=dict(status='FULL_ACCEPTED_PRICE_BASE_ONLY_NOT_WORLD',inputs_tag='frozen',stock_day_weights_sha256='weights',selected_tickers=5,
              parts=copy.deepcopy(original['parts'])+[dict(release='new',part='same_name',tickers=['X','Y','Z'],archive_sha256='new-archive')])
    request=dict(source_weights_sha256='weights',expected_base_names=2,expected_full_names=5,expected_incremental_names=3,max_names_per_job=2)
    return original,full,request


def test_incremental_plan_preserves_original_and_uses_release_aware_names():
    original,full,request=fixture();before=copy.deepcopy(original)
    plan=addon.make_plan(original,full,request)
    assert original==before and plan['incremental_tickers']==['X','Y','Z']
    assert [p['tickers'] for p in plan['parts']]==[['X','Y'],['Z']]
    assert all(p['release']=='new' and p['archive_sha256']=='new-archive' for p in plan['parts'])
    assert plan['request']['corrected_recipe_fingerprint']=='corrected' and plan['request']['stock_timeout_seconds']==900
    assert 'accepted_tickers' not in plan and plan['base_accepted_tickers']==2
    assert plan['full_world_acceptance']=='RAW_INCREMENTAL_PRICE_ANSWERS_ONLY_NOT_WORLD'


@pytest.mark.parametrize('problem',['rewrite','drop','duplicate_part','duplicate_stock','wrong_count','wrong_inputs','wrong_weights','large_chunk'])
def test_incremental_selection_cannot_replace_or_skip_stocks(problem):
    original,full,request=fixture()
    if problem=='rewrite':full['parts'][0]['archive_sha256']='changed'
    elif problem=='drop':full['parts']=full['parts'][1:];full['selected_tickers']=3;request['expected_full_names']=3
    elif problem=='duplicate_part':full['parts'].append(copy.deepcopy(full['parts'][0]))
    elif problem=='duplicate_stock':full['parts'][1]['tickers'].append('A')
    elif problem=='wrong_count':request['expected_incremental_names']=2
    elif problem=='wrong_inputs':full['inputs_tag']='different'
    elif problem=='wrong_weights':full['stock_day_weights_sha256']='different'
    else:request['max_names_per_job']=50
    with pytest.raises(ValueError):addon.make_plan(original,full,request)


def test_incremental_weights_are_an_exact_nonnegative_date_join():
    full=pd.DataFrame(dict(date=['2020-01-02','2020-01-03'],stock_days=[10,12]))
    old=pd.DataFrame(dict(date=['2020-01-03','2020-01-02'],stock_days=[9,7]))
    result=addon.incremental_weights(full,old.sort_values('date'))
    assert result.stock_days.tolist()==[3,3]
    assert result.stock_days.dtype=='int64'
    full.loc[0,'stock_days']=6
    with pytest.raises(ValueError,match='remove original'):addon.incremental_weights(full,old.sort_values('date'))


def test_build_authenticates_pinned_member_manifest_before_any_compute(tmp_path,monkeypatch):
    from ci import compact_world_build as base
    original,full,request=fixture();plan=addon.make_plan(original,full,request)
    plan['runtime']={'test':'same-runtime'}
    meta=tmp_path/'member.json';meta.write_bytes(b'original-meta')
    plan['unique_raw_source_assets']=[dict(release='new',asset='same_name.json',sha256=addon.sha(meta.read_bytes()))]
    raw=json.dumps(plan).encode();file=tmp_path/'plan.json';file.write_bytes(raw)
    monkeypatch.setattr(addon,'download_asset',lambda tag,name,directory:file if name=='COMPACT_WORLD_BUILD_PLAN.json' else meta)
    monkeypatch.setattr(addon,'verify_compute',lambda request:None)
    monkeypatch.setattr(addon,'runtime_spec',lambda:dict(test='same-runtime'))
    calls=[];monkeypatch.setattr(base,'build',lambda *args:calls.append(args))
    addon.build(tmp_path,'new-inputs',0,addon.sha(raw));assert len(calls)==1
    meta.write_bytes(b'changed-meta')
    with pytest.raises(ValueError,match='source differs'):addon.build(tmp_path,'new-inputs',0,addon.sha(raw))
    assert len(calls)==1
    meta.write_bytes(b'original-meta')
    monkeypatch.setattr(addon,'runtime_spec',lambda:dict(test='changed-runtime'))
    with pytest.raises(ValueError,match='runtime differs'):addon.build(tmp_path,'new-inputs',0,addon.sha(raw))
    assert len(calls)==1


@pytest.mark.parametrize('wrong_days',[False,True])
def test_finalizer_requires_complete_membership_payload_and_stock_day_total(tmp_path,monkeypatch,wrong_days):
    original,full,request=fixture();plan=addon.make_plan(original,full,request)
    plan.update(incremental_stock_days=30,unique_raw_source_assets=[],unique_raw_source_bytes=5,runtime={'test':'same-runtime'})
    raw=json.dumps(plan).encode();file=tmp_path/'plan.json';file.write_bytes(raw)
    monkeypatch.setenv('GITHUB_RUN_ID','901');monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1');monkeypatch.setenv('GITHUB_SHA','new-code')
    monkeypatch.setattr(addon,'checked',lambda *a:file)
    def download(tag,name,directory):
        index=int(tag.rsplit('-',1)[1]);part=plan['parts'][index]
        rows=[dict(ticker=t,release=tag,asset=t.encode().hex()+'.diagnostic_answers.tar.zst',answer_container_sha256='payload',
                   answer_container_bytes=7,shared_registry_sha256='registry',diagnostic_questions=68904,
                   roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT',query_rows=9 if wrong_days else 10) for t in part['tickers']]
        state=dict(status='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD',source_part=part,source_commit='new-code',
                   inputs_release='new-inputs',recipe_fingerprint='corrected',completed=rows,excluded=[])
        directory=Path(directory);directory.mkdir(exist_ok=True);target=directory/name;target.write_text(json.dumps(state));return target
    def inventory(tag):
        index=int(tag.rsplit('-',1)[1]);return {t.encode().hex()+'.diagnostic_answers.tar.zst':dict(size=7,digest='sha256:payload') for t in plan['parts'][index]['tickers']}
    monkeypatch.setattr(addon,'download_asset',download);monkeypatch.setattr(addon,'asset_index',inventory)
    monkeypatch.setattr(addon,'gh_retry',lambda *a:None)
    published=[];monkeypatch.setattr(addon,'publish_assets',lambda tag,*files:published.extend(p.name for p in files))
    if wrong_days:
        with pytest.raises(ValueError,match='incomplete'):addon.finalize(tmp_path,'new-inputs',addon.sha(raw))
    else:addon.finalize(tmp_path,'new-inputs',addon.sha(raw))
    result=json.loads((tmp_path/'PRICE_RAW_ADDON_MEASURED_V1.json').read_text())
    assert len(result['completed'])==3 and result['completed_stock_days']==(27 if wrong_days else 30)
    assert result['status'].endswith('INCOMPLETE' if wrong_days else 'COMPLETE_NOT_WORLD')
    assert result['world_gate']=='NOT_PROVEN' and result['global_coverage_gate']=='NOT_COMPOSED_WITH_BASE_AND_TIMEOUT_RECOVERY'
    assert published==['PRICE_RAW_ADDON_MEASURED_V1.json']
