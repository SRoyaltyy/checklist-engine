import json
import urllib.error
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
import facets_world as fw
from world_timeframes import completed_candles,world_timeframes,TIMEFRAMES
from fetch.fetch_xbrl import get_json,company_rows,add_yoy


def bars(n=960):
    rng=np.random.default_rng(217)
    c=50+np.cumsum(rng.normal(.02,.3,n))
    return pd.DataFrame(dict(date=pd.bdate_range('2019-01-02',periods=n),
        open=c,high=c+1,low=c-1,close=c+.1,volume=rng.uniform(1000,2000,n)))


def test_real_talib_grouped_inputs_and_outputs():
    funcs=fw.discover()
    assert sum(v[0]=='pattern' for v in funcs.values())==61
    assert len(funcs)>=157
    b=bars(320)
    out=fw.compute_talib(*(b[x].to_numpy(float) for x in ('open','high','low','close','volume')),funcs)
    assert len([c for c in out if c.startswith('CDL')])==61
    assert all(c in out for c in ('MACD_macd','MACD_macdsignal','MACD_macdhist','AD','OBV'))
    assert all(v.shape==(320,) for v in out.values())


def test_function_failure_stops_build():
    b=bars(80)
    with patch.object(fw.abstract,'Function',side_effect=RuntimeError('broken')):
        with pytest.raises(RuntimeError,match='refusing partial snapshot'):
            fw.compute_talib(*(b[x].to_numpy(float) for x in ('open','high','low','close','volume')),{'RSI':('indicator',['close'])})


def test_five_session_candle_and_availability():
    b=bars(13)
    c=completed_candles(b,'5d')
    assert len(c)==2
    assert c.iloc[0].available_from==b.date.iloc[5]
    assert c.iloc[0].high==b.high.iloc[:5].max()
    assert c.iloc[0].volume==pytest.approx(b.volume.iloc[:5].sum(),rel=1e-14,abs=1e-10)
    assert c.iloc[0].close==b.close.iloc[4]


def test_monthly_is_calendar_not_daily_proxy():
    b=bars(80)
    c=completed_candles(b,'monthly')
    jan=b[b.date.dt.month==1]
    first=c.iloc[0]
    assert first.available_from==pd.Timestamp('2019-02-01')
    assert first.high==jan.high.max()
    assert first.volume==pytest.approx(jan.volume.sum(),rel=1e-14,abs=1e-10)


@pytest.mark.parametrize('cut',[260,519,800])
def test_all_timeframes_all_columns_future_truncation(cut):
    b=bars()
    funcs=fw.discover()
    full=world_timeframes(b,funcs).iloc[cut]
    truncated=world_timeframes(b.iloc[:cut+1],funcs).iloc[-1]
    assert set(full.index)==set(truncated.index)
    pd.testing.assert_series_equal(full,truncated,check_names=False,rtol=1e-6)
    spike=b.iloc[:cut+1].copy()
    spike.loc[spike.index[-1],['open','high','low','close','volume']]*=1000
    altered=world_timeframes(spike,funcs).iloc[-1]
    pd.testing.assert_series_equal(truncated,altered,check_names=False,rtol=1e-6)
    assert all(any(c.endswith('__'+tf) for c in full.index) for tf in TIMEFRAMES)


def test_xbrl_404_is_skip_but_403_is_error(monkeypatch):
    monkeypatch.setenv('PRIMARY_ACTION_RELAY_URL','https://unit-test-relay.example/')
    with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('x',404,'missing',None,None)):
        assert get_json('https://data.sec.gov/missing',allow_404=True) is None
    with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('x',403,'blocked',None,None)):
        with pytest.raises(urllib.error.HTTPError):get_json('https://data.sec.gov/blocked',allow_404=True)


def test_xbrl_keeps_filing_versions_and_prior_yoy_is_pit():
    def item(end,filed,val,accn):
        return dict(start=end[:4]+'-01-01',end=end,filed=filed,val=val,accn=accn,form='10-K')
    payload={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[
        item('2019-12-31','2020-02-01',100,'a'),
        item('2020-12-31','2021-02-01',120,'b'),
        item('2019-12-31','2022-02-01',200,'c')]}}}}}
    rows=company_rows('TEST',payload)
    assert len(rows)==3
    result=add_yoy(pd.DataFrame(rows))
    assert result[result.accn=='b'].iloc[0].yoy==pytest.approx(.2)


def test_fred_old_period_revision_does_not_replace_latest_observation():
    source=pd.DataFrame(dict(series=['TEST']*3,obs_date=pd.to_datetime(['2020-01-01','2020-02-01','2020-01-01']),
        vintage_date=pd.to_datetime(['2020-02-01','2020-03-01','2020-04-01']),value=[1.,2.,9.]))
    out=fw.fred_columns(pd.to_datetime(['2020-03-01','2020-03-02','2020-04-02']),source)
    np.testing.assert_equal(out['fred_test'],[1.,2.,2.])


def test_zero_mention_news_series_is_not_a_crash():
    source=pd.DataFrame(dict(date=pd.date_range('2020-01-01',periods=10),n=np.zeros(10)))
    out=fw.gd_columns(pd.to_datetime(['2020-01-10']),source)
    assert out['gd_n7'][0]==0
    assert np.isnan(out['gd_days'][0])


