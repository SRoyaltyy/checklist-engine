"""VIX term structure from the released FRED and CBOE files.

A row dated D uses only prints whose publication date is on or before D.
``available_from`` is the next NYSE session, so a buy-at-open reader does not
see that close early. A later FRED revision does not rewrite the close that
was already knowable. CBOE history already on the release is kept; a public
CSV may append only later sessions when the overlap closes agree.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from world_timeframes import TIMEFRAMES, completed_candles
from market_storage import exact_arrow_table,assert_exact_frame
from outside_market import completed_market_candles

WINDOW_START = pd.Timestamp("2020-01-02")
COVERAGE_MIN = 0.95
CLOSE_ATOL = 1e-4
CBOE_RELEASE = "phase1-gap-cboe-v1-40307220071-1"
CBOE_ARCHIVE = "cboe_gap_source.tar.gz"
CBOE_ARCHIVE_SHA256 = "7f5e6cc98ffa0ae632f8b22454d4641cf4402d94f5b7bfbcf115cc3c81904710"
FRED_RELEASE = "fred-structured-v3-40266650669-1"
FRED_ARCHIVE = "fred_structured_source.tar.gz"
FRED_ARCHIVE_SHA256 = "16a60d96ccbc0f9e5424bc9dc5057e3a72327a48b8036078072cca4bfbedb5d8"
OHLC_SERIES = ("VIX9D", "VIX3M")
CLOSE_SERIES = ("VIX", "VVIX")
LEVELS = ("VIX", "VIX9D", "VIX3M", "VVIX")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path, expected):
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError("archive bytes differ: " + Path(path).name)
    return actual


def divide(numerator, denominator):
    """Zero denominator and a positive numerator is +inf. Both zero is blank."""
    num = np.asarray(numerator, dtype=np.float64)
    den = np.asarray(denominator, dtype=np.float64)
    out = np.full(num.shape, np.nan, dtype=np.float64)
    finite = np.isfinite(num) & np.isfinite(den)
    both_zero = finite & (num == 0) & (den == 0)
    positive = finite & (den == 0) & (num > 0)
    negative = finite & (den == 0) & (num < 0)
    ok = finite & (den != 0)
    out[ok] = num[ok] / den[ok]
    out[positive] = np.inf
    out[negative] = -np.inf
    out[both_zero] = np.nan
    return out


def _dates(values):
    return pd.to_datetime(values).astype("datetime64[ns]")


def vix_close_known_by_session(vintages):
    """One close per observation whose vintage is on or before that observation.

    A vintage published after the observation date is ignored, so a later
    revision cannot change the close that was knowable that day.
    """
    frame = vintages.loc[:, ["obs_date", "vintage_date", "value"]].copy()
    frame["obs_date"] = _dates(frame["obs_date"])
    frame["vintage_date"] = _dates(frame["vintage_date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["obs_date", "vintage_date", "value"])
    known = frame[frame["vintage_date"] <= frame["obs_date"]]
    if known.empty:
        return pd.DataFrame(columns=["date", "vix", "vix_vintage"])
    known = known.sort_values(["obs_date", "vintage_date"])
    last = known.groupby("obs_date", as_index=False).tail(1)
    return last.rename(columns={"obs_date": "date", "value": "vix", "vintage_date": "vix_vintage"}).reset_index(drop=True)


def parse_cboe_csv(text, symbol):
    frame = pd.read_csv(io.StringIO(text))
    frame.columns = [str(column).strip().upper() for column in frame.columns]
    if "DATE" not in frame.columns:
        raise ValueError("CBOE CSV has no DATE column: " + symbol)
    frame["date"] = _dates(frame["DATE"])
    if symbol == "VVIX":
        if "VVIX" not in frame.columns:
            raise ValueError("VVIX CSV has no close")
        frame["close"] = pd.to_numeric(frame["VVIX"], errors="coerce")
        for column in ("open", "high", "low"):
            frame[column] = np.nan
    else:
        for column in ("OPEN", "HIGH", "LOW", "CLOSE"):
            if column not in frame.columns:
                raise ValueError("CBOE CSV missing " + column)
        frame = frame.rename(columns={"OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close"})
        for column in ("open", "high", "low", "close"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).sort_values("date")
    if frame["date"].duplicated().any():
        raise ValueError("duplicate CBOE sessions: " + symbol)
    return frame.loc[:, ["date", "open", "high", "low", "close"]].reset_index(drop=True)


def cboe_parquet_frame(frame, symbol):
    out = frame.copy()
    out["date"] = _dates(out["DATE"])
    if symbol == "VVIX":
        out["close"] = pd.to_numeric(out["VVIX"], errors="coerce")
        for column in ("open", "high", "low"):
            out[column] = np.nan
    else:
        out = out.rename(columns={"OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close"})
    out = out.dropna(subset=["date", "close"]).sort_values("date")
    if out["date"].duplicated().any():
        raise ValueError("duplicate released CBOE sessions: " + symbol)
    return out.loc[:, ["date", "open", "high", "low", "close"]].reset_index(drop=True)


def append_verified_tail(prior, fresh, as_of, overlap=20):
    """Keep every released row. Append later sessions only when overlap closes agree."""
    prior = prior.sort_values("date").reset_index(drop=True)
    as_of = pd.Timestamp(as_of)
    if prior.empty or prior["date"].duplicated().any():
        raise ValueError("released series is empty or duplicated")
    if prior["date"].max() > as_of:
        raise ValueError("released series contains a bar after as_of")
    note = dict(tail_status="NO_TAIL", rows_appended=0)
    if fresh is None or len(fresh) == 0:
        return prior.copy(), note
    fresh = fresh[fresh["date"] <= as_of].sort_values("date").reset_index(drop=True)
    shared = sorted(set(prior["date"]).intersection(set(fresh["date"])))
    if len(shared) < 5:
        note["tail_status"] = "OVERLAP_SHORTER_THAN_5"
        return prior.copy(), note
    window = shared[-overlap:]
    gap = float((prior.set_index("date").loc[window, "close"] - fresh.set_index("date").loc[window, "close"]).abs().max())
    if not np.isfinite(gap) or gap > CLOSE_ATOL:
        note["tail_status"] = "OVERLAP_CLOSE_MISMATCH"
        note["close_gap"] = None if not np.isfinite(gap) else gap
        return prior.copy(), note
    extra = fresh[fresh["date"] > prior["date"].max()].copy()
    note["close_gap"] = gap
    if extra.empty:
        note["tail_status"] = "NO_NEW_SESSIONS"
        return prior.copy(), note
    both = pd.concat([prior, extra.loc[:, prior.columns]], ignore_index=True)
    check = both[both["date"].isin(prior["date"])].sort_values("date")
    if not np.array_equal(check["close"].to_numpy(dtype=np.float64), prior["close"].to_numpy(dtype=np.float64)):
        raise ValueError("released close changed while extending")
    note["tail_status"] = "APPENDED"
    note["rows_appended"] = int(len(extra))
    return both.sort_values("date").reset_index(drop=True), note


def attach_available_from(frame, sessions):
    sessions = pd.DatetimeIndex(_dates(sessions))
    if sessions.has_duplicates or not sessions.is_monotonic_increasing:
        raise ValueError("session calendar must be ordered and unique")
    nxt = dict(zip(sessions[:-1], sessions[1:]))
    out = frame.copy()
    out["date"] = _dates(out["date"])
    if (~out["date"].isin(sessions)).any():
        raise ValueError("print date is not an NYSE session")
    out["available_from"] = out["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT))
    out["available_from"] = _dates(out["available_from"])
    return out


def build_daily(levels, sessions, as_of):
    """Wide daily panel. Ratios use same-session closes only."""
    as_of = pd.Timestamp(as_of)
    sessions = pd.DatetimeIndex(_dates(sessions))
    window = sessions[(sessions >= WINDOW_START) & (sessions <= as_of)]
    panel = pd.DataFrame({"date": window})
    for name, frame in levels.items():
        piece = frame.loc[frame["date"] <= as_of, ["date", "close"]].rename(columns={"close": name.lower()})
        panel = panel.merge(piece, on="date", how="left")
    panel["vix_over_vix3m"] = divide(panel["vix"], panel["vix3m"])
    panel["vix9d_over_vix"] = divide(panel["vix9d"], panel["vix"])
    panel["vix9d_over_vix3m"] = divide(panel["vix9d"], panel["vix3m"])
    panel["vix3m_minus_vix"] = panel["vix3m"] - panel["vix"]
    panel["vix_minus_vix9d"] = panel["vix"] - panel["vix9d"]
    panel = attach_available_from(panel, sessions)
    if (panel["date"] > as_of).any():
        raise ValueError("term-structure row after as_of")
    return panel


def coverage_table(panel, sessions, as_of):
    sessions = pd.DatetimeIndex(_dates(sessions))
    as_of = pd.Timestamp(as_of)
    window = sessions[(sessions >= WINDOW_START) & (sessions <= as_of)]
    rows = []
    for column in [name.lower() for name in LEVELS] + [
        "vix_over_vix3m", "vix9d_over_vix", "vix9d_over_vix3m", "vix3m_minus_vix", "vix_minus_vix9d",
    ]:
        present = panel[column].notna()
        # +inf is a real fixed outcome, not a hole.
        present = present | np.isinf(panel[column].to_numpy(dtype=np.float64))
        missing = window[~window.isin(panel.loc[present, "date"])]
        percent = float(present.mean()) if len(panel) else 0.0
        status = "PASS" if percent >= COVERAGE_MIN else "EXCLUDED"
        rows.append(dict(
            series=column, status=status,
            reason="" if status == "PASS" else "COVERAGE_BELOW_95",
            coverage_percent=round(percent * 100, 4),
            rows=int(present.sum()),
            expected_sessions=int(len(window)),
            missing_sessions=int((~present).sum()),
            missing_dates=[str(day.date()) for day in missing[:30]],
            missing_dates_truncated=bool(len(missing) > 30),
        ))
    return rows


def assert_panel_coverage(rows):
    failed = [row["series"] for row in rows if row["status"] != "PASS"]
    if failed:
        raise ValueError("volatility coverage below 95 percent: " + ",".join(failed))
    return dict(series_passed=len(rows), excluded=[])


def level_candles(levels, sessions, as_of):
    """Completed candles. VVIX and VIX are close resamples, not invented OHLC."""
    as_of = pd.Timestamp(as_of)
    session_index = pd.DatetimeIndex(_dates(sessions))
    frames = []
    for name, frame in levels.items():
        bars = frame.loc[frame["date"].isin(session_index) & (frame["date"] <= as_of), ["date", "open", "high", "low", "close"]].copy()
        if name in CLOSE_SERIES:
            bars["open"] = bars["close"]
            bars["high"] = bars["close"]
            bars["low"] = bars["close"]
            basis = "close_resample"
        else:
            basis = "vendor_ohlc"
        bars = bars.dropna(subset=["close"])
        bars["volume"] = np.nan
        for timeframe in TIMEFRAMES:
            candles = completed_market_candles(bars, timeframe, sessions)
            candles = candles[candles["date"] <= as_of].drop(columns=["volume"])
            if candles.empty:
                continue
            candles.insert(0, "series", name)
            candles.insert(1, "basis", basis)
            candles.insert(2, "timeframe", timeframe)
            frames.append(candles)
    if not frames:
        return pd.DataFrame(columns=["series", "basis", "timeframe", "candle_start", "date", "available_from", "open", "high", "low", "close"])
    return pd.concat(frames, ignore_index=True)


def ratio_candles(candles):
    """Term-structure ratios of completed candle closes. No future bucket is used."""
    pieces = []
    pairs = (
        ("vix_over_vix3m", "VIX", "VIX3M"),
        ("vix9d_over_vix", "VIX9D", "VIX"),
        ("vix9d_over_vix3m", "VIX9D", "VIX3M"),
        ("vix3m_minus_vix", "VIX3M", "VIX"),
        ("vix_minus_vix9d", "VIX", "VIX9D"),
    )
    for timeframe, group in candles.groupby("timeframe", sort=True):
        by_series = {series: frame.set_index("date") for series, frame in group.groupby("series")}
        for name, left, right in pairs:
            if left not in by_series or right not in by_series:
                continue
            merged = by_series[left][["close", "available_from"]].join(
                by_series[right][["close", "available_from"]], lsuffix="_left", rsuffix="_right", how="inner")
            if name.startswith("vix3m_minus") or name.startswith("vix_minus"):
                value = (merged["close_left"] - merged["close_right"]).to_numpy(dtype=np.float64)
            else:
                value = divide(merged["close_left"], merged["close_right"])
            stamps = merged[["available_from_left", "available_from_right"]]
            piece = pd.DataFrame({
                "series": name,
                "timeframe": timeframe,
                "date": merged.index,
                "close": np.asarray(value, dtype=np.float64),
                "available_from": stamps.max(axis=1).where(stamps.notna().all(axis=1)).to_numpy(),
            })
            pieces.append(piece.reset_index(drop=True))
    if not pieces:
        return pd.DataFrame(columns=["series", "timeframe", "date", "close", "available_from"])
    return pd.concat(pieces, ignore_index=True)


def write_lossless(frame, path, dictionary_columns):
    path = Path(path)
    sort_on = [column for column in ("series", "timeframe", "date") if column in frame.columns]
    stored = frame.sort_values(sort_on).reset_index(drop=True)
    encodings = {}
    for column in stored.columns:
        if stored[column].dtype == np.float64 or str(stored[column].dtype).startswith("float"):
            stored[column] = stored[column].astype(np.float64)
            encodings[column] = "BYTE_STREAM_SPLIT"
    dictionaries = [column for column in dictionary_columns if column in stored.columns]
    table = exact_arrow_table(stored)
    pq.write_table(
        table, path, compression="zstd", compression_level=19,
        use_dictionary=dictionaries, column_encoding=encodings, data_page_version="2.0",
    )
    assert_exact_frame(frame.sort_values(sort_on).reset_index(drop=True),pq.read_table(path).to_pandas())
    return dict(rows=len(stored), sha256=sha256_file(path), encoding="float64_byte_stream_split_zstd19",roundtrip='ALL_VALUE_BITS_EXACT')
