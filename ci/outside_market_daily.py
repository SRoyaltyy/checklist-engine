"""Build the outside-the-stock daily panel on one runner.

Reuses the immutable ETF release through 2026-10-23 and appends only later
completed sessions. Industry ETFs are fetched from the same free Yahoo chart
path. One process, no extra matrix.
"""

import argparse
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

from ci.release_assets import gh_retry
from outside_market import (
    INDUSTRY_ETFS,
    NAMED_ETFS,
    PANEL_COLUMNS,
    PRIOR_RELEASE,
    WINDOW_START,
    assert_no_lookahead,
    build_candles,
    coverage_row,
    extend_released,
    family_of,
    fetch_yahoo,
    latest_completed_session,
    panel_passes,
    prior_records,
    session_index,
    vendor_panel,
    write_lossless,
)


def download_prior(record, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / record["file"]
    url = "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + PRIOR_RELEASE + "/" + record["file"]
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
    with urllib.request.urlopen(request, timeout=180) as response:
        target.write_bytes(response.read())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != record["sha256"]:
        raise ValueError("released ETF bytes differ: " + record["file"])
    frame = pd.read_parquet(target)
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    return frame.sort_values("date").reset_index(drop=True)


def _period(day):
    return int(pd.Timestamp(day).tz_localize("America/New_York").timestamp())


def build(out, document, now=None, sleep_seconds=0.35, publish=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    calendar = xcals.get_calendar("XNYS", start="1990-01-01")
    as_of = latest_completed_session(now or pd.Timestamp.now(tz="UTC"), calendar)
    sessions = session_index(calendar, "1990-01-02", as_of + pd.offsets.Day(45))
    records = prior_records(document)
    pieces = []
    notes = []
    for index, ticker in enumerate(NAMED_ETFS):
        prior = download_prior(records[ticker], out / "prior")
        tail = None
        tail_error = ""
        try:
            if index:
                time.sleep(sleep_seconds)
            tail = fetch_yahoo(ticker, _period(prior["date"].max() - pd.offsets.Day(60)), _period(as_of + pd.offsets.Day(1)))
        except ValueError as exc:
            tail_error = str(exc)
        frame, note = extend_released(prior, tail, sessions, as_of)
        frame["ticker"] = ticker
        frame["family"] = family_of(ticker)
        note = dict(note, ticker=ticker, tail_error=tail_error)
        notes.append(note)
        pieces.append(frame)
    for index, (ticker, _name) in enumerate(INDUSTRY_ETFS):
        time.sleep(sleep_seconds)
        try:
            fetched = fetch_yahoo(ticker, 631152000, _period(as_of + pd.offsets.Day(1)))
            frame, dropped = vendor_panel(fetched, sessions, as_of, "YAHOO_CHART_V8")
            frame["ticker"] = ticker
            frame["family"] = "industry"
            notes.append(dict(ticker=ticker, tail_status="FULL_VENDOR", **dropped))
            pieces.append(frame)
        except ValueError as exc:
            notes.append(dict(ticker=ticker, tail_status="EXCLUDED", error=str(exc)))
            pieces.append(pd.DataFrame(columns=list(PANEL_COLUMNS)))
    rows = []
    kept = []
    for frame in pieces:
        ticker = frame["ticker"].iloc[0] if len(frame) else notes[len(rows)]["ticker"]
        if frame.empty:
            rows.append(dict(ticker=ticker, family=family_of(ticker), status="EXCLUDED", reason=notes[len(rows)].get("error", "NO_BARS"),
                             coverage_percent=0.0, rows=0, first=None, last=None, expected_sessions=0,
                             missing_sessions=0, missing_dates=[], missing_dates_truncated=False))
            continue
        assert_no_lookahead(frame, as_of)
        row = coverage_row(frame, sessions, as_of, ticker)
        rows.append(row)
        if row["status"] == "PASS":
            kept.append(frame.loc[:, list(PANEL_COLUMNS)])
    summary = panel_passes(rows)
    panel = pd.concat(kept, ignore_index=True)
    daily_meta = write_lossless(panel, out / "outside_market_daily.parquet")
    candles = build_candles(panel, sessions, as_of)
    candle_meta = write_lossless(candles, out / "outside_market_candles.parquet", dictionary_columns=("ticker", "timeframe"))
    proof = dict(
        block="outside_market_daily",
        as_of=str(as_of.date()),
        window_start=str(WINDOW_START.date()),
        prior_release=PRIOR_RELEASE,
        prior_bytes_unchanged=True,
        price_basis="released adjusted units through the prior last session; a later tail is level-linked and keeps vendor prints",
        lookahead="session date is that close; available_from is the next NYSE session; no bar date is after as_of",
        industry_source="https://www.ssga.com/library-content/products/fund-docs/etfs/us/information-schedules/spdr-etf-listing.pdf",
        summary=summary,
        daily=daily_meta,
        candles=dict(candle_meta, timeframes=sorted(candles.timeframe.unique()), candle_rows=int(len(candles))),
        series=rows,
        tails=notes,
    )
    proof_path = out / "OUTSIDE_MARKET_DAILY_PROOF.json"
    proof_path.write_text(json.dumps(proof, indent=2, default=str) + "\n")
    if publish:
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        tag = "outside-market-daily-v1-" + run_id + "-1"
        gh_retry(
            "release", "create", tag, "--draft", "--title", tag,
            "--notes", "Outside-the-stock daily panel through " + proof["as_of"] + ". Lossless. See OUTSIDE_MARKET_DAILY_PROOF.json.",
            "--target", os.environ.get("GITHUB_SHA", "HEAD"),
            str(out / "outside_market_daily.parquet"),
            str(out / "outside_market_candles.parquet"),
            str(proof_path),
        )
        proof["release"] = tag
        proof_path.write_text(json.dumps(proof, indent=2, default=str) + "\n")
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--prior-document", default="docs/ETF_BASELINE_SOURCE_FETCHED_V1.json")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.35)
    args = parser.parse_args()
    document = json.loads(Path(args.prior_document).read_text())
    proof = build(args.out, document, sleep_seconds=args.sleep_seconds, publish=args.publish)
    print(json.dumps(proof["summary"]))


if __name__ == "__main__":
    main()
