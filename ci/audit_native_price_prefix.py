"""Rebuild the released four-entity price smoke after removing future bars."""
import hashlib,io,json,os,tarfile
from pathlib import Path
import numpy as np
import pandas as pd
import facets_world as fw
from world_timeframes import completed_candles,candle_features,TIMEFRAMES
from ci.native_price_blocks import download,sha,write_json,gh,recipe_fingerprint
INPUTS="native-price-inputs-v1-40333811160-1"
BLOCKS="native-price-blocks-v1-40333811160-1-000"
def main():
    root=Path("native-prefix");root.mkdir(exist_ok=True)
    inputs=json.loads(download(INPUTS,"BUILD_INPUTS.json",root).read_text())
    if inputs["recipe_fingerprint"]!=recipe_fingerprint()[0]:raise ValueError("smoke recipe changed")
    summary=json.loads(download(BLOCKS,"SHARD_COMPLETE.json",root).read_text())
    if set(r["ticker"] for r in summary["records"])!={"SPY","AAPL","MSFT","NVDA"}:raise ValueError("unexpected smoke cohort")
    calfile=download(INPUTS,"market_sessions.parquet",root)
    if sha(calfile)!=inputs["calendar_sha256"]:raise ValueError("calendar fingerprint differs")
    calendar=pd.DatetimeIndex(pd.read_parquet(calfile).date)
    funcs=fw.discover();checks=[];failures=[];tested_columns=0
    for part in summary["parts"]:
        report=json.loads(download(part["release"],part["part"]+".json",root).read_text())
        archive=download(part["release"],part["part"]+".tar",root)
        if sha(archive)!=part["archive_sha256"]:raise ValueError("released part archive changed")
        members={r["name"]:r for r in report["members"]}
        with tarfile.open(archive) as tar:
            def read(name):
                raw=tar.extractfile(name).read()
                if len(raw)!=members[name]["bytes"] or hashlib.sha256(raw).hexdigest()!=members[name]["sha256"]:
                    raise ValueError("released member changed: "+name)
                return pd.read_parquet(io.BytesIO(raw))
            for ticker in part["tickers"]:
                prefix=ticker.encode().hex();bars=read(prefix+".bars.parquet")
                for cut in (pd.Timestamp("2023-01-03"),pd.Timestamp("2025-01-02")):
                    prior=bars[bars.date<cut];cal=calendar[calendar<=cut]
                    for tf in TIMEFRAMES:
                        released=read(prefix+"."+tf+".parquet")
                        released=released[released.available_from<=cut].reset_index(drop=True)
                        candles=completed_candles(prior,tf,session_calendar=cal)
                        rebuilt=candle_features(candles,funcs,timeframe=tf)
                        columns=[c for c in rebuilt if c!="available_from"]
                        expected=[c for c in released if c not in ("ticker","available_from","candle_start","source_candle_end")]
                        if set(columns)!=set(expected) or not rebuilt.available_from.reset_index(drop=True).equals(released.available_from):
                            raise ValueError("prefix schema/availability differs: "+ticker+" "+tf+" "+str(cut))
                        bad=[]
                        for column in columns:
                            a=rebuilt[column].to_numpy(dtype=float);b=released[column].to_numpy(dtype=float)
                            if not np.allclose(a,b,rtol=1e-5,atol=1e-6,equal_nan=True):bad.append(column)
                        tested_columns+=len(columns)
                        row={"ticker":ticker,"cut":str(cut)[:10],"timeframe":tf,"columns":len(columns),"native_rows":len(rebuilt),"mismatch_columns":bad}
                        checks.append(row)
                        if bad:failures.append(row)
                    print("NATIVE_PREFIX_CUT_CHECKED",ticker,str(cut)[:10],flush=True)
        archive.unlink()
    report={"status":"FAIL" if failures else "PASS_SAMPLE_ONLY_NOT_FULL_WORLD_LEAK_GATE","tickers":4,
            "cuts":["2023-01-03","2025-01-02"],"timeframes":list(TIMEFRAMES),"blocks_checked":len(checks),
            "column_checks":tested_columns,"mismatch_blocks":len(failures),"checks":checks,
            "inputs_tag":INPUTS,"blocks_tag":BLOCKS,"recipe_fingerprint":inputs["recipe_fingerprint"],
            "source_commit":os.environ["GITHUB_SHA"],"full_world_leak_gate":"NOT_RUN"}
    file=root/"NATIVE_PRICE_PREFIX_SMOKE_V1.json";write_json(file,report)
    tag=f"native-price-prefix-smoke-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh("release","create",tag,file,"--title",tag,"--notes","Four real entities and two cuts, all native price-feature columns. Sample only; no full-world leak approval.","--target",os.environ["GITHUB_SHA"])
    print("NATIVE_PREFIX_SMOKE_RESULT",report["status"],len(checks),tested_columns,len(failures),flush=True)
    if failures:raise ValueError("future truncation changed prefix values: "+json.dumps(failures[:10]))
if __name__=="__main__":main()
