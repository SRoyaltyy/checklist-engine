"""Market breadth from daily bars. Windows end on session D.

Percent above a moving average, new highs, and new lows use only bars through
D. The advance/decline line on D adds only that session's advances and
declines. A later bar cannot change an earlier row.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

STITCH_RELEASE = "accepted-price-stitch-v2-40494479693-1"
STITCH_MANIFEST = "ACCEPTED_PRICE_STITCH.json"
STITCH_MANIFEST_SHA256 = "9f97db992522777ef9ae27a0ec9aad4fb9caa80a269393b0d76521aa9aa3f6fe"
WINDOW_START = pd.Timestamp("2020-01-02")
SMA_WINDOWS = (20, 50, 200)
HIGH_LOW_WINDOW = 252
COUNT_COLUMNS = (
    "eligible_sma20", "above_sma20", "eligible_sma50", "above_sma50",
    "eligible_sma200", "above_sma200", "eligible_52w", "new_high", "new_low",
    "advance", "decline", "unchanged", "up_volume", "down_volume",
)


def checked_sessions(values):
    dates = pd.DatetimeIndex(pd.to_datetime(values)).as_unit('ns')
    if (dates.empty or dates.tz is not None or dates.hasnans
            or dates.has_duplicates or not dates.is_monotonic_increasing):
        raise ValueError('breadth calendar must be ordered unique naive sessions')
    return dates


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path, expected):
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError("bytes differ: " + Path(path).name)
    return actual


def _sma_above(close, window):
    eligible = np.zeros(len(close), dtype=np.int64)
    above = np.zeros(len(close), dtype=np.int64)
    if len(close) < window or not np.isfinite(close).all():
        finite = np.isfinite(close)
        if len(close) < window or not finite.all():
            # A gap makes the simple rolling sum unsafe. Fall back to a strict window.
            for index in range(window - 1, len(close)):
                sample = close[index - window + 1:index + 1]
                if np.isfinite(sample).all():
                    eligible[index] = 1
                    above[index] = int(close[index] > sample.mean())
            return eligible, above
    sums = np.cumsum(close)
    totals = np.empty(len(close))
    totals[window - 1] = sums[window - 1]
    if len(close) > window:
        totals[window:] = sums[window:] - sums[:-window]
    eligible[window - 1:] = 1
    above[window - 1:] = close[window - 1:] > (totals[window - 1:] / window)
    return eligible, above


def _new_extreme(values, higher):
    """Strict extreme versus the prior 251 bars. The current bar is not in that window."""
    series = pd.Series(np.asarray(values, dtype=np.float64))
    prior = series.rolling(HIGH_LOW_WINDOW - 1, min_periods=HIGH_LOW_WINDOW - 1)
    prior = (prior.max() if higher else prior.min()).shift(1)
    eligible = prior.notna().to_numpy(dtype=np.int64)
    comparison = series.gt(prior) if higher else series.lt(prior)
    flag = (comparison & prior.notna()).fillna(False).to_numpy(dtype=np.int64)
    return eligible, flag


def stock_contributions(frame):
    """Integer votes for one name. Empty when the frame has no usable bars."""
    bars = frame.sort_values("date").reset_index(drop=True)
    if bars["date"].duplicated().any():
        raise ValueError("duplicate sessions")
    dates = pd.to_datetime(bars["date"]).astype("datetime64[ns]")
    high = bars["high"].to_numpy(dtype=np.float64)
    low = bars["low"].to_numpy(dtype=np.float64)
    close = bars["close"].to_numpy(dtype=np.float64)
    volume = bars["volume"].to_numpy(dtype=np.float64)
    out = pd.DataFrame({"date": dates})
    for window in SMA_WINDOWS:
        eligible, above = _sma_above(close, window)
        out[f"eligible_sma{window}"] = eligible
        out[f"above_sma{window}"] = above
    eligible, new_high = _new_extreme(high, True)
    _, new_low = _new_extreme(low, False)
    out["eligible_52w"] = eligible
    out["new_high"] = new_high
    out["new_low"] = new_low
    advance = np.zeros(len(close), dtype=np.int64)
    decline = np.zeros(len(close), dtype=np.int64)
    unchanged = np.zeros(len(close), dtype=np.int64)
    up_volume = np.zeros(len(close), dtype=np.float64)
    down_volume = np.zeros(len(close), dtype=np.float64)
    if len(close) > 1:
        change = close[1:] - close[:-1]
        finite = np.isfinite(change)
        advance[1:] = (finite & (change > 0)).astype(np.int64)
        decline[1:] = (finite & (change < 0)).astype(np.int64)
        unchanged[1:] = (finite & (change == 0)).astype(np.int64)
        vol = np.where(np.isfinite(volume[1:]), volume[1:], 0.0)
        up_volume[1:] = np.where(advance[1:] == 1, vol, 0.0)
        down_volume[1:] = np.where(decline[1:] == 1, vol, 0.0)
    out["advance"] = advance
    out["decline"] = decline
    out["unchanged"] = unchanged
    out["up_volume"] = up_volume
    out["down_volume"] = down_volume
    return out


def divide(numerator, denominator):
    num = np.asarray(numerator, dtype=np.float64)
    den = np.asarray(denominator, dtype=np.float64)
    out = np.full(num.shape, np.nan)
    finite = np.isfinite(num) & np.isfinite(den)
    out[finite & (den == 0) & (num > 0)] = np.inf
    out[finite & (den == 0) & (num < 0)] = -np.inf
    out[finite & (den != 0)] = num[finite & (den != 0)] / den[finite & (den != 0)]
    return out


def aggregate(contributions, sessions, as_of, retain_history=False):
    """Sum votes causally. V2 retains all supplied calendar history explicitly.

    The cumulative line starts at the first retained session. Changing its
    origin therefore requires a new release; V1 remains separately retained.
    """
    as_of = pd.Timestamp(as_of)
    sessions = checked_sessions(sessions)
    rows = sessions[sessions <= as_of]
    if not retain_history:
        rows = rows[rows >= WINDOW_START]
    panel = pd.DataFrame({"date": rows})
    if contributions is None or len(contributions) == 0:
        for column in COUNT_COLUMNS:
            panel[column] = 0
    else:
        votes = contributions[contributions["date"] <= as_of]
        grouped = votes.groupby("date", as_index=False)[list(COUNT_COLUMNS)].sum()
        panel = panel.merge(grouped, on="date", how="left")
        for column in COUNT_COLUMNS:
            panel[column] = panel[column].fillna(0)
    panel["pct_above_sma20"] = divide(panel["above_sma20"], panel["eligible_sma20"])
    panel["pct_above_sma50"] = divide(panel["above_sma50"], panel["eligible_sma50"])
    panel["pct_above_sma200"] = divide(panel["above_sma200"], panel["eligible_sma200"])
    panel["new_highs_minus_new_lows"] = panel["new_high"] - panel["new_low"]
    panel["ad_net"] = panel["advance"] - panel["decline"]
    panel["ad_line"] = panel["ad_net"].cumsum()
    panel["ad_ratio"] = divide(panel["advance"], panel["decline"])
    panel["up_down_volume_ratio"] = divide(panel["up_volume"], panel["down_volume"])
    nxt = dict(zip(sessions[:-1], sessions[1:]))
    panel["available_from"] = panel["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT))
    panel["available_from"] = pd.to_datetime(panel["available_from"]).astype("datetime64[ns]")
    if (panel["date"] > as_of).any():
        raise ValueError("breadth row after as_of")
    return panel


def coverage_row(panel, sessions, as_of):
    sessions = checked_sessions(sessions)
    as_of = pd.Timestamp(as_of)
    window = sessions[(sessions >= WINDOW_START) & (sessions <= as_of)]
    present = panel.loc[(panel.date >= WINDOW_START) & (panel.date <= as_of), "pct_above_sma20"].notna()
    # A session with eligible names has a percent. Zero eligible is a hole, not a zero.
    matched = window.isin(panel.loc[panel["eligible_sma20"] > 0, "date"])
    percent = float(matched.mean()) if len(window) else 0.0
    missing = window[~matched]
    return dict(
        series="pct_above_sma20",
        status="PASS" if percent >= 0.95 else "EXCLUDED",
        reason="" if percent >= 0.95 else "COVERAGE_BELOW_95",
        coverage_percent=round(percent * 100, 4),
        expected_sessions=int(len(window)),
        missing_sessions=int((~matched).sum()),
        missing_dates=[str(day.date()) for day in missing[:30]],
        rows=int(present.sum()) if len(panel) else 0,
    )


def assert_breadth(summary, stocks_used, stocks_expected):
    if stocks_expected <= 0:
        raise ValueError("no accepted names")
    percent = stocks_used / stocks_expected
    if percent < 0.95:
        raise ValueError("breadth names below 95 percent")
    if summary["status"] != "PASS":
        raise ValueError("breadth sessions below 95 percent")
    return dict(names_used=int(stocks_used), names_expected=int(stocks_expected),
                names_percent=round(percent * 100, 4))


def breadth_candles(panel, boundary_sessions):
    """Completed buckets of the market-wide series. Flows are summed. Levels use the last session.

    New highs minus new lows, the advance/decline ratio, and the up/down volume
    ratio are rebuilt from the summed counts. Copying the last session would
    drop the other sessions in the bucket.
    """
    from world_timeframes import TIMEFRAMES
    sessions = checked_sessions(boundary_sessions)
    frame = panel.sort_values("date").reset_index(drop=True)
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    if frame.date.duplicated().any():
        raise ValueError("duplicate breadth sessions")
    positions = sessions.get_indexer(frame["date"])
    if (positions < 0).any():
        raise ValueError("breadth date is outside the session calendar")
    flows = ["advance", "decline", "unchanged", "new_high", "new_low", "ad_net", "up_volume", "down_volume"]
    # Percents and the cumulative line are the end session. Counts and ratios are rebuilt from the bucket.
    levels = ["pct_above_sma20", "pct_above_sma50", "pct_above_sma200", "ad_line"]
    frames = []
    for timeframe in TIMEFRAMES:
        if timeframe == "monthly":
            key = frame["date"].dt.to_period("M")
            complete_end = {}
            for period in key.unique():
                month_sessions = sessions[sessions.to_period("M") == period]
                if len(month_sessions) == 0 or month_sessions[-1] >= sessions[-1]:
                    continue
                complete_end[period] = month_sessions[-1]
        else:
            k = int(timeframe[:-1])
            bucket = positions // k
            key = bucket
            complete_end = {}
            for item in np.unique(bucket):
                if (item + 1) * k >= len(sessions):
                    continue
                complete_end[item] = sessions[(item + 1) * k - 1]
        grouped = frame.groupby(key, sort=True)
        for item, part in grouped:
            if item not in complete_end:
                continue
            end = pd.Timestamp(complete_end[item])
            if timeframe == "monthly":
                expected = sessions[sessions.to_period("M") == item]
            else:
                expected = sessions[item * k:(item + 1) * k]
            if (len(part) != len(expected)
                    or not pd.DatetimeIndex(part.date).equals(pd.DatetimeIndex(expected))
                    or part["date"].max() != end):
                continue
            row = {"timeframe": timeframe, "date": end, "candle_start": part["date"].min()}
            for column in flows:
                row[column] = part[column].sum()
            last = part.iloc[-1]
            for column in levels:
                row[column] = last[column]
            row["new_highs_minus_new_lows"] = row["new_high"] - row["new_low"]
            row["ad_ratio"] = divide([row["advance"]], [row["decline"]])[0]
            row["up_down_volume_ratio"] = divide([row["up_volume"]], [row["down_volume"]])[0]
            row["available_from"] = sessions[sessions > end][0] if (sessions > end).any() else pd.NaT
            frames.append(row)
    return pd.DataFrame(frames)


def write_lossless(frame, path):
    from market_storage import exact_int64, exact_arrow_table, assert_exact_frame
    path = Path(path)
    sort_on = [column for column in ("timeframe", "date") if column in frame.columns]
    stored = frame.sort_values(sort_on).reset_index(drop=True)
    encodings = {}
    for column in COUNT_COLUMNS:
        if column in stored.columns and stored[column].notna().all():
            if column.endswith("volume"):
                stored[column] = stored[column].astype(np.float64)
                encodings[column] = "BYTE_STREAM_SPLIT"
            else:
                integers = exact_int64(stored[column])
                if integers is None:
                    raise ValueError("nonintegral or out-of-range breadth count: " + column)
                stored[column] = integers
                encodings[column] = "DELTA_BINARY_PACKED"
    for column in ("pct_above_sma20", "pct_above_sma50", "pct_above_sma200", "ad_ratio", "up_down_volume_ratio"):
        stored[column] = stored[column].astype(np.float64)
        encodings[column] = "BYTE_STREAM_SPLIT"
    for column in ("new_highs_minus_new_lows", "ad_net", "ad_line"):
        integers = exact_int64(stored[column])
        if integers is None:
            raise ValueError("nonintegral or out-of-range breadth count: " + column)
        stored[column] = integers
        encodings[column] = "DELTA_BINARY_PACKED"
    table = exact_arrow_table(stored)
    pq.write_table(
        table, path, compression="zstd", compression_level=19,
        use_dictionary=False, column_encoding=encodings, data_page_version="2.0",
    )
    assert_exact_frame(stored, pd.read_parquet(path))
    return dict(rows=len(stored), sha256=sha256_file(path), encoding="int64_delta_and_float64_byte_stream_split_zstd19")
