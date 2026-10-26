from copy import deepcopy

import pytest

from ci.native_price_recovery import validate_failed_shards


def source():
    request={"shards":[0,2],"source_run":123,"source_run_sha":"commit","source_run_attempt":1}
    run={"id":123,"head_sha":"commit","run_attempt":1}
    jobs=[{"id":10,"name":"build (0)","status":"completed","conclusion":"failure"},
          {"id":12,"name":"build (2)","status":"completed","conclusion":"failure"},
          {"id":13,"name":"build (3)","status":"in_progress","conclusion":None},
          {"id":14,"name":"build (4)","status":"completed","conclusion":"success"}]
    return request,run,jobs


def test_recovery_selects_only_confirmed_failed_shards_and_keeps_other_work():
    request,run,jobs=source();before=deepcopy(jobs)
    proof=validate_failed_shards(request,run,jobs)
    assert [r["source_job_id"] for r in proof]==[10,12]
    assert jobs==before


@pytest.mark.parametrize("shards",[[3],[4],[5],[],[0,0],[-1],[64],[True]])
def test_recovery_refuses_live_successful_missing_or_invalid_shards(shards):
    request,run,jobs=source();request["shards"]=shards
    with pytest.raises(ValueError):validate_failed_shards(request,run,jobs)


@pytest.mark.parametrize("field,value",[("head_sha","other"),("run_attempt",2),("id",999)])
def test_recovery_rejects_changed_source_run(field,value):
    request,run,jobs=source();run[field]=value
    with pytest.raises(ValueError,match="differs"):validate_failed_shards(request,run,jobs)


def test_ambiguous_source_job_listing_cannot_start_duplicate_work():
    request,run,jobs=source();jobs.append(dict(jobs[0],id=99))
    with pytest.raises(ValueError,match="ambiguous"):validate_failed_shards(request,run,jobs)
