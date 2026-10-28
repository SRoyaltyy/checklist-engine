import numpy as np
import pandas as pd
import pytest

from market_storage import assert_exact_frame
from outside_breadth import aggregate, breadth_candles, coverage_row, stock_contributions, write_lossless
from world_timeframes import TIMEFRAMES


def sample():
    sessions = pd.bdate_range('2019-10-01', '2020-05-08')
    close = 20 + np.sin(np.arange(len(sessions)) / 4) + np.arange(len(sessions)) / 20
    bars = pd.DataFrame(dict(date=sessions, open=close, high=close+1, low=close-1, close=close, volume=100.))
    votes = stock_contributions(bars)
    return sessions, votes


def test_full_history_is_retained_and_v1_line_is_exactly_reconstructible():
    sessions, votes = sample()
    full = aggregate(votes, sessions, sessions[-2], retain_history=True)
    old = aggregate(votes, sessions, sessions[-2])
    assert full.date.min() == sessions[0] and old.date.min() == pd.Timestamp('2020-01-02')
    offset = int(full.loc[full.date < pd.Timestamp('2020-01-02'), 'ad_net'].sum())
    restored = full.loc[full.date >= pd.Timestamp('2020-01-02')].reset_index(drop=True)
    restored['ad_line'] -= offset
    assert_exact_frame(old, restored)
    assert coverage_row(full, sessions, sessions[-2])['rows'] == len(old)


def test_every_integer_grid_omits_an_opening_partial_bucket_and_keeps_later_complete_buckets():
    sessions, votes = sample()
    full = aggregate(votes, sessions, sessions[-2], retain_history=True)
    clipped = full.iloc[57:].reset_index(drop=True)
    native = breadth_candles(clipped, sessions)
    for tf in TIMEFRAMES[:-1]:
        n = int(tf[:-1])
        own = native.loc[native.timeframe == tf]
        assert len(own)
        for row in own.itertuples():
            pos = sessions.get_indexer([row.date])[0]
            assert row.candle_start == sessions[pos-n+1]
            assert pos % n == n-1
            assert len(clipped.loc[clipped.date.between(row.candle_start, row.date)]) == n
    assert sessions[59] not in set(native.loc[native.timeframe == '20d', 'date'])
    assert sessions[79] in set(native.loc[native.timeframe == '20d', 'date'])


def test_partial_month_and_an_interior_missing_session_cannot_be_completed_candles():
    sessions, votes = sample()
    full = aggregate(votes, sessions, '2020-03-10', retain_history=True)
    clipped = full.loc[full.date >= pd.Timestamp('2020-01-15')].copy()
    native = breadth_candles(clipped, sessions)
    assert list(native.loc[native.timeframe == 'monthly', 'date'].dt.month) == [2]
    missing = full.drop(index=10)
    native = breadth_candles(missing, sessions)
    assert sessions[19] not in set(native.loc[native.timeframe == '20d', 'date'])


def test_raw_cutoff_rebuild_preserves_all_fields_on_all_native_grids():
    sessions, votes = sample()
    full = aggregate(votes, sessions, sessions[-2], retain_history=True)
    expected = breadth_candles(full, sessions)
    for cut in (pd.Timestamp('2020-01-03'), pd.Timestamp('2020-03-04')):
        earlier = aggregate(votes.loc[votes.date < cut], sessions, cut-pd.Timedelta(days=1), retain_history=True)
        actual = breadth_candles(earlier, sessions)
        a = actual.loc[actual.available_from <= cut].sort_values(['timeframe','date']).reset_index(drop=True)
        b = expected.loc[expected.available_from <= cut].sort_values(['timeframe','date']).reset_index(drop=True)
        assert_exact_frame(a, b)
        assert set(a.timeframe) == set(TIMEFRAMES)


def test_storage_preserves_nan_payload_and_negative_zero_without_count_truncation(tmp_path):
    sessions, votes = sample()
    frame = aggregate(votes, sessions, sessions[3], retain_history=True)
    values = np.array([0x8000000000000000, 0x7ff8000000000042, 0x7ff0000000000000, 0x3ff0000000000000], dtype='uint64').view('float64')
    frame['ad_ratio'] = values
    write_lossless(frame, tmp_path/'exact.parquet')
    np.testing.assert_array_equal(pd.read_parquet(tmp_path/'exact.parquet').ad_ratio.to_numpy().view('uint64'), values.view('uint64'))
    frame['advance'] = frame.advance.astype('float64')
    frame.loc[0,'advance'] = .5
    with pytest.raises(ValueError, match='nonintegral'):
        write_lossless(frame, tmp_path/'bad.parquet')


def test_duplicate_input_or_calendar_sessions_fail():
    sessions, votes = sample()
    frame = aggregate(votes, sessions, sessions[5], retain_history=True)
    with pytest.raises(ValueError, match='duplicate breadth'):
        breadth_candles(pd.concat([frame,frame.iloc[:1]]), sessions)
    with pytest.raises(ValueError, match='calendar'):
        aggregate(votes, sessions.append(sessions[:1]), sessions[5], retain_history=True)


