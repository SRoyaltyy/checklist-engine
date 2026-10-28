import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import light_box_market as box


def write_symbol(directory, symbol, dates, closes):
    frame = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": closes, "high": closes, "low": closes, "close": closes,
        "adj_close": [c * 0.9 for c in closes],
        "volume": [10] * len(closes),
    })
    path = Path(directory) / (symbol + ".parquet")
    frame.to_parquet(path, index=False)
    return dict(
        symbol=symbol, file=path.name, rows=len(frame),
        first=str(pd.Timestamp(dates[0]).date()), last=str(pd.Timestamp(dates[-1]).date()),
        expected_days=len(frame), missing_days=0, missing_sample=[], coverage=1.0,
        status="PASS", reason="", sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def test_available_from_is_the_next_session_and_sha_is_checked(tmp_path):
    dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
    rows = [write_symbol(tmp_path, symbol, dates, [10, 11, 12]) for symbol in ("SPY", "XBI")]
    (tmp_path / "manifest.json").write_text(json.dumps({"window_start": "2020-01-02", "source": "test", "symbols": rows}))
    panel, _, _ = box.build_panel(tmp_path, as_of="2024-01-03")
    assert set(panel.date.dt.strftime("%Y-%m-%d")) == {"2024-01-02", "2024-01-03"}
    spy = panel[panel.ticker == "SPY"].sort_values("date")
    assert spy.available_from.iloc[0] == pd.Timestamp("2024-01-03")
    assert spy.adj_close.iloc[0] == pytest.approx(9.0)
    rows[0]["sha256"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps({"window_start": "2020-01-02", "source": "test", "symbols": rows}))
    with pytest.raises(ValueError, match="sha256"):
        box.build_panel(tmp_path)


def test_a_later_bar_does_not_change_an_earlier_candle(tmp_path):
    dates = list(pd.bdate_range("2024-01-02", periods=8))
    rows = [write_symbol(tmp_path, symbol, dates, list(range(10, 18))) for symbol in ("SPY", "XBI")]
    (tmp_path / "manifest.json").write_text(json.dumps({"window_start": "2020-01-02", "source": "test", "symbols": rows}))
    early, _, _ = box.build_panel(tmp_path, as_of=dates[4])
    full, _, _ = box.build_panel(tmp_path, as_of=dates[-1])
    boundary = pd.bdate_range("2024-01-02", periods=12)
    early_candles = box.build_candles(early, boundary, dates[4])
    full_candles = box.build_candles(full, boundary, dates[-1])
    visible = full_candles[full_candles.available_from.notna() & (full_candles.available_from <= dates[5])]
    left = early_candles[early_candles.available_from.notna() & (early_candles.available_from <= dates[5])]
    merged = left.merge(visible, on=["ticker", "timeframe", "date"], suffixes=("_early", "_full"))
    assert len(merged) == len(left) == len(visible) > 0
    assert (merged.close_early == merged.close_full).all()


def test_index_files_are_not_in_the_etf_panel(tmp_path):
    dates = ["2024-01-02", "2024-01-03"]
    rows = [write_symbol(tmp_path, "SPY", dates, [10, 11]), write_symbol(tmp_path, "^VIX", dates, [15, 16])]
    (tmp_path / "manifest.json").write_text(json.dumps({"window_start": "2020-01-02", "source": "test", "symbols": rows}))
    panel, _, used = box.build_panel(tmp_path)
    assert [row["symbol"] for row in used] == ["SPY"]
    assert set(panel.ticker) == {"SPY"}
