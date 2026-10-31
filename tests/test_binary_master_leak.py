"""Empirical leak property test for bound BINARY_MASTER definitions.

Complements the by-construction leak argument (PR #177): every bound master
definition must give the SAME answer when the supplied history gains bars that
are not knowable at the setup date (future slots, day-D or later candles, even
with absurd prices or leaked availability), and must go NOT_EVALUABLE — never
answer from a bar whose end >= setup date — when such a bar sits at the cutoff
slot. Both properties are checked across a sample that covers every FACETS
recipe.
"""
from datetime import date, timedelta

import numpy as np
import pytest

from world_binary_master import FACETS, NativeBar, bind_master_question, evaluate_master
from world_question_grid import CanonicalGrid

BASE = date(2015, 1, 5)
# ~10.4 years: long enough that 10-day-candle MA200 rows (need 200 native
# candles = 2000 sessions) are evaluable, so the leak test is not vacuous on
# the slowest facets.
N_BARS = 2600


def _tape(seed=7, n=N_BARS):
    """Deterministic pseudo-random daily tape: regime-shifted random walk
    with varying ranges and volumes; always strictly positive, OHLC-valid."""
    rng = np.random.default_rng(seed)
    drift = np.where(np.arange(n) < n // 2, 0.08, -0.05)
    changes = rng.normal(drift, 1.2, n)
    closes = 100.0 * np.exp(np.cumsum(changes) / 100.0)
    bars = {}
    prev = closes[0] * 0.99
    for i in range(n):
        c = float(closes[i])
        o = float(prev)
        spread = abs(rng.normal(0, 0.6))
        h = max(o, c) + spread
        l = min(o, c) - spread
        end = BASE + timedelta(days=i)
        bars[i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                            open=o, high=h, low=l, close=c,
                            volume=float(rng.uniform(1e5, 9e5)))
        prev = c
    return bars


def _future_bars(start_slot, n, setup, absurd=1e6):
    """Bars entirely at/after the setup date: impossible prices, leaked
    availability on the first one (end == setup yet available_from == setup).
    None of these is knowable at the setup open."""
    out = {}
    for k in range(n):
        slot = start_slot + k
        end = setup + timedelta(days=k)
        af = setup if k == 0 else end + timedelta(days=1)   # k=0 leaks
        out[slot] = NativeBar(end=end, available_from=af, open=absurd,
                              high=absurd * 1.1, low=absurd * 0.9,
                              close=absurd, volume=absurd)
    return out


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid()


@pytest.fixture(scope='module')
def definitions(grid):
    """One bound definition set per FACETS entry (first covered tree row,
    default variant), spanning every master recipe."""
    out = []
    seen_recipes = set()
    for qid in sorted(grid.tree):
        row = grid.tree[qid]
        if row.get('part') != 'base':
            continue
        entry = FACETS.get(row['L4_analysis'])
        specs = entry if isinstance(entry, list) else (entry,) if entry else ()
        if not any((row['L1_type'], row['L3_derivative']) in spec['l1_l3']
                   for spec in specs):
            continue
        variant = next(grid.variants(qid))
        try:
            defs = bind_master_question(row, variant)
        except NotImplementedError:
            continue
        recipe = defs[0]['feature']['recipe']
        if recipe in seen_recipes:
            continue
        seen_recipes.add(recipe)
        out.append((qid, defs))
    return out


def _answers(defs, bars, setup, last):
    return [evaluate_master(d, bars, setup, last).answer for d in defs]


def test_leak_future_bars_do_not_change_answers(definitions):
    setup = BASE + timedelta(days=N_BARS)
    last = N_BARS - 1
    base = _tape()
    future_lo = _future_bars(N_BARS, 30, setup, absurd=1e6)
    future_hi = _future_bars(N_BARS, 30, setup, absurd=1e-3)
    checked = 0
    for qid, defs in definitions:
        want = _answers(defs, base, setup, last)
        if not any(a != 'NOT_EVALUABLE' for a in want):
            continue                      # vacuous on this tape; construction
            # argument covers it, and the invariance check would be empty
        checked += 1
        assert _answers(defs, {**base, **future_lo}, setup, last) == want, \
            f'{qid}: answer changed after adding absurd-price future bars'
        assert _answers(defs, {**base, **future_hi}, setup, last) == want, \
            f'{qid}: answer changed after adding absurd-price future bars'
    assert checked >= 20, f'only {checked} recipes evaluable; leak test too thin'


def test_leak_day_d_bar_at_cutoff_forces_not_evaluable(definitions):
    """Replace the cutoff bar (the last slot every facet's window ends on)
    with a candle that ends ON the setup date (never knowable before D's
    open). Every definition must go NOT_EVALUABLE — never answer from day-D
    information."""
    setup = BASE + timedelta(days=N_BARS)
    last = N_BARS - 1
    for qid, defs in definitions:
        bars = _tape()
        bars[last] = NativeBar(
            end=setup, available_from=setup + timedelta(days=1),
            open=500.0, high=510.0, low=490.0, close=505.0, volume=5e6)
        got = _answers(defs, bars, setup, last)
        assert all(a == 'NOT_EVALUABLE' for a in got), \
            f'{qid}: day-D bar at cutoff produced {set(got)}'


def test_leak_unavailable_bar_at_cutoff_forces_not_evaluable(definitions):
    """Same, but the cutoff bar is only available AFTER the setup date
    (published late). Also must be NOT_EVALUABLE everywhere."""
    setup = BASE + timedelta(days=N_BARS)
    last = N_BARS - 1
    for qid, defs in definitions:
        bars = _tape()
        bar = bars[last]
        bars[last] = NativeBar(
            end=bar.end, available_from=setup + timedelta(days=3),
            open=bar.open, high=bar.high, low=bar.low, close=bar.close,
            volume=bar.volume)
        got = _answers(defs, bars, setup, last)
        assert all(a == 'NOT_EVALUABLE' for a in got), \
            f'{qid}: late-available bar at cutoff produced {set(got)}'
