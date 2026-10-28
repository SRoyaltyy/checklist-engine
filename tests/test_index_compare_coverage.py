"""The QQQ, IWM, and DIA comparison rows must match the measured proof."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "docs" / "INDEX_COMPARE_COVERAGE.json"
COVERAGE = ROOT / "docs" / "WORLD_COVERAGE.csv"


def rows_from_proof(proof):
    expected = []
    for name, item in proof["comparators"].items():
        for column, record in item["columns"].items():
            timeframe = "1d" if column == "rel_strength_ratio" else column.rsplit("_", 1)[-1]
            percent = "" if record["non_null_percent"] is None else "%.4f" % record["non_null_percent"]
            expected.append((name.lower() + "_compare", name, column, timeframe, record["status"], percent, record["first_date"] or ""))
        expected.append((name.lower() + "_compare", name, "corr_1d", "1d", "EXCLUDED", "", ""))
    return expected


def test_index_comparison_rows_match_the_measured_proof():
    proof = json.loads(PROOF.read_text())
    assert proof["afcg_versus_spy"] == "MATCH"
    assert proof["afcg_corr_5d_max_abs_spy_minus_qqq"] > 0
    assert set(proof["comparators"]) == {"QQQ", "IWM", "DIA"}
    for item in proof["comparators"].values():
        assert item["rows"] == 12362658
        assert item["names"] == 8315
        assert item["early_available_from"] == 0
        assert item["weekend_available_from"] == 0
        assert item["missing_available_from"] == 0
        assert item["missing_bars"] == 0
        assert item["errors"] == 0
        for column, record in item["columns"].items():
            if column.startswith("corr_break_"):
                assert record["status"] == "EXCLUDED"
                assert record["non_null_percent"] < 95
            else:
                assert record["status"] == "MEASURED"
                assert record["non_null_percent"] >= 95
    with COVERAGE.open(newline="") as stream:
        stored = [
            (row["namespace"], row["item_id"], row["item"], row["timeframe"], row["status"], row["non_null_pct_2020_2026"], row["first_date_available"])
            for row in csv.DictReader(stream)
            if row["namespace"] in {"qqq_compare", "iwm_compare", "dia_compare"}
        ]
    assert stored == rows_from_proof(proof)
