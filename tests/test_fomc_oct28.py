"""The October 2026 FOMC meeting includes the completed second day."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "FOMC_OCT28_CHECK.json").read_text())


def test_october_28_is_the_only_added_fomc_session():
    frame = pd.read_parquet(ROOT / "docs" / "fomc_session_20261028.parquet")
    assert list(frame.date.dt.strftime("%Y-%m-%d")) == ["2026-10-28"]
    assert list(frame.available_from.dt.strftime("%Y-%m-%d")) == ["2026-10-28"]
    assert bool(frame.is_fomc.iloc[0])
    assert PROOF["fed_label"] == "October 27-28"
    assert PROOF["published_flags_through_file_end"] == 109
    assert PROOF["published_flags_not_on_the_fed_list"] == []
    assert PROOF["fed_sessions_missing_from_the_file"] == ["2026-10-28"]
