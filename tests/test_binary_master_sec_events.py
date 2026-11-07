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
        assert row['expression'] == 'CONCRETE'
        # strict contract: literal thresholds only, formula matches its own parts
        if row['feature_kind'] == 'category_code':
            assert row['comparison_threshold']  # fixed-set code, not numeric
        else:
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
            'form4_max_trade', 'short_volume_ratio', 'short_volume_ratio_mean',
            'short_volume_ratio_percentile', 'short_volume_ratio_state_change',
            'cboe_pc_volume_ratio', 'cboe_pc_oi_ratio', 'cboe_pc_ratio_percentile',
            'vix_level', 'vix_term_structure', 'cboe_skew'} <= facets
    blocks = {row['block'] for row in rows}
    assert {sec_options_master.BLOCK_FORM4, sec_options_master.BLOCK_SHORTVOL,
            sec_options_master.BLOCK_CBOE, sec_options_master.BLOCK_ANALYST,
            sec_options_master.BLOCK_13F, sec_options_master.BLOCK_SECTOR,
            sec_options_master.BLOCK_SHORTINT, sec_options_master.BLOCK_SHARES,
            sec_options_master.BLOCK_DIV, sec_options_master.BLOCK_XBRL} <= blocks
    # every emitted recipe is implemented
    import world_sec_events as wse
    import world_market_series as wms
    import world_sec_ratios as wsr
    implemented = {'sec_form4_days_since_last_v1': wse.days_since_last,
                   'sec_form4_count_v1': wse.count_in_window,
                   'sec_form4_net_dollars_v1': wse.net_dollars,
                   'sec_form4_cluster_v1': wse.insider_cluster,
                   'sec_form4_max_trade_v1': wse.max_trade_dollars,
                   'sec_analyst_days_since_last_v1': wse.days_since_last,
                   'sec_analyst_count_v1': wse.count_in_window,
                   'sec_analyst_net_direction_v1': wse.net_direction_count,
                   'sec_analyst_last_pt_change_pct_v1': wse.last_pt_change_pct,
                   'sec_13f_days_since_last_v1': wse.days_since_last,
                   'sec_13f_filers_v1': wse.filers_13f_v1,
                   'sec_13f_shares_change_pct_v1': wse.shares_change_pct_13f_v1,
                   'sec_13f_new_filer_v1': wse.new_filer_13f_v1,
                   'finra_si_pct_float_v1': wse.si_pct_float_v1,
                   'finra_si_days_to_cover_v1': wse.si_days_to_cover_v1,
                   'finra_si_pct_percentile_v1': wse.si_pct_percentile_v1,
                   'finra_si_tercile_state_change_v1': wse.si_tercile_state_change_v1,
                   'sec_sector_membership_days_v1': wse.sector_membership_days,
                   'sec_sector_changed_within_v1': wse.sector_changed_within,
                   'sec_sector_change_count_v1': wse.sector_change_count,
                   'sec_shares_change_pct_v1': wse.shares_out_change_pct_v1,
                   'sec_shares_out_event_within_v1': wse.shares_out_event_within,
                   'sec_div_days_since_ex_v1': wse.days_since_ex_dividend_v1,
                   'sec_div_dps_changed_v1': wse.dps_changed_v1,
                   'sec_xbrl_pe_v1': wsr.pe_ratio_v1,
                   'sec_xbrl_pb_v1': wsr.pb_ratio_v1,
                   'sec_xbrl_revenue_growth_yoy_v1': wsr.revenue_growth_yoy_v1,
                   'sec_xbrl_margin_expanded_yoy_v1': wsr.margin_expanded_yoy_v1,
                   'finra_short_ratio_v1': wms.finra_short_ratio_v1,
                   'finra_short_ratio_mean_v1': wms.finra_short_ratio_mean_v1,
                   'finra_short_ratio_percentile_v1': wms.finra_short_ratio_percentile_v1,
                   'finra_short_ratio_cross_median_v1': wms.finra_short_ratio_cross_median_v1,
                   'cboe_put_call_volume_ratio_v1': wms.cboe_put_call_volume_ratio_v1,
                   'cboe_put_call_oi_ratio_v1': wms.cboe_put_call_oi_ratio_v1,
                   'cboe_pc_ratio_percentile_v1': wms.cboe_pc_ratio_percentile_v1,
                   'vix_level_v1': wms.vix_level_v1,
                   'vix_term_structure_state_v1': wms.vix_term_structure_state_v1,
                   'cboe_skew_v1': wms.cboe_skew_v1}
    used = {row['feature_expression'].split('(')[0] for row in rows}
    assert used <= set(implemented)


