"""Native Williams %R sign/bit parity and executable oscillator ranges."""
import hashlib
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

from world_binary_master import NativeBar, _osc_series, bind_master_question, evaluate_master
from world_question_grid import CanonicalGrid, ROOT


@pytest.fixture(scope='module')
def frozen():
    raw = subprocess.check_output(['git', 'show', '7dcaa48680daeac9a6025c09f9e4d138f5fcbda5:world_timeframes.py'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == 'a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95'
    module = types.ModuleType('_williams_r_frozen_oracle')
    module.__file__ = str(Path(ROOT) / 'world_timeframes.py')
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


@pytest.mark.parametrize('prices', [np.linspace(100., 140., 90), np.linspace(140., 100., 90),
                                   100. + 4. * np.sin(np.arange(90) / 6.)])
def test_williams_r_bits_match_registered_field_and_truncated_window(frozen, prices):
    high, low = prices + 1., prices - 1.
    feature = dict(osc_kind='WILLR', osc_period='14', cross_line='-50')
    actual, line, known = _osc_series(feature, prices, high, low)
    native = frozen.parameter_variants(prices, high, low, prices, np.ones(len(prices)))['WILLR14'][13:]
    assert np.array_equal(actual.view(np.uint64), native.view(np.uint64))
    assert (actual <= 0).all() and (actual >= -100).all()
    assert (line == -50).all()
    assert known.all()
    shorter, _, shorter_known = _osc_series(feature, prices[-24:], high[-24:], low[-24:])
    assert shorter_known.all()
    assert np.array_equal(shorter.view(np.uint64), native[-11:].view(np.uint64))


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


def bars(prices, high=None, low=None):
    dates = pd.bdate_range('2020-01-01', periods=len(prices) + 1)
    high = prices + 1. if high is None else high
    low = prices - 1. if low is None else low
    values = {i: NativeBar(end=dates[i].date(), available_from=dates[i + 1].date(),
                          open=float(c), high=float(high[i]), low=float(low[i]),
                          close=float(c), volume=1.) for i, c in enumerate(prices)}
    return values, dates[-1].date(), len(prices) - 1


@pytest.mark.parametrize('derivative,prices,winner', [
    ('WilliamsR14', np.linspace(140., 100., 90), 'mostly_low'),
    ('WilliamsR14', np.linspace(100., 140., 90), 'mostly_high'),
    ('Stoch14_3', np.linspace(100., 140., 90), 'mostly_high')])
def test_registered_zone_questions_execute_and_use_correct_signed_levels(grid, derivative, prices, winner):
    source, setup, last = bars(prices)
    answers = {d['source_outcome']: evaluate_master(d, source, setup, last).answer
               for d in definitions(grid, derivative, 'native_osc_zone_share_v1')}
    assert answers[winner] == 'YES'
    assert sum(v == 'YES' for v in answers.values()) == 1


@pytest.mark.parametrize('ramp,winner', [(np.linspace(96., 105., 10), 'up'),
                                       (np.linspace(104., 95., 10), 'down')])
def test_crossing_negative_midline_is_not_constant_none(grid, ramp, winner):
    prices = np.r_[np.full(40, ramp[0]), ramp]
    source, setup, last = bars(prices, high=np.full(50, 110.), low=np.full(50, 90.))
    answers = {d['source_outcome']: evaluate_master(d, source, setup, last).answer
               for d in definitions(grid, 'WilliamsR14', 'native_osc_cross_v1')}
    assert answers[winner] == 'YES'
    assert answers['none'] == 'NO'


@pytest.mark.parametrize('derivative', ['WilliamsR14', 'Stoch14_3'])
def test_zero_range_remains_not_evaluable(grid, derivative):
    prices = np.full(50, 100.)
    source, setup, last = bars(prices, high=prices, low=prices)
    for definition in definitions(grid, derivative, 'native_osc_zone_share_v1'):
        assert evaluate_master(definition, source, setup, last).answer == 'NOT_EVALUABLE'


def test_unused_unknown_anchor_does_not_invalidate_a_defined_zone_window(frozen, grid):
    prices = np.full(25, 100.)
    high = np.r_[np.full(14, 100.), np.full(11, 110.)]
    low = np.r_[np.full(14, 100.), np.full(11, 90.)]
    actual, _, known = _osc_series(dict(osc_kind='WILLR', osc_period='14', cross_line='-50'),
                                   prices, high, low)
    native = frozen.parameter_variants(prices, high, low, prices, np.ones(25))['WILLR14'][13:]
    assert np.array_equal(actual.view(np.uint64), native.view(np.uint64))
    assert actual[0] == 0. and not known[0]  # native zero for undefined range
    assert known[1:].all() and (actual[1:] == -50.).all()
    source, setup, _ = bars(prices, high, low)
    dates = pd.bdate_range('2020-01-01', periods=26)
    for recipe in ('native_osc_zone_share_v1', 'native_osc_cross_v1'):
        defs = definitions(grid, 'WilliamsR14', recipe)
        at23 = {d['source_outcome']: evaluate_master(d, source, dates[24].date(), 23).answer for d in defs}
        at24 = {d['source_outcome']: evaluate_master(d, source, setup, 24).answer for d in defs}
        if recipe == 'native_osc_zone_share_v1':
            assert at23 == dict(mostly_high='NO', mostly_low='NO', mostly_mid='YES', mixed='NO')
            assert at24 == at23
        else:
            assert set(at23.values()) == {'NOT_EVALUABLE'}  # cross uses the anchor
            assert at24 == dict(up='NO', down='NO', both='NO', none='YES')


@pytest.mark.parametrize('price,winner', [(110., 'mostly_high'), (90., 'mostly_low')])
def test_defined_zero_and_minus_hundred_remain_known(grid, price, winner):
    prices = np.full(50, price)
    source, setup, last = bars(prices, np.full(50, 110.), np.full(50, 90.))
    answers = {d['source_outcome']: evaluate_master(d, source, setup, last).answer
               for d in definitions(grid, 'WilliamsR14', 'native_osc_zone_share_v1')}
    assert answers[winner] == 'YES' and sum(a == 'YES' for a in answers.values()) == 1
