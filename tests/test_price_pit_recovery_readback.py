"""Synthetic receipt metadata only; never a market replay."""
import copy
import json

import pytest

from ci import price_pit_recovery_readback as audit


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


@pytest.fixture
def synthetic_recovery(monkeypatch):
    names = [f'SYNTHETIC{i:04d}' for i in range(audit.SELECTED)]
    groups = [names[i:i + 48] for i in range(0, len(names), 48)]
    rows, extra = divmod(audit.QUERY_ROWS, len(names))
    base = dict(work_parts=[dict(tickers=[]) for _ in range(34)] + [dict(tickers=g) for g in groups],
        references=[dict(ticker=t, query_rows=rows + (i < extra)) for i, t in enumerate(names)])
    base_raw = encoded(base)
    monkeypatch.setattr(audit, 'PLAN_SHA', audit.fingerprint(base_raw)['sha256'])
    parts, states, evidence = [], {}, dict(records=[], errors=[])
    for index, group in zip(audit.INDICES, groups):
        tag = audit.INPUT_RELEASE.removesuffix('-inputs') + f'-{index:03d}'
        failure = dict(job_id=index, name=f'measure ({index})', conclusion='failure', completed_at='2026-11-02T00:00:00Z')
        parts.append(dict(index=index, tag=tag, expected_names=group, original_failure=failure))
        records = [dict(ticker=t, release=tag, asset=t.encode().hex() + '.pit.json.gz', bytes=123,
                        sha256='a' * 64, reused=i % 2 == 0) for i, t in enumerate(group)]
        evidence['records'].extend({k: v for k, v in r.items() if k != 'reused'} for r in records)
        states[index] = dict(format='PRICE_FULL_COHORT_PIT_PART_RECOVERY_V1', index=index, release=tag,
            base_plan_sha256=audit.PLAN_SHA, recovery_inputs=audit.RECOVERY_INPUTS,
            actual_recovery_run_id=audit.RUN, actual_recovery_attempt='1', recovery_commit=audit.COMMIT,
            worker_lf_sha256=audit.WORKER_SHA, original_failure=failure, expected_names=group,
            records=records, unmeasured=[], scoring_gate='CLOSED')
    plan = dict(format='PRICE_FULL_COHORT_PIT_RECOVERY_PLAN_V1', parts=parts,
        actual_recovery_run_id=audit.RUN, recovery_commit=audit.COMMIT, worker_lf_sha256=audit.WORKER_SHA,
        base_plan=dict(release=audit.INPUT_RELEASE, asset='PRICE_FULL_COHORT_PIT_PLAN_V1.json', sha256=audit.PLAN_SHA),
        scoring_gate='CLOSED')
    plan_raw = encoded(plan)
    monkeypatch.setattr(audit, 'RECOVERY_SHA', audit.fingerprint(plan_raw)['sha256'])
    for state in states.values():
        state['recovery_plan_sha256'] = audit.RECOVERY_SHA
    report = dict(run_id=audit.RUN, run_attempt='2', measurement='MEASURED', scoring_gate='CLOSED')
    return base_raw, encoded(report), evidence, plan_raw, states


def check(data, mutation=None):
    base, report, evidence, plan, states = copy.deepcopy(data)
    first = states[34]
    if mutation == 'wrong_worker':
        first['worker_lf_sha256'] = '0' * 64
    elif mutation == 'wrong_attempt':
        first['actual_recovery_attempt'] = '2'
    elif mutation == 'wrong_failure':
        first['original_failure'] = dict(first['original_failure'], job_id=999)
    elif mutation == 'wrong_proof':
        first['records'][0]['sha256'] = 'b' * 64
    elif mutation == 'duplicate_name':
        first['records'][0] = copy.deepcopy(first['records'][1])
    elif mutation == 'non_boolean_reuse':
        first['records'][0]['reused'] = 1
    elif mutation == 'partial':
        first['unmeasured'] = [{'ticker': first['records'][0]['ticker']}]
    raw_states = {i: encoded(s) for i, s in states.items()}
    receipts = [dict(index=i, release=s['release'], asset=f'PRICE_FULL_COHORT_PIT_PART_RECOVERY_{audit.RUN}_1.json',
                     **audit.fingerprint(raw_states[i])) for i, s in states.items()]
    reused = sum(r['reused'] for s in states.values() for r in s['records'])
    summary = dict(format='PRICE_FULL_COHORT_PIT_RECOVERY_SUMMARY_V1', base_plan_sha256=audit.PLAN_SHA,
        recovery_plan_sha256=audit.RECOVERY_SHA, recovery_inputs=audit.RECOVERY_INPUTS,
        actual_recovery_run_id=audit.RUN, recovery_commit=audit.COMMIT, worker_lf_sha256=audit.WORKER_SHA,
        complete_report_sha256=audit.fingerprint(report)['sha256'], complete_measurement='MEASURED',
        selected_names=audit.SELECTED, reused_names=reused, newly_measured_names=audit.SELECTED - reused,
        part_receipts=receipts, scoring_gate='CLOSED')
    if mutation == 'missing_part':
        summary['part_receipts'] = receipts[:-1]
    elif mutation == 'false_accounting':
        summary['newly_measured_names'] += 1
    summary_raw = encoded(summary)
    inventories = []

    def inventory(tag, objects):
        inventories.append(dict(tag_name=tag, draft=False, assets=[dict(name=n, state='uploaded',
            size=len(raw), digest='sha256:' + audit.fingerprint(raw)['sha256']) for n, raw in objects]))

    inventory(f'price-full-cohort-pit-v1-{audit.RUN}-2-measured', [(audit.REPORT, report), (audit.SUMMARY, summary_raw)])
    inventory(audit.RECOVERY_INPUTS, [(audit.RECOVERY_PLAN, plan)])
    for receipt in receipts:
        inventory(receipt['release'], [(receipt['asset'], raw_states[receipt['index']])])
    if mutation == 'draft':
        inventories[-1]['draft'] = True
    elif mutation == 'different_public_body':
        inventories[-1]['assets'][0]['digest'] = 'sha256:' + '0' * 64
    return audit.validate_lineage(base, report, evidence, plan, summary_raw, raw_states, inventories)


def test_all_142_receipts_bind_complete_manifest_with_later_finalizer_attempt(synthetic_recovery):
    result = check(synthetic_recovery)
    assert result['part_receipts_verified'] == 142
    assert result['selected_names'] == 6799 and result['selected_query_rows'] == 10110205
    assert result['reused_names'] + result['newly_measured_names'] == 6799
    assert result['scoring_gate'] == 'CLOSED'


@pytest.mark.parametrize('mutation', ['wrong_worker', 'wrong_attempt', 'wrong_failure', 'wrong_proof',
    'duplicate_name', 'non_boolean_reuse', 'partial', 'missing_part', 'false_accounting', 'draft', 'different_public_body'])
def test_published_but_invalid_lineage_is_rejected(synthetic_recovery, mutation):
    with pytest.raises(ValueError):
        check(synthetic_recovery, mutation)


def test_sealed_plan_body_cannot_change(synthetic_recovery):
    base, report, evidence, plan, states = synthetic_recovery
    with pytest.raises(ValueError, match='sealed recovery plan'):
        audit.validate_lineage(base, report, evidence, plan + b' ', b'{}', {}, [])
