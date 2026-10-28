"""Recompute the derived breadth series from the published daily counts."""

import hashlib
import urllib.request
from pathlib import Path

import pandas as pd

import breadth_derived

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "outside-breadth-v1-40689026569-1"
DAILY_SHA = "22dfcd51f88d898a7bc156efa9d79677c769d207604f3a68aec065623d65b2c0"
COMMITTED = ROOT / "docs" / "breadth_derived_daily.parquet"


def main():
    target = Path("/tmp/breadth-derived-check/outside_breadth_daily.parquet")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = "https://github.com/SRoyaltyy/checklist-engine/releases/download/%s/outside_breadth_daily.parquet" % RELEASE
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
    with urllib.request.urlopen(request, timeout=120) as response:
        target.write_bytes(response.read())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != DAILY_SHA:
        raise ValueError("published breadth daily bytes differ")
    fresh = breadth_derived.derive(pd.read_parquet(target))
    stored = pd.read_parquet(COMMITTED)
    if list(fresh.columns) != list(stored.columns) or len(fresh) != len(stored):
        raise ValueError("derived breadth shape differs")
    for column in fresh.columns:
        if column in ("date", "available_from"):
            if not fresh[column].equals(stored[column]):
                raise ValueError(column + " differs")
            continue
        gap = (fresh[column] - stored[column]).abs()
        if float(gap.max()) != 0.0:
            raise ValueError(column + " differs")
    print("BREADTH_DERIVED_MATCH", len(fresh), digest)


if __name__ == "__main__":
    main()
