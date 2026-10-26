"""Release transport regressions: HTTP 500 must not discard completed batches."""
import hashlib
import json
import subprocess

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
        if args[:2] == ("release", "view"):
            return "123\n"
        if args[0] == "api":
            if args[-1] == "DELETE":
                asset_id = int(args[1].rsplit("/", 1)[-1])
                del assets[next(name for name, item in assets.items() if item["id"] == asset_id)]
                return ""
            return json.dumps([list(assets.values())])
        assert args[:3] == ("release", "upload", "tag")
        file = args[3]
        action = failures.pop(0) if failures else "success"
        if action in ("success", "lost_response"):
            assets[file.name] = {"id": len(assets) + 1, "name": file.name, "state": "uploaded",
                                 "size": file.stat().st_size, "digest": publisher._digest(file)}
        elif action == "starter":
            assets[file.name] = {"id": 42, "name": file.name, "state": "starter", "size": 0}
        if action != "success":
            raise subprocess.CalledProcessError(1, args, stderr="HTTP 403" if action == "forbidden" else "HTTP 500")
        return ""

    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(publisher, "_run", run)
    monkeypatch.setattr(publisher.time, "sleep", sleeps.append)
    return files, assets, calls, failures, sleeps


def uploads(calls):
    return [call[-1] for call in calls if call[:2] == ("release", "upload")]


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
