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
    names = {row["column"] for row in rows}
    assert "calendar_is_fomc__1d" in names
    assert "etf_xbi_close__1d" in names
    assert not any(name.startswith("etf_spy_") for name in names)
