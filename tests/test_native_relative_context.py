import numpy as np
import pandas as pd
import pytest

from market_storage import assert_exact_frame
from outside_compare import compare_one
from outside_market import completed_market_candles
from world_bar_statistics import relative_statistics
from world_context_store import validate_factor
from world_relative_context import native_comparisons, native_grid, ratio_variants, relative_row_view
from world_timeframes import TIMEFRAMES


def prices(calendar,seed=12):
    rng=np.random.default_rng(seed)
    close=40*np.exp(np.cumsum(rng.normal(.0003,.012,len(calendar))))
    return pd.DataFrame(dict(date=calendar,open=close-.1,high=close+.5,low=close-.5,close=close,volume=1000.))


def market():
    calendar=pd.bdate_range('2019-01-01','2021-01-15')
    return calendar,prices(calendar),prices(calendar,99)


def test_legacy_defaults_keep_registered_daily_formulas_and_missing_outcomes():
    dates=pd.bdate_range('2024-01-02',periods=8)
    stock=pd.DataFrame(dict(date=dates,close=[10.,10.,10.,11.,11.,10.,9.,10.]))
    other=pd.DataFrame(dict(date=dates,close=[10.,9.4,9.4,9.,10.,10.,10.,11.]))
    actual=compare_one(stock,other)
    assert pd.isna(actual.divergence_flat_vs_fall_1d.iloc[0])
    assert actual.divergence_flat_vs_fall_1d.iloc[1]==1
    assert actual.divergence_fall_vs_flat_1d.iloc[5]==1
    assert actual.return_spread_5d.iloc[5]==pytest.approx((10/10-1)-(10/10-1))
    expected=stock.close.pct_change(fill_method=None).rolling(5).corr(other.close.pct_change(fill_method=None))
    np.testing.assert_allclose(actual.corr_5d,expected,equal_nan=True)
    assert 'return_spread_10d' not in actual and 'corr_1d' not in actual


def test_ten_bar_setting_is_available_without_relabeling_daily_defaults():
    calendar,stock,other=market()
    actual=compare_one(stock,other,windows=(1,5,10,20,60),correlation_windows=(5,10,20,60))
    expected=(stock.close/stock.close.shift(10)-1)-(other.close/other.close.shift(10)-1)
    np.testing.assert_allclose(actual.return_spread_10d,expected,equal_nan=True,rtol=0,atol=0)


def test_true_five_day_comparison_uses_five_day_closes_and_native_lookbacks():
    calendar,stock,other=market()
    day=calendar[-1]
    actual=native_comparisons('A','SPY',stock,other,calendar,'5d',day)
    a=completed_market_candles(stock.loc[stock.date<day],'5d',calendar)
    b=completed_market_candles(other.loc[other.date<day],'5d',calendar)
    expected=(a.close/a.close.shift(5)-1)-(b.close/b.close.shift(5)-1)
    np.testing.assert_allclose(actual.relative_spy_return_spread_n5,expected,equal_nan=True,rtol=0,atol=0)
    assert len(actual)<len(stock)/4
    assert (actual.source_candle_end<actual.available_from).all()


def test_missing_native_interval_is_not_compressed_or_forward_filled():
    calendar,stock,other=market()
    missing=other.drop(index=6)
    actual=native_comparisons('A','SPY',stock,missing,calendar,'1d',calendar[25])
    row=actual.loc[actual.source_candle_end==calendar[6]].iloc[0]
    assert pd.isna(row.relative_spy_rel_strength_ratio)
    following=actual.loc[actual.source_candle_end==calendar[7]].iloc[0]
    assert pd.isna(following.relative_spy_return_spread_n1)
    assert pd.isna(following.relative_spy_corr_n5)
    assert len(actual)==25
    views=relative_row_view('A',calendar[5:10],'SPY',stock,missing,calendar,'1d')
    assert pd.isna(views.loc[views.date==calendar[7],'relative_spy_rel_strength_ratio__1d']).all()


def test_an_interior_halt_invalidates_the_entire_composite_bucket():
    calendar,stock,other=market()
    actual=native_comparisons('A','SPY',stock.drop(index=6),other,calendar,'5d',calendar[25])
    row=actual.loc[actual.source_candle_end==calendar[9]].iloc[0]
    assert pd.isna(row.relative_spy_rel_strength_ratio)
    assert actual.attrs['stock']['unavailable_native_rows']>=1


