import json
import subprocess

import pytest

from ci import native_price_run as runner


def test_only_release_uploads_use_new_transport_and_recipe_stays_identical(monkeypatch,tmp_path):
    calls=[];uploads=[]
    original_gh=lambda *args:calls.append(args)
    monkeypatch.setattr(runner.builder,"gh",original_gh)
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
