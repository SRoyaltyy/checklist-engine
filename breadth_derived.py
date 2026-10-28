"""Breadth series derived from the accepted-universe daily counts.

Definitions are fixed:
- ad_volume_line is the cumulative sum of up volume minus down volume.
- trin is (advances / declines) / (up volume / down volume). A zero denominator
  with a positive numerator is infinite, and both zero is blank.
- mcclellan_oscillator is the 19-session exponential average of advances minus
  declines, minus the 39-session exponential average. The average is the
  recursive form seeded with the first value, alpha = 2 / (span + 1).
- mcclellan_summation is the cumulative sum of that oscillator.
- bullish percent is not built. The point-and-figure box size and reversal
  are not registered, so a current choice would be a new parameter.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FAST_SPAN = 19
SLOW_SPAN = 39
COLUMNS = (
    "ad_volume_line",
    "trin",
    "mcclellan_oscillator",
    "mcclellan_summation",
)
EXCLUDED = {
    "bullish_percent": "POINT_AND_FIGURE_BOX_AND_REVERSAL_NOT_REGISTERED",
}


def _divide(numerator, denominator):
    out = np.full(len(numerator), np.nan, dtype=np.float64)
    num = np.asarray(numerator, dtype=np.float64)
    den = np.asarray(denominator, dtype=np.float64)
    ok = den != 0
    out[ok] = num[ok] / den[ok]
    out[(~ok) & (num > 0)] = np.inf
    out[(~ok) & (num < 0)] = -np.inf
    return out


def derive(frame):
    ordered = frame.sort_values("date").reset_index(drop=True)
    if ordered["date"].duplicated().any():
        raise ValueError("duplicate breadth sessions")
    advance = ordered["advance"].to_numpy(dtype=np.float64)
    decline = ordered["decline"].to_numpy(dtype=np.float64)
    up = ordered["up_volume"].to_numpy(dtype=np.float64)
    down = ordered["down_volume"].to_numpy(dtype=np.float64)
    net = pd.Series(advance - decline)
    fast = net.ewm(span=FAST_SPAN, adjust=False).mean()
    slow = net.ewm(span=SLOW_SPAN, adjust=False).mean()
    oscillator = fast - slow
    out = pd.DataFrame({
        "date": pd.to_datetime(ordered["date"]),
        "available_from": pd.to_datetime(ordered["available_from"]),
        "ad_volume_line": np.cumsum(up - down),
        "trin": _divide(advance * down, decline * up),
        "mcclellan_oscillator": oscillator.to_numpy(dtype=np.float64),
        "mcclellan_summation": oscillator.cumsum().to_numpy(dtype=np.float64),
    })
    if (out["available_from"] <= out["date"]).any():
        raise ValueError("derived breadth is visible on its source session")
    if pd.to_datetime(out["available_from"]).dt.dayofweek.ge(5).any():
        raise ValueError("derived breadth is visible on a weekend")
    return out
