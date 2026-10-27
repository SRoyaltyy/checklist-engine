"""Publish compact daily/execution/native-OHLCV inputs for context joins.

Reuses the exact prepared inputs of the large price-feature build. Never
re-downloads prices from vendors and never changes excluded tickers or bars.
"""
import argparse,csv,hashlib,io,json,os,re,shutil,tarfile,time
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from price_reconcile import reconcile_one
from world_timeframes import TIMEFRAMES,PRICE_COLS,completed_candles
from ci.native_price_blocks import download,source_archive,read_member,sha,gh,write_json,recipe_fingerprint,measure_availability,add_metrics,CUTOFF
from ci.release_assets import publish_assets,describe_failure,asset_index


def recover_base_parts(tag,inputs,selected,directory):
    """Reuse complete compact parts without fetching their large archives."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    assets=asset_index(tag);parts=[];records=[];seen=set();skipped=[]
    for name in sorted(n for n in assets if re.fullmatch(r"base_\d+\.json",n)):
        stem=name[:-5]
        required=[name,stem+".tar",stem+".coverage.csv",stem+".stock_days.csv"]
        if any(n not in assets or assets[n]["state"]!="uploaded" for n in required):
            skipped.append(stem);continue
        file=download(tag,name,directory)
        if assets[name].get("digest")!="sha256:"+sha(file):raise ValueError("base checkpoint manifest digest differs")
        report=json.loads(file.read_text())
        if report["status"]!="PRICE_BASE_PART_ONLY_NOT_WORLD":raise ValueError("base checkpoint status differs")
        if report["inputs_tag"]!=inputs["inputs_tag"] or report["recipe_fingerprint"]!=inputs["recipe_fingerprint"]:
            raise ValueError("base checkpoint recipe/input differs")
        for suffix,key in ((".tar","archive_sha256"),(".coverage.csv","coverage_sha256"),(".stock_days.csv","stock_days_sha256")):
            if assets[stem+suffix].get("digest")!="sha256:"+report[key]:raise ValueError("base checkpoint asset digest differs")
        tickers=[r["ticker"] for r in report["records"]]
        if not tickers or len(tickers)!=len(set(tickers)) or seen&set(tickers) or not set(tickers)<=selected:
            raise ValueError("base checkpoint membership differs")
        if not report.get("members") or sum(r["query_rows"] for r in report["records"])!=report["query_rows"]:
            raise ValueError("base checkpoint records incomplete")
        names=[m["name"] for m in report["members"]]
        required={ticker.encode().hex()+suffix for ticker in tickers for suffix in (".bars.parquet",".execution.parquet",".native.parquet")}
        if len(names)!=len(set(names)) or not required<=set(names):raise ValueError("base checkpoint entity files incomplete")
        if any(set(r["native_rows"])!=set(TIMEFRAMES) or any(n<=0 for n in r["native_rows"].values()) for r in report["records"]):
            raise ValueError("base checkpoint native grid differs")
        seen.update(tickers);records.extend(report["records"])
        parts.append(dict(part=stem,release=tag,tickers=tickers,**{key:report[key] for key in ("archive_sha256","coverage_sha256","stock_days_sha256")}))
    write_json(Path(directory)/"BASE_RESUME.json",{"source_release":tag,"completed_parts":len(parts),"completed_entities":len(records),"skipped_incomplete":skipped})
    return parts,records


def verify_base_asset_digests(part,assets):
    for suffix,key in ((".tar","archive_sha256"),(".coverage.csv","coverage_sha256"),(".stock_days.csv","stock_days_sha256")):
        asset=assets.get(part["part"]+suffix,{})
        if asset.get("state")!="uploaded" or asset.get("digest")!="sha256:"+part[key]:
            raise ValueError("compact part remote asset differs")

def execution_rows(bars):
    """Separate execution-only D-open from every historical feature column."""
    q=bars[bars.date>=pd.Timestamp("2020-01-01")]
    return q[["ticker","date","open"]].rename(columns={"open":"execution_open_reference_units"}).reset_index(drop=True)

def native_rows(bars,calendar):
    frames=[]
    for tf in TIMEFRAMES:
        frame=completed_candles(bars,tf,session_calendar=calendar)
        if frame.empty:raise ValueError("no completed candles for "+tf)
        if not (frame.date<frame.available_from).all():raise ValueError("native candle exposed too early")
        frame.insert(0,"timeframe",tf);frames.append(frame)
    return pd.concat(frames,ignore_index=True)


def publish_failure(root,tag,failure):
    file=root/"BASE_FAILED.json";write_json(file,failure)
    try:publish_assets(tag,file)
    except Exception as exc:
        failure["failure_report_upload_error"]=describe_failure(exc);write_json(file,failure)
        print("PRICE_BASE_FAILURE_REPORT_LOCAL",str(file),describe_failure(exc),flush=True)

def flush(root,tag,number,records,metrics,date_counts,inputs,receipts):
    current=root/"current";files=sorted(current.iterdir())
    if not records or not files:raise ValueError("empty base part")
    stem=f"base_{number:04d}";archive=root/(stem+".tar")
    size=sum(p.stat().st_size for p in files)
    reserve=7000000000 if 17<=datetime.now(ZoneInfo("Asia/Hong_Kong")).hour<21 else 2000000000
    if shutil.disk_usage(root).free<reserve+size:raise RuntimeError("disk reserve would be breached")
    members=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]
    with tarfile.open(archive,"w") as tar:
        for p in files:tar.add(p,arcname=p.name,recursive=False)
    if archive.stat().st_size>=1900000000:raise ValueError("base part exceeds asset bound")
    coverage=root/(stem+".coverage.csv")
    rows=sorted(metrics.values(),key=lambda r:(r["timeframe"],r["column"]))
    with coverage.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    dates=root/(stem+".stock_days.csv")
    with dates.open("w",newline="") as f:
        writer=csv.writer(f);writer.writerow(["date","stock_days"]);writer.writerows(sorted(date_counts.items()))
    report={"status":"PRICE_BASE_PART_ONLY_NOT_WORLD","inputs_tag":inputs["inputs_tag"],
            "recipe_fingerprint":inputs["recipe_fingerprint"],"source_commit":os.environ["GITHUB_SHA"],
            "base_export_code_sha256":sha(__file__),"archive_sha256":sha(archive),"coverage_sha256":sha(coverage),
            "stock_days_sha256":sha(dates),"members":members,"records":records,"source_receipts":receipts,
            "query_rows":sum(r["query_rows"] for r in records),"execution_price_basis":"frozen reference units, not nominal",
            "historical_tradeability_gate":"NOT_RUN"}
    meta=root/(stem+".json");write_json(meta,report)
    publish_assets(tag,archive,coverage,dates,meta)
    gh("release","edit",tag,"--draft=false")
    for p in files:p.unlink()
    for p in (archive,coverage,dates,meta):p.unlink()
    print("PRICE_BASE_PART_DURABLE",tag,stem,len(records),flush=True)
    return {"part":stem,"release":tag,"tickers":[r["ticker"] for r in records],"archive_sha256":report["archive_sha256"],
            "coverage_sha256":report["coverage_sha256"],"stock_days_sha256":report["stock_days_sha256"]}

def build(args):
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    inputs=json.loads(download(args.inputs_tag,"BUILD_INPUTS.json",root).read_text());inputs["inputs_tag"]=args.inputs_tag
    if recipe_fingerprint()[0]!=inputs["recipe_fingerprint"]:raise ValueError("input recipe differs")
    if inputs["feature_shards"]%16:raise ValueError("prepared shard grid cannot be grouped into 16 source shards")
    records=[r for r in inputs["records"] if int(r["ordinal"])%16==args.shard]
    selected={r["ticker"] for r in records}
    resume_tag=getattr(args,"resume_prefix",None)
    resume_tag=resume_tag+f"-{args.shard:03d}" if resume_tag else None
    prior_parts,prior_records=recover_base_parts(resume_tag,inputs,selected,root/"resume") if resume_tag else ([],[])
    frames=[]
    for n in range(args.shard,inputs["feature_shards"],16):
        name=f"frozen_{n:03d}.parquet";file=download(args.inputs_tag,name,root)
        if sha(file)!=inputs["prepared_shards"][name]["sha256"]:raise ValueError("frozen shard changed")
        frames.append(pd.read_parquet(file));file.unlink()
    frozen=pd.concat(frames,ignore_index=True);old={str(t):g.reset_index(drop=True) for t,g in frozen.groupby("ticker",observed=True)}
    if set(old)!=selected:raise ValueError("frozen/source-shard membership differs")
    file=download(args.inputs_tag,"market_sessions.parquet",root)
    if sha(file)!=inputs["calendar_sha256"]:raise ValueError("calendar changed")
    calendar=pd.DatetimeIndex(pd.read_parquet(file).date)
    tag=f"native-price-base-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{args.shard:03d}"
    request=root/"BASE_REQUEST.json";write_json(request,{"inputs":args.inputs_tag,"selected":len(records),"shard":args.shard,"scope":"PRICE_BASE_ONLY_NOT_WORLD"})
    gh("release","create",tag,request,"--draft","--title",tag,"--notes","Compact verified daily, execution-only open and native OHLCV inputs; not nominal PIT prices or full-world approval.","--target",os.environ["GITHUB_SHA"])
    current=root/"current";current.mkdir(exist_ok=True);stage=root/"entity";stage.mkdir(exist_ok=True)
    groups=defaultdict(list)
    resumed={r["ticker"] for r in prior_records}
    for r in records:groups[r["source_part"]].append(r["ticker"])
    groups={stem:[ticker for ticker in names if ticker not in resumed] for stem,names in groups.items()}
    groups={stem:names for stem,names in groups.items() if names}
    all_records=list(prior_records);parts=list(prior_parts);pending=[];metrics={};dates=Counter();receipts=[];number=0;ticker=None
    try:
        for stem,names in sorted(groups.items()):
            archive,manifest,mhash=source_archive(stem,root/"source")
            for ticker in sorted(names):
                started=time.time();name=ticker.encode().hex()
                new=pd.read_parquet(io.BytesIO(read_member(archive,manifest,name+".parquet")))
                new=new[pd.to_datetime(new.date)<=pd.Timestamp(CUTOFF)]
                event_name=name+".events.parquet"
                events=pd.read_parquet(io.BytesIO(read_member(archive,manifest,event_name))) if any(m["name"]==event_name for m in manifest["members"]) else None
                bars,bridge=reconcile_one(ticker,old[ticker],new,min_overlap=60,allow_short_history=False,events=events)
                if bridge["all_overlap_volumes_zero"] or bridge["supplemental_end"]!=CUTOFF:raise ValueError("rejected/stale source")
                native=native_rows(bars,calendar);execution=execution_rows(bars);own_metrics={}
                for tf,frame in native.groupby("timeframe",sort=False):
                    add_metrics(own_metrics,tf,measure_availability(frame[["available_from",*PRICE_COLS]],execution.date))
                bars.to_parquet(stage/(name+".bars.parquet"),index=False)
                execution.to_parquet(stage/(name+".execution.parquet"),index=False)
                native.to_parquet(stage/(name+".native.parquet"),index=False,compression="zstd")
                if events is not None:events.to_parquet(stage/(name+".events.parquet"),index=False)
                for file in stage.iterdir():file.replace(current/file.name)
                row={"ticker":ticker,"query_rows":len(execution),"first_query":str(execution.date.min())[:10],
                     "last_query":str(execution.date.max())[:10],"native_rows":{str(tf):len(g) for tf,g in native.groupby("timeframe")},
                     "bridge":bridge}
                all_records.append(row);pending.append(row)
                for metric in own_metrics.values():add_metrics(metrics,metric["timeframe"],[metric])
                dates.update(execution.date.dt.strftime("%Y-%m-%d"))
                receipts.append({"source_part":stem,"manifest_sha256":mhash,"archive_sha256":manifest["archive_sha256"]})
                print("PRICE_BASE_ENTITY",ticker,len(execution),round(time.time()-started,2),flush=True)
                size=sum(p.stat().st_size for p in current.iterdir())
                if len(pending)>=50 or size>=250000000:
                    parts.append(flush(root,tag,number,pending,metrics,dates,inputs,receipts))
                    number+=1;pending=[];metrics={};dates=Counter();receipts=[]
            archive.unlink()
        if pending:parts.append(flush(root,tag,number,pending,metrics,dates,inputs,receipts));pending=[]
    except Exception as exc:
        checkpoint_error=None
        if pending:
            try:parts.append(flush(root,tag,number,pending,metrics,dates,inputs,receipts))
            except Exception as ce:checkpoint_error=describe_failure(ce)
        failure={"status":"INCOMPLETE_NOT_WORLD","failed_ticker":ticker,"error":describe_failure(exc),"checkpoint_error":checkpoint_error,"parts":parts}
        publish_failure(root,tag,failure)
        raise
    if {r["ticker"] for r in all_records}!=selected:raise ValueError("incomplete source shard")
    result={"status":"COMPLETE_PRICE_BASE_SHARD_NOT_WORLD","inputs_tag":args.inputs_tag,"recipe_fingerprint":inputs["recipe_fingerprint"],
            "shard":args.shard,"selected":len(selected),"completed":len(all_records),"records":all_records,"parts":parts,"timeframes":list(TIMEFRAMES),
            "query_rows":sum(r["query_rows"] for r in all_records),"source_commit":os.environ["GITHUB_SHA"],
            "checkpoint_sources":[resume_tag] if resume_tag else [],"base_export_code_sha256":sha(__file__),
            "full_world_gate":"NOT_RUN","historical_tradeability_gate":"NOT_RUN"}
    file=root/"BASE_COMPLETE.json";write_json(file,result);publish_assets(tag,file)
    gh("release","edit",tag,"--draft=false")
    print("PRICE_BASE_SHARD_COMPLETE",tag,len(all_records),result["query_rows"],flush=True)

def collect_base_reports(root,inputs,inputs_tag,build_prefix,routes=None):
    """Fail with all upstream shard errors before aggregating any coverage."""
    reports=[];errors=[]
    for shard in range(16):
        tag=(routes or {}).get(str(shard),build_prefix+f"-{shard:03d}");directory=root/str(shard)
        try:
            report=json.loads(download(tag,"BASE_COMPLETE.json",directory).read_text())
            expected={r["ticker"] for r in inputs["records"] if r["ordinal"]%16==shard}
            actual=[r["ticker"] for r in report["records"]]
            if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError("base shard membership differs")
            if report["status"]!="COMPLETE_PRICE_BASE_SHARD_NOT_WORLD" or report["shard"]!=shard:raise ValueError("base shard completion differs")
            if report["selected"]!=len(expected) or report["completed"]!=len(expected):raise ValueError("base shard count differs")
            if report["recipe_fingerprint"]!=inputs["recipe_fingerprint"] or report["inputs_tag"]!=inputs_tag:raise ValueError("base recipe/input differs")
            if set(report["timeframes"])!=set(TIMEFRAMES):raise ValueError("base timeframe grid differs")
            for row in report["records"]:
                if set(row["native_rows"])!=set(TIMEFRAMES) or any(v<=0 for v in row["native_rows"].values()):raise ValueError("missing native grid")
            if sorted(t for p in report["parts"] for t in p["tickers"])!=sorted(expected):raise ValueError("durable part membership differs")
            permitted={tag,*report.get("checkpoint_sources",[])}
            if any(not source.endswith(f"-{shard:03d}") for source in permitted):raise ValueError("base checkpoint source shard differs")
            if any(p["release"] not in permitted for p in report["parts"]):raise ValueError("base part release differs")
            reports.append((tag,directory,report))
        except Exception as exc:
            error={"shard":shard,"release":tag,"error":describe_failure(exc)}
            try:error["upstream_failure"]=json.loads(download(tag,"BASE_FAILED.json",directory).read_text())
            except Exception as failure_exc:error["failure_report_error"]=describe_failure(failure_exc)
            errors.append(error)
    if errors:
        write_json(root/"BASE_BUILD_INCOMPLETE.json",{"status":"INCOMPLETE_NOT_WORLD","errors":errors,
                   "complete_shards":len(reports),"expected_shards":16})
        raise ValueError("price base incomplete: "+json.dumps(errors))
    return reports


def merge(args):
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    inputs=json.loads(download(args.inputs_tag,"BUILD_INPUTS.json",root).read_text())
    if recipe_fingerprint()[0]!=inputs["recipe_fingerprint"]:raise ValueError("merge recipe differs")
    records=[];parts=[];total={};dates=Counter();inventories={}
    routes=json.loads(Path(args.routes).read_text()) if getattr(args,"routes",None) else {}
    if not isinstance(routes,dict) or not set(routes)<={str(n) for n in range(16)} or any(not isinstance(v,str) for v in routes.values()):
        raise ValueError("invalid compact shard routes")
    for tag,directory,report in collect_base_reports(root,inputs,args.inputs_tag,args.build_prefix,routes):
        records.extend(report["records"]);parts.extend(report["parts"])
        for part in report["parts"]:
            pdir=directory/part["part"]
            source=part["release"]
            if source not in inventories:inventories[source]=asset_index(source)
            verify_base_asset_digests(part,inventories[source])
            coverage=download(source,part["part"]+".coverage.csv",pdir)
            stock_days=download(source,part["part"]+".stock_days.csv",pdir)
            if sha(coverage)!=part["coverage_sha256"] or sha(stock_days)!=part["stock_days_sha256"]:raise ValueError("base coverage/date weights changed")
            with coverage.open(newline="") as f:
                for row in csv.DictReader(f):
                    for key in ("query_rows","non_null_rows","tickers_with_values"):row[key]=int(row[key])
                    add_metrics(total,row["timeframe"],[row])
            with stock_days.open(newline="") as f:
                for row in csv.DictReader(f):dates[row["date"]]+=int(row["stock_days"])
    expected={r["ticker"] for r in inputs["records"]};actual=[r["ticker"] for r in records]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError("base universe incomplete")
    query_rows=sum(r["query_rows"] for r in records)
    if sum(dates.values())!=query_rows:raise ValueError("stock-day weights inconsistent")
    rows=sorted(total.values(),key=lambda r:(r["timeframe"],r["column"]))
    for row in rows:
        if row["query_rows"]!=query_rows or not 0<row["non_null_rows"]<=query_rows:raise ValueError("OHLCV coverage empty/inconsistent")
        row["non_null_pct"]=100*row["non_null_rows"]/query_rows
    coverage=root/"NATIVE_PRICE_BASE_COVERAGE_V1.csv"
    with coverage.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    stock_days=root/"PRICE_BASE_STOCK_DAY_WEIGHTS_V1.csv"
    with stock_days.open("w",newline="") as f:
        writer=csv.writer(f);writer.writerow(["date","stock_days"]);writer.writerows(sorted(dates.items()))
    result={"status":"FULL_ACCEPTED_PRICE_BASE_ONLY_NOT_WORLD","inputs_tag":args.inputs_tag,"selected_tickers":len(actual),
            "query_rows":query_rows,"timeframes":list(TIMEFRAMES),"column_timeframe_rows":len(rows),"parts":parts,
            "coverage_sha256":sha(coverage),"stock_day_weights_sha256":sha(stock_days),"recipe_fingerprint":inputs["recipe_fingerprint"],
            "base_build_prefix":args.build_prefix,"source_commit":os.environ["GITHUB_SHA"],"execution_open_separate":True,
            "base_shard_routes":routes,"base_export_code_sha256":sha(__file__),
            "price_basis":"frozen reference units, nominal historical price NOT proven","historical_tradeability_gate":"NOT_RUN",
            "full_world_gate":"NOT_RUN","scoring_gate":"CLOSED"}
    file=root/"NATIVE_PRICE_BASE_STATUS_V1.json";write_json(file,result)
    tag=f"native-price-base-coverage-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh("release","create",tag,file,coverage,stock_days,"--title",tag,"--notes","Full accepted-price native base coverage only; historical tradeability, context and scoring remain gated.","--target",os.environ["GITHUB_SHA"])
    print("PRICE_BASE_COVERAGE_COMPLETE",tag,len(actual),query_rows,len(rows),flush=True)
def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="operation",required=True)
    for op in ("build","merge"):
        p=sub.add_parser(op);p.add_argument("--directory",required=True);p.add_argument("--inputs-tag",required=True)
        if op=="build":
            p.add_argument("--shard",type=int,required=True);p.add_argument("--resume-prefix")
        else:
            p.add_argument("--build-prefix",required=True);p.add_argument("--routes")
    args=ap.parse_args();(build if args.operation=="build" else merge)(args)
if __name__=="__main__":main()
