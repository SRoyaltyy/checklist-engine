import pandas as pd
import pytest

import cursor_session_factors as factors
from world_context_native import attach_context
from world_context_store import validate_factor
from world_timeframes import TIMEFRAMES


def _candle(ticker, timeframe, start, end, available, close):
    return dict(
        ticker=ticker, timeframe=timeframe,
        candle_start=pd.Timestamp(start), date=pd.Timestamp(end),
        available_from=pd.Timestamp(available),
        open=close, high=close, low=close, close=close, volume=1,
    )


def _industry_panel(extra_rows=()):
    rows = []
    for ticker in sorted(factors.INDUSTRY_ETFS):
        for timeframe in TIMEFRAMES:
            rows.append(_candle(ticker, timeframe, "2024-01-02", "2024-01-02", "2024-01-03", 4.0))
            rows.append(_candle(ticker, timeframe, "2024-01-03", "2024-01-03", "2024-01-04", 5.0))
    rows.extend(extra_rows)
    return pd.DataFrame(rows)


def test_calendar_flag_is_numeric_and_hidden_until_the_next_session():
    frame = pd.DataFrame({
        "timeframe": ["1d", "1d"],
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
        "is_fomc": [True, False],
    })
    native = factors.to_native_factor(frame, "calendar_")
    assert validate_factor(native) == ["calendar_is_fomc"]
    attached = attach_context(pd.to_datetime(["2024-01-02", "2024-01-03"]), native, "1d")
    assert pd.isna(attached["calendar_is_fomc__1d"].iloc[0])
    assert attached["calendar_is_fomc__1d"].iloc[1] == 1


def test_industry_panel_skips_spy_and_keeps_eighteen():
    panel = _industry_panel([
        _candle("SPY", "1d", "2024-01-02", "2024-01-02", "2024-01-03", 10.0),
    ])
    frames = factors.industry_native_frames(panel)
    symbols = {ticker for ticker, _, _ in frames}
    columns = {column for _, _, native in frames for column in native.columns}
    assert symbols == set(factors.INDUSTRY_ETFS)
    assert "etf_xbi_close" in columns
    assert not any(column.startswith("etf_spy_") for column in columns)
    assert len(frames) == len(factors.INDUSTRY_ETFS) * len(TIMEFRAMES)


def test_weekend_availability_is_rejected():
    panel = _industry_panel()
    panel.loc[panel.index[0], "available_from"] = pd.Timestamp("2024-01-06")
    with pytest.raises(ValueError, match="weekend"):
        factors.industry_native_frames(panel)


def test_monthly_weekend_moves_forward_to_the_next_session_only():
    frame = pd.DataFrame({
        "candle_start": pd.to_datetime(["1990-03-01", "2024-01-02"]),
        "source_candle_end": pd.to_datetime(["1990-03-30", "2024-01-31"]),
        "available_from": pd.to_datetime(["1990-04-01", "2024-02-03"]),
        **{column: [1.0, 1.1] for column in factors.VOL_COLUMNS},
    })
    sessions = pd.to_datetime(["2024-02-01", "2024-02-05"])
    native = factors.volatility_native(frame, sessions)
    assert list(native.available_from) == [pd.Timestamp("2024-02-05")]
    assert native.attrs["availability_moved"] == 1
    assert native.attrs["availability_dropped"] == 1
    assert native.available_from.iloc[0] > native.source_candle_end.iloc[0]


def test_volatility_file_keeps_the_published_five_columns():
    frame = pd.DataFrame({
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "source_candle_end": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
        "vol_vix_over_vix3m": [1.1, 1.2],
        "vol_vix9d_over_vix": [0.9, 0.8],
        "vol_vix9d_over_vix3m": [0.95, 0.96],
        "vol_vix3m_minus_vix": [1.0, 1.1],
        "vol_vix_minus_vix9d": [0.2, 0.3],
    })
    native = factors.volatility_native(frame)
    assert validate_factor(native) == list(factors.VOL_COLUMNS)


def test_followon_directory_rejects_a_repeated_column(tmp_path):
    frame = pd.DataFrame({
        "candle_start": pd.to_datetime(["2024-01-02"]),
        "source_candle_end": pd.to_datetime(["2024-01-02"]),
        "available_from": pd.to_datetime(["2024-01-03"]),
        **{column: [1.0] for column in factors.VOL_COLUMNS},
    })
    for timeframe in TIMEFRAMES:
        frame.to_parquet(tmp_path / ("volatility_term_" + timeframe + ".parquet"), index=False)
    weights = pd.DataFrame({"date": ["2024-01-03"], "stock_days": [2]})
    rows, bindings, nbytes = factors.measure_directory(tmp_path, weights)
    assert {row["family"] for row in bindings} == {"volatility_term"}
    assert nbytes > 0 and rows
    with pytest.raises(ValueError, match="repeats a column"):
        factors.attach_outside_followon(rows, [], 0, weights, tmp_path)
