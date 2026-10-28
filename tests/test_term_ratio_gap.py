"""Term ratios for the three sessions that now have all three closes."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads((ROOT / "docs" / "TERM_RATIO_GAP_20261023.json").read_text())


def test_ratios_are_the_same_formulas_as_the_release_row():
    frame = pd.read_parquet(ROOT / "docs" / "term_ratios_20261023_20261027.parquet")
    assert list(frame.date.dt.strftime("%Y-%m-%d")) == PROOF["sessions"]
    assert int((frame.available_from <= frame.date).sum()) == 0
    assert int(frame.available_from.dt.dayofweek.ge(5).sum()) == 0
    assert frame.vol_vix_over_vix3m.tolist() == (frame.vix_close / frame.vix3m_close).tolist()
    assert frame.vix9d_vix_term_ratio.tolist() == (frame.vix9d_close / frame.vix_close).tolist()
    assert frame.vix3m_vix_term_ratio.tolist() == (frame.vix3m_close / frame.vix_close).tolist()
    assert frame.vol_vix9d_over_vix.tolist() == frame.vix9d_vix_term_ratio.tolist()
    assert frame.vol_vix9d_over_vix3m.tolist() == (frame.vix9d_close / frame.vix3m_close).tolist()
    assert frame.vol_vix3m_minus_vix.tolist() == (frame.vix3m_close - frame.vix_close).tolist()
    assert frame.vol_vix_minus_vix9d.tolist() == (frame.vix_close - frame.vix9d_close).tolist()
    assert frame.loc[frame.date == "2026-10-23", "vol_vix_over_vix3m"].iloc[0] == 19.45 / 20.48
    assert "2026-10-28" in PROOF["not_computed"]
