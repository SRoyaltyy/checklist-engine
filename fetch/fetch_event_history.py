"""Checkpoint dated analyst/earnings source rows; no historical-PIT approval."""
import argparse,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from ci.release_assets import download_asset,gh_retry,publish_assets,describe_failure

INPUTS="native-price-inputs-v1-40336250454-1"
SCHEMAS={"analyst":["ticker","event_timestamp","event_date","source_timezone","firm","from_grade","to_grade","action","direction"],
         "earnings":["ticker","event_timestamp","event_date","source_timezone","eps_estimate","eps_actual","surprise_pct"]}


def probe_source(kind,root):
    import yfinance as yf
    root.mkdir(parents=True,exist_ok=True)
    report={"kind":kind,"ticker":"AAPL","library_version":yf.__version__,"status":"FAIL_PROVIDER_PROBE_ONLY","world_gate":"NOT_RUN"}
    try:
        obj=yf.Ticker("AAPL")
        frame=obj.get_upgrades_downgrades() if kind=="analyst" else obj.get_earnings_dates(limit=100)
        rows=normalize_rows("AAPL",frame,kind)
        if rows.empty:raise ValueError("known active source probe returned no rows; do not launch full-universe requests")
        report.update(status="PASS_PROVIDER_PROBE_ONLY",rows=len(rows),columns=list(rows),first_event=rows.event_date.min(),last_event=rows.event_date.max())
    except Exception as exc:report["error"]=describe_failure(exc);raise
    finally:(root/"EVENT_SOURCE_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")


def normalize_rows(ticker,frame,kind):
    if frame is None or frame.empty:return pd.DataFrame(columns=SCHEMAS[kind])
    rows=[]
    for timestamp,row in frame.iterrows():
        stamp=pd.Timestamp(timestamp)
        if pd.isna(stamp):raise ValueError("event timestamp is missing")
        source_timezone=str(stamp.tz) if stamp.tz is not None else "PROVIDER_NAIVE_TIMEZONE_UNPROVEN"
        day=stamp.tz_convert("America/New_York").date() if stamp.tz is not None else stamp.date()
        if str(day)<"2018-01-01" or str(day)>datetime.now(timezone.utc).date().isoformat():continue
        out={"ticker":ticker,"event_timestamp":stamp.isoformat(),"event_date":str(day),"source_timezone":source_timezone}
        if kind=="analyst":
            required={"Firm","FromGrade","ToGrade","Action"}
            if not required<=set(row.index):raise ValueError("analyst source schema differs")
            action=str(row["Action"]).lower()
            directions={"up":1,"upgrade":1,"upgraded":1,"down":-1,"downgrade":-1,"downgraded":-1,
                        "main":0,"reit":0,"reiterate":0,"init":0,"initiate":0,"reinit":0,"coverage":0}
            direction=directions.get(action)
            text=lambda value:None if pd.isna(value) else str(value)
            out.update(firm=text(row["Firm"]),from_grade=text(row["FromGrade"]),to_grade=text(row["ToGrade"]),action=action,direction=direction)
        else:
            if not {"EPS Estimate","Reported EPS"}<=set(row.index):raise ValueError("earnings source schema differs")
            for source,target in (("EPS Estimate","eps_estimate"),("Reported EPS","eps_actual"),("Surprise(%)","surprise_pct")):
                value=pd.to_numeric(row.get(source,row.get("Surprise (%)") if target=="surprise_pct" else None),errors="coerce")
                out[target]=float(value) if pd.notna(value) and np.isfinite(value) else np.nan
        rows.append(out)
    return pd.DataFrame(rows,columns=SCHEMAS[kind]).drop_duplicates()


