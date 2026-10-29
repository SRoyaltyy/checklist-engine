from dataclasses import asdict,replace

import numpy as np
import pandas as pd
import pytest

from world_chart_picture import ChartSettings,DEFAULT,MINIMUM_BARS,_wilder,chart_metrics,chart_tags,hard_gate_mask,native_chart_picture


def arrays(n=100):
    c=100+np.arange(n)*.04+np.sin(np.arange(n)/3)
    o=c+np.where(np.arange(n)%2,.3,-.4)
    return o,np.maximum(o,c)+1,np.minimum(o,c)-1,c,1000+np.arange(n)%7


def test_wilder_seed_uses_first_n_true_ranges_and_then_wilder_not_sma():
    np.testing.assert_equal(_wilder(np.array([2.,4.,8.,16.]),2),[np.nan,3.,5.5,10.75])
    np.testing.assert_equal(_wilder(np.array([2.,4.,np.nan,8.,16.]),2),[np.nan,3.,np.nan,np.nan,np.nan])
    np.testing.assert_equal(_wilder(np.array([np.nan,2.,4.,8.]),2),[np.nan,np.nan,3.,5.5])


def test_minimum60_warmup_is_blank_and_blank_never_passes_hard_gate():
    metrics=chart_metrics(*arrays());tags=chart_tags(metrics)
    assert metrics.iloc[:59].isna().all().all() and tags.iloc[:59].isna().all().all()
    assert not hard_gate_mask(tags)[:59].any() and metrics.iloc[59].notna().any()
    assert all(dtype==np.float64 for dtype in metrics.dtypes) and all(dtype==np.float64 for dtype in tags.dtypes)


def test_body_ratio_uses_absolute_price_bodies_and_red_green_volume_is_separate():
    o=np.tile([10.,100.],40);c=o+np.tile([1.,-2.],40)
    m=chart_metrics(o,np.maximum(o,c)+1,np.minimum(o,c)-1,c,np.tile([100.,300.],40))
    assert m.green_red_body_ratio_inf.iloc[-1]==.5
    assert m.red_green_volume_ratio_inf.iloc[-1]==3.
    tags=chart_tags(m);assert tags.cp_gr_body20.iloc[-1]==0 and tags.cp_redgreen_vol10.iloc[-1]==1


def test_most_recent_high_tie_and_exact_pre_high_low_and_drawdown_intervals():
    o=c=np.full(80,4.);h=np.full(80,5.);l=np.full(80,3.);h[[60,70]]=10.;l[65]=2.;l[75]=1.
    m=chart_metrics(o,h,l,c,np.ones(80))
    row=m.iloc[-1]
    assert row.high_age==9 and row.x_high==10 and row.pre_high_low==2
    assert row.run==8 and row.drawdown==9 and row.dd_vs_run_inf==9/8


def test_population_bollinger_variance_and_first_bar_true_range_seed():
    o,h,l,c,v=arrays(80);m=chart_metrics(o,h,l,c,v)
    close=c[-20:];mid=np.mean(close);sd=np.std(close,ddof=0)
    assert m.bb_mid.iloc[-1]==pytest.approx(mid,abs=1e-13)
    assert m.bb_upper.iloc[-1]==pytest.approx(mid+2*sd,abs=1e-12)
    assert m.pct_b.iloc[-1]==pytest.approx((c[-1]-(mid-2*sd))/(4*sd),abs=1e-12)
    tr=[h[0]-l[0]]+[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]
    expected=sum(tr[:14])/14
    for value in tr[14:]:expected=(13*expected+value)/14
    assert m.atr.iloc[-1]==expected


def test_leading_pre_ipo_grid_rows_do_not_change_first_observed_true_range_seed():
    inputs=arrays(100);expected=chart_metrics(*inputs)
    actual=chart_metrics(*(np.r_[np.full(7,np.nan),a] for a in inputs)).iloc[7:].reset_index(drop=True)
    np.testing.assert_array_equal(expected.to_numpy().view('uint64'),actual.to_numpy().view('uint64'))


def test_positive_over_zero_is_infinite_and_blank_variant_does_not_pass():
    o=np.arange(80,dtype=float)+100;c=o+1
    m=chart_metrics(o,c+1,o-1,c,np.ones(80));tags=chart_tags(m)
    assert np.isposinf(m.green_red_body_ratio_inf.iloc[-1]) and np.isnan(m.green_red_body_ratio_blank.iloc[-1])
    assert tags.cp_gr_body20_inf.iloc[-1]==1 and np.isnan(tags.cp_gr_body20_blank.iloc[-1])
    assert tags.cp_gr_body20.equals(tags.cp_gr_body20_inf)


def test_doji_is_neither_color_and_equal_bands_or_nonpositive_run_stay_blank():
    a=np.full(80,4.);m=chart_metrics(a,a,a,a,np.ones(80));tags=chart_tags(m)
    row=m.iloc[-1]
    assert np.isnan(row.green_red_body_ratio_inf) and np.isnan(row.red_green_volume_ratio_inf)
    assert np.isnan(row.pct_b) and np.isnan(row.run) and np.isnan(row.dd_vs_run_inf) and np.isnan(row.dip_atr_inf)
    assert tags.cp_hard_all.iloc[-1]==0 and not hard_gate_mask(tags)[-1]


def synthetic_metrics(**overrides):
    data=dict(mid_change=1.,pct_b=.12,high_age=5.,lower_high_count=4.)
    for policy in ('inf','blank'):
        data.update({f'green_red_body_ratio_{policy}':.9,f'dip_atr_{policy}':4.2,
                     f'dd_vs_run_{policy}':.5,f'red_green_volume_ratio_{policy}':2.})
    data.update(overrides);m=pd.DataFrame([data]);m.attrs=dict(parameters=asdict(DEFAULT));return m


