import numpy as np
import pytest
from world_moving_averages import extra_moving_averages,wilder_mean,hull_mean,mcginley_mean
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


def test_finite_talib_values_are_not_overflowed_by_float32_storage():
    import facets_world as fw
    c=np.full(40,100.,dtype=float)
    out=fw.compute_talib(c,c+1,c-1,c,c,{"EXP":("indicator",["close"])})
    assert np.isfinite(out["EXP"]).all()
    assert out["EXP"][-1]==pytest.approx(np.exp(100),rel=1e-12)


def test_talib_column_dtype_is_fixed_across_stocks_with_different_ranges():
    import facets_world as fw
    funcs={"EXP":("indicator",["close"]),"SMA":("indicator",["close"]),"CDLDOJI":("pattern",["open","high","low","close"])}
    results=[]
    for level in (1.,100.):
        c=np.full(50,level);results.append(fw.compute_talib(c,c+1,c-1,c,c,funcs))
    assert results[0].keys()==results[1].keys()
    for column in results[0]:
        expected=np.dtype("float32" if column=="CDLDOJI" else "float64")
        assert results[0][column].dtype==results[1][column].dtype==expected


def test_mcginley_reseeds_after_missing_bars_and_leading_warmup():
    c=np.r_[np.full(4,np.nan),np.full(20,100.),np.nan,np.full(20,200.)]
    out=mcginley_mean(c,9)
    assert np.isnan(out[:12]).all() and out[12]==100
    assert np.isnan(out[24:33]).all() and out[33]==200
    assert np.isfinite(out[33:]).all()
    for cut in (13,25,33,40):np.testing.assert_equal(out[:cut],mcginley_mean(c[:cut],9))
    generated=extra_moving_averages(c,c+1,c-1,c,np.ones(len(c)))
    np.testing.assert_equal(generated["MCGINLEY9"],out)


def test_hull_root_rounding_changes_a_period_where_floor_is_different():
    # n=8: half=4, round(sqrt(8))=3. On x[t]=t+1 the hand WMA
    # identity gives x - 1/3; the old floor-root=2 incorrectly gives x.
    c=np.arange(1,80,dtype=float);out=hull_mean(c,8)
    assert np.isnan(out[:9]).all()
    assert out[-1]==pytest.approx(c[-1]-1/3,rel=1e-13)
    assert out[-1]!=pytest.approx(c[-1],rel=1e-13)


def test_named_average_storage_preserves_finite_values_above_float32_range():
    c=np.full(300,1e39);v=np.ones(len(c))
    means=extra_moving_averages(c,c*1.01,c*.99,c,v)
    variants=parameter_variants(c,c*1.01,c*.99,c,v)
    columns=("RMA9","HMA9","ALMA9_0p85_6","VWMA9_inf","MCGINLEY9","MEDIAN9")
    for key in columns:
        assert means[key].dtype==np.dtype("float64") and np.isfinite(means[key][-1]),key
        assert means[key][-1]==pytest.approx(1e39,rel=1e-12),key
    for key in ("SMA5","SMA250","EMA8","WMA20","DEMA20","TEMA20","KAMA20","LINEARREG20","BBANDS20_mid"):
        assert variants[key].dtype==np.dtype("float64") and np.isfinite(variants[key][-1]),key
        assert variants[key][-1]==pytest.approx(1e39,rel=1e-12),key


def test_box_1_08_sma_on_buy_date_matches_hand_mean_excluding_day_d():
    import pandas as pd
    from world_timeframes import completed_candles,align_features,PRICE_COLS
    dates=pd.bdate_range("2020-01-02",periods=8)
    c=np.array([2.,4.,8.,16.,32.,1000.,2000.,4000.])
    bars=pd.DataFrame(dict(date=dates,open=c,high=c+1,low=c-1,close=c,volume=np.ones(8)))
    def on_buy_date(source):
        candles=completed_candles(source,"1d",session_calendar=dates)
        values=parameter_variants(*(candles[key].to_numpy(float) for key in PRICE_COLS))
        features=pd.DataFrame({"available_from":candles.available_from,"SMA5":values["SMA5"]})
        return align_features([dates[5]],features,"1d").iloc[0].SMA5__1d
    # D is the sixth session; only the five prior closes enter the average.
    expected=(2+4+8+16+32)/5
    assert on_buy_date(bars)==pytest.approx(expected,rel=1e-14)
    changed=bars.copy();changed.loc[changed.date>=dates[5],list(PRICE_COLS)]=1e20
    assert on_buy_date(changed)==pytest.approx(expected,rel=1e-14)
    assert on_buy_date(bars[bars.date<dates[5]])==pytest.approx(expected,rel=1e-14)


def test_corrected_math_recipe_cannot_accept_old_checkpoint_fingerprint():
    from ci.native_price_blocks import recipe_fingerprint,validate_shard
    from test_world_native_blocks import complete_shard
    from world_moving_averages import MATH_RECIPE_VERSION
    fingerprint,_=recipe_fingerprint()
    old="0738f12902e29f1272d06f30fdd56d6f80e200bc25f825cf9a737404acdffcc4"
    assert MATH_RECIPE_VERSION==2 and fingerprint!=old
    summary,inputs=complete_shard();summary["recipe_fingerprint"]=old;inputs["recipe_fingerprint"]=fingerprint
    with pytest.raises(ValueError,match="recipe differs"):validate_shard(summary,inputs,0)
