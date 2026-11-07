import copy
import json

import pytest

from ci.price_column_availability_probe import (REQUEST, CUTS, validate_request,
    validate_result, require_runner)
from world_price_availability import TIMEFRAMES, CALENDAR_SHA, load_contract


def test_runner_request_keeps_exact_frozen_scope_and_all_declared_controls():
    request = validate_request(json.loads(REQUEST.read_bytes()))
    assert request['controls'] == ['BPOP', 'DJCO', 'KGRN']
    assert request['expected_columns'] == 22968 and request['expected_names'] == 8439


@pytest.mark.parametrize('key,value', [('controls', ['BPOP']), ('prefix_cuts', ['2025-01-02']),
    ('expected_columns', 1044), ('base_plan_sha256', 'different'), ('execute', 1)])
def test_probe_cannot_narrow_or_change_the_declared_source(key, value):
    request = json.loads(REQUEST.read_bytes()); request[key] = value
    with pytest.raises(ValueError, match='exact measured source'):
        validate_request(request)


def test_local_environment_cannot_launch_real_price_probes(monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError, match='only on the authorized GitHub runner'):
        require_runner()


def fixture():
    def comparison(cells):
        return dict(cells=cells, different_cells=0, missing_differences=0, field_differences=[])
    return dict(status='PASS_FROZEN_PRICE_COLUMN_CLOCKS_AND_LEAK_TRAPS', ticker='SYNTHETIC',
        query_rows=7, columns_per_timeframe=1044, column_bindings=22968, timeframes=list(TIMEFRAMES),
        raw_sha256='a' * 64, calendar_sha256=CALENDAR_SHA,
        columns_lf_sha256=load_contract().columns_sha256, scoring_gate='CLOSED',
        checks=[dict(timeframe=tf, native_rows=2, columns=1044, query_rows=7, clock_pair_checks=3 * 1044,
            exact_alignment=comparison(7 * 1044), cuts=[dict(cut=cut, columns=1044,
            prefix=comparison(1044), future_perturbation=comparison(1044)) for cut in CUTS]) for tf in TIMEFRAMES])


def test_complete_synthetic_control_accepts_every_column_and_cut():
    validate_result(fixture(), 'SYNTHETIC', 7, 'a' * 64)


@pytest.mark.parametrize('damage', ['missing_tf', 'missing_field', 'missing_cut', 'leak',
                                  'partial_cells', 'wrong_source', 'false_scoring', 'missing_clocks'])
def test_partial_or_leaking_controls_cannot_be_claimed_as_pass(damage):
    result = copy.deepcopy(fixture())
    if damage == 'missing_tf':
        result['checks'].pop()
    elif damage == 'missing_field':
        result['checks'][0]['columns'] = 1043
    elif damage == 'missing_cut':
        result['checks'][0]['cuts'].pop()
    elif damage == 'leak':
        result['checks'][0]['cuts'][0]['future_perturbation']['different_cells'] = 1
    elif damage == 'partial_cells':
        result['checks'][0]['exact_alignment']['cells'] -= 1
    elif damage == 'wrong_source':
        result['raw_sha256'] = 'b' * 64
    elif damage == 'missing_clocks':
        result['checks'][0]['clock_pair_checks'] -= 1
    else:
        result['scoring_gate'] = 'OPEN'
    with pytest.raises(ValueError):
        validate_result(result, 'SYNTHETIC', 7, 'a' * 64)
