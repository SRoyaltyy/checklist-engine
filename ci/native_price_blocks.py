"""Build versioned native-price blocks from already-published source archives.

This is Phase 1 price/indicator work, never a complete world or scoring result.
"""
import argparse,base64,csv,hashlib,io,json,os,shutil,subprocess,tarfile,time
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from world_timeframes import TIMEFRAMES,PRICE_COLS,completed_candles,candle_features
from price_reconcile import reconcile_one

CUTOFF="2026-10-23"
PRICE_TAG="world-prices-v3-40259691137-1"
FROZEN_TAG="data-2020-24-v1"
FROZEN_HASHES={
 "universe_2020_survivors_le2024.parquet":"df552a70afe4be60330ea3b1ee96bf8d48d89cd4c431e0de029d4c73a1b4f5b1",
 "bars_all_le2024.parquet":"cf6090bbb5769e7afee5825005d83df2c5f04d4082dff6d6dfae927110325cdc",
}
FIELDS=["ticker","date",*PRICE_COLS]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def gh(*args):subprocess.run(["gh",*map(str,args)],check=True)

def download(tag,name,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    target=directory/name
    if not target.exists():gh("release","download",tag,"-p",name,"-D",directory)
    return target

def json_safe(value):
    if isinstance(value,dict):return {str(k):json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_safe(v) for v in value]
    if isinstance(value,np.generic):return json_safe(value.item())
    if isinstance(value,float) and not np.isfinite(value):return None
    return value

def write_json(path,value):
    Path(path).write_text(json.dumps(json_safe(value),indent=2,allow_nan=False)+"\n",encoding="utf-8")

def recipe_fingerprint():
    names=["facets_world.py","world_timeframes.py","world_bar_statistics.py","world_food_statistics.py",
           "world_indicator_settings.py","world_indicator_extra.py","world_moving_averages.py","world_dates.py","price_reconcile.py","requirements-world-v2.txt",
           "dictionary/INDICATOR_SETTINGS.json","dictionary/BAR_STATISTICS_REGISTRY.json","ci/native_price_blocks.py"]
    values={name:sha(name) for name in names}
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest(),values

def source_part(ordinal):
    return f"prices_shard_{ordinal%16:03d}_attempt_1_part_{(ordinal//16)//50:03d}"

def read_member(archive,manifest,name):
    meta={m["name"]:m for m in manifest["members"]}[name]
    with tarfile.open(archive) as tar:
        data=tar.extractfile(name).read()
    if len(data)!=meta["bytes"] or hashlib.sha256(data).hexdigest()!=meta["sha256"]:
        raise ValueError("source member fingerprint mismatch: "+name)
    return data

def source_archive(stem,directory):
    mpath=download(PRICE_TAG,stem+".json",directory)
    manifest=json.loads(mpath.read_text())
    archive=download(PRICE_TAG,stem+".tar",directory)
    if sha(archive)!=manifest["archive_sha256"]:raise ValueError("source archive hash mismatch")
    return archive,manifest,sha(mpath)

def market_session_calendar(spy_dates,vix_dates):
    import exchange_calendars as xcals
    from importlib.metadata import version
    dates=xcals.get_calendar("XNYS",start="1990-01-01",end=CUTOFF).sessions
    dates=pd.DatetimeIndex(dates).tz_localize(None).as_unit("ns")
    spy_dates=pd.DatetimeIndex(spy_dates).as_unit("ns")
    vix_dates=pd.DatetimeIndex(vix_dates).as_unit("ns")
    off_calendar=spy_dates.difference(dates)
    missing_spy=dates[dates>=spy_dates.min()].difference(spy_dates)
    receipt={"calendar_package":"exchange_calendars","version":version("exchange_calendars"),"exchange":"XNYS",
             "first":str(dates.min())[:10],"last":str(dates.max())[:10],
             "spy_off_calendar_dates":[str(d)[:10] for d in off_calendar],
             "spy_missing_sessions":[str(d)[:10] for d in missing_spy],
             "vix_missing_sessions":[str(d)[:10] for d in dates.difference(vix_dates)],
             "vix_off_calendar_dates":[str(d)[:10] for d in vix_dates.difference(dates)],
             "price_rows_modified":False,"vix_values_imputed":False}
    if len(off_calendar) or len(missing_spy):raise ValueError("SPY/calendar validation failed: "+json.dumps(receipt))
    if str(dates.max())[:10]!=CUTOFF:raise ValueError("calendar cutoff differs")
    return dates,receipt


def prepare(args):
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    if args.shards<1 or args.shards>128:raise ValueError("expected 1..128 bounded shards")
    for name,wanted in FROZEN_HASHES.items():
        file=download(FROZEN_TAG,name,root)
        if sha(file)!=wanted:raise ValueError("frozen source hash mismatch: "+name)
    canonical=pd.read_parquet(root/"universe_2020_survivors_le2024.parquet",columns=FIELDS)
    warmup=pd.read_parquet(root/"bars_all_le2024.parquet",columns=FIELDS)
    for frame in (canonical,warmup):
        frame["date"]=pd.to_datetime(frame.date).astype("datetime64[ns]")
        frame["ticker"]=frame.ticker.astype(str)
    universe=set(canonical.ticker)
    if len(universe)!=8727:raise ValueError("canonical universe changed")
    ordered=sorted(universe,key=lambda s:hashlib.sha256(("world-prices-v2|"+s).encode()).hexdigest())
    rank={ticker:i for i,ticker in enumerate(ordered)}
    accepted_file=download("price-source-acceptance-v6-40292775611-1","ACCEPTED_PRICE_INVENTORY_V6.csv",root)
    if sha(accepted_file)!="58383133dc32425de0be69aa8ead7e2c070bd62c6505c11e62c9c5ebd2501a3b":
        raise ValueError("accepted inventory changed")
    with accepted_file.open(newline="") as f:records=list(csv.DictReader(f))
    if len(records)!=8447 or len({r["ticker"] for r in records})!=8447:raise ValueError("accepted inventory incomplete")
    repo=os.environ["GITHUB_REPOSITORY"]
    payload=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/contents/docs/EXCLUDED.csv?ref=main"]))
    exclusion_bytes=base64.b64decode(payload["content"])
    with io.StringIO(exclusion_bytes.decode("utf-8"),newline="") as stream:exclusions=list(csv.DictReader(stream))
    if any(not row.get("reason","").strip() for row in exclusions):raise ValueError("blank exclusion reason")
    excluded={row["ticker"] for row in exclusions if row["scope"]=="candidate_universe"}
    requested=set(args.tickers.split(",")) if args.tickers else {r["ticker"] for r in records}-excluded
    if requested&excluded:raise ValueError("explicitly excluded entity requested")
    if not requested<={r["ticker"] for r in records}:raise ValueError("requested entity not in accepted inventory")
    records=[dict(r,ordinal=rank[r["ticker"]],source_part=source_part(rank[r["ticker"]]),
                 feature_shard=rank[r["ticker"]]%args.shards) for r in records if r["ticker"] in requested]
    frozen=pd.concat([
        warmup[(warmup.date<pd.Timestamp("2020-01-01"))&warmup.ticker.isin(requested)],
        canonical[(canonical.date>=pd.Timestamp("2020-01-01"))&(canonical.date<=pd.Timestamp("2024-12-31"))&canonical.ticker.isin(requested)]
    ],ignore_index=True)
    if frozen.duplicated(["ticker","date"]).any():raise ValueError("conflicting/duplicate frozen sessions require explicit review")
    fingerprint,files=recipe_fingerprint()
    output=root/"prepared";output.mkdir(exist_ok=True);part_hashes={}
    for shard in range(args.shards):
        names={r["ticker"] for r in records if r["feature_shard"]==shard}
        frame=frozen[frozen.ticker.isin(names)].sort_values(["ticker","date"])
        file=output/f"frozen_{shard:03d}.parquet";frame.to_parquet(file,index=False)
        part_hashes[file.name]={"sha256":sha(file),"rows":len(frame),"tickers":len(names)}
    # Use actual observed SPY sessions for its lifetime, and the official VIX
    # record before SPY existed. Do not infer NYSE sessions from weekdays.
    archive,manifest,_=source_archive(source_part(rank["SPY"]),root/"spy")
    spy=pd.read_parquet(io.BytesIO(read_member(archive,manifest,"SPY".encode().hex()+".parquet")))
    spy_dates=pd.DatetimeIndex(pd.to_datetime(spy.date)).as_unit("ns").sort_values().unique()
    cboe=download("phase1-gap-cboe-v1-40307220071-1","cboe_gap_source.tar.gz",root)
    if sha(cboe)!="7f5e6cc98ffa0ae632f8b22454d4641cf4402d94f5b7bfbcf115cc3c81904710":
        raise ValueError("CBOE source archive changed")
    with tarfile.open(cboe) as tar:raw=tar.extractfile("cboe/VIX.parquet").read()
    if hashlib.sha256(raw).hexdigest()!="9599af8baa788513a765e3d7bc8104eb4b9bfd43c14e55fb0196a03ad8949949":
        raise ValueError("VIX member changed")
    vix_dates=pd.DatetimeIndex(pd.read_parquet(io.BytesIO(raw)).DATE).as_unit("ns")
    # A single instrument can omit a real session (VIX omits 1991-03-01).
    # Use a pinned exchange calendar, validated against the complete observed
    # SPY lifetime. This changes no OHLCV source rows or missing index values.
    dates,calendar_receipt=market_session_calendar(spy_dates,vix_dates)
    calendar_file=output/"market_sessions.parquet";pd.DataFrame({"date":dates}).to_parquet(calendar_file,index=False)
    inputs={"status":"PRICE_BLOCK_INPUTS_ONLY_NOT_WORLD","is_smoke":bool(args.tickers),
        "as_of_completed_session":CUTOFF,"price_source_release":PRICE_TAG,"frozen_source_hashes":FROZEN_HASHES,
        "accepted_source_tickers":8447,"current_exclusion_blob_sha":payload["sha"],
        "current_exclusion_sha256":hashlib.sha256(exclusion_bytes).hexdigest(),"current_exclusions":len(excluded),"selected_tickers":len(records),"feature_shards":args.shards,"records":records,
        "prepared_shards":part_hashes,"recipe_fingerprint":fingerprint,"recipe_files":files,
        "calendar_sha256":sha(calendar_file),"calendar_first":str(dates.min())[:10],"calendar_last":str(dates.max())[:10],
        "calendar_rule":"pinned XNYS session calendar validated against actual SPY lifetime",
        "calendar_validation":calendar_receipt,
        "calendar_source_spy_archive_sha256":manifest["archive_sha256"],
        "context_gate":"NOT_RUN; industry/sector/index/breadth/macro joins remain",
        "historical_tradeability_gate":"NOT_RUN; nominal market cap and PIT eligibility remain",
        "source_commit":os.environ["GITHUB_SHA"]}
    write_json(output/"BUILD_INPUTS.json",inputs)
    tag=f"native-price-inputs-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh("release","create",tag,*sorted(output.iterdir()),"--title",tag,"--notes",
       "Prepared immutable inputs for native price blocks. Provisional; not a complete world or scoring result.",
       "--target",os.environ["GITHUB_SHA"])
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:
            f.write("tag="+tag+"\nshards="+json.dumps(list(range(args.shards)))+"\n")
    print("PREPARED_NATIVE_PRICE_INPUTS",tag,len(records),flush=True)

