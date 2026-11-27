import copy
import json

import numpy as np
import pandas as pd
import pytest

from ci.price_pit_split_trace import (REQUEST, ROOT, codes_float32_series_style,
                                      codes_float64_style, f32, fragile_series, next64,
                                      straddle, ulp32_distance, validate_request, verdict)


def test_ulp32_distance_zero_for_identical_and_one_for_adjacent():
    assert ulp32_distance(1.0, 1.0) == 0
    a = np.float32(1.0)
    b = np.nextafter(a, np.float32(2.0), dtype=np.float32)
    assert ulp32_distance(b, a) == 1
    assert ulp32_distance(a, b) == -1
    assert ulp32_distance(float('nan'), 1.0) is None
    # Same-sign negative neighbours keep their ordering under the map.
    c = np.float32(-1.0)
    d = np.nextafter(c, np.float32(-2.0), dtype=np.float32)
    assert ulp32_distance(c, d) == 1


def test_next64_round_trip_and_monotonicity():
    x = 0.123456789
    assert next64(next64(x, 1), -1) == np.float64(x)
    assert next64(x, 1) > x
    assert next64(x, -1) < x
    neg = -x
    assert next64(next64(neg, 1), -1) == np.float64(neg)
    assert next64(x, 1) == np.nextafter(x, np.inf)
    assert next64(neg, 1) == np.nextafter(neg, np.inf)


def test_straddle_detects_boundary_tie_and_rejects_clear_cases():
    f1 = np.float32(1.0)
    f2 = np.nextafter(f1, np.float32(2.0), dtype=np.float32)
    boundary = (np.float64(f1) + np.float64(f2)) / 2
    left = next64(boundary, 1)        # rounds up to f2
    right = np.float64(f1)            # exactly f1
    assert np.float32(left) == f2 and np.float32(right) == f1
    assert straddle(left, right) is True   # left -1ulp64 lands on the boundary, ties-to-even f1
    # Equal float32s away from any rounding boundary cannot flip under 1 ulp64.
    assert straddle(np.float64(1.0000000000000002), np.float64(1.0)) is False
    # Clear separation: no 1-ulp64 perturbation flips the outcome.
    assert straddle(2.0, 1.0) is False


def test_comparison_styles_agree_on_float32_backed_series():
    series = pd.Series(np.array([1.0, 1.5, 1.25, np.nan, 2.0], dtype=np.float32))
    a = codes_float64_style(series)
    b = codes_float32_series_style(series)
    assert a.tolist() == b.tolist() == [0, 2, 1, 0, 0]


def test_code_mapping_matches_production_encoding():
    series = pd.Series(np.array([2.0, 1.0, 1.0, np.nan], dtype=np.float32))
    codes = codes_float64_style(series)
    assert codes.tolist() == [0, 1, 1, 0]   # nan start, then down, flat, missing


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


def test_rails_and_healed_census_cannot_change():
    request = json.loads((ROOT / REQUEST).read_bytes())
    mutated = copy.deepcopy(request)
    mutated['tickers'][2]['rail'] = 'build_vs_replay'
    with pytest.raises(ValueError, match='scope'):
        validate_request(mutated)
    mutated = copy.deepcopy(request)
    mutated['tickers'][2]['expected_differences'] = {'HV10:rising1__1d': 1}
    with pytest.raises(ValueError, match='healed'):
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


def test_verdict_classifies_straddle_vs_code_path_vs_mixed():
    def cell(**kw):
        base = dict(stored_code=2, replay_code=1, stored_code_int=2,
                    code_float64_style=1, code_float32_series_style=1,
                    comparison_styles_agree=True, straddle_1ulp64=True)
        base.update(kw)
        return base
    def trace(cells, ticker='AQMS'):
        return dict(ticker=ticker, style_census_agree=True, cells=cells)
    good = [trace([cell()]), trace([cell()], 'BYRN'), trace([cell()], 'AZIO')]
    assert verdict(good)['classification'] == 'FEATURE_VALUE_SPLIT_1ULP64_STRADDLES_STYLES_AGREE'
    diverged = [trace([cell(code_float32_series_style=2, comparison_styles_agree=False)]),
                trace([cell()], 'BYRN'), trace([cell()], 'AZIO')]
    assert verdict(diverged)['classification'] == 'CODE_PATH_DIVERGENCE_SIGNAL_FIX_IN_LATER_PR_NOT_THIS_STEP'
    mixed = [trace([cell(straddle_1ulp64=False)]), trace([cell()], 'BYRN'), trace([cell()], 'AZIO')]
    assert verdict(mixed)['classification'] == 'MIXED_OR_NON_STRADDLE_CELLS_REQUIRE_REVIEW'
