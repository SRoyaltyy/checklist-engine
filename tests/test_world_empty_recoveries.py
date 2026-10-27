from ci import mark_empty_recoveries as marker


def test_only_request_shells_are_marked_and_assets_are_preserved(monkeypatch):
    calls=[];monkeypatch.setattr(marker,"gh_retry",lambda *args:calls.append(args))
    assets={"SHARD_REQUEST.json":{"id":1}}
    result=marker.mark_empty("tag",assets)
    assert result["status"]=="MARKED_INCOMPLETE_DRAFT"
    assert "--draft=true" in calls[0]
    assert assets=={"SHARD_REQUEST.json":{"id":1}}


def test_any_price_or_diagnostic_evidence_prevents_empty_marking(monkeypatch):
    monkeypatch.setattr(marker,"gh_retry",lambda *args:(_ for _ in ()).throw(AssertionError("data release changed")))
    for name in ("part_0000.tar","SHARD_COMPLETE.json","SHARD_FAILED.json"):
        assert marker.mark_empty("tag",{"SHARD_REQUEST.json":{},name:{}})["status"]=="PRESERVED_HAS_DATA_OR_OTHER_EVIDENCE"
