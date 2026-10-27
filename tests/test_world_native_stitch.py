from copy import deepcopy
import json
from pathlib import Path
import pytest
from ci import native_price_stitch as stitch
from ci import native_price_routes as routes


def source():
    return {"run":10,"head":"head","attempt":1,"prefix":"native-price-blocks-v1-10-1","shards":[2]}


def test_stitch_accepts_only_pinned_successful_source_jobs():
    run={"id":10,"head_sha":"head","run_attempt":1}
    job={"id":20,"name":"build (2)","status":"completed","conclusion":"success"}
    proof=stitch.validate_source(source(),run,[job])
    assert proof[0]["release"]=="native-price-blocks-v1-10-1-002" and proof[0]["source_job"]==20
    for changed in (dict(job,status="in_progress",conclusion=None),dict(job,conclusion="failure"),dict(job,conclusion="cancelled")):
        with pytest.raises(ValueError,match="has not succeeded"):stitch.validate_source(source(),run,[changed])
    with pytest.raises(ValueError,match="ambiguous"):stitch.validate_source(source(),run,[job,job])
    with pytest.raises(ValueError,match="identity differs"):stitch.validate_source(source(),dict(run,head_sha="other"),[job])
    with pytest.raises(ValueError,match="prefix differs"):stitch.validate_source(dict(source(),prefix="other"),run,[job])


@pytest.mark.parametrize("shards",[list(range(63)),list(range(64))+[0],list(range(63))+[True],list(range(1,65))])
def test_stitch_requires_a_complete_nonduplicated_64_shard_route_map(monkeypatch,shards):
    monkeypatch.setattr(routes,"api",lambda *args:pytest.fail("invalid route map must fail before API work"))
    with pytest.raises(ValueError,match="exactly once"):stitch.source_plan({"sources":[dict(source(),shards=shards)]})


def test_recorded_stitch_request_routes_every_shard_to_a_successful_pinned_run(monkeypatch):
    request=json.loads(stitch.REQUEST.read_text());monkeypatch.setenv("GITHUB_REPOSITORY","owner/repo")
    def api(endpoint):
        spec=next(s for s in request["sources"] if f"/{s['run']}" in endpoint)
        if "/jobs?" in endpoint:
            jobs=[{"id":s,"name":f"build ({s})","status":"completed","conclusion":"success"} for s in spec["shards"]]
            return {"total_count":len(jobs),"jobs":jobs}
        return {"id":spec["run"],"head_sha":spec["head"],"run_attempt":spec["attempt"]}
    monkeypatch.setattr(routes,"api",api);proof=stitch.source_plan(request)
    assert [r["shard"] for r in proof]==list(range(64))
    assert proof[40]["source_run"]==40450227376 and proof[42]["source_run"]==40370285123
    assert proof[41]["source_run"]==40453879193


@pytest.mark.parametrize("event,status,conclusion",[("pull_request","completed","success"),("workflow_run","in_progress",None),("workflow_run","completed","failure")])
def test_compact_prerequisite_refuses_review_only_live_and_failed_runs(tmp_path,monkeypatch,event,status,conclusion):
    monkeypatch.setenv("GITHUB_REPOSITORY","owner/repo")
    monkeypatch.setattr(stitch,"api",lambda *args:{"path":".github/workflows/native_price_base_recovery.yml","event":event,"status":status,"conclusion":conclusion})
    monkeypatch.setattr(stitch,"download_asset",lambda *args:pytest.fail("must not read coverage from an unaccepted run"))
    with pytest.raises(ValueError,match="has not completed successfully"):stitch.compact_prerequisite(10,{},tmp_path)


