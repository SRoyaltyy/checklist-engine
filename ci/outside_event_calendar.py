"""Build the event-calendar flags on one runner.

The Federal Reserve pages and the checksummed FRED vintage file are the only
inputs. No price file is read.
"""

import argparse
import io
import json
import os
import tarfile
import urllib.request
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

from ci.release_assets import gh_retry
from outside_calendar import (
    FOMC_2020_URL,
    FOMC_CALENDAR_URL,
    FRED_ARCHIVE,
    FRED_ARCHIVE_SHA256,
    FRED_RELEASE,
    assert_calendar_coverage,
    build_calendar,
    candle_summary,
    carry_onto_candles,
    coverage_table,
    first_release_dates,
    parse_fomc_calendars,
    parse_fomc_historical,
    require_sha256,
    write_lossless,
)


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine research"})
    with urllib.request.urlopen(request, timeout=180) as response:
        Path(path).write_bytes(response.read())
    return Path(path)


def latest_completed_session(now, calendar):
    moment = pd.Timestamp(now)
    if moment.tzinfo is None:
        moment = moment.tz_localize("UTC")
    moment = moment.tz_convert("UTC")
    ny = moment.tz_convert("America/New_York")
    start = (pd.Timestamp(ny.date()) - pd.offsets.Day(14)).date()
    sessions = calendar.sessions_in_range(str(start), str(ny.date()))
    done = [pd.Timestamp(session) for session in sessions if calendar.session_close(session) <= moment]
    if not done:
        raise ValueError("no completed NYSE session")
    return done[-1]


def build(out, now=None, publish=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    calendar = xcals.get_calendar("XNYS", start="1990-01-01")
    as_of = latest_completed_session(now or pd.Timestamp.now(tz="UTC"), calendar)
    # Extend far enough that monthly opex and published FOMC dates still have a next session.
    end = str((as_of + pd.offsets.Day(120)).date())
    sessions = pd.DatetimeIndex(calendar.sessions_in_range("2019-12-02", end)).tz_localize(None)
    historical = download(FOMC_2020_URL, out / "fomc_2020.html").read_text(errors="replace")
    current = download(FOMC_CALENDAR_URL, out / "fomc_calendars.html").read_text(errors="replace")
    fomc = pd.concat([
        parse_fomc_historical(historical, 2020),
        parse_fomc_calendars(current),
    ], ignore_index=True).drop_duplicates(["date", "kind"])
    fred_path = download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + FRED_RELEASE + "/" + FRED_ARCHIVE,
        out / FRED_ARCHIVE,
    )
    require_sha256(fred_path, FRED_ARCHIVE_SHA256)
    with tarfile.open(fred_path) as bundle:
        fred = pd.read_parquet(io.BytesIO(bundle.extractfile("fred.parquet").read()))
    cpi = first_release_dates(fred[fred.series == "CPIAUCSL"])
    jobs = first_release_dates(fred[fred.series == "UNRATE"])
    panel = build_calendar(sessions, fomc, cpi, jobs, as_of)
    rows = coverage_table(panel)
    summary = assert_calendar_coverage(rows)
    meta = write_lossless(panel, out / "outside_event_calendar.parquet")
    candles = carry_onto_candles(panel, sessions, as_of)
    candle_meta = write_lossless(candles, out / "outside_event_calendar_candles.parquet")
    proof = dict(
        block="outside_event_calendar",
        as_of=str(as_of.date()),
        fomc_sources=[FOMC_2020_URL, FOMC_CALENDAR_URL],
        cpi_source="first ALFRED vintage of CPIAUCSL in " + FRED_RELEASE,
        jobs_source="first ALFRED vintage of UNRATE in " + FRED_RELEASE,
        opex_rule="third Friday, or the previous NYSE session when that Friday is closed",
        turn_of_month_rule="the last session of the month or one of the first three sessions",
        lookahead="flags use the published calendar or the vintage date; no price column is read; a release after as_of is not flagged",
        fomc_rows=int(len(fomc)),
        cpi_releases=int(len(cpi)),
        jobs_releases=int(len(jobs)),
        summary=summary,
        storage=meta,
        candles={**candle_summary(candles), "storage": candle_meta},
        series=rows,
        counts={
            column: int(panel[column].sum()) for column in (
                "is_fomc", "is_fomc_notation", "is_cpi", "is_jobs", "is_month_end", "is_opex",
            )
        },
    )
    proof_path = out / "OUTSIDE_EVENT_CALENDAR_PROOF.json"
    proof_path.write_text(json.dumps(proof, indent=2, default=str) + "\n")
    if publish:
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        tag = "outside-event-calendar-v1-" + run_id + "-1"
        gh_retry(
            "release", "create", tag, "--draft", "--title", tag,
            "--notes", "Event calendar flags through " + proof["as_of"] + ". See OUTSIDE_EVENT_CALENDAR_PROOF.json.",
            "--target", os.environ.get("GITHUB_SHA", "HEAD"),
            str(out / "outside_event_calendar.parquet"),
            str(out / "outside_event_calendar_candles.parquet"),
            str(proof_path),
        )
        proof["release"] = tag
        proof_path.write_text(json.dumps(proof, indent=2, default=str) + "\n")
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    proof = build(args.out, publish=args.publish)
    print(json.dumps({"as_of": proof["as_of"], **proof["summary"], "counts": proof["counts"]}))


if __name__ == "__main__":
    main()
