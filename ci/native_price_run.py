"""Run the frozen native-price recipe with separately versioned release transport.

The frozen recipe includes native_price_blocks.py itself. Keep that file intact
so already prepared inputs and durable indicator parts remain reusable. This
entry point changes publication only; source_commit binds the transport version.
"""
import json
from pathlib import Path

from ci import native_price_blocks as builder
from ci.release_assets import describe_failure, publish_assets


def main():
    original_gh = builder.gh

    def durable_gh(*args):
        if args[:2] != ("release", "upload"):
            return original_gh(*args)
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
    try:
        builder.main()
    finally:
        builder.gh = original_gh


if __name__ == "__main__":
    main()
