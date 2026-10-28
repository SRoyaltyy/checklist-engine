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
# One paired daily return cannot make a correlation, so there is no 1-session column.
CORR_WINDOWS = (5, 20, 60)
BREAK_BASELINE = 60
# Fullscan Finviz exports name Ticker, Sector, and Industry. The first file is
# 2026-04-26 and the last is 2026-10-27 (63 dated files, plus finviz_latest.csv).
# A snapshot is usable only on later sessions. That tail is 128 of the 1,714
# NYSE sessions from 2020-01-02 through 2026-10-27, which is 7.4679%. Theme-radar
# sector files are aggregates, not a stock map, and start on 2026-10-21.
# fullscan industry_etf.py maps a current industry name to an ETF and has no date.
# The April 2026 label is not written onto 2020.
# Archived SEC submissions on sec-world-v4 carry one current sic per company.
# The sample part has no SIC on each filing and no SIC column in the facts file.
# That current SIC is not written onto 2020.
MAP_SEARCH = {
    "sources_checked": [
        "SRoyaltyy/fullscan data/exports/finviz_YYYY-MM-DD.csv",
        "SRoyaltyy/theme-radar data/finviz_extras/groups/*_sector.csv",
        "SRoyaltyy/fullscan src/industry_etf.py",
        "sec-world-v4-40267486206-1 sec_world_shard_000_attempt_1_part_000.tar",
    ],
    "fullscan_snapshot_files": 63,
    "fullscan_first_file_date": "2026-04-26",
    "fullscan_last_file_date": "2026-10-27",
    "sessions_2020_01_02_through_2026_10_27": 1714,
    "sessions_on_or_after_first_usable_snapshot": 128,
    "first_usable_session": "2026-04-27",
    "coverage_percent": 7.4679,
    "decision": "EXCLUDED",
    "sec_submissions": {
        "release": "sec-world-v4-40267486206-1",
        "sample_archive": "sec_world_shard_000_attempt_1_part_000.tar",
        "submissions_read": 20,
        "facts_read": 20,
        "sic_fields": ["sic", "sicDescription"],
        "filings_with_sic_column": 0,
        "facts_with_sic_column": 0,
        "decision": "NOT_USED_CURRENT_SIC_WOULD_REWRITE_2020",
    },
}
EXCLUDED_COMPARATORS = (
    {
        "comparator": "sector_etf",
        "reason": "NO_DATED_STOCK_TO_SECTOR_MAP",
        "coverage_percent": MAP_SEARCH["coverage_percent"],
    },
    {
        "comparator": "industry_etf",
        "reason": "NO_DATED_STOCK_TO_INDUSTRY_MAP",
        "coverage_percent": MAP_SEARCH["coverage_percent"],
    },
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
        opposite = np.zeros(len(frame), dtype=np.int8)
        opposite[known] = ((stock[known] <= -FALL) & (np.abs(other[known]) <= FLAT)).astype(np.int8)
        out[f"divergence_fall_vs_flat_{window}d"] = opposite
    daily_name = pd.Series(_return(name_px, 1))
    daily_comp = pd.Series(_return(comp_px, 1))
    for window in CORR_WINDOWS:
        corr = daily_name.rolling(window, min_periods=window).corr(daily_comp).to_numpy(dtype=np.float64)
        out[f"corr_{window}d"] = corr
        history = pd.Series(corr).shift(1).rolling(BREAK_BASELINE, min_periods=BREAK_BASELINE).mean()
        out[f"corr_break_{window}d"] = corr - history.to_numpy(dtype=np.float64)
    return out
