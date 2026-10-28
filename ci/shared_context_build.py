"""Build shared ALFRED/CBOE blocks from verified existing release bytes only."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

import pandas as pd

from ci.native_price_blocks import measure_availability, sha, write_json
from ci.release_assets import publish_assets,download_asset as download,gh_retry as gh
from world_context_native import KEYS, combine_contexts, fred_native, index_native
from world_fred import compile_timelines
from world_timeframes import TIMEFRAMES

INPUTS = "native-price-inputs-v1-40336250454-1"
SOURCES = {
    "macro": ("fred-structured-v3-40266650669-1", "fred_structured_source.tar.gz", "16a60d96ccbc0f9e5424bc9dc5057e3a72327a48b8036078072cca4bfbedb5d8"),
    "macro_extra": ("phase1-gap-fred-v2-40307954973-1", "fred_gap_source.tar.gz", "5b2dffa054d796355be0adf70807404010317cbaf25aa75f85670bb149452b0c"),
    "cboe": ("phase1-gap-cboe-v1-40307220071-1", "cboe_gap_source.tar.gz", "7f5e6cc98ffa0ae632f8b22454d4641cf4402d94f5b7bfbcf115cc3c81904710"),
}


def verified_parquet(archive, expected_hash):
    """Read only the checksummed member; never extract archive paths to disk."""
    with tarfile.open(archive) as source:
        for member in source:
            if member.isfile() and member.name.endswith(".parquet"):
                raw = source.extractfile(member).read()
                if hashlib.sha256(raw).hexdigest() == expected_hash:
                    return pd.read_parquet(io.BytesIO(raw)), member.name
    raise ValueError("required parquet fingerprint absent from " + str(archive))


def normalize_index(frame, metadata):
    expected = metadata["source_columns"]
    if not set(expected) <= set(frame):
        raise ValueError("CBOE source schema differs")
    frame = frame[expected].copy()
    if not metadata["has_true_ohlc"]:
        values = [c for c in expected if c != "DATE"]
        if len(values) != 1:
            raise ValueError("ambiguous close-only CBOE source")
        frame = frame.rename(columns={values[0]: "CLOSE"})
    elif not {"DATE", "OPEN", "HIGH", "LOW", "CLOSE"} <= set(frame):
        raise ValueError("CBOE OHLC not proven")
    frame["DATE"] = pd.to_datetime(frame.DATE).astype("datetime64[ns]")
    return frame.sort_values("DATE").reset_index(drop=True)


def contexts(calendar, timelines, indices, required):
    return {tf: combine_contexts([
        fred_native(calendar, tf, timelines, required_series=required),
        *(index_native(history, calendar, tf, "cboe_" + name.lower()) for name, history in sorted(indices.items())),
    ]) for tf in TIMEFRAMES}


def prefix_check(full, calendar, fred, indices, required, cut):
    cal = calendar[calendar <= cut]
    timelines = compile_timelines(fred[fred.vintage_date < cut])
    earlier = {name: frame[frame.DATE < cut] for name, frame in indices.items()}
    rebuilt = contexts(cal, timelines, earlier, set(required) & set(timelines))
    checks = []
    for tf in TIMEFRAMES:
        expected = full[tf][full[tf].available_from <= cut].reset_index(drop=True)
        actual = rebuilt[tf].reindex(columns=expected.columns)
        pd.testing.assert_frame_equal(expected, actual, check_dtype=True, check_exact=True)
        checks.append({"cut": str(cut.date()), "timeframe": tf, "rows": len(expected),
                       "columns": len(expected.columns) - len(KEYS), "mismatches": 0})
    return checks


def main():
    parser = argparse.ArgumentParser();parser.add_argument("--directory", required=True)
    parser.add_argument('--version',type=int,choices=(2,),default=2)
    args = parser.parse_args();root = Path(args.directory);root.mkdir(parents=True, exist_ok=True)
    inputs = json.loads(download(INPUTS, "BUILD_INPUTS.json", root).read_text())
    file = download(INPUTS, "market_sessions.parquet", root)
    if sha(file) != inputs["calendar_sha256"]:
        raise ValueError("shared calendar fingerprint differs")
    calendar = pd.DatetimeIndex(pd.read_parquet(file).date)
    archives = {};receipts = []
    for kind, (tag, name, digest) in SOURCES.items():
        archive = download(tag, name, root)
        if sha(archive) != digest:
            raise ValueError("source archive fingerprint differs: " + kind)
        archives[kind] = archive
        receipts.append({"kind": kind, "release": tag, "asset": name, "sha256": digest})
    macro = json.loads(Path("docs/MACRO_SOURCE_STATUS_V3.json").read_text())
    digest = next(r["sha256"] for r in macro["files"] if r["path"] == "fred.parquet")
    fred, member = verified_parquet(archives["macro"], digest)
    receipts.append({"kind": "macro_member", "path": member, "sha256": digest})
    extra = json.loads(Path("docs/FRED_1635_DOWNLOAD_ACCEPTANCE_V1.json").read_text())
    addition, member = verified_parquet(archives["macro_extra"], extra["parquet_sha256"])
    aliases = {row["source_series"]: requested for requested, row in extra["series"].items()}
    addition["series"] = addition.series.replace(aliases)
    fred = pd.concat([fred, addition], ignore_index=True)
    for column in ("obs_date", "vintage_date"):
        fred[column] = pd.to_datetime(fred[column]).astype("datetime64[ns]")
    required = set(macro["status"]["series"]) | set(extra["series"])
    if set(fred.series) != required:
        raise ValueError("ALFRED source series differ from registration")
    receipts.append({"kind": "macro_extra_member", "path": member, "sha256": extra["parquet_sha256"], "series_aliases": aliases})
    cboe = json.loads(Path("docs/CBOE_NUMERIC_SOURCE_STATUS_V1.json").read_text())
    indices = {}
    for name, metadata in sorted(cboe["series"].items()):
        if metadata["status"] != "PASS":
            raise ValueError("unverified CBOE source: " + name)
        frame, member = verified_parquet(archives["cboe"], metadata["parquet_sha256"])
        indices[name] = normalize_index(frame, metadata)
        receipts.append({"kind": "cboe_member", "series": name, "path": member, "sha256": metadata["parquet_sha256"]})
    full = contexts(calendar, compile_timelines(fred), indices, required)
    checks = []
    for cut in map(pd.Timestamp, ("2023-01-03", "2025-01-02")):
        checks.extend(prefix_check(full, calendar, fred, indices, required, cut))
        print("SHARED_CONTEXT_PREFIX_PASS", str(cut.date()), flush=True)
    query = calendar[calendar >= pd.Timestamp("2020-01-01")]
    files = [];coverage = [];parts = []
    for tf, frame in full.items():
        file = root / ("shared_context_" + tf + ".parquet")
        frame.to_parquet(file, index=False, compression="zstd");files.append(file)
        selected = [c for c in frame if c not in KEYS]
        rows = measure_availability(frame[["available_from", *selected]], query)
        for row in rows:
            row.update(timeframe=tf, denominator="shared_market_sessions_not_stock_days")
        coverage.extend(rows)
        parts.append({"file": file.name, "sha256": sha(file), "timeframe": tf,
                      "native_rows": len(frame), "feature_columns": len(selected)})
    report = {"status": "SHARED_MACRO_CBOE_NATIVE_BLOCKS_NOT_WORLD", "source_commit": os.environ["GITHUB_SHA"],
              "format_version":args.version,"numeric_precision":"float64; no unproven precision reduction",
              "calendar_inputs": INPUTS, "calendar_sha256": inputs["calendar_sha256"],
              "code_sha256": {name: sha(name) for name in ("world_context_native.py", "world_fred.py", "ci/shared_context_build.py")},
              "timeframes": list(TIMEFRAMES), "fred_series": sorted(required), "cboe_series": sorted(indices),
              "parts": parts, "prefix_checks": checks, "source_receipts": receipts,
              "stock_day_attachment_gate": "NOT_RUN", "full_world_gate": "NOT_RUN", "scoring_gate": "CLOSED"}
    coverage_file = root / "SHARED_CONTEXT_COVERAGE.csv"
    with coverage_file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(coverage[0]));writer.writeheader();writer.writerows(coverage)
    report["coverage_sha256"] = sha(coverage_file)
    status = root / "SHARED_CONTEXT_STATUS.json";write_json(status, report)
    tag = f"shared-context-v2-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh("release", "create", tag, "--draft", "--target", os.environ["GITHUB_SHA"], "--title", tag,
       "--notes", "Shared ALFRED/CBOE native contexts; not stock-day or full-world coverage.")
    publish_assets(tag, *files, coverage_file, status)
    gh('release','edit',tag,'--draft=false')
    print("SHARED_CONTEXT_COMPLETE", tag, len(coverage), flush=True)


if __name__ == "__main__":
    main()
