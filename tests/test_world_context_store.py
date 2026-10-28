import numpy as np
import pandas as pd
import pytest
from world_context_store import context_row_view,weighted_coverage,validate_factor,checked_weights


def factor():
    return pd.DataFrame(dict(candle_start=pd.to_datetime(['2020-01-01','2020-01-02','2020-01-03']),
        source_candle_end=pd.to_datetime(['2020-01-01','2020-01-02','2020-01-03']),
        available_from=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-06']),
        fred_x=[1.0000000001,np.nan,3.]))


def test_reader_preserves_precision_literal_na_identity_and_missing_intervals():
    dates=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-06'])
    actual=context_row_view('NA',dates,'1d',[factor()])
    assert actual.ticker.tolist()==['NA']*3
    assert actual.fred_x__1d.iloc[0]==1.0000000001
    assert np.isnan(actual.fred_x__1d.iloc[1])  # no forward fill over unknown interval
    assert actual.fred_x__1d.iloc[2]==3.


def test_stock_day_coverage_uses_actual_counts_not_equal_session_weights():
    weights=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-06']),stock_days=[100,1,9]))
    row=weighted_coverage(factor(),weights,'1d','macro')[0]
    assert row['query_stock_days']==110 and row['non_null_stock_days']==109
    assert row['non_null_pct']==100*109/110 and row['non_null_market_sessions']==2
    assert row['first_date']=='2020-01-02' and row['last_date']=='2020-01-06'


def test_future_factor_values_cannot_change_any_earlier_stock_row():
    native=factor();query=pd.to_datetime(['2020-01-02','2020-01-03'])
    before=context_row_view('A',query,'1d',[native])
    native.loc[native.available_from>query[-1],'fred_x']=1e39
    pd.testing.assert_frame_equal(before,context_row_view('A',query,'1d',[native]))
    pd.testing.assert_frame_equal(before,context_row_view('A',query,'1d',[native[native.available_from<=query[-1]]]))


def test_no_observations_is_not_a_wired_zero_feature():
    native=factor();native['fred_x']=np.nan
    weights=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-02']),stock_days=[10]))
    row=weighted_coverage(native,weights,'1d','macro')[0]
    assert row['status']=='NO_OBSERVED_VALUES' and row['non_null_stock_days']==0 and row['first_date']==''


@pytest.mark.parametrize('counts',[[1.5,1,1],[0,1,1],[-1,1,1],[np.nan,1,1]])
def test_bad_denominators_cannot_inflate_full_universe_coverage(counts):
    frame=pd.DataFrame(dict(date=pd.date_range('2020-01-01',periods=3),stock_days=counts))
    with pytest.raises(ValueError,match='positive exact integer'):checked_weights(frame)


def test_execution_prices_non_numeric_columns_or_early_availability_are_rejected():
    native=factor();native['execution_open_reference_units']=1.
    with pytest.raises(ValueError,match='execution-only'):validate_factor(native)
    native=factor();native['headline']='text'
    with pytest.raises(ValueError,match='schema invalid'):validate_factor(native)
    native=factor();native.loc[0,'available_from']=native.source_candle_end.iloc[0]
    with pytest.raises(ValueError,match='availability invalid'):validate_factor(native)


def test_duplicate_names_cannot_overwrite_an_existing_context_factor():
    with pytest.raises(ValueError,match='duplicate context features'):
        context_row_view('A',pd.to_datetime(['2020-01-02']),'1d',[factor(),factor()])


@pytest.mark.parametrize('unit',['ns','us'])
def test_mixed_pandas_date_units_join_without_changing_values(unit):
    native=factor()
    for key in ('candle_start','source_candle_end','available_from'):native[key]=native[key].astype('datetime64['+unit+']')
    actual=context_row_view('NA',pd.DatetimeIndex(['2020-01-02']).as_unit('us'),'1d',[native])
    assert actual.fred_x__1d.iloc[0]==1.0000000001 and str(actual.date.dtype)=='datetime64[ns]'
