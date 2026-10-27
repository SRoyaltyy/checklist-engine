import pytest
from ci.recovery_speedup import remaining


def fixture():
    request={"source_run":10,"source_head":"pinned","source_attempt":1,"shards":[18,40,41]}
    run={"id":10,"head_sha":"pinned","run_attempt":1,"status":"completed"}
    jobs=[{"id":s,"name":f"build ({s})","status":"completed","conclusion":c} for s,c in ((18,"success"),(40,"cancelled"),(41,"failure"))]
    return request,run,jobs


def test_speedup_keeps_successes_and_restarts_only_failed_cancelled_shards():
    request,run,jobs=fixture()
    assert remaining(request,run,jobs)==([18],[40,41],[40])


def test_speedup_refuses_live_missing_duplicate_and_changed_source_work():
    request,run,jobs=fixture()
    with pytest.raises(ValueError,match="terminal"):remaining(request,dict(run,status="in_progress"),jobs)
    with pytest.raises(ValueError,match="identity differs"):remaining(request,dict(run,head_sha="other"),jobs)
    with pytest.raises(ValueError,match="missing or still live"):remaining(request,run,jobs[:-1])
    with pytest.raises(ValueError,match="ambiguous"):remaining(request,run,jobs+[jobs[0]])
    with pytest.raises(ValueError,match="missing or still live"):remaining(request,run,[dict(jobs[0],status="in_progress"),*jobs[1:]])
