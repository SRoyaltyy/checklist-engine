"""A comparison value is visible on the next SPY session, not on its source session."""

import csv
from pathlib import Path

from compare_availability import visible_on

COVERAGE = Path(__file__).resolve().parents[1] / "docs" / "WORLD_COVERAGE.csv"


def test_known_sessions_move_forward_one_session():
    assert visible_on("2020-01-02") == "2020-01-03"
    assert visible_on("2020-01-03") == "2020-01-06"
    assert visible_on("2024-01-12") == "2024-01-16"
    assert visible_on("") == ""


def test_ratio_and_one_day_spread_use_the_visible_session():
    with COVERAGE.open(newline="") as stream:
        rows = [
            row for row in csv.DictReader(stream)
            if row["namespace"] == "spy_compare" and row["item"] in {"rel_strength_ratio", "return_spread_1d"}
        ]
    by_item = {row["item"]: row for row in rows}
    assert by_item["rel_strength_ratio"]["first_date_available"] == "2020-01-03"
    assert by_item["return_spread_1d"]["first_date_available"] == "2020-01-06"
    assert by_item["rel_strength_ratio"]["non_null_pct_2020_2026"] == "100.0000"
