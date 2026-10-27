"""Acquire official structured SEC bulk sources through the mandatory relay."""
import argparse,hashlib,io,json,os,re,urllib.parse,zipfile
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from fetch.sec_client import get_bytes
from ci.release_assets import describe_failure,gh_retry,publish_assets

PAGES={
    "form4":"https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets",
    "13f":"https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets",
    "xbrl":"https://www.sec.gov/dera/data/financial-statement-data-sets.html",
}


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            for key,value in attrs:
                if key=="href" and value:self.links.append(value)


def source_links(html,page,start=2018,end=2026):
    parser=Links();parser.feed(html);out=[]
    for link in parser.links:
        url=urllib.parse.urljoin(page,link);parts=urllib.parse.urlsplit(url)
        years=[int(y) for y in re.findall(r"(?:19|20)\d{2}",Path(parts.path).name)]
        if parts.scheme!="https" or parts.hostname not in ("sec.gov","www.sec.gov") or not parts.path.lower().endswith(".zip"):continue
        if parts.username or parts.password or parts.query or parts.fragment:raise ValueError("unexpected SEC bulk URL")
        if not years or max(years)<start or min(years)>end:continue
        out.append(url)
    if not out:raise ValueError("official SEC page returned no bulk ZIP sources in the requested years")
    return sorted(set(out))


def inspect_zip(raw):
    if not raw or len(raw)>=1_900_000_000:raise ValueError("empty or oversized SEC bulk archive")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members=archive.infolist()
        if not members or any(m.flag_bits&1 for m in members):raise ValueError("empty/encrypted SEC bulk archive")
        if sum(m.file_size for m in members)>8_000_000_000:raise ValueError("SEC archive expansion exceeds runner bound")
        if archive.testzip() is not None:raise ValueError("SEC archive CRC verification failed")
        tables=[]
        for member in members:
            if member.is_dir():continue
            path=Path(member.filename)
            if path.is_absolute() or ".." in path.parts:raise ValueError("unsafe SEC archive member")
            if path.suffix.lower() not in (".tsv",".txt"):continue
            with archive.open(member) as stream:
                header=stream.readline(65536).decode("utf-8-sig",errors="strict").rstrip("\r\n").split("\t")
                if len(header)<2:continue
                count=0;last=b""
                for chunk in iter(lambda:stream.read(1<<20),b""):
                    count+=chunk.count(b"\n");last=chunk[-1:]
                if last and last!=b"\n":count+=1
            tables.append({"name":member.filename,"rows_after_header":count,"columns":header,"uncompressed_bytes":member.file_size,"crc32":member.CRC})
        if not tables or not any(t["rows_after_header"]>0 for t in tables):raise ValueError("SEC archive has no populated structured tables")
        return tables


def acquire(dataset,root):
    root.mkdir(parents=True,exist_ok=True);page=PAGES[dataset]
    report={"dataset":dataset,"landing_page":page,"source_commit":os.environ.get("GITHUB_SHA"),"files":[],
            "requested_start_year":2018,"requested_end_year":2026,"status":"INCOMPLETE_SOURCE_ONLY",
            "point_in_time_join":"NOT_RUN; retain accession and filed/acceptance fields, never use reporting period as availability",
            "latest_session_coverage":"NOT_PROVEN; bulk windows end before the current session and require incremental filings",
            "world_gate":"NOT_RUN","scoring_gate":"CLOSED","free_text_features":False}
    tag=f"sec-bulk-{dataset}-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}";created=False
    try:
        html=get_bytes(page).decode("utf-8");urls=source_links(html,page)
        report["requested_urls"]=urls
        for url in urls:
            raw=get_bytes(url);tables=inspect_zip(raw)
            file=root/Path(urllib.parse.urlsplit(url).path).name;file.write_bytes(raw)
            receipt={"url":url,"fetched_at":datetime.now(timezone.utc).isoformat(),"bytes":len(raw),
                     "sha256":hashlib.sha256(raw).hexdigest(),"tables":tables,"scope":"RAW_STRUCTURED_SOURCE_NOT_WORLD_OR_PIT_ACCEPTANCE"}
            meta=root/(file.name+".json");meta.write_text(json.dumps(receipt,indent=2)+"\n")
            if not created:
                gh_retry("release","create",tag,"--draft","--target",os.environ["GITHUB_SHA"],"--title",tag,
                         "--notes","Official structured SEC bulk acquisition via relay; raw source only. Latest-session, point-in-time joins and world coverage remain unverified.")
                created=True
            publish_assets(tag,file,meta);gh_retry("release","edit",tag,"--draft=false")
            report["files"].append({"name":file.name,"url":url,"bytes":len(raw),"sha256":receipt["sha256"],"tables":len(tables),"table_rows":sum(t["rows_after_header"] for t in tables)})
            (root/"SEC_BULK_STATUS.json").write_text(json.dumps(report,indent=2)+"\n")
            file.unlink();meta.unlink();del raw
            print("SEC_BULK_DURABLE",dataset,url,report["files"][-1]["table_rows"],flush=True)
        report["status"]="PUBLISHED_BULK_WINDOWS_FETCHED_SOURCE_ONLY";report["release"]=tag
    except Exception as exc:
        report["error"]=getattr(exc,"evidence",{"message":describe_failure(exc)})
        raise
    finally:
        status=root/"SEC_BULK_STATUS.json";status.write_text(json.dumps(report,indent=2)+"\n")
        if created:
            try:publish_assets(tag,status)
            except Exception as exc:
                report["status_upload_error"]=describe_failure(exc);status.write_text(json.dumps(report,indent=2)+"\n")
                if report["status"]=="PUBLISHED_BULK_WINDOWS_FETCHED_SOURCE_ONLY":raise
        print("SEC_BULK_RESULT",dataset,report["status"],len(report["files"]),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--dataset",choices=PAGES,required=True);parser.add_argument("--directory",required=True)
    args=parser.parse_args();acquire(args.dataset,Path(args.directory))


if __name__=="__main__":main()
