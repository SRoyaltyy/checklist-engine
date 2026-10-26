import numpy as np
import pandas as pd
import pytest

from world_context_native import (
    KEYS, native_intervals, fred_native, index_native, price_native,
    combine_contexts, attach_context,
    membership_at, attach_mapped_context,
    relative_native,
)
from world_fred import compile_timelines
from world_timeframes import TIMEFRAMES, PRICE_COLS, completed_candles


def bars(periods=220):
    dates = pd.bdate_range("2019-01-02", periods=periods)
    close = np.arange(periods, dtype=float) + 100
    return pd.DataFrame(dict(date=dates, open=close-1, high=close+2,
                             low=close-3, close=close, volume=100+close))


def index_source(frame):
    return frame.rename(columns={c:c.upper() for c in ("date","open","high","low","close")})


@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_context_boundaries_equal_true_stock_candle_boundaries(timeframe):
    source = bars()
    expected = completed_candles(source, timeframe, session_calendar=source.date)
    expected = expected.rename(columns={"date":"source_candle_end"})
    actual = native_intervals(source.date, timeframe)
    pd.testing.assert_frame_equal(actual[list(KEYS)], expected[list(KEYS)])


def test_index_ohlc_aggregates_real_sessions_and_missing_interval_stays_blank():
    source = bars(31)
    history = index_source(source)
    actual = index_native(history, source.date, "5d", "cboe_vix")
    first = actual.iloc[0]
    assert first.cboe_vix_open == source.open.iloc[0]
    assert first.cboe_vix_high == source.high.iloc[:5].max()
    assert first.cboe_vix_low == source.low.iloc[:5].min()
    assert first.cboe_vix_close == source.close.iloc[4]
    broken = index_native(history.drop(index=6), source.date, "5d", "cboe_vix")
    assert broken.loc[1, ["cboe_vix_open", "cboe_vix_close"]].isna().all()
    attached = attach_context(source.date, broken, "5d")
    assert attached.loc[10:14,"cboe_vix_close__5d"].isna().all()
    assert attached.loc[15,"cboe_vix_close__5d"] == source.close.iloc[14]


def test_close_only_vvix_never_invents_open_high_low_or_volume():
    source = bars(31)
    frame = index_native(index_source(source)[["DATE","CLOSE"]], source.date, "5d", "vvix")
    assert set(frame) == {*KEYS,"vvix_close","vvix_close_change20","vvix_close_change60"}
    assert frame.vvix_close.iloc[0] == source.close.iloc[4]


def test_invalid_index_observations_and_partial_schema_are_rejected_or_blank():
    source = bars(31);history = index_source(source)
    with pytest.raises(ValueError,match="index dates"):
        index_native(pd.concat([history,history.iloc[:1]]),source.date,"5d","vix")
    with pytest.raises(ValueError,match="incomplete OHLC"):
        index_native(history.drop(columns="OPEN"),source.date,"5d","vix")
    history.loc[6,"CLOSE"] = np.inf
    assert np.isnan(index_native(history,source.date,"5d","vix").vix_close.iloc[1])


def test_fred_releases_and_revisions_are_strictly_before_query_date():
    dates = pd.bdate_range("2020-01-01",periods=12)
    source = pd.DataFrame(dict(series=["TEST"]*3,
        obs_date=pd.to_datetime(["2019-12-01","2019-12-01","2020-01-01"]),
        vintage_date=[dates[2],dates[5],dates[8]],value=[1.,9.,2.]))
    timelines = compile_timelines(source)
    native = fred_native(dates,"1d",timelines,required_series=["TEST"])
    attached = attach_context(dates,native,"1d")
    assert np.isnan(attached.fred_test__1d.iloc[2])
    assert attached.fred_test__1d.iloc[3] == 1
    assert attached.fred_test__1d.iloc[5] == 1
    assert attached.fred_test__1d.iloc[6] == 9
    assert attached.fred_test_first_release__1d.iloc[6] == 1
    with pytest.raises(ValueError,match="required ALFRED"):
        fred_native(dates,"1d",timelines,required_series=["MISSING"])


