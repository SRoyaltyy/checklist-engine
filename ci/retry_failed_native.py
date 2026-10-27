"""Dispatch only an explicitly audited failed subset; leave live jobs untouched."""
import argparse,hashlib,json,os,re,time
from pathlib import Path
from ci.native_price_recovery import api,validate_failed_shards
from ci.release_assets import gh_retry


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True)
    root=Path(parser.parse_args().directory);root.mkdir(parents=True,exist_ok=True)
    request=json.loads(Path("ci/NATIVE_FAILED_RETRY_REQUEST.json").read_text())
    repository=os.environ["GITHUB_REPOSITORY"];endpoint=f"repos/{repository}/actions/runs/{request['source_run']}"
    run=api(endpoint);jobs=api(endpoint+"/jobs?per_page=100")
    if jobs["total_count"]!=len(jobs["jobs"]):raise ValueError("incomplete failed-source job listing")
    proof=validate_failed_shards(request,run,jobs["jobs"])
    live=[j["name"] for j in jobs["jobs"] if j["status"]!="completed" and re.fullmatch(r"build \(\d+\)",j["name"])]
    identifier="draft-fix-"+hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:20]
    listing=f"repos/{repository}/actions/workflows/native_price_recovery.yml/runs?event=workflow_dispatch&branch=main&per_page=100"
    def existing():
        matches=[];page=1
        while True:
            runs=api(listing+f"&page={page}")["workflow_runs"]
            matches.extend(r for r in runs if r["display_title"]=="native-recovery-workflow_dispatch-"+identifier)
            if len(runs)<100:break
            page+=1
        if len(matches)>1:raise ValueError("ambiguous failed-only replacement")
        return matches[0] if matches else None
    new=existing()
    if new is None:
        payload={"ref":"main","inputs":{"request_json":json.dumps(request),"recovery_id":identifier}}
        file=root/"dispatch.json";file.write_text(json.dumps(payload))
        gh_retry("api",f"repos/{repository}/actions/workflows/native_price_recovery.yml/dispatches","--method","POST","--input",file)
        for _ in range(24):
            new=existing()
            if new:break
            time.sleep(5)
        else:raise ValueError("replacement not yet visible; inspect dispatch before retrying")
    report={"source_run":run["id"],"source_jobs":proof,"live_source_jobs_untouched":live,"request":request,
            "replacement_run":new["id"],"replacement_head":new["head_sha"],"replacement_attempt":new["run_attempt"],"parallelism":6,"old_assets_modified":False}
    (root/"FAILED_NATIVE_RETRY_HANDOFF.json").write_text(json.dumps(report,indent=2)+"\n")
    print("FAILED_NATIVE_RETRY_HANDOFF",json.dumps(report),flush=True)


if __name__=="__main__":main()
