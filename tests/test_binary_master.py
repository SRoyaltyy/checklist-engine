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


def _iter_specs():
    for facet, entry in FACETS.items():
        for spec in (entry if isinstance(entry, list) else (entry,)):
            yield facet, spec


def _l1_l3(facet):
    entry = FACETS[facet]
    spec = entry[0] if isinstance(entry, list) else entry
    return spec['l1_l3'][0]


def _first_variant(grid, facet):
    l1, l3 = _l1_l3(facet)
    qid = next(q for q in sorted(grid.questions)
               if q.split('|')[1:4] == [l1, l3, facet])
    return grid.tree[qid], next(grid.variants(qid))


def test_batch1_facets_have_exactly_one_registered_cutoff(grid):
    for facet, spec in _iter_specs():
        expected = {spec['cutoff_id']} | set(spec['baked_cutoff_ids'])
        expected.discard(None)
        for l1, l3 in spec['l1_l3']:
            row = grid.tree[next(q for q in grid.questions if q.split('|')[3] == facet
                                 and q.split('|')[1] == l1 and q.split('|')[2] == l3)]
            assert row['L4_analysis'] == facet
            tags = [t for t in grid.questions[row['question_id']]['default_tags'].split(';') if t]
            if not expected:
                assert tags == []          # bool3 facets register no cutoff dial
            else:
                assert {t.split('=')[0] for t in tags} == expected


def test_bind_default_and_changed_variants(grid):
    for facet, spec in _iter_specs():
        row, variant = _first_variant(grid, facet)
        defs = bind_master_question(row, variant)
        assert len(defs) == len(spec['outcomes'])
        for d in defs:
            assert d['question_id'].startswith('BM1-')
            assert d['definition_status'] == 'BOUND'
            literal_threshold(d['comparison_threshold'])
        # changed variant (second variant yielded) must differ in threshold;
        # bool3 facets (gap fates) have no cutoff dial -> only the default variant
        variants = list(grid.variants(row['question_id']))
        if len(variants) < 2:
            assert spec['cutoff_id'] is None
            continue
        changed = variants[1]
        defs2 = bind_master_question(row, changed)
        if {d['comparison_threshold'] for d in defs} == {d['comparison_threshold'] for d in defs2}:
            # all-boolean/code facets carry dials inside the feature (baked map);
            # the changed variant must differ in at least one baked feature value
            assert spec.get('baked_map'), facet
            assert any({d['feature'][key] for d in defs} != {d['feature'][key] for d in defs2}
                       for key in spec['baked_map'].values())


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


def test_master_no_longer_falls_back_to_gpt_binders(grid):
    # Batch 13 bound intraday_change/interday_change/run_structure natively, so
    # no canonical qid reaches the GPT fallback anymore. Master must bind these
    # families itself, and the GPT binder module must still work standalone.
    for facet in ('intraday_change', 'interday_change', 'run_structure'):
        qid = sorted(q for q in grid.tree if q.split('|')[3] == facet
                     and q.startswith('B|candles|OHLC|'))[0]
        row = grid.tree[qid]
        variant = next(grid.variants(row['question_id']))
        master_defs = bind_master_question(row, variant)
        assert master_defs, f'{facet}: master returned no binding'
        assert all('source_outcome' in d for d in master_defs)
        gpt_defs = bind_price_question(row, variant)
        assert gpt_defs, f'{facet}: GPT binder module broken'
        assert all('source_outcome' in d for d in gpt_defs)


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


def _bars_hlv(spec, slot0=100):
    """spec: list of (open, high, low, close, volume)."""
    bars = {}
    for i, (o, h, l, c, v) in enumerate(spec):
        end = date(2024, 3, 1) + timedelta(days=i)
        bars[slot0 + i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                                    open=float(o), high=float(h), low=float(l),
                                    close=float(c), volume=float(v))
    return bars


def test_bind_batch3_variants(grid):
    for facet, qid, n_outcomes in (
            ('dominance', 'B|volume|up_down_volume|dominance|1x10', 3),
            ('dry_up_at_low', 'B|volume|RVOL20|dry_up_at_low|1x10', 4),
            ('max_vol_position', 'B|volume|RVOL20|max_vol_position|1x10', 4),
            ('vs_own_past', 'B|volume|RVOL20|vs_own_past|1x10', 3)):
        row, variant = _q(grid, qid)
        defs = bind_master_question(row, variant)
        assert len(defs) == n_outcomes
        for d in defs:
            assert d['question_id'].startswith('BM1-')
            assert d['definition_status'] == 'BOUND'
            literal_threshold(d['comparison_threshold'])
        by_outcome = {d['source_outcome']: d for d in defs}
        if facet == 'dominance':
            assert by_outcome['up_heavy']['comparator'] == '>'
            assert by_outcome['down_heavy']['comparator'] == '<'
            assert by_outcome['even']['feature']['transform'] == 'mirror_min'
        if facet == 'dry_up_at_low':
            assert by_outcome['at_low']['feature']['dry_up_mult'] == '0.6'
            assert all(by_outcome[o]['feature_kind'] == 'boolean' for o in by_outcome)
        if facet == 'max_vol_position':
            assert by_outcome['start']['feature']['max_vol_edge_bars'] == '2'
        if facet == 'vs_own_past':
            assert by_outcome['high']['feature']['baseline_bars'] == '250'
            assert by_outcome['high']['feature']['volume_source'] == 'volume'


