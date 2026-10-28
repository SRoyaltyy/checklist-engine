"""The derived breadth formulas use only counts through the session."""

import numpy as np
import pandas as pd

import breadth_derived as derived


def _frame(rows):
    return pd.DataFrame(rows)


def test_trin_and_volume_line_match_a_hand_calculation():
    frame = _frame({
        "date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
        "available_from": pd.to_datetime(["2020-01-03", "2020-01-06"]),
        "advance": [2, 1],
        "decline": [1, 2],
        "up_volume": [10, 4],
        "down_volume": [5, 8],
    })
    out = derived.derive(frame)
    assert out.trin.tolist() == [1.0, 1.0]
    assert out.ad_volume_line.tolist() == [5.0, 1.0]


def test_zero_denominator_trin_is_infinite_or_blank():
    frame = _frame({
        "date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]),
        "available_from": pd.to_datetime(["2020-01-03", "2020-01-06", "2020-01-07"]),
        "advance": [2, 0, 0],
        "decline": [0, 0, 1],
        "up_volume": [3, 0, 4],
        "down_volume": [1, 0, 4],
    })
    out = derived.derive(frame)
    assert out.trin.iloc[0] == np.inf
    assert np.isnan(out.trin.iloc[1])
    assert out.trin.iloc[2] == 0.0


def test_mcclellan_uses_only_counts_through_today_and_withholds_tomorrow():
    dates = pd.bdate_range("2020-01-02", periods=4)
    available = list(dates[1:]) + [dates[-1] + pd.offsets.Day(1)]
    frame = _frame({
        "date": dates,
        "available_from": available,
        "advance": [3, 1, 4, 2],
        "decline": [1, 2, 1, 3],
        "up_volume": [8, 5, 9, 4],
        "down_volume": [2, 6, 1, 7],
    })
    full = derived.derive(frame)
    held = derived.derive(frame.iloc[:-1])
    pd.testing.assert_series_equal(
        held["mcclellan_oscillator"].reset_index(drop=True),
        full["mcclellan_oscillator"].iloc[:-1].reset_index(drop=True),
    )
    pd.testing.assert_series_equal(
        held["mcclellan_summation"].reset_index(drop=True),
        full["mcclellan_summation"].iloc[:-1].reset_index(drop=True),
    )
    net = pd.Series([2.0, -1.0])
    fast = net.ewm(span=19, adjust=False).mean()
    slow = net.ewm(span=39, adjust=False).mean()
    assert full.mcclellan_oscillator.iloc[1] == (fast - slow).iloc[1]
    assert full.mcclellan_summation.iloc[1] == (fast - slow).cumsum().iloc[1]


def test_bullish_percent_is_excluded_because_the_box_is_not_registered():
    assert derived.EXCLUDED["bullish_percent"] == "POINT_AND_FIGURE_BOX_AND_REVERSAL_NOT_REGISTERED"


def _six_sessions():
    dates = pd.bdate_range("2020-01-02", periods=6)
    available = list(dates[1:]) + [dates[-1] + pd.offsets.BDay(1)]
    return _frame({
        "date": dates,
        "available_from": available,
        "advance": [2, 1, 4, 1, 3, 2],
        "decline": [1, 1, 1, 2, 1, 2],
        "up_volume": [10, 1, 8, 2, 6, 4],
        "down_volume": [5, 3, 2, 4, 3, 5],
    }), dates


def test_candle_trin_uses_the_summed_counts():
    frame, dates = _six_sessions()
    candles = derived.derive_candles(frame, dates)
    two = candles[candles.timeframe == "2d"].reset_index(drop=True)
    assert len(two) == 2
    assert two.loc[0, "date"] == dates[1]
    assert two.loc[0, "available_from"] == dates[2]
    # (3/2) / (11/8) = 12/11, not the second session's own TRIN of 3.
    assert two.loc[0, "trin"] == np.float64(12) / 11
    assert two.loc[0, "ad_volume_line"] == 3.0
    daily = derived.derive(frame)
    assert two.loc[0, "mcclellan_oscillator"] == daily.mcclellan_oscillator.iloc[1]
    assert two.loc[0, "mcclellan_summation"] == daily.mcclellan_summation.iloc[1]


def test_a_bucket_with_no_later_session_is_omitted():
    frame, dates = _six_sessions()
    candles = derived.derive_candles(frame, dates)
    one = candles[candles.timeframe == "1d"]
    assert len(one) == 5
    assert one.date.max() == dates[-2]
    held = derived.derive_candles(frame.iloc[:-2], dates[:-2])
    left = candles[candles.timeframe == "2d"].iloc[:1]
    right = held[held.timeframe == "2d"]
    assert len(right) == 1
    assert left.trin.iloc[0] == right.trin.iloc[0]
    assert left.mcclellan_summation.iloc[0] == right.mcclellan_summation.iloc[0]


def test_an_unfinished_month_is_omitted():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-31", "2020-02-03"])
    available = pd.to_datetime(["2020-01-03", "2020-01-06", "2020-02-03", "2020-02-04"])
    frame = _frame({
        "date": dates,
        "available_from": available,
        "advance": [2, 1, 3, 1],
        "decline": [1, 1, 1, 1],
        "up_volume": [4, 2, 6, 1],
        "down_volume": [1, 2, 3, 1],
    })
    candles = derived.derive_candles(frame, dates)
    month = candles[candles.timeframe == "monthly"]
    assert list(month.date) == [pd.Timestamp("2020-01-31")]
    assert list(month.available_from) == [pd.Timestamp("2020-02-03")]
    assert month.trin.iloc[0] == np.float64((2 + 1 + 3) * (1 + 2 + 3)) / ((1 + 1 + 1) * (4 + 2 + 6))