def measure_availability(features,query_dates):
    """Exact daily-as-of counts without expanding a wide daily matrix."""
    q=np.asarray(pd.to_datetime(query_dates).astype("datetime64[ns]"))
    avail=features.available_from.to_numpy(dtype="datetime64[ns]")
    if len(avail)>1 and np.any(avail[1:]<=avail[:-1]):raise ValueError("availability must be ordered and unique")
    if len(q)>1 and np.any(q[1:]<=q[:-1]):raise ValueError("query dates must be ordered and unique")
    columns=[c for c in features if c!="available_from"]
    if len(avail)==0:return []
    positions=np.searchsorted(avail,q,side="right")-1;good=positions>=0
    weights=np.bincount(positions[good],minlength=len(avail))
    first=np.full(len(avail),len(q),dtype=int);last=np.full(len(avail),-1,dtype=int)
    np.minimum.at(first,positions[good],np.flatnonzero(good))
    np.maximum.at(last,positions[good],np.flatnonzero(good))
    values=features[columns].to_numpy(dtype=float)
    valid=np.isfinite(values)
    for i,name in enumerate(columns):
        if name.endswith("_inf"):valid[:,i]|=np.isinf(values[:,i])
    counts=np.einsum('i,ij->j',weights,valid,dtype=np.int64)
    used=valid&(weights[:,None]>0)
    first_rows=used.argmax(axis=0);last_rows=len(avail)-1-used[::-1].argmax(axis=0)
    return [{"column":name,"query_rows":len(q),"non_null_rows":int(counts[i]),
             "first_date":str(q[first[first_rows[i]]])[:10] if counts[i] else "",
             "last_date":str(q[last[last_rows[i]]])[:10] if counts[i] else "",
             "tickers_with_values":int(counts[i]>0)}
            for i,name in enumerate(columns)]

