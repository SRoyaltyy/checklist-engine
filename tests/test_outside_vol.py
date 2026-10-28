import numpy as np
import pandas as pd
import pytest

import outside_vol as vol


def days(start, count):
    return pd.bdate_range(start, periods=count)


def test_later_vintage_does_not_rewrite_the_close_known_that_day():
    vintages = pd.DataFrame({
        "obs_date": ["2020-01-02", "2020-01-02", "2020-01-03"],
        "vintage_date": ["2020-01-02", "2020-01-10", "2020-01-06"],
        "value": [12.5, 99.0, 13.0],
    })
    out = vol.vix_close_known_by_session(vintages)
    assert out.set_index("date").loc[pd.Timestamp("2020-01-02"), "vix"] == 12.5
    assert "2020-01-03" not in set(out.date.dt.strftime("%Y-%m-%d"))


def test_divide_uses_the_zero_denominator_rule():
    out = vol.divide([1.0, 0.0, -2.0, np.nan, 4.0], [2.0, 0.0, 0.0, 0.0, 0.0])
    assert out[0] == 0.5
    assert np.isnan(out[1])
    assert out[2] == -np.inf
    assert np.isnan(out[3])
    assert out[4] == np.inf


def test_ratio_on_day_d_ignores_a_later_close():
    calendar = days("2024-01-02", 6)
    levels = {
        "VIX": pd.DataFrame({"date": calendar[:4], "close": [10, 10, 10, 50]}),
        "VIX9D": pd.DataFrame({"date": calendar[:4], "close": [12, 12, 12, 12]}),
        "VIX3M": pd.DataFrame({"date": calendar[:4], "close": [20, 20, 20, 20]}),
        "VVIX": pd.DataFrame({"date": calendar[:4], "close": [80, 80, 80, 80]}),
    }
    early = vol.build_daily({name: frame[frame.date <= calendar[1]] for name, frame in levels.items()}, calendar, calendar[1])
    full = vol.build_daily(levels, calendar, calendar[3])
    row = early.set_index("date").loc[calendar[1]]
    later = full.set_index("date").loc[calendar[1]]
    assert row["vix_over_vix3m"] == later["vix_over_vix3m"] == 0.5
    assert row["available_from"] == calendar[2]
    assert calendar[3] not in set(early.date)


def test_tail_keeps_released_closes_and_rejects_a_mismatch():
    calendar = days("2024-01-02", 8)
    prior = pd.DataFrame({
        "date": calendar[:5],
        "open": [1, 2, 3, 4, 5],
        "high": [1, 2, 3, 4, 5],
        "low": [1, 2, 3, 4, 5],
        "close": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
    fresh = prior.copy()
    fresh = pd.concat([fresh, pd.DataFrame({
        "date": calendar[5:],
        "open": [6, 7, 8], "high": [6, 7, 8], "low": [6, 7, 8], "close": [6.0, 7.0, 8.0],
    })], ignore_index=True)
    out, note = vol.append_verified_tail(prior, fresh, calendar[-1])
    assert note["tail_status"] == "APPENDED" and note["rows_appended"] == 3
    assert np.array_equal(out.close.iloc[:5].to_numpy(), prior.close.to_numpy())
    bad = fresh.copy()
    bad.loc[0, "close"] = 50
    kept, refused = vol.append_verified_tail(prior, bad, calendar[-1])
    assert refused["tail_status"] == "OVERLAP_CLOSE_MISMATCH"
    assert len(kept) == len(prior)


def test_future_cboe_row_is_not_stored():
    text = "DATE,OPEN,HIGH,LOW,CLOSE\n01/02/2024,1,1,1,1\n01/03/2024,2,2,2,2\n01/04/2024,3,3,3,3\n"
    frame = vol.parse_cboe_csv(text, "VIX9D")
    kept, note = vol.append_verified_tail(frame.iloc[:2], frame, "2024-01-03")
    assert list(kept.date.dt.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]
    assert note["rows_appended"] == 0 or note["tail_status"] == "NO_NEW_SESSIONS"


def test_coverage_logs_a_short_series_and_accepts_ninety_five():
    calendar = days("2020-01-02", 100)
    # One extra session so the last close has a next session.
    sessions = days("2020-01-02", 101)
    def level(values):
        return pd.DataFrame({"date": calendar[:len(values)], "close": values})
    good = {name: level(np.arange(100) + 1.0) for name in vol.LEVELS}
    panel = vol.build_daily(good, sessions, calendar[-1])
    rows = vol.coverage_table(panel, sessions, calendar[-1])
    summary = vol.assert_panel_coverage(rows)
    assert summary["series_passed"] == len(rows)
    short_vix = level(np.arange(90) + 1.0)
    bad_levels = dict(good)
    bad_levels["VIX"] = short_vix
    bad = vol.build_daily(bad_levels, sessions, calendar[-1])
    bad_rows = vol.coverage_table(bad, sessions, calendar[-1])
    vix = next(row for row in bad_rows if row["series"] == "vix")
    assert vix["status"] == "EXCLUDED" and vix["reason"] == "COVERAGE_BELOW_95"
    with pytest.raises(ValueError, match="vix"):
        vol.assert_panel_coverage(bad_rows)


def test_candle_ratio_does_not_use_a_later_bucket():
    calendar = days("2024-01-02", 12)
    closes = np.arange(10) + 10.0
    def frame(scale):
        return pd.DataFrame({
            "date": calendar[:10],
            "open": closes * scale, "high": closes * scale,
            "low": closes * scale, "close": closes * scale,
        })
    levels = {"VIX": frame(1), "VIX9D": frame(1.2), "VIX3M": frame(2), "VVIX": frame(8)}
    early_levels = {name: frame[frame.date <= calendar[4]] for name, frame in levels.items()}
    early = vol.ratio_candles(vol.level_candles(early_levels, calendar, calendar[4]))
    full = vol.ratio_candles(vol.level_candles(levels, calendar, calendar[9]))
    early = early[early.available_from.notna() & (early.available_from <= calendar[5])]
    full = full[full.available_from.notna() & (full.available_from <= calendar[5])]
    merged = early.merge(full, on=["series", "timeframe", "date"], suffixes=("_early", "_full"))
    assert len(merged) == len(early) == len(full) > 0
    assert np.allclose(merged.close_early, merged.close_full, equal_nan=True)


def test_float_panel_round_trips_infinity(tmp_path):
    frame = pd.DataFrame({
        "date": days("2024-01-02", 2),
        "vix_over_vix3m": [0.5, np.inf],
    })
    path = tmp_path / "vol.parquet"
    meta = vol.write_lossless(frame, path, dictionary_columns=())
    back = pd.read_parquet(path)
    assert meta["rows"] == 2
    assert back.vix_over_vix3m.iloc[1] == np.inf


def test_monthly_level_waits_for_the_next_session_when_the_first_is_closed():
    from outside_market import completed_market_candles
    sessions = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04"])
    bars = pd.DataFrame({
        "date": sessions[:2], "open": [10.0, 11.0], "high": [10.0, 11.0],
        "low": [10.0, 11.0], "close": [10.0, 11.0], "volume": [1.0, 1.0],
    })
    candles = completed_market_candles(bars, "monthly", sessions)
    assert candles.available_from.iloc[0] == pd.Timestamp("2020-02-03")
