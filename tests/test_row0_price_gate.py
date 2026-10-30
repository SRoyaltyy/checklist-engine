import copy
import json
from pathlib import Path
import pytest
from ci.row0_price_gate import reconcile
from ci.terminal_price_recovery import compose


def fixture():
    request=json.loads(Path('ci/COMPACT_WORLD_BUILD_REQUEST.json').read_text())
    prior=request['prior_timeout_ledger']['tickers'];names=prior+[f'B{i:04d}' for i in range(8311)]
    first=names[:-50];parts=[];offset=0
    for i in range(172):
        count=len(first)//172+(i<len(first)%172)
        parts.append(dict(release='raw',part=str(i),tickers=first[offset:offset+count]));offset+=count
    parts.append(dict(release='raw',part='172',tickers=names[-50:]))
    original=dict(request=dict(inputs_tag=request['inputs_tag']),parts=parts,accepted_tickers=8316)
    extra=[f'X{i:03d}' for i in range(131)];full_parts=copy.deepcopy(parts)+[dict(release='addon',part='0',tickers=extra)]
    full=dict(status='FULL_ACCEPTED_PRICE_BASE_ONLY_NOT_WORLD',inputs_tag=request['inputs_tag'],selected_tickers=8447,
        query_rows=12560808,stock_day_weights_sha256=request['full_raw_source']['stock_day_weights_sha256'],parts=full_parts)
    missing=names[-50:]+prior
    base=dict(completed=[dict(ticker=t,query_rows=1) for t in names if t not in missing],
              excluded=[dict(ticker=t,reason='STOCK_TIMEOUT' if t in prior else 'SHARD_RESULT_UNVERIFIED') for t in missing])
    base['completed'][0]['query_rows']+=12560808-8447
    addon=dict(status='RAW_INCREMENTAL_PRICE_ANSWERS_COMPLETE_NOT_WORLD',errors=[],excluded=[],completed=[dict(ticker=t,query_rows=1) for t in extra])
    ordered=missing[:24]+[prior[0]]+missing[24:50]+prior[1:]
    recovered=[dict(ticker=t,query_rows=1,origin_kind='EXACT_DRAFT_CHECKPOINT_COPY' if i<24 else
        'EXISTING_VERIFIED_GUARDED_SAMPLE' if i==24 else 'NEW_GUARDED_TERMINAL_CALCULATION',
        recipe_fingerprint='pinned',release='recovered',asset=t+'.bin',answer_container_sha256='a'*64) for i,t in enumerate(ordered)]
    recovery=dict(status='TERMINAL_PRICE_55_RECOVERED_NOT_WORLD',errors=[],excluded=[],completed=recovered)
    composition=compose(base,addon,full,recovered,{})
    plan=dict(request=request,parts=full_parts,accepted_tickers=8447,source_input_extension=dict(incremental_tickers=extra),
        prior_timeout_dispositions=[dict(ticker=t,prior_reason='STOCK_TIMEOUT',disposition='GUARDED_RECIPE_RETRY_WITH_BOUNDED_WORKER') for t in prior])
    registry={'synthetic':[dict(question_id=f'feature{i}:rising1__1d') for i in range(68904)]}
    return [original,base,addon,full,recovery,composition,plan,registry]


def test_full_name_coverage_never_opens_world_or_scoring_gate():
    report,ledger,coverage=reconcile(*fixture())
    assert report['source_part_name_coverage']=='173/173' and report['part172_recovered_names']==50
    assert report['original_run_job_completion']=='172/173_UNCHANGED'
    assert report['diagnostic_membership_gate']=='PASS'
    assert report['price_world_gate']=='FAIL' and report['scoring_gate']=='CLOSED'
    assert len(ledger)==len({r['ticker'] for r in ledger})==55
    assert len(coverage)==173 and all(r['covered']==r['expected'] for r in coverage)


@pytest.mark.parametrize('problem',['part_rewritten','added_missing','timeout_missing','old_omission_missing',
                                  'composition_changed','registry_duplicate','unguarded_request','resolution_unexplained'])
def test_partial_or_changed_evidence_cannot_pass_name_reconciliation(problem):
    args=fixture();original,base,addon,full,recovery,composition,plan,registry=args
    if problem=='part_rewritten':plan['parts']=copy.deepcopy(plan['parts']);plan['parts'][0]['release']='other'
    elif problem=='added_missing':plan['source_input_extension']['incremental_tickers'].pop()
    elif problem=='timeout_missing':plan['prior_timeout_dispositions'].pop()
    elif problem=='old_omission_missing':recovery['completed'].pop()
    elif problem=='composition_changed':composition['completed'][0]['query_rows']+=1
    elif problem=='registry_duplicate':registry['synthetic'][-1]=registry['synthetic'][0]
    elif problem=='unguarded_request':plan['request']=dict(plan['request'],recipe_transform=None)
    else:recovery['completed'][0]['origin_kind']='UNEXPLAINED'
    with pytest.raises(ValueError):reconcile(*args)