def test_measurement_counts_absent_columns_in_total_denominator(tmp_path):
    from ci.world_v2_coverage import measure
    a=tmp_path/'a.parquet';b=tmp_path/'b.parquet'
    pd.DataFrame(dict(ticker=['A'],date=pd.to_datetime(['2026-01-02']),x__1d=[1.])).to_parquet(a,index=False)
    pd.DataFrame(dict(ticker=['B'],date=pd.to_datetime(['2026-01-05']),y__1d=[2.])).to_parquet(b,index=False)
    measured=measure([a,b])
    assert measured['columns']['x__1d']['non_null_pct']==50
    assert measured['columns']['x__1d']['first_date']=='2026-01-02'


def test_gate_rejects_partially_missing_multi_output_item(tmp_path,monkeypatch):
    import ci.world_v2_coverage as gate
    (tmp_path/'dictionary').mkdir();(tmp_path/'docs').mkdir()
    (tmp_path/'dictionary/DATA_SOURCES.csv').write_text('id,item,block\nI999,Example,A\n')
    (tmp_path/'docs/TV_COVERAGE.csv').write_text('item_id,item,block,status,reason\n')
    monkeypatch.setattr(gate,'mappings',lambda:({'I999':dict(status='WIRED',snapshot_columns='x|missing')},{}))
    measured=dict(rows=10,date_max='2026-10-01',columns={'x__'+tf:dict(non_null_rows=10,non_null_pct=100.,first_date='2020-01-01') for tf in TIMEFRAMES})
    rows,failures=gate.build(measured,root=tmp_path)
    assert len(failures)==len(TIMEFRAMES)
    assert all(r['status']=='PENDING' for r in rows)


def test_external_fields_with_microsecond_dates_align_on_all_timeframes():
    b=bars(100)
    external=pd.DataFrame(dict(date=b.date.astype('datetime64[us]'),mkt_vix=np.arange(len(b),dtype=float)))
    result=world_timeframes(b,fw.discover(),external)
    assert 'mkt_vix__monthly' in result
    assert result['mkt_vix__5d'].iloc[5]==5


def test_earnings_same_day_preserves_previous_known_report_and_precision():
    source=pd.DataFrame(dict(report_date=pd.to_datetime(['2020-01-01','2020-02-01']).astype('datetime64[us]'),
        amc=[1.,0.],surprise_pct_fill=[10.,20.],eps_delta=[.1,.2]))
    out=fw.earn_for(pd.to_datetime(['2020-02-01','2020-02-02']),source)
    np.testing.assert_equal(out.earn_surp.to_numpy(),[10.,20.])


def test_named_band_stochastic_periods_and_pattern_warmup():
    from world_timeframes import parameter_variants
    b=bars(80)
    a=[b[c].to_numpy(float) for c in ('open','high','low','close','volume')]
    variants=parameter_variants(*a)
    np.testing.assert_allclose(variants['BBANDS20_mid'],b.close.rolling(20).mean(),rtol=1e-6,equal_nan=True)
    import talib
    sk,sd=talib.STOCH(a[1],a[2],a[3],fastk_period=14,slowk_period=3,slowd_period=3)
    np.testing.assert_allclose(variants['STOCH14_3_3_k'],sk,rtol=1e-6,equal_nan=True)
    values=fw.compute_talib(*a,fw.discover())
    lookback=fw.abstract.Function('CDLDOJI').lookback
    assert np.isnan(values['CDLDOJI'][:lookback]).all()


def test_supplemental_prices_preserve_quote_and_adjusted_bases():
    from fetch.fetch_world_prices import chart_rows
    payload={'chart':{'result':[{'timestamp':[1735830000,1735916400],
        'indicators':{'quote':[{'open':[90,100],'high':[110,120],'low':[80,90],'close':[100,110],'volume':[1000,2000]}],
                      'adjclose':[{'adjclose':[50,55]}]},'events':{}}]}}
    frame,events=chart_rows('TEST',payload)
    np.testing.assert_equal(frame.vendor_close.to_numpy(),[100,110])
    np.testing.assert_equal(frame.close.to_numpy(),[50,55])
    np.testing.assert_equal(frame.open.to_numpy(),[45,50])
    assert events.empty


def test_missing_adjusted_series_is_a_source_failure():
    from fetch.fetch_world_prices import chart_rows
    payload={'chart':{'result':[{'timestamp':[1735830000],'indicators':{'quote':[{'close':[100]}]}}]}}
    with pytest.raises(ValueError,match='adjusted-close'):chart_rows('TEST',payload)


def test_kagi_initial_state_never_reads_the_second_close():
    full=fw.kagi_direction([10.,12.,11.,9.,10.])
    assert np.isnan(full[0])
    for length in range(1,6):
        np.testing.assert_equal(fw.kagi_direction([10.,12.,11.,9.,10.][:length]),full[:length])
    assert full[1]==1


def test_vendor_coarse_bars_cannot_pass_as_daily_prices():
    from fetch.fetch_world_prices import chart_rows
    payload={'chart':{'result':[{'meta':{'dataGranularity':'3mo'},'timestamp':[],
        'indicators':{'quote':[{}],'adjclose':[{}]}}]}}
    with pytest.raises(ValueError,match='non-daily'):chart_rows('TEST',payload)
