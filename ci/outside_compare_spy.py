"""Per-name comparisons versus SPY, computed on this machine from stitch bars."""

import argparse
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

from outside_compare import EXCLUDED_COMPARATORS, MAP_SEARCH, WINDOWS, compare_one

STITCH_RELEASE = "accepted-price-stitch-v2-40494479693-1"
STITCH_MANIFEST = "ACCEPTED_PRICE_STITCH.json"
STITCH_MANIFEST_SHA256 = "9f97db992522777ef9ae27a0ec9aad4fb9caa80a269393b0d76521aa9aa3f6fe"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def divergence_columns():
    columns = []
    for window in WINDOWS:
        columns.append("divergence_flat_vs_fall_%dd" % window)
        columns.append("divergence_fall_vs_flat_%dd" % window)
    return columns


def build(out, spy_path, chunk_size=400, flags_only=False):
    out = Path(out)
    part_dir = out / "parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + STITCH_RELEASE + "/" + STITCH_MANIFEST,
        out / STITCH_MANIFEST,
    )
    if sha256_file(manifest_path) != STITCH_MANIFEST_SHA256:
        raise ValueError("stitch manifest bytes differ")
    manifest = json.loads(manifest_path.read_text())
    spy = pd.read_parquet(spy_path, columns=["date", "close"])
    spy["date"] = pd.to_datetime(spy["date"]).astype("datetime64[ns]")
    spy = spy.sort_values("date").drop_duplicates("date")
    nxt = dict(zip(spy["date"].iloc[:-1], spy["date"].iloc[1:]))
    as_of = spy["date"].max()
    used = 0
    excluded = list(EXCLUDED_COMPARATORS)
    rows = 0
    part_rows = []
    writer = None
    schema = None
    part_index = 0

    def flush(batch):
        nonlocal writer, schema, part_index, rows
        if not batch:
            return
        frame = pd.concat(batch, ignore_index=True)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if flags_only:
            frame = frame.loc[:, ["ticker", "date", "available_from", *divergence_columns()]].copy()
            for column in divergence_columns():
                frame[column] = frame[column].astype(bool)
            table = pa.Table.from_pandas(frame, preserve_index=False)
        if writer is None:
            schema = table.schema
            output_name = "compare_spy_divergence.parquet" if flags_only else "compare_spy.parquet"
            writer = pq.ParquetWriter(
                part_dir / output_name, schema, compression="zstd", compression_level=19,
                use_dictionary=["ticker"] if flags_only else False,
            )
        writer.write_table(table.cast(schema))
        rows += len(frame)
        part_rows.append(len(frame))
        part_index += 1
        print(json.dumps({"flushed": part_index, "rows": rows, "used": used}), flush=True)

    batch = []
    for part in manifest["parts"]:
        url = "https://github.com/SRoyaltyy/checklist-engine/releases/download/" + part["release"] + "/" + part["part"] + ".tar"
        archive = out / (part["part"] + ".tar")
        download(url, archive)
        if sha256_file(archive) != part["archive_sha256"]:
            raise ValueError("archive bytes differ: " + part["part"])
        with tarfile.open(archive) as bundle:
            for ticker in part["tickers"]:
                if ticker == "SPY":
                    excluded.append({"ticker": "SPY", "reason": "SELF_COMPARATOR"})
                    continue
                member = ticker.encode().hex() + ".bars.parquet"
                extracted = bundle.extractfile(member)
                if extracted is None:
                    excluded.append({"ticker": ticker, "reason": "MISSING_BARS"})
                    continue
                try:
                    bars = pd.read_parquet(io.BytesIO(extracted.read()), columns=["date", "close"])
                    compared = compare_one(bars, spy, as_of=as_of)
                except (ValueError, OSError) as exc:
                    excluded.append({"ticker": ticker, "reason": type(exc).__name__})
                    continue
                compared.insert(0, "ticker", ticker)
                compared["available_from"] = pd.to_datetime(compared["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT)))
                batch.append(compared)
                used += 1
                if len(batch) >= chunk_size:
                    flush(batch)
                    batch = []
        archive.unlink()
    flush(batch)
    if writer is not None:
        writer.close()
    names_expected = int(manifest["accepted_tickers"])
    # SPY itself is the one expected self exclusion when it is in the release.
    proof = dict(
        block="outside_compare_spy",
        as_of=str(pd.Timestamp(as_of).date()),
        stitch_release=STITCH_RELEASE,
        spy_source="light-daily-box-v1-20261028 SPY close",
        names_used=used,
        names_expected=names_expected,
        names_percent=round(100 * used / names_expected, 4),
        rows=rows,
        output_file="compare_spy_divergence.parquet" if flags_only else "compare_spy.parquet",
        output_sha256=sha256_file(part_dir / ("compare_spy_divergence.parquet" if flags_only else "compare_spy.parquet")),
        excluded_comparators=EXCLUDED_COMPARATORS,
        map_search=MAP_SEARCH,
        excluded_names=[row for row in excluded if "ticker" in row],
        windows=[1, 5, 20, 60],
        flat_return=0.01,
        comparator_fall=0.02,
        lookahead="windows end on the session; available_from is the next SPY session",
    )
    if proof["names_percent"] < 95:
        raise ValueError("compared names below 95 percent")
    (out / "OUTSIDE_COMPARE_SPY_PROOF.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"as_of": proof["as_of"], "names_used": used, "rows": rows}))
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--spy", required=True)
    parser.add_argument("--flags-only", action="store_true")
    args = parser.parse_args()
    build(args.out, args.spy, flags_only=args.flags_only)


if __name__ == "__main__":
    main()
