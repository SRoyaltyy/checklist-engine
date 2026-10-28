"""The 2026-10-28 ratio that does not need VIX, with the others left blank."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "TERM_RATIO_20261028.json").read_text())


def test_only_vix9d_over_vix3m_is_filled():
    frame = pd.read_parquet(ROOT / "docs" / "term_ratio_20261028.parquet")
    assert list(frame.date.dt.strftime("%Y-%m-%d")) == ["2026-10-28"]
    assert list(frame.available_from.dt.strftime("%Y-%m-%d")) == ["2026-10-29"]
    assert frame.vol_vix9d_over_vix3m.iloc[0] == np.float64(15.60) / np.float64(19.22)
    for column in PROOF["blank_not_zero"]:
        assert np.isnan(frame[column].iloc[0])
        assert frame[column].iloc[0] != 0
    assert PROOF["reason"] == "CBOE VIX history still ends 2026-10-27"
