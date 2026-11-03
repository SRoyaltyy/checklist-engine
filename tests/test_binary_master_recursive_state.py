"""Native RSI/MACD state, exact values, window masks and historical cuts."""
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

from world_binary_master import (NativeBar, _measure, _native_indicator_history,
                                 _native_rsi_series, _osc_series, _rsi_at,
                                 bind_master_question, evaluate_master)
from world_question_grid import CanonicalGrid, ROOT

BASE = '7dcaa48680daeac9a6025c09f9e4d138f5fcbda5'


def frozen_module(path, digest):
    raw = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == digest
    module = types.ModuleType('_recursive_oracle_' + Path(path).stem)
    module.__file__ = str(Path(ROOT) / path)
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.fixture(scope='module')
def oracle():
    timeframes = frozen_module('world_timeframes.py',
        'a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95')
    settings = frozen_module('world_indicator_settings.py',
        '8447cf994ed29639be5460b3bc2aaad94e2a833a68dcf2f3d835c87bec7de9db')
    raw = subprocess.check_output(['git', 'show', BASE + ':dictionary/INDICATOR_SETTINGS.json'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == '015aae37cd549ab6297407b501534d2143a02c70c0b482ac330c6b9b570ad610'
    config = json.loads(raw)
    default = next(s for s in config['items']['I030']['settings'] if s['name'] == 'default')
    assert default['parameters'] == dict(fast=12, slow=26, signal=9)
    # Execute the unchanged registered MACD branch with only its setting.
    settings.load_settings = lambda: {'items': {'I030': {'settings': [default]}}}
    return timeframes, settings


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


def bars_from_prices(prices):
    dates = pd.bdate_range('2020-01-01', periods=len(prices) + 1)
    bars = {i: NativeBar(end=dates[i].date(), available_from=dates[i + 1].date(),
                        open=float(c), high=float(c + 1), low=float(c - 1),
                        close=float(c), volume=1.) for i, c in enumerate(prices)}
    return bars, dates


def definitions(grid, derivative, recipe):
    for qid, row in sorted(grid.tree.items()):
        if row['L3_derivative'] != derivative or not qid.endswith('|1x10'):
            continue
        try:
            result = bind_master_question(row, next(grid.variants(qid)))
        except NotImplementedError:
            continue
        if result[0]['feature']['recipe'] == recipe:
            return result
    raise AssertionError('registered definition missing')


def answers(defs, bars, dates, end):
    return {d['source_outcome']: evaluate_master(d, bars, dates[end + 1].date(), end).answer for d in defs}


@pytest.mark.parametrize('k', range(1, 22))
def test_native_bits_for_all_registered_rsi_periods_and_macd_at_every_candle_size(oracle, k):
    tf, settings = oracle
    prices = np.repeat(100. + 10. * np.sin(np.arange(120) / 7.) + .02 * np.arange(120), k)
    bars, dates = bars_from_prices(prices)
    # Independently resample the source, including an earlier partial group
    # while the adapter still receives every future bar.
    for end in (len(prices) - 1, 80 * k + k // 2 - 1):
        frame = pd.DataFrame([dict(date=b.end, open=b.open, high=b.high,
                                   low=b.low, close=b.close, volume=b.volume)
                              for i, b in bars.items() if i <= end])
        native = tf.completed_candles(frame, f'{k}d', session_calendar=dates)
        history = _native_indicator_history(bars, dates[end + 1].date(), end, k)
        assert [b.end for b in history] == list(native.date.dt.date)
        arrays = [native[c].to_numpy(dtype=np.float64) for c in tf.PRICE_COLS]
        registered = tf.parameter_variants(*arrays)
        close = np.array([b.close for b in history])
        for p in (6, 12, 14, 24):
            values, known = _native_rsi_series(close, p)
            assert np.array_equal(values.view(np.uint64), registered['RSI' + str(p)].view(np.uint64))
            assert not known[:p].any() and known[p:].all()
        registered_macd = settings.configured_indicators(*arrays)
        values, signal, known = _osc_series(dict(osc_kind='MACD', osc_fast='12',
            osc_slow='26', osc_signal='9'), close, arrays[1], arrays[2])
        assert np.array_equal(values.view(np.uint64), registered_macd['I030_default_line'].view(np.uint64))
        assert np.array_equal(signal.view(np.uint64), registered_macd['I030_default_signal'].view(np.uint64))
        assert not known[:33].any() and known[33:].all()


@pytest.mark.parametrize('period', [6, 12, 14, 24])
def test_flat_zero_is_unknown_but_defined_all_loss_zero_is_known(period):
    close = np.r_[np.full(70, 1000.), np.full(25, 100.), [101., 102., 103.]]
    values, known = _native_rsi_series(close, period)
    assert (values[period:70] == 0).all() and not known[:70].any()
    assert (values[70:95] == 0).all() and known[70:].all()
    assert _rsi_at(close, period, 69) is None
    assert _rsi_at(close, period, 70) == 0.
    assert _rsi_at(close, period, 96) == values[96]
    assert _rsi_at(close[:97], period, 96) == values[96]


def test_small_nonzero_state_is_known_without_added_epsilon():
    close = 1. + np.arange(40) * 1e-14
    values, known = _native_rsi_series(close, 14)
    assert known[14:].all()
    import talib
    assert np.array_equal(values.view(np.uint64), talib.RSI(close, timeperiod=14).view(np.uint64))


def test_rsi_counterexample_and_flat_window_policy(grid):
    defs = definitions(grid, 'RSI14', 'native_osc_zone_share_v1')
    close = np.r_[np.full(70, 1000.), np.full(25, 100.), [101., 102., 103.]]
    bars, dates = bars_from_prices(close)
    assert answers(defs, bars, dates, 97) == dict(mostly_high='NO', mostly_low='YES', mostly_mid='NO', mixed='NO')
    assert set(answers(defs, bars, dates, 69).values()) == {'NOT_EVALUABLE'}
    # Once all ten window bars have defined state, a prior flat prefix must
    # not invalidate the window. An unknown anchor still invalidates a cross.
    assert set(answers(defs, bars, dates, 78).values()) == {'NOT_EVALUABLE'}
    assert answers(defs, bars, dates, 79)['mostly_low'] == 'YES'
    cross = definitions(grid, 'RSI14', 'native_osc_cross_v1')
    assert set(answers(cross, bars, dates, 79).values()) == {'NOT_EVALUABLE'}
    assert answers(cross, bars, dates, 80)['none'] == 'YES'


def test_macd_registered_cross_counterexample_and_native_warmup(grid):
    close = 100. + 10. * np.sin(np.arange(160) / 7.) + .02 * np.arange(160)
    bars, dates = bars_from_prices(close)
    defs = definitions(grid, 'MACD12_26_9', 'native_osc_cross_v1')
    assert answers(defs, bars, dates, 45) == dict(up='YES', down='NO', both='NO', none='NO')
    assert answers(defs, {i: b for i, b in bars.items() if i <= 45}, dates, 45) == answers(defs, bars, dates, 45)
    assert set(answers(defs, bars, dates, 42).values()) == {'NOT_EVALUABLE'}
    assert set(answers(defs, bars, dates, 43).values()) <= {'YES', 'NO'}


@pytest.mark.parametrize('recipe', ['native_rsi_floor_v1', 'native_rsi_ceiling_v1'])
def test_rsi_extremes_use_only_last_n_values(grid, recipe):
    close = np.r_[100. + np.arange(50), 150. - np.arange(50), 100. + np.arange(50)]
    if recipe == 'native_rsi_ceiling_v1':
        close = 250. - close
    bars, dates = bars_from_prices(close)
    feature = definitions(grid, 'RSI14', recipe)[0]['feature']
    values, known = _native_rsi_series(close, 14)
    assert known[-10:].all()
    extreme = min(values[-10:]) if recipe == 'native_rsi_floor_v1' else max(values[-10:])
    thresholds = [float(feature[k]) for k in ('rsi_t1', 'rsi_t2', 'rsi_t3')]
    expected = sum(extreme >= t if recipe == 'native_rsi_floor_v1' else extreme > t for t in thresholds)
    old_extreme = min(values[14:]) if recipe == 'native_rsi_floor_v1' else max(values[14:])
    assert expected != sum(old_extreme >= t if recipe == 'native_rsi_floor_v1' else old_extreme > t for t in thresholds)
    assert _measure(recipe, list(bars.values()), feature) == expected


@pytest.mark.parametrize('derivative,recipe', [('RSI14', 'native_osc_cross_v1'),
    ('RSI14', 'native_osc_zone_share_v1'), ('RSI6', 'native_osc_swing_speed_v1'),
    ('RSI14', 'native_extreme_position_v1')])
def test_unknown_window_is_not_no_and_late_history_is_not_silently_reseeded(grid, derivative, recipe):
    defs = definitions(grid, derivative, recipe)
    bars, dates = bars_from_prices(100. + np.sin(np.arange(100) / 5.))
    # A present history candle unavailable at D cannot seed recursive state.
    bars[10] = replace(bars[10], available_from=dates[-1].date() + timedelta(days=1))
    assert set(answers(defs, bars, dates, 99).values()) == {'NOT_EVALUABLE'}
    flat, dates = bars_from_prices(np.full(100, 100.))
    assert set(answers(defs, flat, dates, 99).values()) == {'NOT_EVALUABLE'}
