"""Shared helpers for no-AI data pipelines (plain HTTP + gh release). No LLM calls."""
import html, json, math, os, re, subprocess, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime

UA = "checklist-engine research cyrus-checklist@users.noreply.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "SRoyaltyy/checklist-engine")
COMPOSED = ("compact-world-build-composed-v1-41221028803-1", "COMPACT_WORLD_BUILD_COMPOSED.json")
_last = [0.0]


SEC_HOSTS = {"sec.gov", "www.sec.gov", "data.sec.gov"}


def redact(value):
    text = str(value)
    relay = os.environ.get("PRIMARY_ACTION_RELAY_URL", "").strip()
    if relay:
        text = text.replace(relay, "[RELAY REDACTED]")
        parsed = urllib.parse.urlsplit(relay)
        if parsed.netloc:
            text = text.replace(parsed.netloc, "[RELAY HOST REDACTED]")
        for _, token in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
            if len(token) > 3:
                text = text.replace(token, "[REDACTED]")
                text = text.replace(urllib.parse.quote(token, safe=""), "[REDACTED]")
    return re.sub(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',
                  '[CONTACT EMAIL REDACTED]', text)


class SourceError(RuntimeError):
    def __init__(self, evidence):
        self.evidence = evidence
        super().__init__(json.dumps(evidence, sort_keys=True))


def response_excerpt(raw):
    text=raw.decode('utf-8','replace')
    text=re.sub(r'<(style|script)\b[^>]*>.*?</\1\s*>',' ',text,flags=re.I|re.S)
    text=html.unescape(re.sub(r'<[^>]+>',' ',text))
    text=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','[IP REDACTED]',text)
    return redact(re.sub(r'\s+',' ',text).strip())[:800]


def retry_after_seconds(headers):
    value=(headers or {}).get('Retry-After')
    if value is None:return None
    value=str(value).strip()
    if value.isdigit():return int(value)
    try:
        deadline=parsedate_to_datetime(value)
        if deadline.tzinfo is None:return None
        return max(0,math.ceil((deadline-datetime.now(timezone.utc)).total_seconds()))
    except (TypeError,ValueError,OverflowError):return None


def _relay(url):
    relay = os.environ.get("PRIMARY_ACTION_RELAY_URL", "").strip()
    if not relay:
        raise RuntimeError("DIRECT_SEC_REQUEST_FORBIDDEN: PRIMARY_ACTION_RELAY_URL is required")
    b = urllib.parse.urlsplit(relay)
    target = urllib.parse.urlsplit(url)
    if target.scheme != "https" or target.hostname not in SEC_HOSTS or target.username or target.password:
        raise ValueError("SEC source must be an official HTTPS URL without credentials")
    if b.scheme != "https" or not b.hostname or b.username or b.password or b.hostname in SEC_HOSTS:
        raise ValueError("SEC relay must be HTTPS without embedded credentials")
    q = [(k, v) for k, v in urllib.parse.parse_qsl(b.query, keep_blank_values=True) if k != "url"] + [("url", url)]
    return urllib.parse.urlunsplit((b.scheme, b.netloc, b.path or "/", urllib.parse.urlencode(q), ""))


def get(url, dest=None, pace=0.15, tries=6, ua=None, timeout=300, max_bytes=None):
    """SEC uses the established relay only; a denied request never changes routes."""
    sec = urllib.parse.urlsplit(url).hostname in SEC_HOSTS
    agent = ua or os.environ.get("SEC_USER_AGENT") or os.environ.get("SEC_UA") or UA
    if sec:
        if "@" not in agent or "\n" in agent or "\r" in agent:
            raise ValueError("SEC User-Agent requires a declared name and contact email")
        return _get(_relay(url), dest, max(1.0, pace), tries, agent, timeout,
                    shown=url, route="relay", max_bytes=max_bytes)
    return _get(url, dest, pace, tries, agent, timeout, max_bytes=max_bytes)


def _get(url, dest=None, pace=0.15, tries=6, ua=UA, timeout=300, shown=None, route="direct", max_bytes=None):
    """Paced HTTP; stream downloads atomically and redact route secrets."""
    if urllib.parse.urlsplit(url).hostname in SEC_HOSTS:
        raise RuntimeError("DIRECT_SEC_REQUEST_FORBIDDEN")
    if tries < 1 or (max_bytes is not None and max_bytes < 1):
        raise ValueError("positive retry and byte limits required")
    source = shown or url
    for i in range(tries):
        wait = pace - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity", "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if dest:
                    with open(dest + ".part", "wb") as f:
                        size = 0
                        while True:
                            b = r.read(1 << 20)
                            if not b:
                                break
                            size += len(b)
                            if max_bytes is not None and size > max_bytes:
                                raise ValueError("source exceeds declared byte limit")
                            f.write(b)
                    os.replace(dest + ".part", dest)
                    return dest
                raw = r.read() if max_bytes is None else r.read(max_bytes + 1)
                if max_bytes is not None and len(raw) > max_bytes:
                    raise ValueError("source exceeds declared byte limit")
                return raw
        except urllib.error.HTTPError as e:
            try:
                excerpt = response_excerpt(e.read(16384))
            except Exception:
                excerpt = "unreadable HTTP error body"
            err = dict(url=source, route=route, http_status=e.code, attempts=i+1,
                       response_excerpt=redact(excerpt), user_agent=redact(ua), request_spacing_seconds=pace)
            if e.code==429:err['retry_after_seconds']=retry_after_seconds(e.headers)
            if e.code in (403, 404, 429) or e.code < 500 or i == tries - 1:
                raise SourceError(err) from None
        except (OSError, TimeoutError) as e:
            err = dict(url=source, route=route, attempts=i+1, error_type=type(e).__name__, message=redact(e))
        finally:
            if dest and os.path.exists(dest + ".part"):
                os.remove(dest + ".part")
        if i == tries - 1:
            break
        time.sleep(min(60, 2 ** i))
    raise SourceError(err) from None


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
