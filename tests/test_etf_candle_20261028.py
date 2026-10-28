"""The new ETF session uses the same candle columns as the published panel."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_the_new_session_is_a_one_day_candle():
    candles = pd.read_parquet(ROOT / "docs" / "etf_candle_1d_20261028.parquet")
    source = pd.read_parquet(ROOT / "docs" / "etf_session_20261028.parquet")
    assert list(candles.columns) == [
        "ticker", "timeframe", "candle_start", "date", "available_from",
        "open", "high", "low", "close", "volume",
    ]
    assert len(candles) == 43
    assert set(candles.timeframe) == {"1d"}
    assert candles.candle_start.tolist() == candles.date.tolist()
    assert set(candles.available_from.dt.strftime("%Y-%m-%d")) == {"2026-10-29"}
    assert int((candles.available_from <= candles.date).sum()) == 0
    left = candles.sort_values("ticker").reset_index(drop=True)
    right = source.sort_values("ticker").reset_index(drop=True)
    assert left.ticker.tolist() == right.ticker.tolist()
    assert left.close.tolist() == right.close.tolist()
    assert left.volume.tolist() == right.volume.tolist()
