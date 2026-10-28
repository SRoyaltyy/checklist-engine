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
    stored["volume"] = stored["volume"].astype(np.int64)
    table = pa.Table.from_pandas(stored, preserve_index=False)
    pq.write_table(
        table, path, compression="zstd", compression_level=19, use_dictionary=["ticker"],
        column_encoding={
            "open": "BYTE_STREAM_SPLIT", "high": "BYTE_STREAM_SPLIT", "low": "BYTE_STREAM_SPLIT",
            "close": "BYTE_STREAM_SPLIT", "adj_close": "BYTE_STREAM_SPLIT",
            "volume": "DELTA_BINARY_PACKED",
        },
        data_page_version="2.0",
    )
    return dict(rows=len(stored), sha256=sha256_file(path), encoding="float64_byte_stream_split_volume_int64_delta_zstd19")


def proof_from_release(directory, out_dir, as_of=None):
    panel, document, rows = build_panel(directory, as_of=as_of)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    storage = write_panel(panel, out_dir / "outside_market_daily.parquet")
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
        lookahead="session date is that close; available_from is the next SPY session; rows after as_of are dropped",
        price_basis="published open/high/low/close plus adj_close and volume; nothing recomputed",
    )
    if failed:
        raise ValueError("light-daily ETF coverage below 95 percent: " + ",".join(failed))
    path = out_dir / "OUTSIDE_MARKET_DAILY_PROOF.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    return proof
