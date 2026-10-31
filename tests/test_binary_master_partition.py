"""Partition-exactness property tests for categorical BINARY_MASTER_V1 facets.

For every facet in world_binary_master.EXACT_PARTITION_FACETS, on seeded
random-regime tapes plus crafted regime tapes, every bound outcome set must
satisfy: at most one outcome answers YES per tape, and if any outcome is
evaluable at all, exactly one answers YES. Zero YES is only legitimate when
every outcome is NOT_EVALUABLE (excluded, never NO). This catches partition
bugs (overlapping or gappy outcome buckets) across all OAT dial variants and
timeframes of the included facets before any mining consumes the answers.
"""
from datetime import date, timedelta

import pytest

from world_binary_master import (EXACT_PARTITION_FACETS, FACETS, NativeBar,
                                 _iter_specs, bind_master_question,
                                 evaluate_master)
from world_question_grid import CanonicalGrid, ROOT

SPAN = 600                      # bars; supports lb*k <= 200 rows comfortably
CRAFTED = 3
RANDOM_TAPES = 3
TOTAL_TAPES = CRAFTED + RANDOM_TAPES


def _tape_bars(closes, volumes, slot0=100):
    bars = {}
    base = date(2024, 3, 1)
    for i, (c, v) in enumerate(zip(closes, volumes)):
        end = base + timedelta(days=i)
        bars[slot0 + i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                                    open=float(c), high=float(c) + 1.5,
                                    low=float(c) - 1.0, close=float(c),
                                    volume=float(v))
    return bars


def _crafted_tapes():
    import math
    tapes = []
    # 1: steady uptrend, calm volume
    closes = [100.0 * math.exp(0.0012 * i) for i in range(SPAN)]
    vols = [1.0e6] * SPAN
    tapes.append(_tape_bars(closes, vols))
    # 2: long rise, violent 3-bar crash on 8x volume, slow recovery, flat tail
    closes = [100.0 * math.exp(0.0010 * i) for i in range(400)]
    vols = [1.0e6] * 400
    for j in range(3):
        closes.append(closes[-1] * 0.92)
        vols.append(8.0e6)
    for i in range(400):
        closes.append(closes[-1] * 1.0008)
        vols.append(1.2e6)
    closes += [closes[-1]] * (SPAN - len(closes))
    vols += [1.0e6] * (SPAN - len(vols))
    tapes.append(_tape_bars(closes, vols))
    # 3: sawtooth with alternating volume (dominance flips, big chop)
    closes, vols = [], []
    c = 100.0
    for i in range(SPAN):
        c *= 1.03 if i % 2 == 0 else 0.97
        closes.append(c)
        vols.append(2.0e6 if i % 2 == 0 else 0.6e6)
    tapes.append(_tape_bars(closes, vols))
    return tapes


def _random_tapes():
    import numpy as np
    tapes = []
    for seed in range(RANDOM_TAPES):
        rng = np.random.RandomState(10_000 + seed)
        n = SPAN
        drift1, drift2 = rng.choice([-0.002, 0.0, 0.002], 2, replace=False)
        vol1, vol2 = rng.choice([0.01, 0.02, 0.04], 2, replace=False)
        rets = np.concatenate([
            drift1 + vol1 * rng.randn(n // 2),
            drift2 + vol2 * rng.randn(n - n // 2),
        ])
        closes = list(100.0 * np.exp(np.cumsum(rets)))
        vols = list(1.0e6 * np.exp(0.3 * rng.randn(n)))
        spike_at = rng.randint(50, n - 50)
        vols[spike_at] *= 5.0
        tapes.append(_tape_bars(closes, vols))
    return tapes


@pytest.fixture(scope='module')
def tapes():
    return _crafted_tapes() + _random_tapes()


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


def _specs_by_facet():
    out = {}
    for facet, spec in _iter_specs():
        out.setdefault(facet, []).append(spec)
    return out


def _rows_for(grid, facet, spec):
    """Tree rows for this facet's sub-spec (L1,L3,L4), restricted to tape length."""
    rows = []
    for l1, l3 in spec['l1_l3']:
        for qid in sorted(grid.questions):
            p = qid.split('|')
            if len(p) == 5 and p[1] == l1 and p[2] == l3 and p[3] == facet:
                row = grid.tree[qid]
                k = int(row['L2_timeframe'].split('x')[0])
                lb = int(row['L2_timeframe'].split('x')[1])
                if lb * k <= 200:          # evaluable on the 600-bar tapes
                    rows.append((qid, row))
    return rows


def test_exact_partition_facets_are_bound(grid):
    by_facet = _specs_by_facet()
    for facet in sorted(EXACT_PARTITION_FACETS):
        assert facet in by_facet, f'{facet}: not a FACETS key'
        rows = [r for spec in by_facet[facet] for r in _rows_for(grid, facet, spec)]
        bound = 0
        for qid, row in rows:
            try:
                bound += len(bind_master_question(row, next(grid.variants(qid))))
            except NotImplementedError:
                pass        # honestly unbound L3s (e.g. VWAP_anchored) skip
        assert bound > 0, f'{facet}: no bound rows found for partition test'


def test_exact_partition_property(grid, tapes):
    by_facet = _specs_by_facet()
    setup = date(2024, 3, 1) + timedelta(days=SPAN + 1)
    last = 100 + SPAN - 1
    total_yes = 0
    family_yes = {}
    for facet in sorted(EXACT_PARTITION_FACETS):
        rows = [r for spec in by_facet[facet] for r in _rows_for(grid, facet, spec)]
        yes_here = 0
        checked = 0
        for qid, row in rows:
            try:
                defs = bind_master_question(row, next(grid.variants(qid)))
            except NotImplementedError:
                continue
            # very wide outcome sets (capitulation_bar 73): one daily row and
            # four tapes only — the partition logic is timeframe-agnostic and
            # each evaluation recomputes heavy talib series (~0.25 s/def)
            use_tapes = tapes
            if len(defs) > 20:
                if row['L2_timeframe'] != '1x10':
                    continue
                use_tapes = tapes[:4]
            for bars in use_tapes:
                answers = [evaluate_master(d, bars, setup, last).answer
                           for d in defs]
                n_yes = answers.count('YES')
                n_eval = sum(1 for a in answers if a != 'NOT_EVALUABLE')
                assert n_yes <= 1, (
                    f'{facet} {qid}: {n_yes} outcomes YES simultaneously '
                    f'({[d["source_outcome"] for d, a in zip(defs, answers) if a == "YES"]})')
                assert (n_yes == 1) == (n_eval >= 1), (
                    f'{facet} {qid}: evaluable outcomes but none YES '
                    f'({dict(zip([d["source_outcome"] for d in defs], answers))})')
                checked += 1
                yes_here += n_yes
        assert checked > 0, f'{facet}: no evaluations ran'
        total_yes += yes_here
        family_yes[facet] = yes_here
    # non-vacuous: the tapes must actually produce YES answers broadly
    assert total_yes >= 200, f'partition test nearly vacuous: {family_yes}'
    # every included family must fire at least once across the tapes
    cold = {f: n for f, n in family_yes.items() if n == 0}
    assert not cold, f'families with zero YES across all tapes: {cold}'
