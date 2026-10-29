import numpy as np
import pandas as pd

from ci.renko_diagnostic import diagnose


def test_flat_tail_with_decaying_positive_atr_exposes_a_nonadvancing_float_step():
    dates=pd.bdate_range('2020-01-01',periods=700)
    bars=pd.DataFrame(dict(date=dates,close=37.,high=37.,low=37.))
    bars.loc[:20,'high']=38.;bars.loc[:20,'low']=36.
    report=diagnose(bars)
    problem=report['first_problem']
    assert problem['reason']=='FLOAT_STEP_CANNOT_ADVANCE'
    assert problem['close']==problem['last_brick']==problem['next_brick']==37.
    assert 0<problem['atr14']<abs(np.spacing(37.))/2
    assert report['exact_probe_brick_steps']==0 and report['replacement_numeric_values'] is False


def test_exact_zero_atr_has_no_brick_or_nontermination():
    bars=pd.DataFrame(dict(date=pd.bdate_range('2020-01-01',periods=100),close=37.,high=37.,low=37.))
    report=diagnose(bars)
    assert report['first_problem'] is None and report['exact_probe_brick_steps']==0


def test_large_but_advancing_loop_stops_at_the_explicit_probe_bound():
    close=np.arange(100,dtype='float64')+10
    bars=pd.DataFrame(dict(date=pd.bdate_range('2020-01-01',periods=100),close=close,high=close+1,low=close-1))
    report=diagnose(bars,limit=1)
    assert report['exact_probe_brick_steps']==1
    assert report['first_problem']['reason']=='BOUNDED_STEP_PROBE_LIMIT'
