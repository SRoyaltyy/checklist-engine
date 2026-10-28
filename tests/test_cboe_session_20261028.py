"""The 2026-10-28 CBOE rows are the published new lines only."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "CBOE_SESSION_20261028.json").read_text())


def test_three_series_are_visible_the_next_session():
    frame = pd.read_parquet(ROOT / "docs" / "cboe_session_20261028.parquet").set_index("series")
    assert list(frame.index) == ["VIX9D", "VIX3M", "VVIX"]
    assert set(frame.date.dt.strftime("%Y-%m-%d")) == {"2026-10-28"}
    assert set(frame.available_from.dt.strftime("%Y-%m-%d")) == {"2026-10-29"}
    assert int((frame.available_from <= frame.date).sum()) == 0
    assert frame.loc["VIX9D", ["open", "high", "low", "close"]].tolist() == [16.71, 17.23, 14.96, 15.60]
    assert frame.loc["VIX3M", ["open", "high", "low", "close"]].tolist() == [19.50, 19.70, 18.92, 19.22]
    assert frame.loc["VVIX", "close"] == 96.61
    assert frame.loc["VVIX", ["open", "high", "low"]].isna().all()
    assert PROOF["prior_rows_changed"] == 0
    assert "still ends 10/27/2026" in PROOF["vix"]
    assert PROOF["published_shared_release_unchanged"] == "shared-context-v2-40636949344-1"
