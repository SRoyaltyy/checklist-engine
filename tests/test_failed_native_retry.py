from copy import deepcopy
import json
import pytest
from ci import retry_failed_native as retry


def test_failed_only_dispatch_preserves_live_jobs_and_reuses_same_request_across_controller_runs(tmp_path,monkeypatch):
    request=json.loads(retry.Path("ci/NATIVE_FAILED_RETRY_REQUEST.json").read_text())
    jobs=[{"id":s,"name":f"build ({s})","status":"completed","conclusion":"failure"} for s in request["shards"]]
    jobs += [{"id":s,"name":f"build ({s})","status":"in_progress","conclusion":None} for s in (18,40)]
    before=deepcopy(jobs);dispatched=[];visible=[]
    def api(endpoint):
        if "/workflows/" in endpoint:return {"workflow_runs":visible}
        if "/jobs?" in endpoint:return {"total_count":len(jobs),"jobs":jobs}
        return {"id":request["source_run"],"head_sha":request["source_run_sha"],"run_attempt":request["source_run_attempt"]}
    def gh(*args):
        assert "/dispatches" in args[1] and "cancel" not in str(args)
        payload=json.loads(retry.Path(args[-1]).read_text());dispatched.append(payload)
        visible.append({"id":999,"head_sha":"fixed","run_attempt":1,"display_title":"native-recovery-workflow_dispatch-"+payload["inputs"]["recovery_id"]})
    monkeypatch.setattr(retry,"api",api);monkeypatch.setattr(retry,"gh_retry",gh)
    monkeypatch.setenv("GITHUB_REPOSITORY","owner/repo");monkeypatch.setattr(retry,"__name__","test")
    import sys
    monkeypatch.setattr(sys,"argv",["retry","--directory",str(tmp_path)])
    retry.main();monkeypatch.setenv("GITHUB_RUN_ID","a-later-controller-run");retry.main()
    report=json.loads((tmp_path/"FAILED_NATIVE_RETRY_HANDOFF.json").read_text())
    assert len(dispatched)==1 and jobs==before
    assert report["live_source_jobs_untouched"]==["build (18)","build (40)"] and report["replacement_run"]==999
    assert not {18,40}&set(report["request"]["shards"])
