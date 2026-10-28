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


def derive_candles(panel, sessions):
    """Completed buckets of the derived series.

    TRIN is rebuilt from the summed advance, decline, up volume, and down
    volume. The volume line, McClellan oscillator, and McClellan summation are
    the last session in the bucket. The 19 and 39 spans stay daily sessions.
    A bucket with no later session on the calendar is omitted.
    """
    from world_timeframes import TIMEFRAMES

    daily = derive(panel)
    ordered = panel.sort_values("date").reset_index(drop=True)
    flows = ordered[["date", "advance", "decline", "up_volume", "down_volume"]].copy()
    flows["date"] = pd.to_datetime(flows["date"])
    frame = daily.merge(flows, on="date", how="left")
    calendar = pd.DatetimeIndex(pd.to_datetime(sessions)).sort_values().unique()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    positions = calendar.get_indexer(frame["date"])
    if (positions < 0).any():
        raise ValueError("breadth date is outside the session calendar")
    rows = []
    for timeframe in TIMEFRAMES:
        if timeframe == "monthly":
            key = frame["date"].dt.to_period("M")
            complete_end = {}
            for period in key.unique():
                month_sessions = calendar[calendar.to_period("M") == period]
                if len(month_sessions) == 0 or month_sessions[-1] >= calendar[-1]:
                    continue
                complete_end[period] = month_sessions[-1]
        else:
            size = int(timeframe[:-1])
            key = positions // size
            complete_end = {}
            for item in np.unique(key):
                if (item + 1) * size >= len(calendar):
                    continue
                complete_end[item] = calendar[(item + 1) * size - 1]
        for item, part in frame.groupby(key, sort=True):
            if item not in complete_end:
                continue
            end = pd.Timestamp(complete_end[item])
            if pd.Timestamp(part["date"].max()) != end:
                continue
            advance = float(part["advance"].sum())
            decline = float(part["decline"].sum())
            up = float(part["up_volume"].sum())
            down = float(part["down_volume"].sum())
            last = part.iloc[-1]
            rows.append({
                "timeframe": timeframe,
                "candle_start": pd.Timestamp(part["date"].min()),
                "date": end,
                "available_from": pd.Timestamp(calendar[calendar > end][0]),
                "ad_volume_line": float(last["ad_volume_line"]),
                "trin": float(_divide([advance * down], [decline * up])[0]),
                "mcclellan_oscillator": float(last["mcclellan_oscillator"]),
                "mcclellan_summation": float(last["mcclellan_summation"]),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    if (out["available_from"] <= out["date"]).any():
        raise ValueError("derived candle is visible on its source session")
    if out["available_from"].dt.dayofweek.ge(5).any():
        raise ValueError("derived candle is visible on a weekend")
    return out
