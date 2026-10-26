import numpy as np
import pandas as pd
import pytest
from price_reconcile import reconcile_one,PRICE

def bars(periods=100):
    dates=pd.bdate_range('2024-08-01',periods=periods);c=np.arange(periods,dtype=float)+100
    return pd.DataFrame(dict(ticker='TEST',date=dates,open=c,high=c+1,low=c-1,close=c,volume=1000.))

def test_matching_quote_basis_is_used_instead_of_extra_dividend_adjustment():
    new=bars();old=new.iloc[:70].copy()
    for c in PRICE:
        new['vendor_'+c]=new[c]
        new[c]*=np.linspace(.5,1,len(new))
    result,report=reconcile_one('TEST',old,new)
    np.testing.assert_array_equal(result.close,bars().close)
    assert report['supplemental_basis']=='vendor_split_adjusted_quote_matching_frozen'

def test_short_history_requires_every_frozen_ohlcv_value_to_match():
    new=bars();old=new.iloc[:7].copy()
    result,report=reconcile_one('TEST',old,new,allow_short_history=True)
    assert len(result)==100 and report['overlap_rows']==7 and report['short_history_all_sessions_exact']
    bad=new.copy();bad.loc[2,'high']+=1
    with pytest.raises(ValueError,match='insufficient overlap'):reconcile_one('TEST',old,bad,allow_short_history=True)
    with pytest.raises(ValueError,match='insufficient overlap'):reconcile_one('TEST',old,new)

def test_later_split_must_explain_price_and_volume_units_before_bridge_acceptance():
    original=bars();old=original.iloc[:70].copy();new=original.copy()
    for c in PRICE:new[c]*=10
    new['volume']/=10
    event=pd.DataFrame(dict(date=['2024-12-01'],kind=['split'],value=[.1]))
    with pytest.raises(ValueError,match='RECONCILIATION_FAIL'):reconcile_one('TEST',old,new)
    result,report=reconcile_one('TEST',old,new,events=event)
    np.testing.assert_allclose(result.close,original.close)
    np.testing.assert_allclose(result.volume,original.volume)
    assert report['volume_normalization_scale']==10 and len(report['split_normalization_events'])==1
    event['value']=.2
    with pytest.raises(ValueError,match='RECONCILIATION_FAIL'):reconcile_one('TEST',old,new,events=event)

def test_actual_zero_volume_is_preserved_and_not_an_invented_liquidity_pass():
    new=bars();new['volume']=0.;old=new.iloc[:70].copy()
    result,report=reconcile_one('TEST',old,new)
    assert report['all_overlap_volumes_zero'] and (result.volume==0).all()
    assert not report['nominal_historical_price_verified']
