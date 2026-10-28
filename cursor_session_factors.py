"""Turn Cursor breadth and calendar candles into native context factors.

The value on a candle becomes visible at available_from, which is the next
session after the candle ends. Bool flags are stored as 0/1 integers so the
existing numeric factor check can read them. No column is dropped.
"""
from __future__ import annotations

import pandas as pd

from world_context_native import KEYS

BREADTH_COLUMNS = (
    "advance", "decline", "unchanged", "new_high", "new_low", "ad_net",
    "up_volume", "down_volume", "pct_above_sma20", "pct_above_sma50",
    "pct_above_sma200", "ad_line", "new_highs_minus_new_lows", "ad_ratio",
    "up_down_volume_ratio",
)


def to_native_factor(frame, prefix):
    """One timeframe. date is the source candle end."""
    out = frame.copy()
    if "timeframe" in out.columns:
        if out["timeframe"].nunique() != 1:
            raise ValueError("pass one timeframe")
        out = out.drop(columns=["timeframe"])
    out = out.rename(columns={"date": "source_candle_end"})
    missing = [column for column in ("candle_start", "source_candle_end", "available_from") if column not in out]
    if missing:
        raise ValueError("missing candle keys: " + ",".join(missing))
    feature_columns = [column for column in out.columns if column not in KEYS]
    for column in feature_columns:
        if out[column].dtype == bool:
            out[column] = out[column].astype("int8")
    out = out.rename(columns={column: prefix + column for column in feature_columns})
    out = out.sort_values("available_from").reset_index(drop=True)
    return out.loc[:, list(KEYS) + [prefix + column for column in feature_columns]]
