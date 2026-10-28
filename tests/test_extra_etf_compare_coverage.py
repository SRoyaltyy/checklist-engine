"""The extra-ETF comparison rows must match the measured proof."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "docs" / "EXTRA_COMPARE_COVERAGE.json"
COVERAGE = ROOT / "docs" / "WORLD_COVERAGE.csv"
COMPLETE = ("TLT", "HYG", "LQD", "UUP", "GLD", "CPER", "USO", "RSP", "VXX")


def rows_from_proof(proof):
    expected = []
    for name, item in proof["comparators"].items():
        for column, record in item["columns"].items():
            timeframe = "1d" if column == "rel_strength_ratio" else column.rsplit("_", 1)[-1]
            percent = "" if record["non_null_percent"] is None else "%.4f" % record["non_null_percent"]
            expected.append(("extra_etf_compare", name, column, timeframe, record["status"], percent, record["first_date"] or ""))
        expected.append(("extra_etf_compare", name, "corr_1d", "1d", "EXCLUDED", "", ""))
    return expected


def test_extra_etf_comparison_rows_match_the_measured_proof():
    proof = json.loads(PROOF.read_text())
    assert proof["dia_control"] == "MATCH"
    assert proof["window_start"] == "2020-01-02"
    assert tuple(proof["comparators"]) == COMPLETE + ("IBIT",)
    for name in COMPLETE:
        item = proof["comparators"][name]
        assert item["rows"] == 12362658
        assert item["names"] == 8315
        assert item["early_available_from"] == 0
        assert item["weekend_available_from"] == 0
        assert item["columns"]["rel_strength_ratio"]["non_null_percent"] == 100.0
        assert item["columns"]["corr_60d"]["status"] == "MEASURED"
        assert item["columns"]["corr_break_60d"]["status"] == "EXCLUDED"
    ibit = proof["comparators"]["IBIT"]
    assert ibit["columns"]["rel_strength_ratio"]["first_date"] == "2024-01-11"
    assert ibit["columns"]["rel_strength_ratio"]["non_null_percent"] < 95
    assert all(record["status"] == "EXCLUDED" for record in ibit["columns"].values())
    assert ibit["early_available_from"] == 0
    assert ibit["weekend_available_from"] == 0
    with COVERAGE.open(newline="") as stream:
        stored = [
            (row["namespace"], row["item_id"], row["item"], row["timeframe"], row["status"], row["non_null_pct_2020_2026"], row["first_date_available"])
            for row in csv.DictReader(stream)
            if row["namespace"] == "extra_etf_compare"
        ]
    assert stored == rows_from_proof(proof)
