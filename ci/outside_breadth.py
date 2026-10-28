"""Breadth from the accepted stitch-v2 daily bars. One job, one archive at a time."""

import argparse
import io
import json
import os
import tarfile
import urllib.request
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from ci.release_assets import gh_retry
from outside_breadth import (
    COUNT_COLUMNS,
    STITCH_MANIFEST,
    STITCH_MANIFEST_SHA256,
    STITCH_RELEASE,
    aggregate,
    assert_breadth,
    breadth_candles,
    coverage_row,
    require_sha256,
    stock_contributions,
    write_lossless,
)


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".partial")
    with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as stream:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            stream.write(chunk)
    temporary.replace(target)
    return target


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
    manifest_path = download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + STITCH_RELEASE + "/" + STITCH_MANIFEST,
        out / STITCH_MANIFEST,
    )
    require_sha256(manifest_path, STITCH_MANIFEST_SHA256)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "ACCEPTED_PRICE_BASE_WITH_LOGGED_EXCLUSIONS_NOT_WORLD":
        raise ValueError("unexpected stitch status")
    if int(manifest["accepted_tickers"]) != len(manifest["records"]):
        raise ValueError("accepted ticker count differs from records")
    calendar = xcals.get_calendar("XNYS", start="1990-01-01")
    completed = latest_completed_session(now or pd.Timestamp.now(tz="UTC"), calendar)
    last_query = max(pd.Timestamp(row["last_query"]) for row in manifest["records"])
    as_of = min(completed, last_query)
    sessions = pd.DatetimeIndex(calendar.sessions_in_range("1990-01-02", str((as_of + pd.offsets.Day(10)).date()))).tz_localize(None)
    index = pd.DatetimeIndex(sessions)
    store = {column: np.zeros(len(index), dtype=np.float64 if column.endswith("volume") else np.int64) for column in COUNT_COLUMNS}
    used = 0
    excluded = []
    for part_index, part in enumerate(manifest["parts"]):
        url = "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + part["release"] + "/" + part["part"] + ".tar"
        archive = out / (part["part"] + ".tar")
        download(url, archive)
        require_sha256(archive, part["archive_sha256"])
        with tarfile.open(archive) as bundle:
            for ticker in part["tickers"]:
                member = ticker.encode().hex() + ".bars.parquet"
                extracted = bundle.extractfile(member)
                if extracted is None:
                    excluded.append(dict(ticker=ticker, reason="MISSING_BARS"))
                    continue
                try:
                    frame = pd.read_parquet(io.BytesIO(extracted.read()))
                    votes = stock_contributions(frame)
                except (ValueError, OSError) as exc:
                    excluded.append(dict(ticker=ticker, reason=type(exc).__name__ + ": " + str(exc)[:160]))
                    continue
                positions = index.get_indexer(pd.to_datetime(votes["date"]).astype("datetime64[ns]"))
                ok = positions >= 0
                for column in COUNT_COLUMNS:
                    np.add.at(store[column], positions[ok], votes[column].to_numpy()[ok])
                used += 1
        archive.unlink()
        if part_index % 10 == 0:
            print(json.dumps(dict(part=part_index, used=used, excluded=len(excluded))), flush=True)
    counts = pd.DataFrame({"date": index, **store})
    panel = aggregate(counts, sessions, as_of)
    summary = coverage_row(panel, sessions, as_of)
    names = assert_breadth(summary, used, int(manifest["accepted_tickers"]))
    meta = write_lossless(panel, out / "outside_breadth_daily.parquet")
    candles = breadth_candles(panel, sessions)
    candle_meta = write_lossless(candles, out / "outside_breadth_candles.parquet")
    proof = dict(
        block="outside_breadth",
        as_of=str(as_of.date()),
        stitch_release=STITCH_RELEASE,
        stitch_manifest_sha256=STITCH_MANIFEST_SHA256,
        accepted_names=int(manifest["accepted_tickers"]),
        excluded_by_stitch=int(manifest["excluded_tickers"]),
        universe_label="accepted stitch-v2 names; survivors-only as labeled on that release; the manifest does not split ETF and stock",
        lookahead="each session uses only that name's bars through the session; available_from is the next NYSE session",
        high_low_window=252,
        sma_windows=[20, 50, 200],
        names=names,
        sessions=summary,
        storage=meta,
        candles={
            **candle_meta,
            "note": "Flows are summed inside the completed candle. New highs minus new lows and both ratios are rebuilt from those sums. Percents and the advance/decline line are the end session. available_from is the next session.",
        },
        excluded=excluded[:200],
        excluded_count=len(excluded),
        excluded_truncated=len(excluded) > 200,
    )
    proof_path = out / "OUTSIDE_BREADTH_PROOF.json"
    proof_path.write_text(json.dumps(proof, indent=2, default=str) + "\n")
    if publish:
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        tag = "outside-breadth-v1-" + run_id + "-1"
        gh_retry(
            "release", "create", tag, "--draft", "--title", tag,
            "--notes", "Breadth from stitch-v2 through " + proof["as_of"] + ". See OUTSIDE_BREADTH_PROOF.json.",
            "--target", os.environ.get("GITHUB_SHA", "HEAD"),
            str(out / "outside_breadth_daily.parquet"),
            str(out / "outside_breadth_candles.parquet"),
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
    print(json.dumps({"as_of": proof["as_of"], "names": proof["names"], "sessions": proof["sessions"]["coverage_percent"]}))


if __name__ == "__main__":
    main()
