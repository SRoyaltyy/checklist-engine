"""Bounded public SQL probes for options coverage planning; never features."""
import gzip,hashlib,json,os,re,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
ROOT=Path("gap-sources/dolt-index")
REF="8fvk999ugbld4o782kvi36k7sv37ljbm"
BASE="https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master"
receipts=[]
def query(name,sql):
    if sql.startswith(("SELECT","EXPLAIN")):
        sql=re.sub(r"FROM (volatility_history|option_chain|dolt_docs)\b",lambda m:m.group(0)+" AS OF '"+REF+"'",sql)
    url=BASE+"?"+urllib.parse.urlencode({"q":sql})
    started=time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"checklist-engine read-only options source evaluation"}),timeout=75) as r:raw=r.read()
        payload=json.loads(raw);status=payload.get("query_execution_status","").lower()
        if status!="success":raise ValueError(str(payload)[:1000])
        rows=payload.get("rows",[]);status="PASS";error=None
    except urllib.error.HTTPError as exc:
        raw=exc.read();rows=None;status="FAIL";error=f"HTTP {exc.code}: "+raw.decode(errors="replace")[:800]
    except Exception as exc:
        raw=json.dumps({"error":str(exc)}).encode();rows=None;status="FAIL";error=str(exc)[:1000]
    with gzip.open(ROOT/(name+".json.gz"),"wb") as f:f.write(raw)
    row={"name":name,"sql":sql,"status":status,"error":error,"elapsed_s":round(time.time()-started,2),
         "raw_sha256":hashlib.sha256(raw).hexdigest(),"rows":rows}
    receipts.append(row);print("DOLT_INDEX_PROBE",json.dumps(row),flush=True)
    time.sleep(1)
    return rows
def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    query("head","SELECT commit_hash,date,message FROM dolt_log LIMIT 1")
    query("documentation","SELECT * FROM dolt_docs LIMIT 3")
    for table in ("volatility_history","option_chain"):
        query(table+"_create","SHOW CREATE TABLE "+table)
        query(table+"_indexes","SHOW INDEX FROM "+table)
        query(table+"_plan","EXPLAIN SELECT act_symbol,date FROM "+table+" WHERE act_symbol='AAPL' AND date>='2020-01-01' AND date<='2026-10-23' ORDER BY date LIMIT 10")
        query(table+"_tiny","SELECT * FROM "+table+" WHERE act_symbol='AAPL' AND date>='2020-01-01' AND date<='2026-10-23' ORDER BY date LIMIT 3")
        query(table+"_bounded","SELECT MIN(date) first_date,MAX(date) last_date,COUNT(DISTINCT date) dates_present FROM "+table+" WHERE act_symbol='AAPL' AND date>='2020-01-01' AND date<'2020-02-01'")
    result={"status":"BOUNDED_SOURCE_DIAGNOSTIC_ONLY","source":"post-no-preference/options","database_ref":REF,"queries":receipts,
            "feature_build_permitted":False,"universe_coverage_pct":None,"run":os.environ["GITHUB_RUN_ID"]}
    (ROOT/"DOLT_OPTIONS_INDEX_PROBE_V3.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
