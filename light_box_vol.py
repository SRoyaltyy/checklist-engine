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


def write_panel(frame, path):
    stored = frame.sort_values("date").reset_index(drop=True)
    encodings = {}
    for column in stored.columns:
        if stored[column].dtype == np.float64:
            encodings[column] = "BYTE_STREAM_SPLIT"
    table = pa.Table.from_pandas(stored, preserve_index=False)
    pq.write_table(table, path, compression="zstd", compression_level=19, use_dictionary=False,
                   column_encoding=encodings, data_page_version="2.0")
    return dict(rows=len(stored), sha256=sha256_file(path), encoding="float64_byte_stream_split_zstd19")


def proof_from_release(directory, out_dir, as_of=None):
    panel, document, off_calendar = build_panel(directory, as_of=as_of)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    storage = write_panel(panel, out_dir / "outside_vol_daily.parquet")
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
        lookahead="ratios use same-session closes; available_from is the next SPY session",
    )
    if failed:
        raise ValueError("volatility coverage below 95 percent: " + ",".join(failed))
    path = out_dir / "OUTSIDE_VOL_TERM_PROOF.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    return proof
