"""Join outside-the-stock panels onto approved stock days.

Industry ETF candles and the five VIX term ratios come from the published
releases. Breadth and the event calendar come from their own candle panels.
Each value stays stored once. A row is visible only when
source_candle_end < available_from <= the stock session. A weekend before the
first known session moves to the next weekday. A later weekend with no session
within four days is rejected.
"""
from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

import pandas as pd

from world_context_native import KEYS
from world_context_store import validate_factor, weighted_coverage
from world_timeframes import TIMEFRAMES

BREADTH_COLUMNS = (
    "advance", "decline", "unchanged", "new_high", "new_low", "ad_net",
    "up_volume", "down_volume", "pct_above_sma20", "pct_above_sma50",
    "pct_above_sma200", "ad_line", "new_highs_minus_new_lows", "ad_ratio",
    "up_down_volume_ratio",
)

# These 25 names are already in etf-native-context. Do not attach them again.
ATTACHED_ETFS = frozenset(
    "CPER DIA GLD HYG IBIT IWM LQD QQQ RSP SPY TLT USO UUP VXX "
    "XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY".split()
)

INDUSTRY_ETFS = frozenset(
    "KBE KRE KCE KIE XAR XTN XBI XPH XHE XHS XOP XES XME XRT XHB XSD XSW XTL".split()
)

VOL_COLUMNS = (
    "vol_vix_over_vix3m",
    "vol_vix9d_over_vix",
    "vol_vix9d_over_vix3m",
    "vol_vix3m_minus_vix",
    "vol_vix_minus_vix9d",
)

MARKET_RELEASE = "outside-market-released-v3-40667431231-1"
VOLATILITY_RELEASE = "volatility-term-native-v1-40667837889-1"


def to_native_factor(frame, prefix):
    """One timeframe. date is the source candle end."""
    out = frame.copy()
    if "timeframe" in out.columns:
        if out["timeframe"].nunique() != 1:
            raise ValueError("pass one timeframe")
        out = out.drop(columns=["timeframe"])
    if "ticker" in out.columns:
        raise ValueError("drop ticker before converting a candle panel")
    out = out.rename(columns={"date": "source_candle_end"})
    missing = [column for column in KEYS if column not in out.columns]
    if missing:
        raise ValueError("missing candle keys: " + ",".join(missing))
    feature_columns = [column for column in out.columns if column not in KEYS]
    for column in feature_columns:
        if out[column].dtype == bool:
            out[column] = out[column].astype("int8")
    out = out.rename(columns={column: prefix + column for column in feature_columns})
    out = out.sort_values("available_from").reset_index(drop=True)
    _reject_weekend_availability(out)
    return out.loc[:, list(KEYS) + [prefix + column for column in feature_columns]]


def volatility_native(frame, sessions=None):
    """A published term-factor file is already one native timeframe.

    Monthly rows in the published file sometimes use the first calendar day.
    A date that is not a session moves forward to the next session when that
    session is at most four days later. It never moves earlier. A weekend before
    the first known session moves to the next weekday, still before that
    session, so an older observed bar is not deleted. A weekend that cannot
    move without landing on or after the first session is dropped.
    """
    columns = [column for column in frame.columns if column not in KEYS]
    if columns != list(VOL_COLUMNS):
        raise ValueError("volatility term columns differ from the published five")
    out = frame.loc[:, list(KEYS) + list(VOL_COLUMNS)].copy()
    out, moved, dropped = _snap_availability(out, sessions)
    out = out.sort_values("available_from").reset_index(drop=True)
    if out.available_from.duplicated().any() or not out.available_from.is_monotonic_increasing:
        raise ValueError("volatility availability is not ordered after the session snap")
    validate_factor(out)
    out.attrs["availability_moved"] = moved
    out.attrs["availability_dropped"] = dropped
    return out


def _snap_availability(frame, sessions):
    if sessions is None:
        _reject_weekend_availability(frame)
        return frame, 0, 0
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).as_unit("ns")
    sessions = sessions[~sessions.duplicated()].sort_values()
    avail = pd.to_datetime(frame.available_from).astype("datetime64[ns]")
    ends = pd.to_datetime(frame.source_candle_end).astype("datetime64[ns]")
    positions = sessions.searchsorted(pd.DatetimeIndex(avail), side="left")
    values = avail.to_numpy().copy()
    session_values = sessions.to_numpy()
    first = pd.Timestamp(session_values[0])
    moved = 0
    for index, position in enumerate(positions):
        current = pd.Timestamp(values[index])
        if current < first:
            if current.dayofweek >= 5:
                nxt = pd.Timestamp(current.to_pydatetime() + datetime.timedelta(days=7 - int(current.dayofweek)))
                if nxt < first and nxt > pd.Timestamp(ends.iloc[index]):
                    values[index] = nxt.to_datetime64()
                    moved += 1
            continue
        if position < len(session_values) and session_values[position] == values[index]:
            continue
        if position >= len(session_values):
            continue
        nxt = pd.Timestamp(session_values[position])
        if 0 < (nxt - current).days <= 4 and nxt > pd.Timestamp(ends.iloc[index]):
            values[index] = session_values[position]
            moved += 1
    out = frame.copy()
    out["available_from"] = values
    weekends = pd.DatetimeIndex(pd.to_datetime(out.available_from)).dayofweek >= 5
    dropped = int(weekends.sum())
    out = out.loc[~weekends].reset_index(drop=True)
    if out.empty:
        raise ValueError("every volatility row fell on a weekend without a nearby session")
    return out, moved, dropped


