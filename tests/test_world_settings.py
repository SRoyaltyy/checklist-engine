import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from ci.audit_indicator_settings import audit
from world_indicator_settings import configured_indicators,load_settings,SUPPORTED_IDS
from world_timeframes import completed_candles,candle_features
from test_world_bar_statistics import market

def test_registered_grid_is_explicit_and_preserves_raw_indicators():
    report=audit(Path(__file__).resolve().parents[1])
    assert report["registered_items"]==60
    assert report["registered_settings"]==187
    settings=load_settings()["items"]
    for ident in ("I093","I094","I096"):
        assert settings[ident]["settings"][0]=={"name":"default","kind":"raw","parameters":{}}
    assert settings["I061"]["settings"][1]["parameters"]=={"acceleration":.02,"maximum":.2}

def test_configured_alternates_match_independent_hand_calculations():
    args=market();out=configured_indicators(*args);o,h,l,c,v=args
    assert out["I080_short_value"][-1]==pytest.approx(v[-1]/v[-6:-1].mean(),rel=1e-6)
    assert out["I101_long_upper"][-1]==pytest.approx(h[-56:-1].max(),rel=1e-6)
    assert out["I098_short_mid"][-1]==pytest.approx(c[-10:].mean(),rel=1e-6)
    assert out["I098_short_upper"][-1]==pytest.approx(c[-10:].mean()+1.5*c[-10:].std(ddof=0),rel=1e-6)
    for name in ("I030_short_line","I030_short_signal","I030_short_histogram","I028_long_k","I028_long_d"):
        assert np.isfinite(out[name][-1]),name
    assert set(key.split("_")[0] for key in out)==SUPPORTED_IDS

@pytest.mark.parametrize("cut",[81,179,301])
def test_all_configured_recipes_are_prefix_causal(cut):
    args=market();full=configured_indicators(*args);short=configured_indicators(*(a[:cut] for a in args))
    for key in full:np.testing.assert_allclose(full[key][:cut],short[key],rtol=2e-5,atol=1e-6,equal_nan=True,err_msg=key)

def test_settings_are_recomputed_from_true_five_day_candles():
    import facets_world as fw
    args=market(220);bars=pd.DataFrame(dict(zip(("open","high","low","close","volume"),args)))
    bars["date"]=pd.bdate_range("2020-01-02",periods=len(bars))
    candles=completed_candles(bars,"5d")
    native=candle_features(candles,fw.discover(),timeframe="5d")
    x=candles.close.to_numpy()
    assert native["I098_short_mid"].iloc[-1]==pytest.approx(x[-10:].mean(),rel=1e-6)
    # The last native short Bollinger mean is not the last 10 DAILY prices.
    assert abs(native["I098_short_mid"].iloc[-1]-bars.close.iloc[-10:].mean())>.01

def test_fractal_appears_at_confirmation_not_pivot_date():
    c=np.array([10,11,15,11,10,9,10,11,10,9.],dtype=float)
    out=configured_indicators(c,c+1,c-1,c,c*100)
    a=out["I066_default_confirmed_high"]
    assert np.isnan(a[2])
    assert a[4]==16
