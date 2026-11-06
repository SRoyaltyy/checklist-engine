import copy
import json
import subprocess

import pytest

from ci import price_pit_missing_recovery as recovery

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


@pytest.fixture
def release_item(monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'SRoyaltyy/checklist-engine')
    monkeypatch.setenv('GITHUB_RUN_ID', '999')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    monkeypatch.setattr(recovery.io, '_RELEASE_IDS', {})
    return dict(index=100, tag=original_tag(100), existing_release_id=None)


@pytest.mark.parametrize('draft', [False, True])
def test_stale_sealed_absence_reuses_current_public_or_draft_release(release_item, monkeypatch, draft):
    release = dict(id=17, tag_name=release_item['tag'], target_commitish=recovery.WORKER, draft=draft)
    monkeypatch.setattr(recovery.io, 'release_info', lambda tag: release)
    monkeypatch.setattr(recovery.io, 'gh_retry', lambda *args: pytest.fail('existing release must not be created again'))
    assert recovery.ensure_recovery_release(release_item) is release


def test_only_current_404_without_a_sealed_id_allows_creation(release_item, monkeypatch):
    release = dict(id=17, tag_name=release_item['tag'], target_commitish=recovery.WORKER, draft=True)
    responses = [subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 404: Not Found'), release]
    calls = []
    def read(tag):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(recovery.io, 'release_info', read)
    monkeypatch.setattr(recovery.io, 'gh_retry', lambda *args: calls.append(args))
    assert recovery.ensure_recovery_release(release_item) is release
    assert len(calls) == 1 and calls[0][:3] == ('release', 'create', release_item['tag'])


def test_permission_failure_is_not_absence_and_never_creates(release_item, monkeypatch):
    def denied(tag):
        raise subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 403: Forbidden')
    monkeypatch.setattr(recovery.io, 'release_info', denied)
    monkeypatch.setattr(recovery.io, 'gh_retry', lambda *args: pytest.fail('permission error cannot create a release'))
    with pytest.raises(subprocess.CalledProcessError):
        recovery.ensure_recovery_release(release_item)


def test_missing_sealed_release_id_cannot_be_replaced(release_item, monkeypatch):
    release_item['existing_release_id'] = 17
    def absent(tag):
        raise subprocess.CalledProcessError(1, ['gh'], stderr='HTTP 404: Not Found')
    monkeypatch.setattr(recovery.io, 'release_info', absent)
    monkeypatch.setattr(recovery.io, 'gh_retry', lambda *args: pytest.fail('sealed release identity cannot be replaced'))
    with pytest.raises(ValueError, match='disappeared'):
        recovery.ensure_recovery_release(release_item)


@pytest.mark.parametrize('key,value', [('tag_name', 'other'), ('target_commitish', 'other')])
def test_current_release_must_keep_exact_namespace_and_worker(release_item, monkeypatch, key, value):
    release = dict(id=17, tag_name=release_item['tag'], target_commitish=recovery.WORKER, draft=False)
    release[key] = value
    monkeypatch.setattr(recovery.io, 'release_info', lambda tag: release)
    with pytest.raises(ValueError, match='identity'):
        recovery.ensure_recovery_release(release_item)


def test_reused_proof_does_not_upload_a_redundant_checkpoint(release_item, monkeypatch, tmp_path):
    monkeypatch.setattr(recovery.io, 'publish_assets', lambda *args: pytest.fail('reused bytes already durable'))
    recovery.publish_checkpoint(tmp_path, release_item['tag'], {'records': [{}], 'unmeasured': []}, [], True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('failure', [False, True])
def test_new_proof_or_explicit_failure_keeps_durable_checkpoint(release_item, monkeypatch, tmp_path, failure):
    state = dict(records=[] if failure else [{'ticker': 'SYNTHETIC'}],
                 unmeasured=[{'ticker': 'SYNTHETIC', 'reason': 'failure'}] if failure else [])
    files = []
    if not failure:
        proof = tmp_path / 'synthetic.pit.json.gz'
        proof.write_bytes(b'synthetic proof')
        files.append(proof)
    calls = []
    monkeypatch.setattr(recovery.io, 'publish_assets', lambda *args: calls.append(args))
    recovery.publish_checkpoint(tmp_path, release_item['tag'], state, files, False)
    assert len(calls) == 1 and calls[0][0] == release_item['tag']
    assert list(calls[0][1:-1]) == files
    checkpoint = calls[0][-1]
    assert checkpoint.name == 'recovery_999_1_0001.json' and json.loads(checkpoint.read_bytes()) == state


def test_reused_proof_cannot_be_republished(release_item, tmp_path):
    with pytest.raises(ValueError, match='republished'):
        recovery.publish_checkpoint(tmp_path, release_item['tag'], {}, [tmp_path / 'old'], True)


def test_resume_never_remeasures_a_completed_name():
    recovery.allow_new_measurement({'allowed_new_names': ['KGRN']}, 'KGRN')
    with pytest.raises(ValueError, match='refusing to remeasure'):
        recovery.allow_new_measurement({'allowed_new_names': ['KGRN']}, 'SYNTHETIC_RETAINED')
    recovery.allow_new_measurement({}, 'SYNTHETIC_INITIAL_MISSING')


def test_resume_request_binds_the_exact_published_gap():
    request = json.loads((ROOT / REQUEST).read_bytes())
    request.update(resume_report=copy.deepcopy(recovery.RESUME_REPORT), allowed_new_names=['KGRN'])
    validate_request(request)
    for key, value in [('resume_report', dict(recovery.RESUME_REPORT, sha256='0' * 64)),
                       ('allowed_new_names', ['OTHER'])]:
        changed = copy.deepcopy(request)
        changed[key] = value
        with pytest.raises(ValueError, match='resume scope'):
            validate_request(changed)


@pytest.mark.parametrize('mutation', [None, 'missing_names', 'rows', 'recipe', 'source', 'plan', 'open', 'false_complete'])
def test_resume_report_must_preserve_scope_source_and_closed_gate(mutation):
    base = dict(expected_names=['SYNTHETIC', 'KGRN'], references=[dict(ticker='SYNTHETIC', query_rows=7),
        dict(ticker='KGRN', query_rows=1712)], expected_query_rows=1719, source_commit='price-source',
        composition={'test': True}, frozen_build_request={'corrected_recipe_fingerprint': 'recipe'})
    report = dict(measurement='PARTIAL_NOT_MEASURED_FULL_COHORT', plan_sha256=recovery.PLAN_SHA,
        inputs_release=recovery.INPUT_RELEASE, run_id='41655284751', run_attempt='2', expected_names=2,
        measured_names=1, expected_query_rows=1719, measured_query_rows=7, unmeasured_names=['KGRN'],
        source_commit='price-source', composition={'test': True}, frozen_recipe='recipe', scoring_gate='CLOSED')
    if mutation is None:
        recovery.validate_resume_report(report, base, ['KGRN'])
        return
    key, value = {'missing_names': ('unmeasured_names', []), 'rows': ('measured_query_rows', 8),
        'recipe': ('frozen_recipe', 'different'), 'source': ('source_commit', 'different'),
        'plan': ('plan_sha256', 'different'), 'open': ('scoring_gate', 'OPEN'),
        'false_complete': ('measurement', 'MEASURED')}[mutation]
    report[key] = value
    with pytest.raises(ValueError, match='resume report'):
        recovery.validate_resume_report(report, base, ['KGRN'])
