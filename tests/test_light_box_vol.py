import hashlib
import json

import pandas as pd

import light_box_vol as vol


def write_symbol(directory, symbol, dates, closes):
    frame = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": closes, "high": closes, "low": closes, "close": closes,
        "adj_close": closes, "volume": [0] * len(closes),
    })
    path = directory / (symbol + ".parquet")
    frame.to_parquet(path, index=False)
    return dict(symbol=symbol, file=path.name, rows=len(frame), first=dates[0], last=dates[-1],
                expected_days=len(frame), missing_days=0, missing_sample=[], coverage=1.0,
                status="PASS", reason="", sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_ratio_uses_the_same_session_and_skips_a_non_spy_print(tmp_path):
    spy = ["2024-01-02", "2024-01-03", "2024-01-04"]
    rows = [write_symbol(tmp_path, "SPY", spy, [10, 11, 12])]
    for symbol, level in (("^VIX", [10, 20, 10]), ("^VIX9D", [12, 12, 12]), ("^VIX3M", [20, 20, 20]), ("^VVIX", [80, 80, 80])):
        rows.append(write_symbol(tmp_path, symbol, spy, level))
    # A holiday print that is not a SPY session must not create a stock-session row.
    extra = write_symbol(tmp_path, "^VIX", spy + ["2024-01-05"], [10, 20, 10, 99])
    rows = [row for row in rows if row["symbol"] != "^VIX"] + [extra]
    (tmp_path / "manifest.json").write_text(json.dumps({"window_start": "2020-01-02", "source": "test", "symbols": rows}))
    panel, _, off = vol.build_panel(tmp_path, as_of="2024-01-03")
    assert list(panel.date.dt.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]
    assert panel.vix_over_vix3m.tolist() == [0.5, 1.0]
    assert off["^VIX"] == ["2024-01-05"]
    assert panel.available_from.iloc[0] == pd.Timestamp("2024-01-03")
