"""Open, high, low, and volume keep the measured close fill."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "ETF_OHLCV_COVERAGE.json").read_text())
NAMESPACES = ("sector_baseline_stock_days", "industry_etf_stock_days", "extra_etf_stock_days")
FIELDS = ("open", "high", "low", "volume")


def _rows():
    with (ROOT / "docs" / "WORLD_COVERAGE.csv").open(newline="") as stream:
        return [
            row for row in csv.DictReader(stream)
            if row["namespace"] in NAMESPACES
        ]


def test_ohlcv_fields_match_the_close_fill():
    grouped = {}
    for row in _rows():
        grouped.setdefault((row["namespace"], row["timeframe"], row["item_id"]), row)
    closes = [row for row in _rows() if row["item"].endswith(" close")]
    assert len(closes) == PROOF["close_rows_copied"] == 946
    for close in closes:
        ticker = close["item"][: -len(" close")]
        assert close["item_id"] == ticker
        for field in FIELDS:
            other = grouped[(close["namespace"], close["timeframe"], ticker + "_" + field)]
            assert other["item"] == ticker + " " + field
            assert other["non_null_pct_2020_2026"] == close["non_null_pct_2020_2026"]
            assert other["first_date_available"] == close["first_date_available"]
            assert other["status"] == close["status"] == "MEASURED"
            assert other["column_measurements"] == close["column_measurements"]
            assert other["snapshot_columns"] == close["snapshot_columns"][: -len("close")] + field
            assert "810a581b08e1b421a35a32f441d1ea0116fa22ac2f5cac804f737eba1041bbae" in other["source_evidence"]
            if field == "volume":
                assert "not a proven first-publication vintage" in other["reason"]
            else:
                assert other["reason"] == close["reason"]


def test_the_candle_file_had_no_blank_ohlcv():
    assert PROOF["sha256"] == "810a581b08e1b421a35a32f441d1ea0116fa22ac2f5cac804f737eba1041bbae"
    assert PROOF["rows"] == 267883
    assert PROOF["nulls"] == {"open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
    assert PROOF["added_rows"] == 3784
