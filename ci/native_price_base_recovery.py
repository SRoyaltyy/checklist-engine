"""Target terminal compact-price failures and stitch explicit source routes."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from ci.native_price_recovery import api,validate_failed_shards

REQUEST=Path("ci/NATIVE_PRICE_BASE_RECOVERY_REQUEST.json")


def plan(request,directory):
    prerequisite=api(f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{request['prerequisite_native_run']}")
    if prerequisite["head_sha"]!=request["prerequisite_native_sha"] or prerequisite["status"]!="completed" or prerequisite["conclusion"]!="success":
        raise ValueError("required native recovery has not completed successfully at its pinned commit")
    native_proof=[]
    if request.get("require_all_native_sources") is True:
        from ci.native_price_routes import source_plan
        native_proof=source_plan(json.loads(Path("ci/NATIVE_PRICE_STITCH_REQUEST.json").read_text()))
    endpoint=f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{request['source_run']}"
    run=api(endpoint);jobs=api(endpoint+"/jobs?per_page=100")
    if len(jobs["jobs"])!=jobs["total_count"]:raise ValueError("incomplete source job listing")
    if request["shards"]!=[13,14,15]:raise ValueError("only audited failed compact shards may be recovered")
    proof=validate_failed_shards(request,run,jobs["jobs"])
    directory.mkdir(parents=True,exist_ok=True)
    report={"request":request,"source_jobs":proof,"native_source_jobs":native_proof,
            "successful_shards_preserved":list(range(13)),"full_world_gate":"NOT_RUN"}
    (directory/"BASE_RECOVERY_PLAN.json").write_text(json.dumps(report,indent=2)+"\n")
    with open(os.environ["GITHUB_OUTPUT"],"a") as stream:stream.write("shards="+json.dumps(request["shards"])+"\n")
    print(json.dumps(report),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("operation",choices=("plan","build","merge"))
    parser.add_argument("--directory",required=True);parser.add_argument("--shard",type=int)
    args=parser.parse_args();request=json.loads(REQUEST.read_text());root=Path(args.directory)
    if args.operation=="plan":plan(request,root);return
    command=[sys.executable,"-m","ci.native_price_base_run",args.operation,"--directory",str(root),"--inputs-tag",request["inputs_tag"]]
    if args.operation=="build":
        if args.shard not in request["shards"]:raise ValueError("unrequested compact shard")
        command += ["--shard",str(args.shard),"--resume-prefix",request["resume_prefix"]]
    else:
        root.mkdir(parents=True,exist_ok=True)
        prefix=f"native-price-base-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
        routes={str(n):prefix+f"-{n:03d}" for n in request["shards"]}
        route_file=root/"BASE_SHARD_ROUTES.json";route_file.write_text(json.dumps(routes,indent=2)+"\n")
        command += ["--build-prefix",request["resume_prefix"],"--routes",str(route_file)]
    subprocess.run(command,check=True)


if __name__=="__main__":main()
