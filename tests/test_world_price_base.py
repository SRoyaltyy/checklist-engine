import numpy as np
import pandas as pd
import json
import subprocess
import pytest
from ci import native_price_base as base
from ci.native_price_base import execution_rows,native_rows
from world_timeframes import TIMEFRAMES,PRICE_COLS

def source_bars():
    dates=pd.bdate_range("2019-01-02",periods=400);close=50+np.arange(len(dates))*.1
    return pd.DataFrame({"ticker":"NA","date":dates,"open":close-1,"high":close+2,"low":close-3,"close":close,"volume":1000+np.arange(len(dates))})

def test_execution_open_is_separate_and_keeps_literal_na_identity():
    bars=source_bars();result=execution_rows(bars)
    assert set(result)=={"ticker","date","execution_open_reference_units"}
    assert set(result.ticker)=={"NA"}
    assert (result.date>=pd.Timestamp("2020-01-01")).all()
    np.testing.assert_array_equal(result.execution_open_reference_units,bars.loc[bars.date>=pd.Timestamp("2020-01-01"),"open"])

def test_all_native_bars_use_completed_intervals_and_true_volume_aggregation():
    bars=source_bars();frame=native_rows(bars,pd.DatetimeIndex(bars.date))
    assert set(frame.timeframe)==set(TIMEFRAMES)
    assert (frame.date<frame.available_from).all()
    row=frame[frame.timeframe=="5d"].iloc[0]
    assert row.open==bars.open.iloc[0]
    assert row.high==bars.high.iloc[:5].max()
    assert row.low==bars.low.iloc[:5].min()
    assert row.close==bars.close.iloc[4]
    assert row.volume==bars.volume.iloc[:5].sum()
    assert "execution_open_reference_units" not in frame

def test_day_d_open_change_cannot_change_any_available_native_price_input():
    bars=source_bars();calendar=pd.DatetimeIndex(bars.date);cut=calendar[320]
    original=native_rows(bars,calendar)
    changed=bars.copy();changed.loc[changed.date>=cut,list(PRICE_COLS)]=1e8
    altered=native_rows(changed,calendar)
    before=original[original.available_from<=cut].reset_index(drop=True)
    after=altered[altered.available_from<=cut].reset_index(drop=True)
    pd.testing.assert_frame_equal(before,after)
    truncated=native_rows(bars[bars.date<cut],calendar[calendar<=cut])
    pd.testing.assert_frame_equal(before,truncated.reset_index(drop=True))


def test_failed_failure_report_upload_preserves_original_error_locally(tmp_path,monkeypatch):
    def broken_upload(*args):
        raise subprocess.CalledProcessError(1,["gh","release","upload"],stderr="HTTP 500")
    monkeypatch.setattr(base,"publish_assets",broken_upload)
    original=ValueError("original source mismatch")
    with pytest.raises(ValueError,match="original source mismatch") as error:
        try:raise original
        except ValueError:
            base.publish_failure(tmp_path,"tag",{"error":str(original),"parts":[]})
            raise
    assert error.value is original
    report=json.loads((tmp_path/"BASE_FAILED.json").read_text())
    assert report["error"]=="original source mismatch"
    assert "HTTP 500" in report["failure_report_upload_error"]


@pytest.mark.parametrize("upload_succeeds",[False,True])
def test_flush_removes_local_data_only_after_entire_part_verifies(tmp_path,monkeypatch,upload_succeeds):
    from types import SimpleNamespace
    from collections import Counter
    current=tmp_path/"current";current.mkdir();source=current/"entity.parquet";source.write_bytes(b"source")
    monkeypatch.setenv("GITHUB_SHA","commit")
    monkeypatch.setattr(base.shutil,"disk_usage",lambda path:SimpleNamespace(free=10**12))
    def upload(tag,*paths):
        assert source.exists()
        assert [p.suffix for p in paths]==[".tar",".csv",".csv",".json"]
        assert all(p.exists() for p in paths)
        if not upload_succeeds:raise RuntimeError("upload exhausted")
    monkeypatch.setattr(base,"publish_assets",upload)
    metrics={("1d","close"):{"timeframe":"1d","column":"close","query_rows":1}}
    args=(tmp_path,"tag",0,[{"ticker":"NA","query_rows":1}],metrics,Counter({"2020-01-02":1}),
          {"inputs_tag":"inputs","recipe_fingerprint":"recipe"},[])
    if upload_succeeds:
        assert base.flush(*args)["tickers"]==["NA"]
        assert not source.exists()
        assert not list(tmp_path.glob("base_0000.*"))
    else:
        with pytest.raises(RuntimeError,match="upload exhausted"):base.flush(*args)
        assert source.exists()
        assert len(list(tmp_path.glob("base_0000.*")))==4


def complete_reports(tmp_path,monkeypatch,damaged=None):
    inputs={"recipe_fingerprint":"recipe","records":[{"ticker":f"T{n}","ordinal":n} for n in range(16)]}
    def download(tag,name,directory):
        shard=int(tag.rsplit("-",1)[1]);ticker=f"T{shard}"
        report={"status":"COMPLETE_PRICE_BASE_SHARD_NOT_WORLD","shard":shard,"selected":1,"completed":1,
                "recipe_fingerprint":"recipe","inputs_tag":"inputs","timeframes":list(TIMEFRAMES),
                "records":[{"ticker":ticker,"native_rows":{tf:1 for tf in TIMEFRAMES}}],
                "parts":[{"tickers":[ticker],"release":tag}]}
        if name=="BASE_FAILED.json":
            report={"error":"HTTP 500 uploading part","failed_ticker":ticker}
        elif damaged is not None:
            damaged(shard,report)
        directory.mkdir(parents=True,exist_ok=True);file=directory/name
        file.write_text(json.dumps(report));return file
    monkeypatch.setattr(base,"download",download)
    return inputs


def test_merge_preflight_accepts_only_complete_matching_shards(tmp_path,monkeypatch):
    inputs=complete_reports(tmp_path,monkeypatch)
    assert len(base.collect_base_reports(tmp_path,inputs,"inputs","build"))==16
    assert not (tmp_path/"BASE_BUILD_INCOMPLETE.json").exists()


def test_merge_reports_every_failed_shard_and_original_upload_error(tmp_path,monkeypatch):
    def damage(shard,report):
        if shard in (4,5,6,7):raise FileNotFoundError("BASE_COMPLETE.json missing")
    inputs=complete_reports(tmp_path,monkeypatch,damage)
    with pytest.raises(ValueError,match="price base incomplete"):
        base.collect_base_reports(tmp_path,inputs,"inputs","build")
    report=json.loads((tmp_path/"BASE_BUILD_INCOMPLETE.json").read_text())
    assert report["complete_shards"]==12
    assert [r["shard"] for r in report["errors"]]==[4,5,6,7]
    assert all(r["upstream_failure"]["error"]=="HTTP 500 uploading part" for r in report["errors"])


@pytest.mark.parametrize("field,value",[("recipe_fingerprint","other"),("inputs_tag","other"),
                                      ("shard",3),("completed",0),("status","INCOMPLETE_NOT_WORLD")])
def test_merge_rejects_mixed_or_incomplete_completion_reports(tmp_path,monkeypatch,field,value):
    def damage(shard,report):
        if shard==0:report[field]=value
    inputs=complete_reports(tmp_path,monkeypatch,damage)
    with pytest.raises(ValueError,match="price base incomplete"):
        base.collect_base_reports(tmp_path,inputs,"inputs","build")