# ---- I189 FINRA short volume -------------------------------------------------

from world_market_series import (cboe_pc_ratio_percentile_v1,
                                 cboe_put_call_oi_ratio_v1,
                                 cboe_put_call_volume_ratio_v1, cboe_skew_v1,
                                 cboe_era, finra_short_ratio_cross_median_v1,
                                 finra_short_ratio_mean_v1,
                                 finra_short_ratio_percentile_v1,
                                 finra_short_ratio_v1, vix_level_v1,
                                 vix_term_structure_state_v1)


def _rec(session, short_vol, total_vol, public_hour=18):
    return dict(session=session, public_dt=datetime.combine(session, datetime.min.time())
                + timedelta(hours=public_hour), short_vol=short_vol, total_vol=total_vol)


def _shortvol_series(ratios, sessions):
    return [_rec(s, round(r * 1000), 1000) for s, r in zip(sessions[-len(ratios):], ratios)]


def test_finra_ratio_pit_and_ne_rules():
    sessions = _sessions(40)
    assert finra_short_ratio_v1([], sessions, D) is None
    recs = [_rec(sessions[-1], 500, 1000)]
    assert finra_short_ratio_v1(recs, sessions, D) == 0.5
    # zero total volume -> NE, never a fake 0 or division error
    assert finra_short_ratio_v1([_rec(sessions[-1], 0, 0)], sessions, D) is None
    # published after the open -> invisible at D -> NE
    late = [dict(session=D, public_dt=datetime.combine(D, datetime.min.time())
                 + timedelta(hours=10), short_vol=500, total_vol=1000)]
    assert finra_short_ratio_v1(late, sessions, D) is None


def test_finra_mean_and_percentile_need_full_history():
    sessions = _sessions(80)
    recs = _shortvol_series([0.4] * 4, sessions)
    assert finra_short_ratio_mean_v1(recs, sessions, D, 5) is None  # only 4 usable
    recs = _shortvol_series([0.4] * 5, sessions)
    assert finra_short_ratio_mean_v1(recs, sessions, D, 5) == 0.4
    recs = _shortvol_series([0.5] * 58 + [0.6], sessions)
    assert finra_short_ratio_percentile_v1(recs, sessions, D, 60) is None  # only 59 usable
    recs = _shortvol_series([0.5] * 60 + [0.6], sessions)
    pct = finra_short_ratio_percentile_v1(recs, sessions, D, 60)
    assert pct == 1.0  # 0.6 is the max of the window


def test_finra_median_cross_state_change():
    sessions = _sessions(80)
    flat = [0.5] * 70
    spike = [0.5] * 70 + [0.9, 0.9, 0.9, 0.9, 0.9]
    assert finra_short_ratio_cross_median_v1(_shortvol_series(flat, sessions), sessions, D, 60, 5) is False
    assert finra_short_ratio_cross_median_v1(_shortvol_series(spike, sessions), sessions, D, 60, 5) is True
    # a cross 6 sessions ago is outside the `within` window
    older = [0.5] * 65 + [0.9] + [0.5] * 5
    assert finra_short_ratio_cross_median_v1(_shortvol_series(older, sessions), sessions, D, 60, 5) is False


# ---- I201 CBOE market-wide ---------------------------------------------------

def _cboe(session, call_vol=1000, put_vol=800, call_oi=5000, put_oi=4000,
          vix=15.0, vix3m=16.0, skew=120.0, group='equity', public_hour=18):
    return dict(session=session, group=group,
                public_dt=datetime.combine(session, datetime.min.time()) + timedelta(hours=public_hour),
                call_vol=call_vol, put_vol=put_vol, call_oi=call_oi, put_oi=put_oi,
                vix=vix, vix3m=vix3m, skew=skew)


def test_cboe_ratios_raw_counts_and_zero_call_ne():
    sessions = _sessions(10)
    recs = [_cboe(sessions[-1], call_vol=1000, put_vol=800)]
    assert cboe_put_call_volume_ratio_v1(recs, sessions, D) == 0.8
    assert cboe_put_call_oi_ratio_v1(recs, sessions, D) == 0.8
    zero_call = [_cboe(sessions[-1], call_vol=0, put_vol=800)]
    assert cboe_put_call_volume_ratio_v1(zero_call, sessions, D) is None
    # group filter: equity questions never read index-group records
    idx_only = [dict(_cboe(sessions[-1]), group='index')]
    assert cboe_put_call_volume_ratio_v1(idx_only, sessions, D, group='equity') is None
    assert cboe_put_call_volume_ratio_v1(idx_only, sessions, D, group='index') is not None


