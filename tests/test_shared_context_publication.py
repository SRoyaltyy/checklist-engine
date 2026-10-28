import json
import subprocess
import pytest
from ci import shared_context_build as builder


def test_failed_creation_reports_server_reason_and_keeps_all_completed_native_files(tmp_path,monkeypatch,capsys):
    files=[tmp_path/'shared_context_1d.parquet',tmp_path/'coverage.csv',tmp_path/'status.json']
    for file in files:file.write_bytes(b'completed-native-value')
    monkeypatch.setenv('GITHUB_SHA','source')
    calls=[]
    def fail(*args):
        calls.append(args)
        raise subprocess.CalledProcessError(1,['gh','api','release'],stderr='HTTP 422',
                                            output=json.dumps(dict(message='Validation Failed',errors=[dict(field='target_commitish',code='invalid')])))
    monkeypatch.setattr(builder,'gh',fail)
    monkeypatch.setattr(builder,'publish_assets',lambda *args:pytest.fail('upload cannot follow failed creation'))
    with pytest.raises(subprocess.CalledProcessError):builder.publish_shared('tag',files[:1],files[1],files[2])
    output=capsys.readouterr().out
    assert 'SHARED_CONTEXT_PUBLICATION_FAILED' in output and 'target_commitish' in output
    assert len(calls)==1 and all(file.read_bytes()==b'completed-native-value' for file in files)


def test_publication_uploads_all_values_before_finalizing_release(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_SHA','source');calls=[]
    monkeypatch.setattr(builder,'gh',lambda *args:calls.append(args))
    monkeypatch.setattr(builder,'publish_assets',lambda *args:calls.append(('upload',*args)))
    files=[tmp_path/'one.parquet',tmp_path/'two.parquet'];coverage=tmp_path/'coverage.csv';status=tmp_path/'status.json'
    builder.publish_shared('tag',files,coverage,status)
    assert calls[1]==('upload','tag',*files,coverage,status)
    assert calls[2]==('release','edit','tag','--draft=false')