def industry_native_frames(candles):
    """The 18 industry ETFs. The 25 already-attached names are left out."""
    if "ticker" not in candles.columns:
        raise ValueError("market candles need a ticker")
    found = set(candles["ticker"].unique())
    industry = found - ATTACHED_ETFS
    if industry != set(INDUSTRY_ETFS):
        missing = sorted(INDUSTRY_ETFS - industry)
        extra = sorted(industry - INDUSTRY_ETFS)
        raise ValueError("industry ETF set differs, missing " + ",".join(missing) + " extra " + ",".join(extra))
    if found & ATTACHED_ETFS and not (found >= ATTACHED_ETFS or industry == set(INDUSTRY_ETFS)):
        raise ValueError("market candle universe is neither the 43 nor the 18")
    frames = []
    selected = candles.loc[candles["ticker"].isin(INDUSTRY_ETFS)]
    for ticker, piece in selected.groupby("ticker", sort=True):
        bars = piece.drop(columns=["ticker"])
        seen = set()
        for timeframe, group in bars.groupby("timeframe", sort=False):
            seen.add(str(timeframe))
            native = to_native_factor(group, "etf_" + str(ticker).lower() + "_")
            validate_factor(native)
            frames.append((str(ticker), str(timeframe), native))
        if seen != set(TIMEFRAMES):
            raise ValueError(str(ticker) + " is missing a timeframe")
    return frames


def _reject_weekend_availability(frame):
    weekends = pd.DatetimeIndex(pd.to_datetime(frame.available_from)).dayofweek >= 5
    if weekends.any():
        raise ValueError("available_from falls on a weekend")


def _file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(path, digest, family, timeframe, native, source, symbol=None):
    columns = validate_factor(native)
    row = dict(
        family=family, timeframe=timeframe, release=source, asset=Path(path).name,
        sha256=digest, columns=columns,
        numeric_dtypes={column: str(native[column].dtype) for column in columns},
        native_rows=len(native),
        source_rule="source_candle_end < available_from <= stock query D",
        all_source_columns_preserved=True,
    )
    if symbol is not None:
        row["symbol"] = symbol
    return row


def _persist_native(directory, native, filename):
    folder = Path(directory) / "native"
    folder.mkdir(exist_ok=True)
    path = folder / filename
    native.to_parquet(path, index=False)
    stored = pd.read_parquet(path)
    columns = validate_factor(stored)
    if len(stored) != len(native) or columns != validate_factor(native):
        raise ValueError("persisted native frame does not match the binding")
    return path, _file_sha256(path)


def _cover_native(native, weights, timeframe, family, source_path, source_digest, source, symbol=None):
    filename = family + "_" + ((str(symbol).lower() + "_") if symbol else "") + str(timeframe) + ".parquet"
    path, digest = _persist_native(Path(source_path).parent, native, filename)
    rows = weighted_coverage(native, weights, timeframe, family)
    binding = _binding(path, digest, family, timeframe, native, source, symbol)
    binding["asset"] = "native/" + path.name
    binding["source_asset"] = Path(source_path).name
    binding["source_sha256"] = source_digest
    return rows, binding


