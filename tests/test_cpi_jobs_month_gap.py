"""The published calendar skips one CPI month and one jobs month."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "CPI_JOBS_MONTH_GAP.json").read_text())
COVERAGE = ROOT / "docs" / "WORLD_COVERAGE.csv"


def test_the_gap_is_named_and_not_filled():
    assert PROOF["cpi_missing_months"] == ["2025-11"]
    assert PROOF["jobs_missing_months"] == ["2025-10"]
    assert PROOF["not_invented"].startswith("No date")
    with COVERAGE.open(newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["namespace"] == "calendar_stock_days"]
    cpi = [row for row in rows if row["item"] == "CPI release day"]
    jobs = [row for row in rows if row["item"] == "jobs-report day"]
    assert len(cpi) == len(jobs) == 22
    for row in cpi:
        assert "2025-11" in row["reason"]
        assert row["status"] == "MEASURED"
    for row in jobs:
        assert "2025-10" in row["reason"]
        assert row["status"] == "MEASURED"
