"""Read one actions run and commit its verdict. No logs access needed.

Usage: python scripts/nai/probe_result.py <run_id>
Writes agent/RESULT.json and leaves committing to the workflow.
"""
import json, os, subprocess, sys, urllib.request

API = "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GH_TOKEN"]

def api(path, raw=False):
req = urllib.request.Request(API + path, headers={
"Authorization": "Bearer " + TOKEN,
"Accept": "application/vnd.github+json",
"X-GitHub-Api-Version": "2022-11-28",
})
with urllib.request.urlopen(req, timeout=60) as r:
data = r.read()
return data if raw else json.loads(data)

def main():
run_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["RUN_ID"]
run = api("/actions/runs/" + run_id)
jobs = api("/actions/runs/" + run_id + "/jobs")

tail = ""
try:
    blob = api("/actions/runs/" + run_id + "/logs", raw=True)
    open("/tmp/logs.zip", "wb").write(blob)
    out = subprocess.run(["unzip", "-p", "/tmp/logs.zip", "*.txt"],
                         capture_output=True)
    tail = out.stdout.decode("utf-8", "replace")[-4096:]
except Exception as exc:
    tail = "log fetch failed: %r" % (exc,)

verdict = {
    "run": {
        "id": run.get("id"),
        "name": run.get("name"),
        "branch": run.get("head_branch"),
        "sha": run.get("head_sha"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "html_url": run.get("html_url"),
    },
    "jobs": [
        {
            "name": j.get("name"),
            "conclusion": j.get("conclusion"),
            "failed_steps": [s.get("name") for s in j.get("steps", [])
                             if s.get("conclusion") == "failure"],
        }
        for j in jobs.get("jobs", [])
    ],
    "log_tail": tail,
}
os.makedirs("agent", exist_ok=True)
with open("agent/RESULT.json", "w") as f:
    json.dump(verdict, f, indent=1)
print(json.dumps({"run": verdict["run"]["name"],
                  "conclusion": verdict["run"]["conclusion"]}))

if name == "main":
main()
