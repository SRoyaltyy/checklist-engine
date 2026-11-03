"""Stochastic native bits, strict midline events and undefined-range masks."""
from dataclasses import replace
from datetime import timedelta
import hashlib
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

from world_binary_master import (NativeBar, _native_indicator_history, _osc_series,
                                 bind_master_question, evaluate_master)
from world_question_grid import CanonicalGrid, ROOT

FEATURE = dict(osc_kind='STOCH', osc_period='14', osc_slow='3', cross_line='50')


@pytest.fixture(scope='module')
def frozen():
    raw = subprocess.check_output(['git', 'show', '7dcaa48680daeac9a6025c09f9e4d138f5fcbda5:world_timeframes.py'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == 'a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95'
    module = types.ModuleType('_stochastic_frozen_oracle')
    module.__file__ = str(Path(ROOT) / 'world_timeframes.py')
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


def bars_from_prices(prices, high=None, low=None):
    high = prices + 1. if high is None else high
    low = prices - 1. if low is None else low
    dates = pd.bdate_range('2020-01-01', periods=len(prices) + 1)
    bars = {i: NativeBar(end=dates[i].date(), available_from=dates[i + 1].date(),
                        open=float(c), high=float(high[i]), low=float(low[i]),
                        close=float(c), volume=1.) for i, c in enumerate(prices)}
    return bars, dates


def definitions(grid, facet):
    qid = 'B|overbought_oversold|Stoch14_3|' + facet + '|1x10'
    return bind_master_question(grid.tree[qid], next(grid.variants(qid)))


def answers(defs, bars, dates, end):
    return {d['source_outcome']: evaluate_master(d, bars, dates[end + 1].date(), end).answer for d in defs}


@pytest.mark.parametrize('k', range(1, 22))
def test_native_k_exact_bits_at_every_candle_size_and_cutoff(frozen, k):
    prices = np.repeat(100. + 7. * np.sin(np.arange(120) / 6.), k)
    bars, dates = bars_from_prices(prices)
    for end in (len(prices) - 1, 80 * k + k // 2 - 1):
        frame = pd.DataFrame([dict(date=b.end, open=b.open, high=b.high,
            low=b.low, close=b.close, volume=b.volume) for i, b in bars.items() if i <= end])
        native = frozen.completed_candles(frame, f'{k}d', session_calendar=dates)
        arrays = [native[c].to_numpy(dtype=np.float64) for c in frozen.PRICE_COLS]
        registered = frozen.parameter_variants(*arrays)['STOCH14_3_3_k']
        history = _native_indicator_history(bars, dates[end + 1].date(), end, k)
        assert [b.end for b in history] == list(native.date.dt.date)
        actual, line, known = _osc_series(FEATURE,
            np.array([b.close for b in history]), np.array([b.high for b in history]),
            np.array([b.low for b in history]))
        assert np.array_equal(actual.view(np.uint64), registered.view(np.uint64))
        assert (line == 50).all()
        assert not known[:17].any() and known[17:].all()


def test_strict_down_cross_from_exact_fifty_is_not_missed(frozen, grid):
    prices = np.r_[np.full(100, 100.), 99., 105., 95.]
    bars, dates = bars_from_prices(prices, np.full(103, 110.), np.full(103, 90.))
    args = (prices, np.full(103, 110.), np.full(103, 90.), prices, np.ones(103))
    native = frozen.parameter_variants(*args)['STOCH14_3_3_k']
    assert native[99] == 50. and native[100] < 50.
    defs = definitions(grid, 'cross_event')
    assert answers(defs, bars, dates, 100) == dict(up='NO', down='YES', both='NO', none='NO')
    assert answers(defs, {i: b for i, b in bars.items() if i <= 100}, dates, 100) == answers(defs, bars, dates, 100)


def test_native_slow_d_warmup_is_required_for_registered_k(grid):
    bars, dates = bars_from_prices(np.linspace(100., 130., 50))
    zone = definitions(grid, 'time_in_zone')
    cross = definitions(grid, 'cross_event')
    assert set(answers(zone, bars, dates, 25).values()) == {'NOT_EVALUABLE'}
    assert set(answers(zone, bars, dates, 26).values()) <= {'YES', 'NO'}
    assert set(answers(cross, bars, dates, 26).values()) == {'NOT_EVALUABLE'}
    assert set(answers(cross, bars, dates, 27).values()) <= {'YES', 'NO'}


def test_zero_range_native_zero_stays_unknown_only_while_used(grid):
    prices = np.full(100, 100.)
    high, low = prices.copy(), prices.copy()
    high[60:], low[60:] = 110., 90.
    values, _, known = _osc_series(FEATURE, prices, high, low)
    assert (values[17:60] == 0).all() and not known[:62].any()
    assert known[62:].all() and (values[62:] == 50).all()
    bars, dates = bars_from_prices(prices, high, low)
    zone = definitions(grid, 'time_in_zone')
    cross = definitions(grid, 'cross_event')
    assert set(answers(zone, bars, dates, 70).values()) == {'NOT_EVALUABLE'}
    assert answers(zone, bars, dates, 71)['mostly_mid'] == 'YES'
    assert set(answers(cross, bars, dates, 71).values()) == {'NOT_EVALUABLE'}
    assert answers(cross, bars, dates, 72)['none'] == 'YES'


def test_unavailable_old_history_cannot_be_silently_reseeded(grid):
    bars, dates = bars_from_prices(100. + np.sin(np.arange(100) / 5.))
    bars[10] = replace(bars[10], available_from=dates[-1].date() + timedelta(days=1))
    assert set(answers(definitions(grid, 'cross_event'), bars, dates, 99).values()) == {'NOT_EVALUABLE'}


@pytest.mark.parametrize('value,high,low,winner', [(0., 110., 100., 'mostly_low'),
                                                (100., 100., 90., 'mostly_high')])
def test_defined_zero_and_hundred_remain_known(grid, value, high, low, winner):
    prices = np.full(60, 100.)
    highs, lows = np.full(60, high), np.full(60, low)
    values, _, known = _osc_series(FEATURE, prices, highs, lows)
    assert known[17:].all() and (values[17:] == value).all()
    bars, dates = bars_from_prices(prices, highs, lows)
    assert answers(definitions(grid, 'time_in_zone'), bars, dates, 59)[winner] == 'YES'
