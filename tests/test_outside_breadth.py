import numpy as np
import pandas as pd
import pytest

import outside_breadth as breadth


def bars(closes, highs=None, lows=None, volumes=None, start="2020-01-02"):
    closes = np.asarray(closes, dtype=float)
    dates = pd.bdate_range(start, periods=len(closes))
    if highs is None:
        highs = closes + 0.5
    if lows is None:
        lows = closes - 0.5
    if volumes is None:
        volumes = np.full(len(closes), 100.0)
    return pd.DataFrame({
        "date": dates, "open": closes, "high": highs, "low": lows, "close": closes, "volume": volumes,
    })


def test_moving_average_uses_only_bars_through_today():
    closes = list(range(1, 21)) + [100]
    frame = bars(closes)
    early = breadth.stock_contributions(frame.iloc[:20])
    full = breadth.stock_contributions(frame)
    day = frame.date.iloc[19]
    assert int(early.set_index("date").loc[day, "eligible_sma20"]) == 1
    assert int(early.set_index("date").loc[day, "above_sma20"]) == int(full.set_index("date").loc[day, "above_sma20"]) == 1


def test_sma20_hand_value():
    closes = list(range(1, 21)) + [30]
    frame = bars(closes)
    out = breadth.stock_contributions(frame)
    # First eligible row is the 20th close, mean of 1..20 = 10.5, close 20 is above.
    row = out.iloc[19]
    assert row.eligible_sma20 == 1 and row.above_sma20 == 1
    assert out.iloc[18].eligible_sma20 == 0


def test_new_high_ignores_the_current_bar_and_the_future():
    # 252 flat highs, then a higher one, then a much higher future bar.
    highs = [10.0] * 251 + [11.0, 50.0]
    closes = highs
    frame = bars(closes, highs=highs, lows=[9.0] * len(highs))
    out = breadth.stock_contributions(frame)
    assert out.eligible_52w.iloc[250] == 0
    assert out.new_high.iloc[251] == 1
    assert out.new_high.iloc[250] == 0
    early = breadth.stock_contributions(frame.iloc[:-1])
    assert int(early.new_high.iloc[251]) == 1


def test_advance_decline_line_stops_at_the_session():
    one = bars([10, 11, 10], start="2024-01-02")
    two = bars([10, 9, 12], start="2024-01-02")
    votes = pd.concat([
        breadth.stock_contributions(one),
        breadth.stock_contributions(two),
    ], ignore_index=True)
    sessions = pd.bdate_range("2024-01-02", periods=5)
    early = breadth.aggregate(votes[votes.date <= sessions[1]], sessions, sessions[1])
    full = breadth.aggregate(votes, sessions, sessions[2])
    assert int(early.set_index("date").loc[sessions[1], "ad_line"]) == int(full.set_index("date").loc[sessions[1], "ad_line"])
    # Day 2: stock one up, stock two down. Net zero. Line stays at day-1 value.
    assert int(full.set_index("date").loc[sessions[1], "advance"]) == 1
    assert int(full.set_index("date").loc[sessions[1], "decline"]) == 1
    assert full.set_index("date").loc[sessions[1], "available_from"] == sessions[2]


def test_percent_is_blank_when_nobody_is_eligible_and_zero_denominator_is_infinite():
    frame = bars([1, 2, 3])
    votes = breadth.stock_contributions(frame)
    sessions = pd.bdate_range(frame.date.iloc[0], periods=4)
    panel = breadth.aggregate(votes, sessions, frame.date.iloc[-1])
    first = panel.iloc[0]
    assert first.eligible_sma20 == 0
    assert np.isnan(first.pct_above_sma20)
    # No declines and one advance later makes the ratio infinite.
    later = panel.set_index("date").loc[frame.date.iloc[1]]
    assert later.advance == 1 and later.decline == 0
    assert later.ad_ratio == np.inf


def test_breadth_candle_uses_only_a_completed_bucket():
    sessions = pd.bdate_range("2024-01-02", periods=12)
    panel = pd.DataFrame({
        "date": sessions[:10],
        "advance": 1, "decline": 0, "unchanged": 0, "new_high": 1, "new_low": 0,
        "ad_net": 1, "up_volume": 5.0, "down_volume": 0.0,
        "pct_above_sma20": 0.5, "pct_above_sma50": 0.4, "pct_above_sma200": 0.3,
        "ad_line": range(10), "ad_ratio": 1.0, "up_down_volume_ratio": np.inf,
        "new_highs_minus_new_lows": 1,
    })
    candles = breadth.breadth_candles(panel, sessions)
    five = candles[candles.timeframe == "5d"]
    # First bucket is sessions 0-4. The second starts at 5 and ends at 9. Both are complete.
    assert list(five.date) == [sessions[4], sessions[9]]
    assert int(five.advance.iloc[0]) == 5
    assert int(five.ad_line.iloc[0]) == 4


def test_name_gate_and_round_trip():
    summary = dict(status="PASS")
    assert breadth.assert_breadth(summary, 96, 100)["names_percent"] == 96
    with pytest.raises(ValueError, match="95"):
        breadth.assert_breadth(summary, 94, 100)
    import os
    import tempfile
    sessions = pd.bdate_range("2024-01-02", periods=3)
    panel = breadth.aggregate(pd.DataFrame(), sessions, sessions[1])
    # No votes: counts are zero and percents are blank.
    assert panel.eligible_sma20.sum() == 0
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "breadth.parquet")
        # Give the blank percents a finite value so the writer sees a float column.
        panel["pct_above_sma20"] = [np.nan, 0.5]
        panel["pct_above_sma50"] = panel["pct_above_sma20"]
        panel["pct_above_sma200"] = panel["pct_above_sma20"]
        panel["ad_ratio"] = [np.nan, np.inf]
        panel["up_down_volume_ratio"] = panel["ad_ratio"]
        meta = breadth.write_lossless(panel, path)
        back = pd.read_parquet(path)
        assert meta["rows"] == len(panel)
        assert back.ad_ratio.iloc[1] == np.inf
