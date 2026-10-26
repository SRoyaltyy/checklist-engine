"""Publish immutable release assets, recovering bounded transient upload failures."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


ATTEMPTS = 5
TRANSIENT = re.compile(
    r"HTTP (?:408|429|5\d\d)\b|connection reset|unexpected EOF|"
    r"TLS handshake timeout|i/o timeout|temporary failure|connection timed out",
    re.IGNORECASE,
)


def _run(*args):
    return subprocess.run(
        ["gh", *map(str, args)], check=True, capture_output=True, text=True,
        encoding="utf-8",
    ).stdout


def describe_failure(exc):
    if isinstance(exc, subprocess.CalledProcessError):
        return f"{exc}; stderr: {str(exc.stderr or '').strip()}"
    return str(exc)


def _transient(exc):
    return bool(TRANSIENT.search(str(exc.stderr or "") + str(exc.stdout or "")))


def _pause(attempt):
    time.sleep(2 ** (attempt + 1))


def _read(*args):
    for attempt in range(ATTEMPTS):
        try:
            return _run(*args)
        except subprocess.CalledProcessError as exc:
            if not _transient(exc) or attempt == ATTEMPTS - 1:
                raise
            _pause(attempt)


def _digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return "sha256:" + value.hexdigest()


def publish_assets(tag, *paths):
    """Upload in order, reusing only assets with the same size and SHA-256.

    A part's manifest must be last. No completed asset is replaced. An interrupted
    upload's empty ``starter`` asset may be removed before retrying that name.
    Local files remain available to the caller until the entire part is durable.
    """
    paths = [Path(path) for path in paths]
    if not paths or len({path.name for path in paths}) != len(paths):
        raise ValueError("expected nonempty, uniquely named release assets")
    fingerprints = [(path, path.stat().st_size, _digest(path)) for path in paths]
    repository = os.environ["GITHUB_REPOSITORY"]
    release_id = int(_read("release", "view", tag, "--json", "databaseId", "--jq", ".databaseId"))
    endpoint = f"repos/{repository}/releases/{release_id}/assets"

    def existing(name):
        pages = json.loads(_read("api", endpoint, "--paginate", "--slurp"))
        matches = [asset for page in pages for asset in page if asset["name"] == name]
        if len(matches) > 1:
            raise ValueError("duplicate release asset: " + name)
        return matches[0] if matches else None

    for path, size, digest in fingerprints:
        for attempt in range(ATTEMPTS):
            asset = existing(path.name)
            if asset is not None:
                if asset["state"] == "uploaded" and asset["size"] == size and asset.get("digest") == digest:
                    break
                if asset["state"] == "starter" and asset["size"] == 0:
                    # Only an empty failed upload, never a published data asset.
                    _run("api", f"repos/{repository}/releases/assets/{int(asset['id'])}", "--method", "DELETE")
                else:
                    raise ValueError("immutable release asset differs or has no verified digest: " + path.name)
            try:
                _run("release", "upload", tag, path)
            except subprocess.CalledProcessError as exc:
                # An upload can succeed remotely but lose its response. Reconcile
                # before deciding to retry, including on the final attempt.
                asset = existing(path.name)
                if asset and asset["state"] == "uploaded" and asset["size"] == size and asset.get("digest") == digest:
                    break
                if not _transient(exc) or attempt == ATTEMPTS - 1:
                    raise
                print("RELEASE_UPLOAD_RETRY", tag, path.name, attempt + 1, flush=True)
                _pause(attempt)
                continue
            asset = existing(path.name)
            if not asset or asset["state"] != "uploaded" or asset["size"] != size or asset.get("digest") != digest:
                raise ValueError("release upload did not verify: " + path.name)
            break
