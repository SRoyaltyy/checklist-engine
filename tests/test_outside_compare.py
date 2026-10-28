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
    assert np.isnan(out.divergence_flat_vs_fall_1d.iloc[0])
    assert int(out.divergence_flat_vs_fall_1d.iloc[1]) == 1
    assert int(out.divergence_flat_vs_fall_1d.iloc[2]) == 0
    assert int(out.divergence_fall_vs_flat_1d.iloc[1]) == 0


def test_falling_name_and_flat_comparator_is_the_other_divergence():
    name = frame([10, 9.4, 9.4])
    other = frame([10, 10, 10])
    out = comp.compare_one(name, other)
    assert np.isnan(out.divergence_fall_vs_flat_1d.iloc[0])
    assert int(out.divergence_fall_vs_flat_1d.iloc[1]) == 1
    assert int(out.divergence_fall_vs_flat_1d.iloc[2]) == 0
    assert int(out.divergence_flat_vs_fall_1d.iloc[1]) == 0


def test_five_session_correlation_uses_five_paired_daily_returns():
    name_close = [10, 11, 10, 12, 11, 13, 12, 14]
    other_close = [10, 10, 11, 11, 12, 10, 11, 13]
    out = comp.compare_one(frame(name_close), frame(other_close))
    assert "corr_1d" not in out.columns and "corr_break_1d" not in out.columns
    name_ret = pd.Series(name_close).pct_change()
    other_ret = pd.Series(other_close).pct_change()
    expected = name_ret.rolling(5, min_periods=5).corr(other_ret)
    assert out.corr_5d.iloc[:5].isna().all()
    assert np.isclose(out.corr_5d.iloc[5], expected.iloc[5])
    assert np.isnan(out.corr_break_5d.iloc[5])


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


def test_committed_five_session_correlation_waits_for_the_next_session():
    import hashlib
    from pathlib import Path
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    path = Path("docs/compare_spy_corr5.parquet")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == "49a4ad58dd73505bc7246612d900157d89bf4b87a6f88676b911744d0c854878"
    table = pq.read_table(path)
    assert table.num_rows == 12362658
    assert table.column_names == ["ticker", "date", "available_from", "corr_5d"]
    early = pc.sum(pc.and_(pc.is_valid(table.column("available_from")), pc.less_equal(table.column("available_from"), table.column("date")))).as_py()
    assert early == 0
    filled = pc.sum(pc.is_valid(table.column("corr_5d"))).as_py()
    assert filled / table.num_rows >= 0.95


def test_committed_divergence_flags_stay_blank_until_the_window_is_known():
    import hashlib
    from pathlib import Path
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    path = Path("docs/compare_spy_divergence.parquet")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == "a0be3251298d763df11069c42a90b7b880ed72e1705db563c5861ecd98652c22"
    table = pq.read_table(path)
    assert table.num_rows == 12362658
    early = pc.sum(pc.and_(pc.is_valid(table.column("available_from")), pc.less_equal(table.column("available_from"), table.column("date")))).as_py()
    assert early == 0
    for column in table.column_names:
        if not column.startswith("divergence"):
            continue
        filled = pc.sum(pc.is_valid(table.column(column))).as_py() / table.num_rows
        assert filled >= 0.95


def test_sector_and_industry_are_named_exclusions():
    reasons = {row["comparator"]: row["reason"] for row in comp.EXCLUDED_COMPARATORS}
    assert reasons["sector_etf"] == "NO_DATED_STOCK_TO_SECTOR_MAP"
    assert "INDUSTRY" in reasons["industry_etf"]
    assert comp.MAP_SEARCH["decision"] == "EXCLUDED"
    assert comp.MAP_SEARCH["coverage_percent"] < 95
    assert comp.MAP_SEARCH["sessions_on_or_after_first_usable_snapshot"] == 128
    assert comp.MAP_SEARCH["sessions_2020_01_02_through_2026_10_27"] == 1714
    sec = comp.MAP_SEARCH["sec_submissions"]
    assert sec["submissions_read"] == 20 and sec["filings_with_sic_column"] == 0
    assert sec["facts_with_sic_column"] == 0
    assert sec["decision"] == "NOT_USED_CURRENT_SIC_WOULD_REWRITE_2020"
