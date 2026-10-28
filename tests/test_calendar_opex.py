"""Published options-expiry flags match the third-Friday rule."""

import json
from pathlib import Path

import exchange_calendars as xc
import pandas as pd

from calendar_opex import expiry_sessions

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "OPEX_EXPIRY_CHECK.json").read_text())


def test_the_published_flags_are_the_third_friday_sessions():
    sessions = xc.get_calendar("XNYS").sessions_in_range("2020-01-02", "2026-10-27")
    found = [str(day.date()) for day in expiry_sessions(sessions)]
    assert found == PROOF["flags"]
    assert len(found) == 82
    assert found[0] == "2020-01-17"
    assert found[-1] == "2026-10-16"
    assert PROOF["mismatches"] == 0


def test_the_countdown_after_october_expiry_reaches_november():
    sessions = list(pd.DatetimeIndex(
        xc.get_calendar("XNYS").sessions_in_range("2026-10-19", "2026-11-20")
    ))
    after = [day for day in sessions if day > pd.Timestamp("2026-10-19")]
    assert len(after) == 24
    assert str(after[-1].date()) == "2026-11-20"
    assert PROOF["after_last_in_file"]["published_days_to_opex_on_2026_10_19"] == 24
