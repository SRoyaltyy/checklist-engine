"""Market and cross-asset daily bars outside a single stock.

A row dated D is that session's own close. ``available_from`` is the next
NYSE session, so a buy-at-open reader cannot see the row before the next
open. No bar after the latest completed session is stored.

Released ETF files are copied through their last session. A later vendor
tail is appended only when the overlap returns agree. Prices that already
sit on a cent are stored as delta-encoded integer cents. Anything else
stays float64 with byte-stream-split. Nothing is dropped to save space.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from world_timeframes import PRICE_COLS, TIMEFRAMES, completed_candles

WINDOW_START = pd.Timestamp("2020-01-02")
COVERAGE_MIN = 0.95
CENT_ATOL = 1e-4
RETURN_ATOL = 5e-4
PRIOR_RELEASE = "etf-native-context-v1-40484930003-1"
# Free issuer lineup read 2026-10-28. These are the SPDR S&P industry funds
# on that list, finer than the 11 sector SPDRs. Source:
# https://www.ssga.com/library-content/products/fund-docs/etfs/us/information-schedules/spdr-etf-listing.pdf
INDUSTRY_ETFS = (
    ("KBE", "SPDR S&P Bank"),
    ("KRE", "SPDR S&P Regional Banking"),
    ("KCE", "SPDR S&P Capital Markets"),
    ("KIE", "SPDR S&P Insurance"),
    ("XAR", "SPDR S&P Aerospace & Defense"),
    ("XTN", "SPDR S&P Transportation"),
    ("XBI", "SPDR S&P Biotech"),
    ("XPH", "SPDR S&P Pharmaceuticals"),
    ("XHE", "SPDR S&P Health Care Equipment"),
    ("XHS", "SPDR S&P Health Care Services"),
    ("XOP", "SPDR S&P Oil & Gas Exploration & Production"),
    ("XES", "SPDR S&P Oil & Gas Equipment & Services"),
    ("XME", "SPDR S&P Metals & Mining"),
    ("XRT", "SPDR S&P Retail"),
    ("XHB", "SPDR S&P Homebuilders"),
    ("XSD", "SPDR S&P Semiconductor"),
    ("XSW", "SPDR S&P Software & Services"),
    ("XTL", "SPDR S&P Telecom"),
)
INDEX_ETFS = ("SPY", "QQQ", "IWM", "DIA", "RSP")
SECTOR_ETFS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
CROSS_ASSET_ETFS = ("TLT", "HYG", "LQD", "UUP", "GLD", "CPER", "USO", "VXX", "IBIT")
NAMED_ETFS = INDEX_ETFS + SECTOR_ETFS + CROSS_ASSET_ETFS
OHLC = ("open", "high", "low", "close")
VENDOR = ("vendor_open", "vendor_high", "vendor_low", "vendor_close", "vendor_volume")
PANEL_COLUMNS = (
    "ticker", "family", "date", "available_from", *OHLC, "volume", *VENDOR, "source",
)


def family_of(ticker):
    if ticker in INDEX_ETFS:
        return "index"
    if ticker in SECTOR_ETFS:
        return "sector"
    if ticker in CROSS_ASSET_ETFS:
        return "cross_asset"
    if ticker in dict(INDUSTRY_ETFS):
        return "industry"
    raise ValueError("ticker is outside the market panel: " + ticker)


def latest_completed_session(now, calendar):
    """Last NYSE session whose close is at or before ``now``."""
    moment = pd.Timestamp(now)
    if moment.tzinfo is None:
        moment = moment.tz_localize("UTC")
    else:
        moment = moment.tz_convert("UTC")
    ny = moment.tz_convert("America/New_York")
    start = (pd.Timestamp(ny.date()) - pd.offsets.Day(14)).date()
    sessions = calendar.sessions_in_range(str(start), str(ny.date()))
    done = [pd.Timestamp(session) for session in sessions if calendar.session_close(session) <= moment]
    if not done:
        raise ValueError("no completed NYSE session")
    return done[-1]


def session_index(calendar, start, end):
    start = pd.Timestamp(start).date()
    end = pd.Timestamp(end).date()
    sessions = calendar.sessions_in_range(str(start), str(end))
    return pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)


def _normalize_dates(frame):
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"]).astype("datetime64[ns]")
    return out


def attach_available_from(frame, sessions):
    """Map each session to the next one. The last session stays blank."""
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)
    if sessions.has_duplicates or not sessions.is_monotonic_increasing:
        raise ValueError("session calendar must be ordered and unique")
    nxt = dict(zip(sessions[:-1], sessions[1:]))
    out = _normalize_dates(frame)
    missing = ~out["date"].isin(sessions)
    if missing.any():
        raise ValueError("bar date is not an NYSE session")
    out["available_from"] = out["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT))
    out["available_from"] = pd.to_datetime(out["available_from"]).astype("datetime64[ns]")
    return out


def _cent_residual(values):
    arr = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(arr)
    if not finite.all():
        return np.inf
    cents = np.rint(arr * 100.0)
    return float(np.max(np.abs(arr - cents / 100.0))) if len(arr) else 0.0


def price_storage_kind(frame):
    residual = max(_cent_residual(frame[column].to_numpy()) for column in OHLC)
    if residual <= CENT_ATOL:
        return "int64_cents_delta", residual
    return "float64_byte_stream_split", residual


def _volume_storage_kind(volume):
    arr = volume.to_numpy(dtype=np.float64, na_value=np.nan) if hasattr(volume, "to_numpy") else np.asarray(volume, dtype=np.float64)
    if np.isnan(arr).any():
        return "float64_byte_stream_split_nulls_kept"
    if len(arr) and np.max(np.abs(arr - np.rint(arr))) <= CENT_ATOL:
        return "int64_delta"
    return "float64_byte_stream_split"


def write_lossless(frame, path, dictionary_columns=("ticker", "family", "source")):
    """Write one sorted frame. Cent prices become delta-encoded integers."""
    path = Path(path)
    sort_on = [column for column in ("ticker", "timeframe", "date") if column in frame.columns]
    out = frame.sort_values(sort_on).reset_index(drop=True)
    price_kind, residual = price_storage_kind(out)
    volume_kind = _volume_storage_kind(out["volume"]) if "volume" in out.columns else None
    stored = out.copy()
    encodings = {}
    if price_kind == "int64_cents_delta":
        for column in OHLC:
            stored[column] = np.rint(stored[column].to_numpy(dtype=np.float64) * 100.0).astype(np.int64)
            encodings[column] = "DELTA_BINARY_PACKED"
    else:
        for column in OHLC:
            stored[column] = stored[column].astype(np.float64)
            encodings[column] = "BYTE_STREAM_SPLIT"
    float_columns = [column for column in stored.columns if column in VENDOR or stored[column].dtype == np.float64]
    for column in float_columns:
        if column in encodings:
            continue
        if column in ("volume", "vendor_volume") and volume_kind == "int64_delta" and stored[column].notna().all():
            stored[column] = np.rint(stored[column].to_numpy(dtype=np.float64)).astype(np.int64)
            encodings[column] = "DELTA_BINARY_PACKED"
            continue
        stored[column] = stored[column].astype(np.float64)
        encodings[column] = "BYTE_STREAM_SPLIT"
    if "volume" in stored.columns and "volume" not in encodings:
        if volume_kind == "int64_delta":
            stored["volume"] = np.rint(stored["volume"].to_numpy(dtype=np.float64)).astype(np.int64)
            encodings["volume"] = "DELTA_BINARY_PACKED"
        else:
            stored["volume"] = stored["volume"].astype(np.float64)
            encodings["volume"] = "BYTE_STREAM_SPLIT"
    dictionaries = [column for column in dictionary_columns if column in stored.columns]
    table = pa.Table.from_pandas(stored, preserve_index=False)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=19,
        use_dictionary=dictionaries,
        column_encoding=encodings,
        data_page_version="2.0",
    )
    return dict(price_storage=price_kind, volume_storage=volume_kind, cent_residual=residual, rows=len(out), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def read_lossless(path, price_storage):
    frame = pq.read_table(path).to_pandas()
    if price_storage == "int64_cents_delta":
        for column in OHLC:
            frame[column] = frame[column].astype(np.int64) / 100.0
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    frame["available_from"] = pd.to_datetime(frame["available_from"]).astype("datetime64[ns]")
    return frame


def parse_yahoo_chart(payload, ticker):
    """Adjusted OHLC from a Yahoo v8 chart payload. Quote fields stay beside it."""
    results = (payload.get("chart") or {}).get("result")
    if not results:
        error = (payload.get("chart") or {}).get("error")
        raise ValueError("no chart result: " + str(error))
    result = results[0]
    stamps = result.get("timestamp") or []
    quote = (result.get("indicators") or {}).get("quote") or [{}]
    quote = quote[0]
    adjusted = ((result.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or []
    if len(adjusted) != len(stamps):
        raise ValueError("adjusted-close series missing")
    dates = pd.to_datetime(stamps, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()
    frame = pd.DataFrame({"ticker": ticker, "date": dates})
    for column in OHLC + ("volume",):
        values = quote.get(column) or []
        if len(values) != len(frame):
            raise ValueError("quote array length mismatch " + column)
        frame["vendor_" + column] = pd.to_numeric(pd.Series(values), errors="coerce")
    frame["adjusted_close"] = pd.to_numeric(pd.Series(adjusted), errors="coerce")
    factor = frame["adjusted_close"] / frame["vendor_close"].replace(0, np.nan)
    for column in OHLC:
        frame[column] = frame["vendor_" + column] * factor
    frame["volume"] = frame["vendor_volume"]
    for column in OHLC:
        frame[column] = frame[column].replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(subset=["close", "open", "high", "low"]).sort_values("date")
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    if frame.empty:
        raise ValueError("no usable daily bars")
    if frame["date"].duplicated().any():
        raise ValueError("duplicate source sessions")
    return frame.reset_index(drop=True)


def yahoo_url(ticker, period1, period2):
    symbol = str(ticker).replace(".", "-")
    query = urllib.parse.urlencode({"period1": int(period1), "period2": int(period2), "interval": "1d", "events": "div,splits"})
    return "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?" + query


def fetch_yahoo(ticker, period1, period2, opener=None, attempts=4):
    opener = opener or urllib.request.urlopen
    url = yahoo_url(ticker, period1, period2)
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with opener(request, timeout=90) as response:
                payload = json.load(response)
            return parse_yahoo_chart(payload, ticker)
        except Exception as exc:  # noqa: BLE001 — the caller logs the reason and moves on
            last = exc
            code = getattr(exc, "code", None)
            if code not in (None, 429, 500, 502, 503, 504) and not isinstance(exc, (TimeoutError, OSError, ValueError)):
                break
            if attempt == attempts - 1:
                break
    raise ValueError("yahoo fetch failed for " + ticker + ": " + str(last))


def _on_calendar(frame, sessions, as_of):
    out = _normalize_dates(frame)
    as_of = pd.Timestamp(as_of)
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)
    future = int((out["date"] > as_of).sum())
    out = out[out["date"] <= as_of]
    off = ~out["date"].isin(sessions)
    dropped = int(off.sum())
    out = out.loc[~off].sort_values("date").reset_index(drop=True)
    if out["date"].duplicated().any():
        raise ValueError("duplicate sessions after the calendar filter")
    return out, dict(future_rows_dropped=future, non_session_rows_dropped=dropped)


def extend_released(prior, tail, sessions, as_of, overlap=20):
    """Keep every released row. Append later sessions when the overlap agrees."""
    prior = _normalize_dates(prior).sort_values("date").reset_index(drop=True)
    if prior.empty or prior["date"].duplicated().any() or not prior["date"].is_monotonic_increasing:
        raise ValueError("released series is empty or unordered")
    as_of = pd.Timestamp(as_of)
    if prior["date"].max() > as_of:
        raise ValueError("released series contains a bar after as_of")
    note = dict(tail_status="NO_TAIL", rows_appended=0)
    if tail is None or len(tail) == 0:
        kept = prior.copy()
        kept["source"] = "RELEASED_ETF_NATIVE"
        for column in VENDOR:
            kept[column] = np.nan
        return attach_available_from(kept, sessions), note
    tail, dropped = _on_calendar(tail, sessions, as_of)
    note.update(dropped)
    shared = sorted(set(prior["date"]).intersection(set(tail["date"])))
    if len(shared) < 5:
        note["tail_status"] = "OVERLAP_SHORTER_THAN_5"
        kept = _blank_vendor(prior)
        return attach_available_from(kept, sessions), note
    window = shared[-overlap:]
    p = prior.set_index("date").loc[window, "close"].astype(float)
    t = tail.set_index("date").loc[window, "close"].astype(float)
    gap = float((p.pct_change().iloc[1:] - t.pct_change().iloc[1:]).abs().max())
    if not np.isfinite(gap) or gap > RETURN_ATOL:
        note["tail_status"] = "OVERLAP_RETURN_MISMATCH"
        note["return_gap"] = None if not np.isfinite(gap) else gap
        return attach_available_from(_blank_vendor(prior), sessions), note
    anchor = shared[-1]
    if float(t.loc[anchor]) == 0 or not np.isfinite(float(t.loc[anchor])):
        note["tail_status"] = "OVERLAP_ANCHOR_BLANK"
        return attach_available_from(_blank_vendor(prior), sessions), note
    ratio = float(p.loc[anchor]) / float(t.loc[anchor])
    fresh = tail[tail["date"] > prior["date"].max()].copy()
    if fresh.empty:
        note["tail_status"] = "NO_NEW_SESSIONS"
        note["level_ratio"] = ratio
        return attach_available_from(_blank_vendor(prior), sessions), note
    for column in OHLC:
        fresh[column] = fresh[column].astype(float) * ratio
    fresh["source"] = "YAHOO_TAIL_LEVEL_LINKED"
    note["tail_status"] = "APPENDED"
    note["rows_appended"] = int(len(fresh))
    note["level_ratio"] = ratio
    note["return_gap"] = gap
    kept = _blank_vendor(prior)
    both = pd.concat([kept, fresh[list(kept.columns)]], ignore_index=True)
    check = both[both["date"].isin(prior["date"])].sort_values("date")
    for column in OHLC + ("volume",):
        if not np.array_equal(check[column].to_numpy(dtype=np.float64), prior[column].to_numpy(dtype=np.float64)):
            raise ValueError("released " + column + " changed while extending")
    return attach_available_from(both, sessions), note


def _blank_vendor(prior):
    kept = prior.copy()
    kept["source"] = "RELEASED_ETF_NATIVE"
    for column in VENDOR:
        if column not in kept:
            kept[column] = np.nan
    return kept


def vendor_panel(frame, sessions, as_of, source):
    """A full vendor history, cut at as_of, with the next-session availability."""
    cut, dropped = _on_calendar(frame, sessions, as_of)
    if cut.empty:
        raise ValueError("vendor history has no sessions in range")
    cut = cut.copy()
    cut["source"] = source
    cut = attach_available_from(cut, sessions)
    return cut, dropped


def coverage_row(frame, sessions, as_of, ticker):
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)
    as_of = pd.Timestamp(as_of)
    window = sessions[(sessions >= WINDOW_START) & (sessions <= as_of)]
    dates = pd.DatetimeIndex(pd.to_datetime(frame["date"]))
    first = dates.min() if len(dates) else pd.NaT
    if pd.isna(first):
        return dict(ticker=ticker, status="EXCLUDED", reason="NO_BARS", coverage_percent=0.0, rows=0,
                    first=None, last=None, missing_sessions=0, missing_dates=[])
    expected = window[window >= first]
    present = expected.isin(dates)
    missing = expected[~present]
    percent = float(present.mean()) if len(expected) else 0.0
    status = "PASS" if percent >= COVERAGE_MIN else "EXCLUDED"
    reason = "" if status == "PASS" else "COVERAGE_BELOW_95"
    full_present = window.isin(dates)
    full_percent = float(full_present.mean()) if len(window) else 0.0
    listed = [str(day.date()) for day in missing[:30]]
    return dict(
        ticker=ticker, family=family_of(ticker), status=status, reason=reason,
        coverage_percent=round(percent * 100, 4),
        full_window_percent=round(full_percent * 100, 4),
        full_window_sessions=int(len(window)),
        rows=int(len(frame)),
        first=str(pd.Timestamp(first).date()), last=str(pd.Timestamp(dates.max()).date()),
        expected_sessions=int(len(expected)), missing_sessions=int(len(missing)),
        missing_dates=listed, missing_dates_truncated=int(len(missing) > 30),
        window_gap_reason="LISTED_AFTER_WINDOW_START" if first > window[0] else "",
    )


def assert_no_lookahead(frame, as_of):
    as_of = pd.Timestamp(as_of)
    if (pd.to_datetime(frame["date"]) > as_of).any():
        raise ValueError("bar after as_of")
    known = frame["available_from"].notna()
    if (pd.to_datetime(frame.loc[known, "available_from"]) <= pd.to_datetime(frame.loc[known, "date"])).any():
        raise ValueError("available_from is not after the session")


def build_candles(daily, boundary_sessions, as_of):
    """Native candles for every timeframe. The last open bucket is omitted."""
    as_of = pd.Timestamp(as_of)
    frames = []
    for ticker, bars in daily.groupby("ticker", sort=True):
        piece = bars.sort_values("date").loc[:, ["date", *PRICE_COLS]]
        for timeframe in TIMEFRAMES:
            candles = completed_candles(piece, timeframe, boundary_sessions)
            candles = candles[candles["date"] <= as_of]
            if candles.empty:
                continue
            candles.insert(0, "ticker", ticker)
            candles.insert(1, "timeframe", timeframe)
            frames.append(candles)
    if not frames:
        return pd.DataFrame(columns=["ticker", "timeframe", "candle_start", "date", "available_from", *PRICE_COLS])
    out = pd.concat(frames, ignore_index=True)
    assert_no_lookahead(out, as_of)
    return out


def prior_records(document):
    release = document["release"]
    if release != PRIOR_RELEASE:
        raise ValueError("unexpected prior ETF release")
    records = {}
    for row in document["records"]:
        records[row["ticker"]] = dict(file=row["file"], sha256=row["sha256"], rows=row["rows"], last=row["last"])
    missing = [ticker for ticker in NAMED_ETFS if ticker not in records]
    if missing:
        raise ValueError("prior release is missing " + ",".join(missing))
    return records


def panel_passes(rows):
    passed = [row for row in rows if row["status"] == "PASS"]
    if not rows:
        raise ValueError("no coverage rows")
    percent = len(passed) / len(rows)
    if percent < COVERAGE_MIN:
        raise ValueError("panel coverage below 95 percent")
    failed_core = [row["ticker"] for row in rows if row["ticker"] in NAMED_ETFS and row["status"] != "PASS"]
    if failed_core:
        raise ValueError("named series excluded: " + ",".join(failed_core))
    return dict(requested=len(rows), passed=len(passed), coverage_percent=round(percent * 100, 4),
                excluded=[row for row in rows if row["status"] != "PASS"])
