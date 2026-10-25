import numpy as np
import pandas as pd
import pytest
from price_reconcile import reconcile_one
from world_dates import date_ns,normalize_dates
from unittest.mock import patch


def fixture():
    c=50+np.arange(140)*.05+np.sin(np.arange(140))*.1
    new=pd.DataFrame(dict(ticker='TEST',date=pd.bdate_range('2024-08-01',periods=140),
        open=c,high=c+1,low=c-1,close=c,volume=1000.))
    old=new.iloc[20:110].copy()
    old[['open','high','low','close']]*=3
    return old,new


def test_preserves_frozen_prices_and_extends_both_ends():
    old,new=fixture();out,report=reconcile_one('TEST',old,new)
    np.testing.assert_allclose(out.close,new.close*3)
    assert report['warmup_rows']==20 and report['extension_rows']==30
    assert report['frozen_values_unchanged']
    assert not report['nominal_historical_price_verified']


@pytest.mark.parametrize('change',['returns','volume'])
def test_rejects_incompatible_price_or_volume_history(change):
    old,new=fixture()
    if change=='returns':new.loc[new.index%2==0,'close']*=2
    else:new.volume*=100
    with pytest.raises(ValueError,match='RECONCILIATION_FAIL'):reconcile_one('TEST',old,new)


def test_date_helper_normalizes_arrow_microseconds_and_join_inputs():
    from facets_world import earn_for
    source=pd.DataFrame(dict(report_date=pd.to_datetime(['2024-11-01']).astype('datetime64[us]'),
        amc=[1.],surprise_pct_fill=[5.],eps_delta=[.1]))
    assert str(normalize_dates(source).report_date.dtype)=='datetime64[ns]'
    assert str(date_ns(pd.date_range('2020-01-01',periods=1).as_unit('us')).dtype)=='datetime64[ns]'
    out=earn_for(pd.to_datetime(['2024-11-04']).as_unit('us'),source)
    assert out.earn_surp.iloc[0]==5.


def test_earnings_does_not_claim_coverage_after_calendar_ends():
    from facets_world import earn_for
    source=pd.DataFrame(dict(report_date=pd.to_datetime(['2024-11-01']),coverage_end=pd.to_datetime(['2024-12-31']),
        amc=[1.],surprise_pct_fill=[5.],eps_delta=[.1]))
    out=earn_for(pd.to_datetime(['2024-12-31','2025-01-02']),source)
    assert out.earn_surp.iloc[0]==5.
    assert pd.isna(out.earn_surp.iloc[1])


def test_sec_403_retries_before_reporting_blocked():
    import urllib.error
    from fetch.fetch_xbrl import get_json
    err=urllib.error.HTTPError('x',403,'blocked',None,None)
    with patch('urllib.request.urlopen',side_effect=err) as request,patch('time.sleep'):
        with pytest.raises(urllib.error.HTTPError):get_json('https://data.sec.gov/blocked')
        assert request.call_count==4


def test_fred_paginates_all_vintage_versions():
    from fetch.fetch_fred import alfred_observations
    observations=[dict(date='2020-01-01',realtime_start=d,value=str(i)) for i,d in enumerate(['2020-02-01','2020-03-01','2020-04-01'])]
    with patch('fetch.fetch_fred.alfred_page',side_effect=[dict(count=3,observations=observations[:2]),dict(count=3,observations=observations[2:])]) as request,patch('time.sleep'):
        out=alfred_observations('test-key','TEST',limit=2,start_year=2020,end_year=2020)
    assert len(out)==3 and out[-1]['vintage_date']=='2020-04-01'
    assert request.call_args_list[1].args[2]==2


def test_fred_errors_never_expose_key():
    import urllib.error
    from fetch.fetch_fred import alfred_page
    err=urllib.error.HTTPError('https://example/?api_key=private-test',400,'private-test',None,None)
    with patch('urllib.request.urlopen',side_effect=err):
        with pytest.raises(RuntimeError) as caught:alfred_page('private-test','TEST',0,10,'2020-01-01','2020-12-31')
    assert 'private-test' not in str(caught.value)


def test_daily_breadth_stops_when_feed_stops():
    import facets_world as fw
    dates=pd.bdate_range('2024-12-27',periods=5)
    b=pd.DataFrame(dict(date=dates,open=10.,high=11.,low=9.,close=10.,volume=1000.))
    breadth=pd.DataFrame(dict(date=dates[:2].as_unit('us'),test_breadth=[1.,2.]))
    out=fw.ticker_frame('TEST',b,{},None,breadth,None)
    np.testing.assert_equal(out.test_breadth.to_numpy(),[np.nan,1.,2.,np.nan,np.nan])


def test_peer_return_does_not_carry_a_stale_daily_return():
    import facets_world as fw
    dates=pd.bdate_range('2024-12-27',periods=6)
    b=pd.DataFrame(dict(close=[10.,11.,12.,13.,14.,15.]))
    peers=fw.Peers({'TEST':0},pd.DataFrame(dict(date=dates[:2],peer_cret_0=[.01,.02])),
        dict(cluster_n={'0':20},formation_year=2020,corr_thresh=.5,usable_from='2021-01-01'))
    out=fw.peer_columns(dates,b,peers,0)
    np.testing.assert_allclose(out['peer_r1'],[np.nan,.01,.02,np.nan,np.nan,np.nan],equal_nan=True)


def test_fred_splits_vintage_ranges_below_json_limit():
    from fetch.fetch_fred import alfred_observations
    with patch('fetch.fetch_fred.alfred_page',return_value=dict(count=0,observations=[])) as request,patch('time.sleep'):
        assert alfred_observations('test-key','TEST',as_of='2026-12-31')==[]
    assert request.call_count==9
    assert request.call_args_list[0].args[4:] == ('2018-01-01','2018-12-31')
    assert request.call_args_list[-1].args[4:] == ('2026-01-01','2026-12-31')


def test_fred_current_vintage_interval_ends_today():
    from fetch.fetch_fred import alfred_observations
    with patch('fetch.fetch_fred.alfred_page',return_value=dict(count=0,observations=[])) as request,patch('time.sleep'):
        alfred_observations('test-key','TEST',start_year=2026,end_year=2027,as_of='2026-10-25')
    assert request.call_count==1
    assert request.call_args.args[4:]==('2026-01-01','2026-10-25')
