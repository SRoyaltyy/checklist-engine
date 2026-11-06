import pandas as pd

from stooq_gapfill import classify_dates, parse_stooq_dates


def sessions():
    return pd.bdate_range("2024-01-02", periods=20)


def test_parser_skips_the_header_and_reads_the_date():
    text = "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>\nAAA.US,D,20240102,000000,1,1,1,1,10,0\n"
    assert parse_stooq_dates(text) == [pd.Timestamp("2024-01-02").date()]


def test_dense_late_listing_passes_and_a_gappy_name_is_excluded():
    days = list(sessions().date)
    late = classify_dates(days[5:], days)
    assert late["status"] == "PASS"
    assert late["reason"] == "LISTED_AFTER_WINDOW_START"
    assert late["internal_percent"] == 100
    holes = classify_dates([days[0], days[-1]], days)
    assert holes["status"] == "EXCLUDE"
    assert holes["reason"] == "HOLES_BETWEEN_FIRST_AND_LAST"
    assert holes["internal_percent"] < 95


def test_a_dense_series_that_stops_early_keeps_its_bars():
    days = list(sessions().date)
    ended = classify_dates(days[:12], days)
    assert ended["status"] == "PASS"
    assert ended["reason"] == "ENDED_BEFORE_WINDOW_END"


def test_no_bar_inside_the_window_is_excluded():
    days = list(sessions().date)
    missing = classify_dates([pd.Timestamp("1999-01-04").date()], days)
    assert missing["status"] == "EXCLUDE"
    assert missing["reason"] == "NO_WINDOW_BARS"
