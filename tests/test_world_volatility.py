import numpy as np
import pandas as pd
import pytest
from world_context_native import native_intervals
from world_context_store import context_row_view
from world_volatility import term_native


def source():
    frame=native_intervals(pd.bdate_range('2020-01-02',periods=7),'1d')
    frame['cboe_vix_close']=[10.,np.nan,0.,20.,25.,30.]
    frame['cboe_vix9d_close']=[5.,5.,0.,10.,10.,15.]
    frame['cboe_vix3m_close']=[20.,20.,0.,40.,50.,60.]
    return frame


def test_missing_native_row_remains_unknown_in_an_asof_stock_day_view():
    native=term_native(source())
    assert len(native)==6 and native.vol_vix_over_vix3m.iloc[0]==.5
    queries=pd.DatetimeIndex(native.available_from.iloc[:3])
    attached=context_row_view('TEST',queries,'1d',[native])
    assert attached.vol_vix_over_vix3m__1d.iloc[0]==.5
    assert np.isnan(attached.vol_vix_over_vix3m__1d.iloc[1])
    assert np.isnan(attached.vol_vix_over_vix3m__1d.iloc[2])
    assert native.vol_vix9d_over_vix3m.iloc[1]==.25


def test_infinite_and_zero_difference_outcomes_remain_distinct_from_missing():
    frame=source();frame.loc[0,'cboe_vix3m_close']=0.
    native=term_native(frame)
    assert np.isposinf(native.vol_vix_over_vix3m.iloc[0])
    assert native.vol_vix3m_minus_vix.iloc[2]==0.
    assert np.isnan(native.vol_vix_over_vix3m.iloc[2])


@pytest.mark.parametrize('mutation',['missing','precision'])
def test_unregistered_or_reduced_precision_source_is_rejected(mutation):
    frame=source()
    if mutation=='missing':frame=frame.drop(columns='cboe_vix_close')
    else:frame['cboe_vix_close']=frame.cboe_vix_close.astype('float32')
    with pytest.raises(ValueError,match='float64 CBOE close'):term_native(frame)


def test_future_rows_cannot_change_any_prior_ratio_bit():
    frame=source();full=term_native(frame)
    earlier=term_native(frame.iloc[:3].copy())
    pd.testing.assert_frame_equal(earlier,full.iloc[:3],check_exact=True)
