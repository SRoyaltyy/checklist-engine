"""The sector-ETF comparison rows must match the measured proof."""

import csv
import json
from pathlib import Path

from compare_availability import visible_on

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "docs" / "SECTOR_COMPARE_COVERAGE.json"
COVERAGE = ROOT / "docs" / "WORLD_COVERAGE.csv"
SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")


def rows_from_proof(proof):
    expected = []
    for name, item in proof["comparators"].items():
        for column, record in item["columns"].items():
            timeframe = "1d" if column == "rel_strength_ratio" else column.rsplit("_", 1)[-1]
            percent = "" if record["non_null_percent"] is None else "%.4f" % record["non_null_percent"]
            expected.append(("sector_etf_compare", name, column, timeframe, record["status"], percent, visible_on(record["first_date"] or "")))
        expected.append(("sector_etf_compare", name, "corr_1d", "1d", "EXCLUDED", "", ""))
    return expected


def test_sector_etf_rows_match_the_measured_proof_and_are_not_own_sector():
    proof = json.loads(PROOF.read_text())
    assert proof["own_sector"] == "NOT_ASSIGNED"
    assert proof["spy_control"] == "MATCH"
    assert tuple(proof["comparators"]) == SECTORS
    for item in proof["comparators"].values():
        assert item["rows"] == 12362658
        assert item["names"] == 8315
        assert item["early_available_from"] == 0
        assert item["weekend_available_from"] == 0
        assert item["columns"]["rel_strength_ratio"]["non_null_percent"] == 100.0
        assert item["columns"]["corr_60d"]["status"] == "MEASURED"
        assert item["columns"]["corr_break_60d"]["status"] == "EXCLUDED"
    with COVERAGE.open(newline="") as stream:
        stored = [
            (row["namespace"], row["item_id"], row["item"], row["timeframe"], row["status"], row["non_null_pct_2020_2026"], row["first_date_available"])
            for row in csv.DictReader(stream)
            if row["namespace"] == "sector_etf_compare"
        ]
    assert stored == rows_from_proof(proof)
