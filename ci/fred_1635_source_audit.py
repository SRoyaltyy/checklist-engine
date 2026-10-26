"""Checkpoint each newly requested ALFRED series independently."""
import hashlib,json,os,time
from pathlib import Path
import pandas as pd
from fetch.fetch_fred import first_vintage,alfred_observations

SERIES=[
("T10Y3M","T10Y3M"),("T5YIE","T5YIE"),("T10YIE","T10YIE"),
("STICKCPIM159S","STICKCPIM159SFRBATL"),("DFII10","DFII10"),
("CIVPART","CIVPART"),("INDPRO","INDPRO"),("BUSLOANS","BUSLOANS")]

def main():
    key=os.environ.get("FRED_API_KEY","")
    if not key:raise RuntimeError("BLOCKED_SECRET: FRED_API_KEY absent")
    root=Path("gap-sources/fred");root.mkdir(parents=True,exist_ok=True)
    report={"status":"RUNNING","source":"FRED/ALFRED","series":{},
       "source_commit":os.environ["GITHUB_SHA"],
       "run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/"+os.environ["GITHUB_RUN_ID"],
       "identifier_mapping_note":"Requested sticky-CPI shorthand STICKCPIM159S has no ALFRED archive. Official ALFRED Sticky Price CPI is STICKCPIM159SFRBATL; both identifiers are retained, not silently relabelled.",
       "identifier_source":"https://alfred.stlouisfed.org/series?seid=STICKCPIM159SFRBATL",
       "features_built":False}
    target=root/"fred_1635.source.json";frames=[]
    for requested,actual in SERIES:
        try:
            available=first_vintage(key,actual)
            rows=alfred_observations(key,actual,available_from=available)
            if not rows:raise ValueError("no numeric vintage rows")
            frame=pd.DataFrame(rows).drop_duplicates()
            frame["requested_series"]=requested
            file=root/(actual+".parquet");frame.to_parquet(file,index=False)
            frames.append(frame)
            report["series"][requested]={"status":"PASS","source_series":actual,"requested_series":requested,
               "archive_first_vintage":available,"rows":len(frame),
               "first_obs":str(frame.obs_date.min()),"last_obs":str(frame.obs_date.max()),
               "first_vintage":str(frame.vintage_date.min()),"last_vintage":str(frame.vintage_date.max()),
               "parquet_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
               "point_in_time_rule":"vintage_date < D; preserve original and subsequent filing/release versions"}
        except Exception as exc:
            report["series"][requested]={"status":"FAIL","source_series":actual,"error":str(exc).replace(key,"[REDACTED]")[:500]}
        target.write_text(json.dumps(report,indent=2)+"\n")
        print("FRED_SERIES_CHECKPOINT",requested,json.dumps(report["series"][requested]),flush=True);time.sleep(1.5)
    report["status"]="PASS" if all(r["status"]=="PASS" for r in report["series"].values()) and len(report["series"])==8 else "PARTIAL_SOURCE_FAILURES_NOT_WORLD_GATE"
    if frames:
        combined=pd.concat(frames,ignore_index=True);file=root/"fred_1635.parquet";combined.to_parquet(file,index=False)
        report["combined_rows"]=len(combined);report["parquet_sha256"]=hashlib.sha256(file.read_bytes()).hexdigest()
    target.write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":main()