def add_metrics(total,tf,rows):
    for row in rows:
        key=(tf,row["column"])
        if key not in total:total[key]=dict(row,timeframe=tf)
        else:
            value=total[key]
            for field in ("query_rows","non_null_rows","tickers_with_values"):value[field]+=row[field]
            if row["first_date"]:value["first_date"]=min(x for x in (value["first_date"],row["first_date"]) if x)
            value["last_date"]=max(value["last_date"],row["last_date"])

def flush_part(root,tag,number,tickers,metrics,inputs,source_receipts,entity_records=None):
    part=root/"current";files=sorted(p for p in part.iterdir() if p.is_file())
    if not files or not tickers:raise ValueError("empty part cannot be published")
    stem=f"part_{number:04d}";archive=root/(stem+".tar")
    members=[{"name":f.name,"bytes":f.stat().st_size,"sha256":sha(f)} for f in files]
    reserve=7000000000 if 17<=datetime.now(ZoneInfo("Asia/Hong_Kong")).hour<21 else 2000000000
    if shutil.disk_usage(root).free<reserve+sum(f.stat().st_size for f in files):
        raise RuntimeError("Disk reserve would be breached; current source part remains local, earlier parts are durable")
    with tarfile.open(archive,"w") as tar:
        for f in files:tar.add(f,arcname=f.name,recursive=False)
    if archive.stat().st_size>=1900000000:raise ValueError("part exceeds bounded release asset size")
    coverage=root/(stem+".coverage.csv")
    rows=sorted(metrics.values(),key=lambda r:(r["timeframe"],r["column"]))
    with coverage.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report={"status":"PRICE_PART_COMPLETE_NOT_WORLD","tickers":tickers,"timeframes":list(TIMEFRAMES),
        "archive_sha256":sha(archive),"coverage_sha256":sha(coverage),"members":members,
        "recipe_fingerprint":inputs["recipe_fingerprint"],"source_receipts":source_receipts,
        "inputs_tag":inputs["inputs_tag"],"is_smoke":inputs["is_smoke"],"entity_records":entity_records or [],
        "source_commit":os.environ["GITHUB_SHA"]}
    meta=root/(stem+".json");write_json(meta,report)
    gh("release","upload",tag,archive,coverage,meta)
    # Only remove this builder's bounded current part after durable upload.
    for f in files:f.unlink()
    archive.unlink();coverage.unlink();meta.unlink()
    print("NATIVE_PART_DURABLE",tag,stem,len(tickers),flush=True)
    return {"part":stem,"release":tag,"tickers":tickers,"archive_sha256":report["archive_sha256"],"coverage_sha256":report["coverage_sha256"]}

