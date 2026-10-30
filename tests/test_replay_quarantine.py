import copy
import json
from pathlib import Path
import pytest
from world_replay_quarantine import load_policy,filter_parts,v1_eligible,excluded_names,REASON


def test_owner_scope_and_exact_original_denominator_are_preserved():
    policy=load_policy()
    assert excluded_names()==frozenset(('FEIM','HHS','JHI','NKTR','OCGN','ABX','AMTD','CATO'))
    assert policy['v1_names']==8439 and policy['quarantined_stock_days']==13520
    assert policy['v1_stock_days']==12547288 and policy['v1_pct_original_names']>95
    assert all(r['reason_code']==REASON and r['affected_predicates'] for r in policy['records'])


def test_quarantine_overrides_pit_but_unknown_other_names_stay_unknown():
    for ticker in excluded_names():
        assert v1_eligible(ticker,True) is False and v1_eligible(ticker,None) is False
    assert v1_eligible('CONTROL',True) is True
    assert v1_eligible('CONTROL',False) is False
    assert v1_eligible('CONTROL',None) is None
    with pytest.raises(TypeError):v1_eligible('CONTROL',1)


def test_new_work_list_excludes_all_eight_without_rewriting_source_or_archive_bindings():
    policy=load_policy();parts=[dict(release='source',part='one',archive_sha256='pinned',tickers=['CONTROL',*sorted(excluded_names())])]
    original=copy.deepcopy(parts);active,records=filter_parts(parts,policy)
    assert parts==original and active==[dict(parts[0],tickers=['CONTROL'])] and len(records)==8
    with pytest.raises(ValueError):filter_parts([dict(parts[0],tickers=['CONTROL'])],policy)


def test_changed_owner_policy_is_not_silently_accepted(tmp_path):
    file=tmp_path/'policy.json';policy=load_policy();policy['records'].pop();file.write_text(json.dumps(policy))
    with pytest.raises(ValueError,match='digest'):load_policy(file)


def test_v1_answer_entry_point_never_reads_excluded_or_unknown_prices():
    from world_binary_price import evaluate_v1_price
    class Forbidden:
        def get(self,*args):raise AssertionError('excluded prices read')
    definition=dict(comparator='>',comparison_threshold='0')
    assert evaluate_v1_price(definition,Forbidden(),None,None,ticker='FEIM',pit_eligible=True).answer=='NOT_EVALUABLE'
    assert evaluate_v1_price(definition,Forbidden(),None,None,ticker='CONTROL',pit_eligible=None).answer=='NOT_EVALUABLE'


def test_ex_quarantine_gate_waives_only_known_minor_replay_names():
    from ci.price_gate_ex_quarantine import restate
    policy=load_policy();denied=sorted(excluded_names());names=denied+[f'C{i:04d}' for i in range(8439)]
    counts={r['ticker']:r['source_query_stock_days'] for r in policy['records']}
    rows=[dict(ticker=t,query_rows=counts.get(t,1)) for t in names]
    rows[8]['query_rows']+=policy['v1_stock_days']-8439
    raw=[dict(release='raw',part='part',tickers=names)];active,_=filter_parts(raw,policy)
    plan=dict(raw_source_parts=raw,parts=active,accepted_tickers=8439,replay_quarantine=policy['records'],
              raw_source_excluded_tickers=280,source_excluded_tickers=288)
    replay=json.loads(Path('docs/ROW0_PART172_REPLAY_V1.json').read_text(encoding='utf-8'))
    prior=json.loads(Path('docs/ROW0_PRICE_WORLD_GATE_V1.json').read_text(encoding='utf-8'))
    result=restate(dict(completed=rows),replay,prior,plan,policy)
    assert result['known_replay_mismatch_gate'].startswith('PASS')
    assert result['price_world_gate']=='FAIL' and result['replay_diagnosis']=='OPTIONAL_NONBLOCKING_BACKGROUND'
    assert result['source_coverage_gate'].startswith('PASS') and result['scoring_gate']=='CLOSED'
    bad=copy.deepcopy(plan);bad['parts'][0]['tickers'].append(denied[0])
    with pytest.raises(ValueError):restate(dict(completed=rows),replay,prior,bad,policy)
