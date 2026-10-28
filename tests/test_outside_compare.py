import numpy as np
import pandas as pd

import outside_compare as comp


def frame(closes, start="2024-01-02"):
    return pd.DataFrame({"date": pd.bdate_range(start, periods=len(closes)), "close": closes})


def test_future_close_does_not_change_today():
    name = frame(list(range(10, 90)))
    other = frame(list(range(20, 100)))
    early = comp.compare_one(name.iloc[:40], other.iloc[:40])
    full = comp.compare_one(name, other)
    day = early.date.iloc[30]
    left = early.set_index("date").loc[day]
    right = full.set_index("date").loc[day]
    assert left["return_spread_5d"] == right["return_spread_5d"]
    assert left["corr_20d"] == right["corr_20d"]


def test_flat_name_and_falling_comparator_is_divergence():
    name = frame([10, 10, 10])
    other = frame([10, 9.4, 9.4])
    out = comp.compare_one(name, other)
    assert int(out.divergence_flat_vs_fall_1d.iloc[1]) == 1
    assert int(out.divergence_flat_vs_fall_1d.iloc[2]) == 0
    assert int(out.divergence_fall_vs_flat_1d.iloc[1]) == 0


def test_falling_name_and_flat_comparator_is_the_other_divergence():
    name = frame([10, 9.4, 9.4])
    other = frame([10, 10, 10])
    out = comp.compare_one(name, other)
    assert int(out.divergence_fall_vs_flat_1d.iloc[1]) == 1
    assert int(out.divergence_fall_vs_flat_1d.iloc[2]) == 0
    assert int(out.divergence_flat_vs_fall_1d.iloc[1]) == 0


def test_zero_variance_correlation_stays_blank():
    name = frame([10.0] * 30)
    other = frame([float(i + 1) for i in range(30)])
    out = comp.compare_one(name, other)
    assert np.isnan(out.corr_20d.iloc[-1])


def test_as_of_drops_later_rows():
    name = frame([10, 11, 12, 13])
    other = frame([10, 10, 10, 10])
    out = comp.compare_one(name, other, as_of="2024-01-03")
    assert list(out.date.dt.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]


def test_sector_and_industry_are_named_exclusions():
    reasons = {row["comparator"]: row["reason"] for row in comp.EXCLUDED_COMPARATORS}
    assert reasons["sector_etf"] == "NO_DATED_STOCK_TO_SECTOR_MAP"
    assert "INDUSTRY" in reasons["industry_etf"]
    assert comp.MAP_SEARCH["decision"] == "EXCLUDED"
    assert comp.MAP_SEARCH["coverage_percent"] < 95
    assert comp.MAP_SEARCH["sessions_on_or_after_first_usable_snapshot"] == 128
    assert comp.MAP_SEARCH["sessions_2020_01_02_through_2026_10_27"] == 1714
