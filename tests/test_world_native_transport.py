import json
import subprocess

import pytest

from ci import native_price_run as runner


def test_only_release_uploads_use_new_transport_and_recipe_stays_identical(monkeypatch,tmp_path):
    calls=[];uploads=[]
    original_gh=lambda *args:calls.append(args)
    monkeypatch.setattr(runner.builder,"gh",original_gh)
    monkeypatch.setattr(runner,"gh_retry",original_gh)
    monkeypatch.setattr(runner,"publish_assets",lambda *args:uploads.append(args))
    recipe=runner.builder.recipe_fingerprint()
    def build():
        assert runner.builder.recipe_fingerprint()==recipe
        runner.builder.gh("release","create","tag","--title","tag")
        runner.builder.gh("release","download","source","-p","source.tar")
        runner.builder.gh("release","upload","tag",tmp_path/"part.tar",tmp_path/"part.json")
    monkeypatch.setattr(runner.builder,"main",build)
    runner.main()
    assert calls==[("release","create","tag","--title","tag"),("release","download","source","-p","source.tar")]
    assert uploads==[("tag",tmp_path/"part.tar",tmp_path/"part.json")]
    assert runner.builder.gh is original_gh


def test_failure_report_upload_cannot_mask_original_builder_error(monkeypatch,tmp_path):
    original_gh=lambda *args:None
    monkeypatch.setattr(runner.builder,"gh",original_gh)
    def failed_upload(*args):
        raise subprocess.CalledProcessError(1,["gh","release","upload"],stderr="HTTP 500")
    monkeypatch.setattr(runner,"publish_assets",failed_upload)
    report=tmp_path/"SHARD_FAILED.json"
    original=ValueError("source interval mismatch")
    def build():
        try:raise original
        except ValueError:
            report.write_text(json.dumps({"error":str(original)}))
            runner.builder.gh("release","upload","tag",report)
            raise
    monkeypatch.setattr(runner.builder,"main",build)
    with pytest.raises(ValueError,match="source interval mismatch") as error:runner.main()
    assert error.value is original
    assert "HTTP 500" in json.loads(report.read_text())["failure_report_upload_error"]
    assert runner.builder.gh is original_gh


def test_completion_upload_failure_is_still_fatal_and_restores_transport(monkeypatch,tmp_path):
    original_gh=lambda *args:None
    monkeypatch.setattr(runner.builder,"gh",original_gh)
    def failed_upload(*args):raise RuntimeError("upload exhausted")
    monkeypatch.setattr(runner,"publish_assets",failed_upload)
    monkeypatch.setattr(runner.builder,"main",lambda:runner.builder.gh("release","upload","tag",tmp_path/"SHARD_COMPLETE.json"))
    with pytest.raises(RuntimeError,match="upload exhausted"):runner.main()
    assert runner.builder.gh is original_gh


def recovered_source(tmp_path,monkeypatch):
    report={"inputs_tag":"inputs","recipe_fingerprint":"recipe","tickers":["NA"],
            "entity_records":[{"ticker":"NA"}],"archive_sha256":"a"*64,"coverage_sha256":"b"*64}
    file=tmp_path/"part_0000.json";file.write_text(json.dumps(report))
    assets={"part_0000.json":{"state":"uploaded","digest":"sha256:"+runner.builder.sha(file)},
            "part_0000.tar":{"state":"uploaded","digest":"sha256:"+"a"*64},
            "part_0000.coverage.csv":{"state":"uploaded","digest":"sha256:"+"b"*64}}
    monkeypatch.setattr(runner,"asset_index",lambda tag:assets)
    monkeypatch.setattr(runner.builder,"download",lambda tag,name,directory:tmp_path/name)
    return report,assets,file


def test_recovery_reuses_only_digest_verified_complete_parts(tmp_path,monkeypatch):
    report,assets,file=recovered_source(tmp_path,monkeypatch)
    parts,records=runner.recovered_parts("tag",{"inputs_tag":"inputs","recipe_fingerprint":"recipe"},tmp_path)
    assert parts[0]["tickers"]==["NA"]
    assert records==[{"ticker":"NA"}]
    assert json.loads((tmp_path/"RECOVERY_SKIPPED_PARTS.json").read_text())["completed_parts_reused"]==1


def test_recovery_skips_orphan_manifests_without_deleting_any_old_asset(tmp_path,monkeypatch):
    report,assets,file=recovered_source(tmp_path,monkeypatch)
    del assets["part_0000.tar"]
    before=dict(assets)
    parts,records=runner.recovered_parts("tag",{"inputs_tag":"inputs","recipe_fingerprint":"recipe"},tmp_path)
    assert parts==records==[]
    assert assets==before and file.exists()
    assert json.loads((tmp_path/"RECOVERY_SKIPPED_PARTS.json").read_text())["skipped"][0]["part"]=="part_0000"


@pytest.mark.parametrize("name",["part_0000.json","part_0000.tar","part_0000.coverage.csv"])
def test_recovery_rejects_changed_completed_bytes(tmp_path,monkeypatch,name):
    report,assets,file=recovered_source(tmp_path,monkeypatch)
    assets[name]["digest"]="sha256:"+"0"*64
    with pytest.raises(ValueError,match="remote digest differs"):
        runner.recovered_parts("tag",{"inputs_tag":"inputs","recipe_fingerprint":"recipe"},tmp_path)


def test_compact_entry_restores_source_helpers_even_on_failure(monkeypatch):
    from ci import native_price_base_run as compact
    original=(compact.base.gh,compact.base.download,compact.sources.gh,compact.sources.download)
    def build():
        assert compact.base.gh is compact.sources.gh is compact.gh_retry
        assert compact.base.download is compact.sources.download is compact.download_asset
        raise ValueError("original build failure")
    monkeypatch.setattr(compact.base,"main",build)
    with pytest.raises(ValueError,match="original build failure"):compact.main()
    assert (compact.base.gh,compact.base.download,compact.sources.gh,compact.sources.download)==original