def test_pinned_inclusive_thresholds_and_warning_only_volume_do_not_veto_hard_core():
    tags=chart_tags(synthetic_metrics())
    assert tags.cp_hard_all.iloc[0]==1 and tags.cp_redgreen_vol10.iloc[0]==1
    assert hard_gate_mask(tags)[0] and tags.lower_highs10.iloc[0]==4
    assert chart_tags(synthetic_metrics(mid_change=0)).cp_mid_slope_up.iloc[0]==0
    assert chart_tags(synthetic_metrics(red_green_volume_ratio_inf=1)).cp_redgreen_vol10.iloc[0]==0
    for day in (5,18):assert chart_tags(synthetic_metrics(high_age=day)).cp_days_since_h20.iloc[0]==1
    for day in (4,19):assert chart_tags(synthetic_metrics(high_age=day)).cp_days_since_h20.iloc[0]==0
    assert chart_tags(synthetic_metrics(pct_b=np.nan)).cp_hard_all.iloc[0]==0


def test_hard_gate_keeps_explicit_inf_and_blank_policies_and_never_counts_aliases_twice():
    tags=chart_tags(synthetic_metrics(green_red_body_ratio_inf=np.inf,green_red_body_ratio_blank=np.nan))
    assert tags.cp_hard_all_inf.iloc[0]==tags.cp_hard_all.iloc[0]==1
    assert tags.cp_hard_all_blank.iloc[0]==0
    assert tags.attrs['aliases']['cp_hard_all']=='cp_hard_all_inf'


@pytest.mark.parametrize('length',[0,1,59])
def test_empty_or_short_native_history_is_not_observed_false(length):
    tags=chart_tags(chart_metrics(*arrays(length)))
    assert len(tags)==length and tags.isna().all().all() and not hard_gate_mask(tags).any()


def test_raw_prefix_rebuild_is_exact_without_future_pivots_or_future_high_ties():
    inputs=arrays(150);full=chart_metrics(*inputs)
    for cut in (60,79,120):
        before=chart_metrics(*(a[:cut] for a in inputs))
        np.testing.assert_array_equal(full.iloc[:cut].to_numpy().view('uint64'),before.to_numpy().view('uint64'))


def bars(n=1800):
    dates=pd.bdate_range('2015-01-01',periods=n);o,h,l,c,v=arrays(n)
    return pd.DataFrame(dict(date=dates,open=o,high=h,low=l,close=c,volume=v)),dates


@pytest.mark.parametrize('tf',['1d','2d','5d','21d','monthly'])
def test_native_inputs_end_before_query_day_and_future_extremes_cannot_change_any_field(tf):
    source,calendar=bars();day=calendar[-1]
    expected=native_chart_picture(source,calendar,tf,day)
    changed=source.copy();changed.loc[changed.date>=day,['open','high','low','close','volume']]=[1e11,1e12,.001,2e11,1e18]
    actual=native_chart_picture(changed,calendar,tf,day)
    pd.testing.assert_frame_equal(expected,actual,check_exact=True)
    assert (actual.source_candle_end<actual.available_from).all() and (actual.available_from<=day).all()
    assert actual.cp_mid_slope_up.notna().any()


def test_missing_native_interval_is_retained_before60_bar_warmup_not_compressed():
    source,calendar=bars(320);source=source.drop(index=200)
    out=native_chart_picture(source,calendar,'1d',calendar[250])
    assert len(out)==250 and out.iloc[-1].drop(labels=['candle_start','source_candle_end','available_from']).isna().all()


def test_invalid_daily_ohlc_is_visible_as_an_unavailable_interval_without_mutating_source():
    source,calendar=bars(320);source.loc[200,'high']=0.;before=source.copy(deep=True)
    out=native_chart_picture(source,calendar,'1d',calendar[250])
    pd.testing.assert_frame_equal(source,before)
    assert out.attrs['source']['invalid_ohlcv_rows']==1
    assert out.iloc[-1].drop(labels=['candle_start','source_candle_end','available_from']).isna().all()


@pytest.mark.parametrize('mixed',[False,True])
def test_native_source_cannot_silently_splice_two_different_tickers(mixed):
    source,calendar=bars(100);source['ticker']='ONE'
    if mixed:
        source.loc[50:,'ticker']='OTHER'
        with pytest.raises(ValueError,match='one literal source ticker'):native_chart_picture(source,calendar,'1d',calendar[-1])
    else:
        out=native_chart_picture(source,calendar,'1d',calendar[-1]);assert out.attrs['ticker']=='ONE'
        assert out.attrs['aliases']['lower_highs10']=='cp_metric_lower_high_count'


@pytest.mark.parametrize('bad',[dict(bb_period=0),dict(high_age_max=20),dict(mid_lag=True),dict(bb_width=0),dict(body_threshold=np.nan)])
def test_invalid_parameter_bindings_are_rejected(bad):
    with pytest.raises(ValueError):ChartSettings(**bad)


def test_parameters_remain_explicit_and_metric_tag_mismatch_fails():
    custom=replace(DEFAULT,mid_lag=2,body_window=10)
    m=chart_metrics(*arrays(),custom)
    assert m.attrs['parameters']['mid_lag']==2
    with pytest.raises(ValueError,match='parameter binding'):chart_tags(m)
    assert len(chart_tags(m,custom))==100