def test_production_grid_guard_and_native_reader_reject_partial_or_early_rows():
    from ci.breadth_native_history import check_grid, native_factor
    from world_context_store import context_row_view
    sessions, votes = sample()
    full = aggregate(votes, sessions, sessions[-2], retain_history=True)
    native = breadth_candles(full, sessions)
    check_grid(native, sessions)
    own = native.loc[native.timeframe == '20d'].reset_index(drop=True)
    factor = native_factor(own)
    before = own.available_from.iloc[0]-pd.Timedelta(days=1)
    row = context_row_view('A', pd.DatetimeIndex([before,own.available_from.iloc[0]]), '20d',[factor])
    assert pd.isna(row.breadth_ad_line__20d.iloc[0])
    assert row.breadth_ad_line__20d.iloc[1] == own.ad_line.iloc[0]
    bad = native.copy()
    bad.loc[bad.timeframe == '20d','candle_start'] += pd.Timedelta(days=1)
    with pytest.raises(ValueError, match='partial'):
        check_grid(bad,sessions)
    bad = native.copy()
    bad.loc[bad.timeframe == '1d','available_from'] = bad.loc[bad.timeframe == '1d','date']
    with pytest.raises(ValueError, match='availability'):
        check_grid(bad,sessions)


def test_production_prefix_guard_detects_changed_historical_values():
    from ci.breadth_native_history import prefix_checks
    sessions, votes = sample()
    full = aggregate(votes, sessions, sessions[-2], retain_history=True)
    native = breadth_candles(full,sessions)
    cut = '2020-03-04'
    assert len(prefix_checks(full,native,{cut:votes},sessions)) == 22
    bad = votes.copy()
    bad.loc[0,'advance'] += 1
    with pytest.raises(AssertionError):
        prefix_checks(full,native,{cut:bad},sessions)


def test_legacy_overlap_retains_the_original_values_and_accounts_for_partial_v1():
    from ci.breadth_native_history import legacy_overlap
    sessions,votes = sample()
    full = aggregate(votes,sessions,sessions[-2],retain_history=True)
    native = breadth_candles(full,sessions)
    old = aggregate(votes,sessions,sessions[-2])
    old_native = breadth_candles(old,sessions)
    # Reproduce one old opening bucket. Its partialness is logged, not certified.
    opening = native.loc[(native.timeframe=='20d')&(native.date>=pd.Timestamp('2020-01-02'))&(native.candle_start<pd.Timestamp('2020-01-02'))].head(1).copy()
    assert len(opening)==1
    opening['candle_start'] = pd.Timestamp('2020-01-02')
    offset = int(full.loc[full.date<pd.Timestamp('2020-01-02'),'ad_net'].sum())
    opening['ad_line'] -= offset
    old_native = pd.concat([old_native,opening],ignore_index=True)
    result = legacy_overlap(full,native,sessions,old,old_native)
    assert result['partial_v1_native_rows']==1 and result['v1_ad_line_offset']==offset


def test_no_eligible_history_is_unknown_not_an_observed_zero_and_flows_require_every_day(tmp_path):
    from outside_breadth import available_breadth
    sessions,votes=sample()
    raw=aggregate(votes,sessions,sessions[-2],retain_history=True)
    visible=available_breadth(raw)
    assert raw.new_high.eq(0).all() and raw.eligible_52w.eq(0).all()
    assert visible.new_high.isna().all() and visible.new_low.isna().all()
    assert visible.new_highs_minus_new_lows.isna().all()
    assert pd.isna(visible.ad_net.iloc[0]) and visible.ad_line.iloc[0]==0
    assert visible.ad_net.iloc[1]==raw.ad_net.iloc[1]
    native=breadth_candles(visible,sessions)
    first=native.loc[native.timeframe=='5d'].iloc[0]
    assert pd.isna(first.ad_net) and pd.isna(first.new_high)
    second=native.loc[native.timeframe=='5d'].iloc[1]
    assert second.ad_net==raw.ad_net.iloc[5:10].sum()
    write_lossless(native,tmp_path/'unknown.parquet')
    back=pd.read_parquet(tmp_path/'unknown.parquet')
    assert pd.isna(back.loc[back.timeframe=='5d','ad_net'].iloc[0])


def test_registered_sma_breadth_requires_more_than100_eligible_names():
    from outside_breadth import available_breadth
    sessions,votes=sample()
    raw=aggregate(votes,sessions,sessions[2],retain_history=True)
    for window in (20,50,200):
        raw[f'eligible_sma{window}']=[0,100,101]
        raw[f'pct_above_sma{window}']=[np.nan,.2,.3]
    visible=available_breadth(raw)
    for window in (20,50,200):
        assert visible[f'pct_above_sma{window}'].iloc[:2].isna().all()
        assert visible[f'pct_above_sma{window}'].iloc[2]==.3
