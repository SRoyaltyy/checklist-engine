"""Run the frozen native-price recipe with separately versioned release transport.

The frozen recipe includes native_price_blocks.py itself. Keep that file intact
so already prepared inputs and durable indicator parts remain reusable. This
entry point changes publication only; source_commit binds the transport version.
"""
import json
from pathlib import Path
import re

from ci import native_price_blocks as builder
from ci.release_assets import describe_failure, publish_assets, asset_index, gh_retry, download_asset


def recovered_parts(tag, inputs, directory):
    """Reuse only complete remote parts; preserve abandoned partial uploads."""
    assets = asset_index(tag);parts = [];records = [];seen = set();skipped = []
    directory = Path(directory);directory.mkdir(parents=True, exist_ok=True)
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


def main():
    original_gh = builder.gh
    original_recovered = builder.recovered_parts
    original_download = builder.download

    def durable_gh(*args):
        if args[:2] != ("release", "upload"):
            return gh_retry(*args)
        tag, *files = args[2:]
        try:
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
    builder.recovered_parts = recovered_parts
    builder.download = download_asset
    try:
        builder.main()
    finally:
        builder.gh = original_gh
        builder.recovered_parts = original_recovered
        builder.download = original_download


if __name__ == "__main__":
    main()
