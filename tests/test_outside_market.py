import json

import numpy as np
import pandas as pd
import pytest

import outside_market as market


def sessions(days):
    return pd.DatetimeIndex(pd.to_datetime(days))


def bars(days, close, ticker="SPY"):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame({
        "ticker": ticker,
        "date": pd.to_datetime(days),
        "open": close,
        "high": close + 0.01,
        "low": close - 0.01,
        "close": close,
        "volume": np.full(len(close), 1000.0),
    })


def chart(stamps, closes):
    closes = list(closes)
    return {"chart": {"result": [{
        "timestamp": list(stamps),
        "indicators": {
            "quote": [{
                "open": closes, "high": [c + 1 for c in closes], "low": [c - 1 for c in closes],
                "close": closes, "volume": [100] * len(closes),
            }],
            "adjclose": [{"adjclose": [c * 0.5 for c in closes]}],
        },
    }]}}


def stamp(day):
    return int(pd.Timestamp(day).tz_localize("America/New_York").replace(hour=9, minute=30).timestamp())


def test_named_universe_matches_the_order():
    assert market.NAMED_ETFS == (
        "SPY", "QQQ", "IWM", "DIA", "RSP",
        "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
        "TLT", "HYG", "LQD", "UUP", "GLD", "CPER", "USO", "VXX", "IBIT",
    )
    assert len(market.INDUSTRY_ETFS) == 18
    assert len({ticker for ticker, _name in market.INDUSTRY_ETFS}) == 18


def test_latest_session_is_the_last_close_already_printed():
    class Calendar:
        def sessions_in_range(self, start, end):
            return pd.bdate_range(start, end)

        def session_close(self, session):
            return pd.Timestamp(session).tz_localize("America/New_York").replace(hour=16).tz_convert("UTC")

    # 2026-10-28 00:06 ET is after the 27th close and before the 28th close.
    now = pd.Timestamp("2026-10-28 04:06", tz="UTC")
    assert market.latest_completed_session(now, Calendar()) == pd.Timestamp("2026-10-27")


def test_yahoo_adjustment_and_new_york_session():
    frame = market.parse_yahoo_chart(chart([stamp("2024-01-02")], [20.0]), "SPY")
    assert frame.date.iloc[0] == pd.Timestamp("2024-01-02")
    assert frame.close.iloc[0] == 10.0
    assert frame.vendor_close.iloc[0] == 20.0
    assert frame.volume.iloc[0] == 100


def test_future_session_is_dropped():
    days = ["2024-01-02", "2024-01-03", "2024-01-04"]
    cal = sessions(days)
    fetched = market.parse_yahoo_chart(chart([stamp(day) for day in days], [10, 11, 12]), "XBI")
    frame, dropped = market.vendor_panel(fetched, cal, "2024-01-03", "YAHOO_CHART_V8")
    assert dropped["future_rows_dropped"] == 1
    assert list(frame.date.dt.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]
    assert frame.available_from.iloc[0] == pd.Timestamp("2024-01-03")
    # The next session is still the availability date. Its bar is not stored.
    assert frame.available_from.iloc[1] == pd.Timestamp("2024-01-04")
    assert "2024-01-04" not in set(frame.date.dt.strftime("%Y-%m-%d"))
    market.assert_no_lookahead(frame, "2024-01-03")


def test_extension_keeps_released_rows_and_links_the_level():
    days = pd.bdate_range("2024-01-02", periods=12)
    prior = bars(days[:8], np.arange(8) + 10)
    # Same returns at twice the level, then four new sessions.
    tail_close = (np.arange(10) + 12) * 2
    tail = bars(days[2:], tail_close)
    tail["vendor_close"] = tail["close"]
    for column in ("vendor_open", "vendor_high", "vendor_low"):
        tail[column] = tail["close"]
    tail["vendor_volume"] = tail["volume"]
    out, note = market.extend_released(prior, tail, days, days[-1])
    assert note["tail_status"] == "APPENDED"
    assert note["rows_appended"] == 4
    kept = out[out.date.isin(prior.date)].sort_values("date")
    assert np.array_equal(kept.close.to_numpy(), prior.close.to_numpy())
    # New close continues the released level, not the vendor's double level.
    fresh = out[out.date > prior.date.max()]
    assert fresh.source.eq("YAHOO_TAIL_LEVEL_LINKED").all()
    assert fresh.close.iloc[0] == pytest.approx(prior.close.iloc[-1] + 1)
    assert fresh.vendor_close.iloc[0] == pytest.approx((prior.close.iloc[-1] + 1) * 2)


def test_return_mismatch_does_not_append():
    days = pd.bdate_range("2024-01-02", periods=10)
    prior = bars(days[:8], np.arange(8) + 10.0)
    tail = bars(days[2:], np.array([10, 50, 10, 50, 10, 50, 10, 50], dtype=float))
    for column in market.VENDOR:
        tail[column] = 1.0
    out, note = market.extend_released(prior, tail, days, days[-1])
    assert note["tail_status"] == "OVERLAP_RETURN_MISMATCH"
    assert len(out) == len(prior)
    assert np.array_equal(out.close.to_numpy(), prior.close.to_numpy())


