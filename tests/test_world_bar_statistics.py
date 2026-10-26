import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from world_bar_statistics import bar_statistics,relative_statistics,universe_rs_rank,wilder_atr

def market(n=360):
    rng=np.random.default_rng(2309)
    c=100*np.exp(np.cumsum(rng.normal(.0005,.02,n)))
    o=np.r_[c[0],c[:-1]]*np.exp(rng.normal(0,.01,n))
    return o,np.maximum(o,c)+1,np.minimum(o,c)-1,c,rng.uniform(100,1000,n)

def test_hv_zscore_and_streak_have_hand_computed_values():
    args=market();out=bar_statistics(*args,"1d");c=args[3]
    assert out["HV20"][-1]==pytest.approx(np.std(np.diff(np.log(c))[-20:],ddof=1)*np.sqrt(252)*100,rel=1e-6)
    assert out["PRICE_ZSCORE20"][-1]==pytest.approx((c[-1]-c[-20:].mean())/c[-20:].std(ddof=0),rel=1e-6)
    c=np.array([10,11,12,12,11,10.],dtype=float)
    out=bar_statistics(c,c+1,c-1,c,c*100,"1d")
    np.testing.assert_equal(out["UP_STREAK"],[np.nan,1,2,0,0,0])
    np.testing.assert_equal(out["DOWN_STREAK"],[np.nan,0,0,0,1,2])

def test_annualization_follows_native_duration():
    args=market();daily=bar_statistics(*args,"1d");five=bar_statistics(*args,"5d");monthly=bar_statistics(*args,"monthly")
    assert five["HV20"][-1]==pytest.approx(daily["HV20"][-1]/np.sqrt(5),rel=1e-6)
    assert monthly["HV20"][-1]==pytest.approx(daily["HV20"][-1]*np.sqrt(12/252),rel=1e-6)

@pytest.mark.parametrize("cut",[65,180,300])
def test_every_new_bar_statistic_is_prefix_causal(cut):
    args=market();full=bar_statistics(*args,"5d");short=bar_statistics(*(a[:cut] for a in args),"5d")
    assert full.keys()==short.keys()
    for key in full:np.testing.assert_allclose(full[key][:cut],short[key],rtol=1e-6,equal_nan=True,err_msg=key)

def test_gap_fill_cohort_matures_only_after_entire_horizon():
    n=90;c=np.full(n,10.);o=c.copy();h=c+1;l=c-1;v=c*100
    o[30]=14;h[30]=15;l[30]=13;c[30]=14
    # The up gap fills the following bar. Its H=5 cohort enters at bar 35,
    # never at bar 30 or bar 31.
    out=bar_statistics(o,h,l,c,v,"1d")
    assert np.isnan(out["GAP_FILL_RATE20_H5"][34])
    assert out["GAP_FILL_RATE20_H5"][35]==1.

def test_relative_statistics_require_matching_intervals_and_keep_roles_distinct():
    n=170;dates=pd.bdate_range("2020-01-01",periods=n)
    b=pd.DataFrame({"candle_start":dates,"date":dates,"close":market(n)[3]})
    a=b.copy();a["close"]*=2
    out=relative_statistics(a,b,"sector")
    assert out["MANSFIELD_sector_60"][-1]==pytest.approx(0,abs=1e-5)
    assert out["BETA_sector_60"][-1]==pytest.approx(1,rel=1e-5)
    assert out["CORRELATION_sector_60"][-1]==pytest.approx(1,rel=1e-5)
    bad=b.copy();bad.loc[0,"candle_start"]-=pd.Timedelta(days=1)
    with pytest.raises(ValueError,match="identical candle boundaries"):relative_statistics(a,bad,"industry")

def test_universe_rank_uses_only_explicitly_eligible_names_and_average_ties():
    close=pd.DataFrame([[10,10,10,10],[11,12,12,20]],columns=list("ABCD"))
    eligible=pd.DataFrame(True,index=close.index,columns=close.columns);eligible.loc[1,"D"]=False
    result=universe_rs_rank(close,eligible,1)
    np.testing.assert_allclose(result.iloc[1],[100/3,250/3,250/3,np.nan],equal_nan=True)

def test_constant_windows_do_not_create_infinite_signals():
    c=np.full(180,10.);out=bar_statistics(c,c,c,c,c,"1d")
    for key in ("PRICE_ZSCORE20","HV_RATIO10_60","LINEARREG_R2_20","HURST_RS20"):
        assert np.isnan(out[key][-1]),key
