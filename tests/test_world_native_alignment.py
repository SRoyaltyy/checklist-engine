import numpy as np
import pandas as pd
import pytest
from world_timeframes import completed_candles,candle_features
from world_food_statistics import additional_bar_statistics,regression_statistics,peer_correlations
from test_world_bar_statistics import market

def test_global_candles_align_entities_with_different_listing_dates():
    dates=pd.bdate_range("2020-01-02",periods=22)
    def frame(ds):
        c=np.arange(len(ds),dtype=float)+20
        return pd.DataFrame(dict(date=ds,open=c,high=c+1,low=c-1,close=c,volume=c*100))
    older=completed_candles(frame(dates),"5d",session_calendar=dates)
    newer=completed_candles(frame(dates[3:]),"5d",session_calendar=dates)
    # The first partial IPO bucket is omitted; later boundaries match exactly.
    pd.testing.assert_frame_equal(older[["candle_start","date","available_from"]].iloc[1:].reset_index(drop=True),
                                  newer[["candle_start","date","available_from"]])
    assert newer.iloc[0].candle_start==dates[5]
    assert newer.iloc[0].available_from==dates[10]

def test_global_calendar_rejects_unknown_dates_and_omits_halt_buckets():
    ds=pd.bdate_range("2020-01-02",periods=22);c=np.arange(22,dtype=float)+20
    b=pd.DataFrame(dict(date=ds,open=c,high=c+1,low=c-1,close=c,volume=c*100))
    missing=b.drop(index=6)
    candles=completed_candles(missing,"5d",session_calendar=ds)
    assert ds[9] not in set(candles.date)
    with pytest.raises(ValueError,match="outside"):completed_candles(b,"5d",session_calendar=ds[1:])

def test_global_monthly_needs_a_whole_completed_month():
    ds=pd.bdate_range("2020-01-02","2020-04-10");c=np.ones(len(ds))*20
    b=pd.DataFrame(dict(date=ds,open=c,high=c+1,low=c-1,close=c,volume=c*100))
    result=completed_candles(b.iloc[5:],"monthly",session_calendar=ds)
    assert list(result.date.dt.month)==[2,3]  # partial IPO January and partial April omitted

def test_regression_parameters_and_errors_have_known_linear_values():
    y=3+2*np.arange(150,dtype=float)
    out=regression_statistics(y,20)
    assert out["slope"][-1]==pytest.approx(2)
    assert out["intercept"][-1]==pytest.approx(3+2*130)
    assert out["residual_standard_error"][-1]==pytest.approx(0,abs=1e-12)
    assert np.isnan(out["slope"][:19]).all()

def test_twiggs_balanced_flow_is_zero_and_starc_mid_is_a_hand_mean():
    c=np.full(200,10.);v=np.full(200,100.)
    out=additional_bar_statistics(c,c+1,c-1,c,v)
    assert out["I222_default_value"][-1]==0
    assert out["I223_default_mid"][-1]==10
    assert out["I223_default_upper"][-1]==14
    assert out["I223_default_lower"][-1]==6

@pytest.mark.parametrize("cut",[81,179,300])
def test_additional_statistics_and_global_candles_are_prefix_causal(cut):
    args=market();full=additional_bar_statistics(*args);short=additional_bar_statistics(*(a[:cut] for a in args))
    for key in full:np.testing.assert_allclose(full[key][:cut],short[key],equal_nan=True,rtol=1e-5,atol=1e-6,err_msg=key)
    dates=pd.bdate_range("2020-01-02",periods=len(args[0]))
    b=pd.DataFrame(dict(zip(("open","high","low","close","volume"),args)));b["date"]=dates
    for tf in ("1d","5d","21d","monthly"):
        a=completed_candles(b,tf,session_calendar=dates)
        z=completed_candles(b.iloc[:cut],tf,session_calendar=dates)
        # A supplied calendar can name future availability, but cannot invent
        # an OHLC value for an incomplete interval.
        pd.testing.assert_frame_equal(a[a.available_from<=dates[cut-1]].reset_index(drop=True),
                                      z[z.available_from<=dates[cut-1]].reset_index(drop=True))

def test_peer_correlations_require_explicit_membership_and_exclude_self():
    rng=np.random.default_rng(1);x=rng.normal(size=100)
    r=pd.DataFrame({"A":x,"B":2*x,"C":-x})
    membership=pd.DataFrame({"B":True,"C":True},index=r.index);membership.loc[99,"C"]=False
    result=peer_correlations(r,"A",membership,20)
    assert result.B.iloc[-1]==pytest.approx(1)
    assert result.C.iloc[-2]==pytest.approx(-1)
    assert np.isnan(result.C.iloc[-1])
    membership["A"]=True
    with pytest.raises(ValueError,match="self"):peer_correlations(r,"A",membership,20)
