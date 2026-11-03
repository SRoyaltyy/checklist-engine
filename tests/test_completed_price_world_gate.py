from copy import deepcopy
import json

import pytest

from ci.completed_price_world_gate import (TIMEFRAMES, assess, sha, validate_registry,
                                          validate_worker, verify_payloads)


def row(name='A'):
    return dict(ticker=name, release='public', asset=name + '.zst', answer_container_bytes=123,
                answer_container_sha256='a' * 64, shared_registry_sha256='b' * 64,
                diagnostic_questions=68904, roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT', query_rows=10)


def inventory(record):
    return {'public': {record['asset']: dict(size=123, digest='sha256:' + 'a' * 64, state='uploaded')}}


@pytest.mark.parametrize('mutation', ['missing', 'digest', 'size', 'state', 'draft', 'registry', 'roundtrip', 'duplicate'])
def test_full_payload_validation_rejects_partial_or_changed_evidence(mutation):
    r = row()
    inventories = inventory(r)
    asset = inventories['public'][r['asset']]
    rows = [r]
    if mutation == 'missing':
        inventories['public'].clear()
    elif mutation == 'digest':
        asset['digest'] = 'sha256:' + 'c' * 64
    elif mutation == 'size':
        asset['size'] += 1
    elif mutation == 'state':
        asset['state'] = 'starter'
    elif mutation == 'draft':
        asset['_draft_release'] = True
    elif mutation == 'registry':
        r['shared_registry_sha256'] = 'wrong'
    elif mutation == 'roundtrip':
        r['roundtrip'] = 'NOT_CHECKED'
    else:
        rows.append(deepcopy(r))
    with pytest.raises(ValueError):
        verify_payloads(rows, 'b' * 64, inventories)


def test_payload_pass_remains_metadata_only():
    r = row()
    result = verify_payloads([r], 'b' * 64, inventory(r))
    assert result['tickers'] == 1 and result['status'] == 'PASS'
    assert 'bodies not reread' in result['scope']


@pytest.fixture(scope='module')
def registry():
    result = {}
    for tf in TIMEFRAMES:
        questions = [dict(question_id=f'C{i}:{facet}__{tf}', outcomes=[0, 1], formula='finite x > y; available_from <= D')
                     for i in range(1044) for facet in ('rising1', 'above_mean20', 'above_mean_plus_sd20')]
        digest = sha(json.dumps(questions, sort_keys=True, separators=(',', ':')).encode())
        result[digest] = questions
    return result


def test_registry_covers_the_actual_diagnostic_grid_but_is_not_canonical(registry):
    result = validate_registry(registry, 'b' * 64)
    assert result['questions'] == 68904 and result['columns_per_timeframe'] == 1044
    assert len(result['timeframes']) == 22
    assert result['kind'].endswith('NOT_CANONICAL_BINARY_MASTER')


def test_registry_digest_and_missing_timeframe_are_rejected(registry):
    changed = dict(registry)
    changed.pop(next(iter(changed)))
    with pytest.raises(ValueError, match='inventory differs'):
        validate_registry(changed, 'b' * 64)
    changed = dict(registry)
    key = next(iter(changed))
    changed['wrong'] = changed.pop(key)
    with pytest.raises(ValueError, match='digest differs'):
        validate_registry(changed, 'b' * 64)


def test_diagnostic_worker_mask_claim_is_hash_bound():
    raw = b'eligibility_mask_sha256=sha(np.ones(len(query),dtype=np.uint8).tobytes())'
    validate_worker(raw, dict(sha256=sha(raw)))
    with pytest.raises(ValueError, match='worker differs'):
        validate_worker(raw + b'changed', dict(sha256=sha(raw)))
    with pytest.raises(ValueError, match='policy changed'):
        validate_worker(b'other policy', dict(sha256=sha(b'other policy')))


@pytest.fixture
def sources():
    composed = dict(completed=[row(), row('B')], excluded=[], shard_errors=[], completed_tickers=2, build_excluded_tickers=0,
                    original_universe=3, source_excluded_tickers=1,
                    storage_gate='PASS_PRICE_RESERVATION_ONLY_NOT_WORLD', measured_price_dependency_bytes=500)
    plan = dict(parts=[dict(tickers=['A', 'B'])], accepted_tickers=2,
                request=dict(hard_world_cap_bytes=1000, corrected_recipe_fingerprint='new'))
    return dict(composed=composed, plan=plan, registry=dict(questions=68904),
                payloads=dict(status='PASS', tickers=2),
                sample=dict(sample_stocks=1, run=123, compared_cells=222, prefix_mismatch_blocks=0, price_v1_gate='PASS'),
                reconstruction=dict(samples=[1, 2, 3], stock_recipe_fingerprint='old'))


def test_source_and_storage_pass_cannot_promote_sample_to_world_proof(sources):
    result = assess(**sources)
    assert result['world_gate'] == 'NOT_PROVEN' and result['scoring_gate'] == 'CLOSED'
    assert result['full_cohort_price_PIT'] == 'UNMEASURED'
    assert result['checks']['retained_price_cohort_and_current_payload_metadata']['status'] == 'PASS'
    assert result['checks']['full_cohort_price_prefix_PIT']['status'] == 'SCOPE_INCOMPLETE'
    assert 'canonical_binary_price_answers_and_quality' in result['failing_checks']
    assert 'historical_tradeable_and_nominal_100M_eligibility' in result['failing_checks']


def test_incomplete_cohort_and_changed_sample_fail_closed(sources):
    changed = deepcopy(sources)
    changed['plan']['parts'][0]['tickers'].append('C')
    with pytest.raises(ValueError, match='cohort'):
        assess(**changed)
    sources['sample']['prefix_mismatch_blocks'] = 1
    assert assess(**sources)['checks']['full_cohort_price_prefix_PIT']['status'] == 'FAIL'


def test_declared_storage_pass_cannot_hide_an_actual_overrun(sources):
    sources['composed']['measured_price_dependency_bytes'] = 1001
    assert assess(**sources)['checks']['price_dependency_storage_reservation']['status'] == 'FAIL'
