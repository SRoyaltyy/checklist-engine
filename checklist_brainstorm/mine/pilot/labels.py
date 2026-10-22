#!/usr/bin/env python3
"""Build open→next-open (primary) and open→close (secondary) labels from Yahoo OHLC.

Merges Grok pilot_matrix OHLC (Aug–Oct 2026, burned smoke) with ds1016 parquet
(pre-Jul selection tape). Prefer non-null rows; on overlap, Grok wins for those dates.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
GROK_OHLC = Path("/workspace/checklist_brainstorm/engine/out/pilot_matrix/yahoo_ohlc_pilot.parquet")
DS_OHLC = Path("/workspace/ds1016/data/prices/ohlc.parquet")
FEE_SIDE = 0.001  # 10 bp


def load_ohlc(tickers: list[str] | None = None) -> pd.DataFrame:
    frames = []
    if DS_OHLC.exists():
        df = pd.read_parquet(DS_OHLC)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        frames.append(df)
    if GROK_OHLC.exists():
        df = pd.read_parquet(GROK_OHLC)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        frames.append(df)
    if not frames:
        raise FileNotFoundError("no OHLC sources")
    all_ = pd.concat(frames, ignore_index=True)
    # prefer last source on dupes (Grok after ds1016)
    all_ = all_.drop_duplicates(["ticker", "date"], keep="last")
    if tickers is not None:
        all_ = all_[all_["ticker"].isin(tickers)].copy()
    return all_.sort_values(["ticker", "date"]).reset_index(drop=True)


def build_labels(ohlc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t, g in ohlc.groupby("ticker", sort=False):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            d = g.at[i, "date"]
            o = float(g.at[i, "open"])
            c = float(g.at[i, "close"])
            prior = float(g.at[i - 1, "close"]) if i > 0 else np.nan
            o2c = (c / o - 1.0) if o > 0 else np.nan
            if i + 1 < len(g):
                o2 = float(g.at[i + 1, "open"])
                o2o = (o2 / o - 1.0) if o > 0 else np.nan
                next_d = g.at[i + 1, "date"]
            else:
                o2o, next_d = np.nan, ""
            rows.append(
                {
                    "ticker": t,
                    "date": d,
                    "prior_close": prior,
                    "open": o,
                    "close": c,
                    "ret_o2o": o2o,
                    "ret_o2c": o2c,
                    "next_date": next_d,
                }
            )
    return pd.DataFrame(rows)


def after_fees(ret, sides: int = 2):
    return ret - sides * FEE_SIDE


if __name__ == "__main__":
    univ = (HERE / "universe.txt").read_text().split()
    lab = build_labels(load_ohlc(univ))
    out = HERE / "panel" / "labels.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    lab.to_parquet(out, index=False)
    pre = lab[lab.date < "2026-07-01"]
    burned = lab[lab.date >= "2026-07-01"]
    print(out, lab.shape, "preJul_o2o", pre.ret_o2o.notna().sum(), "burned_o2o", burned.ret_o2o.notna().sum())
