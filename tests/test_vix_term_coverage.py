"""VIX close and term ratios stay cited from the already measured releases."""

import csv
from pathlib import Path

COVERAGE = Path(__file__).resolve().parents[1] / "docs" / "WORLD_COVERAGE.csv"
TIMEFRAMES = [f"{i}d" for i in range(1, 22)] + ["monthly"]
CBOE = {
    "VIX": "cboe_vix_close",
    "vix9d_vix_term_ratio": "vix9d_vix_term_ratio",
    "vix3m_vix_term_ratio": "vix3m_vix_term_ratio",
}
VOL = (
    "vol_vix_over_vix3m",
    "vol_vix9d_over_vix",
    "vol_vix9d_over_vix3m",
    "vol_vix3m_minus_vix",
    "vol_vix_minus_vix9d",
)


def _rows():
    with COVERAGE.open(newline="") as stream:
        return list(csv.DictReader(stream))


def test_shared_context_vix_and_term_ratios_are_complete():
    rows = [
        row for row in _rows()
        if row["namespace"] == "cboe_shared_context" and row["item_id"] in CBOE
    ]
    assert len(rows) == 66
    seen = {(row["item_id"], row["timeframe"]) for row in rows}
    assert seen == {(item, tf) for item in CBOE for tf in TIMEFRAMES}
    for row in rows:
        assert row["snapshot_columns"] == CBOE[row["item_id"]]
        assert row["non_null_pct_2020_2026"] == "100.0000"
        assert row["first_date_available"] == "2020-01-02"
        assert row["status"] == "MEASURED"
        assert row["universe_scope"] == "shared_market_sessions_not_stock_days"
        assert "0caf833d8ab7e4144e0be651f112209359a0e8919be2f2fbe53ea93de9e1cb79" in row["source_evidence"]


def test_original_cboe_closes_stay_measured():
    rows = [
        row for row in _rows()
        if row["namespace"] == "cboe_shared_context"
        and row["item"] in {"VIX9D close", "VIX3M close", "VVIX close"}
    ]
    assert len(rows) == 66
    assert {row["status"] for row in rows} == {"MEASURED"}
    assert {row["non_null_pct_2020_2026"] for row in rows} == {"100.0000"}


def test_volatility_term_ratios_cover_every_timeframe():
    rows = [row for row in _rows() if row["namespace"] == "volatility_term"]
    assert len(rows) == 110
    seen = {(row["item_id"], row["timeframe"]) for row in rows}
    assert seen == {(item, tf) for item in VOL for tf in TIMEFRAMES}
    for row in rows:
        assert row["non_null_pct_2020_2026"] == "100.0000"
        assert row["first_date_available"] == "2020-01-02"
        assert row["status"] == "MEASURED"
        assert row["universe_scope"] == "approved_stock_days"
        assert "8ca51dcb83be2099dab6d02f896419a7fd3c1040babe4f78b26ee37b19cb4acd" in row["source_evidence"]
        assert '"stock_days":12364370' in row["column_measurements"]
        assert '"non_null_sessions":1712' in row["column_measurements"]


def test_dictionary_vix_level_stays_pending():
    rows = [row for row in _rows() if row["namespace"] == "dictionary" and row["item"] == "VIX level"]
    assert len(rows) == 22
    assert {row["status"] for row in rows} == {"PENDING"}
