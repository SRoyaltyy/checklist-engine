"""Tests for Kimi batch-1 master binders and the BINARY_MASTER emitter."""
import csv
from datetime import date, timedelta
import hashlib
import shutil
from pathlib import Path

import pytest

from world_binary_master import (FACETS, NativeBar, bind_master_question,
                                 evaluate_master)
from world_binary_price import bind_price_question
from world_question_grid import CanonicalGrid, GRID, QUESTIONS, TREE, ROOT
from world_binary_questions import literal_threshold
from ci.binary_master_build import LADDERS, MASTER_CSV, REPORT, build


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


def _first_variant(grid, facet):
    qid = next(q for q in sorted(grid.questions)
               if q.split('|')[1:4] == ['candles', 'OHLC', facet])
    return grid.tree[qid], next(grid.variants(qid))


def test_batch1_facets_have_exactly_one_registered_cutoff(grid):
    for facet, spec in FACETS.items():
        row = grid.tree[next(q for q in grid.questions if q.split('|')[3] == facet
                             and q.split('|')[1] == 'candles')]
        assert row['L4_analysis'] == facet
        tags = [t for t in grid.questions[row['question_id']]['default_tags'].split(';') if t]
        assert [t.split('=')[0] for t in tags] == [spec['cutoff_id']]


def test_bind_default_and_changed_variants(grid):
    for facet in FACETS:
        row, variant = _first_variant(grid, facet)
        defs = bind_master_question(row, variant)
        assert len(defs) == 3
        for d in defs:
            assert d['question_id'].startswith('BM1-')
            assert d['definition_status'] == 'BOUND'
            literal_threshold(d['comparison_threshold'])
        # changed variant (second variant yielded) must differ in threshold
        _, changed = None, None
        variants = list(grid.variants(row['question_id']))
        changed = variants[1]
        defs2 = bind_master_question(row, changed)
        assert {d['comparison_threshold'] for d in defs} != {d['comparison_threshold'] for d in defs2}


def test_ratio_mirror_threshold_is_exact_reciprocal(grid):
    row, variant = _first_variant(grid, 'red_green_balance')
    spec = FACETS['red_green_balance']
    v = dict(variant.settings)[spec['cutoff_id']]
    defs = bind_master_question(row, variant)
    by_outcome = {d['source_outcome']: d for d in defs}
    from decimal import Decimal, getcontext
    getcontext().prec = 28
    assert by_outcome['red']['comparison_threshold'] == format(
        Decimal(1) / Decimal(v), 'f').rstrip('0').rstrip('.')
    assert by_outcome['green']['comparator'] == '>'
    assert by_outcome['red']['comparator'] == '<'
    assert by_outcome['even']['feature']['transform'] == 'mirror_min'
    assert by_outcome['even']['comparator'] == '>='


def test_wick_body_signed_thresholds(grid):
    row, variant = _first_variant(grid, 'wick_body')
    defs = bind_master_question(row, variant)
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['upper_dominant']['comparison_threshold'] == '0.15'
    assert by_outcome['lower_dominant']['comparison_threshold'] == '-0.15'
    assert by_outcome['balanced']['feature']['transform'] == 'abs'


def _bars(closes, slot0=100):
    """All-green or custom synthetic daily bars; end < setup_date."""
    bars = {}
    for i, c in enumerate(closes):
        o = c[0] if isinstance(c, tuple) else c - 1.0
        h = (max(o, c[1] if isinstance(c, tuple) else c) + 0.5)
        l = (min(o, c[1] if isinstance(c, tuple) else c) - 0.5)
        cl = c[1] if isinstance(c, tuple) else c
        end = date(2024, 3, 1) + timedelta(days=i)
        bars[slot0 + i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                                    open=o, high=h, low=l, close=cl)
    return bars


def _tf(row):
    timeframe, lookback = map(int, row['L2_timeframe'].split('x'))
    return timeframe, lookback, timeframe * lookback


def _defs_by_outcome(grid, facet):
    row, variant = _first_variant(grid, facet)
    return row, variant, {d['source_outcome']: d for d in bind_master_question(row, variant)}


def _setup(row):
    timeframe, lookback, span = _tf(row)
    return timeframe, lookback, span, date(2024, 3, 1) + timedelta(days=span + 1), 100 + span - 1


