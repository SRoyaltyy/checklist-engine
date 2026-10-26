"""Log the tested NYSE TICK free-history gap without adding zero columns."""
import csv,hashlib,json,re
from pathlib import Path
def main():
    method=Path("METHODOLOGY.md").read_text(encoding="utf-8")
    section=method.split("### 0b.",1)[1].split("## 0c.",1)[0]
    newest=re.search(r"\*\*2026-10-26 ~([0-9:]+) HKT",section)
    if not newest or newest.group(1)!="16:55":raise ValueError("Owner policy changed; re-read before exclusion publication")
    first=Path("docs/NYSE_TICK_SOURCE_PROBE_V1.json");last=Path("docs/NYSE_TICK_SOURCE_FOLLOWUP_V4.json")
    a=json.loads(first.read_text());b=json.loads(last.read_text())
    if b.get("verified_page_instrument_id")!="961122" or not any(r["http_status"]==403 for r in b["probes"]):
        raise ValueError("missing actual verified-identity API refusal")
    attempts=[{"name":p["name"],"url":p["url"],"http_status":p["http_status"],"finding":p.get("finding","No complete numeric daily history verified.")} for p in a["probes"]]
    attempts += [dict(p,name="verified_investing_history_api",finding="Exact NYSE TICK identity; ordinary 2020 historical API access returned HTTP403. Stopped without bypass.") for p in b["probes"]]
    report={"status":"NOT_AVAILABLE_FREE_FROM_TESTED_SOURCES","item_id":"NYSE_TICK","requested":["2020-01-01","2026-10-23"],
            "attempts":attempts,"latest_followup_run":b["run"],"source_release":a["run"],"zero_columns_added":0,
            "numeric_history_built":False,"ticker_roster_modified":False,
            "reason":"No tested free source yielded complete 2020-present numeric history. Investing verified id961122 API403; Yahoo candidates404; Stooq browser verification; Sierra/EODData require paid/account history; StockCharts public chart is not a complete numeric download.",
            "extreme_readings":"No intraday history. An extreme count cannot be inferred from daily high/low.",
            "evidence_sha256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (first,last)},
            "options_IV_exclusion":"UNCHANGED_PENDING_DOLT; no options decision made here"}
    target=Path("docs/WORLD_COVERAGE.csv")
    with target.open(newline="",encoding="utf-8") as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    if any(r["namespace"]=="series" and r["item_id"]=="NYSE_TICK" for r in rows):raise ValueError("TICK already logged; inspect before changing published record")
    added=[]
    for tf in [str(k)+"d" for k in range(1,22)]+["monthly"]:
        row={k:"" for k in fields};row.update(namespace="series",item_id="NYSE_TICK",item="NYSE uptick-minus-downtick index",
            timeframe=tf,block="K",status="NOT_AVAILABLE_FREE",reason=report["reason"],
            source_evidence=json.dumps({"receipt":"docs/NYSE_TICK_SOURCE_EXCLUSION_V1.json","source_probes":str(first),"verified_identity_followup":str(last)}),
            column_measurements="{}",universe_scope="NO_COMPLETE_FREE_HISTORY_FROM_TESTED_SOURCES")
        added.append(row)
    with target.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows+added)
    report["coverage_rows_logged"]=len(added);report["coverage_sha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
    Path("docs/NYSE_TICK_SOURCE_EXCLUSION_V1.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("NYSE_TICK_GAP_LOGGED",len(added),len(attempts),flush=True)
if __name__=="__main__":main()
