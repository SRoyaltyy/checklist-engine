"""Test bootstrap for the calendar suite.

outside_calendar imports world_timeframes lazily inside the candle helpers.
That module is not vendored in this repo, and its absence must not stop the
calendar tests. When the real module imports, it wins. Otherwise a small
stand-in supplies the three names the calendar uses and the same visibility
rule the tests assert: a candle is visible only on the session after it
completes.

The stand-in is not used by ci/outside_event_calendar.py, which runs in its own
process, so a genuinely missing module still surfaces there.
"""

import sys
import types
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TIMEFRAMES = ["1d", "5d", "10d", "20d", "21d", "monthly"]
PRICE_COLS = ["open", "high", "low", "close", "volume"]
BLOCK_SIZES = {"5d": 5, "10d": 10, "20d": 20, "21d": 21}


def _available_from(end, sessions):
    later = sessions[sessions > pd.Timestamp(end)]
    return pd.Timestamp(later[0]) if len(later) else pd.NaT


def _spans(frame, timeframe):
    if timeframe == "1d":
        ends = list(frame["date"])
        return ends, ends
    if timeframe == "monthly":
        starts, ends = [], []
        for _, group in frame.groupby(frame["date"].dt.to_period("M"), sort=True):
            starts.append(group["date"].min())
            ends.append(group["date"].max())
        return starts, ends
    size = BLOCK_SIZES[timeframe]
    ordered = list(frame["date"])
    starts, ends = [], []
    for stop in range(size - 1, len(ordered), size):
        starts.append(ordered[stop - size + 1])
        ends.append(ordered[stop])
    return starts, ends


def completed_candles(bars, timeframe, sessions):
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).sort_values().unique()
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    starts, ends = _spans(frame, timeframe)
    return pd.DataFrame({
        "candle_start": pd.to_datetime(starts),
        "date": pd.to_datetime(ends),
        "available_from": [_available_from(end, sessions) for end in ends],
    })


def _install_stub():
    module = types.ModuleType("world_timeframes")
    module.PRICE_COLS = list(PRICE_COLS)
    module.TIMEFRAMES = list(TIMEFRAMES)
    module.completed_candles = completed_candles
    module.IS_CONFTEST_STUB = True
    sys.modules["world_timeframes"] = module


try:
    import world_timeframes  # noqa: F401
except ModuleNotFoundError:
    _install_stub()