def test_coverage_keeps_ninety_five_and_logs_the_rest():
    days = pd.bdate_range("2020-01-02", periods=100)
    keep = [i for i in range(10, 100) if i not in (20, 21, 22, 23, 24, 25)]
    bad = bars(days[keep], np.arange(len(keep)) + 1, ticker="XBI")
    good_row = market.coverage_row(bars(days, np.arange(100)), days, days[-1], "SPY")
    assert good_row["status"] == "PASS" and good_row["coverage_percent"] == 100
    five = bars(days.delete([10, 11, 12, 13, 14]), np.arange(95))
    five_row = market.coverage_row(five, days, days[-1], "QQQ")
    assert five_row["status"] == "PASS" and five_row["missing_sessions"] == 5
    six = market.coverage_row(bad, days, days[-1], "XBI")
    assert six["status"] == "EXCLUDED" and six["reason"] == "COVERAGE_BELOW_95"
    assert six["missing_sessions"] == 6


def test_ibit_style_late_listing_is_not_a_hole():
    days = pd.bdate_range("2020-01-02", periods=40)
    late = bars(days[25:], np.arange(15) + 1, ticker="IBIT")
    row = market.coverage_row(late, days, days[-1], "IBIT")
    assert row["status"] == "PASS"
    assert row["expected_sessions"] == 15
    assert row["missing_sessions"] == 0
    assert row["full_window_sessions"] == 40
    assert row["full_window_percent"] == 37.5
    assert row["window_gap_reason"] == "LISTED_AFTER_WINDOW_START"


def test_cent_prices_round_trip_and_subcent_prices_stay_float(tmp_path):
    days = pd.bdate_range("2024-01-02", periods=4)
    noisy = bars(days, [26.629999, 27.940001, 24.969999, 26.4])
    noisy["family"] = "index"
    noisy["source"] = "RELEASED_ETF_NATIVE"
    noisy["available_from"] = noisy["date"] + pd.offsets.Day(1)
    for column in market.VENDOR:
        noisy[column] = np.nan
    file = tmp_path / "panel.parquet"
    meta = market.write_lossless(noisy, file)
    assert meta["price_storage"] == "float64_byte_stream_split"
    back = market.read_lossless(file, meta["price_storage"])
    assert back.close.to_numpy().tobytes() == noisy.close.to_numpy().tobytes()
    eighth = noisy.copy()
    eighth["close"] = [10.125, 10.125, 10.125, 10.125]
    meta2 = market.write_lossless(eighth, tmp_path / "float.parquet")
    assert meta2["price_storage"] == "float64_byte_stream_split"
    back2 = market.read_lossless(tmp_path / "float.parquet", meta2["price_storage"])
    assert back2.close.iloc[0] == 10.125

def test_monthly_candle_waits_for_the_next_session_when_the_first_is_closed():
    sessions = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04"])
    frame = bars(sessions[:2], np.array([10.0, 11.0]))
    frame["volume"] = 1
    candles = market.build_candles(frame, sessions, sessions[1])
    monthly = candles[candles.timeframe == "monthly"]
    assert len(monthly) == 1
    assert monthly.available_from.iloc[0] == pd.Timestamp("2020-02-03")


def test_candles_do_not_change_when_the_future_is_removed():
    days = pd.bdate_range("2024-01-02", periods=30)
    full = bars(days, np.arange(30) + 50.0)
    full["volume"] = 10
    early = full[full.date <= days[14]].copy()
    boundary = days
    cut = days[14]
    early_candles = market.build_candles(early, boundary, cut)
    full_candles = market.build_candles(full, boundary, days[-1])
    visible = full_candles[full_candles.available_from.notna() & (full_candles.available_from <= days[15])]
    # Compare the candles both builds could already see by the session after the cut.
    left = early_candles[early_candles.available_from.notna() & (early_candles.available_from <= days[15])]
    keys = ["timeframe", "date"]
    merged = left.merge(visible, on=keys, suffixes=("_early", "_full"))
    assert len(merged) == len(left) == len(visible)
    assert np.allclose(merged.close_early, merged.close_full)


def test_panel_gate_rejects_a_named_miss_and_accepts_an_industry_miss():
    def row(ticker, status):
        return dict(ticker=ticker, status=status)
    named = [row(ticker, "PASS") for ticker in market.NAMED_ETFS]
    industry = [row(ticker, "PASS") for ticker, _name in market.INDUSTRY_ETFS]
    industry[0]["status"] = "EXCLUDED"
    summary = market.panel_passes(named + industry)
    assert summary["passed"] == len(named) + len(market.INDUSTRY_ETFS) - 1
    broken = named.copy()
    broken[0] = row("SPY", "EXCLUDED")
    with pytest.raises(ValueError, match="named series"):
        market.panel_passes(broken + industry)


def test_prior_catalog_requires_every_named_etf():
    document = {"release": market.PRIOR_RELEASE, "records": [
        {"ticker": ticker, "file": "etf_daily_" + ticker + ".parquet", "sha256": "abc", "rows": 1, "last": "2026-10-23"}
        for ticker in market.NAMED_ETFS
    ]}
    assert market.prior_records(document)["SPY"]["file"] == "etf_daily_SPY.parquet"
    document["records"] = document["records"][1:]
    with pytest.raises(ValueError, match="SPY"):
        market.prior_records(document)
