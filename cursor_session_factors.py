"""Turn Cursor breadth and calendar candles into native context factors.

The value on a candle becomes visible at available_from, which is the next
session after the candle ends. Bool flags are stored as 0/1 integers so the
existing numeric factor check can read them. No column is dropped.

VIX, VIX9D, VIX3M, VVIX, and the released term ratios stay in the macro/CBOE
factor. The 25 index, sector, and cross-asset ETFs stay in etf-native-context.
This module adds breadth, the event-calendar flags, and the 18 industry ETFs.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from world_context_native import KEYS
from world_context_store import validate_factor, weighted_coverage

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


# These 25 names are already in etf-native-context-v1. Do not attach them again.
ATTACHED_ETFS = frozenset(
    "CPER DIA GLD HYG IBIT IWM LQD QQQ RSP SPY TLT USO UUP VXX "
    "XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY".split()
)


def cover_session_directory(directory, weights):
    """Read Cursor candle panels, if present, and measure them on the stock-day weights."""
    directory = Path(directory)
    rows = []
    specs = (
        ("outside_breadth_candles.parquet", "breadth", "breadth_"),
        ("outside_event_calendar_candles.parquet", "calendar", "calendar_"),
    )
    for filename, family, prefix in specs:
        path = directory / filename
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        for timeframe, piece in frame.groupby("timeframe"):
            rows.extend(weighted_coverage(to_native_factor(piece, prefix), weights, timeframe, family))
    market = directory / "outside_market_candles.parquet"
    if market.exists():
        frame = pd.read_parquet(market)
        industry = frame[~frame["ticker"].isin(ATTACHED_ETFS)]
        for ticker, piece in industry.groupby("ticker"):
            prefix = "etf_" + str(ticker).lower() + "_"
            bars_for_ticker = piece.drop(columns=["ticker"])
            for timeframe, bars in bars_for_ticker.groupby("timeframe"):
                rows.extend(weighted_coverage(to_native_factor(bars, prefix), weights, timeframe, "industry_etf"))
    return rows


def _file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(path, digest, family, timeframe, native, source_pr, symbol=None):
    columns = validate_factor(native)
    row = dict(
        family=family, timeframe=timeframe, release="cursor_factors", asset=path.name,
        sha256=digest, source_pr=source_pr,
        columns=columns, numeric_dtypes={column: str(native[column].dtype) for column in columns},
        native_rows=len(native),
        source_rule="source_candle_end < available_from <= stock query D",
        all_source_columns_preserved=True,
    )
    if symbol is not None:
        row["symbol"] = symbol
    return row


def session_factor_report(directory, weights):
    """Coverage rows plus store bindings for the committed candle panels."""
    directory = Path(directory)
    rows = cover_session_directory(directory, weights)
    bindings = []
    specs = (
        ("outside_breadth_candles.parquet", "breadth", "breadth_", "PR #54"),
        ("outside_event_calendar_candles.parquet", "calendar", "calendar_", "PR #52"),
    )
    for filename, family, prefix, source_pr in specs:
        path = directory / filename
        if not path.exists():
            continue
        digest = _file_sha256(path)
        frame = pd.read_parquet(path)
        for timeframe, piece in frame.groupby("timeframe"):
            bindings.append(_binding(path, digest, family, timeframe, to_native_factor(piece, prefix), source_pr))
    market = directory / "outside_market_candles.parquet"
    if market.exists():
        digest = _file_sha256(market)
        frame = pd.read_parquet(market)
        industry = frame[~frame["ticker"].isin(ATTACHED_ETFS)]
        for ticker, piece in industry.groupby("ticker"):
            prefix = "etf_" + str(ticker).lower() + "_"
            bars_for_ticker = piece.drop(columns=["ticker"])
            for timeframe, bars in bars_for_ticker.groupby("timeframe"):
                bindings.append(_binding(market, digest, "industry_etf", timeframe, to_native_factor(bars, prefix), "PR #49", symbol=str(ticker)))
    nbytes = sum(path.stat().st_size for path in directory.glob("*.parquet")) if rows else 0
    return rows, bindings, nbytes


def attach_session_factors(coverage, bindings, factor_bytes, weights, directory):
    directory = Path(directory)
    if not directory.is_dir():
        return coverage, bindings, factor_bytes
    rows, extra, nbytes = session_factor_report(directory, weights)
    if not rows:
        return coverage, bindings, factor_bytes
    return list(coverage) + rows, list(bindings) + extra, factor_bytes + nbytes
