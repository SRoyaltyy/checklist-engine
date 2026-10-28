"""The derived candle proof and the coverage rows name the same fills."""

import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "BREADTH_DERIVED_CANDLE_PROOF.json").read_text())
COLUMNS = ("ad_volume_line", "trin", "mcclellan_oscillator", "mcclellan_summation")


def test_candle_file_matches_the_proof_counts():
    frame = pd.read_parquet(ROOT / "docs" / "breadth_derived_candles.parquet")
    assert len(frame) == PROOF["candle_rows"] == 6310
    assert int((frame.available_from <= frame.date).sum()) == 0
    assert int(frame.available_from.dt.dayofweek.ge(5).sum()) == 0
    counts = frame.groupby("timeframe").size().to_dict()
    for item in PROOF["timeframes"]:
        assert counts[item["timeframe"]] == item["rows"]
        assert item["non_null_percent"] >= 99.0778
        assert item["status"] == "MEASURED"


def test_higher_timeframes_are_in_world_coverage_and_daily_is_unchanged():
    with (ROOT / "docs" / "WORLD_COVERAGE.csv").open(newline="") as stream:
        rows = [
            row for row in csv.DictReader(stream)
            if row["namespace"] == "breadth_derived" and row["item_id"] in COLUMNS
        ]
    by_tf = {}
    for row in rows:
        by_tf.setdefault(row["timeframe"], []).append(row)
    assert len(by_tf["1d"]) == 4
    assert {row["non_null_pct_2020_2026"] for row in by_tf["1d"]} == {"99.9562"}
    expected = {item["timeframe"]: f"{item['non_null_percent']:.4f}" for item in PROOF["timeframes"] if item["timeframe"] != "1d"}
    assert set(expected) <= set(by_tf)
    for timeframe, percent in expected.items():
        assert len(by_tf[timeframe]) == 4
        assert {row["status"] for row in by_tf[timeframe]} == {"MEASURED"}
        assert {row["non_null_pct_2020_2026"] for row in by_tf[timeframe]} == {percent}
        assert {row["first_date_available"] for row in by_tf[timeframe]} == {
            next(item["first_date_available"] for item in PROOF["timeframes"] if item["timeframe"] == timeframe)
        }


def test_bullish_percent_stays_excluded():
    with (ROOT / "docs" / "WORLD_COVERAGE.csv").open(newline="") as stream:
        rows = [
            row for row in csv.DictReader(stream)
            if row["namespace"] == "breadth_derived" and row["item_id"] == "bullish_percent"
        ]
    assert len(rows) == 1
    assert rows[0]["status"] == "EXCLUDED"
    assert rows[0]["reason"] == "POINT_AND_FIGURE_BOX_AND_REVERSAL_NOT_REGISTERED"
