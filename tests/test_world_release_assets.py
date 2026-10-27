"""Release transport regressions: HTTP 500 must not discard completed batches."""
import hashlib
import json
import subprocess
import io

import pytest

from ci import release_assets as publisher


@pytest.fixture
def transport(tmp_path, monkeypatch):
    files = [tmp_path / name for name in ("part.tar", "part.csv", "part.json")]
    for file in files:
        file.write_bytes(file.name.encode())
    assets = {}
    calls = []
    failures = []
    sleeps = []

    def run(*args):
        calls.append(tuple(map(str, args)))
        if args[0] == "api" and "--input" not in args:
            if args[-1] == "DELETE":
                asset_id = int(args[1].rsplit("/", 1)[-1])
                del assets[next(name for name, item in assets.items() if item["id"] == asset_id)]
                return ""
            return json.dumps({"id":123,"assets":list(assets.values())})
        assert args[0] == "api" and args[1].startswith("https://uploads.github.com/")
        assert "--input" in args
        file = args[args.index("--input")+1]
        action = failures.pop(0) if failures else "success"
        if action in ("success", "lost_response"):
            assets[file.name] = {"id": len(assets) + 1, "name": file.name, "state": "uploaded",
                                 "size": file.stat().st_size, "digest": publisher._digest(file)}
        elif action == "starter":
            assets[file.name] = {"id": 42, "name": file.name, "state": "starter", "size": 0}
        if action != "success":
            raise subprocess.CalledProcessError(1, args, stderr="HTTP 403" if action == "forbidden" else "HTTP 500")
        return json.dumps(assets[file.name])

    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(publisher, "_run", run)
    monkeypatch.setattr(publisher.time, "sleep", sleeps.append)
    return files, assets, calls, failures, sleeps


def uploads(calls):
    return [call[call.index("--input")+1] for call in calls if "--input" in call]


def test_partial_batch_retries_only_failed_asset_and_publishes_manifest_last(transport):
    files, assets, calls, failures, sleeps = transport
    failures.extend(["success", "server_error", "success"])
    publisher.publish_assets("tag", *files)
    assert uploads(calls) == [str(files[0]), str(files[1]), str(files[1]), str(files[2])]
    assert sleeps == [2]
    assert all(file.exists() for file in files)
    publisher.publish_assets("tag", *files)
    assert len(uploads(calls)) == 4  # A repeated flush reuses the complete part.


def test_lost_success_response_is_verified_without_duplicate_upload(transport):
    files, assets, calls, failures, sleeps = transport
    failures.append("lost_response")
    publisher.publish_assets("tag", files[0])
    assert uploads(calls) == [str(files[0])]
    assert sleeps == []


def test_empty_failed_starter_is_removed_before_retry(transport):
    files, assets, calls, failures, sleeps = transport
    failures.append("starter")
    publisher.publish_assets("tag", files[0])
    assert any(call[-1] == "DELETE" for call in calls)
    assert assets[files[0].name]["state"] == "uploaded"


@pytest.mark.parametrize("damage", ["size", "digest", "missing_digest"])
def test_conflicting_completed_asset_is_never_overwritten(transport, damage):
    files, assets, calls, failures, sleeps = transport
    publisher.publish_assets("tag", files[0])
    asset = assets[files[0].name]
    if damage == "size":
        asset["size"] += 1
    elif damage == "digest":
        asset["digest"] = "sha256:" + "0" * 64
    else:
        del asset["digest"]
    with pytest.raises(ValueError, match="immutable"):
        publisher.publish_assets("tag", files[0])
    assert len(uploads(calls)) == 1
    assert not any(call[-1] == "DELETE" for call in calls)


def test_permanent_error_is_not_retried_and_manifest_is_not_published(transport):
    files, assets, calls, failures, sleeps = transport
    failures.append("forbidden")
    with pytest.raises(subprocess.CalledProcessError):
        publisher.publish_assets("tag", *files)
    assert uploads(calls) == [str(files[0])]
    assert sleeps == []


def test_retry_exhaustion_preserves_all_local_files_and_original_error(transport):
    files, assets, calls, failures, sleeps = transport
    failures.extend(["server_error"] * publisher.ATTEMPTS)
    with pytest.raises(subprocess.CalledProcessError) as error:
        publisher.publish_assets("tag", *files)
    assert error.value.stderr == "HTTP 500"
    assert len(uploads(calls)) == publisher.ATTEMPTS
    assert sleeps == [2, 4, 8, 16]
    assert all(file.exists() for file in files)


def test_invalid_asset_lists_fail_before_accessing_github(transport):
    files, assets, calls, failures, sleeps = transport
    for selected in ([], [files[0], files[0]]):
        with pytest.raises(ValueError, match="uniquely named"):
            publisher.publish_assets("tag", *selected)
    assert not calls


def test_digest_reads_file_contents(transport):
    files, *_ = transport
    assert publisher._digest(files[0]) == "sha256:" + hashlib.sha256(files[0].read_bytes()).hexdigest()


