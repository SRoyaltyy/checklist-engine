"""Recompute derived breadth candles from the published daily counts."""

import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

import breadth_derived

ROOT = Path(__file__).resolve().parents[1]
DAILY_RELEASE = "outside-breadth-stitch-v1"
DAILY_SHA = "22dfcd51f88d898a7bc156efa9d79677c769d207604f3a68aec065623d65b2c0"
WEIGHT_RELEASE = "accepted-price-stitch-v2-40494479693-1"
WEIGHT_SHA = "6961605c52041be1c437b425bc8c6251e65ee6c63270d185ea507605fe597114"
COMMITTED = ROOT / "docs" / "breadth_derived_candles.parquet"
PROOF = ROOT / "docs" / "BREADTH_DERIVED_CANDLE_PROOF.json"


def _download(url, target):
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
    with urllib.request.urlopen(request, timeout=120) as response:
        target.write_bytes(response.read())


def _order(frame):
    rank = frame["timeframe"].map(lambda value: 99 if value == "monthly" else int(value[:-1]))
    return frame.assign(_rank=rank).sort_values(["_rank", "date"]).drop(columns="_rank").reset_index(drop=True)


def _fill(weights, frame):
    total = int(weights["stock_days"].sum())
    left = weights.sort_values("date").rename(columns={"date": "stock_date"})
    right = frame.sort_values("available_from")
    joined = pd.merge_asof(left, right, left_on="stock_date", right_on="available_from", direction="backward")
    present = joined["trin"].notna()
    counted = int(joined.loc[present, "stock_days"].sum())
    first = pd.Timestamp(joined.loc[present, "stock_date"].min()).date().isoformat()
    return len(frame), counted, round(100 * counted / total, 4), first


def main():
    work = Path("/tmp/breadth-derived-candle-check")
    work.mkdir(parents=True, exist_ok=True)
    daily_path = work / "outside_breadth_daily.parquet"
    weight_path = work / "ACCEPTED_PRICE_STOCK_DAYS.csv"
    _download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/%s/outside_breadth_daily.parquet" % DAILY_RELEASE,
        daily_path,
    )
    _download(
        "https://github.com/SRoyaltyy/checklist-engine/releases/download/%s/ACCEPTED_PRICE_STOCK_DAYS.csv" % WEIGHT_RELEASE,
        weight_path,
    )
    if hashlib.sha256(daily_path.read_bytes()).hexdigest() != DAILY_SHA:
        raise ValueError("published breadth daily bytes differ")
    if hashlib.sha256(weight_path.read_bytes()).hexdigest() != WEIGHT_SHA:
        raise ValueError("published stock-day weights differ")
    panel = pd.read_parquet(daily_path)
    fresh = _order(breadth_derived.derive_candles(panel, pd.to_datetime(panel["date"])))
    stored = _order(pd.read_parquet(COMMITTED))
    if list(fresh.columns) != list(stored.columns) or len(fresh) != len(stored):
        raise ValueError("derived candle shape differs")
    for column in fresh.columns:
        if column in breadth_derived.COLUMNS:
            if not np.array_equal(fresh[column].to_numpy(), stored[column].to_numpy(), equal_nan=True):
                raise ValueError(column + " differs")
            continue
        if not fresh[column].astype(str).equals(stored[column].astype(str)):
            raise ValueError(column + " differs")
    proof = json.loads(PROOF.read_text())
    weights = pd.read_csv(weight_path, parse_dates=["date"])
    for item in proof["timeframes"]:
        rows, counted, percent, first = _fill(weights, fresh[fresh.timeframe == item["timeframe"]])
        if (rows, counted, percent, first) != (
            item["rows"], item["non_null_stock_days"], item["non_null_percent"], item["first_date_available"],
        ):
            raise ValueError(item["timeframe"] + " coverage differs")
    print("BREADTH_DERIVED_CANDLES_MATCH", len(fresh), DAILY_SHA)


if __name__ == "__main__":
    main()
