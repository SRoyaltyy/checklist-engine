import numpy as np
import pandas as pd
import pytest

import outside_calendar as cal

HISTORICAL = """
<h5>March 15 (unscheduled) Meeting - 2020</h5>
<h5>March 17-18 (cancelled) Meeting - 2020</h5>
<h5>March 19 (notation vote) - 2020</h5>
<h5>April 28-29 Meeting - 2020</h5>
"""

CURRENT = """
<a id="1">2024 FOMC Meetings</a>
<div class="fomc-meeting__month">Apr/May</div>
<div class="fomc-meeting__date">30-1*</div>
<div class="fomc-meeting__month">August</div>
<div class="fomc-meeting__date">22 (notation vote)</div>
<a id="2">2025 FOMC Meetings</a>
<div class="fomc-meeting__month">January</div>
<div class="fomc-meeting__date">28-29</div>
"""


def sessions_through(start, count, extra=5):
    return pd.bdate_range(start, periods=count + extra)


def test_historical_parser_skips_cancelled_and_keeps_notation_separate():
    frame = cal.parse_fomc_historical(HISTORICAL, 2020)
    dates = set(frame.date.dt.strftime("%Y-%m-%d"))
    assert "2020-03-17" not in dates and "2020-03-18" not in dates
    assert set(frame.loc[frame.kind == "meeting", "date"].dt.strftime("%Y-%m-%d")) == {
        "2020-03-15", "2020-04-28", "2020-04-29",
    }
    assert list(frame.loc[frame.kind == "notation", "date"].dt.strftime("%Y-%m-%d")) == ["2020-03-19"]


def test_current_parser_splits_years_and_month_wraps():
    frame = cal.parse_fomc_calendars(CURRENT)
    meetings = set(frame.loc[frame.kind == "meeting", "date"].dt.strftime("%Y-%m-%d"))
    assert meetings == {"2024-04-30", "2024-05-01", "2025-01-28", "2025-01-29"}
    assert list(frame.loc[frame.kind == "notation", "date"].dt.strftime("%Y-%m-%d")) == ["2024-08-22"]


def test_weekend_announcement_flags_the_next_session():
    sessions = pd.bdate_range("2020-03-13", periods=5)
    # 2020-03-15 is a Sunday.
    chosen = cal.session_or_next(["2020-03-15"], sessions)
    assert list(chosen.strftime("%Y-%m-%d")) == ["2020-03-16"]


def test_opex_moves_off_a_missing_friday_and_days_to_is_zero_on_the_day():
    sessions = list(pd.bdate_range("2024-01-02", periods=25))
    friday = pd.Timestamp("2024-01-19")  # third Friday
    assert friday in sessions
    sessions = [day for day in sessions if day != friday]
    opex = cal.monthly_opex(sessions)
    assert pd.Timestamp("2024-01-18") in opex
    assert friday not in opex
    panel = cal.build_calendar(
        list(sessions) + list(pd.bdate_range("2024-02-01", periods=5)),
        pd.DataFrame(columns=["date", "kind"]),
        [], [], "2024-01-31",
    )
    # The January panel uses the sessions passed in, which still omit Jan 19.
    row = panel.set_index("date").loc[pd.Timestamp("2024-01-18")]
    assert bool(row.is_opex) and row.days_to_opex == 0


def test_first_vintage_is_the_release_and_a_future_release_is_not_flagged():
    vintages = pd.DataFrame({
        "obs_date": ["2024-01-01", "2024-01-01", "2024-02-01"],
        "vintage_date": ["2024-02-13", "2024-03-12", "2024-03-20"],
    })
    dates = cal.first_release_dates(vintages)
    assert list(pd.DatetimeIndex(dates).strftime("%Y-%m-%d")) == ["2024-02-13", "2024-03-20"]
    sessions = pd.bdate_range("2024-02-01", periods=40)
    panel = cal.build_calendar(sessions, pd.DataFrame({"date": [], "kind": []}), dates, [], "2024-03-01")
    flagged = set(panel.loc[panel.is_cpi, "date"].dt.strftime("%Y-%m-%d"))
    assert flagged == {"2024-02-13"}
    assert "2024-03-12" not in flagged
    assert "2024-03-20" not in flagged


def test_month_rules_and_no_price_input():
    sessions = pd.bdate_range("2024-01-02", periods=45)
    panel = cal.build_calendar(sessions, pd.DataFrame({"date": [], "kind": []}), [], [], "2024-02-15")
    january = panel[panel.date.dt.month == 1]
    assert bool(january.iloc[0].is_month_start)
    assert bool(january.iloc[-1].is_month_end)
    assert bool(january.iloc[2].is_turn_of_month)
    assert not bool(january.iloc[10].is_turn_of_month)
    assert panel.available_from.eq(panel.date).all()
    assert (panel.date <= "2024-02-15").all()