def test_fred_changes_count_native_candles_and_do_not_interpolate_monthly_data():
    dates = pd.bdate_range("2020-01-01",periods=150)
    source = pd.DataFrame(dict(series="TEST",obs_date=dates,vintage_date=dates,value=np.arange(150,dtype=float)**2))
    native = fred_native(dates,"2d",compile_timelines(source))
    assert native.fred_test.iloc[20] == 41**2
    assert native.fred_test_change20.iloc[20] == 41**2-1**2
    monthly = source.iloc[[0]].copy()
    native = fred_native(dates,"2d",compile_timelines(monthly))
    assert set(native.fred_test.dropna()) == {0.0}


def test_price_context_uses_composite_returns_and_preserves_ipo_halt_blanks():
    source = bars(301)
    native = price_native(source,source.date,"5d","etf_spy")
    assert native.etf_spy_volume.iloc[0] == source.volume.iloc[:5].sum()
    assert native.etf_spy_r5.iloc[5] == pytest.approx(source.close.iloc[29]/source.close.iloc[4]-1)
    assert native.etf_spy_d50.iloc[49] == pytest.approx(source.close.iloc[249]/source.close.iloc[4:250:5].mean()-1)
    ipo = price_native(source.iloc[3:],source.date,"5d","etf_spy")
    assert np.isnan(ipo.etf_spy_close.iloc[0])
    assert ipo.etf_spy_close.iloc[1] == source.close.iloc[9]
    halted = price_native(source.drop(index=6),source.date,"5d","etf_spy")
    assert np.isnan(halted.etf_spy_close.iloc[1])


def test_combination_requires_exact_boundaries_and_noncolliding_columns():
    source = bars(40)
    vix = index_native(index_source(source),source.date,"5d","cboe_vix")
    vix9 = index_native(index_source(source),source.date,"5d","cboe_vix9d")
    result = combine_contexts([vix,vix9])
    assert (result.vix9d_vix_term_ratio == 1).all()
    with pytest.raises(ValueError,match="duplicate"):
        combine_contexts([vix,vix])
    changed = vix9.copy();changed.loc[0,"candle_start"] += pd.Timedelta(days=1)
    with pytest.raises(ValueError,match="boundaries"):
        combine_contexts([vix,changed])


@pytest.mark.parametrize("timeframe",["1d","2d","5d","21d","monthly"])
def test_future_truncation_preserves_every_available_context_value(timeframe):
    source = bars(301);calendar = source.date;cut = calendar.iloc[220]
    fred_source = pd.DataFrame(dict(series="TEST",obs_date=calendar,vintage_date=calendar,value=np.arange(len(calendar))**2))
    full = combine_contexts([
        price_native(source,calendar,timeframe,"etf_spy"),
        index_native(index_source(source),calendar,timeframe,"cboe_vix"),
        fred_native(calendar,timeframe,compile_timelines(fred_source)),
    ])
    prefix = source[source.date < cut];prefix_calendar = calendar[calendar <= cut]
    rebuilt = combine_contexts([
        price_native(prefix,prefix_calendar,timeframe,"etf_spy"),
        index_native(index_source(prefix),prefix_calendar,timeframe,"cboe_vix"),
        fred_native(prefix_calendar,timeframe,compile_timelines(fred_source[fred_source.vintage_date < cut])),
    ])
    query = calendar[calendar <= cut]
    pd.testing.assert_frame_equal(attach_context(query,full,timeframe),attach_context(query,rebuilt,timeframe))


def test_attach_rejects_unproven_dates_and_keeps_empty_schema():
    source = bars(10)
    native = price_native(source,source.date,"21d","spy")
    attached = attach_context(source.date,native,"21d")
    assert "spy_close__21d" in attached
    assert attached.spy_close__21d.isna().all()
    native = price_native(source,source.date,"1d","spy")
    native.loc[0,"source_candle_end"] = native.available_from.iloc[0]
    with pytest.raises(ValueError,match="completion"):
        attach_context(source.date,native,"1d")


@pytest.mark.parametrize("calendar",[[],["2020-01-02","2020-01-01"],["2020-01-01"]*2,[pd.NaT]])
def test_bad_calendars_fail(calendar):
    with pytest.raises(ValueError):native_intervals(calendar,"1d")


