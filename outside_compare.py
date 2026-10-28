"""Comparisons of one name with SPY. Windows end on session D.

Sector and industry comparators are not filled here: there is no dated
stock-to-ETF map that was known on each past day. A current label is not
written back onto 2020.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOWS = (1, 5, 20, 60)
FLAT = 0.01
FALL = 0.02
CORR_WINDOWS = (20, 60)
BREAK_BASELINE = 60
EXCLUDED_COMPARATORS = (
    {"comparator": "sector_etf", "reason": "NO_DATED_STOCK_TO_SECTOR_MAP"},
    {"comparator": "industry_etf", "reason": "NO_DATED_STOCK_TO_INDUSTRY_MAP"},
)


def _return(close, window):
    out = np.full(len(close), np.nan, dtype=np.float64)
    if len(close) <= window:
        return out
    base = close[:-window]
    last = close[window:]
    ok = np.isfinite(base) & np.isfinite(last) & (base != 0)
    changed = np.divide(last, base, out=np.full(len(last), np.nan), where=ok)
    out[window:] = np.where(ok, changed - 1.0, np.nan)
    return out


def compare_one(name, comparator, as_of=None):
    left = name.loc[:, ["date", "close"]].rename(columns={"close": "name"})
    right = comparator.loc[:, ["date", "close"]].rename(columns={"close": "comp"})
    left["date"] = pd.to_datetime(left["date"]).astype("datetime64[ns]")
    right["date"] = pd.to_datetime(right["date"]).astype("datetime64[ns]")
    frame = left.merge(right, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise ValueError("duplicate sessions")
    if as_of is not None:
        frame = frame[frame["date"] <= pd.Timestamp(as_of)].reset_index(drop=True)
    name_px = frame["name"].to_numpy(dtype=np.float64)
    comp_px = frame["comp"].to_numpy(dtype=np.float64)
    out = pd.DataFrame({"date": frame["date"]})
    valid = np.isfinite(name_px) & np.isfinite(comp_px) & (comp_px != 0)
    ratio = np.full(len(frame), np.nan)
    ratio[valid] = name_px[valid] / comp_px[valid]
    out["rel_strength_ratio"] = ratio
    name_ret = {window: _return(name_px, window) for window in WINDOWS}
    comp_ret = {window: _return(comp_px, window) for window in WINDOWS}
    for window in WINDOWS:
        stock = name_ret[window]
        other = comp_ret[window]
        spread = np.full(len(frame), np.nan)
        known = np.isfinite(stock) & np.isfinite(other)
        spread[known] = stock[known] - other[known]
        out[f"return_spread_{window}d"] = spread
        flag = np.zeros(len(frame), dtype=np.int8)
        flag[known] = ((np.abs(stock[known]) <= FLAT) & (other[known] <= -FALL)).astype(np.int8)
        out[f"divergence_flat_vs_fall_{window}d"] = flag
    daily_name = pd.Series(_return(name_px, 1))
    daily_comp = pd.Series(_return(comp_px, 1))
    for window in CORR_WINDOWS:
        corr = daily_name.rolling(window, min_periods=window).corr(daily_comp).to_numpy(dtype=np.float64)
        out[f"corr_{window}d"] = corr
        history = pd.Series(corr).shift(1).rolling(BREAK_BASELINE, min_periods=BREAK_BASELINE).mean()
        out[f"corr_break_{window}d"] = corr - history.to_numpy(dtype=np.float64)
    return out
