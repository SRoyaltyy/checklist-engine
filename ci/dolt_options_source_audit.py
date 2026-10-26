"""Read-only DoltHub coverage evaluation. No options feature construction."""
import csv,gzip,hashlib,json,os,time,urllib.request,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd

ROOT=Path("gap-sources/dolt")
BASE="https://www.dolthub.com/api/v2/databases/post-no-preference/options/sql"
REF="master"
receipts=[]
def query(name,sql,limit=1000):
    body=json.dumps({"ref":REF,"q":sql,"limit":limit,"timeout_ms":60000}).encode()
    req=urllib.request.Request(BASE,data=body,headers={"Content-Type":"application/json","User-Agent":"checklist-engine source coverage research"},method="POST")
    started=time.time()
    try:
        with urllib.request.urlopen(req,timeout=90) as response:raw=response.read()
        payload=json.loads(raw)
        data=payload.get("data",payload)
        status=data.get("status",data.get("query_execution_status","")).lower()
        if status!="success":raise ValueError("query status "+status+": "+str(data.get("message",""))[:300])
        rows=data.get("rows",[])
        if rows and isinstance(rows[0],list):
            columns=[c.get("name",c.get("columnName")) for c in data["columns"]]
            rows=[dict(zip(columns,row)) for row in rows]
        status="PASS";error=None
    except Exception as exc:
        raw=json.dumps({"error":str(exc)[:500]}).encode();rows=None;status="FAIL";error=str(exc)[:500]
    path=ROOT/(name+".json.gz")
    with gzip.open(path,"wb") as f:f.write(raw)
    (ROOT/(name+".sql")).write_text(sql)
    receipts.append({"name":name,"sql_file":name+".sql","sql_sha256":hashlib.sha256(sql.encode()).hexdigest(),"ref":REF,"status":status,"error":error,
        "elapsed_s":round(time.time()-started,2),"raw_sha256":hashlib.sha256(raw).hexdigest(),"raw_file":path.name,
        "returned_rows":len(rows) if rows is not None else None})
    print("DOLT_QUERY",name,status,len(rows) if rows is not None else error,flush=True)
    time.sleep(1)
    return rows

