"""Calendar coverage keeps the known look-ahead rows from reading as clean."""

import csv
from pathlib import Path

COVERAGE = Path(__file__).resolve().parents[1] / "docs" / "WORLD_COVERAGE.csv"


def _rows():
    with COVERAGE.open(newline="") as stream:
        return [row for row in csv.DictReader(stream) if row["namespace"] == "calendar_stock_days"]


def test_month_end_cpi_and_jobs_carry_the_review_reason():
    rows = _rows()
    month = [row for row in rows if row["item"] == "month-end"]
    cpi = [row for row in rows if row["item"] == "CPI release day"]
    jobs = [row for row in rows if row["item"] == "jobs-report day"]
    assert len(month) == len(cpi) == len(jobs) == 22
    for row in month:
        assert row["status"] == "MEASURED"
        assert "2026-10-27" in row["reason"]
        assert "4c66ac9" in row["reason"]
    for row in cpi + jobs:
        assert row["status"] == "MEASURED"
        assert "announcement record" in row["reason"]
        assert row["non_null_pct_2020_2026"] == "99.9562" or row["timeframe"] != "1d"


def test_forward_countdowns_are_excluded():
    rows = _rows()
    excluded = [row for row in rows if row["status"] == "EXCLUDED"]
    assert {row["item_id"] for row in excluded} == {"DAYS_TO_FOMC", "DAYS_TO_CPI", "DAYS_TO_JOBS"}
    assert len(excluded) == 66
    for row in excluded:
        assert row["non_null_pct_2020_2026"] == ""
        assert "4c66ac9" in row["reason"]


def test_day_of_week_stays_measured_without_that_reason():
    rows = [row for row in _rows() if row["item"] == "day of week" and row["timeframe"] == "1d"]
    assert len(rows) == 1
    assert rows[0]["status"] == "MEASURED"
    assert rows[0]["reason"] == ""
