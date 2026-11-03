"""Strict SEC event definitions: PIT boundary, direction mapping, NE rules."""
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from world_sec_events import (count_in_window, days_since_last, event_direction,
                              insider_cluster, max_trade_dollars, net_dollars,
                              usable_events)
from world_question_grid import ROOT, identity
from ci.binary_master_build import CSV_COLUMNS
from ci import sec_options_master

D = date(2026, 6, 10)


def _sessions(n=80, end=D):
    days = []
    cur = end - timedelta(days=140)
    while len(days) < n or cur < end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return [s for s in days if s < end][-n:]


def _ev(session, public_dt, action='P', dollars=1000.0, insider='i1', source='form4'):
    return dict(session=session, public_dt=public_dt, action=action,
                dollars=dollars, insider_id=insider, source=source)


def _public(session, hour=18):
    """Same-day evening acceptance (public before next open)."""
    return datetime.combine(session, datetime.min.time()) + timedelta(hours=hour)


def test_c29_public_timestamp_strictly_before_d_0930_et():
    sessions = _sessions()
    t0 = sessions[-3]
    on_time = [_ev(t0, _public(t0))]
    # accepted D 08:00 ET is before the open: knowable at D, usable per C29
    pre_open = [_ev(D, datetime.combine(D, datetime.min.time()) + timedelta(hours=8))]
    # accepted D 10:00 ET is after the open: invisible at D (day-D information)
    late = [_ev(D, datetime.combine(D, datetime.min.time()) + timedelta(hours=10))]
    assert len(usable_events(on_time, D)) == 1
    assert len(usable_events(pre_open, D)) == 1
    assert usable_events(late, D) == []
    assert usable_events(on_time + late, D) == on_time


def test_event_exactly_at_cutoff_is_excluded():
    sessions = _sessions()
    edge = [_ev(D, datetime.combine(D, datetime.min.time()) + timedelta(hours=9, minutes=30))]
    assert usable_events(edge, D) == []
    just_before = [_ev(D - timedelta(days=1),
                       datetime.combine(D - timedelta(days=1), datetime.min.time())
                       + timedelta(hours=23, minutes=59))]
    assert len(usable_events(just_before, D)) == 1


def test_direction_mapping_table():
    assert event_direction('form4', 'P') == 'bullish'
    assert event_direction('form4', 'S') == 'bearish'
    assert event_direction('form4', 'A') is None
    assert event_direction('form4', 'M') is None
    assert event_direction('analyst', 'upgrade') == 'bullish'
    assert event_direction('analyst', 'downgrade') == 'bearish'
    assert event_direction('analyst', 'reiterate') is None


def test_days_since_last_ne_before_any_usable_event():
    sessions = _sessions()
    assert days_since_last([], sessions, D, source='form4', direction='bullish') is None
    future = [_ev(D + timedelta(days=1), _public(D + timedelta(days=1)))]
    assert days_since_last(future, sessions, D, source='form4') is None


def test_days_since_last_counts_sessions_after_event_day():
    sessions = _sessions()
    t0 = sessions[-6]
    events = [_ev(t0, _public(t0))]
    got = days_since_last(events, sessions, D, source='form4', direction='bullish')
    assert got == sum(1 for s in sessions if t0 < s < D) == 5


def test_count_in_window_zero_is_evaluable_and_pit():
    sessions = _sessions()
    assert count_in_window([], sessions, D, 20, source='form4', direction='bullish') == 0
    t_old = sessions[-30]
    t_new = sessions[-2]
    events = [_ev(t_old, _public(t_old), action='P'),
              _ev(t_new, _public(t_new), action='S', dollars=500.0)]
    assert count_in_window(events, sessions, D, 20, source='form4', direction='bullish') == 0
    assert count_in_window(events, sessions, D, 20, source='form4', direction='bearish') == 1
    assert count_in_window(events, sessions, D, 40, source='form4') == 2


