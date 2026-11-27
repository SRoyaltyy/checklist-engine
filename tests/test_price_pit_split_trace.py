import copy
import json

import numpy as np
import pytest

from ci.price_pit_split_trace import (REQUEST, ROOT, TICKERS, code_of, f32, fragile_series,
                                      next64, straddle, ulp32_distance, validate_request,
                                      verdict)


def test_ulp32_distance_zero_for_identical_and_one_for_adjacent():
    assert ulp32_distance(1.0, 1.0) == 0
    a = np.float32(1.0)
    b = np.nextafter(a, np.float32(2.0), dtype=np.float32)
    assert ulp32_distance(b, a) == 1
    assert ulp32_distance(a, b) == -1
    assert ulp32_distance(float('nan'), 1.0) is None


def test_next64_round_trip_and_monotonicity():
    x = 0.123456789
    assert next64(next64(x, 1), -1) == np.float64(x)
    assert next64(x, 1) > x
    assert next64(x, -1) < x
    neg = -x
    assert next64(next64(neg, 1), -1) == np.float64(neg)


def test_straddle_detects_near_tie_and_rejects_clear_comparison():
    from ci.price_pit_split_trace import next64 as step
    f1 = np.float32(1.0)
    f2 = np.nextafter(f1, np.float32(2.0), dtype=np.float32)
    boundary = (np.float64(f1) + np.float64(f2)) / 2
    left = step(boundary, 1)        # rounds up to f2
    right = np.float64(f1)          # exactly f1
    assert np.float32(left) == f2 and np.float32(right) == f1
    assert straddle(left, right) is True   # left -1ulp64 lands on the boundary, ties-to-even f1
    # Equal float32s away from any rounding boundary cannot flip under 1 ulp64.
    assert straddle(np.float64(1.0000000000000002), np.float64(1.0)) is False
    # Clear separation: no 1-ulp64 perturbation flips the outcome.
    assert straddle(2.0, 1.0) is False


def test_code_of_matches_production_encoding():
    assert code_of(np.float32(2.0), np.float32(1.0)) == 2
    assert code_of(np.float32(1.0), np.float32(2.0)) == 1
    assert code_of(np.float32(1.0), np.float32(1.0)) == 1
    assert code_of(np.float32('nan'), np.float32(1.0)) == 0
    assert code_of(np.float32(1.0), np.float32('nan')) == 0


def test_fragile_series_bitwise_matches_production_cast():
    from world_bar_statistics import bar_statistics
    rng = np.random.default_rng(7)
    close = 50 + np.cumsum(rng.normal(0, 1, 400))
    assert (close > 0).all()
    o = close + rng.normal(0, 0.2, 400)
    h = np.maximum(o, close) + 0.1
    l = np.minimum(o, close) - 0.1
    v = rng.integers(1000, 5000, 400).astype(float)
    produced = bar_statistics(o, h, l, close, v, '1d')
    mine = fragile_series(close, '1d')
    for field in ('HV10', 'RETURN_EXCESS_KURTOSIS60', 'RETURN_AUTOCORR1_20', 'RETURN_AUTOCORR1_60'):
        restated = mine[field].astype(np.float32)
        assert np.array_equal(np.isfinite(produced[field]), np.isfinite(restated)), field
        finite = np.isfinite(produced[field])
        assert np.array_equal(produced[field][finite], restated[finite]), field


def test_request_scope_and_bindings_cannot_change():
    request = json.loads((ROOT / REQUEST).read_bytes())
    validate_request(request)
    for key, value in [('version', 2), ('execute', 'true'),
                       ('questions', {'Q1': 'other'}),
                       ('selector_verdict', {'release': 'x', 'asset': 'y', 'sha256': 'z'})]:
        mutated = copy.deepcopy(request)
        mutated[key] = value
        with pytest.raises(ValueError, match='scope'):
            validate_request(mutated)


def test_predeclared_cells_must_flip_and_use_rising1():
    request = json.loads((ROOT / REQUEST).read_bytes())
    mutated = copy.deepcopy(request)
    mutated['tickers'][0]['cells'][0]['replay_code'] = 2
    with pytest.raises(ValueError, match='shape'):
        validate_request(mutated)
    mutated = copy.deepcopy(request)
    mutated['tickers'][0]['cells'][0]['question_id'] = 'RETURN_EXCESS_KURTOSIS60:above_mean20__1d'
    with pytest.raises(ValueError, match='shape'):
        validate_request(mutated)


def test_verdict_classifies_all_straddle_vs_mixed():
    def trace(cells, ticker='AQMS'):
        return dict(ticker=ticker, cells=cells)
    good = dict(stored_code=2, replay_code=1, stored_code_int=2, recomputed_code=1,
                straddle_1ulp64=True)
    outcome = verdict([trace([good]), trace([dict(good)], 'BYRN'), trace([dict(good)], 'AZIO')])
    assert outcome['classification'] == 'ALL_FLIPPING_CELLS_ARE_1ULP64_STRADDLES'
    bad = dict(good, straddle_1ulp64=False)
    outcome = verdict([trace([bad]), trace([dict(good)], 'BYRN'), trace([dict(good)], 'AZIO')])
    assert outcome['classification'] == 'MIXED_OR_NON_STRADDLE_CELLS_REQUIRE_REVIEW'
