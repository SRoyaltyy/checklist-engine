"""Compare the master adapter to the frozen registered native MA fields."""
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

from world_binary_master import (NativeBar, _ma_series, _measure,
                                 _native_ma_history, bind_master_question,
                                 evaluate_master)
from world_question_grid import CanonicalGrid, ROOT

BASE = '7dcaa48680daeac9a6025c09f9e4d138f5fcbda5'


@pytest.fixture(scope='module')
def frozen():
    raw = subprocess.check_output(['git', 'show', BASE + ':world_timeframes.py'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == 'a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95'
    module = types.ModuleType('_native_ma_frozen_oracle')
    module.__file__ = str(Path(ROOT) / 'world_timeframes.py')
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


def bars_from_prices(prices):
    dates = pd.bdate_range('2020-01-01', periods=len(prices) + 1)
    bars = {i: NativeBar(end=dates[i].date(), available_from=dates[i + 1].date(),
                        open=float(c - .25), high=float(c + 1), low=float(c - 1),
                        close=float(c), volume=1.) for i, c in enumerate(prices)}
    return bars, dates


def reference(frozen, bars, calendar, k):
    frame = pd.DataFrame([dict(date=b.end, open=b.open, high=b.high, low=b.low,
                               close=b.close, volume=b.volume) for _, b in sorted(bars.items())])
    native = frozen.completed_candles(frame, f'{k}d', session_calendar=calendar)
    values = frozen.parameter_variants(*(native[c].to_numpy(dtype=np.float64)
                                         for c in frozen.PRICE_COLS))
    return native, values


def definitions(grid, facet, span='1x10'):
    qid = f'B|moving_averages|EMA21|{facet}|{span}'
    return bind_master_question(grid.tree[qid], next(grid.variants(qid)))


@pytest.mark.parametrize('k', range(1, 22))
@pytest.mark.parametrize('kind', ['SMA', 'EMA'])
def test_full_native_series_bit_matches_frozen_field_on_every_candle_size(frozen, k, kind):
    prices = np.repeat(np.r_[np.full(70, 1000.), np.full(25, 100.), [101., 102., 103.]], k)
    bars, dates = bars_from_prices(prices)
    history = _native_ma_history(bars, dates[-1].date(), len(prices) - 1, k)
    native, values = reference(frozen, bars, dates, k)
    assert [b.end for b in history] == list(native.date.dt.date)
    assert [b.available_from for b in history] == list(native.available_from.dt.date)
    actual = _ma_series(dict(ma_kind=kind, ma_period='21'), np.array([b.close for b in history]))
    expected = values[kind + '21'][20:]
    assert np.array_equal(actual.view(np.uint64), expected.view(np.uint64))
    # A partial current bucket and a supplied future suffix must not alter
    # state at an earlier cut. Compare to an independently truncated source.
    cut = 70 * k + k // 2 - 1
    shorter = _native_ma_history(bars, dates[cut + 1].date(), cut, k)
    prefix_native, prefix_values = reference(frozen, {i: b for i, b in bars.items() if i <= cut}, dates, k)
    assert [b.end for b in shorter] == list(prefix_native.date.dt.date)
    actual_prefix = _ma_series(dict(ma_kind=kind, ma_period='21'), np.array([b.close for b in shorter]))
    expected_prefix = prefix_values[kind + '21'][20:]
    assert np.array_equal(actual_prefix.view(np.uint64), expected_prefix.view(np.uint64))
    assert np.array_equal(actual_prefix.view(np.uint64), actual[:len(actual_prefix)].view(np.uint64))


def test_current_ema21_counterexample_uses_native_state_and_last_n_only(frozen, grid):
    prices = np.r_[np.full(70, 1000.), np.full(25, 100.), [101., 102., 103.]]
    bars, dates = bars_from_prices(prices)
    _, values = reference(frozen, bars, dates, 1)
    assert values['EMA21'][-1] > prices[-1]
    answers = {d['source_outcome']: evaluate_master(d, bars, dates[-1].date(), 97).answer
               for d in definitions(grid, 'fresh_cross', '1x3')}
    assert answers == dict(up='NO', down='NO', both='NO', none='YES')
    # The older down-cross at the 1000 -> 100 transition must not count in N.
    count = definitions(grid, 'cross_count')[0]['feature']
    history = _native_ma_history(bars, dates[-1].date(), 97, 1)
    assert _measure('native_ma_cross_count_v1', history, count) == 0
    slope = definitions(grid, 'slope')[0]['feature']
    n = slope['lookback']
    expected = (values['EMA21'][-1] / values['EMA21'][-n] - 1.) * 100.
    assert _measure('native_ma_slope_v1', history, slope) == expected


def test_old_partial_ipo_halt_groups_match_frozen_initialization(frozen):
    bars, dates = bars_from_prices(np.linspace(100., 190., 300))
    del bars[0]                 # partial initial 3-session bucket
    del bars[34]                # old partial halt bucket, outside the facet
    native, values = reference(frozen, bars, dates, 3)
    history = _native_ma_history(bars, dates[-1].date(), 299, 3)
    assert [b.end for b in history] == list(native.date.dt.date)
    actual = _ma_series(dict(ma_kind='EMA', ma_period='21'), np.array([b.close for b in history]))
    assert np.array_equal(actual.view(np.uint64), values['EMA21'][20:].view(np.uint64))


def test_future_suffix_does_not_change_past_answer_and_late_history_is_unknown(grid):
    bars, dates = bars_from_prices(np.r_[np.full(70, 1000.), np.full(25, 100.), [101., 102., 103.]])
    definition = next(d for d in definitions(grid, 'fresh_cross', '1x3') if d['source_outcome'] == 'none')
    setup = dates[-1].date()
    assert evaluate_master(definition, bars, setup, 97).answer == 'YES'
    bars[98] = replace(bars[97], end=dates[-1].date(), available_from=(dates[-1] + pd.Timedelta(days=1)).date(), close=1e9, high=1e9)
    assert evaluate_master(definition, bars, setup, 97).answer == 'YES'
    bars[10] = replace(bars[10], available_from=(dates[-1] + pd.Timedelta(days=1)).date())
    assert evaluate_master(definition, bars, setup, 97).answer == 'NOT_EVALUABLE'


def test_missing_facet_bucket_remains_unknown(grid):
    bars, dates = bars_from_prices(np.linspace(100., 150., 98))
    del bars[96]
    definition = definitions(grid, 'fresh_cross', '1x3')[0]
    assert evaluate_master(definition, bars, dates[-1].date(), 97).answer == 'NOT_EVALUABLE'


def test_numpy_integral_shared_slots_preserve_supplied_history(grid):
    bars, dates = bars_from_prices(np.r_[np.full(70, 1000.), np.full(25, 100.), [101., 102., 103.]])
    bars = {np.int64(k): v for k, v in bars.items()}
    definition = next(d for d in definitions(grid, 'fresh_cross', '1x3') if d['source_outcome'] == 'none')
    assert evaluate_master(definition, bars, dates[-1].date(), 97).answer == 'YES'


def family_definitions(grid, facet):
    candidates = [(q, r) for q, r in sorted(grid.tree.items()) if r['L4_analysis'] == facet]
    row = next((r for q, r in candidates if q.endswith('|1x10')), candidates[0][1])
    return bind_master_question(row, next(grid.variants(row['question_id'])))


def test_all_sma_stack_ingredients_match_registered_fields_and_keep_n_window(frozen, grid):
    prices = np.r_[100. + np.arange(300) * .5, 300. - np.arange(300) * .5]
    bars, dates = bars_from_prices(prices)
    _, values = reference(frozen, bars, dates, 1)
    for p in (10, 20, 30, 50, 200):
        measured = _ma_series(dict(ma_kind='SMA', ma_period=str(p)), prices)
        assert np.array_equal(measured.view(np.uint64), values['SMA' + str(p)][p - 1:].view(np.uint64))
    stack = {d['source_outcome']: evaluate_master(d, bars, dates[-1].date(), 599).answer
             for d in family_definitions(grid, 'full_stack_streak')}
    assert stack['bear_mid'] == 'YES' and stack['bull_zero'] == 'YES'
    weekly_definitions = family_definitions(grid, 'weekly_stack')
    k = weekly_definitions[0]['feature']['candle_days']
    weekly_bars, weekly_dates = bars_from_prices(np.repeat(prices, k))
    weekly = {d['source_outcome']: evaluate_master(d, weekly_bars, weekly_dates[-1].date(), len(weekly_bars) - 1).answer
              for d in weekly_definitions}
    assert weekly['bear'] == 'YES' and weekly['mixed'] == 'NO'


def test_ma30_record_uses_baked_prior_history_not_entire_initialization_prefix(grid):
    # An old 271-bar above-SMA run is outside the baked 500 prior bars. The
    # current 40-bar run is a record within that declared comparison history.
    prices = np.r_[100. + np.arange(300) * .5,
                   100. + .1 * (np.arange(560) % 2),
                   101. + np.arange(40) * .5]
    bars, dates = bars_from_prices(prices)
    answers = {d['source_outcome']: evaluate_master(d, bars, dates[-1].date(), 899).answer
               for d in family_definitions(grid, 'ma30_side_streak')}
    assert answers['above_long_record'] == 'YES'
    assert answers['above_long_not'] == 'NO'