def build_entity(ticker,old,archive,manifest,calendar,funcs,directory):
    """Commit a complete entity to a part only after every timeframe succeeds."""
    started=time.time();hexname=ticker.encode().hex();directory.mkdir(exist_ok=True)
    if any(directory.iterdir()):raise ValueError("staging directory is not empty")
    new=pd.read_parquet(io.BytesIO(read_member(archive,manifest,hexname+".parquet")))
    new=new[pd.to_datetime(new.date)<=pd.Timestamp(CUTOFF)]
    event_name=hexname+".events.parquet"
    events=pd.read_parquet(io.BytesIO(read_member(archive,manifest,event_name))) if any(m["name"]==event_name for m in manifest["members"]) else None
    bars,bridge=reconcile_one(ticker,old,new,min_overlap=60,allow_short_history=False,events=events)
    if bridge["overlap_rows"]<60 or bridge["all_overlap_volumes_zero"] or bridge["supplemental_end"]!=CUTOFF:
        raise ValueError("rejected/stale source entered build: "+ticker)
    bars.to_parquet(directory/(hexname+".bars.parquet"),index=False)
    if events is not None:events.to_parquet(directory/(hexname+".events.parquet"),index=False)
    query=pd.to_datetime(bars.loc[bars.date>=pd.Timestamp("2020-01-01"),"date"]).astype("datetime64[ns]")
    missing=pd.DatetimeIndex(bars.date).difference(calendar)
    if len(missing):
        raise ValueError("Observed-session calendar mismatch: "+json.dumps({"ticker":ticker,"count":len(missing),"dates":[str(d)[:10] for d in missing[:100]],"calendar_first":str(calendar.min())[:10],"calendar_last":str(calendar.max())[:10]}))
    counts={};metrics={}
    for tf in TIMEFRAMES:
        candles=completed_candles(bars,tf,session_calendar=calendar)
        if candles.empty:raise ValueError("no native candle rows: "+ticker+" "+tf)
        if not (candles.date<candles.available_from).all():raise ValueError("day-D candle leakage")
        features=candle_features(candles,funcs,timeframe=tf)
        add_metrics(metrics,tf,measure_availability(features,query))
        frame=features.copy();frame.insert(0,"ticker",ticker)
        frame.insert(1,"candle_start",candles.candle_start.to_numpy())
        frame.insert(2,"source_candle_end",candles.date.to_numpy())
        frame.to_parquet(directory/(hexname+"."+tf+".parquet"),index=False,compression="zstd")
        schema=sorted(c for c in features if c!="available_from")
        counts[tf]={"native_rows":len(frame),"feature_columns":len(schema),
                    "schema_sha256":hashlib.sha256(json.dumps(schema).encode()).hexdigest()}
    record={"ticker":ticker,"bridge":bridge,"native":counts,"query_rows":len(query),
            "elapsed_s":round(time.time()-started,2),"price_basis":"frozen split-adjusted reference units; nominal prices pending"}
    write_json(directory/(hexname+".status.json"),record)
    print("NATIVE_TICKER_COMPLETE",ticker,len(query),round(time.time()-started,2),flush=True)
    return record,metrics


