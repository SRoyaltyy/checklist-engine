import numpy as np
import pandas as pd
import pytest
from world_fred import compile_timelines,columns

def source():
    return pd.DataFrame(dict(series=['TEST']*5,obs_date=pd.to_datetime(['2020-01-01','2020-02-01','2020-02-01','2020-01-01','2020-03-01']),vintage_date=pd.to_datetime(['2020-02-01','2020-03-01','2020-03-10','2020-04-01','2020-04-10']),value=[1.,2.,3.,99.,4.]))

def test_old_period_revision_never_replaces_latest_period_and_first_release_is_stable():
    out=columns(pd.to_datetime(['2020-02-01','2020-03-01','2020-03-02','2020-03-11','2020-04-02','2020-04-11']),compile_timelines(source()))
    np.testing.assert_equal(out['fred_test'],[np.nan,1.,2.,3.,3.,4.])
    np.testing.assert_equal(out['fred_test_first_release'],[np.nan,1.,2.,2.,2.,4.])

def test_independent_future_cut_recompile_matches_full_timeline_prefix():
    frame=source();dates=pd.to_datetime(['2020-03-11','2020-04-02'])
    full=columns(dates,compile_timelines(frame))
    for i,day in enumerate(dates):
        independent=columns(pd.to_datetime([day]),compile_timelines(frame[frame.vintage_date<day]))
        for key in full:np.testing.assert_equal(independent[key][0],full[key][i])

def test_conflicting_values_at_one_vintage_fail_loudly():
    frame=source();conflict=frame.iloc[[0]].copy();conflict['value']=9.
    with pytest.raises(ValueError,match='Conflicting'):compile_timelines(pd.concat([frame,conflict],ignore_index=True))

def test_future_observation_period_is_not_visible_early():
    frame=source().iloc[:1].copy();frame['obs_date']=pd.Timestamp('2030-01-01')
    assert compile_timelines(frame)=={}


def test_macro_change_window_counts_native_candles(monkeypatch):
    import world_timeframes as tf
    monkeypatch.setattr(tf,'TIMEFRAMES',('2d',))
    monkeypatch.setattr(tf,'candle_features',lambda candles,funcs:candles[['available_from']].copy())
    dates=pd.bdate_range('2020-01-01',periods=150)
    bars=pd.DataFrame(dict(date=dates,open=1.,high=1.,low=1.,close=1.,volume=1.))
    external=pd.DataFrame(dict(date=dates,fred_test=np.r_[np.nan,np.arange(149,dtype=float)**2]))
    result=tf.world_timeframes(bars,{},external)
    assert np.isnan(result.loc[40,'fred_test_change20__2d'])
    assert result.loc[42,'fred_test_change20__2d']==41.**2-1.**2
    assert result.loc[42,'fred_test_change20__2d']!=41.**2-21.**2


def test_narrow_output_retains_full_native_candle_warmup(monkeypatch):
    import world_timeframes as tf
    monkeypatch.setattr(tf,'TIMEFRAMES',('2d','3d'))
    def features(candles,funcs):
        out=candles[['available_from']].copy()
        out['MEAN5']=candles.close.rolling(5).mean().to_numpy()
        return out
    monkeypatch.setattr(tf,'candle_features',features)
    dates=pd.bdate_range('2019-10-01',periods=150);price=np.arange(150,dtype=float)+1
    bars=pd.DataFrame(dict(date=dates,open=price,high=price,low=price,close=price,volume=1.))
    full=tf.world_timeframes(bars,{})
    narrow=tf.world_timeframes(bars,{},query_start='2020-01-01')
    pd.testing.assert_frame_equal(narrow.reset_index(drop=True),full[full.date>='2020-01-01'].reset_index(drop=True))
    assert not narrow[['MEAN5__2d','MEAN5__3d']].iloc[0].isna().any()
