"""Mark only terminal request-only recovery releases as incomplete drafts."""
import argparse,json,os
from pathlib import Path
import subprocess
from ci.release_assets import asset_index,gh_retry


def mark_empty(tag,assets):
    if set(assets)-{"SHARD_REQUEST.json"}:
        return {"release":tag,"status":"PRESERVED_HAS_DATA_OR_OTHER_EVIDENCE"}
    gh_retry("release","edit",tag,"--draft=true","--notes",
             "INCOMPLETE REQUEST-ONLY RECOVERY: no price data was produced. Preserved for audit; not usable for coverage or scoring. Superseded by corrected recovery.")
    return {"release":tag,"status":"MARKED_INCOMPLETE_DRAFT","assets_preserved":sorted(assets)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True)
    root=Path(parser.parse_args().directory);root.mkdir(parents=True,exist_ok=True)
    request=json.loads(Path("ci/EMPTY_RECOVERY_MARK_REQUEST.json").read_text())
    endpoint=f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{request['source_run']}"
    source=json.loads(gh_retry("api",endpoint))
    if source["status"]!="completed" or source["head_sha"]!=request["source_sha"]:
        raise ValueError("source recovery is live or its commit differs")
    results=[]
    for shard in request["shards"]:
        tag=request["prefix"]+f"-{shard:03d}"
        try:results.append(mark_empty(tag,asset_index(tag)))
        except subprocess.CalledProcessError as exc:
            if "HTTP 404" not in str(exc.stderr or ""):raise
            results.append({"release":tag,"status":"ABSENT_NOT_CREATED"})
    report={"source_run":request["source_run"],"results":results,"price_assets_deleted":False}
    (root/"EMPTY_RECOVERY_MARKING.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report),flush=True)


if __name__=="__main__":main()
