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
    monkeypatch.setattr(base,"gh",lambda *args:None)
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


def checkpoint(tmp_path,monkeypatch,damage=None):
    report={"status":"PRICE_BASE_PART_ONLY_NOT_WORLD","recipe_fingerprint":"recipe","inputs_tag":"inputs",
            "archive_sha256":"archive","coverage_sha256":"coverage","stock_days_sha256":"dates",
            "members":[{"name":"4e41"+suffix} for suffix in (".bars.parquet",".execution.parquet",".native.parquet")],"query_rows":2,
            "records":[{"ticker":"NA","query_rows":2,"native_rows":{tf:1 for tf in TIMEFRAMES}}]}
    if damage:damage(report)
    directory=tmp_path/"source";directory.mkdir();file=directory/"base_0000.json";file.write_text(json.dumps(report))
    assets={file.name:{"state":"uploaded","digest":"sha256:"+base.sha(file)}}
    for suffix,value in ((".tar","archive"),(".coverage.csv","coverage"),(".stock_days.csv","dates")):
        assets["base_0000"+suffix]={"state":"uploaded","digest":"sha256:"+value}
    monkeypatch.setattr(base,"asset_index",lambda tag:assets)
    monkeypatch.setattr(base,"download",lambda *args:file)
    return assets


def test_compact_resume_reuses_complete_data_and_skips_orphan_manifest(tmp_path,monkeypatch):
    assets=checkpoint(tmp_path,monkeypatch);assets["base_0001.json"]={"state":"uploaded","digest":"sha256:orphan"}
    parts,records=base.recover_base_parts("old-013",{"inputs_tag":"inputs","recipe_fingerprint":"recipe"},{"NA"},tmp_path)
    assert [r["ticker"] for r in records]==["NA"]
    assert [(p["part"],p["release"]) for p in parts]==[("base_0000","old-013")]
    assert json.loads((tmp_path/"BASE_RESUME.json").read_text())["skipped_incomplete"]==["base_0001"]


@pytest.mark.parametrize("damage",[
    lambda r:r.update(inputs_tag="other"),lambda r:r.update(recipe_fingerprint="other"),
    lambda r:r.update(query_rows=3),lambda r:r.update(members=[]),lambda r:r["members"].pop(),
    lambda r:r["records"].append(r["records"][0]),lambda r:r["records"][0].update(ticker="OTHER"),
    lambda r:r["records"][0]["native_rows"].pop("5d")])
def test_compact_resume_rejects_wrong_inputs_incomplete_data_and_foreign_entities(tmp_path,monkeypatch,damage):
    checkpoint(tmp_path,monkeypatch,damage)
    with pytest.raises(ValueError):base.recover_base_parts("old-013",{"inputs_tag":"inputs","recipe_fingerprint":"recipe"},{"NA"},tmp_path)


def test_compact_resume_rejects_changed_remote_archive(tmp_path,monkeypatch):
    assets=checkpoint(tmp_path,monkeypatch);assets["base_0000.tar"]["digest"]="sha256:changed"
    with pytest.raises(ValueError,match="digest differs"):
        base.recover_base_parts("old-013",{"inputs_tag":"inputs","recipe_fingerprint":"recipe"},{"NA"},tmp_path)


def test_all_resumed_compact_shard_publishes_completion_without_recomputing_entities(tmp_path,monkeypatch):
    from types import SimpleNamespace
    record={"ticker":"NA","query_rows":2,"native_rows":{tf:1 for tf in TIMEFRAMES}}
    part={"part":"base_0000","release":"old-013","tickers":["NA"]}
    inputs={"recipe_fingerprint":"recipe","records":[{"ticker":"NA","ordinal":13,"source_part":"source"}],
            "feature_shards":64,"prepared_shards":{f"frozen_{n:03d}.parquet":{"sha256":"hash"} for n in (13,29,45,61)},"calendar_sha256":"hash"}
    def download(tag,name,directory):
        directory.mkdir(parents=True,exist_ok=True);file=directory/name
        if name=="BUILD_INPUTS.json":file.write_text(json.dumps(inputs))
        elif name=="market_sessions.parquet":pd.DataFrame({"date":pd.bdate_range("2020-01-01",periods=2)}).to_parquet(file)
        else:pd.DataFrame({"ticker":["NA"] if name=="frozen_013.parquet" else []}).to_parquet(file)
        return file
    monkeypatch.setattr(base,"download",download);monkeypatch.setattr(base,"sha",lambda p:"hash")
    monkeypatch.setattr(base,"recipe_fingerprint",lambda:("recipe",{}))
    monkeypatch.setattr(base,"recover_base_parts",lambda *args:([part],[record]))
    def forbidden(*args):raise AssertionError("completed entities must not be recomputed")
    monkeypatch.setattr(base,"source_archive",forbidden)
    calls=[];monkeypatch.setattr(base,"gh",lambda *args:calls.append(args))
    monkeypatch.setattr(base,"publish_assets",lambda *args:None)
    for key,value in (("GITHUB_RUN_ID","123"),("GITHUB_RUN_ATTEMPT","1"),("GITHUB_SHA","commit")):monkeypatch.setenv(key,value)
    base.build(SimpleNamespace(directory=str(tmp_path),inputs_tag="inputs",shard=13,resume_prefix="old"))
    report=json.loads((tmp_path/"BASE_COMPLETE.json").read_text())
    assert report["completed"]==1 and report["records"]==[record] and report["parts"]==[part]
    assert report["checkpoint_sources"]==["old-013"]
    assert "--draft" in calls[0] and "--draft=false" in calls[-1]