def test_monthly_values_wait_for_the_actual_next_session():
    calendar,stock,other=market()
    # January2020 ends Friday31; a calendar-first February date is Saturday.
    a=native_comparisons('A','SPY',stock,other,calendar,'monthly','2020-02-03')
    row=a.loc[a.source_candle_end==pd.Timestamp('2020-01-31')].iloc[0]
    assert row.available_from==pd.Timestamp('2020-02-03')
    assert row.candle_start==pd.Timestamp('2020-01-01')  # synthetic business calendar
    assert pd.Timestamp('2020-01-31') not in set(native_grid(calendar,'monthly','2020-01-31').source_candle_end)


def test_day_d_ohlcv_and_later_prices_cannot_change_any_earlier_native_value():
    calendar,stock,other=market()
    day=calendar[300]
    for tf in TIMEFRAMES:
        baseline=native_comparisons('A','SPY',stock,other,calendar,tf,day)
        a=stock.copy();b=other.copy()
        a.loc[a.date>=day,['open','high','low','close','volume']]=1e12
        b.loc[b.date>=day,['open','high','low','close','volume']]=2e12
        rebuilt=native_comparisons('A','SPY',a,b,calendar,tf,day)
        assert_exact_frame(baseline,rebuilt)
        assert not any(c.startswith('execution_') for c in rebuilt)
        assert validate_factor(rebuilt)


def test_ipo_and_partial_opening_candles_remain_missing_until_a_complete_bucket():
    calendar,stock,other=market()
    actual=native_comparisons('A','SPY',stock.iloc[7:],other,calendar,'5d',calendar[30])
    first=actual.loc[actual.relative_spy_rel_strength_ratio.notna()].iloc[0]
    assert first.candle_start==calendar[10]
    assert first.source_candle_end==calendar[14]
    assert first.available_from==calendar[15]


def test_self_comparison_is_an_explicit_exclusion_not_fabricated_false_answers():
    calendar,stock,other=market()
    actual=native_comparisons('SPY','SPY',stock,other,calendar,'1d',calendar[60])
    values=actual.drop(columns=['candle_start','source_candle_end','available_from'])
    assert values.isna().all().all()
    assert actual.attrs['self_comparison_exclusion']=='SELF_COMPARISON'


def test_missing_divergence_is_not_cast_to_true():
    calendar,stock,other=market()
    actual=native_comparisons('A','SPY',stock.iloc[25:],other,calendar,'1d',calendar[40])
    assert actual.relative_spy_divergence_flat_vs_fall_n1.iloc[:26].isna().all()


def test_ratio_variants_keep_zero_missing_and_infinite_distinct():
    inf,blank=ratio_variants([1.,-1.,0.,np.nan,4.],[0.,0.,0.,0.,2.])
    np.testing.assert_equal(inf,[np.inf,-np.inf,np.nan,np.nan,2.])
    np.testing.assert_equal(blank,[np.nan,np.nan,np.nan,np.nan,2.])


def test_registered_beta_keeps_default_precision_and_supports_exact_float64():
    calendar,stock,other=market()
    a=stock.assign(candle_start=calendar)
    b=other.assign(candle_start=calendar)
    default=relative_statistics(a,b,'spy')
    single=relative_statistics(a,b,'spy',dtype=np.float32)
    precise=relative_statistics(a,b,'spy',dtype=np.float64)
    for name in default:
        np.testing.assert_array_equal(default[name].view('uint32'),single[name].view('uint32'))
        np.testing.assert_array_equal(default[name].view('uint32'),precise[name].astype('float32').view('uint32'))
        assert precise[name].dtype==np.float64
    assert np.any(precise['MANSFIELD_spy_20'][20:]!=default['MANSFIELD_spy_20'][20:].astype('float64'))
    ar=stock.close.pct_change(fill_method=None);br=other.close.pct_change(fill_method=None)
    expected=ar.rolling(20).cov(br)/br.rolling(20).var(ddof=1)
    np.testing.assert_allclose(precise['BETA_spy_20'],expected,equal_nan=True,rtol=0,atol=0)


@pytest.mark.parametrize('windows',[(0,5),(5,5),(True,5)])
def test_bad_parameter_grids_fail_before_they_can_inflate_coverage(windows):
    calendar,stock,other=market()
    with pytest.raises(ValueError,match='comparison windows'):
        native_comparisons('A','SPY',stock,other,calendar,'1d',calendar[40],windows=windows)


def test_literal_sources_cannot_silently_select_sector_or_reassign_identity():
    calendar,stock,other=market()
    with pytest.raises(ValueError,match='registered ETF'):
        native_comparisons('A','current_sector',stock,other,calendar,'1d',calendar[40])
    with pytest.raises(ValueError,match='identity'):
        native_comparisons('A','SPY',stock.assign(ticker='B'),other,calendar,'1d',calendar[40])
