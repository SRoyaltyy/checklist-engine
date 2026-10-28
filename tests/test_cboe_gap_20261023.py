"""The CBOE sessions after the shared-context release and before 2026-10-28."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "CBOE_GAP_20261023.json").read_text())


def test_three_sessions_for_four_series():
    frame = pd.read_parquet(ROOT / "docs" / "cboe_sessions_20261023_20261027.parquet")
    assert len(frame) == 12
    assert set(frame.series) == {"VIX", "VIX9D", "VIX3M", "VVIX"}
    assert set(frame.date.dt.strftime("%Y-%m-%d")) == {"2026-10-23", "2026-10-26", "2026-10-27"}
    assert int((frame.available_from <= frame.date).sum()) == 0
    assert int(frame.available_from.dt.dayofweek.ge(5).sum()) == 0
    vix = frame[frame.series == "VIX"].set_index(frame.loc[frame.series == "VIX", "date"].dt.strftime("%Y-%m-%d"))
    assert vix.loc["2026-10-23", "close"] == 19.45
    assert vix.loc["2026-10-23", "available_from"].strftime("%Y-%m-%d") == "2026-10-26"
    assert vix.loc["2026-10-27", "close"] == 17.52
    vvix = frame[frame.series == "VVIX"]
    assert vvix[["open", "high", "low"]].isna().all().all()
    assert PROOF["vix_2026_10_28"] == "NOT_IN_CBOE_HISTORY"
    assert PROOF["cboe_match_on_2026_10_22"] is True