def acquire(kind,root,shard,shards):
    import yfinance as yf
    root.mkdir(parents=True,exist_ok=True)
    inputs=json.loads(download_asset(INPUTS,"BUILD_INPUTS.json",root).read_text())
    names=sorted(r["ticker"] for r in inputs["records"])[shard::shards]
    tag=f"event-history-{kind}-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{shard:03d}"
    report={"kind":kind,"source_commit":os.environ["GITHUB_SHA"],"library_version":yf.__version__,"inputs_tag":INPUTS,
            "requested_tickers":names,"attempts":[],"parts":[],"source_rows":0,"status":"INCOMPLETE_SOURCE_ONLY",
            "point_in_time_gate":"NOT_RUN; provider event dates are not proof of first historical observation or revision history",
            "historical_coverage":"NOT_PROVEN; no rows returned is not a zero event count","world_gate":"NOT_RUN","scoring_gate":"CLOSED"}
    if kind=="earnings":
        import hashlib
        frozen=download_asset("data-2020-24-v1","nasdaq_earn_2020-24.tar",root)
        report["existing_frozen_earnings_reference"]={"release":"data-2020-24-v1","asset":frozen.name,"sha256":hashlib.sha256(frozen.read_bytes()).hexdigest(),
                                                    "scope":"Original 2020–24 source preserved; provider fetch is additional dated evidence, not a replacement"}
    pending=[];ledger=[];created=False;part=0;consecutive_errors=0

    def flush():
        nonlocal pending,ledger,created,part
        if not ledger:return
        events=pd.concat(pending,ignore_index=True) if pending else pd.DataFrame(columns=SCHEMAS[kind])
        if len(events):
            file=root/f"events_{part:04d}.parquet";events.to_parquet(file,index=False)
            meta=root/f"events_{part:04d}.json"
            import hashlib
            receipt={"rows":len(events),"schema":SCHEMAS[kind],"sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"attempts":ledger}
            meta.write_text(json.dumps(receipt,indent=2)+"\n")
            if not created:
                gh_retry("release","create",tag,"--draft","--target",os.environ["GITHUB_SHA"],"--title",tag,
                         "--notes","Dated provider event rows only; historical completeness/PIT revisions and world acceptance remain unverified.")
                created=True
            publish_assets(tag,file,meta);gh_retry("release","edit",tag,"--draft=false")
            report["parts"].append({"file":file.name,"rows":len(events),"sha256":receipt["sha256"]})
            report["source_rows"]+=len(events);file.unlink();meta.unlink();part+=1
        pending=[];ledger=[]
        (root/"EVENT_SOURCE_STATUS.json").write_text(json.dumps(report,indent=2)+"\n")

    try:
        for index,ticker in enumerate(names):
            attempt={"ticker":ticker,"observed_at":datetime.now(timezone.utc).isoformat()}
            try:
                obj=yf.Ticker(ticker.replace(".","-"))
                frame=obj.get_upgrades_downgrades() if kind=="analyst" else obj.get_earnings_dates(limit=100)
                rows=normalize_rows(ticker,frame,kind)
                attempt.update(status="ROWS_RETURNED" if len(rows) else "NO_ROWS_RETURNED_HISTORY_UNPROVEN",rows=len(rows))
                if len(rows):pending.append(rows)
                consecutive_errors=0
            except Exception as exc:
                attempt.update(status="SOURCE_ERROR",error=describe_failure(exc));consecutive_errors+=1
                time.sleep(min(60,2**min(consecutive_errors,6)))
            report["attempts"].append(attempt);ledger.append(attempt)
            print("EVENT_SOURCE_ENTITY",kind,ticker,attempt["status"],attempt.get("rows"),flush=True)
            if len(ledger)>=25:flush()
            if consecutive_errors>=5:raise RuntimeError("repeated provider errors; stop and retain checkpoints")
            if index>=24 and report["source_rows"]==0 and not pending:raise RuntimeError("no usable event rows in first 25 attempts; history remains unavailable")
            time.sleep(2)
        flush();report["status"]="REQUESTED_TICKERS_ATTEMPTED_SOURCE_ONLY"
    except Exception as exc:
        report["error"]=describe_failure(exc)
        try:flush()
        except Exception as checkpoint:report["checkpoint_error"]=describe_failure(checkpoint)
        raise
    finally:
        report["release"]=tag if created else None
        file=root/"EVENT_SOURCE_STATUS.json";file.write_text(json.dumps(report,indent=2)+"\n")
        if created:
            try:publish_assets(tag,file)
            except Exception as exc:
                report["status_upload_error"]=describe_failure(exc);file.write_text(json.dumps(report,indent=2)+"\n")
                if report["status"]=="REQUESTED_TICKERS_ATTEMPTED_SOURCE_ONLY":raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--kind",choices=SCHEMAS,required=True);parser.add_argument("--directory",required=True)
    parser.add_argument("--shard",type=int,default=0);parser.add_argument("--shards",type=int,default=8)
    parser.add_argument("--probe",action="store_true")
    args=parser.parse_args()
    if not 0<=args.shard<args.shards:raise ValueError("invalid event source shard")
    if args.probe:probe_source(args.kind,Path(args.directory))
    else:acquire(args.kind,Path(args.directory),args.shard,args.shards)


if __name__=="__main__":main()
