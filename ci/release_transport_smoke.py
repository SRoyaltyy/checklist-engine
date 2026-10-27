"""Verify real immutable release uploads before launching checkpoint recovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from ci import release_assets as transport
from ci.release_assets import gh_retry, publish_assets, asset_index, download_asset,release_info


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True)
    root=Path(parser.parse_args().directory);root.mkdir(parents=True,exist_ok=True)
    tag=f"release-transport-smoke-v3-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    data=root/"fixture.bin";data.write_bytes(b"immutable release transport fixture\x00\x01")
    coverage=root/"fixture.csv";coverage.write_text("name,rows\nfixture,1\n",encoding="utf-8")
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=root/"fixture.json"
    manifest.write_text(json.dumps({p.name:digest(p) for p in (data,coverage)},indent=2)+"\n",encoding="utf-8")
    files=[data,coverage,manifest]
    gh_retry("release","create",tag,"--draft","--target",os.environ["GITHUB_SHA"],"--title",tag,
             "--notes","Release transport fixture only; no market-data or world-coverage claim.")
    publish_assets(tag,*files)
    publish_assets(tag,*files)  # Must reuse identical completed bytes, never clobber.
    if not release_info(tag)["draft"]:raise ValueError("draft smoke published before verification")
    for file in files:
        if digest(download_asset(tag,file.name,root/"draft-download-check"))!=digest(file):raise ValueError("draft asset bytes differ")
    gh_retry("release","edit",tag,"--draft=false")
    transport._DOWNLOAD_INVENTORIES.pop((os.environ["GITHUB_REPOSITORY"],tag),None)
    assets=asset_index(tag)
    if set(assets)!={p.name for p in files}:
        raise ValueError("smoke asset inventory differs")
    for file in files:
        if assets[file.name]["size"]!=file.stat().st_size or assets[file.name].get("digest")!="sha256:"+digest(file):
            raise ValueError("smoke asset fingerprint differs")
        downloaded=download_asset(tag,file.name,root/"download-check")
        if digest(downloaded)!=digest(file):raise ValueError("public asset bytes differ")
    report={"status":"PASS_TRANSPORT_ONLY_NOT_WORLD","release":tag,"source_commit":os.environ["GITHUB_SHA"],
            "transport_code_sha256":digest(Path("ci/release_assets.py")),
            "verified_assets":{p.name:digest(p) for p in files},"identical_second_upload_reused":True,
            "public_downloads_verified":True,
            "draft_upload_and_authenticated_download_verified":True,
            "world_gate":"NOT_RUN"}
    output=root/"TRANSPORT_SMOKE_STATUS.json";output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    publish_assets(tag,output)
    print(json.dumps(report),flush=True)


if __name__=="__main__":main()
