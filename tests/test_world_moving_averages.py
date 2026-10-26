import numpy as np
import pytest
from world_moving_averages import extra_moving_averages,wilder_mean
from world_timeframes import parameter_variants
from test_world_bar_statistics import market

def test_registered_sma_range_and_named_ma_periods_are_present():
    args=market()
    out=parameter_variants(*args)
    assert {int(k[3:]) for k in out if k.startswith("SMA") and k[3:].isdigit()}==set(range(5,251))
    for name in ("EMA8","EMA13","EMA20","EMA21","EMA34","EMA55","WMA200","DEMA9","TEMA50","KAMA100","LINEARREG20"):
        assert np.isfinite(out[name][-1]),name

def test_rma_and_mcginley_have_distinct_hand_computed_updates():
    c=np.arange(1,41,dtype=float)
    assert wilder_mean(c,9)[9]==pytest.approx((5*8+10)/9)
    out=extra_moving_averages(c,c+1,c-1,c,c)
    assert out["MCGINLEY9"][8]==5
    assert out["MCGINLEY9"][9]==pytest.approx(5+5/(9*16),rel=1e-6)
    assert out["VWMA9_inf"][8]==pytest.approx(285/45,rel=1e-6)
    assert out["MEDIAN9"][8]==5

def test_hull_average_linear_trend_has_the_analytic_lag():
    c=np.arange(1,320,dtype=float)
    out=extra_moving_averages(c,c+1,c-1,c,c*100)
    assert out["HMA9"][-1]==pytest.approx(c[-1],rel=1e-6)
    assert out["HMA20"][-1]==pytest.approx(c[-1]-2/3,rel=1e-6)

@pytest.mark.parametrize("cut",[81,179,301])
def test_every_named_moving_average_is_prefix_causal(cut):
    args=market();full=extra_moving_averages(*args);short=extra_moving_averages(*(a[:cut] for a in args))
    for key in full:np.testing.assert_allclose(full[key][:cut],short[key],equal_nan=True,rtol=1e-5,atol=1e-6,err_msg=key)
