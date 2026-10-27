"""Run the frozen native-price recipe with separately versioned release transport.

The frozen recipe includes native_price_blocks.py itself. Keep that file intact
so already prepared inputs and durable indicator parts remain reusable. This
entry point changes publication only; source_commit binds the transport version.
"""
import json
from pathlib import Path
import re
import subprocess
import os

from ci import native_price_blocks as builder
from ci.release_assets import describe_failure, publish_assets, asset_index, gh_retry, download_asset


def recovered_parts(tag, inputs, directory):
    """Reuse only complete remote parts; preserve abandoned partial uploads."""
    directory = Path(directory);directory.mkdir(parents=True, exist_ok=True)
    try:assets = asset_index(tag)
    except subprocess.CalledProcessError as exc:
        if not re.search(r"\bHTTP\s+404\b", str(exc.stderr or "")):
            raise
        builder.write_json(directory / "RECOVERY_SKIPPED_PARTS.json", {
            "source_release": tag, "prior_release_absent": True, "completed_parts_reused": 0,
            "skipped": [], "original_assets_modified": False})
        print("RECOVERY_FROM_SCRATCH", tag, flush=True)
        return [], []
    parts = [];records = [];seen = set();skipped = []
    for name in sorted(n for n in assets if re.fullmatch(r"part_\d+\.json", n)):
        stem = name[:-5]
        required = [name, stem + ".tar", stem + ".coverage.csv"]
        incomplete = [n for n in required if n not in assets or assets[n]["state"] != "uploaded"]
        if incomplete:
            skipped.append({"part": stem, "missing_or_incomplete": incomplete})
            print("RECOVERY_SKIP_INCOMPLETE_PART", tag, stem, incomplete, flush=True)
            continue
        file = builder.download(tag, name, directory)
        if assets[name].get("digest") != "sha256:" + builder.sha(file):
            raise ValueError("resume manifest remote digest differs")
        report = json.loads(file.read_text())
        if report["recipe_fingerprint"] != inputs["recipe_fingerprint"] or report["inputs_tag"] != inputs["inputs_tag"]:
            raise ValueError("resume recipe/input differs")
        for suffix, field in ((".tar", "archive_sha256"), (".coverage.csv", "coverage_sha256")):
            if assets[stem + suffix].get("digest") != "sha256:" + report[field]:
                raise ValueError("resume part remote digest differs: " + stem + suffix)
        tickers = report["tickers"]
        if len(tickers) != len(set(tickers)) or seen & set(tickers):
            raise ValueError("duplicate resumed tickers")
        entities = report["entity_records"]
        if len(entities) != len(tickers) or {r["ticker"] for r in entities} != set(tickers):
            raise ValueError("resume records incomplete")
        seen.update(tickers);records.extend(entities)
        parts.append({"part": stem, "release": tag, "tickers": tickers,
                      "archive_sha256": report["archive_sha256"], "coverage_sha256": report["coverage_sha256"]})
    builder.write_json(directory / "RECOVERY_SKIPPED_PARTS.json", {"source_release": tag, "skipped": skipped,
                       "completed_parts_reused": len(parts), "original_assets_modified": False})
    return parts, records


def recovered_chain(tag, inputs, directory):
    """Combine disjoint complete parts from newest and earlier failed attempts."""
    prefixes = json.loads(os.environ.get("NATIVE_RESUME_PREFIXES", "[]"))
    tags = list(dict.fromkeys([tag, *(prefix + "-" + tag.rsplit("-", 1)[1] for prefix in prefixes)]))
    parts = [];records = [];seen = set();skipped = []
    directory = Path(directory)
    for position, source in enumerate(tags):
        source_parts, source_records = recovered_parts(source, inputs, directory / f"source_{position}")
        by_ticker = {r["ticker"]: r for r in source_records}
        for part in source_parts:
            if seen & set(part["tickers"]):
                skipped.append({"release": source, "part": part["part"], "reason": "overlaps newer complete part; uncovered entities will be rebuilt"})
                continue
            parts.append(part);records.extend(by_ticker[ticker] for ticker in part["tickers"]);seen.update(part["tickers"])
    directory.mkdir(parents=True, exist_ok=True)
    builder.write_json(directory / "RECOVERY_CHAIN.json", {"source_releases": tags, "parts": parts,
                       "completed_entities_reused": len(records), "skipped_overlaps": skipped})
    return parts, records


def main():
    original_gh = builder.gh
    original_recovered = builder.recovered_parts
    original_download = builder.download
    pending_releases = {}
    created_drafts = set()

    def durable_gh(*args):
        if args[:2] == ("release", "create") and len(args) > 3 and Path(args[3]).name == "SHARD_REQUEST.json":
            # A request is not data. Delay any remote release until a complete
            # nonempty part (or a verified all-resumed completion) exists.
            pending_releases[args[2]] = args
            return
        if args[:2] != ("release", "upload"):
            return gh_retry(*args)
        tag, *files = args[2:]
        try:
            if tag in pending_releases:
                pending = pending_releases[tag]
                if len(files) == 1 and Path(files[0]).name == "SHARD_FAILED.json":
                    print("NATIVE_NO_DATA_RELEASE_NOT_CREATED", tag, flush=True)
                    return
                manifest = json.loads(Path(files[-1]).read_text())
                if Path(files[-1]).name == "SHARD_COMPLETE.json":
                    nonempty = manifest.get("records") and manifest.get("parts")
                else:
                    nonempty = manifest.get("tickers") and manifest.get("members")
                if not nonempty:
                    raise ValueError("refusing release without completed price data")
                # Remain draft if uploading the first price part fails. Never
                # expose a request-only shell as a published price release.
                if tag not in created_drafts:
                    gh_retry("release", "create", tag, "--draft", *pending[4:])
                    created_drafts.add(tag)
                publish_assets(tag, *files, pending[3])
                gh_retry("release", "edit", tag, "--draft=false")
                del pending_releases[tag]
                return
            return publish_assets(tag, *files)
        except Exception as exc:
            # The builder will re-raise its original exception after emitting
            # SHARD_FAILED. Do not replace that cause with a reporting failure.
            if len(files) != 1 or Path(files[0]).name != "SHARD_FAILED.json":
                raise
            file = Path(files[0])
            failure = json.loads(file.read_text(encoding="utf-8"))
            failure["failure_report_upload_error"] = describe_failure(exc)
            builder.write_json(file, failure)
            print("NATIVE_FAILURE_REPORT_LOCAL", str(file), describe_failure(exc), flush=True)

    builder.gh = durable_gh
    builder.recovered_parts = recovered_chain
    builder.download = download_asset
    try:
        builder.main()
    finally:
        builder.gh = original_gh
        builder.recovered_parts = original_recovered
        builder.download = original_download


if __name__ == "__main__":
    main()
