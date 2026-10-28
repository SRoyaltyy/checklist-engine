"""Verify and route immutable native completions into the frozen merge recipe."""
import argparse,json,os,re
from pathlib import Path
from types import SimpleNamespace
from ci import native_price_blocks as builder
from ci.native_price_recovery import api
from ci.native_price_routes import source_plan,validate_source
from ci.release_assets import asset_index,download_asset,gh_retry,publish_assets

REQUEST=Path("ci/NATIVE_PRICE_STITCH_REQUEST.json")


def compact_prerequisite(run_id,request,root):
    run=api(f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}")
    if run["path"]!=".github/workflows/native_price_base_recovery.yml" or run["event"]=="pull_request" or run["status"]!="completed" or run["conclusion"]!="success":
        raise ValueError("compact recovery workflow has not completed successfully")
    tag=f"native-price-base-coverage-v1-{run_id}-{run['run_attempt']}"
    file=download_asset(tag,"NATIVE_PRICE_BASE_STATUS_V1.json",root)
    status=json.loads(file.read_text())
    if status["status"]!="FULL_ACCEPTED_PRICE_BASE_ONLY_NOT_WORLD" or status["inputs_tag"]!=request["inputs_tag"]:
        raise ValueError("compact coverage input/status differs")
    for name,key in (("NATIVE_PRICE_BASE_COVERAGE_V1.csv","coverage_sha256"),("PRICE_BASE_STOCK_DAY_WEIGHTS_V1.csv","stock_day_weights_sha256")):
        if builder.sha(download_asset(tag,name,root))!=status[key]:raise ValueError("compact coverage digest differs")
    return tag,status


def stitch(request,proof,base_tag,base_status,root):
    routes={f"native-price-source-route-{r['shard']:03d}":r["release"] for r in proof}
    inventories={};archive_bytes={}
    original=builder.download,builder.gh

    def inventory(tag):
        if tag not in inventories:inventories[tag]=asset_index(tag)
        return inventories[tag]

    def download(tag,name,directory):
        if name=="SHARD_COMPLETE.json":
            if tag not in routes:raise ValueError("unrouted native shard completion")
            tag=routes[tag]
        file=download_asset(tag,name,directory)
        if name=="SHARD_COMPLETE.json":
            report=json.loads(file.read_text())
            if report["status"]!="ALL_SELECTED_PRICE_ENTITIES_BUILT_NOT_WORLD":raise ValueError("native completion status differs")
            if not tag.endswith(f"-{report['shard']:03d}"):raise ValueError("native completion shard differs")
        if re.fullmatch(r"part_\d+\.json",name):
            report=json.loads(file.read_text());assets=inventory(tag);stem=name[:-5]
            for suffix,key in ((".tar","archive_sha256"),(".coverage.csv","coverage_sha256")):
                asset=assets.get(stem+suffix,{})
                if asset.get("state")!="uploaded" or asset.get("digest")!="sha256:"+report[key]:raise ValueError("native remote part digest differs")
            archive_bytes[(tag,stem)]=assets[stem+".tar"]["size"]
        return file

    def publish(*args):
        if args[:2]!=("release","create"):return gh_retry(*args)
        tag=args[2];coverage,status_file=map(Path,args[3:5])
        status=json.loads(status_file.read_text())
        if (status["selected_tickers"],status["query_rows"],status["recipe_fingerprint"],set(status["timeframes"]))!=(
                base_status["selected_tickers"],base_status["query_rows"],base_status["recipe_fingerprint"],set(base_status["timeframes"])):
            raise ValueError("native/compact universe, stock-day denominator or recipe differs")
        status.update(shard_sources=proof,compact_coverage_release=base_tag,compact_coverage_sha256=base_status["coverage_sha256"],
                      unique_archive_bytes=sum(archive_bytes.values()),recipe_review_gate="CLOSED_PENDING_PR13_MATH_REVIEW",
                      stitch_code_sha256=builder.sha(__file__))
        builder.write_json(status_file,status)
        gh_retry("release","create",tag,"--draft",*args[5:])
        publish_assets(tag,coverage,status_file,root/"NATIVE_STITCH_SOURCE_PLAN.json")
        gh_retry("release","edit",tag,"--draft=false")

    builder.download=download;builder.gh=publish
    try:builder.merge(SimpleNamespace(directory=str(root),inputs_tag=request["inputs_tag"],build_prefix="native-price-source-route"))
    finally:builder.download,builder.gh=original


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);parser.add_argument("--base-run",required=True,type=int)
    args=parser.parse_args();root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    request=json.loads(REQUEST.read_text());base_tag,base_status=compact_prerequisite(args.base_run,request,root/"compact")
    proof=source_plan(request)
    builder.write_json(root/"NATIVE_STITCH_SOURCE_PLAN.json",{"request":request,"source_jobs":proof,"compact_release":base_tag,"scoring_gate":"CLOSED"})
    stitch(request,proof,base_tag,base_status,root)


if __name__=="__main__":main()