def test_cboe_era_split_percentile_never_crosses_boundary():
    from world_market_series import CBOE_0DTE_FLAG_DATE, CBOE_ERA_BREAK

    def weekdays_around(anchor, before, after):
        out, cur = [], anchor - timedelta(days=before + 3)
        while len(out) < before + after:
            if cur.weekday() < 5:
                out.append(cur)
            cur += timedelta(days=1)
        return out

    # sessions spanning all three eras; D is well after the 0DTE flag
    sessions = (weekdays_around(CBOE_ERA_BREAK, 6, 4)
                + weekdays_around(CBOE_0DTE_FLAG_DATE, 6, 4))
    D2 = sessions[-1] + timedelta(days=3)
    sessions = [s for s in sessions if s < D2]
    while (D2.weekday() >= 5) or D2 in sessions:
        D2 += timedelta(days=1)
    recs = [_cboe(s) for s in sessions]
    assert cboe_era(sessions[0]) == 'pre_2019_10_07'
    assert cboe_era(sessions[-1]) == 'post_2022_0dte'
    # current era (post_2022_0dte) has far fewer than 252 usable sessions -> NE,
    # even though the full history spans three eras (they must NOT be pooled)
    assert cboe_pc_ratio_percentile_v1(recs, sessions + [D2], D2, 252) is None
    # within-era percentile works when the current era has enough history:
    # D3 sits ~16 months after the 0DTE flag so 300 sessions fit in-era
    D3 = date(2024, 3, 1)
    long_recent = [D3 - timedelta(days=d) for d in range(430, 0, -1)
                   if (D3 - timedelta(days=d)).weekday() < 5][:300]
    assert all(cboe_era(s) == 'post_2022_0dte' for s in long_recent)
    recs2 = [_cboe(s) for s in long_recent]
    assert cboe_pc_ratio_percentile_v1(recs2, long_recent + [D3], D3, 252) == 1.0


def test_vix_level_term_structure_and_skew():
    sessions = _sessions(10)
    recs = [_cboe(sessions[-1], vix=22.0, vix3m=20.0, skew=135.0)]
    assert vix_level_v1(recs, sessions, D) == 22.0
    assert vix_term_structure_state_v1(recs, sessions, D) == 'backwardation'
    assert cboe_skew_v1(recs, sessions, D) == 135.0
    contango = [dict(_cboe(sessions[-1]), vix=14.0, vix3m=16.0)]
    assert vix_term_structure_state_v1(contango, sessions, D) == 'contango'
    missing_3m = [dict(_cboe(sessions[-1]), vix3m=None)]
    assert vix_term_structure_state_v1(missing_3m, sessions, D) is None


# ---- I197 analyst actions + I199 13F -----------------------------------------

from world_sec_events import (filers_13f_v1, last_pt_change_pct,
                              net_direction_count, new_filer_13f_v1,
                              shares_change_pct_13f_v1)


def _anev(session, action, pt=None, public_hour=10):
    e = _ev(session, _public(session, public_hour), action=action, insider='n1',
            source='analyst')
    e['pt_change_pct'] = pt
    return e


def test_analyst_net_direction_and_neutral_counting():
    sessions = _sessions(40)
    t1, t2, t3 = sessions[-10], sessions[-8], sessions[-3]
    events = [_anev(t1, 'upgrade'), _anev(t2, 'downgrade'),
              _anev(t3, 'reiterate'), _anev(t3, 'initiate')]
    assert net_direction_count(events, sessions, D, 30, 'analyst') == 0
    # non-directional actions contribute 0 but are still counted as events
    from world_sec_events import count_in_window
    assert count_in_window(events, sessions, D, 30, source='analyst') == 4
    assert count_in_window(events, sessions, D, 30, source='analyst',
                           direction='bullish') == 1
    assert net_direction_count([], sessions, D, 30, 'analyst') == 0  # evaluable zero


