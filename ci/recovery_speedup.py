"""Apply the explicitly authorized six-way restart without repeating successes."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
from ci.native_price_recovery import api
from ci.release_assets import gh_retry

REQUEST=Path("ci/RECOVERY_SPEEDUP_REQUEST.json")


def remaining(request,run,jobs):
    if (run["id"],run["head_sha"],run["run_attempt"])!=(request["source_run"],request["source_head"],request["source_attempt"]):
        raise ValueError("speed-up source identity differs")
    if run["status"]!="completed":raise ValueError("source must be terminal before replacement planning")
    names={}
    for job in jobs:
        match=re.fullmatch(r"build \((\d+)\)",job["name"])
        if match:
            shard=int(match[1])
            if shard in names:raise ValueError("ambiguous speed-up source shard")
            names[shard]=job
    preserve=[];replace=[];cancelled=[]
    for shard in request["shards"]:
        job=names.get(shard,{})
        if job.get("status")!="completed":raise ValueError("source shard is missing or still live")
        if job["conclusion"]=="success":preserve.append(shard)
        elif job["conclusion"] in ("failure","cancelled"):
            replace.append(shard)
            if job["conclusion"]=="cancelled":cancelled.append(shard)
        else:raise ValueError("source shard has unsupported terminal state")
    return preserve,replace,cancelled


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True)
    root=Path(parser.parse_args().directory);root.mkdir(parents=True,exist_ok=True)
    request=json.loads(REQUEST.read_text());repository=os.environ["GITHUB_REPOSITORY"]
    endpoint=f"repos/{repository}/actions/runs/{request['source_run']}"
    run=api(endpoint)
    if (run["head_sha"],run["run_attempt"],run["path"])!=(request["source_head"],request["source_attempt"],".github/workflows/native_price_recovery.yml"):
        raise ValueError("refusing to cancel an unrecognized source run")
    if run["status"]!="completed":
        try:gh_retry("api",endpoint+"/cancel","--method","POST")
        except subprocess.CalledProcessError as exc:
            if "HTTP 409" not in str(exc.stderr or "") or api(endpoint)["status"]!="completed":raise
        for _ in range(60):
            time.sleep(5);run=api(endpoint)
            if run["status"]=="completed":break
    jobs=api(endpoint+"/jobs?per_page=100")
    if jobs["total_count"]!=len(jobs["jobs"]):raise ValueError("incomplete source jobs")
    preserve,replace,cancelled=remaining(request,run,jobs["jobs"])
    replacement={"version":4,"source_run":run["id"],"source_run_sha":run["head_sha"],"source_run_attempt":run["run_attempt"],
                 "inputs_tag":request["inputs_tag"],"resume_prefix":f"native-price-blocks-v1-{run['id']}-{run['run_attempt']}",
                 "additional_resume_prefixes":request["additional_resume_prefixes"],"shards":replace,
                 "allowed_cancelled_shards":cancelled,"request":request["authorization"]}
    report={"source_run":run["id"],"source_head":run["head_sha"],"preserved_completed_shards":preserve,
            "replacement_shards":replace,"replacement_request":replacement,"parallelism":6,"old_assets_modified":False}
    if replace:
        identifier="speedup-"+os.environ["GITHUB_RUN_ID"]
        payload={"ref":"main","inputs":{"request_json":json.dumps(replacement),"recovery_id":identifier}}
        file=root/"dispatch.json";file.write_text(json.dumps(payload))
        gh_retry("api",f"repos/{repository}/actions/workflows/native_price_recovery.yml/dispatches","--method","POST","--input",file)
        for _ in range(24):
            runs=api(f"repos/{repository}/actions/workflows/native_price_recovery.yml/runs?event=workflow_dispatch&branch=main&per_page=10")
            matches=[r for r in runs["workflow_runs"] if r["display_title"]=="native-recovery-workflow_dispatch-"+identifier]
            if len(matches)>1:raise ValueError("ambiguous replacement dispatch")
            if matches:
                new=matches[0];report.update(replacement_run=new["id"],replacement_head=new["head_sha"],replacement_attempt=new["run_attempt"]);break
            time.sleep(5)
        else:raise ValueError("replacement dispatch not visible; inspect before another dispatch")
    (root/"RECOVERY_SPEEDUP_HANDOFF.json").write_text(json.dumps(report,indent=2)+"\n")
    print("RECOVERY_SPEEDUP_HANDOFF",json.dumps(report),flush=True)


if __name__=="__main__":main()
