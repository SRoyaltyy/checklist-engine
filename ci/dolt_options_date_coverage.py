"""Date-indexed options source measurement, with branch revision guards."""
import csv,gzip,hashlib,json,os,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path("dolt-coverage-v5");REF="8fvk999ugbld4o782kvi36k7sv37ljbm"
BASE="https://www.dolthub.com/api/v2/databases/post-no-preference/options/sql"
receipts=[]
def query(name,sql,limit=1000):
    body=json.dumps({"ref":"master","q":sql,"limit":limit,"timeout_ms":60000}).encode();started=time.time()
    try:
        request=urllib.request.Request(BASE,data=body,headers={"Content-Type":"application/json","User-Agent":"checklist-engine read-only source coverage"},method="POST")
        with urllib.request.urlopen(request,timeout=75) as response:raw=response.read()
        data=json.loads(raw).get("data",{})
        if data.get("status","").lower()!="success":raise ValueError(str(data)[:1000])
        rows=data["rows"]
        if rows and isinstance(rows[0],list):
            columns=[c.get("name",c.get("columnName")) for c in data["columns"]];rows=[dict(zip(columns,r)) for r in rows]
        status="PASS";error=None
    except urllib.error.HTTPError as exc:raw=exc.read();rows=None;status="FAIL";error=f"HTTP {exc.code}: "+raw.decode(errors="replace")[:800]
    except Exception as exc:raw=json.dumps({"error":str(exc)}).encode();rows=None;status="FAIL";error=str(exc)[:1000]
    with gzip.open(ROOT/(name+".json.gz"),"wb") as f:f.write(raw)
    receipts.append({"name":name,"sql":sql,"status":status,"error":error,"elapsed_s":round(time.time()-started,2),
                     "raw_sha256":hashlib.sha256(raw).hexdigest(),"returned_rows":len(rows) if rows is not None else None})
    print("DOLT_COVERAGE_QUERY",name,status,len(rows) if rows is not None else error,round(time.time()-started,2),flush=True)
    return rows
def pin(name):
    rows=query(name,"SELECT commit_hash FROM dolt_log LIMIT 1")
    if not rows or rows[0]["commit_hash"]!=REF:raise ValueError("database revision changed/unverified")
def main():
    ROOT.mkdir(exist_ok=True);pin("head_before")
    with Path("docs/ACCEPTED_PRICE_INVENTORY_V6.csv").open() as f:inventory=list(csv.DictReader(f))
    accepted={r["ticker"] for r in inventory};stocks={r["ticker"] for r in inventory if r["current_listing_classification"]=="NON_ETF"}
    result={"status":"SOURCE_COVERAGE_EVALUATION_ONLY","database_ref":REF,"revision_guard":"exact same master head before and after; no AS OF materialization",
            "accepted_universe":len(accepted),"current_non_etf_universe":len(stocks),"tables":{},"features_permitted":False,
            "source_commit":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"]}
    for table in ("volatility_history","option_chain"):
        first=query(table+"_first","SELECT date FROM "+table+" ORDER BY date LIMIT 1")
        last=query(table+"_last","SELECT date FROM "+table+" ORDER BY date DESC LIMIT 1")
        sample_dates=("2020-01-04","2026-10-23")
        samples=[]
        for date in sample_dates:
            got=[];after="";complete=False
            for page in range(10):
                where="date='"+date+"'"+(" AND act_symbol>'"+after.replace("'","''")+"'" if after else "")
                rows=query(table+"_"+date+f"_{page:02}",f"SELECT act_symbol FROM {table} WHERE {where} GROUP BY act_symbol ORDER BY act_symbol LIMIT 1000")
                if rows is None:break
                got.extend(str(r["act_symbol"]) for r in rows)
                if len(rows)<1000:complete=True;break
                after=str(rows[-1]["act_symbol"])
            symbols=set(got);samples.append({"date":date,"complete":complete,"source_symbols":len(symbols),
                "matched_accepted":len(symbols&accepted),"accepted_presence_pct":100*len(symbols&accepted)/len(accepted) if complete else None,
                "matched_non_etf":len(symbols&stocks),"non_etf_presence_pct":100*len(symbols&stocks)/len(stocks) if complete else None,
                "unmatched_accepted":sorted(accepted-symbols) if complete else None,"source_symbols_list":sorted(symbols)})
        result["tables"][table]={"first_source_date":first[0]["date"] if first else None,"last_source_date":last[0]["date"] if last else None,"date_samples":samples}
    # Lighter table: exact ticker/date counts across the whole requested interval.
    grouped=[];after="";complete=False
    for page in range(10):
        clause="date>='2020-01-01' AND date<='2026-10-23'"+(" AND act_symbol>'"+after.replace("'","''")+"'" if after else "")
        rows=query("volatility_symbol_"+str(page),f"SELECT act_symbol,MIN(date) first_date,MAX(date) last_date,COUNT(*) dates_present,SUM(iv_current IS NOT NULL) iv_rows,SUM(hv_current IS NOT NULL) hv_rows FROM volatility_history WHERE {clause} GROUP BY act_symbol ORDER BY act_symbol LIMIT 1000")
        if rows is None:break
        grouped.extend(rows)
        if len(rows)<1000:complete=True;break
        after=str(rows[-1]["act_symbol"])
    symbols={str(r["act_symbol"]) for r in grouped}
    result["tables"]["volatility_history"].update(full_symbol_aggregation_complete=complete,
        accepted_ticker_presence_pct=100*len(symbols&accepted)/len(accepted) if complete else None,
        non_etf_ticker_presence_pct=100*len(symbols&stocks)/len(stocks) if complete else None,
        unmatched_accepted_tickers=sorted(accepted-symbols) if complete else None,symbol_records=grouped)
    daily=query("volatility_jan2020_dates","SELECT date,COUNT(*) symbols_present FROM volatility_history WHERE date>='2020-01-01' AND date<'2020-02-01' GROUP BY date ORDER BY date")
    result["tables"]["volatility_history"]["jan2020_source_date_counts"]=daily
    pin("head_after");result["revision_guards_passed"]=True;result["queries"]=receipts
    result["point_in_time_status"]="UNVERIFIED: source date includes non-session labels; no publication timestamps, vintage truth or ATM definition yet"
    result["chain_open_interest"]="ABSENT_FROM_CONFIRMED_SCHEMA; cannot derive put/call OI, max-pain or max-OI"
    result["full_daily_universe_coverage"]="NOT_YET_MEASURED; date samples and ticker presence are explicitly different metrics"
    (ROOT/"DOLT_OPTIONS_COVERAGE_V5.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