def test_insider_cluster_counts_distinct_insiders_not_trades():
    sessions = _sessions()
    t1, t2 = sessions[-3], sessions[-2]
    two_insiders = [_ev(t1, _public(t1), insider='a'), _ev(t2, _public(t2), insider='b'),
                    _ev(t2, _public(t2), insider='b')]
    assert insider_cluster(two_insiders, sessions, D, window=10, min_insiders=3) is False
    three = two_insiders + [_ev(t2, _public(t2), insider='c')]
    assert insider_cluster(three, sessions, D, window=10, min_insiders=3) is True
    # sales never count toward the purchase cluster
    sales = [_ev(t, _public(t), action='S', insider=x) for t, x in ((t1, 'a'), (t1, 'b'), (t1, 'c'))]
    assert insider_cluster(sales, sessions, D, window=10, min_insiders=3) is False


def test_net_dollars_signed_and_ignores_non_directional_codes():
    sessions = _sessions()
    t = sessions[-2]
    events = [_ev(t, _public(t), action='P', dollars=1000.0),
              _ev(t, _public(t), action='S', dollars=250.0),
              _ev(t, _public(t), action='A', dollars=99999.0),
              _ev(t, _public(t), action='M', dollars=99999.0)]
    assert net_dollars(events, sessions, D, 10) == 750.0
    assert net_dollars([], sessions, D, 10) == 0.0  # evaluable zero


def test_max_trade_ne_when_no_matching_event():
    sessions = _sessions()
    assert max_trade_dollars([], sessions, D, 60) is None
    t = sessions[-2]
    events = [_ev(t, _public(t), action='S', dollars=10.0)]
    assert max_trade_dollars(events, sessions, D, 60, direction='bullish') is None
    assert max_trade_dollars(events, sessions, D, 60, direction='bearish') == 10.0


def test_emitter_schema_literals_and_determinism(tmp_path):
    import shutil
    root = tmp_path / 'r'
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '__pycache__', 'data', 'docs'))
    r1 = sec_options_master.build(root)
    first = (root / 'docs' / sec_options_master.SEC_CSV).read_bytes()
    r2 = sec_options_master.build(root)
    assert r1 == r2 and (root / 'docs' / sec_options_master.SEC_CSV).read_bytes() == first
    with (root / 'docs' / sec_options_master.SEC_CSV).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == r1['rows'] > 0
    assert list(rows[0].keys()) == CSV_COLUMNS
    assert len({row['question_id'] for row in rows}) == len(rows)
    for row in rows:
        assert row['definition_status'] == 'BOUND'
        assert row['data_group'] == sec_options_master.DATA_GROUP
        assert row['source_question_id'] == 'I187'
        assert row['expression'] == 'CONCRETE'
        # strict contract: literal thresholds only, formula matches its own parts
        float(row['comparison_threshold'])
        formula = row['formula']
        assert formula.startswith('(') and formula.endswith(
            ' ' + row['comparator'] + ' ' + row['comparison_threshold'])
        assert row['feature_expression'] in formula
        json.loads(row['feature_json'])
        assert row['question_id'] == 'BS1-' + identity(
            {'feature': json.loads(row['feature_json']),
             'comparator': row['comparator'],
             'comparison_threshold': row['comparison_threshold'],
             'outcome': row['source_outcome']})
    facets = {row['facet'] for row in rows}
    assert {'form4_days_since', 'form4_count', 'form4_net_dollars', 'form4_cluster',
            'form4_max_trade'} <= facets
    # every emitted recipe is implemented in world_sec_events
    import world_sec_events as wse
    implemented = {'sec_form4_days_since_last_v1': wse.days_since_last,
                   'sec_form4_count_v1': wse.count_in_window,
                   'sec_form4_net_dollars_v1': wse.net_dollars,
                   'sec_form4_cluster_v1': wse.insider_cluster,
                   'sec_form4_max_trade_v1': wse.max_trade_dollars}
    used = {row['feature_expression'].split('(')[0] for row in rows}
    assert used <= set(implemented)
