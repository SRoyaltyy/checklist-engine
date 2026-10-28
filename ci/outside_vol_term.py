"""Build the VIX term-structure panel on one runner.

CBOE history comes from the checksummed release. A public CSV may append
sessions after that release. VIX comes from the checksummed FRED vintages.
A tail fetch uses FRED_API_KEY when it is set and never prints it.
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
from fetch.fetch_fred import alfred_observations
from outside_vol import (
    CBOE_ARCHIVE,
    CBOE_ARCHIVE_SHA256,
    CBOE_RELEASE,
    CLOSE_SERIES,
    FRED_ARCHIVE,
    FRED_ARCHIVE_SHA256,
    FRED_RELEASE,
    OHLC_SERIES,
    append_verified_tail,
    assert_panel_coverage,
    build_daily,
    cboe_parquet_frame,
    coverage_table,
    level_candles,
    parse_cboe_csv,
    ratio_candles,
    require_sha256,
    vix_close_known_by_session,
    write_lossless,
)

CBOE_URLS = {
    "VIX9D": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv",
    "VIX3M": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv",
    "VVIX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv",
}


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine research"})
    with urllib.request.urlopen(request, timeout=180) as response:
        Path(path).write_bytes(response.read())
    return Path(path)


def member(archive, name):
    with tarfile.open(archive) as bundle:
        extracted = bundle.extractfile(name)
        if extracted is None:
            raise ValueError("archive member missing: " + name)
        return extracted.read()


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


def extend_vix(vintages, as_of):
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        return vintages, dict(tail_status="RELEASED_ONLY_NO_KEY")
    last = pd.to_datetime(vintages["vintage_date"]).max()
    start = (last + pd.offsets.Day(1)).date().isoformat()
    try:
        rows = alfred_observations(
            key, "VIXCLS", available_from=start, as_of=str(pd.Timestamp(as_of).date()),
            start_year=int(last.year), end_year=int(pd.Timestamp(as_of).year),
        )
    except Exception as exc:
        message = str(exc).replace(key, "[REDACTED]")
        return vintages, dict(tail_status="TAIL_FETCH_FAILED", error=message[:300])
    if not rows:
        return vintages, dict(tail_status="NO_NEW_VINTAGES")
    extra = pd.DataFrame(rows)
    both = pd.concat([vintages, extra.loc[:, ["series", "obs_date", "vintage_date", "value"]]], ignore_index=True)
    both = both.drop_duplicates(["obs_date", "vintage_date"])
    return both, dict(tail_status="APPENDED", rows=int(len(extra)))


def build(out, now=None, publish=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    calendar = xcals.get_calendar("XNYS", start="1990-01-01")
    as_of = latest_completed_session(now or pd.Timestamp.now(tz="UTC"), calendar)
    sessions = pd.DatetimeIndex(calendar.sessions_in_range("1990-01-02", str((as_of + pd.offsets.Day(45)).date()))).tz_localize(None)
    cboe_path = download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + CBOE_RELEASE + "/" + CBOE_ARCHIVE,
        out / CBOE_ARCHIVE,
    )
    require_sha256(cboe_path, CBOE_ARCHIVE_SHA256)
    fred_path = download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + FRED_RELEASE + "/" + FRED_ARCHIVE,
        out / FRED_ARCHIVE,
    )
    require_sha256(fred_path, FRED_ARCHIVE_SHA256)
    fred = pd.read_parquet(io.BytesIO(member(fred_path, "fred.parquet")))
    vintages, vix_note = extend_vix(fred[fred.series == "VIXCLS"].copy(), as_of)
    vix = vix_close_known_by_session(vintages)
    vix_level = pd.DataFrame({
        "date": vix["date"], "close": vix["vix"],
        "open": vix["vix"], "high": vix["vix"], "low": vix["vix"],
    })
    levels = {"VIX": vix_level}
    notes = {"VIX": vix_note}
    for symbol in OHLC_SERIES + ("VVIX",):
        released = cboe_parquet_frame(pd.read_parquet(io.BytesIO(member(cboe_path, "cboe/" + symbol + ".parquet"))), symbol)
        try:
            text = download(CBOE_URLS[symbol], out / (symbol + ".csv")).read_text()
            fresh = parse_cboe_csv(text, symbol)
        except (OSError, ValueError) as exc:
            fresh = None
            notes[symbol] = dict(tail_status="CSV_UNAVAILABLE", error=str(exc)[:200])
            levels[symbol] = released
            continue
        levels[symbol], notes[symbol] = append_verified_tail(released, fresh, as_of)
    panel = build_daily(levels, sessions, as_of)
    rows = coverage_table(panel, sessions, as_of)
    summary = assert_panel_coverage(rows)
    candles = level_candles(levels, sessions, as_of)
    ratios = ratio_candles(candles)
    daily_meta = write_lossless(panel, out / "outside_vol_daily.parquet", dictionary_columns=())
    candle_meta = write_lossless(candles, out / "outside_vol_candles.parquet", dictionary_columns=("series", "basis", "timeframe"))
    ratio_meta = write_lossless(ratios, out / "outside_vol_ratio_candles.parquet", dictionary_columns=("series", "timeframe"))
    proof = dict(
        block="outside_vol_term",
        as_of=str(as_of.date()),
        cboe_release=CBOE_RELEASE,
        fred_release=FRED_RELEASE,
        vix_source="FRED VIXCLS vintages; a vintage after the observation date is not used",
        cboe_source="released CBOE parquet plus a public CSV tail when overlap closes agree",
        close_only=list(CLOSE_SERIES),
        lookahead="row D uses prints published on or before D; available_from is the next NYSE session",
        summary=summary,
        daily=daily_meta,
        candles=candle_meta,
        ratio_candles=ratio_meta,
        series=rows,
        tails=notes,
    )
    proof_path = out / "OUTSIDE_VOL_TERM_PROOF.json"
    proof_path.write_text(json.dumps(proof, indent=2, default=str) + "\n")
    if publish:
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        tag = "outside-vol-term-v1-" + run_id + "-1"
        gh_retry(
            "release", "create", tag, "--draft", "--title", tag,
            "--notes", "VIX term structure through " + proof["as_of"] + ". Lossless. See OUTSIDE_VOL_TERM_PROOF.json.",
            "--target", os.environ.get("GITHUB_SHA", "HEAD"),
            str(out / "outside_vol_daily.parquet"),
            str(out / "outside_vol_candles.parquet"),
            str(out / "outside_vol_ratio_candles.parquet"),
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
    print(json.dumps({"as_of": proof["as_of"], **proof["summary"], "vix_tail": proof["tails"]["VIX"]["tail_status"]}))


if __name__ == "__main__":
    main()
