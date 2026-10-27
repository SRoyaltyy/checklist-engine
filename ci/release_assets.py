"""Publish immutable release assets, recovering bounded transient upload failures."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import quote
import urllib.error
import urllib.request


ATTEMPTS = 5
_DOWNLOAD_INVENTORIES = {}
_RELEASE_IDS = {}
_DRAFTS_SCANNED = set()
TRANSIENT = re.compile(
    r"HTTP (?:408|429|5\d\d)\b|connection reset|unexpected EOF|"
    r"TLS handshake timeout|i/o timeout|temporary failure|timed out",
    re.IGNORECASE,
)


def _run(*args):
    command = ["gh", *map(str, args)]
    if args[0] == "api":
        command.append("--include")
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    body = result.stdout.replace("\r\n", "\n");headers = {}
    while body.startswith("HTTP/"):
        head, separator, body = body.partition("\n\n")
        if not separator:
            raise ValueError("incomplete GitHub HTTP response headers")
        headers = {key.strip().lower(): value.strip() for line in head.splitlines()[1:]
                   if ":" in line for key, value in [line.split(":", 1)]}
    if result.returncode:
        exc = subprocess.CalledProcessError(result.returncode, command, output=body, stderr=result.stderr)
        exc.response_headers = headers
        raise exc
    return body


def describe_failure(exc):
    if isinstance(exc, subprocess.CalledProcessError):
        return f"{exc}; stderr: {str(exc.stderr or '').strip()}"
    return str(exc)


def _transient(exc):
    return _rate_limited(exc) or isinstance(exc, json.JSONDecodeError) or bool(
        TRANSIENT.search(str(getattr(exc, "stderr", "") or "") + str(getattr(exc, "stdout", "") or "")))


def _rate_limited(exc):
    message = str(getattr(exc, "stderr", "") or "") + str(getattr(exc, "stdout", "") or "")
    headers = getattr(exc, "response_headers", {})
    return headers.get("x-ratelimit-remaining") == "0" or bool(re.search(
        r"API rate limit exceeded|secondary rate limit|HTTP 429\b", message, re.IGNORECASE))


def _pause(attempt):
    time.sleep(2 ** (attempt + 1))


def _wait_after(exc, attempt):
    if not _rate_limited(exc):
        _pause(attempt)
        return
    headers = getattr(exc, "response_headers", {})
    delay = 60 * 2 ** attempt
    if headers.get("retry-after", "").isdigit():
        delay = max(delay, int(headers["retry-after"]))
    reset = headers.get("x-ratelimit-reset") if headers.get("x-ratelimit-remaining") == "0" else None
    if reset is None and not headers:
        # This endpoint does not consume primary quota; do not poll it repeatedly.
        try:
            core = json.loads(_run("api", "rate_limit"))["resources"]["core"]
            if core["remaining"] == 0:
                reset = str(core["reset"])
        except (subprocess.CalledProcessError, ValueError, KeyError):
            pass
    if reset is not None:
        delay = max(delay, int(reset) - int(time.time()) + 1)
    if delay > 3605:
        raise RuntimeError("GitHub quota reset exceeds bounded one-hour wait; local assets retained") from exc
    while delay > 0:
        step = min(60, delay)
        print("GITHUB_RATE_LIMIT_WAIT", step, "remaining", delay, flush=True)
        time.sleep(step);delay -= step


def _read(*args):
    for attempt in range(ATTEMPTS):
        try:
            return _run(*args)
        except subprocess.CalledProcessError as exc:
            if not _transient(exc) or attempt == ATTEMPTS - 1:
                raise
            _wait_after(exc, attempt)


def gh_retry(*args):
    """CLI operations with quota-aware bounded retries; never retries permission errors."""
    result=_read(*args)
    if args[:2]==("release","create") and ("--draft" in args or "--draft=true" in args):
        _DRAFTS_SCANNED.discard(os.environ["GITHUB_REPOSITORY"])
    return result


def release_info(tag):
    """Tag lookup is published-only; authenticate draft discovery and use its ID."""
    repository=os.environ["GITHUB_REPOSITORY"];key=(repository,tag)
    if key in _RELEASE_IDS:
        return json.loads(_read("api",f"repos/{repository}/releases/{_RELEASE_IDS[key]}"))
    try:
        result=json.loads(_read("api",f"repos/{repository}/releases/tags/{quote(tag,safe='')}"))
    except subprocess.CalledProcessError as original:
        if not re.search(r"\bHTTP\s+404\b",str(original.stderr or "")):raise
        if repository not in _DRAFTS_SCANNED:
            page=1
            while True:
                batch=json.loads(_read("api",f"repos/{repository}/releases?per_page=100&page={page}"))
                for release in batch:
                    if not release.get("draft"):continue
                    draft_key=(repository,release["tag_name"]);release_id=int(release["id"])
                    if draft_key in _RELEASE_IDS and _RELEASE_IDS[draft_key]!=release_id:
                        raise ValueError("ambiguous draft release tag")
                    _RELEASE_IDS[draft_key]=release_id
                if len(batch)<100:break
                page+=1
            _DRAFTS_SCANNED.add(repository)
        if key not in _RELEASE_IDS:raise original
        result=json.loads(_read("api",f"repos/{repository}/releases/{_RELEASE_IDS[key]}"))
    _RELEASE_IDS[key]=int(result["id"])
    return result


def _digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return "sha256:" + value.hexdigest()


def asset_index(tag):
    release = release_info(tag)
    assets = release["assets"]
    if len({asset["name"] for asset in assets}) != len(assets):
        raise ValueError("duplicate release asset names")
    return {asset["name"]: dict(asset,_draft_release=True) if release.get("draft") else asset for asset in assets}


def download_asset(tag, name, directory):
    """Use one release inventory, then GitHub's published binary-download URL.

    Public artifact bytes need no repeated REST metadata lookup. Downloaded
    bytes must still match the authenticated inventory's size and SHA-256.
    """
    if Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError("asset name must be a basename")
    repository = os.environ["GITHUB_REPOSITORY"]
    key = (repository, tag)
    if key not in _DOWNLOAD_INVENTORIES:
        _DOWNLOAD_INVENTORIES[key] = asset_index(tag)
    asset = _DOWNLOAD_INVENTORIES[key].get(name)
    if not asset or asset["state"] != "uploaded" or not asset.get("digest", "").startswith("sha256:"):
        raise ValueError("published asset missing or unverified: " + name)
    url = f"https://github.com/{repository}/releases/download/{quote(tag, safe='')}/{quote(name, safe='')}"
    draft=asset.get("_draft_release",False)
    if not draft and asset["browser_download_url"] != url:
        raise ValueError("published download URL differs from requested repository/tag/asset")
    directory = Path(directory);directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    if target.exists():
        if target.stat().st_size == asset["size"] and _digest(target) == asset["digest"]:
            return target
        raise ValueError("cached source asset fingerprint differs: " + name)
    temporary = directory / (name + ".download")
    for attempt in range(ATTEMPTS):
        try:
            if draft:
                # Draft assets have no public URL. gh handles authenticated
                # redirect/download; the token is never placed in a URL or log.
                command=["gh","api",f"repos/{repository}/releases/assets/{int(asset['id'])}","--header","Accept: application/octet-stream"]
                with temporary.open("wb") as stream:
                    result=subprocess.run(command,stdout=stream,stderr=subprocess.PIPE,timeout=360)
                if result.returncode:raise subprocess.CalledProcessError(result.returncode,command,stderr=result.stderr.decode("utf-8",errors="replace"))
            else:
                request = urllib.request.Request(url, headers={"User-Agent": "checklist-engine artifact reader"})
                with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as stream:
                    for chunk in iter(lambda: response.read(1 << 20), b""):
                        stream.write(chunk)
            if temporary.stat().st_size != asset["size"] or _digest(temporary) != asset["digest"]:
                raise ValueError("downloaded asset fingerprint differs: " + name)
            temporary.replace(target)
            return target
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            if isinstance(exc,subprocess.CalledProcessError):error=exc
            elif isinstance(exc, urllib.error.HTTPError):
                error = subprocess.CalledProcessError(exc.code, ["public-asset-download", url], stderr=f"HTTP {exc.code}")
                error.response_headers = {key.lower(): value for key, value in exc.headers.items()}
            elif isinstance(exc, (urllib.error.URLError, TimeoutError)):
                error = subprocess.CalledProcessError(1, ["public-asset-download", url], stderr=str(exc))
            else:
                raise
            if not _transient(error) or attempt == ATTEMPTS - 1:
                raise
            _wait_after(error, attempt)


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
    release = release_info(tag);release_id = int(release["id"])
    assets = {asset["name"]: asset for asset in release["assets"]}
    if len(assets) != len(release["assets"]):
        raise ValueError("duplicate release asset names")

    def matches(asset, path, size, digest):
        return bool(asset and asset.get("name") == path.name and asset["state"] == "uploaded"
                    and asset["size"] == size and asset.get("digest") == digest)

    for path, size, digest in fingerprints:
        for attempt in range(ATTEMPTS):
            asset = assets.get(path.name)
            if asset is not None:
                if matches(asset, path, size, digest):
                    break
                if asset["state"] == "starter" and asset["size"] == 0:
                    # Only an empty failed upload, never a published data asset.
                    _read("api", f"repos/{repository}/releases/assets/{int(asset['id'])}", "--method", "DELETE")
                    assets.pop(path.name)
                else:
                    raise ValueError("immutable release asset differs or has no verified digest: " + path.name)
            try:
                upload = f"https://uploads.github.com/repos/{repository}/releases/{release_id}/assets?name={quote(path.name, safe='')}"
                asset = json.loads(_run("api", upload, "--method", "POST", "--header",
                                        "Content-Type: application/octet-stream", "--input", path))
            except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                # An upload can succeed remotely but lose its response. Reconcile
                # before deciding to retry, including on the final attempt.
                if _rate_limited(exc):
                    if attempt == ATTEMPTS - 1:
                        raise
                    _wait_after(exc, attempt)
                assets = asset_index(tag);asset = assets.get(path.name)
                if matches(asset, path, size, digest):
                    break
                if not _transient(exc) or attempt == ATTEMPTS - 1:
                    raise
                print("RELEASE_UPLOAD_RETRY", tag, path.name, attempt + 1, flush=True)
                if not _rate_limited(exc):
                    _wait_after(exc, attempt)
                continue
            if not matches(asset, path, size, digest):
                raise ValueError("release upload did not verify: " + path.name)
            assets[path.name] = asset
            break
