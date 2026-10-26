"""Append only the four skips retained by the 16:50/16:55 owner updates."""
import csv,json,re
from pathlib import Path

def main():
    method=Path("METHODOLOGY.md").read_text()
    section=method.split("### 0b.",1)[1].split("## 0c.",1)[0]
    newest=re.search(r"\*\*2026-10-26 ~([0-9:]+) HKT",section)
    if not newest or newest.group(1)!="16:55":raise ValueError("Owner policy changed; root must re-read before publishing skips")
    target=Path("docs/WORLD_COVERAGE.csv")
    with target.open(newline="",encoding="utf-8") as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    skipped=[
       ("MAX_PAIN","Max pain","No free PIT historical strike-level open-interest source verified. Retained live-only by owner 16:50/16:55, pending DoltHub chain evaluation."),
       ("MAX_OI_STRIKES","Max-OI strikes","No free PIT historical strike-level open interest verified. Retained live-only by owner 16:50/16:55, pending DoltHub chain evaluation."),
       ("UNUSUAL_ACTIVITY","Unusual-activity flag","No free PIT historical option-activity baseline verified; owner 16:55 retains live-only. No paid source."),
       ("IMPLIED_CORRELATION","Implied correlation","No free PIT historical series verified for the requested measure; owner 16:55 retains live-only. No paid source.")]
    keys={"LIVE_ONLY_"+x[0] for x in skipped}
    rows=[r for r in rows if not (r["namespace"]=="series" and r["item_id"] in keys)]
    added=[]
    for ident,item,reason in skipped:
        for tf in [f"{k}d" for k in range(1,22)]+["monthly"]:
            row={k:"" for k in fields};row.update(namespace="series",item_id="LIVE_ONLY_"+ident,item=item,
                timeframe=tf,block="O",status="EXCLUDED_LIVE_ONLY",reason=reason,
                source_evidence=json.dumps({"policy":"METHODOLOGY 0b 2026-10-26 16:50 and 16:55 HKT","no_fetch":True}),
                column_measurements="{}",universe_scope="EXCLUDED_LIVE_ONLY_NOT_HISTORICAL_INPUT")
            added.append(row)
    if len(added)!=88 or any(not r["reason"] or r["snapshot_columns"] or r["non_null_pct_2020_2026"] for r in added):raise ValueError("invalid exclusions")
    with target.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows+added)
    status={"status":"RETAINED_OWNER_LIVE_ONLY_SKIPS_LOGGED","distinct_series":4,"excluded_timeframe_rows":88,
        "source":"docs/WORLD_COVERAGE.csv namespace=series status=EXCLUDED_LIVE_ONLY",
        "reopened_not_excluded":["NYSE_TICK","ATM_IV","IV_RANK","IV_PERCENTILE","DELTA25_SKEW","RISK_REVERSAL","HV_MINUS_IV"],
        "options_history_evaluation":"PENDING_DOLT_LOG_REVIEW","fetched_series":0,"zero_columns_added":0,
        "ticker_exclusion_roster":"docs/EXCLUDED.csv unchanged, 280 tickers",
        "existing_scope":"Existing historical measurements remain provisional; no world gate is passed."}
    Path("docs/LIVE_ONLY_EXCLUSIONS_STATUS_V1.json").write_text(json.dumps(status,indent=2)+"\n")
    print(json.dumps(status))
if __name__=="__main__":main()
