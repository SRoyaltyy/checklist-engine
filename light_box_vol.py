"""VIX term structure from the published light-daily index files.

No runner. Closes are the published index prints. A ratio on day D uses only
that session. ``available_from`` is the next SPY session.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from outside_vol import divide
from market_storage import exact_arrow_table,assert_exact_frame
from outside_market import completed_market_candles

RELEASE = "light-daily-box-v1-20261028"
WINDOW_START = "2020-01-02"
INDEXES = ("^VIX", "^VIX9D", "^VIX3M", "^VVIX")
NAMES = {"^VIX": "vix", "^VIX9D": "vix9d", "^VIX3M": "vix3m", "^VVIX": "vvix"}


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
    return document


def read_symbol(directory, row):
    path = Path(directory) / row["file"]
    if sha256_file(path) != row["sha256"]:
        raise ValueError("sha256 differs: " + row["file"])
    frame = pd.read_parquet(path)
    frame = frame.loc[:, ["date", "close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    if frame["date"].duplicated().any():
        raise ValueError("duplicate sessions: " + row["symbol"])
    if len(frame) != int(row["rows"]):
        raise ValueError("row count differs: " + row["symbol"])
    return frame.sort_values("date").reset_index(drop=True)


def index_rows(document):
    rows = [row for row in document["symbols"] if row["symbol"] in INDEXES]
    if [row["symbol"] for row in rows] != list(INDEXES) and set(row["symbol"] for row in rows) != set(INDEXES):
        found = sorted(row["symbol"] for row in rows)
        if set(found) != set(INDEXES):
            raise ValueError("index files differ: " + ",".join(found))
    return rows


def build_panel(directory, as_of=None):
    document = load_manifest(directory)
    spy = read_symbol(directory, next(row for row in document["symbols"] if row["symbol"] == "SPY"))
    calendar = pd.DatetimeIndex(spy["date"])
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(calendar.max())
    sessions = calendar[calendar <= as_of]
    panel = pd.DataFrame({"date": sessions})
    off_calendar = {}
    for row in index_rows(document):
        frame = read_symbol(directory, row)
        off = frame.loc[~frame["date"].isin(calendar), "date"]
        off_calendar[row["symbol"]] = [str(day.date()) for day in off]
        use = frame[frame["date"].isin(sessions)].loc[:, ["date", "close"]]
        panel = panel.merge(use.rename(columns={"close": NAMES[row["symbol"]]}), on="date", how="left")
    panel["vix_over_vix3m"] = divide(panel["vix"], panel["vix3m"])
    panel["vix9d_over_vix"] = divide(panel["vix9d"], panel["vix"])
    panel["vix9d_over_vix3m"] = divide(panel["vix9d"], panel["vix3m"])
    panel["vix3m_minus_vix"] = panel["vix3m"] - panel["vix"]
    panel["vix_minus_vix9d"] = panel["vix"] - panel["vix9d"]
    nxt = dict(zip(calendar[:-1], calendar[1:]))
    panel["available_from"] = pd.to_datetime(panel["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT))).astype("datetime64[ns]")
    if (panel["date"] > as_of).any():
        raise ValueError("term-structure row after as_of")
    return panel, document, off_calendar


def coverage(panel):
    rows = []
    for column in ("vix", "vix9d", "vix3m", "vvix", "vix_over_vix3m", "vix9d_over_vix", "vix9d_over_vix3m", "vix3m_minus_vix", "vix_minus_vix9d"):
        values = panel[column].to_numpy(dtype=np.float64)
        present = np.isfinite(values) | np.isinf(values)
        percent = float(present.mean()) if len(panel) else 0.0
        rows.append(dict(
            series=column, status="PASS" if percent >= 0.95 else "EXCLUDED",
            reason="" if percent >= 0.95 else "COVERAGE_BELOW_95",
            coverage_percent=round(percent * 100, 4),
            rows=int(present.sum()), expected_sessions=int(len(panel)),
            missing_sessions=int((~present).sum()),
        ))
    return rows


def read_ohlc(directory, row):
    path = Path(directory) / row["file"]
    if sha256_file(path) != row["sha256"]:
        raise ValueError("sha256 differs: " + row["file"])
    frame = pd.read_parquet(path)
    frame = frame.loc[:, ["date", "open", "high", "low", "close", "volume"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    return frame.sort_values("date").reset_index(drop=True)


def level_candles(directory, boundary_sessions, as_of):
    from world_timeframes import TIMEFRAMES, completed_candles
    document = load_manifest(directory)
    as_of = pd.Timestamp(as_of)
    frames = []
    for row in index_rows(document):
        bars = read_ohlc(directory, row)
        session_index = pd.DatetimeIndex(pd.to_datetime(boundary_sessions))
        bars = bars[bars["date"].isin(session_index) & (bars["date"] <= as_of)]
        for timeframe in TIMEFRAMES:
            candles = completed_market_candles(bars, timeframe, boundary_sessions)
            candles = candles[candles["date"] <= as_of]
            if candles.empty:
                continue
            candles.insert(0, "series", NAMES[row["symbol"]])
            candles.insert(1, "timeframe", timeframe)
            frames.append(candles)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def ratio_candles(candles):
    pairs = (
        ("vix_over_vix3m", "vix", "vix3m", True),
        ("vix9d_over_vix", "vix9d", "vix", True),
        ("vix9d_over_vix3m", "vix9d", "vix3m", True),
        ("vix3m_minus_vix", "vix3m", "vix", False),
        ("vix_minus_vix9d", "vix", "vix9d", False),
    )
    pieces = []
    for timeframe, group in candles.groupby("timeframe", sort=True):
        by_series = {series: frame.set_index("date") for series, frame in group.groupby("series")}
        for name, left, right, is_ratio in pairs:
            if left not in by_series or right not in by_series:
                continue
            merged = by_series[left][["close", "available_from"]].join(
                by_series[right][["close", "available_from"]], lsuffix="_l", rsuffix="_r", how="inner")
            value = divide(merged["close_l"], merged["close_r"]) if is_ratio else (merged["close_l"] - merged["close_r"]).to_numpy()
            stamps = merged[["available_from_l", "available_from_r"]]
            pieces.append(pd.DataFrame({
                "series": name, "timeframe": timeframe, "date": merged.index,
                "close": np.asarray(value, dtype=np.float64),
                "available_from": stamps.max(axis=1).where(stamps.notna().all(axis=1)).to_numpy(),
            }))
    if not pieces:
        return pd.DataFrame(columns=["series", "timeframe", "date", "close", "available_from"])
    return pd.concat(pieces, ignore_index=True)


def write_panel(frame, path):
    sort_on = [column for column in ("series", "timeframe", "date") if column in frame.columns]
    stored = frame.sort_values(sort_on).reset_index(drop=True)
    encodings = {}
    for column in stored.columns:
        if stored[column].dtype == np.float64:
            encodings[column] = "BYTE_STREAM_SPLIT"
    table = exact_arrow_table(stored)
    pq.write_table(table, path, compression="zstd", compression_level=19, use_dictionary=False,
                   column_encoding=encodings, data_page_version="2.0")
    assert_exact_frame(frame.sort_values(sort_on).reset_index(drop=True),pq.read_table(path).to_pandas())
    return dict(rows=len(stored), sha256=sha256_file(path), encoding="float64_byte_stream_split_zstd19",roundtrip='ALL_VALUE_BITS_EXACT')


def proof_from_release(directory, out_dir, as_of=None):
    panel, document, off_calendar = build_panel(directory, as_of=as_of)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    storage = write_panel(panel, out_dir / "outside_vol_daily.parquet")
    as_of_stamp = pd.Timestamp(panel["date"].max())
    import exchange_calendars as xcals
    calendar = xcals.get_calendar("XNYS", start="1990-01-01")
    end = str((as_of_stamp + pd.offsets.Day(40)).date())
    boundary = pd.DatetimeIndex(calendar.sessions_in_range("2019-12-02", end)).tz_localize(None)
    candles = level_candles(directory, boundary, as_of_stamp)
    ratios = ratio_candles(candles)
    candle_storage = write_panel(candles, out_dir / "outside_vol_candles.parquet")
    ratio_storage = write_panel(ratios, out_dir / "outside_vol_ratio_candles.parquet")
    rows = coverage(panel)
    failed = [row["series"] for row in rows if row["status"] != "PASS"]
    proof = dict(
        block="outside_vol_term",
        release=RELEASE,
        source=document.get("source"),
        window_start=WINDOW_START,
        as_of=str(pd.Timestamp(panel["date"].max()).date()),
        vix_note="Published Yahoo ^VIX close from this release. It has no ALFRED vintage column. available_from is the next SPY session.",
        off_spy_calendar=off_calendar,
        summary=dict(series_passed=len(rows) - len(failed), excluded=[row for row in rows if row["status"] != "PASS"]),
        series=rows,
        storage=storage,
        candles=candle_storage,
        ratio_candles=ratio_storage,
        lookahead="ratios use same-session closes; available_from is the next SPY session",
    )
    if failed:
        raise ValueError("volatility coverage below 95 percent: " + ",".join(failed))
    path = out_dir / "OUTSIDE_VOL_TERM_PROOF.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    return proof