def release_assets(tag):
    repo=os.environ["GITHUB_REPOSITORY"]
    result=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/releases/tags/{tag}"]))
    return {a["name"] for a in result["assets"]}


def recovered_parts(tag,inputs,directory):
    """Reuse only durable, same-input, same-recipe completed parts."""
    names=release_assets(tag);parts=[];records=[];seen=set()
    for name in sorted(n for n in names if n.startswith("part_") and n.endswith(".json")):
        report=json.loads(download(tag,name,directory).read_text())
        if report["recipe_fingerprint"]!=inputs["recipe_fingerprint"] or report["inputs_tag"]!=inputs["inputs_tag"]:
            raise ValueError("resume recipe/input differs")
        stem=name[:-5]
        if not {stem+".tar",stem+".coverage.csv"}<=names:raise ValueError("incomplete durable part")
        tickers=report["tickers"]
        if len(tickers)!=len(set(tickers)) or seen&set(tickers):raise ValueError("duplicate resumed tickers")
        if {r["ticker"] for r in report["entity_records"]}!=set(tickers):raise ValueError("resume records incomplete")
        seen.update(tickers);records.extend(report["entity_records"])
        parts.append({"part":stem,"release":tag,"tickers":tickers,"archive_sha256":report["archive_sha256"],
                      "coverage_sha256":report["coverage_sha256"]})
    return parts,records


