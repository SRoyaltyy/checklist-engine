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
        if spec['cutoff_id'] is None:
            # bool3 facets (gap fates) register no cutoff dial
            assert tags == []
        else:
            assert [t.split('=')[0] for t in tags] == [spec['cutoff_id']]


def test_bind_default_and_changed_variants(grid):
    for facet in FACETS:
        row, variant = _first_variant(grid, facet)
        defs = bind_master_question(row, variant)
        assert len(defs) == len(FACETS[facet]['outcomes'])
        for d in defs:
            assert d['question_id'].startswith('BM1-')
            assert d['definition_status'] == 'BOUND'
            literal_threshold(d['comparison_threshold'])
        # changed variant (second variant yielded) must differ in threshold;
        # bool3 facets (gap fates) have no cutoff dial -> only the default variant
        variants = list(grid.variants(row['question_id']))
        if len(variants) < 2:
            assert FACETS[facet]['cutoff_id'] is None
            continue
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
    # overnight_vs_intraday has no registered share cutoff (gap_driven vs mixed
    # boundary undefined) -> honestly unbound until the dials register one.
    row = grid.tree['B|candles|OHLC|overnight_vs_intraday|1x3']
    variant = next(grid.variants(row['question_id']))
    with pytest.raises(NotImplementedError):
        bind_master_question(row, variant)


def _q(grid, qid):
    return grid.tree[qid], next(grid.variants(qid))


def _by_outcome(defs):
    return {d['source_outcome']: d for d in defs}


def test_bind_batch2_variants(grid):
    for facet, qid, n_outcomes in (('gap_up', 'B|candles|OHLC|gap_up|1x3', 3),
                                   ('gap_down', 'B|candles|OHLC|gap_down|1x3', 3),
                                   ('inside_outside', 'B|candles|OHLC|inside_outside|1x3', 4),
                                   ('run_biggest_move', 'B|candles|OHLC|run_biggest_move|1x20', 3)):
        row, variant = _q(grid, qid)
        defs = bind_master_question(row, variant)
        assert len(defs) == n_outcomes
        for d in defs:
            assert d['feature_kind'] in ('boolean', 'integer_count', 'continuous')
            literal_threshold(d['comparison_threshold'])
    # bool3 facets take no cutoff; mixed/band take exactly their registered one
    _, gv = _q(grid, 'B|candles|OHLC|gap_up|1x3')
    assert dict(gv.settings) == {}
    _, iv = _q(grid, 'B|candles|OHLC|inside_outside|1x3')
    assert set(dict(iv.settings)) == {'C019_inside_outside__scalar2'}


def _bars_hl(spec, slot0=100):
    """spec: list of (open, high, low, close)."""
    bars = {}
    for i, (o, h, l, c) in enumerate(spec):
        end = date(2024, 3, 1) + timedelta(days=i)
        bars[slot0 + i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                                    open=float(o), high=float(h), low=float(l), close=float(c))
    return bars


def test_evaluate_gap_up_fate(grid):
    row, variant = _q(grid, 'B|candles|OHLC|gap_up|1x3')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 8)
    last = 103
    # bars 1..3 = window; no gap (each open inside prior range)
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (11, 12, 10.5, 11.5),
                     (11.5, 12.5, 11, 12)])
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['open'], bars, setup, last).answer == 'NO'
    # gap up at window bar 2 (open 13 > prior high 11.5), never trades back -> open
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (13, 14, 12.5, 13.5),
                     (13.5, 14.5, 13, 14)])
    assert evaluate_master(defs['open'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['filled'], bars, setup, last).answer == 'NO'
    # gap up then a later low back at/below the pre-gap high -> filled
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (13, 14, 12.5, 13.5),
                     (13, 13.2, 11.0, 11.5)])
    assert evaluate_master(defs['filled'], bars, setup, last).answer == 'YES'
    # insufficient bars (need 4) -> all NOT_EVALUABLE
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (11, 12, 10.5, 11.5)])
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_gap_down_fate(grid):
    row, variant = _q(grid, 'B|candles|OHLC|gap_down|1x3')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 8)
    last = 103
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (11, 12, 10.5, 11.5),
                     (11.5, 12.5, 11, 12)])
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'
    # gap down at bar 2 (open 8 < prior low 10), later high back >= prior low -> filled
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (8, 9.5, 7.5, 9),
                     (9, 10.5, 8.8, 10.2)])
    assert evaluate_master(defs['filled'], bars, setup, last).answer == 'YES'
    # gap down staying down -> open
    bars = _bars_hl([(10, 11, 9, 10.5), (10.5, 11.5, 10, 11), (8, 9.5, 7.5, 9),
                     (9, 9.6, 8.6, 9.2)])
    assert evaluate_master(defs['open'], bars, setup, last).answer == 'YES'


def test_evaluate_inside_outside(grid):
    row, variant = _q(grid, 'B|candles|OHLC|inside_outside|1x3')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 8)
    last = 103
    # bar2 inside bar1 (h/l within), bar3 inside bar2 -> max inside run 2
    bars = _bars_hl([(10, 12, 9, 11), (10.5, 11.5, 9.5, 11), (10.6, 11.4, 9.6, 10.8),
                     (10.7, 11.3, 9.7, 10.9)])
    assert evaluate_master(defs['inside_cluster_ge'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # strict majority outside: make 2 of 3 window bars outside
    bars = _bars_hl([(10, 12, 9, 11), (13, 14, 8, 9.5), (10.5, 11.5, 9.5, 11),
                     (13, 14, 8, 9.5)])
    assert evaluate_master(defs['mostly_outside'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['inside_cluster_ge'], bars, setup, last).answer == 'NO'


def test_evaluate_run_biggest_move(grid):
    row, variant = _q(grid, 'B|candles|OHLC|run_biggest_move|1x20')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 21   # lookback 20 + 1 prior
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # tiny ranges (ATR ~0.3) then one big body run: 3 green bars of body ~3
    spec = [(10 + i * 0.05, 10.2 + i * 0.05, 9.9 + i * 0.05, 10.1 + i * 0.05)
            for i in range(span - 4)]
    base = 10.1 + (span - 5) * 0.05
    spec += [(base, base + 3.2, base - 0.1, base + 3.0),
             (base + 3.0, base + 6.2, base + 2.9, base + 6.0),
             (base + 6.0, base + 9.2, base + 5.9, base + 9.0),
             (base + 9.0, base + 9.3, base + 8.9, base + 9.2)]
    bars = _bars_hl(spec)
    assert evaluate_master(defs['big'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['normal'], bars, setup, last).answer == 'NO'
    # all doji -> NOT_EVALUABLE (no run)
    spec = [(10, 10.1, 9.9, 10)] * span
    bars = _bars_hl(spec)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


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