def test_evaluate_red_green_balance(grid):
    row, variant, defs = _defs_by_outcome(grid, 'red_green_balance')
    timeframe, lookback, span, setup, last_slot = _setup(row)
    bars = _bars([(10, 12.0)] * span)  # all green, body 2
    assert evaluate_master(defs['green'], bars, setup, last_slot).answer == 'YES'
    assert evaluate_master(defs['red'], bars, setup, last_slot).answer == 'NO'
    assert evaluate_master(defs['even'], bars, setup, last_slot).answer == 'NO'
    # all red -> ratio 0.0 -> red YES
    bars = _bars([(12, 10.0)] * span)
    assert evaluate_master(defs['red'], bars, setup, last_slot).answer == 'YES'
    # all doji (zero bodies) -> NOT_EVALUABLE, never NO
    bars = _bars([(10, 10.0)] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last_slot).answer == 'NOT_EVALUABLE'


def test_evaluate_down_vs_up_and_last_green(grid):
    row, variant, defs = _defs_by_outcome(grid, 'down_vs_up_moves')
    timeframe, lookback, span, setup, last_slot = _setup(row)
    big_down = (12.0, 6.0)
    small_up = (10.0, 11.0)
    bars = _bars([big_down if (i // timeframe) % 2 == 0 else small_up for i in range(span)])
    assert evaluate_master(defs['downs_bigger'], bars, setup, last_slot).answer == 'YES'
    # one-sided window -> NOT_EVALUABLE
    bars = _bars([(10, 12.0)] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last_slot).answer == 'NOT_EVALUABLE'

    row2, _, defs2 = _defs_by_outcome(grid, 'last_green_vs_red')
    timeframe2, lookback2, span2, setup2, last_slot2 = _setup(row2)
    bars = _bars([(10, 10.5)] * (span2 - 2 * timeframe2)
                 + [(12.0, 6.0)] * timeframe2
                 + [(20, 30.0)] * timeframe2)
    assert evaluate_master(defs2['green_bigger'], bars, setup2, last_slot2).answer == 'YES'


def test_evaluate_wick_body(grid):
    row, variant, defs = _defs_by_outcome(grid, 'wick_body')
    timeframe, lookback, span, setup, last_slot = _setup(row)
    # upper-wick-heavy candles: O=L=10, C=11, H=13 -> upper wick 2, lower 0
    bars = {}
    for i in range(span):
        end = date(2024, 3, 1) + timedelta(days=i)
        bars[100 + i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                                  open=10.0, high=13.0, low=10.0, close=11.0)
    assert evaluate_master(defs['upper_dominant'], bars, setup, last_slot).answer == 'YES'
    assert evaluate_master(defs['lower_dominant'], bars, setup, last_slot).answer == 'NO'


def test_master_falls_back_to_gpt_binders(grid):
    row = grid.tree['B|candles|OHLC|intraday_change|1x3']
    variant = next(grid.variants(row['question_id']))
    assert bind_master_question(row, variant) == bind_price_question(row, variant)


def test_unbound_family_raises(grid):
    row = grid.tree['B|candles|OHLC|gap_up|1x3']
    variant = next(grid.variants(row['question_id']))
    with pytest.raises(NotImplementedError):
        bind_master_question(row, variant)


def _stage_root(tmp_path):
    for rel in (GRID, QUESTIONS, TREE, LADDERS):
        src = Path(ROOT) / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)


def test_emitter_smoke_and_determinism(tmp_path):
    _stage_root(tmp_path)
    report1 = build(tmp_path)
    csv_path = tmp_path / 'docs' / MASTER_CSV
    first = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    report2 = build(tmp_path)
    assert report1['csv_sha256'] == first == report2['csv_sha256']
    assert report1['master_total_rows'] == (
        report1['bound_unique_binary_definitions'] + report1['ladder_add_on_rows'])
    assert report1['ladder_add_on_rows'] == 2680
    assert report1['bound_unique_binary_definitions'] > 633  # GPT 633 + batch-1 facets
    with csv_path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == report1['master_total_rows']
    bound = [r for r in rows if r['definition_status'] == 'BOUND']
    assert {r['facet'] for r in bound} >= set(FACETS)
    assert {r['facet'] for r in bound} <= set(FACETS) | {
        'intraday_change', 'interday_change', 'run_structure'}
    for r in bound:
        literal_threshold(r['comparison_threshold'])
        assert r['question_id'].startswith('BM1-')
        assert r['knowable_at_setup_open']
        assert r['not_evaluable_condition']
    assert report1['unbound_oat_variants'] > 0
    assert (tmp_path / 'docs' / REPORT).exists()
