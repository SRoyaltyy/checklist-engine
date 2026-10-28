"""Month-end is the last NYSE session of the month, not the last row in the file."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "CALENDAR_MONTH_END_CORRECTION.json").read_text())


def test_october_27_is_not_month_end():
    frame = pd.read_parquet(ROOT / "docs" / "calendar_month_end.parquet")
    frame["date"] = pd.to_datetime(frame["date"])
    assert len(frame) == PROOF["rows"] == 1714
    assert int(frame.is_month_end.sum()) == 81
    october = frame.loc[frame.date == "2026-10-27", "is_month_end"]
    assert len(october) == 1
    assert not bool(october.iloc[0])
    assert bool(frame.loc[frame.date == "2020-01-31", "is_month_end"].iloc[0])
    assert "2026-10-30" not in set(frame.date.dt.strftime("%Y-%m-%d"))
    assert PROOF["only_difference"] == "2026-10-27"
    assert PROOF["october_2026_last_session"] == "2026-10-30"
    assert int((frame.available_from < frame.date).sum()) == 0