def test_later_fomc_does_not_change_an_earlier_flag():
    sessions = pd.bdate_range("2024-01-02", periods=80)
    early = pd.DataFrame({"date": [pd.Timestamp("2024-01-31")], "kind": ["meeting"]})
    later = pd.concat([early, pd.DataFrame({"date": [pd.Timestamp("2024-03-20")], "kind": ["meeting"]})])
    left = cal.build_calendar(sessions, early, [], [], "2024-04-01")
    right = cal.build_calendar(sessions, later, [], [], "2024-04-01")
    day = pd.Timestamp("2024-01-31")
    assert bool(left.set_index("date").loc[day, "is_fomc"])
    assert bool(right.set_index("date").loc[day, "is_fomc"])
    # The later meeting is public on the Fed calendar, so the forward count may see it.
    assert right.set_index("date").loc[day, "days_to_fomc"] == 0
    assert left.set_index("date").loc[pd.Timestamp("2024-02-01"), "days_to_fomc"] != right.set_index("date").loc[pd.Timestamp("2024-02-01"), "days_to_fomc"]


def test_bool_round_trip_keeps_a_blank_forward_count():
    import os
    import tempfile
    frame = pd.DataFrame({
        "date": pd.bdate_range("2024-01-02", periods=3),
        "is_fomc": [False, True, False],
        "days_to_cpi": [1, 0, np.nan],
    })
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "cal.parquet")
        meta = cal.write_lossless(frame, path)
        back = pd.read_parquet(path)
        assert meta["rows"] == 3
        assert list(back.is_fomc) == [False, True, False]
        assert np.isnan(back.days_to_cpi.iloc[2])


def test_candle_flags_copy_the_end_session_and_are_not_combined():
    sessions = pd.bdate_range("2024-01-02", periods=45)
    as_of = sessions[29]
    # Sessions 2 and 3 sit inside the first 5-session block. The block ends at session 4.
    fomc = pd.DataFrame({"date": [sessions[2], sessions[3]], "kind": ["meeting", "meeting"]})
    panel = cal.build_calendar(sessions, fomc, [], [], as_of)
    candles = cal.carry_onto_candles(panel, sessions, as_of)
    assert {"1d", "5d", "10d", "20d", "21d", "monthly"} <= set(candles.timeframe)
    assert not {"open", "high", "low", "close", "volume"} & set(candles.columns)
    daily = panel.set_index("date")
    one = candles[candles.timeframe == "1d"].set_index("date")
    assert one.index.isin(daily.index).all()
    assert one["is_fomc"].equals(daily.loc[one.index, "is_fomc"])
    assert one["days_to_opex"].equals(daily.loc[one.index, "days_to_opex"])
    assert (one.available_from > one.index).all()
    five = candles[candles.timeframe == "5d"].sort_values("date").iloc[0]
    assert pd.Timestamp(five.date) == sessions[4]
    assert bool(daily.loc[sessions[2], "is_fomc"])
    assert not bool(five.is_fomc)
    assert "not resampled prices" in cal.CANDLE_NOTE


def test_earlier_as_of_preserves_calendar_candles_already_available():
    sessions = pd.bdate_range("2024-01-02", periods=50)
    fomc = pd.DataFrame({"date": [sessions[10]], "kind": ["meeting"]})
    early_as_of = sessions[20]
    early = cal.carry_onto_candles(cal.build_calendar(sessions, fomc, [], [], early_as_of), sessions, early_as_of)
    later = cal.carry_onto_candles(cal.build_calendar(sessions, fomc, [], [], sessions[40]), sessions, sessions[40])
    keys = ["timeframe", "date"]
    kept = early[early.available_from <= early_as_of]
    merged = kept.merge(later, on=keys, suffixes=("", "_later"))
    assert len(merged) == len(kept)
    for column in ("is_fomc", "is_opex", "is_month_end", "days_since_opex", "days_to_opex"):
        assert merged[column].equals(merged[column + "_later"])


def test_days_to_fomc_counts_a_published_meeting_after_as_of():
    sessions = pd.bdate_range("2024-01-02", periods=80)
    fomc = pd.DataFrame({"date": [pd.Timestamp("2024-03-20")], "kind": ["meeting"]})
    panel = cal.build_calendar(sessions, fomc, [], [], "2024-01-31")
    row = panel.set_index("date").loc[pd.Timestamp("2024-01-31")]
    assert not bool(row.is_fomc)
    assert row.days_to_fomc > 0
    assert pd.isna(row.days_since_fomc)


def test_days_to_opex_counts_the_next_third_friday_after_as_of():
    sessions = pd.bdate_range("2024-01-02", periods=80)
    panel = cal.build_calendar(sessions, pd.DataFrame(columns=["date", "kind"]), [], [], "2024-01-31")
    row = panel.set_index("date").loc[pd.Timestamp("2024-01-31")]
    assert not bool(row.is_opex)
    assert row.days_to_opex > 0
    assert pd.Timestamp("2024-02-16") not in set(panel.date)


def test_monthly_candle_waits_for_the_next_session_when_the_first_is_closed():
    from world_timeframes import completed_candles
    sessions = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04"])
    bars = pd.DataFrame({
        "date": sessions[:2], "open": [1.0, 1.0], "high": [1.0, 1.0],
        "low": [1.0, 1.0], "close": [1.0, 1.0], "volume": [1.0, 1.0],
    })
    candles = completed_candles(bars, "monthly", sessions)
    assert candles.available_from.iloc[0] == pd.Timestamp("2020-02-03")