def measure_directory(directory, weights):
    """Read a follow-on directory and measure every panel on the stock-day weights."""
    directory = Path(directory)
    rows = []
    bindings = []
    market = _first_existing(directory, ("outside_market_candles_v3.parquet", "outside_market_candles.parquet"))
    sessions = None
    if market is not None:
        market_frame = pd.read_parquet(market)
        sessions = _spy_sessions(market_frame)
        digest = _file_sha256(market)
        for ticker, timeframe, native in industry_native_frames(market_frame):
            covered, binding = _cover_native(
                native, weights, timeframe, "industry_etf", market, digest, MARKET_RELEASE, ticker)
            rows.extend(covered)
            bindings.append(binding)
    for timeframe in TIMEFRAMES:
        path = directory / ("volatility_term_" + timeframe + ".parquet")
        if not path.exists():
            continue
        digest = _file_sha256(path)
        native = volatility_native(pd.read_parquet(path), sessions)
        covered, binding = _cover_native(
            native, weights, timeframe, "volatility_term", path, digest, VOLATILITY_RELEASE)
        rows.extend(covered)
        bindings.append(binding)
    panels = (
        ("outside_breadth_candles.parquet", "breadth", "breadth_", "PR #54"),
        ("outside_event_calendar_candles.parquet", "calendar", "calendar_", "PR #52"),
    )
    for filename, family, prefix, source in panels:
        path = directory / filename
        if not path.exists():
            continue
        digest = _file_sha256(path)
        frame = pd.read_parquet(path)
        if family == "breadth":
            missing = [column for column in BREADTH_COLUMNS if column not in frame.columns]
            if missing:
                raise ValueError("breadth columns missing: " + ",".join(missing))
        for timeframe, piece in frame.groupby("timeframe", sort=False):
            native = to_native_factor(piece, prefix)
            covered, binding = _cover_native(
                native, weights, str(timeframe), family, path, digest, source)
            rows.extend(covered)
            bindings.append(binding)
    if not rows:
        raise ValueError("outside follow-on directory has no factors")
    names = [(row["timeframe"], row["column"]) for row in rows]
    if len(names) != len(set(names)):
        raise ValueError("duplicate outside follow-on columns")
    nbytes = sum(path.stat().st_size for path in directory.glob("*.parquet"))
    return rows, bindings, nbytes


def _spy_sessions(candles):
    spy = candles.loc[(candles["ticker"] == "SPY") & (candles["timeframe"] == "1d"), "date"]
    if spy.empty:
        raise ValueError("market candles have no SPY daily sessions")
    return pd.DatetimeIndex(pd.to_datetime(spy))


def validate_released_directory(directory):
    """Check the published panels. This does not count approved stock days."""
    directory = Path(directory)
    report = {"families": {}, "availability_moved": 0, "availability_dropped": 0}
    market = _first_existing(directory, ("outside_market_candles_v3.parquet", "outside_market_candles.parquet"))
    sessions = None
    if market is not None:
        market_frame = pd.read_parquet(market)
        sessions = _spy_sessions(market_frame)
        frames = industry_native_frames(market_frame)
        report["families"]["industry_etf"] = dict(
            asset=market.name, sha256=_file_sha256(market), release=MARKET_RELEASE,
            symbols=sorted({ticker for ticker, _, _ in frames}),
            timeframes=sorted({timeframe for _, timeframe, _ in frames}),
            native_frames=len(frames),
            native_rows=sum(len(native) for _, _, native in frames),
        )
    vol = {}
    moved = 0
    dropped = 0
    for timeframe in TIMEFRAMES:
        path = directory / ("volatility_term_" + timeframe + ".parquet")
        if not path.exists():
            continue
        native = volatility_native(pd.read_parquet(path), sessions)
        moved += native.attrs["availability_moved"]
        dropped += native.attrs["availability_dropped"]
        vol[timeframe] = dict(
            asset=path.name, sha256=_file_sha256(path), native_rows=len(native),
            columns=list(VOL_COLUMNS), availability_moved=native.attrs["availability_moved"],
            availability_dropped=native.attrs["availability_dropped"],
        )
    if vol:
        if set(vol) != set(TIMEFRAMES):
            raise ValueError("volatility term grid is missing a timeframe")
        report["families"]["volatility_term"] = dict(release=VOLATILITY_RELEASE, timeframes=vol)
        report["availability_moved"] = moved
        report["availability_dropped"] = dropped
    panels = (
        ("outside_breadth_candles.parquet", "breadth", "breadth_"),
        ("outside_event_calendar_candles.parquet", "calendar", "calendar_"),
    )
    for filename, family, prefix in panels:
        path = directory / filename
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        native_rows = 0
        columns = None
        for _, piece in frame.groupby("timeframe", sort=False):
            native = to_native_factor(piece, prefix)
            validate_factor(native)
            native_rows += len(native)
            columns = [column for column in native.columns if column not in KEYS]
        if set(frame["timeframe"].astype(str)) != set(TIMEFRAMES):
            raise ValueError(family + " grid is missing a timeframe")
        report["families"][family] = dict(
            asset=path.name, sha256=_file_sha256(path), timeframes=list(TIMEFRAMES),
            columns=columns, native_rows=native_rows,
        )
    if not report["families"]:
        raise ValueError("outside follow-on directory has no factors")
    return report


def attach_outside_followon(coverage, bindings, factor_bytes, weights, directory):
    rows, extra, nbytes = measure_directory(directory, weights)
    prior = {(row["timeframe"], row["column"]) for row in coverage}
    added = {(row["timeframe"], row["column"]) for row in rows}
    if prior & added:
        raise ValueError("outside follow-on repeats a column already attached")
    return list(coverage) + rows, list(bindings) + extra, factor_bytes + nbytes


def _first_existing(directory, names):
    for name in names:
        path = directory / name
        if path.exists():
            return path
    return None
