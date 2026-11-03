import copy
import json

import pytest

from ci.price_pit_missing_recovery import (ROOT, REQUEST, latest_receipt, original_tag,
    selected_failures, validate_request, validate_state, worker_unchanged)


def test_bound_recovery_keeps_the_observed_source_and_exact_failed_scope():
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    assert len(request['failed_indices']) == 142 and request['expected_selected_names'] == 6799
    worker_unchanged()


@pytest.mark.parametrize('key,value', [('failed_indices', [33, 34]), ('worker_commit', 'different'),
    ('expected_selected_names', 8439), ('reserved_release_ids', {})])
def test_changed_source_scope_or_namespace_cannot_start_recovery(key, value):
    request = copy.deepcopy(json.loads((ROOT / REQUEST).read_bytes()))
    request[key] = value
    with pytest.raises(ValueError, match='scope'):
        validate_request(request)


def job(status='completed', conclusion='failure'):
    return dict(id=123, name='measure (34)', status=status, conclusion=conclusion, completed_at='time')


def test_only_actual_failed_original_jobs_can_be_selected():
    assert selected_failures([job()], [34])[34]['job_id'] == 123
    for jobs in ([job(conclusion='success')], [job(status='in_progress', conclusion=None)], [job(), job()], []):
        with pytest.raises(ValueError):
            selected_failures(jobs, [34])


@pytest.mark.parametrize('index', [33, 176, '34', 40621517496])
def test_recovery_never_writes_successful_or_protected_namespaces(index):
    with pytest.raises(ValueError):
        original_tag(index)


def test_partition_preserves_unmeasured_names_without_drops_or_duplicates():
    validate_state({'records': [{'ticker': 'A'}], 'unmeasured': [{'ticker': 'B'}]}, ['A', 'B'])
    for state in ({'records': [{'ticker': 'A'}], 'unmeasured': []},
                  {'records': [{'ticker': 'A'}], 'unmeasured': [{'ticker': 'A'}]}):
        with pytest.raises(ValueError):
            validate_state(state, ['A', 'B'])


def test_metadata_only_finalizer_retry_finds_actual_part_attempts_without_recomputing():
    names = {'PRICE_FULL_COHORT_PIT_PART_RECOVERY_123_1.json': {},
             'PRICE_FULL_COHORT_PIT_PART_RECOVERY_123_2.json': {},
             'PRICE_FULL_COHORT_PIT_PART_RECOVERY_124_9.json': {}}
    assert latest_receipt(names, '123') == 'PRICE_FULL_COHORT_PIT_PART_RECOVERY_123_2.json'
    with pytest.raises(ValueError):
        latest_receipt(names, '125')
