import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ci.fred_pit_measure import online_levels, oracle_native, check_native
from market_storage import assert_exact_frame
from world_context_native import fred_native
from world_fred import compile_timelines, columns
from world_timeframes import TIMEFRAMES


def source():
    return pd.DataFrame(dict(series=['TEST']*5,
        obs_date=pd.to_datetime(['2020-01-01','2020-02-01','2020-02-01','2020-01-01','2030-01-01']),
        vintage_date=pd.to_datetime(['2020-02-01','2020-03-01','2020-03-10','2020-04-01','2020-04-10']),
        value=[1.,2.,3.,99.,4.]))


def test_online_oracle_excludes_exact_vintage_and_future_obs_and_keeps_first_release():
    dates = pd.to_datetime(['2020-02-01','2020-03-01','2020-03-02','2020-03-11','2020-04-02','2020-04-11']).as_unit('ns')
    actual = online_levels(source(), dates, ('TEST',))
    np.testing.assert_equal(actual.fred_test.to_numpy(), [np.nan,1,2,3,3,3])
    np.testing.assert_equal(actual.fred_test_first_release.to_numpy(), [np.nan,1,2,2,2,2])
    np.testing.assert_equal(actual.fred_test_odays.to_numpy(), [np.nan,60,30,39,61,70])
    np.testing.assert_equal(actual.fred_test_vintage_days.to_numpy(), [np.nan,29,1,1,1,1])
    expected = pd.DataFrame(columns(dates, compile_timelines(source())), index=dates)
    assert_exact_frame(actual, expected)
    assert actual.attrs['future_rows_consumed'] == 0


def test_future_value_perturbations_cannot_change_any_earlier_oracle_cutoff():
    raw = source(); cut = pd.Timestamp('2020-03-10')
    changed = raw.copy(); changed.loc[changed.vintage_date >= cut, 'value'] = 1e20
    dates = pd.to_datetime(['2020-02-01','2020-03-02','2020-03-10'])
    assert_exact_frame(online_levels(raw, dates, ('TEST',)), online_levels(changed, dates, ('TEST',)))
    # Positive/negative zero and full float64 source precision are preserved.
    raw = raw.iloc[:1].copy(); raw.loc[:, 'value'] = -0.
    assert np.signbit(online_levels(raw, pd.to_datetime(['2020-02-02']), ('TEST',)).fred_test.iloc[0])


def test_every_native_field_projection_and_fresh_prefix_is_exact_on_all22_grids():
    calendar = pd.bdate_range('2019-11-01','2020-06-12')
    raw = pd.DataFrame(dict(series='TEST', obs_date=calendar-pd.Timedelta(days=5),
                            vintage_date=calendar, value=100+np.sin(np.arange(len(calendar)))))
    late = raw.loc[raw.vintage_date >= '2020-04-01'].copy(); late['series'] = 'LATE'
    raw = pd.concat([raw, late], ignore_index=True)
    timelines = compile_timelines(raw)
    full = {tf: fred_native(calendar, tf, timelines, required_series=('TEST',)) for tf in TIMEFRAMES}
    checks, projections, prefixes, oracle = check_native(full, raw, calendar,
        [pd.Timestamp('2020-01-02'), pd.Timestamp('2020-04-01')])
    assert len(checks) == len(projections) == 22 and len(prefixes) == 44
    assert all(len(c['columns']) == 16 for c in checks)
    assert all(c['all_columns_preserved'] and c['unavailable_series'] == ['LATE'] for c in prefixes)
    assert oracle['future_rows_consumed'] == 0


def test_native_change_windows_count_native_rows_with_unknowns_preserved():
    calendar = pd.bdate_range('2019-01-01', periods=150)
    keys = pd.DataFrame(dict(candle_start=calendar, source_candle_end=calendar,
                             available_from=calendar+pd.Timedelta(days=1)))
    values = np.arange(150, dtype=float)**2; values[100] = np.nan
    levels = pd.DataFrame(dict(fred_test=values, fred_test_first_release=values,
                              fred_test_odays=1., fred_test_vintage_days=1.),
                          index=pd.DatetimeIndex(keys.available_from))
    out = oracle_native(keys, levels)
    assert out.fred_test_change20.iloc[90] == 90.**2-70.**2
    assert np.isnan(out.fred_test_change20.iloc[100]) and np.isnan(out.fred_test_change20.iloc[120])
    assert 'fred_test_odays_change20' not in out


def test_request_retains_all_published_series_and_original_eight_extra_identifiers():
    request = json.loads(Path('ci/FRED_PIT_REQUEST.json').read_text(encoding='utf-8'))
    assert len(request['series']) == len(set(request['series'])) == 21
    assert set(request['required_extra_series']) == {'T10Y3M','T5YIE','T10YIE','STICKCPIM159S','DFII10','CIVPART','INDPRO','BUSLOANS'}
    assert request['parent']['sha256'] == '4e13e4c9d3380b23d217156c83e7d2ee472dafd226b1626e128c06d9c65da643'
    assert len(request['cutoffs']) == 8


@pytest.mark.parametrize('dates', [['2020-03-02','2020-03-02'], ['2020-03-02','2020-03-01']])
def test_oracle_rejects_duplicate_or_unordered_cutoffs(dates):
    with pytest.raises(ValueError): online_levels(source(), pd.to_datetime(dates), ('TEST',))