def main():
    global REF
    ROOT.mkdir(parents=True,exist_ok=True)
    with Path("docs/ACCEPTED_PRICE_INVENTORY_V6.csv").open() as f:accepted=list(csv.DictReader(f))
    universe={r["ticker"] for r in accepted};stocks={r["ticker"] for r in accepted if r["current_listing_classification"]=="NON_ETF"}
    head=query("head","SELECT commit_hash,date,message FROM dolt_log LIMIT 1")
    if head and head[0].get("commit_hash"):REF=head[0]["commit_hash"]
    pinned=REF!="master"
    tables=query("tables","SHOW TABLES")
    results={}
    for table in ("volatility_history","option_chain"):
        schema=query(table+"_schema","SHOW COLUMNS FROM "+table)
        columns={str(r.get("Field",r.get("field",""))).lower() for r in schema or []}
        result={"schema_columns":sorted(columns),"has_open_interest":bool(columns&{"open_interest","openinterest","oi"}),
            "publication_timestamp_fields":sorted(c for c in columns if any(x in c for x in ("publish","capture","available","timestamp")))}
        stats=query(table+"_totals",f"SELECT MIN(date) first_date,MAX(date) last_date,COUNT(*) raw_rows,COUNT(DISTINCT date) dates_present,COUNT(DISTINCT act_symbol) symbols FROM {table}")
        result["global_totals"]=stats[0] if stats else None
        # Exact symbol-level date counts with keyset pages; errors remain unknown.
        grouped=[];last="";complete=False
        for page in range(40):
            where="date>='2020-01-01' AND date<='2026-10-23'"
            if last:where+=" AND act_symbol>'"+last.replace("'","''")+"'"
            rows=query(table+f"_symbol_page_{page:02}",
                f"SELECT act_symbol,MIN(date) first_date,MAX(date) last_date,COUNT(DISTINCT date) dates_present FROM {table} WHERE {where} GROUP BY act_symbol ORDER BY act_symbol LIMIT 500",500)
            if rows is None:break
            grouped.extend(rows)
            if len(rows)<500:complete=True;break
            next_last=str(rows[-1]["act_symbol"])
            if next_last<=last:raise ValueError("Dolt keyset page did not advance")
            last=next_last
        by_symbol={str(r["act_symbol"]):r for r in grouped}
        matched=universe&set(by_symbol);stock_matched=stocks&set(by_symbol)
        result.update(symbol_aggregation_complete=complete,observed_source_symbols=len(by_symbol),
            matched_accepted_tickers=len(matched),accepted_universe=len(universe),
            accepted_ticker_presence_pct=100*len(matched)/len(universe) if complete else None,
            matched_current_non_etf=len(stock_matched),current_non_etf_universe=len(stocks),
            current_non_etf_ticker_presence_pct=100*len(stock_matched)/len(stocks) if complete else None,
            unmatched_accepted_tickers=sorted(universe-set(by_symbol)) if complete else None,
            unmatched_names_status="CONFIRMED_ABSENT" if complete else "NOT_OBSERVED_PARTIAL_QUERY",
            identity_rule="exact canonical symbol only, no silent aliases/remapping",
            date_counts_scope="source date keys, not verified exchange-session or post-IPO/PIT tradeable denominators")
        # Exact annual date-key counts for accepted symbols. No large chain download.
        escaped=",".join("'"+s.replace("'","''")+"'" for s in sorted(universe))
        yearly=[]
        for year in range(2020,2027):
            stop=min(f"{year}-12-31","2026-10-23")
            got=query(table+f"_year_{year}",
                f"SELECT date,COUNT(DISTINCT act_symbol) symbols_present FROM {table} WHERE date>='{year}-01-01' AND date<='{stop}' AND act_symbol IN ({escaped}) GROUP BY date ORDER BY date",400)
            yearly.append({"year":year,"status":"PASS" if got is not None else "UNMEASURED_QUERY_FAILED",
                 "source_dates":len(got) if got is not None else None,
                 "observed_ticker_date_pairs":sum(int(r["symbols_present"]) for r in got) if got is not None else None})
            if got is not None:
                with (ROOT/(table+f"_dates_{year}.csv")).open("w",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=["date","symbols_present"]);w.writeheader();w.writerows(got)
        result["yearly_accepted_source_date_counts"]=yearly
        result["pit_status"]="UNVERIFIED: date keys alone do not establish original publication time, revision history or ATM definition"
        result["features_permitted"]=False
        results[table]=result
        with (ROOT/(table+"_symbol_coverage.csv")).open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["act_symbol","first_date","last_date","dates_present"]);w.writeheader();w.writerows(grouped)
    summary={"status":"SOURCE_EVALUATION_ONLY_NO_FEATURES","source":"post-no-preference/options",
      "source_url":"https://www.dolthub.com/repositories/post-no-preference/options",
      "evaluated_at":datetime.now(timezone.utc).isoformat(),"database_ref":REF,"database_revision_pinned":pinned,
      "period_requested":["2020-01-01","2026-10-23"],"source_commit":os.environ["GITHUB_SHA"],
      "run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/"+os.environ["GITHUB_RUN_ID"],
      "accepted_inventory_sha256":hashlib.sha256(Path("docs/ACCEPTED_PRICE_INVENTORY_V6.csv").read_bytes()).hexdigest(),
      "tables":results,"queries":receipts,
      "reopening_decision":"PENDING_JAMES_REVIEW: no options features built, no final ATM-IV/skew/risk-reversal/HV-minus-IV exclusion",
      "notes":["Finviz Elite supplies current snapshots only; not historical backfill per owner 16:55.",
               "Ticker presence is not daily completeness or PIT validity.",
               "Unsuccessful queries have null coverage, never fabricated zero coverage.",
               "Source vol fields are not automatically option volume or open interest."] }
    (ROOT/"DOLT_OPTIONS_SOURCE_COVERAGE_V1.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("DOLT_AUDIT_DONE",json.dumps({k:v for k,v in summary.items() if k not in ("tables","queries")}),flush=True)
if __name__=="__main__":main()
