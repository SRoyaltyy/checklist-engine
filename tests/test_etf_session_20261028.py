"""The 2026-10-28 ETF session is a supplement, not a rewrite of the release."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "ETF_SESSION_20261028.json").read_text())
REQUIRED = {
    "SPY", "QQQ", "IWM", "DIA", "RSP",
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
    "KBE", "KRE", "KCE", "KIE", "XAR", "XTN", "XBI", "XPH", "XHE", "XHS", "XOP",
    "XES", "XME", "XRT", "XHB", "XSD", "XSW", "XTL",
    "TLT", "HYG", "LQD", "UUP", "GLD", "CPER", "USO", "VXX", "IBIT",
}


def test_the_new_session_is_complete_and_not_yet_visible():
    frame = pd.read_parquet(ROOT / "docs" / "etf_session_20261028.parquet")
    assert set(frame.ticker) == REQUIRED
    assert len(frame) == PROOF["rows"] == 43
    assert set(frame.date.dt.strftime("%Y-%m-%d")) == {"2026-10-28"}
    assert set(frame.available_from.dt.strftime("%Y-%m-%d")) == {"2026-10-29"}
    assert int(frame.available_from.dt.dayofweek.ge(5).sum()) == 0
    assert int((frame.available_from <= frame.date).sum()) == 0
    assert int(frame[["open", "high", "low", "close", "volume"]].isna().sum().sum()) == 0
    assert int((frame.high < frame[["open", "close", "low"]].max(axis=1)).sum()) == 0
    assert int((frame.low > frame[["open", "close", "high"]].min(axis=1)).sum()) == 0
    assert PROOF["prior_ohlc_max_abs"] == 0.0
    assert PROOF["prior_volume_names_that_differ"] == 8
    assert PROOF["published_candle_release_unchanged"] == "outside-market-released-v3-40667431231-1"