def test_analyst_pt_change_uses_latest_usable_only():
    sessions = _sessions(40)
    t1, t2 = sessions[-6], sessions[-2]
    events = [_anev(t1, 'upgrade', pt=12.0), _anev(t2, 'downgrade', pt=-7.5)]
    assert last_pt_change_pct(events, sessions, D) == -7.5
    no_pt = [_anev(t2, 'reiterate', pt=None)]
    assert last_pt_change_pct(no_pt, sessions, D) is None
    assert last_pt_change_pct([], sessions, D) is None


def _13f(session, filers, shares, public_hour=18):
    e = _ev(session, _public(session, public_hour), insider='13f', source='13f')
    e['filers'] = frozenset(filers)
    e['shares'] = shares
    return e


def test_13f_filers_and_qoq_change():
    sessions = _sessions(80)
    q1, q2 = sessions[-70], sessions[-45]
    events = [_13f(q1, {'a', 'b', 'c'}, 1000), _13f(q2, {'a', 'b', 'c', 'd'}, 1250)]
    assert filers_13f_v1(events, sessions, D) == 4
    assert shares_change_pct_13f_v1(events, sessions, D) == 25.0
    assert new_filer_13f_v1(events, sessions, D) is True
    # only one usable filing -> QoQ change and new-filer are NE
    assert shares_change_pct_13f_v1(events[:1], sessions, D) is None
    assert new_filer_13f_v1(events[:1], sessions, D) is None
    assert filers_13f_v1([], sessions, D) is None
    # same filer set -> no new filer
    same = [_13f(q1, {'a', 'b'}, 1000), _13f(q2, {'a', 'b'}, 900)]
    assert new_filer_13f_v1(same, sessions, D) is False
    assert shares_change_pct_13f_v1(same, sessions, D) == -10.0


def test_13f_filing_after_cutoff_is_invisible():
    sessions = _sessions(40)
    late = [_13f(D, {'a'}, 1000, public_hour=10)]  # filed D 10:00 ET -> invisible
    assert filers_13f_v1(late, sessions, D) is None


# ---- I188 short interest + C26/I193/I196 -------------------------------------

from world_sec_events import (days_since_ex_dividend_v1, dps_changed_v1,
                              sector_change_count, sector_changed_within,
                              sector_membership_days, shares_out_change_pct_v1,
                              shares_out_event_within, si_days_to_cover_v1,
                              si_pct_float_v1, si_pct_percentile_v1,
                              si_tercile_state_change_v1)


def _si(session, si, float_shares, adv=1000.0, hour=18):
    return dict(session=session, public_dt=datetime.combine(session, datetime.min.time())
                + timedelta(hours=hour), source='short_interest', si_shares=si,
                float_shares=float_shares, avg_daily_vol=adv)


def test_short_interest_levels_and_ne():
    sessions = _sessions(40)
    assert si_pct_float_v1([], D) is None
    recs = [_si(sessions[-1], 800, 10000)]
    assert si_pct_float_v1(recs, D) == 8.0
    assert si_days_to_cover_v1(recs, D) == 0.8
    zero_float = [_si(sessions[-1], 800, 0)]
    assert si_pct_float_v1(zero_float, D) is None


def test_short_interest_publication_point_history():
    sessions = _sessions(60)
    biweekly = [sessions[-(2 * i)] for i in range(1, 13)]  # 12 publication points
    recs = [_si(s, 5000, 100000) for s in biweekly]
    assert si_pct_percentile_v1(recs, D, 12) == 1.0
    assert si_pct_percentile_v1(recs[:-1], D, 12) is None  # only 11 points
    flat = [_si(s, 5000, 100000) for s in biweekly]
    assert si_tercile_state_change_v1(flat, D) is False
    assert si_tercile_state_change_v1(flat[:11], D) is None
    # 10 high points, one low SECOND-NEWEST (bottom tercile), newest high again
    jump = [_si(biweekly[0], 9000, 100000), _si(biweekly[1], 1000, 100000)]
    jump += [_si(s, 9000, 100000) for s in biweekly[2:]]
    assert si_tercile_state_change_v1(jump, D) is True


def _sec(session, code, hour=18):
    return dict(session=session, public_dt=datetime.combine(session, datetime.min.time())
                + timedelta(hours=hour), source='sector', sector_code=code)


