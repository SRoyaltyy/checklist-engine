import copy
import json
import os

import pytest

from ci.price_pit_dispatch_selector import (CONTROLS, COUNTEREXAMPLES, PROFILES, REQUEST, ROOT,
                                            comparison, profile_env, repetitions_for, summarize,
                                            validate_request, verdict)


def stock(cells, gate='PASS', ticker='AQMS'):
    return dict(ticker=ticker, packet_replay_gate=gate, prefix_gate='PASS', alignment_gate='PASS',
                packet_replay=[dict(timeframe='1d', different_cells=cells, missing_differences=0,
                                    differences=[] if not cells else [{'question_id': 'x', 'different_cells': cells}])])


def result(ticker, profile, cells, repetition=1):
    return dict(ticker=ticker, role='counterexample', profile=profile, repetition=repetition,
                summary=summarize(stock(cells, ticker=ticker)))


def control_result(ticker, profile, cells=0):
    return dict(ticker=ticker, role='control', profile=profile, repetition=1,
                summary=summarize(stock(cells, ticker=ticker)))


def grid(cells_by_profile):
    out = []
    for ticker in COUNTEREXAMPLES:
        results = [result(ticker, 'native', cells_by_profile['native']),
                   result(ticker, 'avx512_off', cells_by_profile['avx512_off']),
                   result(ticker, 'no_numpy_dispatch', cells_by_profile['no_numpy_dispatch'], 1),
                   result(ticker, 'no_numpy_dispatch', cells_by_profile['no_numpy_dispatch'], 2)]
        out.append(comparison(ticker, 'counterexample', stock(1, gate='FAIL', ticker=ticker), results))
    for ticker in CONTROLS:
        results = [control_result(ticker, 'native'), control_result(ticker, 'avx512_off'),
                   control_result(ticker, 'no_numpy_dispatch')]
        out.append(comparison(ticker, 'control', stock(0, ticker=ticker), results))
    return out


def test_selector_prefers_conservative_continuation_pin():
    outcome = verdict(grid({'native': 1, 'avx512_off': 0, 'no_numpy_dispatch': 0}))
    assert outcome['outcome'] == 'SELECTED'
    assert outcome['selected_profiles'] == ['avx512_off', 'no_numpy_dispatch']
    assert outcome['continuation_profile'] == 'no_numpy_dispatch'
    assert outcome['profiles']['native']['counterexamples_recovered'] is False


def test_selector_never_overclaims_when_no_profile_recovers():
    outcome = verdict(grid({'native': 1, 'avx512_off': 3, 'no_numpy_dispatch': 2}))
    assert outcome['outcome'] == 'UNRESOLVED'
    assert outcome['selected_profiles'] == []
    assert outcome['continuation_profile'] is None


def test_all_profiles_match_means_dispatch_does_not_explain_the_flip():
    outcome = verdict(grid({'native': 0, 'avx512_off': 0, 'no_numpy_dispatch': 0}))
    assert outcome['outcome'] == 'ALL_PROFILES_MATCH'
    assert outcome['selected_profiles'] == PROFILES


def test_comparison_rejects_foreign_ticker_and_wrong_declared_gate():
    results = [result('AQMS', 'native', 1)]
    with pytest.raises(ValueError, match='ticker'):
        comparison('AZIO', 'counterexample', stock(1, gate='FAIL', ticker='AZIO'), results)
    with pytest.raises(ValueError, match='gate'):
        comparison('AVGO', 'control', stock(1, gate='FAIL', ticker='AVGO'),
                   [control_result('AVGO', 'native')])


def test_request_scope_and_frozen_worker_cannot_change():
    request = json.loads((ROOT / REQUEST).read_bytes())
    validate_request(request)
    for key, value in [('profiles', ['native']), ('worker_lf_sha256', 'wrong'), ('execute', 'true'),
                       ('repetitions', {'counterexample_native': 2, 'counterexample_avx512_off': 1, 'counterexample_no_numpy_dispatch': 2, 'control': 1})]:
        mutated = copy.deepcopy(request)
        mutated[key] = value
        with pytest.raises(ValueError, match='scope'):
            validate_request(mutated)


def test_native_profile_refuses_overridden_env(monkeypatch):
    monkeypatch.setenv('NPY_DISABLE_CPU_FEATURES', 'AVX512F')
    with pytest.raises(ValueError, match='native'):
        profile_env('native', ['AVX512F'])
    monkeypatch.delenv('NPY_DISABLE_CPU_FEATURES')
    monkeypatch.delenv('OPENBLAS_CORETYPE', raising=False)
    assert profile_env('native', ['AVX512F']) is None


def test_avx512_off_profile_disables_only_avx512_features(monkeypatch):
    monkeypatch.delenv('NPY_DISABLE_CPU_FEATURES', raising=False)
    monkeypatch.delenv('OPENBLAS_CORETYPE', raising=False)
    env = profile_env('avx512_off', ['AVX2', 'AVX512F', 'AVX512CD', 'AVX512_SKX'])
    assert env['NPY_DISABLE_CPU_FEATURES'] == 'AVX512F,AVX512CD,AVX512_SKX'
    assert 'NPY_DISABLE_CPU_FEATURES' not in os.environ
    with pytest.raises(ValueError, match='no AVX512'):
        profile_env('avx512_off', ['AVX2', 'SSE42'])


def test_no_dispatch_profile_sets_only_child_env(monkeypatch):
    monkeypatch.delenv('NPY_DISABLE_CPU_FEATURES', raising=False)
    monkeypatch.delenv('OPENBLAS_CORETYPE', raising=False)
    env = profile_env('no_numpy_dispatch', ['AVX512F', 'AVX512CD'])
    assert env['NPY_DISABLE_CPU_FEATURES'] == 'AVX512F,AVX512CD'
    assert 'NPY_DISABLE_CPU_FEATURES' not in os.environ
    with pytest.raises(ValueError, match='no features'):
        profile_env('no_numpy_dispatch', [])


def test_repetition_matrix_matches_the_declared_request():
    request = json.loads((ROOT / REQUEST).read_bytes())
    assert repetitions_for(request, 'counterexample', 'native') == 1
    assert repetitions_for(request, 'counterexample', 'avx512_off') == 1
    assert repetitions_for(request, 'counterexample', 'no_numpy_dispatch') == 2
    assert repetitions_for(request, 'control', 'native') == 1
    assert repetitions_for(request, 'control', 'no_numpy_dispatch') == 1