def build(args):
    import facets_world as fw
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    inp=download(args.inputs_tag,"BUILD_INPUTS.json",root);inputs=json.loads(inp.read_text());inputs["inputs_tag"]=args.inputs_tag
    fp,_=recipe_fingerprint()
    if fp!=inputs["recipe_fingerprint"]:raise ValueError("recipe files differ from input preparation")
    name=f"frozen_{args.shard:03d}.parquet";file=download(args.inputs_tag,name,root)
    if sha(file)!=inputs["prepared_shards"][name]["sha256"]:raise ValueError("prepared frozen shard changed")
    frozen=pd.read_parquet(file);old={str(t):g.reset_index(drop=True) for t,g in frozen.groupby("ticker",observed=True)}
    file=download(args.inputs_tag,"market_sessions.parquet",root)
    if sha(file)!=inputs["calendar_sha256"]:raise ValueError("calendar changed")
    calendar=pd.DatetimeIndex(pd.read_parquet(file).date).as_unit("ns")
    selected={r["ticker"]:r for r in inputs["records"] if r["feature_shard"]==args.shard}
    if set(old)!=set(selected):raise ValueError("frozen shard membership differs")
    tag=f"native-price-blocks-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{args.shard:03d}"
    request=root/"SHARD_REQUEST.json";write_json(request,{"scope":"PROVISIONAL_PRICE_BLOCKS_ONLY_NOT_WORLD","inputs":args.inputs_tag,
        "shard":args.shard,"tickers":sorted(selected),"is_smoke":inputs["is_smoke"],"recipe_fingerprint":fp})
    gh("release","create",tag,request,"--title",tag,"--notes",
       "Checkpointed price/native indicator blocks only. Not full world coverage, tradeability or probabilities.",
       "--target",os.environ["GITHUB_SHA"])
    current=root/"current";current.mkdir(exist_ok=True);stage=root/"entity";funcs=fw.discover()
    completed=[];parts=[]
    if args.resume_prefix:
        previous_tag=args.resume_prefix+f"-{args.shard:03d}"
        parts,completed=recovered_parts(previous_tag,inputs,root/"resume")
        if not {r["ticker"] for r in completed}<=set(selected):raise ValueError("resumed names outside selected shard")
    done={r["ticker"] for r in completed};groups=defaultdict(list)
    for ticker,record in selected.items():
        if ticker not in done:groups[record["source_part"]].append(ticker)
    pending=[];pending_records=[];metrics={};receipts=[];number=0;active_ticker=None
    try:
        for stem,names in sorted(groups.items()):
            archive,manifest,mhash=source_archive(stem,root/"source")
            for ticker in sorted(names):
                active_ticker=ticker
                record,entity_metrics=build_entity(ticker,old[ticker],archive,manifest,calendar,funcs,stage)
                for file in stage.iterdir():file.replace(current/file.name)
                for tf in TIMEFRAMES:
                    add_metrics(metrics,tf,[r for (t,_),r in entity_metrics.items() if t==tf])
                completed.append(record);pending.append(ticker);pending_records.append(record)
                receipts.append({"source_part":stem,"manifest_sha256":mhash,"archive_sha256":manifest["archive_sha256"]})
                size=sum(p.stat().st_size for p in current.iterdir() if p.is_file())
                if len(pending)>=10 or size>=500000000:
                    parts.append(flush_part(root,tag,number,pending,metrics,inputs,receipts,pending_records))
                    number+=1;pending=[];pending_records=[];metrics={};receipts=[]
            archive.unlink()
        if pending:
            parts.append(flush_part(root,tag,number,pending,metrics,inputs,receipts,pending_records))
            pending=[]
    except Exception as exc:
        # The failed entity stayed in staging and cannot contaminate a good part.
        checkpoint_error=None
        if pending:
            try:parts.append(flush_part(root,tag,number,pending,metrics,inputs,receipts,pending_records))
            except Exception as checkpoint_exc:checkpoint_error=str(checkpoint_exc)
        failure={"status":"FAILED_NOT_WORLD","failed_ticker":active_ticker,"error":str(exc),
                 "checkpoint_error":checkpoint_error,"durable_parts":parts,"completed_entities":len(completed),
                 "inputs_tag":args.inputs_tag,"recipe_fingerprint":fp}
        file=root/"SHARD_FAILED.json";write_json(file,failure);gh("release","upload",tag,file)
        raise
    if {r["ticker"] for r in completed}!=set(selected):raise ValueError("incomplete shard")
    summary={"status":"ALL_SELECTED_PRICE_ENTITIES_BUILT_NOT_WORLD","shard":args.shard,"inputs_tag":args.inputs_tag,
        "is_smoke":inputs["is_smoke"],"selected":len(selected),"completed":len(completed),"parts":parts,
        "recipe_fingerprint":fp,"timeframes":list(TIMEFRAMES),"records":completed,
        "full_world_gate":"NOT_RUN","historical_tradeability_gate":"NOT_RUN","source_commit":os.environ["GITHUB_SHA"]}
    file=root/"SHARD_COMPLETE.json";write_json(file,summary);gh("release","upload",tag,file)
    print("NATIVE_SHARD_COMPLETE",tag,len(completed),flush=True)


