"""Native ATR14 state and independently bounded facet/volume evidence."""
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

from world_binary_master import (NativeBar, _measure, _native_atr_series,
    _native_indicator_history, bind_master_question, evaluate_master)
from world_question_grid import CanonicalGrid, ROOT


@pytest.fixture(scope='module')
def frozen():
    raw = subprocess.check_output(['git', 'show', '7dcaa48680daeac9a6025c09f9e4d138f5fcbda5:world_timeframes.py'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == 'a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95'
    module = types.ModuleType('_atr_frozen_oracle')
    module.__file__ = str(Path(ROOT) / 'world_timeframes.py')
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


def source(opened, high, low, close, volume=None):
    dates = pd.bdate_range('2020-01-01', periods=len(close) + 1)
    volume = np.full(len(close), 100.) if volume is None else volume
    bars = {i: NativeBar(end=dates[i].date(), available_from=dates[i + 1].date(),
        open=float(o), high=float(h), low=float(l), close=float(c), volume=float(v))
        for i, (o, h, l, c, v) in enumerate(zip(opened, high, low, close, volume))}
    return bars, dates


def old_wide_prefix():
    close = np.full(98, 100.)
    return close.copy(), np.r_[np.full(70, 150.), np.full(28, 100.2)], np.r_[np.full(70, 50.), np.full(28, 99.8)], close


def definitions(grid, recipe, span='1x10'):
    for qid, row in sorted(grid.tree.items()):
        if not qid.endswith('|' + span):
            continue
        try:
            defs = bind_master_question(row, next(grid.variants(qid)))
        except NotImplementedError:
            continue
        if defs[0]['feature']['recipe'] == recipe:
            return defs
    raise AssertionError('registered definition missing: ' + recipe)


def answers(defs, bars, dates, end=None):
    end = len(dates) - 2 if end is None else end
    return {d['source_outcome']: evaluate_master(d, bars, dates[end + 1].date(), end).answer for d in defs}


@pytest.mark.parametrize('k', range(1, 22))
def test_atr_exact_native_bits_on_all_candle_sizes_and_earlier_cuts(frozen, k):
    close = np.repeat(100. + 7. * np.sin(np.arange(120) / 6.), k)
    bars, dates = source(close - .2, close + 1.1, close - 1.3, close)
    for end in (len(close) - 1, 80 * k + k // 2 - 1):
        frame = pd.DataFrame([dict(date=b.end, open=b.open, high=b.high,
            low=b.low, close=b.close, volume=b.volume) for i, b in bars.items() if i <= end])
        native = frozen.completed_candles(frame, f'{k}d', session_calendar=dates)
        registered = frozen.parameter_variants(*(native[c].to_numpy(dtype=np.float64)
            for c in frozen.PRICE_COLS))['ATR14']
        history = _native_indicator_history(bars, dates[end + 1].date(), end, k)
        assert [b.end for b in history] == list(native.date.dt.date)
        actual = _native_atr_series(np.array([b.high for b in history]),
            np.array([b.low for b in history]), np.array([b.close for b in history]))
        assert np.array_equal(actual.view(np.uint64), registered.view(np.uint64))
        assert np.isnan(actual[:14]).all() and not np.isnan(actual[14:]).any()


def test_run_counterexample_uses_native_atr_and_only_n_bodies(frozen, grid):
    opened, high, low, close = old_wide_prefix()
    opened[:70], opened[70:], high[70:], low[70:] = 50., 99., 100.1, 98.9
    bars, dates = source(opened, high, low, close)
    native = frozen.parameter_variants(opened, high, low, close, np.full(98, 100.))['ATR14']
    assert native[-1] == 13.604686992378044
    defs = definitions(grid, 'native_run_biggest_move_ratio_v1', '1x20')
    assert _measure(defs[0]['feature']['recipe'], list(bars.values()), defs[0]['feature']) == 1. / native[-1]
    assert answers(defs, bars, dates) == dict(big='NO', normal='NO', small='YES')
    future = dict(bars)
    future[98] = replace(bars[97], high=None, close=None)
    assert answers(defs, future, dates, 97) == answers(defs, bars, dates)
    # A shorter pattern window is evaluable once native endpoint ATR has
    # enough history; the old N<14 shortcut permanently hid these questions.
    assert answers(definitions(grid, 'native_run_biggest_move_ratio_v1'), bars, dates)['small'] == 'YES'


def test_max_volume_wick_does_not_read_old_volume_or_old_event(grid):
    opened, high, low, close = old_wide_prefix()
    high[70:], low[70:], low[-1] = 100.1, 99.9, 98.
    volume = np.full(98, 100.)
    volume[5], volume[-1] = 1e9, 900.
    bars, dates = source(opened, high, low, close, volume)
    defs = definitions(grid, 'native_maxvol_wick_v1', '1x20')
    assert answers(defs, bars, dates) == dict(bull_wick='NO', bear_wick='NO', small='YES')
    assert answers(definitions(grid, 'native_maxvol_wick_v1'), bars, dates)['small'] == 'YES'
    bars[5] = replace(bars[5], volume=None)
    assert answers(defs, bars, dates)['small'] == 'YES'
    bars[90] = replace(bars[90], volume=None)
    assert set(answers(defs, bars, dates).values()) == {'NOT_EVALUABLE'}


def test_segment_means_are_native_atr_only_inside_n(frozen, grid):
    opened, high, low, close = old_wide_prefix()
    close[-10:] = [100., 99., 98., 97., 96., 97., 98., 99., 100., 101.]
    opened[-10:], high[-10:], low[-10:] = close[-10:], close[-10:] + .2, close[-10:] - .2
    bars, dates = source(opened, high, low, close)
    native = frozen.parameter_variants(opened, high, low, close, np.full(98, 100.))['ATR14'][-10:]
    expected = (native[4:].mean(dtype=np.float64) / native[:5].mean(dtype=np.float64) - 1.) * 100.
    defs = definitions(grid, 'native_segment_atr_compare_v1')
    assert _measure(defs[0]['feature']['recipe'], list(bars.values()), defs[0]['feature']) == expected
    assert answers(defs, bars, dates) == dict(expanded='NO', contracted='YES', similar='NO')


@pytest.mark.parametrize('recipe,winner', [('native_absorption_day_v1', 'after_rise_ageR'),
                                         ('native_capitulation_bar_v1', 'none')])
def test_event_counterexamples_preserve_volume_baseline_and_use_native_atr(frozen, grid, recipe, winner):
    opened, high, low, close = old_wide_prefix()
    volume = np.full(98, 100.)
    volume[-1] = 900.
    if recipe == 'native_absorption_day_v1':
        opened[-1], high[-1], low[-1], close[-1] = 100., 101.2, 99.8, 101.
    else:
        opened[-1], high[-1], low[-1], close[-1] = 103., 103., 97., 97.6
    native = frozen.parameter_variants(opened, high, low, close, volume)['ATR14']
    defs = definitions(grid, recipe)
    f = defs[0]['feature']
    if recipe == 'native_absorption_day_v1':
        assert abs(close[-1] / close[-2] - 1.) < float(f['atr_frac']) * native[-1] / close[-2]
    else:
        assert high[-1] - low[-1] <= float(f['shock_atr']) * native[-1]
    bars, dates = source(opened, high, low, close, volume)
    actual = answers(defs, bars, dates)
    assert actual[winner] == 'YES' and sum(a == 'YES' for a in actual.values()) == 1
    # Native ATR initialization reads prices only. Volume older than the
    # original N+49 median context must not add a missingness dependency.
    bars[5] = replace(bars[5], volume=None)
    assert answers(defs, bars, dates)[winner] == 'YES'
    bars[50] = replace(bars[50], volume=None)
    assert set(answers(defs, bars, dates).values()) == {'NOT_EVALUABLE'}


@pytest.mark.parametrize('recipe', ['native_run_biggest_move_ratio_v1', 'native_maxvol_wick_v1',
    'native_segment_atr_compare_v1', 'native_absorption_day_v1', 'native_capitulation_bar_v1'])
def test_unavailable_price_history_is_not_silently_reseeded(grid, recipe):
    bars, dates = source(*old_wide_prefix())
    defs = definitions(grid, recipe)
    bars[5] = replace(bars[5], available_from=dates[-1].date() + timedelta(days=1))
    assert set(answers(defs, bars, dates).values()) == {'NOT_EVALUABLE'}


@pytest.mark.parametrize('recipe', ['native_run_biggest_move_ratio_v1', 'native_maxvol_wick_v1',
                                  'native_segment_atr_compare_v1'])
def test_native_warmup_and_zero_over_zero_are_not_no(grid, recipe):
    close = np.full(13, 100.)
    bars, dates = source(close, close + 1., close - 1., close)
    defs = definitions(grid, recipe)
    assert set(answers(defs, bars, dates).values()) == {'NOT_EVALUABLE'}
    close = np.full(100, 100.)
    bars, dates = source(close, close, close, close)
    assert set(answers(defs, bars, dates).values()) == {'NOT_EVALUABLE'}
