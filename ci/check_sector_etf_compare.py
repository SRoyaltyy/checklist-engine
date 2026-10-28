"""Recompute stock-versus-sector-ETF coverage and match the committed proof."""

import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from outside_compare import CORR_WINDOWS, WINDOWS, compare_one

ROOT = Path(__file__).resolve().parents[1]
PROOF_PATH = ROOT / "docs" / "SECTOR_COMPARE_COVERAGE.json"
STITCH_RELEASE = "accepted-price-stitch-v2-40494479693-1"
STITCH_MANIFEST_SHA256 = "9f97db992522777ef9ae27a0ec9aad4fb9caa80a269393b0d76521aa9aa3f6fe"
LIGHT_DAILY = "light-daily-box-v1-20261028"
COMPARATORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY", "SPY")
VALUE_COLUMNS = (
    ["rel_strength_ratio"]
    + ["return_spread_%dd" % window for window in WINDOWS]
    + ["divergence_flat_vs_fall_%dd" % window for window in WINDOWS]
    + ["divergence_fall_vs_flat_%dd" % window for window in WINDOWS]
    + ["corr_%dd" % window for window in CORR_WINDOWS]
    + ["corr_break_%dd" % window for window in CORR_WINDOWS]
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".partial")
    last_error = None
    for _ in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
            with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as stream:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    stream.write(chunk)
            temporary.replace(target)
            return target
        except Exception as exc:
            last_error = exc
            if temporary.exists():
                temporary.unlink()
    raise RuntimeError("download failed: %s" % url) from last_error


def release_file(tag, name, path):
    return download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/%s/%s" % (tag, name),
        path,
    )


def load_close(path):
    frame = pd.read_parquet(path, columns=["date", "close"])
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    return frame.sort_values("date").drop_duplicates("date").reset_index(drop=True)


def align(name, comparator, as_of, window_start):
    built = compare_one(name, comparator, as_of=as_of)
    dates = pd.to_datetime(name["date"]).astype("datetime64[ns]")
    dates = dates[(dates >= window_start) & (dates <= pd.Timestamp(as_of))]
    frame = pd.DataFrame({"date": dates}).drop_duplicates("date")
    return frame.merge(built, on="date", how="left")


def blank_stats():
    return {
        "rows": 0,
        "names": 0,
        "early_available_from": 0,
        "weekend_available_from": 0,
        "missing_available_from": 0,
        "non_null": {column: 0 for column in VALUE_COLUMNS},
        "first_date": {column: None for column in VALUE_COLUMNS},
    }


def update(stats, compared):
    stats["rows"] += len(compared)
    stats["names"] += 1
    early = compared["available_from"].notna() & (compared["available_from"] <= compared["date"])
    stats["early_available_from"] += int(early.sum())
    present = compared["available_from"].notna()
    stats["missing_available_from"] += int((~present).sum())
    stats["weekend_available_from"] += int((present & (compared["available_from"].dt.dayofweek >= 5)).sum())
    for column in VALUE_COLUMNS:
        values = compared[column].to_numpy(dtype=np.float64)
        known = np.isfinite(values)
        stats["non_null"][column] += int(known.sum())
        if known.any():
            stamp = str(pd.Timestamp(compared.loc[known, "date"].iloc[0]).date())
            current = stats["first_date"][column]
            if current is None or stamp < current:
                stats["first_date"][column] = stamp


def measure(work):
    work = Path(work)
    manifest_path = release_file(STITCH_RELEASE, "ACCEPTED_PRICE_STITCH.json", work / "ACCEPTED_PRICE_STITCH.json")
    if sha256_file(manifest_path) != STITCH_MANIFEST_SHA256:
        raise ValueError("stitch manifest bytes differ")
    manifest = json.loads(manifest_path.read_text())
    closes = {}
    for name in ("SPY", *COMPARATORS):
        closes[name] = load_close(release_file(LIGHT_DAILY, name + ".parquet", work / (name + ".parquet")))
    spy_dates = closes["SPY"]["date"]
    nxt = dict(zip(spy_dates.iloc[:-1], spy_dates.iloc[1:]))
    as_of = spy_dates.max()
    window_start = pd.Timestamp("2020-01-02")
    stats = {name: blank_stats() for name in COMPARATORS}
    for part_number, part in enumerate(manifest["parts"], start=1):
        archive = release_file(part["release"], part["part"] + ".tar", work / (part["part"] + ".tar"))
        if sha256_file(archive) != part["archive_sha256"]:
            raise ValueError("archive bytes differ: " + part["part"])
        with tarfile.open(archive) as bundle:
            for ticker in part["tickers"]:
                extracted = bundle.extractfile(ticker.encode().hex() + ".bars.parquet")
                if extracted is None:
                    raise ValueError("missing bars for " + ticker)
                bars = pd.read_parquet(io.BytesIO(extracted.read()), columns=["date", "close"])
                for name in COMPARATORS:
                    if ticker == name:
                        continue
                    compared = align(bars, closes[name], as_of, window_start)
                    compared["available_from"] = pd.to_datetime(
                        compared["date"].map(lambda day: nxt.get(pd.Timestamp(day), pd.NaT))
                    )
                    update(stats[name], compared)
        archive.unlink()
        print(json.dumps({"part": part_number, "parts": len(manifest["parts"])}), flush=True)
    return stats


def require_same(proof, stats):
    for name, item in proof["comparators"].items():
        got = stats[name]
        if got["rows"] != item["rows"] or got["names"] != item["names"]:
            raise ValueError("%s rows %s/%s names %s/%s" % (name, got["rows"], item["rows"], got["names"], item["names"]))
        if got["early_available_from"] or got["weekend_available_from"] or got["missing_available_from"]:
            raise ValueError("%s availability is not the next session" % name)
        rows = got["rows"]
        for column, record in item["columns"].items():
            percent = round(100 * got["non_null"][column] / rows, 4) if rows else None
            if percent != record["non_null_percent"] or got["first_date"][column] != record["first_date"]:
                raise ValueError("%s %s is %s from %s, proof %s from %s" % (
                    name, column, percent, got["first_date"][column], record["non_null_percent"], record["first_date"]))
    print(json.dumps({"sector_etf_compare": "MATCH", "comparators": len(proof["comparators"])}), flush=True)


SPY_EXPECTED = {
    "rel_strength_ratio": 100.0,
    "return_spread_60d": 95.9645,
    "corr_60d": 95.9428,
    "corr_break_60d": 91.8972,
}


def main():
    proof = json.loads(PROOF_PATH.read_text())
    if proof.get("own_sector") != "NOT_ASSIGNED" or proof.get("spy_control") != "MATCH":
        raise ValueError("committed proof is not the sector-ETF measurement")
    stats = measure(Path("/tmp/sector-etf-compare-check"))
    require_same(proof, stats)
    spy = stats["SPY"]
    for column, expected in SPY_EXPECTED.items():
        percent = round(100 * spy["non_null"][column] / spy["rows"], 4)
        if percent != expected:
            raise ValueError("SPY control %s is %s" % (column, percent))
    print(json.dumps({"spy_control": "MATCH"}), flush=True)


if __name__ == "__main__":
    main()
