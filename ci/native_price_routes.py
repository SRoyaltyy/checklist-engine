"""Pure-stdlib validation for the exact 64 immutable native source routes."""
import os,re
from ci.native_price_recovery import api


def validate_source(source,run,jobs):
    if source["prefix"]!=f"native-price-blocks-v1-{source['run']}-{source['attempt']}":
        raise ValueError("native source release prefix differs from run")
    if (run["id"],run["head_sha"],run["run_attempt"])!=(source["run"],source["head"],source["attempt"]):
        raise ValueError("native stitch source run identity differs")
    selected={};proof=[]
    for job in jobs:
        match=re.fullmatch(r"build \((\d+)\)",job["name"])
        if not match:continue
        shard=int(match[1])
        if shard in selected:raise ValueError("ambiguous native source jobs")
        selected[shard]=job
    for shard in source["shards"]:
        job=selected.get(shard,{})
        if job.get("status")!="completed" or job.get("conclusion")!="success":
            raise ValueError(f"native source shard {shard} has not succeeded")
        proof.append({"shard":shard,"source_run":source["run"],"source_head":source["head"],"source_attempt":source["attempt"],
                      "source_job":job["id"],"release":source["prefix"]+f"-{shard:03d}"})
    return proof


def source_plan(request):
    shards=[s for source in request["sources"] for s in source["shards"]]
    if any(type(s) is not int for s in shards) or sorted(shards)!=list(range(64)):
        raise ValueError("native stitch must route each of 64 shards exactly once")
    proof=[]
    for source in request["sources"]:
        endpoint=f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{source['run']}"
        run=api(endpoint);jobs=api(endpoint+"/jobs?per_page=100")
        if len(jobs["jobs"])!=jobs["total_count"]:raise ValueError("incomplete native source job listing")
        proof.extend(validate_source(source,run,jobs["jobs"]))
    return sorted(proof,key=lambda r:r["shard"])
