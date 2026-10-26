import numpy as np
import pandas as pd
from ci.native_price_base import execution_rows,native_rows
from world_timeframes import TIMEFRAMES,PRICE_COLS

def source_bars():
    dates=pd.bdate_range("2019-01-02",periods=400);close=50+np.arange(len(dates))*.1
    return pd.DataFrame({"ticker":"NA","date":dates,"open":close-1,"high":close+2,"low":close-3,"close":close,"volume":1000+np.arange(len(dates))})

def test_execution_open_is_separate_and_keeps_literal_na_identity():
    bars=source_bars();result=execution_rows(bars)
    assert set(result)=={"ticker","date","execution_open_reference_units"}
    assert set(result.ticker)=={"NA"}
    assert (result.date>=pd.Timestamp("2020-01-01")).all()
    np.testing.assert_array_equal(result.execution_open_reference_units,bars.loc[bars.date>=pd.Timestamp("2020-01-01"),"open"])

def test_all_native_bars_use_completed_intervals_and_true_volume_aggregation():
    bars=source_bars();frame=native_rows(bars,pd.DatetimeIndex(bars.date))
    assert set(frame.timeframe)==set(TIMEFRAMES)
    assert (frame.date<frame.available_from).all()
    row=frame[frame.timeframe=="5d"].iloc[0]
    assert row.open==bars.open.iloc[0]
    assert row.high==bars.high.iloc[:5].max()
    assert row.low==bars.low.iloc[:5].min()
    assert row.close==bars.close.iloc[4]
    assert row.volume==bars.volume.iloc[:5].sum()
    assert "execution_open_reference_units" not in frame

def test_day_d_open_change_cannot_change_any_available_native_price_input():
    bars=source_bars();calendar=pd.DatetimeIndex(bars.date);cut=calendar[320]
    original=native_rows(bars,calendar)
    changed=bars.copy();changed.loc[changed.date>=cut,list(PRICE_COLS)]=1e8
    altered=native_rows(changed,calendar)
    before=original[original.available_from<=cut].reset_index(drop=True)
    after=altered[altered.available_from<=cut].reset_index(drop=True)
    pd.testing.assert_frame_equal(before,after)
    truncated=native_rows(bars[bars.date<cut],calendar[calendar<=cut])
    pd.testing.assert_frame_equal(before,truncated.reset_index(drop=True))
