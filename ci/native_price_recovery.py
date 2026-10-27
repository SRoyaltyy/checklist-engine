"""Recover explicitly failed native shards without duplicating live work."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from ci.release_assets import gh_retry


REQUEST = Path("ci/NATIVE_PRICE_RECOVERY_REQUEST.json")


def validate_failed_shards(request, run, jobs):
    shards = request["shards"]
    if not shards or len(shards) != len(set(shards)) or any(type(s) is not int or not 0 <= s < 64 for s in shards):
        raise ValueError("expected unique requested shards in 0..63")
    if run["head_sha"] != request["source_run_sha"]:
        raise ValueError("source run head differs")
    expected = request["source_run"]
    if run["id"] != expected or run["run_attempt"] != request["source_run_attempt"]:
        raise ValueError("source run or attempt differs")
    names = {}
    for job in jobs:
        match = re.fullmatch(r"build \((\d+)\)", job["name"])
        if match:
            shard = int(match[1])
            if shard in names:
                raise ValueError("ambiguous source shard jobs")
            names[shard] = job
    proof = []
    for shard in shards:
        job = names.get(shard)
        allowed = {"failure", "cancelled"} if shard in request.get("allowed_cancelled_shards", []) else {"failure"}
        if not job or job["status"] != "completed" or job["conclusion"] not in allowed:
            raise ValueError(f"refusing to duplicate nonfailed/live source shard {shard}")
        proof.append({"shard": shard, "source_job_id": job["id"], "conclusion": job["conclusion"]})
    return proof


def api(endpoint):
    output = gh_retry("api", endpoint)
    return json.loads(output)


def plan(request, directory):
    repository = os.environ["GITHUB_REPOSITORY"]
    groups = {}
    for shard in request["shards"]:
        source = dict(request, **request.get("source_overrides", {}).get(str(shard), {}))
        key = (source["source_run"], source["source_run_sha"], source["source_run_attempt"])
        groups.setdefault(key, []).append(shard)
    proof = []
    for (run_id, head, attempt), shards in groups.items():
        endpoint = f"repos/{repository}/actions/runs/{run_id}"
        run = api(endpoint);jobs = api(endpoint + "/jobs?per_page=100")
        if jobs["total_count"] != len(jobs["jobs"]):
            raise ValueError("source job listing is not complete")
        source = dict(request, source_run=run_id, source_run_sha=head, source_run_attempt=attempt, shards=shards)
        proof.extend(dict(row, source_run=run_id) for row in validate_failed_shards(source, run, jobs["jobs"]))
    directory.mkdir(parents=True, exist_ok=True)
    report = {"status": "TARGETED_FAILED_SHARD_RECOVERY_ONLY", "request": request,
              "source_jobs": proof, "live_source_shards_untouched": True,
              "recipe_file_changed": False, "full_world_gate": "NOT_RUN"}
    (directory / "RECOVERY_PLAN.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write("shards=" + json.dumps(request["shards"]) + "\n")
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("plan", "build"))
    parser.add_argument("--directory", required=True)
    parser.add_argument("--shard", type=int)
    args = parser.parse_args();request = json.loads(os.environ.get("NATIVE_RECOVERY_REQUEST_JSON") or REQUEST.read_text())
    if args.operation == "plan":
        plan(request, Path(args.directory))
        return
    if args.shard not in request["shards"]:
        raise ValueError("unrequested recovery shard")
    environment = dict(os.environ, NATIVE_RESUME_PREFIXES=json.dumps(request.get("additional_resume_prefixes", [])))
    subprocess.run([sys.executable, "-m", "ci.native_price_run", "build", "--directory", args.directory,
                    "--inputs-tag", request["inputs_tag"], "--shard", str(args.shard),
                    "--resume-prefix", request["resume_prefix"]], check=True, env=environment)


if __name__ == "__main__":
    main()
