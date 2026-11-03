import copy
import json

import pytest

from ci.price_pit_counterexample_replay import ROOT, REQUEST, comparison, validate_request


def stock(cells):
    return dict(ticker='AQMS', prefix_gate='PASS', alignment_gate='PASS',
                packet_replay=[dict(timeframe='1d', different_cells=cells, missing_differences=0,
                                    differences=[] if not cells else [{'question_id': 'x', 'different_cells': cells}])])


def test_repetition_reports_instability_and_never_assigns_a_cause_or_full_scope():
    result = comparison('AQMS', stock(1), [stock(0), stock(1)])
    assert result['reported_signatures_stable_same_runner'] is False
    assert result['matches_original_reported_signature'] == [False, True]
    assert result['repeated_different_cells'] == [0, 1]
    assert result['cause'] == 'NOT_PROVEN'
    assert result['scope'] == 'REPORTED_DIFFERENCE_SIGNATURES_ONLY_NOT_ALL_NUMERIC_OR_ANSWER_BITS'


def test_missing_repetition_cannot_claim_stable_and_foreign_name_is_rejected():
    assert comparison('AQMS', stock(1), [stock(1)])['reported_signatures_stable_same_runner'] is False
    with pytest.raises(ValueError, match='ticker'):
        comparison('BYRN', stock(1), [stock(1), stock(1)])


@pytest.mark.parametrize('key,value', [('repetitions', 1), ('worker_commit', 'other'),
                                      ('worker_lf_sha256', 'wrong'), ('execute', 'true')])
def test_diagnostic_cannot_change_the_predeclared_worker_or_scope(key, value):
    request = json.loads((ROOT / REQUEST).read_bytes())
    validate_request(request)
    request = copy.deepcopy(request)
    request[key] = value
    with pytest.raises(ValueError, match='scope'):
        validate_request(request)
