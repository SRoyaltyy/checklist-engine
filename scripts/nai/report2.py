import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

TOKEN = os.environ.get("GH_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "SRoyaltyy/checklist-engine")
BRANCH = sys.argv[1] if len(sys.argv) > 1 else "venice/sec-options-pipelines"
API = "https://api.github.com/repos/" + REPO
TITLE = "Venice: failed no-AI pipeline runs"

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

def getjson(path):
    status, blob = api(path)
    try:
        return status, json.loads(blob)
    except Exception:
        return status, None

def stop(msg):
    print("reporter:", msg)
    sys.exit(0)

status, runs = getjson("/actions/runs?branch=" + urllib.parse.quote(BRANCH, safe="") + "&status=failure&per_page=50")
if not isinstance(runs, dict):
    stop("runs query failed status " + str(status))
keys = ("nai-sec-", "nai-occ-oi-daily")
hits = [r for r in (runs.get("workflow_runs") or []) if any(k in (r.get("name") or "") for k in keys)]
if not hits:
    stop("no matching failed run")
rid = hits[0].get("id")

status, issues = getjson("/issues?state=open&per_page=100")
if not isinstance(issues, list):
    stop("issue lookup failed status " + str(status))
num = None
for it in issues:
    if it.get("title") == TITLE and "pull_request" not in it:
        num = it.get("number")
        break
if not num:
    stop("no tracking issue")

status, cmts = getjson("/issues/" + str(num) + "/comments?per_page=100&sort=created&direction=desc")
if not isinstance(cmts, list):
    stop("comment lookup failed status " + str(status))
needle = str(rid)
for c in cmts:
    if needle in (c.get("body") or ""):
        print("already reported", rid)
        sys.exit(0)

status, run = getjson("/actions/runs/" + str(rid))
if not isinstance(run, dict):
    stop("run read failed status " + str(status))
status, jobs = getjson("/actions/runs/" + str(rid) + "/jobs")
listing = (jobs or {}).get("jobs") or []
first = listing[0] if listing else {}
failed = [s.get("name") for s in (first.get("steps") or []) if s.get("conclusion") == "failure"]

tail = "[log unavailable]"
try:
    status, blob = api("/actions/runs/" + str(rid) + "/logs")
    archive = zipfile.ZipFile(io.BytesIO(blob))
    text = ""
    for name in archive.namelist():
        text += archive.read(name).decode("utf-8", "replace")
    tail = text[-1500:]
except Exception:
    pass

body = "Run [" + str(run.get("name")) + " " + str(rid) + "](" + str(run.get("html_url")) + ") - " + str(run.get("conclusion") or "unknown") + "\n\nFailing job: " + str(first.get("name") or "n/a") + "\nFailing step: " + (", ".join(failed) if failed else "n/a") + "\n\n" + tail + "\n\nPosted automatically."
status, out = api("/issues/" + str(num) + "/comments", "POST", {"body": body})
print(status, out[:200].decode("utf-8", "replace"))
sys.exit(0)
