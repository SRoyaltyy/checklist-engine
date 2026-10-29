import numpy as np
import pandas as pd
import pytest

from market_storage import assert_exact_frame
from world_calendar_pivots import ANCHORS, LEVELS, anchor_tables, native_calendar_pivots
from world_timeframes import TIMEFRAMES


def fixture():
    cal = pd.bdate_range('2019-09-16', '2020-04-10').difference(
        pd.DatetimeIndex(['2019-12-25', '2020-01-01']))
    close = 100 + np.arange(len(cal), dtype=float)
    bars = pd.DataFrame(dict(date=cal, high=close+2, low=close-3, close=close))
    return cal, bars


@pytest.mark.parametrize('setting,day,frequency', [
    ('short', '2020-01-06', 'W-SUN'), ('default', '2020-02-03', 'M'),
    ('long', '2020-04-01', 'Q-DEC')])
def test_literal_hlc_formula_uses_immediately_prior_complete_calendar_anchor(setting, day, frequency):
    cal, bars = fixture(); day = pd.Timestamp(day)
    out = native_calendar_pivots(bars, cal, '1d', day).iloc[-1]
    wanted = day.to_period(frequency)-1
    source = bars.loc[pd.DatetimeIndex(bars.date).to_period(frequency) == wanted]
    h, l, c = source.high.max(), source.low.min(), source.close.iloc[-1]
    p = (h+l+c)/3
    assert [out['I074_'+setting+'_'+k] for k in LEVELS] == [p, 2*p-l, 2*p-h, p+(h-l), p-(h-l)]


def test_first_anchor_partial_ipo_missing_session_and_bad_hlc_are_unknown_not_older_period():
    cal, bars = fixture(); day = pd.Timestamp('2020-02-03')
    january = bars.date.dt.to_period('M') == day.to_period('M')-1
    for changed in (bars.loc[~(bars.date == pd.Timestamp('2020-01-13'))],
                    bars.loc[bars.date >= '2020-01-13'],
                    bars.assign(high=bars.high.mask(bars.date.eq('2020-01-13'), 1.))):
        last = native_calendar_pivots(changed, cal, '1d', day).iloc[-1]
        assert last.filter(like='I074_default_').isna().all()
    table = anchor_tables(bars, cal, day)['default']
    assert not table.iloc[0].complete and table.loc['2019-12'].complete
    assert table.loc['2020-01'].known_sessions == january.sum()


def test_monthly_availability_uses_actual_next_session_and_just_completed_month():
    cal, bars = fixture(); day = pd.Timestamp('2020-02-03')
    frame = native_calendar_pivots(bars, cal, 'monthly', day)
    last = frame.iloc[-1]
    assert last.source_candle_end == pd.Timestamp('2020-01-31')
    assert last.available_from == day
    expected = anchor_tables(bars, cal, day)['default'].loc['2020-01', 'p']
    assert last.I074_default_p == expected


@pytest.mark.parametrize('timeframe', TIMEFRAMES)
def test_all_native_grids_are_exact_under_raw_and_calendar_truncation(timeframe):
    cal, bars = fixture(); cut = pd.Timestamp('2020-02-03')
    full = native_calendar_pivots(bars, cal, timeframe, cal[-1])
    earlier = native_calendar_pivots(bars.loc[bars.date < cut], cal[cal <= cut], timeframe, cut)
    expected = full.loc[full.available_from <= cut].reset_index(drop=True)
    assert_exact_frame(expected, earlier)
    assert len(full.columns) == 18
    assert all(t == np.float64 for t in full.dtypes.iloc[3:])


def test_day_d_hlc_is_ignored_and_current_partial_period_is_not_an_anchor():
    cal, bars = fixture(); cut = pd.Timestamp('2020-01-29')
    expected = native_calendar_pivots(bars, cal, '1d', cut)
    changed = bars.copy(); changed.loc[changed.date >= cut, ['high', 'low', 'close']] = 1e9
    assert_exact_frame(expected, native_calendar_pivots(changed, cal, '1d', cut))
    tables = anchor_tables(bars, cal, cut)
    assert '2020-01' not in tables['default'].index
    assert '2020Q1' not in tables['long'].index


def test_first_query_session_returns_explicit_empty_native_schema():
    cal, bars = fixture()
    out = native_calendar_pivots(bars, cal, 'monthly', cal[0])
    assert out.empty and len(out.columns) == 18


@pytest.mark.parametrize('bad', ['duplicate', 'unordered', 'spliced', 'outside'])
def test_bad_source_identity_or_dates_fail_closed(bad):
    cal, bars = fixture()
    if bad == 'duplicate': bars = pd.concat([bars, bars.iloc[-1:]])
    elif bad == 'unordered': bars = bars.iloc[::-1]
    elif bad == 'spliced': bars['ticker'] = ['A']*(len(bars)-1)+['B']
    else:
        bars.loc[0, 'date'] = pd.Timestamp('2019-09-15')
        cal = cal[1:]
        # A row inside the calendar's covered date range on a non-session.
        bars.loc[2, 'date'] = pd.Timestamp('2019-09-21')
        bars = bars.sort_values('date')
    with pytest.raises(ValueError): native_calendar_pivots(bars, cal, '1d', cal[-1])
