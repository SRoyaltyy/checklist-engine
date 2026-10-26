import hashlib,io,tarfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ci.native_price_blocks import measure_availability,read_member,source_part,flush_part,FROZEN_HASHES

def test_native_counts_equal_an_explicit_daily_asof_join():
    features=pd.DataFrame({"available_from":pd.to_datetime(["2020-01-02","2020-01-05","2020-01-08"]),
        "x":[np.nan,2.,3.],"ratio_inf":[np.inf,np.nan,-np.inf],"math_value":[np.inf,5.,9.]})
    dates=pd.to_datetime(["2020-01-01","2020-01-02","2020-01-03","2020-01-05","2020-01-07","2020-01-08"])
    rows={r["column"]:r for r in measure_availability(features,dates)}
    expected=pd.merge_asof(pd.DataFrame({"date":dates}),features,left_on="date",right_on="available_from")
    for name,row in rows.items():
        values=expected[name].to_numpy()
        valid=np.isfinite(values)|(np.isinf(values) if name.endswith("_inf") else False)
        assert row["query_rows"]==len(dates)
        assert row["non_null_rows"]==valid.sum()
        assert row["first_date"]==str(dates[valid][0])[:10]
        assert row["last_date"]==str(dates[valid][-1])[:10]
    assert rows["x"]["non_null_rows"]==3
    assert rows["ratio_inf"]["non_null_rows"]==3
    assert rows["math_value"]["non_null_rows"]==3

def test_no_candle_is_exposed_before_its_availability():
    f=pd.DataFrame({"available_from":pd.to_datetime(["2020-02-01"]),"close":[100.]})
    row=measure_availability(f,pd.to_datetime(["2020-01-30","2020-01-31"]))[0]
    assert row["non_null_rows"]==0
    assert row["first_date"]==row["last_date"]==""

def test_price_part_locator_keeps_the_original_source_partition():
    assert source_part(0)=="prices_shard_000_attempt_1_part_000"
    assert source_part(15)=="prices_shard_015_attempt_1_part_000"
    assert source_part(800)=="prices_shard_000_attempt_1_part_001"
    assert source_part(815)=="prices_shard_015_attempt_1_part_001"

def test_source_members_are_verified_before_parquet_parsing(tmp_path):
    name="54455354.parquet";raw=b"verified source bytes";archive=tmp_path/"source.tar"
    with tarfile.open(archive,"w") as tar:
        info=tarfile.TarInfo(name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
    manifest={"members":[{"name":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}]}
    assert read_member(archive,manifest,name)==raw
    manifest["members"][0]["sha256"]="0"*64
    with pytest.raises(ValueError,match="fingerprint"):read_member(archive,manifest,name)

def test_empty_parts_cannot_be_published(tmp_path,monkeypatch):
    (tmp_path/"current").mkdir()
    monkeypatch.setattr("ci.native_price_blocks.gh",lambda *a:pytest.fail("empty part was published"))
    with pytest.raises(ValueError,match="empty part"):flush_part(tmp_path,"unused",0,[],{}, {},[])

def test_frozen_hashes_are_complete_sha256_values():
    assert all(len(value)==64 and set(value)<=set("0123456789abcdef") for value in FROZEN_HASHES.values())


def test_measurement_rejects_unordered_or_duplicate_dates():
    features=pd.DataFrame({"available_from":pd.to_datetime(["2020-01-03","2020-01-02"]),"x":[1.,2.]})
    with pytest.raises(ValueError,match="availability"):measure_availability(features,pd.to_datetime(["2020-01-04"]))
    features=features.sort_values("available_from")
    with pytest.raises(ValueError,match="query dates"):measure_availability(features,pd.to_datetime(["2020-01-04","2020-01-04"]))


def complete_shard():
    from ci.native_price_blocks import TIMEFRAMES
    inputs={"records":[{"ticker":"NA","feature_shard":0},{"ticker":"AAPL","feature_shard":0}],
            "inputs_tag":"immutable-inputs","is_smoke":True,"recipe_fingerprint":"recipe"}
    records=[{"ticker":name,"native":{tf:{"native_rows":2,"feature_columns":3} for tf in TIMEFRAMES}}
             for name in ("NA","AAPL")]
    summary={"records":records,"completed":2,"selected":2,"recipe_fingerprint":"recipe",
             "inputs_tag":"immutable-inputs","is_smoke":True,"timeframes":list(TIMEFRAMES),
             "parts":[{"tickers":["NA","AAPL"]}]}
    return summary,inputs


def test_complete_shard_preserves_literal_na_ticker():
    from ci.native_price_blocks import validate_shard
    summary,inputs=complete_shard()
    assert {r["ticker"] for r in validate_shard(summary,inputs,0)}=={"NA","AAPL"}


@pytest.mark.parametrize("damage",["missing_entity","duplicate_entity","missing_timeframe","missing_part","changed_recipe","changed_inputs"])
def test_coverage_merge_rejects_incomplete_or_mixed_builds(damage):
    from ci.native_price_blocks import validate_shard
    summary,inputs=complete_shard()
    if damage=="missing_entity":summary["records"].pop()
    elif damage=="duplicate_entity":summary["records"].append(summary["records"][0])
    elif damage=="missing_timeframe":del summary["records"][0]["native"]["5d"]
    elif damage=="missing_part":summary["parts"]=[{"tickers":["NA"]}]
    elif damage=="changed_recipe":summary["recipe_fingerprint"]="other"
    elif damage=="changed_inputs":summary["inputs_tag"]="other"
    with pytest.raises(ValueError):validate_shard(summary,inputs,0)


def test_exchange_calendar_keeps_real_session_missing_from_vix():
    xcals=pytest.importorskip("exchange_calendars")
    from ci.native_price_blocks import market_session_calendar,CUTOFF
    expected=xcals.get_calendar("XNYS",start="1990-01-01",end=CUTOFF).sessions.tz_localize(None).as_unit("ns")
    spy=expected[expected>=pd.Timestamp("1993-01-29")]
    vix=expected.difference(pd.DatetimeIndex(["1991-03-01"]))
    sessions,receipt=market_session_calendar(spy,vix)
    assert pd.Timestamp("1991-03-01") in sessions
    for day in ("2001-09-11","2001-09-12","2012-10-29","2012-10-30","2025-01-09"):
        assert pd.Timestamp(day) not in sessions
    assert receipt["vix_missing_sessions"]==["1991-03-01"]
    assert receipt["price_rows_modified"] is False
    assert receipt["vix_values_imputed"] is False
    with pytest.raises(ValueError,match="SPY/calendar validation"):
        market_session_calendar(spy.difference(pd.DatetimeIndex(["2020-06-10"])),vix)
