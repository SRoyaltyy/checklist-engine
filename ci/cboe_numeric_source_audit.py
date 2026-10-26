"""Preserve the approved CBOE numeric histories; never synthesize OHLC."""
import hashlib,io,json,os,time,urllib.request
from pathlib import Path
import pandas as pd

def main():
    root=Path("gap-sources/cboe");root.mkdir(parents=True,exist_ok=True);records={}
    for sid in ("VIX","VIX9D","VIX3M","VVIX","SKEW","OVX","GVZ"):
        url=f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{sid}_History.csv"
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"checklist-engine research"}),timeout=60) as response:raw=response.read()
            (root/(sid+"_raw.csv")).write_bytes(raw)
            lines=raw.decode("utf-8-sig").splitlines()
            start=next(i for i,line in enumerate(lines) if line.split(",")[0].strip().strip('"').upper()=="DATE")
            frame=pd.read_csv(io.StringIO("\n".join(lines[start:])))
            frame.columns=[str(c).strip().upper() for c in frame.columns]
            if "DATE" not in frame:raise ValueError("DATE absent")
            value="CLOSE" if "CLOSE" in frame else sid if sid in frame else None
            if value is None:raise ValueError("no documented index value column")
            frame["DATE"]=pd.to_datetime(frame["DATE"],format="mixed",errors="raise")
            frame=frame[frame.DATE<=pd.Timestamp("2026-10-23")].sort_values("DATE").reset_index(drop=True)
            if frame.DATE.duplicated().any():raise ValueError("duplicate date")
            for c in frame.columns:
                if c!="DATE":frame[c]=pd.to_numeric(frame[c],errors="raise")
            if not len(frame) or frame[value].isna().any():raise ValueError("empty or missing level")
            target=root/(sid+".parquet");frame.to_parquet(target,index=False)
            records[sid]={"status":"PASS" if str(frame.DATE.max())[:10]=="2026-10-23" else "STALE",
                "url":url,"raw_sha256":hashlib.sha256(raw).hexdigest(),"parquet_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                "rows":len(frame),"first_date":str(frame.DATE.min())[:10],"last_date":str(frame.DATE.max())[:10],
                "source_columns":list(frame.columns),"has_true_ohlc":all(c in frame for c in ("OPEN","HIGH","LOW","CLOSE")),
                "point_in_time_rule":"date-only EOD levels usable from the next market session; do not use date D's close",
                "features_built":False}
        except Exception as exc:records[sid]={"status":"FAIL","url":url,"error":str(exc)[:500],"features_built":False}
        print("CBOE_SOURCE",sid,json.dumps(records[sid]),flush=True);time.sleep(1)
    result={"status":"SOURCE_EVALUATION_ONLY","series":records,"run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/"+os.environ["GITHUB_RUN_ID"],
        "source_commit":os.environ["GITHUB_SHA"],"notes":["Close-only series retain their true schema; no artificial open/high/low/volume.",
        "VIX may supply an observed-session alignment calendar after comparison to the accepted SPY price calendar.",
        "No stock context join or measured full-world coverage is claimed."]}
    (root/"CBOE_NUMERIC_SOURCE_STATUS_V1.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