def validate_shard(summary,inputs,shard):
    expected={r["ticker"] for r in inputs["records"] if r["feature_shard"]==shard}
    records=summary["records"];actual=[r["ticker"] for r in records]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError("shard membership incomplete/duplicate")
    if summary["completed"]!=len(expected) or summary["selected"]!=len(expected):raise ValueError("shard count differs")
    if summary["recipe_fingerprint"]!=inputs["recipe_fingerprint"]:raise ValueError("shard recipe differs")
    if summary["inputs_tag"]!=inputs["inputs_tag"] or summary["is_smoke"]!=inputs["is_smoke"]:raise ValueError("shard input differs")
    if set(summary["timeframes"])!=set(TIMEFRAMES):raise ValueError("shard timeframe grid differs")
    for record in records:
        if set(record["native"])!=set(TIMEFRAMES):raise ValueError("entity timeframe grid incomplete")
        if any(v["native_rows"]<=0 or v["feature_columns"]<=0 for v in record["native"].values()):
            raise ValueError("empty entity timeframe")
    part_tickers=[t for p in summary["parts"] for t in p["tickers"]]
    if len(part_tickers)!=len(set(part_tickers)) or set(part_tickers)!=expected:raise ValueError("durable part membership differs")
    return records


def merge(args):
    root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    inputs=json.loads(download(args.inputs_tag,"BUILD_INPUTS.json",root).read_text());inputs["inputs_tag"]=args.inputs_tag
    fp,_=recipe_fingerprint()
    if fp!=inputs["recipe_fingerprint"]:raise ValueError("merge recipe differs")
    all_records=[];total={};part_proofs=[];errors=[]
    for shard in range(inputs["feature_shards"]):
        tag=args.build_prefix+f"-{shard:03d}";directory=root/f"shard_{shard:03d}"
        try:
            summary=json.loads(download(tag,"SHARD_COMPLETE.json",directory).read_text())
            records=validate_shard(summary,inputs,shard)
            shard_metrics={}
            for part in summary["parts"]:
                pdir=directory/part["release"]/part["part"]
                report=json.loads(download(part["release"],part["part"]+".json",pdir).read_text())
                if report["archive_sha256"]!=part["archive_sha256"] or report["tickers"]!=part["tickers"]:
                    raise ValueError("part manifest differs")
                if report["recipe_fingerprint"]!=fp or report["inputs_tag"]!=args.inputs_tag:
                    raise ValueError("part input/recipe differs")
                file=download(part["release"],part["part"]+".coverage.csv",pdir)
                if sha(file)!=part["coverage_sha256"] or sha(file)!=report["coverage_sha256"]:raise ValueError("coverage hash differs")
                with file.open(newline="") as stream:
                    for row in csv.DictReader(stream):
                        for c in ("query_rows","non_null_rows","tickers_with_values"):row[c]=int(row[c])
                        add_metrics(shard_metrics,row["timeframe"],[row])
                part_proofs.append(dict(part,manifest_sha256=sha(pdir/(part["part"]+".json"))))
            for row in shard_metrics.values():add_metrics(total,row["timeframe"],[row])
            all_records.extend(records)
        except Exception as exc:errors.append({"shard":shard,"release":tag,"error":str(exc)})
    expected={r["ticker"] for r in inputs["records"]};actual=[r["ticker"] for r in all_records]
    if errors or len(actual)!=len(set(actual)) or set(actual)!=expected:
        write_json(root/"BUILD_INCOMPLETE.json",{"status":"INCOMPLETE_NOT_WORLD","errors":errors,
                   "complete_tickers":len(actual),"expected_tickers":len(expected)})
        raise ValueError("native build incomplete: "+json.dumps(errors))
    query_rows=sum(r["query_rows"] for r in all_records);rows=[]
    for row in total.values():
        row["observed_schema_query_rows"]=row["query_rows"];row["query_rows"]=query_rows
        if not 0<=row["non_null_rows"]<=query_rows:raise ValueError("invalid measured coverage")
        row["non_null_pct"]=100*row["non_null_rows"]/query_rows if query_rows else 0
        row["status"]="MEASURED_PRICE_ONLY" if row["non_null_rows"] else "NO_OBSERVED_VALUES"
        rows.append(row)
    rows.sort(key=lambda r:(r["timeframe"],r["column"]))
    coverage=root/"NATIVE_PRICE_COLUMN_COVERAGE_V1.csv"
    with coverage.open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    schemas={tf:sorted({r["native"][tf]["schema_sha256"] for r in all_records}) for tf in TIMEFRAMES}
    status={"status":"SMOKE_ONLY_NOT_WORLD" if inputs["is_smoke"] else "PRICE_NATIVE_BLOCKS_MEASURED_NOT_WORLD",
        "is_smoke":inputs["is_smoke"],"selected_tickers":len(expected),"completed_tickers":len(actual),
        "query_rows":query_rows,"timeframes":list(TIMEFRAMES),"column_timeframe_rows":len(rows),
        "schema_fingerprints":schemas,"zero_fill_rows":sum(not r["non_null_rows"] for r in rows),
        "coverage_sha256":sha(coverage),"parts":part_proofs,"inputs_tag":args.inputs_tag,"build_prefix":args.build_prefix,
        "recipe_fingerprint":fp,"source_commit":os.environ["GITHUB_SHA"],
        "full_world_gate":"NOT_RUN; sector/industry/index/breadth/macro and other blocks remain",
        "historical_tradeability_gate":"NOT_RUN; nominal-price/size/liquidity gates remain",
        "scoring_gate":"CLOSED"}
    write_json(root/"NATIVE_PRICE_BUILD_STATUS_V1.json",status)
    tag=f"native-price-coverage-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh("release","create",tag,coverage,root/"NATIVE_PRICE_BUILD_STATUS_V1.json","--title",tag,
       "--notes","Measured price/native-block coverage only. No full-world, tradeability or scoring claim.","--target",os.environ["GITHUB_SHA"])
    print("NATIVE_PRICE_COVERAGE_COMPLETE",tag,len(actual),query_rows,len(rows),flush=True)

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="operation",required=True)
    p=sub.add_parser("prepare");p.add_argument("--directory",required=True);p.add_argument("--shards",type=int,default=16);p.add_argument("--tickers",default="")
    p=sub.add_parser("build");p.add_argument("--directory",required=True);p.add_argument("--inputs-tag",required=True);p.add_argument("--shard",type=int,required=True);p.add_argument("--resume-prefix",default="")
    p=sub.add_parser("merge");p.add_argument("--directory",required=True);p.add_argument("--inputs-tag",required=True);p.add_argument("--build-prefix",required=True)
    args=ap.parse_args()
    {"prepare":prepare,"build":build,"merge":merge}[args.operation](args)
if __name__=="__main__":main()