def test_membership_is_strictly_dated_and_never_backfills_current_labels():
    source = bars(20);dates = source.date
    mapping = pd.DataFrame(dict(ticker=["NA","NA","OTHER"],
        known_from=[dates.iloc[2],dates.iloc[8],dates.iloc[0]],sector_etf=["XLK","XLF","XLE"]))
    result = membership_at("NA",dates,mapping,"sector")
    assert result.benchmark.iloc[:3].isna().all()
    assert result.benchmark.iloc[3:9].eq("XLK").all()
    assert result.benchmark.iloc[9:].eq("XLF").all()
    current = mapping.iloc[:1].copy();current["known_from"] = pd.Timestamp("2026-01-01")
    assert membership_at("NA",dates,current,"sector").benchmark.isna().all()


def test_mapped_context_changes_only_after_knowledge_date_and_keeps_lineage():
    source = bars(20);other = source.copy();other[list(PRICE_COLS)] *= 2
    mapping = pd.DataFrame(dict(ticker=["NA","NA"],known_from=[source.date.iloc[2],source.date.iloc[8]],
                                 sector_etf=["XLK","XLF"]))
    candidates = {"XLK":price_native(source,source.date,"1d","sector"),
                  "XLF":price_native(other,source.date,"1d","sector")}
    result,lineage = attach_mapped_context("NA",source.date,mapping,candidates,"1d","sector")
    assert result.sector_close__1d.iloc[:3].isna().all()
    assert result.sector_close__1d.iloc[8] == source.close.iloc[7]
    assert result.sector_close__1d.iloc[9] == 2*source.close.iloc[8]
    assert lineage.known_from.iloc[9] == source.date.iloc[8]
    assert "benchmark" not in result


def test_missing_or_conflicting_membership_sources_fail_loudly():
    source = bars(20)
    mapping = pd.DataFrame(dict(ticker=["NA","NA"],known_from=[source.date.iloc[2]]*2,
                                 industry_etf=["SMH","XBI"]))
    with pytest.raises(ValueError,match="conflicting membership"):
        membership_at("NA",source.date,mapping,"industry")
    candidates = {"SMH":price_native(source,source.date,"1d","industry")}
    with pytest.raises(ValueError,match="mapped benchmark source missing"):
        attach_mapped_context("NA",source.date,mapping.iloc[[1]],candidates,"1d","industry")
    missing_date = mapping.iloc[[0]].copy();missing_date["known_from"] = pd.NaT
    with pytest.raises(ValueError,match="knowledge date missing"):
        membership_at("NA",source.date,missing_date,"industry")


def test_relative_native_has_exact_registered_returns_and_correlations():
    source = bars(220)
    benchmark = source.copy();benchmark[list(PRICE_COLS)] *= 2
    stock = price_native(source,source.date,"1d","stock")
    peer = price_native(benchmark,source.date,"1d","sector")
    result = relative_native(stock,peer,"sector")
    assert result.RS_LOG_sector.iloc[-1] == pytest.approx(np.log(.5))
    assert result.RS_RETURN_sector_20.iloc[-1] == pytest.approx(0)
    assert result.CORRELATION_sector_60.iloc[-1] == pytest.approx(1)
    assert result.BETA_sector_60.iloc[-1] == pytest.approx(1)
    assert result.MANSFIELD_sector_60.iloc[-1] == pytest.approx(0)
    peer.loc[0,"candle_start"] -= pd.Timedelta(days=1)
    with pytest.raises(ValueError,match="boundaries"):
        relative_native(stock,peer,"sector")


def test_relative_native_does_not_forward_fill_missing_benchmark_buckets():
    source = bars(301)
    stock = price_native(source,source.date,"5d","stock")
    peer = price_native(source.drop(index=100),source.date,"5d","industry")
    result = relative_native(stock,peer,"industry")
    assert np.isnan(result.RS_LOG_industry.iloc[20])
    assert np.isnan(result.RS_RETURN_industry_5.iloc[25])
    assert np.isnan(result.CORRELATION_industry_20.iloc[39])
