"""Shared helpers for no-AI data pipelines (plain HTTP + gh release). No LLM calls."""
import json, os, subprocess, time, urllib.request, urllib.error

UA = os.environ.get("SEC_UA", "checklist-engine research cyrus-checklist@users.noreply.github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "SRoyaltyy/checklist-engine")
COMPOSED = ("compact-world-build-composed-v1-41221028803-1", "COMPACT_WORLD_BUILD_COMPOSED.json")
_last = [0.0]


def get(url, dest=None, pace=0.15, tries=6, ua=UA, timeout=300):
    """GET with polite pacing (<=~7 req/s) and exponential backoff. Streams to dest if given."""
    for i in range(tries):
        wait = pace - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity", "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if dest:
                    with open(dest + ".part", "wb") as f:
                        while True:
                            b = r.read(1 << 20)
                            if not b:
                                break
                            f.write(b)
                    os.replace(dest + ".part", dest)
                    return dest
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            err = e
        except Exception as e:  # network
            err = e
        time.sleep(min(60, 2 ** i))
    raise RuntimeError(f"GET failed {url}: {err}")


def gh(*args, check=True):
    return subprocess.run(["gh", *args, "-R", REPO], capture_output=True, text=True, check=check).stdout


def ensure_release(tag, title):
    if subprocess.run(["gh", "release", "view", tag, "-R", REPO], capture_output=True).returncode != 0:
        gh("release", "create", tag, "--title", title, "--notes", "No-AI data pipeline output. See docs/NO_AI_DATA_PIPELINES_V1.md", "--latest=false")


def assets(tag):
    try:
        return {a["name"] for a in json.loads(gh("release", "view", tag, "--json", "assets"))["assets"]}
    except Exception:
        return set()


def upload(tag, *paths):
    gh("release", "upload", tag, *paths, "--clobber")


def cohort():
    os.makedirs("_in", exist_ok=True)
    p = os.path.join("_in", COMPOSED[1])
    if not os.path.exists(p):
        gh("release", "download", COMPOSED[0], "-p", COMPOSED[1], "-D", "_in", "--clobber")
    return [r["ticker"] for r in json.load(open(p))["completed"]]