def test_evaluate_dominance(grid):
    row, variant = _q(grid, 'B|volume|up_down_volume|dominance|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 12)
    last = 109
    # 6 up bars vol 200, 4 down bars vol 100 -> ratio 1200/400 = 3 -> up_heavy
    spec = [(10, 11, 9, 10.8, 200) if i % 5 in (0, 1, 2) else (10, 10.2, 9.8, 9.9, 100)
            for i in range(10)]
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['up_heavy'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['down_heavy'], bars, setup, last).answer == 'NO'
    # all volume on up bars -> +inf -> up_heavy YES, down_heavy NO
    spec = [(10, 11, 9, 10.8, 100)] * 10
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['up_heavy'], bars, setup, last).answer == 'YES'
    # all doji with volume -> 0/0 -> NOT_EVALUABLE
    spec = [(10, 10.2, 9.8, 10, 100)] * 10
    bars = _bars_hlv(spec)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'
    # bars without volume -> NOT_EVALUABLE, never a crash
    bars = _bars_hl([(10, 11, 9, 10.8)] * 10)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_dry_up_at_low(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|dry_up_at_low|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 59  # 49 prior + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # prior 49 bars volume 100; window: bar 5 has the lowest close AND dry volume 30
    spec = [(10 + i * 0.01, 10.2 + i * 0.01, 9.8 + i * 0.01, 10.1 + i * 0.01, 100)
            for i in range(49)]
    win = [(10.5, 10.7, 10.3, 10.6, 100),
           (10.6, 10.8, 10.4, 10.7, 100),
           (10.7, 10.9, 10.5, 10.8, 100),
           (10.8, 11.0, 10.6, 10.9, 100),
           (10.9, 11.1, 10.7, 11.0, 100),
           (9.0, 9.2, 8.8, 8.9, 30),     # window lowest close, dry (30 < 0.6*100)
           (10.0, 10.2, 9.8, 10.1, 100),
           (10.1, 10.3, 9.9, 10.2, 100),
           (10.2, 10.4, 10.0, 10.3, 100),
           (11.5, 11.7, 11.3, 11.6, 100)]  # window highest close, not dry
    bars = _bars_hlv(spec + win)
    assert evaluate_master(defs['at_low'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['at_high'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['both'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # also dry at the highest close -> both YES (exclusive at_low/at_high NO)
    win2 = list(win)
    win2[9] = (11.5, 11.7, 11.3, 11.6, 20)
    bars = _bars_hlv(spec + win2)
    assert evaluate_master(defs['both'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['at_low'], bars, setup, last).answer == 'NO'


def test_evaluate_max_vol_position(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|max_vol_position|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 12)
    last = 109
    closes = [10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 10.2, 11.1]  # min at 8
    base = [(c - 0.1, c + 0.1, c - 0.2, c, 100) for c in closes]
    # max volume at index 0 -> start (edge bars v=2); price low is index 8
    first = (base[0][0], base[0][1], base[0][2], base[0][3], 900)
    bars = _bars_hlv([first] + list(base[1:]))
    assert evaluate_master(defs['start'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['at_price_low'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['end'], bars, setup, last).answer == 'NO'
    # max volume at the window's lowest close (index 4) -> at_price_low beats start
    spec = list(base)
    spec[4] = (spec[4][0], spec[4][1], 8.8, 9.0, 900)  # valid bar, new lowest close
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['at_price_low'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['start'], bars, setup, last).answer == 'NO'
    # max volume in the middle -> middle
    spec = list(base)
    spec[5] = (spec[5][0], spec[5][1], spec[5][2], spec[5][3], 900)
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['middle'], bars, setup, last).answer == 'YES'
    # max volume at the last bar -> end
    spec = list(base)
    spec[9] = (spec[9][0], spec[9][1], spec[9][2], spec[9][3], 900)
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['end'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['middle'], bars, setup, last).answer == 'NO'


def test_evaluate_vs_own_past(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|vs_own_past|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 260  # 250 baseline + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # baseline volume 100, window volume 200 -> ratio 2 > 1.5 -> high
    spec = [(10 + i * 0.01, 10.2 + i * 0.01, 9.8 + i * 0.01, 10.1 + i * 0.01,
             100 if i < 250 else 200) for i in range(span)]
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['high'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['low'], bars, setup, last).answer == 'NO'
    # window quieter than baseline -> low YES
    spec = [(10 + i * 0.01, 10.2 + i * 0.01, 9.8 + i * 0.01, 10.1 + i * 0.01,
             100 if i < 250 else 50) for i in range(span)]
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['low'], bars, setup, last).answer == 'YES'
    # dollar_volume|vs_own_past registers only S_baseline_bars (no ratio dial)
    # -> stays honestly unbound this batch (counted by the emitter, not skipped)
    import pytest as _pytest
    row2, variant2 = _q(grid, 'B|volume|dollar_volume|vs_own_past|1x10')
    with _pytest.raises(NotImplementedError):
        bind_master_question(row2, variant2)


def test_bind_batch4_spike(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|spike|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 3
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['yes_early']['feature']['spike_baseline_bars'] == '50'
    assert by_outcome['yes_early']['feature']['spike_mult'] == '3'
    for d in defs:
        assert d['feature_kind'] == 'boolean'
        assert d['comparison_threshold'] == '1'
        literal_threshold(d['comparison_threshold'])


def test_evaluate_spike(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|spike|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 59  # 49 prior + 10 window (C031 default baseline 50)
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    prior = [(10 + i * 0.01, 10.2 + i * 0.01, 9.8 + i * 0.01, 10.1 + i * 0.01, 100)
             for i in range(49)]
    win_flat = [(10.5, 10.7, 10.3, 10.6, 100)] * 10
    # no spike: everything at the baseline median
    bars = _bars_hlv(prior + win_flat)
    assert evaluate_master(defs['no'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['yes_early'], bars, setup, last).answer == 'NO'
    # early spike at window index 1 (500 > 3*100); median window still 100
    win = list(win_flat)
    win[1] = (10.5, 10.7, 10.3, 10.6, 500)
    bars = _bars_hlv(prior + win)
    assert evaluate_master(defs['yes_early'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['yes_late'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['no'], bars, setup, last).answer == 'NO'
    # late spike at window index 8
    win = list(win_flat)
    win[8] = (10.5, 10.7, 10.3, 10.6, 500)
    bars = _bars_hlv(prior + win)
    assert evaluate_master(defs['yes_late'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['yes_early'], bars, setup, last).answer == 'NO'
    # earliest spike wins when two spikes present (early one at 2, late at 8)
    win = list(win_flat)
    win[2] = (10.5, 10.7, 10.3, 10.6, 400)
    win[8] = (10.5, 10.7, 10.3, 10.6, 900)
    bars = _bars_hlv(prior + win)
    assert evaluate_master(defs['yes_early'], bars, setup, last).answer == 'YES'
    # missing volume -> NOT_EVALUABLE
    bars = _bars_hl([(10.5, 10.7, 10.3, 10.6)] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_bind_batch4b_variants(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|maxvol_wick|1x20')
    defs = bind_master_question(row, variant)
    assert len(defs) == 3
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['bull_wick']['feature']['maxvol_wick_atr'] == '1'
    assert all(d['feature_kind'] == 'boolean' for d in defs)

    row, variant = _q(grid, 'B|volume|RVOL20|pullback_vs_run_volume|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 6
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['bull_lighter']['feature']['ratio_key'] == 'bull_ratio'
    assert by_outcome['bear_heavier']['feature']['ratio_key'] == 'bear_ratio'
    assert by_outcome['bull_lighter']['comparator'] == '<'
    assert by_outcome['bull_heavier']['comparator'] == '>'
    assert by_outcome['bull_similar']['feature']['transform'] == 'mirror_min'
    for d in defs:
        assert d['feature_kind'] == 'continuous'
        literal_threshold(d['comparison_threshold'])

    row, variant = _q(grid, 'B|volume|up_down_volume|flip|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 3
    assert all(d['feature_kind'] == 'boolean' for d in defs)


def test_evaluate_maxvol_wick(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|maxvol_wick|1x20')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 21
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # calm bars (ATR ~0.3); max-volume bar at window index 10 with a long
    # lower wick of 2 (>> 1*ATR14)
    spec = [(10 + i * 0.02, 10.1 + i * 0.02, 9.9 + i * 0.02, 10.05 + i * 0.02, 100)
            for i in range(span)]
    s = list(spec[10])
    spec[10] = (s[0], s[1], s[0] - 2.0, s[3], 900)   # low 2 below body
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['bull_wick'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bear_wick'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['small'], bars, setup, last).answer == 'NO'
    # long upper wick instead -> bear (lower wick stays small)
    spec = [(10 + i * 0.02, 10.1 + i * 0.02, 9.9 + i * 0.02, 10.05 + i * 0.02, 100)
            for i in range(span)]
    s = spec[10]
    spec[10] = (s[0], s[0] + 2.5, s[0] - 0.02, s[3], 900)
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['bear_wick'], bars, setup, last).answer == 'YES'
    # short window (needs 14+1) -> NOT_EVALUABLE
    bars = _bars_hlv(spec[:10])
    for d in defs.values():
        assert evaluate_master(d, bars, setup, 109).answer == 'NOT_EVALUABLE'


def test_evaluate_pullback_vs_run_volume(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|pullback_vs_run_volume|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 12)
    last = 109
    # up leg: 4 green bars vol 100; pullback: 3 red bars vol 50 -> ratio 0.5 < 1/1.3
    up = (10, 10.5, 9.9, 10.4)
    dn = (10.4, 10.5, 9.9, 10.0)
    spec = [up] * 4 + [dn] * 6   # up leg ends at 3; pullback runs to window end
    vols = [100] * 4 + [50] * 6
    bars = _bars_hlv([(o, h, l, c, v) for (o, h, l, c), v in zip(spec, vols)])
    assert evaluate_master(defs['bull_lighter'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bull_heavier'], bars, setup, last).answer == 'NO'
    # bear side has no qualifying leg -> NOT_EVALUABLE
    assert evaluate_master(defs['bear_lighter'], bars, setup, last).answer == 'NOT_EVALUABLE'
    # heavier pullback: pullback vol 200 -> ratio 2 > 1.3
    vols = [100] * 4 + [200] * 6
    bars = _bars_hlv([(o, h, l, c, v) for (o, h, l, c), v in zip(spec, vols)])
    assert evaluate_master(defs['bull_heavier'], bars, setup, last).answer == 'YES'
    # bear leg last: 4 red bars then bounce to window end
    spec = [dn] * 4 + [up] * 6
    vols = [100] * 4 + [50] * 6
    bars = _bars_hlv([(o, h, l, c, v) for (o, h, l, c), v in zip(spec, vols)])
    assert evaluate_master(defs['bear_lighter'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bull_lighter'], bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_flip(grid):
    row, variant = _q(grid, 'B|volume|up_down_volume|flip|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 12)
    last = 109
    up = (10, 10.5, 9.9, 10.4)
    dn = (10.4, 10.5, 9.9, 10.0)
    # early half down-dominant (vol 200 on down), late half up-dominant -> to_up
    spec = [dn] * 2 + [up] + [dn] + [up] * 4 + [dn] + [up]
    vols = [200, 200, 10, 200, 200, 200, 200, 200, 10, 200]
    bars = _bars_hlv([(o, h, l, c, v) for (o, h, l, c), v in zip(spec, vols)])
    assert evaluate_master(defs['to_up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['to_down'], bars, setup, last).answer == 'NO'
    # mirror -> to_down
    spec = [up] * 3 + [dn] + [dn] * 4 + [up] + [dn]
    vols = [200, 200, 200, 10, 200, 200, 200, 200, 10, 200]
    bars = _bars_hlv([(o, h, l, c, v) for (o, h, l, c), v in zip(spec, vols)])
    assert evaluate_master(defs['to_down'], bars, setup, last).answer == 'YES'
    # same dominance both halves -> none
    spec = [up] * 5 + [up] * 5
    vols = [200] * 10
    bars = _bars_hlv([(o, h, l, c, v) for (o, h, l, c), v in zip(spec, vols)])
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'


def _bars_from_closes(closes, slot0=100):
    bars = {}
    prev = closes[0]
    for i, c in enumerate(closes):
        end = date(2024, 3, 1) + timedelta(days=i)
        o = prev
        bars[slot0 + i] = NativeBar(end=end, available_from=end + timedelta(days=1),
                                    open=float(o), high=float(max(o, c) * 1.001),
                                    low=float(min(o, c) * 0.999), close=float(c))
        prev = c
    return bars


def test_bind_batch5_variants(grid):
    row, variant = _q(grid, 'B|overbought_oversold|RSI14|rsi_floor|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 4
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['below_extreme']['feature']['rsi_period'] == '14'
    assert by_outcome['below_extreme']['feature']['rsi_t1'] == '30'
    assert by_outcome['below_extreme']['feature']['rsi_t2'] == '40'
    assert by_outcome['below_extreme']['feature']['rsi_t3'] == '50'
    assert by_outcome['below_extreme']['comparison_threshold'] == '0'
    assert by_outcome['high_band']['comparison_threshold'] == '3'
    assert all(d['feature_kind'] == 'integer_count' for d in defs)

    row, variant = _q(grid, 'B|overbought_oversold|RSI6|rsi_ceiling|1x10')
    defs = bind_master_question(row, variant)
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['above_extreme']['feature']['rsi_t1'] == '70'

    row, variant = _q(grid, 'B|moving_averages|SMA20|fresh_cross|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 4
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['up']['feature']['ma_kind'] == 'SMA'
    assert by_outcome['up']['feature']['ma_period'] == '20'
    assert all(d['feature_kind'] == 'boolean' for d in defs)

    row, variant = _q(grid, 'B|moving_averages|EMA21|fresh_cross|1x10')
    defs = bind_master_question(row, variant)
    assert {d['source_outcome']: d for d in defs}['up']['feature']['ma_kind'] == 'EMA'


def test_evaluate_rsi_floor(grid):
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|rsi_floor|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 16  # 6 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # all gains in window -> RSI 100 -> code 3 (high_band)
    closes = [50.0 + 0.1 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['high_band'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['below_extreme'], bars, setup, last).answer == 'NO'
    # all losses -> RSI 0 -> code 0 (below_extreme)
    closes = [50.0 - 0.1 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['below_extreme'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['high_band'], bars, setup, last).answer == 'NO'
    # alternating +/- with one extra loss -> min RSI ~41.7 -> code 2 (mid_band 40-50)
    changes = [1, -1, 1, -1, 1, -1, -1, 1, -1, 1, -1, 1, -1, 1, -1]
    closes = [50.0]
    for ch in changes:
        closes.append(closes[-1] + 0.1 * ch)
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['mid_band'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['low_band'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['high_band'], bars, setup, last).answer == 'NO'


def test_evaluate_rsi_ceiling(grid):
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|rsi_ceiling|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 16
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    closes = [50.0 + 0.1 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['above_extreme'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['low_band'], bars, setup, last).answer == 'NO'
    closes = [50.0 - 0.1 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['low_band'], bars, setup, last).answer == 'YES'


def test_evaluate_fresh_cross(grid):
    row, variant = _q(grid, 'B|moving_averages|SMA20|fresh_cross|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 30  # 20 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # flat then rising through the MA -> up
    closes = [100.0] * 20 + [101.0 + i for i in range(10)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # rising then falling back below -> both
    closes = [100.0] * 20 + [101.0 + i for i in range(5)] + [99.0 - i for i in range(5)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['both'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'NO'
    # flat then falling -> down
    closes = [100.0] * 20 + [99.0 - i for i in range(10)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'YES'
    # perfectly flat -> no crossings -> none
    closes = [100.0] * span
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'


def test_bind_batch6_variants(grid):
    row, variant = _q(grid, 'B|moving_averages|SMA20|slope|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 3
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['up']['feature']['ma_kind'] == 'SMA'
    assert by_outcome['up']['feature']['ma_period'] == '20'
    assert by_outcome['up']['comparison_threshold'] == '1'      # C091 default
    assert by_outcome['up']['comparator'] == '>'
    assert by_outcome['down']['comparison_threshold'] == '-1'
    assert by_outcome['down']['comparator'] == '<'
    assert by_outcome['flat']['comparator'] == '<='
    assert by_outcome['flat']['feature']['transform'] == 'abs'
    assert all(d['feature_kind'] == 'continuous' for d in defs)
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C091_slope__pct1') == '0.5')
    defs2 = {d['source_outcome']: d for d in bind_master_question(row, changed)}
    assert defs2['up']['comparison_threshold'] == '0.5'
    assert defs2['down']['comparison_threshold'] == '-0.5'

    row, variant = _q(grid, 'B|overbought_oversold|RSI14|cross_event|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 4
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['up']['feature']['osc_kind'] == 'RSI'
    assert by_outcome['up']['feature']['cross_line'] == '50'
    assert by_outcome['up']['feature']['osc_warmup'] == '15'
    assert all(d['feature_kind'] == 'boolean' for d in defs)

    row, variant = _q(grid, 'B|momentum|MACD12_26_9|cross_event|1x10')
    by_outcome = {d['source_outcome']: d for d in bind_master_question(row, variant)}
    assert by_outcome['up']['feature']['cross_line'] == 'signal'
    assert by_outcome['up']['feature']['osc_warmup'] == '34'

    row, variant = _q(grid, 'B|momentum|ROC20|cross_event|1x10')
    by_outcome = {d['source_outcome']: d for d in bind_master_question(row, variant)}
    assert by_outcome['up']['feature']['cross_line'] == '0'
    assert by_outcome['up']['feature']['osc_warmup'] == '21'


def test_evaluate_slope(grid):
    row, variant = _q(grid, 'B|moving_averages|SMA20|slope|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 30  # 20 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # steadily rising: window MA rises ~5% -> up
    closes = [100.0 + 0.5 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'NO'
    # steadily falling -> down
    closes = [100.0 - 0.5 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'NO'
    # flat -> slope 0 <= 1 -> flat
    closes = [100.0] * span
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'NO'


def test_evaluate_cross_event(grid):
    # RSI14 midline cross: 15 warmup bars all losses, then 10 window bars all gains
    row, variant = _q(grid, 'B|overbought_oversold|RSI14|cross_event|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 25  # 15 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    closes = [100.0 - 0.5 * i for i in range(15)] + [92.5 + 1.0 * i for i in range(10)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'NO'
    # all losses: RSI pinned at 0 -> none
    closes = [100.0 - 0.5 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'

    # ROC20 midline (0) cross: 21 warmup bars drifting down (ROC < 0), then a
    # strong window rise pushing ROC through 0 upwards
    row, variant = _q(grid, 'B|momentum|ROC20|cross_event|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 31  # 21 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    closes = [100.0 - 0.2 * i for i in range(21)] + [95.8 + 0.5 * i for i in range(10)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'NO'

    # MACD vs signal: bind + full evaluation path returns a strict answer
    row, variant = _q(grid, 'B|momentum|MACD12_26_9|cross_event|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 44  # 34 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    closes = [100.0 - 0.3 * i for i in range(34)] + [89.8 + 1.0 * i for i in range(10)]
    bars = _bars_from_closes(closes)
    for outcome in ('up', 'down', 'both', 'none'):
        assert evaluate_master(defs[outcome], bars, setup, last).answer in ('YES', 'NO')


def test_bind_batch7_variants(grid):
    row, variant = _q(grid, 'B|moving_averages|SMA20|cross_count|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 4
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['zero']['feature']['cross_low_edge'] == '2'
    assert by_outcome['zero']['feature']['cross_high_edge'] == '5'
    assert by_outcome['zero']['comparison_threshold'] == '0'
    assert by_outcome['high_band']['comparison_threshold'] == '3'
    assert all(d['feature_kind'] == 'integer_count' for d in defs)

    row, variant = _q(grid, 'B|volatility|ATR14|shock|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 5
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['none']['feature']['baseline_bars'] == '250'
    assert by_outcome['none']['feature']['shock_low_mult'] == '3'
    assert by_outcome['none']['feature']['shock_high_mult'] == '5'
    assert all(d['feature_kind'] == 'boolean' for d in defs)

    row, variant = _q(grid, 'B|overbought_oversold|RSI14|time_in_zone|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 4
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['mostly_high']['feature']['majority_pct'] == '60'
    assert by_outcome['mostly_high']['feature']['zone_high'] == '70'
    assert by_outcome['mostly_high']['feature']['zone_low'] == '30'
    assert all(d['feature_kind'] == 'boolean' for d in defs)
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('S_majority_share_pct') == '90')
    defs2 = {d['source_outcome']: d for d in bind_master_question(row, changed)}
    assert defs2['mostly_high']['feature']['majority_pct'] == '90'

    row, variant = _q(grid, 'B|overbought_oversold|WilliamsR14|time_in_zone|1x10')
    by_outcome = {d['source_outcome']: d for d in bind_master_question(row, variant)}
    assert by_outcome['mostly_high']['feature']['zone_high'] == '-20'
    assert by_outcome['mostly_high']['feature']['zone_low'] == '-80'


def test_evaluate_cross_count(grid):
    row, variant = _q(grid, 'B|moving_averages|SMA20|cross_count|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 30  # 20 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # four sign flips of close vs MA in the window -> mid_band (3-5)
    closes = [95.0] * 20 + [95.0, 95.0, 105.0, 105.0, 95.0, 95.0, 105.0, 105.0,
                            95.0, 95.0]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['mid_band'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['zero'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['high_band'], bars, setup, last).answer == 'NO'
    # perfectly flat -> no crosses -> zero
    closes = [100.0] * span
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['zero'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['mid_band'], bars, setup, last).answer == 'NO'


def test_evaluate_shock(grid):
    row, variant = _q(grid, 'B|volatility|ATR14|shock|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 260  # 250 baseline + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # quiet baseline (range ~0.3), one huge early window bar (range 10 = ~33x)
    closes = [100.0 + 0.1 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    big = bars[100 + 250]
    bars[100 + 250] = NativeBar(end=big.end, available_from=big.available_from,
                                open=big.open, high=big.open + 5.0,
                                low=big.open - 5.0, close=big.close)
    assert evaluate_master(defs['big_early'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # uniform ranges -> biggest ratio ~1x -> none
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'


def test_evaluate_time_in_zone(grid):
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|time_in_zone|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 17  # 7 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # all window bars strong gains -> RSI 100 throughout -> mostly_high
    closes = [50.0 + 0.1 * i for i in range(7)] + [50.7 + 1.0 * i for i in range(10)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['mostly_high'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['mixed'], bars, setup, last).answer == 'NO'
    # all losses -> RSI 0 -> mostly_low
    closes = [50.0 - 0.1 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['mostly_low'], bars, setup, last).answer == 'YES'
    # alternating small +/- keeps RSI mid (~50) -> mostly_mid
    changes = [1, -1] * 8
    closes = [50.0]
    for ch in changes[:span - 1]:
        closes.append(closes[-1] + 0.1 * ch)
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['mostly_mid'], bars, setup, last).answer == 'YES'


def test_bind_batch8_variants(grid):
    row, variant = _q(grid, 'B|moving_averages|MA_group(10/20/50/200)|full_stack_streak|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 8
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['bull_mid']['feature']['streak_low_edge'] == '4'
    assert by_outcome['bull_mid']['feature']['streak_mid_lo'] == '5'
    assert by_outcome['bull_mid']['feature']['streak_mid_hi'] == '19'
    assert by_outcome['bull_mid']['feature']['streak_high_edge'] == '20'
    assert all(d['feature_kind'] == 'boolean' for d in defs)
    degenerate = next(v for v in grid.variants(row['question_id'])
                      if dict(v.settings).get('C101_full_stack_streak__scalar4') == '3')
    defs2 = {d['source_outcome']: d for d in bind_master_question(row, degenerate)}
    assert defs2['bull_mid']['feature']['streak_low_edge'] == '3'

    row, variant = _q(grid, 'B|moving_averages|MA_group(10/20/50/200)|ma30_side_streak|1x10')
    defs = bind_master_question(row, variant)
    assert len(defs) == 12
    by_outcome = {d['source_outcome']: d for d in defs}
    assert by_outcome['above_long_record']['feature']['streak_short_edge'] == '10'
    assert by_outcome['above_long_record']['feature']['streak_long_edge'] == '30'
    assert by_outcome['above_long_record']['feature']['long_history_bars'] == '500'
    assert all(d['feature_kind'] == 'boolean' for d in defs)
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C107_ma30_side_streak__scalar10') == '5')
    defs3 = {d['source_outcome']: d for d in bind_master_question(row, changed)}
    assert defs3['above_long_record']['feature']['streak_short_edge'] == '5'


def test_evaluate_full_stack_streak(grid):
    row, variant = _q(grid, 'B|moving_averages|MA_group(10/20/50/200)|full_stack_streak|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 210  # 200 MA warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # steady rise: full bull order all window -> run 10 -> bull_mid (5-19)
    closes = [100.0 + 0.5 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['bull_mid'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bull_high'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['bear_zero'], bars, setup, last).answer == 'YES'
    # steady decline: full bear order -> bear_mid
    closes = [200.0 - 0.5 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['bear_mid'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bull_zero'], bars, setup, last).answer == 'YES'
    # flat: no strict ordering anywhere -> both zero
    closes = [100.0] * span
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['bull_zero'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bear_zero'], bars, setup, last).answer == 'YES'
    # degenerate dial pairing (3,5,19,20) -> NOT_EVALUABLE
    degenerate = next(v for v in grid.variants(row['question_id'])
                      if dict(v.settings).get('C101_full_stack_streak__scalar4') == '3')
    defs2 = _by_outcome(bind_master_question(row, degenerate))
    closes = [100.0 + 0.5 * i for i in range(span)]
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs2['bull_mid'], bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_ma30_side_streak(grid):
    row, variant = _q(grid, 'B|moving_averages|MA_group(10/20/50/200)|ma30_side_streak|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 540  # 30 SMA warmup + 500 prior history + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # 500 alternating bars (runs of 1), then 40 rising: current above-run 40
    # -> above_long, and a record vs the prior longest run of 1
    closes = [100.0]
    for i in range(499):
        closes.append(closes[-1] + (0.1 if i % 2 == 0 else -0.1))
    base = closes[-1]
    closes += [base + 0.5 * (i + 1) for i in range(40)]
    assert len(closes) == span
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['above_long_record'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['above_mid_record'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['below_long_not'], bars, setup, last).answer == 'NO'
    # prior history holds a 100-bar run; current run 20 -> above_mid, not record
    closes = [100.0 + 0.5 * i for i in range(100)]
    for i in range(400):
        closes.append(closes[-1] + (0.1 if i % 2 == 0 else -0.1))
    base = closes[-1]
    closes += [base + 0.5 * (i + 1) for i in range(40)]
    assert len(closes) == span
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['above_long_not'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['above_long_record'], bars, setup, last).answer == 'NO'


def test_bind_batch9_variants(grid):
    # osc_swing_speed: five baked dials, eight boolean outcomes
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|osc_swing_speed|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 8
    f = defs['bear_mid']['feature']
    assert (f['zone_high'], f['zone_low'], f['swing_low_edge'], f['swing_mid_lo'],
            f['swing_mid_hi'], f['osc_warmup']) == ('80', '20', '5', '6', '15', '7')
    assert all(d['feature_kind'] == 'boolean' for d in defs.values())
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C228_osc_swing_speed__scalar5') == '7')
    defs2 = _by_outcome(bind_master_question(row, changed))
    assert defs2['bear_short']['feature']['swing_low_edge'] == '7'
    # segment_compare: one L4 name, three (L1,L3) sub-specs
    row, variant = _q(grid, 'B|volume|RVOL20|segment_compare|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert defs['rally_heavier']['feature']['recipe'] == 'native_segment_volume_compare_v1'
    assert defs['rally_heavier']['comparator'] == '>'
    assert defs['rally_heavier']['comparison_threshold'] == '1.25'
    assert defs['decline_heavier']['comparison_threshold'] == '0.8'
    assert defs['similar']['feature']['transform'] == 'mirror_min'
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('S_ratio_band_1p25') == '2.5')
    defs2 = _by_outcome(bind_master_question(row, changed))
    assert defs2['rally_heavier']['comparison_threshold'] == '2.5'
    assert defs2['decline_heavier']['comparison_threshold'] == '0.4'
    row, variant = _q(grid, 'B|return_path|daily_returns|segment_compare|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert defs['rally_steeper']['feature']['recipe'] == 'native_segment_return_compare_v1'
    assert defs['rally_steeper']['comparison_threshold'] == '1.5'
    row, variant = _q(grid, 'B|volatility|ATR14|segment_compare|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert defs['expanded']['feature']['recipe'] == 'native_segment_atr_compare_v1'
    assert defs['expanded']['comparison_threshold'] == '20'
    assert defs['contracted']['comparison_threshold'] == '-20'
    assert defs['similar']['feature']['transform'] == 'abs'
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C244_segment_compare__pct20') == '40')
    assert _by_outcome(bind_master_question(row, changed))['expanded']['comparison_threshold'] == '40'


def _closes_from_changes(start, changes):
    closes = [float(start)]
    for d in changes:
        closes.append(closes[-1] + d)
    return closes


def test_evaluate_osc_swing_speed(grid):
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|osc_swing_speed|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 17  # 7 RSI6 warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # 9 up (+3, RSI 100 through window bar 2) then 7 down (-5): RSI hits
    # 18.8 at the last window bar -> bear swing length 7 (start idx 2, end
    # idx 9) -> bear_mid; no bull swing -> bull_none
    closes = _closes_from_changes(100, [3] * 9 + [-5] * 7)
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['bear_mid'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bear_short'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['bear_long'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['bear_none'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['bull_none'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bull_mid'], bars, setup, last).answer == 'NO'
    # mirror: 9 down then 7 up -> RSI 0 then 81.1 at the last bar -> bull
    # swing length 7 -> bull_mid; no bear swing -> bear_none
    closes = _closes_from_changes(160, [-3] * 9 + [5] * 7)
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['bull_mid'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bear_none'], bars, setup, last).answer == 'YES'
    # sharp 3-bar drop to RSI 18.6 then recovery above 20: latest (only)
    # low-zone touch ends the swing at idx 5, start idx 2 -> length 3 -> short
    closes = _closes_from_changes(100, [3] * 9 + [-18] * 3 + [1] * 4)
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs['bear_short'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bear_mid'], bars, setup, last).answer == 'NO'
    # dial variant C230=5: the 7-bar swing of case 1 exceeds the 5-bar mid
    # edge -> bear_long
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C230_osc_swing_speed__scalar15') == '5')
    defs2 = _by_outcome(bind_master_question(row, changed))
    closes = _closes_from_changes(100, [3] * 9 + [-5] * 7)
    bars = _bars_from_closes(closes)
    assert evaluate_master(defs2['bear_long'], bars, setup, last).answer == 'YES'
    # non-contiguous pairing (C228=5, C229=4) -> NOT_EVALUABLE
    degenerate = next(v for v in grid.variants(row['question_id'])
                      if dict(v.settings).get('C229_osc_swing_speed__scalar6') == '4')
    defs3 = _by_outcome(bind_master_question(row, degenerate))
    for d in defs3.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_segment_volume_compare(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|segment_compare|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    setup = date(2024, 3, 12)
    last = 109
    closes = [12, 11, 10, 9, 8, 9, 10, 11, 12, 13]
    # pivot = idx 4 (close 8). Rally leg mean 350 vs decline leg mean 100
    # -> ratio 3.5 -> rally_heavier
    spec = [(c, c * 1.01, c * 0.99, c, 100 if i < 5 else 400)
            for i, c in enumerate(closes)]
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['rally_heavier'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['decline_heavier'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['similar'], bars, setup, last).answer == 'NO'
    # mirror: rally mean 150 vs decline mean 400 -> ratio 0.375
    spec = [(c, c * 1.01, c * 0.99, c, 400 if i < 5 else 100)
            for i, c in enumerate(closes)]
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['decline_heavier'], bars, setup, last).answer == 'YES'
    # equal legs -> ratio 1 -> similar
    spec = [(c, c * 1.01, c * 0.99, c, 200) for c in closes]
    bars = _bars_hlv(spec)
    assert evaluate_master(defs['similar'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['rally_heavier'], bars, setup, last).answer == 'NO'
    # bars without volume -> NOT_EVALUABLE
    bars = _bars_hl([(c, c * 1.01, c * 0.99, c) for c in closes])
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_segment_return_compare(grid):
    row, variant = _q(grid, 'B|return_path|daily_returns|segment_compare|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 10
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # decline 0.5 (12->8), rally 0.625 (8->13) -> ratio 1.25 vs 1.5 band ->
    # similar
    bars = _bars_from_closes([12, 11, 10, 9, 8, 9, 10, 11, 12, 13])
    assert evaluate_master(defs['similar'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['rally_steeper'], bars, setup, last).answer == 'NO'
    # rally 1.5 (6->15) vs decline 0.667 (10->6) -> ratio 2.25 -> rally_steeper
    bars = _bars_from_closes([10, 9, 8, 7, 6, 7, 9, 11, 13, 15])
    assert evaluate_master(defs['rally_steeper'], bars, setup, last).answer == 'YES'
    # window starts at the low: decline magnitude 0, rally 1.125 -> KNOWN
    # infinity -> rally_steeper
    bars = _bars_from_closes([8, 9, 10, 11, 12, 13, 14, 15, 16, 17])
    assert evaluate_master(defs['rally_steeper'], bars, setup, last).answer == 'YES'
    # perfectly flat window -> 0/0 -> NOT_EVALUABLE
    bars = _bars_from_closes([10.0] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_segment_atr_compare(grid):
    row, variant = _q(grid, 'B|volatility|ATR14|segment_compare|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 24  # 14 ATR warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    closes = [12.0] * 14 + [12, 11, 10, 9, 8, 9, 10, 11, 12, 13]
    # uniform ranges -> near-zero signed change -> similar
    spec = [(c, c + 2.0, c - 2.0, c) for c in closes]
    bars = _bars_hl(spec)
    assert evaluate_master(defs['similar'], bars, setup, last).answer == 'YES'
    # all-zero ranges (doji at one price) -> 0/0 -> NOT_EVALUABLE
    bars = _bars_hl([(12.0, 12.0, 12.0, 12.0)] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'
    # strong expansion/contraction need a long rally leg: ATR14 lags 14 bars,
    # so a 6-bar rally still carries the decline-era ranges. Use 1x60.
    row, variant = _q(grid, 'B|volatility|ATR14|segment_compare|1x60')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 74  # 14 ATR warmup + 60 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    decline = [12 - 0.5 * (i + 1) for i in range(12)]          # 12 -> 6
    rally = [6 + 0.25 * (i + 1) for i in range(48)]            # 6 -> 18
    closes = [12.0] * 14 + decline + rally
    pivot = 14 + 11                                            # first lowest close
    assert closes[pivot] == 6.0 and closes[pivot - 1] == 6.5
    # decline leg big ranges, rally leg tiny -> contraction
    spec = [(c, c + (0.05 if i >= pivot else 5.0),
             c - (0.05 if i >= pivot else 5.0), c)
            for i, c in enumerate(closes)]
    bars = _bars_hl(spec)
    assert evaluate_master(defs['contracted'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['expanded'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['similar'], bars, setup, last).answer == 'NO'
    # mirror: tiny ranges into the pivot, big after -> expansion
    spec = [(c, c + (5.0 if i >= pivot else 0.05),
             c - (5.0 if i >= pivot else 0.05), c)
            for i, c in enumerate(closes)]
    bars = _bars_hl(spec)
    assert evaluate_master(defs['expanded'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['contracted'], bars, setup, last).answer == 'NO'


def test_bind_batch10_variants(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|absorption_day|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 7          # 2 directions x 3 age bands + none
    f = defs['after_decline_ageR']['feature']
    assert (f['spike_mult'], f['atr_frac'], f['dir_lookback'],
            f['age_recent'], f['age_old']) == ('3', '0.5', '6', '5', '20')
    assert all(d['feature_kind'] == 'boolean' for d in defs.values())
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C041_absorption_day__scalar6') == '12')
    defs2 = _by_outcome(bind_master_question(row, changed))
    assert defs2['after_rise_ageM']['feature']['dir_lookback'] == '12'
    row, variant = _q(grid, 'B|extremes|drawdown|capitulation_bar|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 73         # 2x3x2x2x3 combos + none
    f = defs['capitulation_ageM_sizeL_recY_end']['feature']
    assert (f['spike_mult'], f['shock_atr'], f['close_pct'], f['big_atr'],
            f['age_recent'], f['age_old']) == ('3', '3', '20', '5', '5', '20')
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('C160_capitulation_bar__atr5') == '10')
    defs2 = _by_outcome(bind_master_question(row, changed))
    assert defs2['capitulation_ageM_sizeL_recY_end']['feature']['big_atr'] == '10'


def _abs_cap_bars(window):
    """49 flat warmup bars (close 100, vol 100, range 0.4) + 10 window bars."""
    spec = [(100.0, 100.2, 99.8, 100.0, 100.0)] * 49
    return spec + window


def test_evaluate_absorption_day(grid):
    row, variant = _q(grid, 'B|volume|RVOL20|absorption_day|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 59  # 49 median warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # window idx 3: vol 500 vs median 100, tiny move (106 -> 106.05) vs
    # ATR~0.66; lookback close (idx -6 -> warmup 100) below -> after_rise;
    # age 6 -> ageM
    window = [(106.0, 106.2, 105.8, 106.0, 100.0)] * 3
    window.append((108.0, 108.0, 104.0, 106.05, 500.0))
    window += [(105.0, 105.2, 104.8, 105.0, 100.0)] * 6
    bars = _bars_hlv(_abs_cap_bars(window))
    assert evaluate_master(defs['after_rise_ageM'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['after_decline_ageM'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # decline into the day instead: lookback close 100 vs day close 94.05
    window = [(94.0, 94.2, 93.8, 94.0, 100.0)] * 3
    window.append((96.0, 96.0, 92.0, 94.05, 500.0))
    window += [(95.0, 95.2, 94.8, 95.0, 100.0)] * 6
    bars = _bars_hlv(_abs_cap_bars(window))
    assert evaluate_master(defs['after_decline_ageM'], bars, setup, last).answer == 'YES'
    # no spike volume day -> none
    bars = _bars_hlv(_abs_cap_bars([(100.0, 100.2, 99.8, 100.0, 100.0)] * 10))
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'
    # bars without volume -> NOT_EVALUABLE
    bars = _bars_hl([(100.0, 100.2, 99.8, 100.0)] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_capitulation_bar(grid):
    row, variant = _q(grid, 'B|extremes|drawdown|capitulation_bar|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 59
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    quiet = (100.0, 100.2, 99.8, 100.0, 100.0)
    # idx 2: range 6 > 3*ATR(~0.8), vol 600 vs median 100, close 0.1 from the
    # low, open at the high -> capitulation, age 7 -> M, 6/0.8 -> sizeL,
    # record vol, close_near_far_end (loc 0.1 <= pct/2)
    window = [quiet, quiet, (103.0, 103.0, 97.0, 97.6, 600.0)] + [quiet] * 7
    bars = _bars_hlv(_abs_cap_bars(window))
    assert evaluate_master(defs['capitulation_ageM_sizeL_recY_end'],
                           bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['capitulation_ageM_sizeS_recY_end'],
                           bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['blowoff_ageM_sizeL_recY_end'],
                           bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # long reversal wick: close at loc 1/6 (in the zone, not extreme),
    # open 0.4 away -> body 0.4, lower wick 1.0 >= 2x body and >= 0.5*ATR
    window = [quiet, quiet, (98.4, 103.0, 97.0, 98.0, 600.0)] + [quiet] * 7
    bars = _bars_hlv(_abs_cap_bars(window))
    assert evaluate_master(defs['capitulation_ageM_sizeL_recY_wk'],
                           bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['capitulation_ageM_sizeL_recY_end'],
                           bars, setup, last).answer == 'NO'
    # close in the qualifying zone but not extreme, no long wick -> mid
    window = [quiet, quiet, (102.0, 103.0, 97.0, 98.1, 600.0)] + [quiet] * 7
    bars = _bars_hlv(_abs_cap_bars(window))
    assert evaluate_master(defs['capitulation_ageM_sizeL_recY_mid'],
                           bars, setup, last).answer == 'YES'
    # mirror blow-off near the high, recent (age 1 -> R)
    window = [quiet] * 8 + [quiet, (97.0, 103.0, 97.0, 102.4, 600.0)]
    bars = _bars_hlv(_abs_cap_bars(window))
    assert evaluate_master(defs['blowoff_ageR_sizeL_recY_end'],
                           bars, setup, last).answer == 'YES'
    # quiet window -> none
    bars = _bars_hlv(_abs_cap_bars([quiet] * 10))
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'
    # bars without volume -> NOT_EVALUABLE
    bars = _bars_hl([(100.0, 100.2, 99.8, 100.0)] * span)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'


def test_bind_batch11_variants(grid):
    row, variant = _q(grid, 'B|extremes|new_highs_lows|hl_base_breakout|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 13         # up/down x lt5/b5_20/gt20 x extreme/not (12) + none
    f = defs['up_lt5_extreme']['feature']
    assert (f['pivot_k_min'], f['pivot_k_divisor'], f['age_recent'],
            f['age_old'], f['rsi_high'], f['rsi_low']) == ('2', '10', '5', '20', '70', '30')
    assert all(d['feature_kind'] == 'boolean' for d in defs.values())
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings).get('S_rsi_extreme_high') == '80')
    defs2 = _by_outcome(bind_master_question(row, changed))
    assert defs2['up_lt5_extreme']['feature']['rsi_high'] == '80'


def _hl_warm_rising(start=100.0, step=1.0):
    return [(start + i * step, start + i * step + 0.5, start + i * step - 0.5,
             start + i * step, 100.0) for i in range(30)]


def _hl_warm_osc(start):
    out, p = [], float(start)
    for i in range(30):
        p += 0.5 if i % 2 else -0.5
        out.append((p, p + 0.4, p - 0.4, p, 100.0))
    return out


# 10-bar windows: pivot lows (highs) at idx 2 and 5, first breakout bar idx 6
# (dist 1 -> lt5).  "not" windows keep the warmup level adjacent to the window
# so the breakout day is not itself an overbought/oversold day; "extreme"
# windows gap away from a trending warmup, which is what pushes RSI6/12/24
# all past 70 (below 30 for the mirror).
_HL_WIN_UP = [(131.2, 131.6, 130.7, 131.0, 100.0), (131.0, 131.2, 130.0, 130.3, 100.0),
              (130.3, 130.5, 129.3, 129.9, 100.0), (129.9, 130.9, 129.8, 130.6, 100.0),
              (130.6, 130.8, 130.1, 130.4, 100.0), (130.4, 130.6, 129.6, 130.2, 100.0),
              (130.2, 134.5, 130.0, 134.0, 100.0), (134.0, 136.5, 133.8, 136.0, 100.0),
              (136.0, 138.4, 135.8, 138.0, 100.0), (138.0, 141.0, 137.8, 140.5, 100.0)]
_HL_WIN_DOWN = [(128.8, 129.3, 128.4, 129.0, 100.0), (129.0, 130.0, 128.8, 129.7, 100.0),
                (129.7, 130.7, 129.5, 130.1, 100.0), (130.1, 130.2, 129.1, 129.4, 100.0),
                (129.4, 129.9, 128.6, 129.6, 100.0), (129.6, 130.4, 129.2, 129.8, 100.0),
                (129.8, 130.0, 125.5, 126.0, 100.0), (126.0, 126.3, 123.8, 124.2, 100.0),
                (124.2, 124.5, 121.8, 122.2, 100.0), (122.2, 122.5, 119.8, 120.2, 100.0)]
_HL_WIN_UP_NOT = [(128.6, 129.0, 128.5, 128.8, 100.0), (128.4, 128.9, 128.2, 128.4, 100.0),
                  (128.2, 128.5, 127.9, 128.1, 100.0), (128.9, 129.0, 128.3, 128.8, 100.0),
                  (129.0, 129.0, 128.6, 128.9, 100.0), (128.9, 129.0, 128.2, 128.7, 100.0),
                  (129.0, 129.1, 128.9, 129.1, 100.0), (129.4, 129.6, 129.2, 129.5, 100.0),
                  (129.5, 129.8, 129.4, 129.6, 100.0), (129.6, 129.9, 129.5, 129.7, 100.0)]
_HL_WIN_DOWN_NOT = [(129.3, 129.6, 129.0, 129.2, 100.0), (128.9, 129.7, 128.6, 128.8, 100.0),
                    (128.7, 130.0, 128.3, 128.5, 100.0), (128.8, 129.4, 128.6, 128.9, 100.0),
                    (128.9, 129.3, 128.7, 129.0, 100.0), (128.8, 129.5, 128.5, 128.8, 100.0),
                    (128.7, 129.1, 128.0, 128.2, 100.0), (128.2, 129.0, 127.9, 127.9, 100.0),
                    (127.8, 128.4, 127.7, 127.8, 100.0), (127.7, 128.2, 127.6, 127.7, 100.0)]


def _hl_win_band():
    """20-bar window, pivot lows (2, 5), first breakout bar idx 11
    (dist 6 -> b5_20).  Warmup level matches the window so the breakout
    day is not an RSI-extreme day."""
    closes = [128.8, 128.4, 128.1, 128.6, 128.8, 128.4, 128.5, 128.6, 128.5,
              128.6, 128.7, 129.0, 129.1, 129.2, 129.3, 129.4, 129.5, 129.6,
              129.7, 129.8]
    lows = [128.5, 128.2, 127.9, 128.3, 128.6, 128.2, 128.3, 128.4, 128.3,
            128.4, 128.5, 128.8, 128.9, 129.0, 129.1, 129.2, 129.3, 129.4,
            129.5, 129.6]
    return [(c - 0.05, c + 0.05, lows[i], c, 100.0) for i, c in enumerate(closes)]


def test_evaluate_hl_base_breakout(grid):
    row, variant = _q(grid, 'B|extremes|new_highs_lows|hl_base_breakout|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 40  # 30 RSI warmup + 10 window
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # up: rising warmup, HL base at idx 2/5 (129.3 -> 129.6), breakout idx 6
    # closes 134.0 above every earlier window high; trending RSI all > 70
    bars = _bars_hlv(_hl_warm_rising() + _HL_WIN_UP)
    assert evaluate_master(defs['up_lt5_extreme'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up_lt5_not'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['down_lt5_extreme'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'NO'
    # down mirror: falling warmup, lower-high top at idx 2/5, breakdown idx 6
    bars = _bars_hlv(_hl_warm_rising(160.0, -1.0) + _HL_WIN_DOWN)
    assert evaluate_master(defs['down_lt5_extreme'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up_lt5_extreme'], bars, setup, last).answer == 'NO'
    # not-extreme: warmup level adjacent to window, small breakout day move
    bars = _bars_hlv(_hl_warm_osc(128.5) + _HL_WIN_UP_NOT)
    assert evaluate_master(defs['up_lt5_not'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up_lt5_extreme'], bars, setup, last).answer == 'NO'
    bars = _bars_hlv(_hl_warm_osc(129.5) + _HL_WIN_DOWN_NOT)
    assert evaluate_master(defs['down_lt5_not'], bars, setup, last).answer == 'YES'
    # monotonically rising window: no pivot pair, no breakout -> none
    mono = [(131.0 + i, 131.5 + i, 130.5 + i, 131.5 + i, 100.0) for i in range(10)]
    bars = _bars_hlv(_hl_warm_rising() + mono)
    assert evaluate_master(defs['none'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up_lt5_extreme'], bars, setup, last).answer == 'NO'
    # all-flat warmup: RSI seeding window is 0/0 -> NOT_EVALUABLE, never NO
    flat = [(100.0, 100.5, 99.5, 100.0, 100.0)] * 30
    bars = _bars_hlv(flat + _HL_WIN_UP)
    for d in defs.values():
        assert evaluate_master(d, bars, setup, last).answer == 'NOT_EVALUABLE'
    # b5_20 band: 20-bar window, breakout 6 bars after the second pivot low
    row20, variant20 = _q(grid, 'B|extremes|new_highs_lows|hl_base_breakout|1x20')
    defs20 = _by_outcome(bind_master_question(row20, variant20))
    span20 = 50  # 30 RSI warmup + 20 window
    setup20 = date(2024, 3, 1) + timedelta(days=span20 + 1)
    last20 = 100 + span20 - 1
    bars = _bars_hlv(_hl_warm_osc(128.5) + _hl_win_band())
    assert evaluate_master(defs20['up_b5_20_not'], bars, setup20, last20).answer == 'YES'
    assert evaluate_master(defs20['up_lt5_not'], bars, setup20, last20).answer == 'NO'
    assert evaluate_master(defs20['up_gt20_not'], bars, setup20, last20).answer == 'NO'
    assert evaluate_master(defs20['none'], bars, setup20, last20).answer == 'NO'


def test_bind_batch12_variants(grid):
    row, variant = _q(grid, 'B|extremes|new_highs_lows|high_then_low|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 2          # {high_first,low_first}; the family has no dials
    assert all(d['feature_kind'] == 'boolean' for d in defs.values())
    assert all(d['comparison_threshold'] == '1' for d in defs.values())


def test_evaluate_high_then_low(grid):
    row, variant = _q(grid, 'B|extremes|new_highs_lows|high_then_low|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 10  # window only; the recipe needs no warmup or prior candle
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    # peak at idx 4 (window high 104.6), trough at idx 9 (window low 99.0)
    win_hf = [(100.0, 100.6, 99.6, 100.2), (101.0, 101.6, 100.6, 101.2),
              (102.0, 102.6, 101.6, 102.2), (103.0, 103.6, 102.6, 103.2),
              (104.0, 104.6, 103.6, 104.2), (103.8, 104.2, 103.0, 103.2),
              (103.0, 103.4, 102.2, 102.4), (102.2, 102.6, 101.4, 101.6),
              (101.4, 101.8, 100.6, 100.8), (100.6, 101.0, 99.0, 99.4)]
    bars = _bars_hl(win_hf)
    assert evaluate_master(defs['high_first'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['low_first'], bars, setup, last).answer == 'NO'
    # trough at idx 4 (window low 95.0), peak at idx 9 (window high 105.0)
    win_lf = [(100.0, 100.4, 99.4, 99.8), (99.0, 99.4, 98.4, 98.8),
              (98.0, 98.4, 97.4, 97.8), (97.0, 97.4, 96.4, 96.8),
              (96.0, 96.4, 95.0, 95.4), (96.2, 97.0, 96.0, 96.6),
              (97.0, 97.8, 96.8, 97.4), (98.0, 98.8, 97.8, 98.4),
              (99.0, 99.8, 98.8, 99.4), (100.0, 105.0, 99.8, 104.6)]
    bars = _bars_hl(win_lf)
    assert evaluate_master(defs['low_first'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['high_first'], bars, setup, last).answer == 'NO'
    # tie: idx 5 is simultaneously the window max high (105.0) and the window
    # min low (95.0) -> documented same_bar rule: counts as high_first
    quiet = (100.0, 100.5, 99.5, 100.0)
    win_tie = [quiet] * 5 + [(99.0, 105.0, 95.0, 96.0)] + [quiet] * 4
    bars = _bars_hl(win_tie)
    assert evaluate_master(defs['high_first'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['low_first'], bars, setup, last).answer == 'NO'
    # missing window -> NOT_EVALUABLE
    for d in defs.values():
        assert evaluate_master(d, {}, setup, last).answer == 'NOT_EVALUABLE'


def test_bind_batch13_variants(grid):
    row, variant = _q(grid, 'B|candles|OHLC|intraday_change|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 3          # {up,down,flat} on the C001 percent band
    assert defs['up']['comparison_threshold'] == '1'
    assert defs['down']['comparison_threshold'] == '-1'
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings)['C001_intraday_change__pct1'] != '1')
    defs2 = _by_outcome(bind_master_question(row, changed))
    v2 = dict(changed.settings)['C001_intraday_change__pct1']
    assert defs2['up']['comparison_threshold'] != '1'
    assert defs2['flat']['comparison_threshold'] == defs2['up']['comparison_threshold']
    row, variant = _q(grid, 'B|candles|OHLC|interday_change|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 3
    assert defs['up']['comparison_threshold'] == '5'
    row, variant = _q(grid, 'B|candles|OHLC|run_structure|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 3
    assert all(d['feature_kind'] == 'boolean' for d in defs.values())


_GREEN = (100.0, 100.6, 99.8, 100.4)
_RED = (100.4, 100.6, 99.8, 100.0)
_DOJI = (100.0, 100.2, 99.8, 100.0)


def test_evaluate_run_structure(grid):
    row, variant = _q(grid, 'B|candles|OHLC|run_structure|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    span = 10
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    bars = _bars_hl([_GREEN] * 6 + [_RED] * 4)
    assert evaluate_master(defs['green_longer'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['red_longer'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['equal'], bars, setup, last).answer == 'NO'
    bars = _bars_hl([_RED] * 6 + [_GREEN] * 4)
    assert evaluate_master(defs['red_longer'], bars, setup, last).answer == 'YES'
    # alternating single bars -> both longest runs length 1 -> equal
    bars = _bars_hl([_GREEN, _RED] * 5)
    assert evaluate_master(defs['equal'], bars, setup, last).answer == 'YES'
    # doji breaks runs; 2-runs on both sides -> equal
    bars = _bars_hl([_GREEN, _GREEN, _DOJI, _RED, _RED, _DOJI,
                     _GREEN, _GREEN, _RED, _RED])
    assert evaluate_master(defs['equal'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['green_longer'], bars, setup, last).answer == 'NO'
    for d in defs.values():
        assert evaluate_master(d, {}, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_intraday_interday_change(grid):
    span = 10
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    row, variant = _q(grid, 'B|candles|OHLC|intraday_change|1x10')
    defs = _by_outcome(bind_master_question(row, variant))  # C001 = 1 (%)
    up2 = (100.0, 102.0, 99.8, 102.0)
    dn2 = (100.0, 100.2, 97.8, 98.0)
    up_half = (100.0, 100.7, 99.8, 100.5)
    bars = _bars_hl([up2] * 10)
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'NO'
    bars = _bars_hl([dn2] * 10)
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'YES'
    bars = _bars_hl([up_half] * 10)
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'NO'
    for d in defs.values():
        assert evaluate_master(d, {}, setup, last).answer == 'NOT_EVALUABLE'
    row, variant = _q(grid, 'B|candles|OHLC|interday_change|1x10')
    defs = _by_outcome(bind_master_question(row, variant))  # C002 = 5 (%)
    rising = [(100.0 + i, 100.9 + i, 99.5 + i, 100.8 + i) for i in range(10)]
    bars = _bars_hl(rising)   # first close 100.8 -> last 109.8: ~+8.9%
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'NO'
    drifting = [(100.0 + 0.3 * i, 100.9 + 0.3 * i, 99.5 + 0.3 * i,
                 100.6 + 0.3 * i) for i in range(10)]  # ~+2.7% -> flat
    bars = _bars_hl(drifting)
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['up'], bars, setup, last).answer == 'NO'
    falling = [(109.0 - i, 109.9 - i, 107.5 - i, 108.0 - i) for i in range(10)]
    bars = _bars_hl(falling)  # ~-8.3%
    assert evaluate_master(defs['down'], bars, setup, last).answer == 'YES'


def test_bind_batch14_variants(grid):
    row, variant = _q(grid, 'B|extremes|big_picture|weekly_trend|5x20')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 3          # {rising,falling,flat}, no dial
    assert all(d['feature_kind'] == 'boolean' for d in defs.values())
    row, variant = _q(grid, 'B|extremes|big_picture|weekly_stack|5x20')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 3          # {bull,bear,mixed}
    # baked C174/C175 periods enter the feature identity and re-hash it
    assert defs['bull']['feature']['ma_fast'] == '10'
    assert defs['bull']['feature']['ma_slow'] == '40'
    changed = next(v for v in grid.variants(row['question_id'])
                   if dict(v.settings)['C175_weekly_stack__scalar40'] != '40')
    defs2 = _by_outcome(bind_master_question(row, changed))
    slow2 = dict(changed.settings)['C175_weekly_stack__scalar40']
    assert defs2['bull']['feature']['ma_slow'] == slow2
    assert defs2['bull']['feature_id'] != defs['bull']['feature_id']
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|extreme_position|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    assert len(defs) == 4


def test_evaluate_weekly_trend_and_stack(grid):
    span = 100                       # 20 bars x 5 sessions
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    row, variant = _q(grid, 'B|extremes|big_picture|weekly_trend|5x20')
    defs = _by_outcome(bind_master_question(row, variant))
    rising = [(100.0 + 2.0 * i, 101.5 + 2.0 * i, 99.0 + 2.0 * i,
               101.0 + 2.0 * i) for i in range(span)]     # +40% over window
    bars = _bars_hl(rising)
    assert evaluate_master(defs['rising'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['falling'], bars, setup, last).answer == 'NO'
    falling = [(300.0 - 2.0 * i, 301.5 - 2.0 * i, 297.0 - 2.0 * i,
                299.0 - 2.0 * i) for i in range(span)]   # -40%
    bars = _bars_hl(falling)
    assert evaluate_master(defs['falling'], bars, setup, last).answer == 'YES'
    drifting = [(100.0 + 0.01 * i, 101.5 + 0.01 * i, 99.0 + 0.01 * i,
                 101.0 + 0.01 * i) for i in range(span)]  # ~+1.0% total -> flat
    bars = _bars_hl(drifting)
    assert evaluate_master(defs['flat'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['rising'], bars, setup, last).answer == 'NO'
    for d in defs.values():
        assert evaluate_master(d, {}, setup, last).answer == 'NOT_EVALUABLE'
    # weekly_stack: needs lookback(20) + ma_slow(40) k-day bars = 300 sessions
    span = 300
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1
    row, variant = _q(grid, 'B|extremes|big_picture|weekly_stack|5x20')
    defs = _by_outcome(bind_master_question(row, variant))
    up = [(100.0 + 0.5 * i, 101.5 + 0.5 * i, 99.0 + 0.5 * i,
           100.5 + 0.5 * i) for i in range(span)]
    bars = _bars_hl(up)          # strict rise: close > SMA10 > SMA40
    assert evaluate_master(defs['bull'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bear'], bars, setup, last).answer == 'NO'
    assert evaluate_master(defs['mixed'], bars, setup, last).answer == 'NO'
    down = [(400.0 - 0.5 * i, 401.5 - 0.5 * i, 396.0 - 0.5 * i,
             397.0 - 0.5 * i) for i in range(span)]
    bars = _bars_hl(down)        # strict fall: close < SMA10 < SMA40
    assert evaluate_master(defs['bear'], bars, setup, last).answer == 'YES'
    flat = [(100.0, 101.5, 99.0, 100.5)] * span   # close == SMA10 == SMA40
    bars = _bars_hl(flat)
    assert evaluate_master(defs['mixed'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['bull'], bars, setup, last).answer == 'NO'
    for d in defs.values():
        assert evaluate_master(d, {}, setup, last).answer == 'NOT_EVALUABLE'


def test_evaluate_extreme_position(grid):
    row, variant = _q(grid, 'B|overbought_oversold|RSI6|extreme_position|1x10')
    defs = _by_outcome(bind_master_question(row, variant))
    # warmup 7 prior bars + 10 window bars; half = index 5. The 7 warmup
    # changes alternate +/-0.1 so the Wilder RSI seed is defined (never 0/0).
    seed = [0.1, -0.1, 0.1, -0.1, 0.1, -0.1]
    span = 17
    setup = date(2024, 3, 1) + timedelta(days=span + 1)
    last = 100 + span - 1

    def bars_for(window_changes):
        closes = [100.0]
        for ch in seed + window_changes:
            closes.append(closes[-1] + ch)
        return _bars_hl([(c, c + 1.5, c - 1.0, c) for c in closes])

    up5 = [2.0] * 5
    dn5 = [-2.0] * 5
    bars = bars_for(up5 + dn5)          # RSI max early (idx 4), min late (idx 9)
    assert evaluate_master(defs['max_early_min_late'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['min_early_max_late'], bars, setup, last).answer == 'NO'
    bars = bars_for(dn5 + up5)          # mirrored
    assert evaluate_master(defs['min_early_max_late'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['max_early_min_late'], bars, setup, last).answer == 'NO'
    bars = bars_for([2.0] * 3 + [-1.0] * 2 + [0.2] * 5)
    assert evaluate_master(defs['both_early'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['both_late'], bars, setup, last).answer == 'NO'
    bars = bars_for([0.1, -0.1, 0.1, -0.1, 0.1, 3.0, 3.0, -3.0, -3.0, 0.5])
    assert evaluate_master(defs['both_late'], bars, setup, last).answer == 'YES'
    assert evaluate_master(defs['both_early'], bars, setup, last).answer == 'NO'
    for d in defs.values():
        assert evaluate_master(d, {}, setup, last).answer == 'NOT_EVALUABLE'


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
    for name in ('world_binary_price.py','world_binary_questions.py'):
        assert report1['code_fingerprints'][name] == hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    assert report1['bound_unique_binary_definitions'] > 633  # GPT 633 + batch-1 facets
    with csv_path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == report1['master_total_rows']
    bound = [r for r in rows if r['definition_status'] == 'BOUND']
    assert {r['facet'] for r in bound} >= set(FACETS)
    assert {r['facet'] for r in bound} <= set(FACETS) | {
        'intraday_change', 'interday_change', 'run_structure'}
    features={}
    for r in bound:
        literal_threshold(r['comparison_threshold'])
        assert r['question_id'].startswith('BM1-')
        assert r['feature_id'].startswith('BF1-')
        signature=tuple(r[k] for k in ('feature_json','feature_expression','feature_kind','feature_unit'))
        assert features.setdefault(r['feature_id'],signature)==signature
        assert r['knowable_at_setup_open']
        assert r['not_evaluable_condition']
    assert report1['unbound_oat_variants'] > 0
    assert (tmp_path / 'docs' / REPORT).exists()


def test_scalar_feature_ids_distinguish_components_of_one_native_recipe(grid):
    qid='B|candles|OHLC|inside_outside|1x3'
    definitions=bind_master_question(grid.tree[qid],next(grid.variants(qid)))
    assert {q['source_outcome'] for q in definitions}=={
        'inside_cluster_ge','outside_after_inside','mostly_outside','none'}
    assert len({q['feature_id'] for q in definitions})==4
    assert {q['feature_kind'] for q in definitions}=={'integer_count','boolean'}