def test_successful_batch_uses_one_inventory_read_and_one_post_per_asset(transport):
    files, assets, calls, failures, sleeps = transport
    publisher.publish_assets("tag",*files)
    reads=[call for call in calls if call[0]=="api" and "--input" not in call]
    assert len(reads)==1
    assert len(uploads(calls))==len(files)


def test_http_headers_are_retained_for_failed_rate_limited_requests(monkeypatch):
    from types import SimpleNamespace
    result=SimpleNamespace(returncode=1,stderr="HTTP 403: API rate limit exceeded",
        stdout='HTTP/2.0 403 Forbidden\r\nX-RateLimit-Remaining: 0\r\nX-RateLimit-Reset: 12345\r\n\r\n{"message":"limited"}')
    monkeypatch.setattr(publisher.subprocess,"run",lambda *a,**k:result)
    with pytest.raises(subprocess.CalledProcessError) as error:publisher._run("api","test")
    assert error.value.response_headers=={"x-ratelimit-remaining":"0","x-ratelimit-reset":"12345"}
    assert json.loads(error.value.stdout)=={"message":"limited"}


def test_rate_limit_wait_respects_reset_in_chunks_of_at_most_a_minute(monkeypatch):
    sleeps=[]
    monkeypatch.setattr(publisher.time,"time",lambda:1000)
    monkeypatch.setattr(publisher.time,"sleep",sleeps.append)
    error=subprocess.CalledProcessError(1,["gh"],stderr="HTTP 403: API rate limit exceeded")
    error.response_headers={"x-ratelimit-remaining":"0","x-ratelimit-reset":"1124"}
    publisher._wait_after(error,0)
    assert sleeps==[60,60,5]


def test_quota_failure_waits_before_any_metadata_retry(transport,monkeypatch):
    files,assets,calls,failures,sleeps=transport
    original=publisher._run;blocked=[True];events=[]
    def run(*args):
        if "--input" in args and blocked[0]:
            blocked[0]=False;events.append("limited")
            error=subprocess.CalledProcessError(1,args,stderr="HTTP 403: API rate limit exceeded")
            error.response_headers={"x-ratelimit-remaining":"0","x-ratelimit-reset":"1001"}
            raise error
        if events:events.append("api")
        return original(*args)
    monkeypatch.setattr(publisher,"_run",run)
    monkeypatch.setattr(publisher.time,"time",lambda:1000)
    monkeypatch.setattr(publisher.time,"sleep",lambda seconds:events.append("wait"))
    publisher.publish_assets("tag",files[0])
    assert events[:3]==["limited","wait","api"]


@pytest.fixture
def public_downloads(monkeypatch):
    payloads={"a.bin":b"verified A","b.bin":b"verified B"}
    assets={name:{"name":name,"state":"uploaded","size":len(raw),
                  "digest":"sha256:"+hashlib.sha256(raw).hexdigest(),
                  "browser_download_url":"https://github.com/owner/repo/releases/download/tag/"+name}
            for name,raw in payloads.items()}
    calls=[]
    def inventory(tag):calls.append("inventory");return assets
    def open_url(request,timeout):
        assert request.get_header("Authorization") is None
        calls.append(request.full_url)
        return io.BytesIO(payloads[request.full_url.rsplit("/",1)[1]])
    monkeypatch.setenv("GITHUB_REPOSITORY","owner/repo")
    monkeypatch.setattr(publisher,"_DOWNLOAD_INVENTORIES",{})
    monkeypatch.setattr(publisher,"asset_index",inventory)
    monkeypatch.setattr(publisher.urllib.request,"urlopen",open_url)
    return payloads,assets,calls


def test_public_downloads_share_one_inventory_and_verify_actual_bytes(tmp_path,public_downloads):
    payloads,assets,calls=public_downloads
    for name,raw in payloads.items():
        assert publisher.download_asset("tag",name,tmp_path).read_bytes()==raw
    assert calls.count("inventory")==1
    assert len(calls)==3
    publisher.download_asset("tag","a.bin",tmp_path)
    assert len(calls)==3  # A verified local copy causes no new request.


def test_corrupt_public_download_is_never_promoted_to_a_source_file(tmp_path,public_downloads):
    payloads,assets,calls=public_downloads;payloads["a.bin"]=b"wrong"
    with pytest.raises(ValueError,match="fingerprint differs"):
        publisher.download_asset("tag","a.bin",tmp_path)
    assert not list(tmp_path.iterdir())


def test_download_refuses_wrong_repository_urls_and_changed_local_bytes(tmp_path,public_downloads):
    payloads,assets,calls=public_downloads
    target=publisher.download_asset("tag","a.bin",tmp_path);target.write_bytes(b"changed")
    with pytest.raises(ValueError,match="cached source"):
        publisher.download_asset("tag","a.bin",tmp_path)
    assets["b.bin"]["browser_download_url"]="https://example.com/b.bin"
    with pytest.raises(ValueError,match="download URL differs"):
        publisher.download_asset("tag","b.bin",tmp_path)