def test_compact_stitch_uses_explicit_shard_routes_and_declared_checkpoint_sources(tmp_path,monkeypatch):
    def damage(shard,report):
        if shard==13:
            report["checkpoint_sources"]=["old-013"];report["parts"][0]["release"]="old-013"
    inputs=complete_reports(tmp_path,monkeypatch,damage)
    reports=base.collect_base_reports(tmp_path,inputs,"inputs","original",{"13":"recovery-013"})
    assert reports[13][0]=="recovery-013" and reports[13][2]["parts"][0]["release"]=="old-013"


def test_compact_stitch_rejects_part_from_another_shard(tmp_path,monkeypatch):
    def damage(shard,report):
        if shard==13:
            report["checkpoint_sources"]=["old-014"];report["parts"][0]["release"]="old-014"
    inputs=complete_reports(tmp_path,monkeypatch,damage)
    with pytest.raises(ValueError,match="price base incomplete"):base.collect_base_reports(tmp_path,inputs,"inputs","original")


def test_compact_stitch_requires_uploaded_archive_and_matching_digests():
    part={"part":"base_0000","archive_sha256":"a","coverage_sha256":"b","stock_days_sha256":"c"}
    assets={"base_0000"+suffix:{"state":"uploaded","digest":"sha256:"+value} for suffix,value in ((".tar","a"),(".coverage.csv","b"),(".stock_days.csv","c"))}
    base.verify_base_asset_digests(part,assets)
    assets["base_0000.tar"]["state"]="starter"
    with pytest.raises(ValueError,match="remote asset differs"):base.verify_base_asset_digests(part,assets)


@pytest.mark.parametrize("status,conclusion,head",[("in_progress",None,"pinned"),("completed","failure","pinned"),("completed","success","other")])
def test_compact_plan_cannot_start_before_pinned_native_recovery_passes(tmp_path,monkeypatch,status,conclusion,head):
    from ci import native_price_base_recovery as recovery
    calls=[]
    def api(endpoint):
        calls.append(endpoint)
        return {"head_sha":head,"status":status,"conclusion":conclusion}
    monkeypatch.setattr(recovery,"api",api);monkeypatch.setenv("GITHUB_REPOSITORY","owner/repo")
    with pytest.raises(ValueError,match="required native recovery"):
        recovery.plan({"prerequisite_native_run":10,"prerequisite_native_sha":"pinned"},tmp_path)
    assert len(calls)==1


def test_compact_plan_preserves_thirteen_successes_and_selects_only_three_failures(tmp_path,monkeypatch):
    from ci import native_price_base_recovery as recovery
    request={"prerequisite_native_run":10,"prerequisite_native_sha":"native","source_run":20,
             "source_run_sha":"compact","source_run_attempt":1,"shards":[13,14,15]}
    def api(endpoint):
        if endpoint.endswith("/10"):return {"head_sha":"native","status":"completed","conclusion":"success"}
        if "/jobs?" in endpoint:
            jobs=[{"id":n,"name":f"build ({n})","status":"completed","conclusion":"success" if n<13 else "failure"} for n in range(16)]
            return {"jobs":jobs,"total_count":16}
        return {"id":20,"head_sha":"compact","run_attempt":1}
    monkeypatch.setattr(recovery,"api",api);monkeypatch.setenv("GITHUB_REPOSITORY","owner/repo")
    monkeypatch.setenv("GITHUB_OUTPUT",str(tmp_path/"output"))
    recovery.plan(request,tmp_path)
    report=json.loads((tmp_path/"BASE_RECOVERY_PLAN.json").read_text())
    assert [r["shard"] for r in report["source_jobs"]]==[13,14,15]
    assert report["successful_shards_preserved"]==list(range(13))
