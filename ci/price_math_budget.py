"""Bounded real-data runner comparison; this is not a coverage or leak pass."""
import argparse,gc,hashlib,json,os,shutil,subprocess,sys,time
from collections import Counter
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
REQUEST=REPO/"ci/NATIVE_PRICE_MATH_BUDGET_REQUEST.json"


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()


def recipe_identity(directory,names):
    files={name:digest(directory/name) for name in names}
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),files


def worker(root,recipe_root,label):
    # A separate interpreter keeps baseline/current imports and peak RSS apart.
    sys.path[:0]=[str(recipe_root),str(REPO)]
    import resource
    import pandas as pd
    import facets_world as fw
    from world_timeframes import TIMEFRAMES,completed_candles,candle_features
    fixtures=json.loads((root/"BUDGET_FIXTURES.json").read_text())
    fingerprint,_=recipe_identity(recipe_root,fixtures["recipe_files"])
    calendar=pd.DatetimeIndex(pd.read_parquet(root/"market_sessions.parquet").date)
    funcs=fw.discover();rows=[]
    for source in fixtures["samples"]:
        file=root/source['file']
        if digest(file)!=source['sha256']:raise ValueError('budget fixture fingerprint differs')
        gc.collect();started=time.perf_counter();bars=pd.read_parquet(file)
        outdir=root/label/source["ticker"].encode().hex();outdir.mkdir(parents=True,exist_ok=True)
        frames={};total_bytes=0
        for tf in TIMEFRAMES:
            candles=completed_candles(bars,tf,session_calendar=calendar)
            frame=candle_features(candles,funcs,timeframe=tf)
            file=outdir/(tf+".parquet");frame.to_parquet(file,index=False,compression="zstd")
            schema={name:str(dtype) for name,dtype in frame.dtypes.items() if name!="available_from"}
            frames[tf]={"native_rows":len(frame),"feature_columns":len(schema),"bytes":file.stat().st_size,
                        "dtype_counts":dict(Counter(schema.values())),
                        "schema_sha256":hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest()}
            total_bytes+=file.stat().st_size
        rows.append({"ticker":source["ticker"],"input_rows":len(bars),"max_reference_close":float(bars.close.max()),
                     "seconds":time.perf_counter()-started,"compressed_bytes":total_bytes,"timeframes":frames})
        print("PRICE_MATH_BUDGET_ENTITY",label,source["ticker"],round(rows[-1]["seconds"],3),total_bytes,flush=True)
    from importlib.metadata import version
    report={"label":label,"recipe_fingerprint":fingerprint,"entities":rows,
            "versions":{name:version(name) for name in ('numpy','pandas','pyarrow','TA-Lib')},"python":sys.version,
            "peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            "schema_variants_by_timeframe":{tf:len({r["timeframes"][tf]["schema_sha256"] for r in rows}) for tf in TIMEFRAMES}}
    (root/(label+".json")).write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


def prepare(root,request):
    sys.path.insert(0,str(REPO))
    import io
    import pandas as pd
    from ci.release_assets import download_asset
    from ci.native_price_blocks import read_member
    source=request["compact_source"];stem=request["compact_part"]
    manifest_file=download_asset(source,stem+".json",root/"source")
    manifest=json.loads(manifest_file.read_text())
    archive=download_asset(source,stem+".tar",root/"source")
    if digest(archive)!=manifest["archive_sha256"]:raise ValueError("budget source archive differs")
    inputs_file=download_asset(request["inputs_tag"],"BUILD_INPUTS.json",root)
    if digest(inputs_file)!=request['inputs_sha256']:raise ValueError('budget frozen inputs manifest differs')
    inputs=json.loads(inputs_file.read_text())
    if manifest["recipe_fingerprint"]!=inputs["recipe_fingerprint"] or manifest["inputs_tag"]!=request["inputs_tag"]:
        raise ValueError("budget source recipe/input differs")
    calendar=download_asset(request["inputs_tag"],"market_sessions.parquet",root)
    if digest(calendar)!=inputs["calendar_sha256"]:raise ValueError("budget calendar differs")
    candidates=[]
    for record in manifest["records"]:
        ticker=record["ticker"];name=ticker.encode().hex()+".bars.parquet"
        bars=pd.read_parquet(io.BytesIO(read_member(archive,manifest,name)))
        candidates.append((ticker,len(bars),float(bars.close.max()),bars))
    # Span observed history length and reference-price scale, without outcomes.
    history=max(candidates,key=lambda r:(r[1],r[0]));price=max(candidates,key=lambda r:(r[2],r[0]))
    ordered=sorted(candidates,key=lambda r:(r[2],r[0]));middle=ordered[len(ordered)//2]
    selected=[];seen=set()
    for candidate in [history,price,middle,*ordered]:
        if candidate[0] in seen:continue
        selected.append(candidate);seen.add(candidate[0])
        if len(selected)==request["sample_entities"]:break
    if len(selected)!=3:raise ValueError("expected three distinct budget entities")
    samples=[]
    for ticker,count,maximum,bars in selected:
        name=ticker.encode().hex()+".bars.parquet";bars.to_parquet(root/name,index=False)
        samples.append({"ticker":ticker,"input_rows":count,"max_reference_close":maximum,"file":name,"sha256":digest(root/name)})
    archive.unlink()  # Fixtures are verified; do not retain the source archive twice.
    counts=Counter(r["feature_shard"] for r in inputs["records"])
    fixtures={"request":request,"samples":samples,"recipe_files":list(inputs["recipe_files"]),
              "baseline_fingerprint":inputs["recipe_fingerprint"],"selected_tickers":inputs["selected_tickers"],
              "max_shard_entities":max(counts.values()),"source_manifest_sha256":digest(manifest_file),
              "inputs_manifest_sha256":digest(inputs_file),"calendar_sha256":digest(calendar)}
    (root/"BUDGET_FIXTURES.json").write_text(json.dumps(fixtures,indent=2,allow_nan=False)+"\n")
    return fixtures,inputs


def publish(root):
    from ci.release_assets import gh_retry,publish_assets
    file=root/'PRICE_MATH_BUDGET_V2.json'
    if not file.exists():
        print('NO_COMPLETE_BUDGET_MEASUREMENT_TO_PUBLISH',flush=True);return
    files=[file,root/'BUDGET_FIXTURES.json',root/'baseline.json',root/'corrected.json']
    manifest=root/'BUDGET_PROOF_MANIFEST.json'
    manifest.write_text(json.dumps({p.name:digest(p) for p in files},indent=2)+'\n')
    tag=f"price-math-budget-v2-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',tag,
             '--notes','Measured three-entity math comparison only. Review the budget status and sampling limits; not full-universe or world acceptance.')
    publish_assets(tag,*files,manifest);gh_retry('release','edit',tag,'--draft=false')


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True)
    parser.add_argument("--worker",choices=("baseline","corrected"));parser.add_argument("--recipe-root")
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args();root=Path(args.directory).resolve();root.mkdir(parents=True,exist_ok=True)
    if args.publish:publish(root);return
    if args.worker:worker(root,Path(args.recipe_root).resolve(),args.worker);return
    request=json.loads(REQUEST.read_text());fixtures,inputs=prepare(root,request)
    baseline=root/"baseline-code";baseline.mkdir(exist_ok=True)
    subprocess.run(["git","fetch","--depth=1","origin",request["baseline_commit"]],cwd=REPO,check=True)
    for name in inputs["recipe_files"]:
        if Path(name).is_absolute() or ".." in Path(name).parts:raise ValueError("unsafe recipe path")
        target=baseline/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(subprocess.check_output(["git","show",request["baseline_commit"]+":"+name],cwd=REPO))
    fingerprint,files=recipe_identity(baseline,inputs["recipe_files"])
    if files!=inputs["recipe_files"] or fingerprint!=inputs["recipe_fingerprint"]:raise ValueError("baseline does not match frozen recipe")
    for label,directory in (("baseline",baseline),("corrected",REPO)):
        subprocess.run([sys.executable,str(Path(__file__).resolve()),"--directory",str(root),"--worker",label,"--recipe-root",str(directory)],cwd=directory,check=True)
    old=json.loads((root/"baseline.json").read_text());new=json.loads((root/"corrected.json").read_text())
    if old["recipe_fingerprint"]==new["recipe_fingerprint"]:raise ValueError("corrected recipe was not separately versioned")
    memory=int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:")))*1024
    free=shutil.disk_usage(root).free;largest=max(r["compressed_bytes"] for r in new["entities"])
    slowest=max(r["seconds"] for r in new["entities"])
    projected_seconds=slowest*fixtures["max_shard_entities"]*1.25+1800
    scratch=1_900_000_000+2*(500_000_000+largest)+512_000_000+7_000_000_000
    limits={"runner_memory_bytes":memory,"free_disk_bytes":free,"peak_rss_bytes":new["peak_rss_bytes"],
            "projected_max_shard_seconds_with_25pct_and_30min_io_margin":projected_seconds,
            "workflow_timeout_seconds":350*60,"scratch_bytes_including_7GB_reserve":scratch,
            "projected_all_entity_compressed_bytes_max_sample_times_universe_with_25pct_margin":largest*fixtures["selected_tickers"]*1.25}
    passed=new["peak_rss_bytes"]<.7*memory and projected_seconds<350*60 and scratch<free and all(n==1 for n in new["schema_variants_by_timeframe"].values())
    report={"status":"PASS_SAMPLE_BUDGET_ONLY" if passed else "BUDGET_REVIEW_REQUIRED","source_commit":os.environ.get("GITHUB_SHA"),
            "request":request,"fixtures":fixtures,"baseline":old,"corrected":new,"limits":limits,
            "compressed_byte_ratio":sum(r["compressed_bytes"] for r in new["entities"])/sum(r["compressed_bytes"] for r in old["entities"]),
            "full_world_gate":"NOT_RUN","scoring_gate":"CLOSED","recipe_review_gate":"PENDING_FULL_VERIFICATION",
            "limitation":"Three deterministic real entities from one published part; projections are measured sample bounds with margins, not full-universe guarantees."}
    (root/"PRICE_MATH_BUDGET_V2.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":report["status"],"limits":limits,"compressed_byte_ratio":report["compressed_byte_ratio"]}),flush=True)
    if not passed:raise RuntimeError("sample budget or schema check requires review")


if __name__=="__main__":main()
