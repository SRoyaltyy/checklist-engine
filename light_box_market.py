"""Build the market panel from James's published light-daily release.

No network and no GitHub runner. The release manifest is the coverage record.
``available_from`` is the next reference session, so a buy-at-open reader does
not see that close early.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from market_storage import exact_int64,exact_arrow_table,assert_exact_frame

RELEASE = "light-daily-box-v1-20261028"
WINDOW_START = "2020-01-02"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(directory):
    document = json.loads((Path(directory) / "manifest.json").read_text())
    if document.get("window_start") != WINDOW_START:
        raise ValueError("unexpected window start")
    symbols = document["symbols"]
    if len(symbols) != len({row["symbol"] for row in symbols}):
        raise ValueError("duplicate symbol in the light-daily manifest")
    return document


def etf_rows(document):
    return [row for row in document["symbols"] if not str(row["symbol"]).startswith("^")]


def read_symbol(directory, row):
    path = Path(directory) / row["file"]
    actual = sha256_file(path)
    if actual != row["sha256"]:
        raise ValueError("sha256 differs: " + row["file"])
    frame = pd.read_parquet(path)
    required = {"date", "open", "high", "low", "close", "adj_close", "volume"}
    if not required <= set(frame.columns):
        raise ValueError("columns differ: " + row["symbol"])
    frame = frame.loc[:, ["date", "open", "high", "low", "close", "adj_close", "volume"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    frame["ticker"] = row["symbol"]
    if frame["date"].duplicated().any() or not frame["date"].is_monotonic_increasing:
        raise ValueError("dates differ: " + row["symbol"])
    if len(frame) != int(row["rows"]):
        raise ValueError("row count differs: " + row["symbol"])
    return frame


def attach_available_from(frame, calendar):
    calendar = pd.DatetimeIndex(pd.to_datetime(calendar)).sort_values().unique()
    nxt = dict(zip(calendar[:-1], calendar[1:]))
    out = frame.copy()
    missing = ~out["date"].isin(calendar)
    if missing.any():
        raise ValueError("bar date is outside the reference calendar")
    out["available_from"] = pd.to_datetime(out["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT))).astype("datetime64[ns]")
    return out


def build_panel(directory, as_of=None):
    directory = Path(directory)
    document = load_manifest(directory)
    rows = etf_rows(document)
    frames = [read_symbol(directory, row) for row in rows]
    spy = next(frame for frame in frames if frame["ticker"].iloc[0] == "SPY")
    calendar = pd.DatetimeIndex(spy["date"])
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(calendar.max())
    if as_of > calendar.max():
        raise ValueError("as_of is after the published calendar")
    kept = []
    for frame in frames:
        cut = frame[frame["date"] <= as_of]
        if (frame["date"] > calendar.max()).any():
            raise ValueError("bar after the reference calendar")
        kept.append(attach_available_from(cut, calendar))
    panel = pd.concat(kept, ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)
    if (panel["date"] > as_of).any():
        raise ValueError("panel row after as_of")
    return panel, document, rows


def write_panel(frame, path):
    path = Path(path)
    stored = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    for column in ("open", "high", "low", "close", "adj_close"):
        stored[column] = stored[column].astype(np.float64)
    integers=exact_int64(stored['volume'].to_numpy())
    stored['volume']=integers if integers is not None else stored['volume'].astype(np.float64)
    table = exact_arrow_table(stored)
    pq.write_table(
        table, path, compression="zstd", compression_level=19, use_dictionary=["ticker"],
        column_encoding={column:("DELTA_BINARY_PACKED" if stored[column].dtype.kind in 'iu' else "BYTE_STREAM_SPLIT")
                         for column in stored if stored[column].dtype.kind in 'fiu'},
        data_page_version="2.0",
    )
    assert_exact_frame(frame.sort_values(['ticker','date']).reset_index(drop=True),pq.read_table(path).to_pandas())
    return dict(rows=len(stored), sha256=sha256_file(path), encoding="float64_byte_stream_split_exact_volume_zstd19",roundtrip='ALL_VALUE_BITS_EXACT')


def build_candles(panel, boundary_sessions, as_of):
    """Completed candles. A bucket that is still open on as_of is omitted."""
    from world_timeframes import TIMEFRAMES
    from outside_market import completed_market_candles
    as_of = pd.Timestamp(as_of)
    frames = []
    for ticker, bars in panel.groupby("ticker", sort=True):
        piece = bars.loc[bars["date"] <= as_of, ["date", "open", "high", "low", "close", "volume"]].sort_values("date")
        for timeframe in TIMEFRAMES:
            candles = completed_market_candles(piece, timeframe, boundary_sessions)
            candles = candles[candles["date"] <= as_of]
            if candles.empty:
                continue
            candles.insert(0, "ticker", ticker)
            candles.insert(1, "timeframe", timeframe)
            frames.append(candles)
    if not frames:
        return pd.DataFrame(columns=["ticker", "timeframe", "candle_start", "date", "available_from", "open", "high", "low", "close", "volume"])
    out = pd.concat(frames, ignore_index=True)
    if (out["date"] > as_of).any():
        raise ValueError("candle after as_of")
    return out


def write_candles(frame, path):
    path = Path(path)
    stored = frame.sort_values(["ticker", "timeframe", "date"]).reset_index(drop=True)
    for column in ("open", "high", "low", "close"):
        stored[column] = stored[column].astype(np.float64)
    integers=exact_int64(stored['volume'].to_numpy())
    stored['volume']=integers if integers is not None else stored['volume'].astype(np.float64)
    table = exact_arrow_table(stored)
    pq.write_table(
        table, path, compression="zstd", compression_level=19, use_dictionary=["ticker", "timeframe"],
        column_encoding={
            "open": "BYTE_STREAM_SPLIT", "high": "BYTE_STREAM_SPLIT", "low": "BYTE_STREAM_SPLIT",
            "close": "BYTE_STREAM_SPLIT", "volume": "DELTA_BINARY_PACKED" if integers is not None else "BYTE_STREAM_SPLIT",
        },
        data_page_version="2.0",
    )
    assert_exact_frame(frame.sort_values(['ticker','timeframe','date']).reset_index(drop=True),pq.read_table(path).to_pandas())
    return dict(rows=len(stored), sha256=sha256_file(path), timeframes=sorted(stored.timeframe.unique()),
                encoding="float64_byte_stream_split_exact_volume_zstd19",roundtrip='ALL_VALUE_BITS_EXACT')


def proof_from_release(directory, out_dir, as_of=None, boundary_sessions=None):
    panel, document, rows = build_panel(directory, as_of=as_of)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    storage = write_panel(panel, out_dir / "outside_market_daily.parquet")
    as_of_stamp = pd.Timestamp(panel["date"].max())
    if boundary_sessions is None:
        import exchange_calendars as xcals
        calendar = xcals.get_calendar("XNYS", start="1990-01-01")
        end = str((as_of_stamp + pd.offsets.Day(40)).date())
        boundary_sessions = pd.DatetimeIndex(calendar.sessions_in_range("2019-12-02", end)).tz_localize(None)
    candles = build_candles(panel, boundary_sessions, as_of_stamp)
    candle_storage = write_candles(candles, out_dir / "outside_market_candles.parquet")
    failed = [row["symbol"] for row in rows if row.get("status") != "PASS" or float(row.get("coverage", 0)) < 0.95]
    proof = dict(
        block="outside_market_daily",
        release=RELEASE,
        source=document.get("source"),
        window_start=document.get("window_start"),
        as_of=str(pd.Timestamp(panel["date"].max()).date()),
        symbols_requested=len(rows),
        symbols_passed=len(rows) - len(failed),
        excluded=[{"symbol": symbol, "reason": "COVERAGE_BELOW_95_OR_MANIFEST_FAIL"} for symbol in failed],
        manifest_coverage=[
            dict(symbol=row["symbol"], rows=row["rows"], first=row["first"], last=row["last"],
                 coverage=row["coverage"], status=row["status"], sha256=row["sha256"])
            for row in rows
        ],
        storage=storage,
        candles=candle_storage,
        lookahead="session date is that close; available_from is the next session; an unfinished candle is omitted",
        window_gaps=[
            dict(symbol=symbol, reason="LISTED_AFTER_WINDOW_START",
                 first=str(pd.Timestamp(group["date"].min()).date()),
                 rows=int(len(group)),
                 full_window_sessions=int(len(panel.loc[panel.ticker == "SPY"])),
                 full_window_percent=round(100 * len(group) / max(len(panel.loc[panel.ticker == "SPY"]), 1), 4),
                 note="Bars before the listing are absent, not zero. The series is kept from the listing date. It does not cover 95 percent of 2020-01-02 through the last session.")
            for symbol, group in panel.groupby("ticker")
            if pd.Timestamp(group["date"].min()) > pd.Timestamp("2020-01-02")
        ],
        price_basis="published open/high/low/close plus adj_close and volume; nothing recomputed",
    )
    if failed:
        raise ValueError("light-daily ETF coverage below 95 percent: " + ",".join(failed))
    path = out_dir / "OUTSIDE_MARKET_DAILY_PROOF.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    return proof
