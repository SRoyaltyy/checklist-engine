"""Notation votes are the five Federal Reserve notation dates, not meeting days."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "FOMC_NOTATION_CHECK.json").read_text())
FED = [
    "2020-03-19",
    "2020-03-23",
    "2020-03-31",
    "2020-08-27",
    "2025-08-22",
]


def test_the_five_notation_votes_match_the_fed_pages():
    assert PROOF["notation_votes"] == FED
    assert PROOF["also_marked_as_meeting_day"] == []
    assert PROOF["extra_flags"] == []
    assert PROOF["missing_flags"] == []
