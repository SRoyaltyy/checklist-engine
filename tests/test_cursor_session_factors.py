import pandas as pd

import cursor_session_factors as factors
from world_context_native import attach_context
from world_context_store import validate_factor


def test_calendar_flag_is_numeric_and_hidden_until_the_next_session():
    frame = pd.DataFrame({
        "timeframe": ["1d", "1d"],
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
        "is_fomc": [True, False],
    })
    native = factors.to_native_factor(frame, "calendar_")
    columns = validate_factor(native)
    assert columns == ["calendar_is_fomc"]
    attached = attach_context(pd.to_datetime(["2024-01-02", "2024-01-03"]), native, "1d")
    assert pd.isna(attached["calendar_is_fomc__1d"].iloc[0])
    assert attached["calendar_is_fomc__1d"].iloc[1] == 1


def test_directory_coverage_skips_etfs_already_attached():
    import os
    import tempfile
    weights = pd.DataFrame({"date": ["2024-01-02", "2024-01-03"], "stock_days": [2, 2]})
    calendar = pd.DataFrame({
        "timeframe": ["1d", "1d"],
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
        "is_fomc": [False, True],
    })
    market = pd.DataFrame({
        "ticker": ["SPY", "SPY", "XBI", "XBI"],
        "timeframe": ["1d", "1d", "1d", "1d"],
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"] * 2),
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"] * 2),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"] * 2),
        "open": 1.0, "high": 1.0, "low": 1.0, "close": [10.0, 11.0, 4.0, 5.0], "volume": 1,
    })
    with tempfile.TemporaryDirectory() as directory:
        calendar.to_parquet(os.path.join(directory, "outside_event_calendar_candles.parquet"))
        market.to_parquet(os.path.join(directory, "outside_market_candles.parquet"))
        rows = factors.cover_session_directory(directory, weights)
        report_rows, bindings, nbytes = factors.session_factor_report(directory, weights)
    names = {row["column"] for row in rows}
    assert "calendar_is_fomc__1d" in names
    assert "etf_xbi_close__1d" in names
    assert not any(name.startswith("etf_spy_") for name in names)
    assert nbytes > 0 and len(report_rows) == len(rows)
    assert {row["family"] for row in bindings} == {"calendar", "industry_etf"}
    assert all(row["sha256"] for row in bindings)


def test_ratio_candles_take_candle_start_from_the_vix_level():
    ratios = pd.DataFrame({
        "series": ["vix_over_vix3m", "vix_over_vix3m"],
        "timeframe": ["1d", "1d"],
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "close": [1.1, 1.2],
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
    })
    levels = pd.DataFrame({
        "series": ["vix", "vix"],
        "timeframe": ["1d", "1d"],
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
    })
    wide = factors.ratio_candles_to_factor(ratios, levels)
    columns = validate_factor(factors.to_native_factor(wide, "vol_"))
    assert columns == ["vol_vix_over_vix3m"]


def test_committed_panels_keep_the_eighteen_industry_etfs():
    from pathlib import Path
    directory = Path("cursor_factors")
    market = pd.read_parquet(directory / "outside_market_candles.parquet", columns=["ticker"])
    tickers = set(market.ticker.unique()) - factors.ATTACHED_ETFS
    assert tickers == set("KBE KRE KCE KIE XAR XTN XBI XPH XHE XHS XOP XES XME XRT XHB XSD XSW XTL".split())
    breadth = pd.read_parquet(directory / "outside_breadth_candles.parquet")
    one_day = breadth[breadth.timeframe == "1d"]
    columns = validate_factor(factors.to_native_factor(one_day, "breadth_"))
    assert "breadth_new_highs_minus_new_lows" in columns
    calendar = pd.read_parquet(directory / "outside_event_calendar_candles.parquet")
    flags = validate_factor(factors.to_native_factor(calendar[calendar.timeframe == "1d"], "calendar_"))
    assert "calendar_is_fomc" in flags and "calendar_is_opex" in flags
    vol = pd.read_parquet(directory / "outside_vol_ratio_factors.parquet")
    one_day = vol[vol.timeframe == "1d"]
    vol_columns = validate_factor(factors.to_native_factor(one_day, "vol_"))
    assert vol_columns == [
        "vol_vix3m_minus_vix",
        "vol_vix9d_over_vix",
        "vol_vix9d_over_vix3m",
        "vol_vix_minus_vix9d",
        "vol_vix_over_vix3m",
    ]