def merge_fixture(tmp_path,monkeypatch,base_rows=2,bad_archive=False):
    proof=[{"shard":2,"release":"completion-002"}]
    base={"selected_tickers":1,"query_rows":base_rows,"recipe_fingerprint":"recipe","timeframes":["1d"],"coverage_sha256":"basehash"}
    summary={"status":"ALL_SELECTED_PRICE_ENTITIES_BUILT_NOT_WORLD","shard":2}
    part={"archive_sha256":"archive","coverage_sha256":"coverage"}
    calls=[]
    def download(tag,name,directory):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);file=directory/name
        calls.append(("download",tag,name));file.write_text(json.dumps(summary if name=="SHARD_COMPLETE.json" else part))
        return file
    monkeypatch.setattr(stitch,"download_asset",download)
    monkeypatch.setattr(stitch,"asset_index",lambda tag:{"part_0000.tar":{"state":"uploaded","digest":"sha256:"+("wrong" if bad_archive else "archive"),"size":123},
                                                         "part_0000.coverage.csv":{"state":"uploaded","digest":"sha256:coverage"}})
    monkeypatch.setattr(stitch,"gh_retry",lambda *args:calls.append(("gh",*args)))
    monkeypatch.setattr(stitch,"publish_assets",lambda *args:calls.append(("upload",*map(str,args))))
    def merge(args):
        root=Path(args.directory)
        stitch.builder.download("native-price-source-route-002","SHARD_COMPLETE.json",root/"summary")
        stitch.builder.download("older-002","part_0000.json",root/"part")
        status=root/"NATIVE_PRICE_BUILD_STATUS_V1.json"
        status.write_text(json.dumps(dict(base,query_rows=2)))
        coverage=root/"coverage.csv";coverage.write_text("measured")
        stitch.builder.gh("release","create","result",coverage,status,"--title","result")
    monkeypatch.setattr(stitch.builder,"merge",merge)
    (tmp_path/"NATIVE_STITCH_SOURCE_PLAN.json").write_text("{}")
    return proof,base,calls


def test_stitch_routes_completions_preserves_old_parts_and_publishes_verified_draft(tmp_path,monkeypatch):
    proof,base,calls=merge_fixture(tmp_path,monkeypatch)
    before=stitch.builder.download,stitch.builder.gh
    stitch.stitch({"inputs_tag":"inputs"},proof,"base-release",base,tmp_path)
    assert (stitch.builder.download,stitch.builder.gh)==before
    assert ("download","completion-002","SHARD_COMPLETE.json") in calls
    assert ("download","older-002","part_0000.json") in calls
    publication=[call for call in calls if call[0] in ("gh","upload")]
    assert publication[0]==("gh","release","create","result","--draft","--title","result")
    assert publication[1][0]=="upload" and publication[2]==("gh","release","edit","result","--draft=false")
    status=json.loads((tmp_path/"NATIVE_PRICE_BUILD_STATUS_V1.json").read_text())
    assert status["shard_sources"]==proof and status["unique_archive_bytes"]==123
    assert status["recipe_review_gate"]=="CLOSED_PENDING_PR13_MATH_REVIEW"


def test_stitch_refuses_disagreeing_native_and_compact_stock_day_totals_before_publishing(tmp_path,monkeypatch):
    proof,base,calls=merge_fixture(tmp_path,monkeypatch,base_rows=3)
    before=stitch.builder.download,stitch.builder.gh
    with pytest.raises(ValueError,match="denominator or recipe differs"):stitch.stitch({"inputs_tag":"inputs"},proof,"base",base,tmp_path)
    assert (stitch.builder.download,stitch.builder.gh)==before
    assert not any(call[0] in ("gh","upload") for call in calls)


def test_stitch_refuses_missing_or_changed_remote_archive_before_coverage_publication(tmp_path,monkeypatch):
    proof,base,calls=merge_fixture(tmp_path,monkeypatch,bad_archive=True)
    with pytest.raises(ValueError,match="remote part digest differs"):stitch.stitch({"inputs_tag":"inputs"},proof,"base",base,tmp_path)
    assert not any(call[0] in ("gh","upload") for call in calls)
