"""Probe free NYSE TICK histories. Never confuse it with trade-by-trade equity ticks."""
import gzip,hashlib,json,os,re,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
import pandas as pd

ROOT=Path("tick-source");records=[]
def get(name,url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"checklist-engine source coverage research"}),timeout=60) as r:
            raw=r.read();status=r.status
    except urllib.error.HTTPError as exc:raw=exc.read();status=exc.code
    except Exception as exc:raw=str(exc).encode();status=None
    with gzip.open(ROOT/(name+".raw.gz"),"wb") as f:f.write(raw)
    row={"name":name,"url":url,"http_status":status,"bytes":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),"usable_complete_history":False}
    records.append(row);print("TICK_SOURCE",name,status,len(raw),flush=True);time.sleep(1)
    return raw,row

def main():
    ROOT.mkdir(exist_ok=True)
    urls=[
      ("investing_page","https://www.investing.com/indices/nyse-tick-index-historical-data"),
      ("sierra_statistics","https://www.sierrachart.com/index.php?page=doc/SCMarketStatistics.php"),
      ("sierra_service","https://www.sierrachart.com/index.php?page=doc/SierraChartHistoricalData.php"),
      ("eoddata","https://www.eoddata.com/stockquote/INDEX/TICK.htm"),
      ("stockcharts","https://stockcharts.com/h-sc/ui?s=%24TICK&p=D&b=5"),
    ]
    investing=None
    for name,url in urls:
        raw,row=get(name,url)
        if name=="investing_page":investing=raw.decode("utf-8",errors="replace")
        if name.startswith("sierra"):row["finding"]="Provider documents historical TICK-NYSE, but service package/account access is required; no paid access requested."
        if name=="eoddata":row["finding"]="Recent public quotes do not prove free complete 2020-present history. Full EOD history is offered for purchase; quote basis/identity must be verified."
        if name=="stockcharts":row["finding"]="Public chart view is not a fetched complete numeric history."
    if investing:
        ids=set(re.findall(r'(?:pair_ID|pairId|pair_id|instrumentId|instrument_id)[\\"\s:=]+([0-9]{2,12})',investing))
        (ROOT/"investing_candidate_ids.json").write_text(json.dumps(sorted(ids)))
        if len(ids)==1:
            ident=next(iter(ids));qs=urllib.parse.urlencode({"start-date":"2020-01-01","end-date":"2026-10-23","time-frame":"Daily","add-missing-rows":"false"})
            raw,row=get("investing_api","https://api.investing.com/api/financialdata/historical/"+ident+"?"+qs)
            row["finding"]="Public API probe only; successful JSON still needs identity/date-completeness validation before use."
        else:records[0]["candidate_ids"]=sorted(ids);records[0]["finding"]="Historical page inspected; no unique verified instrument id, so no blind id substitution."
    for symbol in ("^TICK","TICK-NYSE","^TIC.N"):
        qs=urllib.parse.urlencode({"period1":1577836800,"period2":1792800000,"interval":"1d"})
        raw,row=get("yahoo_"+symbol.encode().hex(),"https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol,safe="")+"?"+qs)
        try:
            payload=json.loads(raw);values=payload["chart"].get("result") or []
            if values:
                result=values[0];row["vendor_metadata"]=result.get("meta",{})
                dates=pd.to_datetime(result.get("timestamp",[]),unit="s",utc=True).tz_convert("America/New_York").strftime("%Y-%m-%d")
                row["observed_daily_dates"]=len(set(dates));row["first_date"]=min(dates) if len(dates) else None;row["last_date"]=max(dates) if len(dates) else None
                row["finding"]="Data not accepted until the vendor explicitly identifies the NYSE uptick-minus-downtick index and full session coverage is checked."
            else:row["finding"]=str(payload["chart"].get("error","no result"))[:500]
        except Exception:row["finding"]="No verified Yahoo NYSE TICK history parsed."
    for symbol in ("^tick","tick.nyse"):
        raw,row=get("stooq_"+symbol.encode().hex(),"https://stooq.com/q/d/l/?"+urllib.parse.urlencode({"s":symbol,"i":"d","d1":"20200101","d2":"20261023"}))
        row["finding"]="Response preserved; no acceptance without documented NYSE TICK identity and complete numeric date keys."
    report={"status":"SOURCE_PROBES_NOT_COMPLETE_HISTORY","requested":["2020-01-01","2026-10-23"],
      "run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/"+os.environ["GITHUB_RUN_ID"],
      "source_commit":os.environ["GITHUB_SHA"],"probes":records,
      "feature_requirements":{"daily":["close","high","low"],"intraday_only":["count of extreme readings"]},
      "notes":["NYSE TICK is reopened under box 1.200, not a final 1.199 exclusion.",
      "Daily highs/lows cannot reveal how many extreme intraday readings occurred.",
      "A blocked or unverified candidate is not a zero column or a proxy.",
      "No paid source, credential purchase, authentication bypass or TLS-verification override."]}
    (ROOT/"NYSE_TICK_SOURCE_PROBE_V1.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":main()
