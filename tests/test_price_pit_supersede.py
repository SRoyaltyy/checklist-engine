import copy
import json

import pytest

from ci import price_pit_supersede as retire


def run(run_id, source, attempt, status='queued', conclusion=None):
    return dict(id=run_id, head_sha=source, run_attempt=attempt, event='push',
                head_branch='codex/price-full-cohort-pit',
                path='.github/workflows/price_pit_missing_recovery.yml',
                repository=dict(full_name=retire.REPOSITORY), status=status, conclusion=conclusion)


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_REPOSITORY', retire.REPOSITORY)
    request = tmp_path / 'request.json'
    request.write_text(json.dumps(dict(version=1, execute=True, obsolete_run_id=retire.OLD,
                                      corrected_run_id=retire.NEW)))
    monkeypatch.setattr(retire, 'REQUEST', request)
    monkeypatch.setattr(retire.time, 'sleep', lambda seconds: None)
    old = run(retire.OLD, retire.OLD_SHA, 3)
    new = run(retire.NEW, retire.NEW_SHA, 1, status='pending')
    monkeypatch.setattr(retire, 'read', lambda run_id: copy.deepcopy(old if run_id == retire.OLD else new))
    calls = []
    monkeypatch.setattr(retire.io, 'gh_retry', lambda *args: calls.append(args))
    return old, new, calls


@pytest.mark.parametrize('key,value', [('id', 40621517496), ('id', retire.NEW),
    ('head_sha', 'different'), ('run_attempt', 4), ('event', 'pull_request'),
    ('head_branch', 'main'), ('path', '.github/workflows/world.yml'),
    ('repository', dict(full_name='different/repository'))])
def test_changed_or_protected_identity_never_reaches_a_mutation(setup, key, value):
    old, _, calls = setup
    old[key] = value
    with pytest.raises(ValueError, match='identity'):
        retire.retire_old()
    assert calls == []


def test_failed_successor_cannot_trigger_cleanup(setup):
    _, new, calls = setup
    new.update(status='completed', conclusion='failure')
    with pytest.raises(ValueError, match='successor failed'):
        retire.retire_old()
    assert calls == []


def test_already_terminal_old_controller_is_a_read_only_noop(setup):
    old, _, calls = setup
    old.update(status='completed', conclusion='cancelled')
    retire.retire_old()
    assert calls == []


def test_normal_cancellation_finishes_without_force_or_successor_mutation(setup, monkeypatch):
    old, _, calls = setup
    def post(*args):
        calls.append(args)
        old.update(status='completed', conclusion='cancelled')
    monkeypatch.setattr(retire.io, 'gh_retry', post)
    retire.retire_old()
    assert calls == [('api', f'repos/{retire.REPOSITORY}/actions/runs/{retire.OLD}/cancel', '--method', 'POST')]
    report = json.loads(retire.Path('PRICE_PIT_SUPERSEDE_READBACK_V1.json').read_bytes())
    assert report['observations'][-1]['conclusion'] == 'cancelled'


def test_force_cancellation_requires_unanswered_normal_cancellation(setup, monkeypatch):
    old, _, calls = setup
    def post(*args):
        calls.append(args)
        if args[1].endswith('/force-cancel'):
            old.update(status='completed', conclusion='cancelled')
    monkeypatch.setattr(retire.io, 'gh_retry', post)
    retire.retire_old()
    assert [args[1].rsplit('/', 1)[1] for args in calls] == ['cancel', 'force-cancel']
    assert all(f'/runs/{retire.OLD}/' in args[1] for args in calls)


def test_changed_identity_during_wait_cannot_be_force_cancelled(setup, monkeypatch):
    old, _, calls = setup
    def post(*args):
        calls.append(args)
        old['run_attempt'] = 4
    monkeypatch.setattr(retire.io, 'gh_retry', post)
    with pytest.raises(ValueError, match='identity'):
        retire.retire_old()
    assert len(calls) == 1


def test_disabled_cleanup_never_reads_or_mutates_runs(setup, monkeypatch):
    _, _, calls = setup
    retire.REQUEST.write_text(json.dumps(dict(version=1, execute=False,
        obsolete_run_id=retire.OLD, corrected_run_id=retire.NEW)))
    monkeypatch.setattr(retire, 'read', lambda run_id: pytest.fail('disabled request cannot read a run'))
    with pytest.raises(ValueError, match='disabled'):
        retire.retire_old()
    assert calls == []
