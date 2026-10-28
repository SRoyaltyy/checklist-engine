"""Recompute the monthly volatility snap from the public term file."""

import io
import urllib.request

import pandas as pd

import cursor_session_factors as factors

VOL_RELEASE = "volatility-term-native-v1-40667837889-1"
SPY_RELEASE = "light-daily-box-v1-20261028"
EXPECTED_MEAN = 0.8352165304365041


def download(tag, name):
    url = "https://github.com/SRoyaltyy/checklist-engine/releases/download/%s/%s" % (tag, name)
    request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def main():
    monthly = pd.read_parquet(io.BytesIO(download(VOL_RELEASE, "volatility_term_monthly.parquet")))
    spy = pd.read_parquet(io.BytesIO(download(SPY_RELEASE, "SPY.parquet")), columns=["date"])
    native = factors.volatility_native(monthly, pd.to_datetime(spy["date"]))
    if native.attrs["availability_dropped"] != 0 or len(native) != 441:
        raise ValueError("monthly snap dropped rows: kept %s dropped %s" % (
            len(native), native.attrs["availability_dropped"]))
    ends = pd.to_datetime(native.source_candle_end).dt.strftime("%Y-%m-%d")
    november = native.loc[ends == "2019-11-29"]
    if len(november) != 1 or str(pd.Timestamp(november.available_from.iloc[0]).date()) != "2019-12-02":
        raise ValueError("November 2019 is not available on 2019-12-02")
    picked = native.loc[ends.isin(["2019-10-31", "2019-11-29", "2019-12-31"]), "vol_vix_over_vix3m"]
    mean = float(picked.mean())
    if abs(mean - EXPECTED_MEAN) > 1e-12:
        raise ValueError("three-bar mean is %s" % mean)
    print("VOLATILITY_MONTHLY_SNAP_MATCH", len(native), native.attrs["availability_moved"], mean)


if __name__ == "__main__":
    main()