def test_sector_membership_and_changes():
    sessions = _sessions(80)
    obs = [_sec(sessions[-60], 'A'), _sec(sessions[-30], 'A'), _sec(sessions[-10], 'B')]
    assert sector_membership_days(obs, sessions, D) == sum(
        1 for s in sessions if sessions[-30] < s < D)
    assert sector_changed_within(obs, sessions, D, 20) is True
    assert sector_changed_within(obs, sessions, D, 5) is False
    assert sector_change_count(obs, sessions, D, 252) == 1
    none = []
    assert sector_membership_days(none, sessions, D) is None
    assert sector_changed_within(none, sessions, D, 20) is None


def _shr(session, shares, hour=18):
    return dict(session=session, public_dt=datetime.combine(session, datetime.min.time())
                + timedelta(hours=hour), source='shares_out', shares=shares)


def test_shares_outstanding_change_and_split_scale():
    sessions = _sessions(40)
    obs = [_shr(sessions[-30], 1000), _shr(sessions[-5], 500)]
    assert shares_out_change_pct_v1(obs, D) == -50.0
    assert shares_out_event_within(obs, D, 40) is True
    assert shares_out_event_within(obs, D, 60) is False
    assert shares_out_change_pct_v1(obs[:1], D) is None
    assert shares_out_event_within(obs[:1], D, 40) is None


def _div(session, ex_date, dps, hour=18):
    return dict(session=session, public_dt=datetime.combine(session, datetime.min.time())
                + timedelta(hours=hour), source='dividend', ex_date=ex_date, dps=dps)


def test_dividend_days_since_ex_and_dps_change():
    sessions = _sessions(40)
    obs = [_div(sessions[-8], sessions[-8], 0.5), _div(sessions[-3], sessions[-3], 0.55)]
    assert days_since_ex_dividend_v1(obs, sessions, D) == sum(
        1 for s in sessions if sessions[-3] < s < D)
    assert dps_changed_v1(obs, D) is True
    same = [obs[0], _div(sessions[-3], sessions[-3], 0.5)]
    assert dps_changed_v1(same, D) is False
    assert dps_changed_v1(obs[:1], D) is None
    assert days_since_ex_dividend_v1([], sessions, D) is None


# ---- I192 XBRL fundamentals ---------------------------------------------------

from world_sec_ratios import (margin_expanded_yoy_v1, pb_ratio_v1, pe_ratio_v1,
                              revenue_growth_yoy_v1)


def _pt(value, status='VALUE'):
    return dict(value=value, status=status)


def test_xbrl_pe_pb_and_status_propagation():
    assert pe_ratio_v1(_pt(2.0), 30.0) == 15.0
    assert pe_ratio_v1(_pt(2.0), dict(value=30.0, status='VALUE')) == 15.0
    assert pe_ratio_v1(_pt(-1.0), 30.0) is None   # negative EPS -> NE
    assert pe_ratio_v1(_pt(2.0), -30.0) is None   # non-positive price -> NE
    # any non-VALUE status propagates: never partially imputed
    for status in ('CONFLICTING_VALUES_SAME_FILED_DATE', 'MULTIPLE_VALID_PERIOD_STARTS',
                   'NO_KNOWN_FACT'):
        assert pe_ratio_v1(_pt(2.0, status), 30.0) is None
    assert pb_ratio_v1(_pt(1_000_000.0), _pt(500_000.0), 6.0) == 3.0
    assert pb_ratio_v1(_pt(-500.0), _pt(100.0), 6.0) is None  # negative book value
    assert pb_ratio_v1(_pt(1_000_000.0), _pt(0.0), 6.0) is None  # zero shares


def test_xbrl_growth_and_margin():
    assert revenue_growth_yoy_v1(_pt(110.0), _pt(100.0)) == 10.0
    assert revenue_growth_yoy_v1(_pt(90.0), _pt(100.0)) == -10.0
    assert revenue_growth_yoy_v1(_pt(110.0), _pt(-100.0)) is None  # negative base
    assert revenue_growth_yoy_v1(_pt(110.0), _pt(0.0)) is None
    assert margin_expanded_yoy_v1(_pt(20.0), _pt(100.0), _pt(10.0), _pt(100.0)) is True
    assert margin_expanded_yoy_v1(_pt(5.0), _pt(100.0), _pt(10.0), _pt(100.0)) is False
    assert margin_expanded_yoy_v1(_pt(20.0, 'NO_KNOWN_FACT'), _pt(100.0),
                                  _pt(10.0), _pt(100.0)) is None
    assert margin_expanded_yoy_v1(_pt(20.0), _pt(0.0), _pt(10.0), _pt(100.0)) is None
