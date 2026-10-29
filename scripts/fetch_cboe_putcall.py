#!/usr/bin/env python3
"""Fetch CBOE daily put/call statistics (I201).
Era 1 (<=2019-10-04): 6 bulk CSVs (Cboe Options Exchange only; spx = SPX only).
Era 2 (>=2019-10-07): one JSON per trading day, ALL Cboe exchanges, SPX+SPXW. DEFINITION BREAK at 2019-10-07.
PIT: day D's file is usable only at the D+1 open (available_from = next session).
Usage: fetch_cboe_putcall.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--out data/cboe_putcall] [--csv-era]
Idempotent: skips days whose raw JSON already exists. Weekends/holidays return 403 (recorded, skipped).
"""
import argparse,csv,datetime as dt,gzip,json,os,sys,time,urllib.request,urllib.error
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
JSON_URL="https://cdn.cboe.com/data/us/options/market_statistics/daily/{d}_daily_options"
CSV_URL="https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/{g}pc.csv"
GROUPS={"total":("SUM OF ALL PRODUCTS","TOTAL PUT/CALL RATIO"),"index":("INDEX OPTIONS","INDEX PUT/CALL RATIO"),
 "etp":("EXCHANGE TRADED PRODUCTS","EXCHANGE TRADED PRODUCTS PUT/CALL RATIO"),"equity":("EQUITY OPTIONS","EQUITY PUT/CALL RATIO"),
 "vix":("CBOE VOLATILITY INDEX (VIX)","CBOE VOLATILITY INDEX (VIX) PUT/CALL RATIO"),"spx":("SPX + SPXW","SPX + SPXW PUT/CALL RATIO")}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*"})
    for a in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as r: return r.status,r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403,404): return e.code,b""
            time.sleep(2*(a+1))
        except Exception: time.sleep(2*(a+1))
    return -1,b""
def fetch_json(out,start,end,pause):
    d=start;raw=os.path.join(out,"raw_json");os.makedirs(raw,exist_ok=True);n=0
    while d<=end:
        if d.weekday()<5:
            p=os.path.join(raw,f"{d}.json.gz")
            if not os.path.exists(p) and not os.path.exists(p+".missing"):
                s,b=get(JSON_URL.format(d=d))
                if s==200: gzip.open(p,"wb").write(b);n+=1
                elif s in (403,404): open(p+".missing","w").write(str(s))
                else: print("ERR",d,s,file=sys.stderr)
                time.sleep(pause)
        d+=dt.timedelta(days=1)
    return n
def tidy(out):
    raw=os.path.join(out,"raw_json");rows={g:[] for g in GROUPS}
    for f in sorted(os.listdir(raw)):
        if not f.endswith(".json.gz"): continue
        day=f[:10];j=json.loads(gzip.open(os.path.join(raw,f)).read())
        rat={r["name"]:r["value"] for r in j.get("ratios",[])}
        nxt=dt.date.fromisoformat(day)+dt.timedelta(days=1)
        while nxt.weekday()>=5: nxt+=dt.timedelta(days=1)
        for g,(blk,rn) in GROUPS.items():
            b={x["name"]:x for x in j.get(blk,[])};v=b.get("VOLUME",{});oi=b.get("OPEN INTEREST",{})
            c,p=v.get("call"),v.get("put")
            rows[g].append([day,str(nxt),c,p,v.get("total"),rat.get(rn,""),round(p/c,6) if c else "",oi.get("call",""),oi.get("put",""),oi.get("total",""),"json_all_cboe_exchanges"])
    for g,r in rows.items():
        with open(os.path.join(out,f"{g}_json_era.csv"),"w",newline="") as fh:
            w=csv.writer(fh);w.writerow(["date","available_from_not_before","call_volume","put_volume","total_volume","published_ratio","pc_recomputed","call_oi","put_oi","total_oi","era"]);w.writerows(r)
    return {g:len(r) for g,r in rows.items()}
def csv_era(out):
    d=os.path.join(out,"csv_era");os.makedirs(d,exist_ok=True);res={}
    for g in GROUPS:
        s,b=get(CSV_URL.format(g=g))
        if s==200: open(os.path.join(d,f"{g}pc.csv"),"wb").write(b);res[g]=b.count(b"\n")
        else: res[g]=f"HTTP {s}"
    return res
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--start",default="2019-10-07");a.add_argument("--end",default=str(dt.date.today()))
    a.add_argument("--out",default="data/cboe_putcall");a.add_argument("--csv-era",action="store_true");a.add_argument("--pause",type=float,default=1.0);a.add_argument("--tidy-only",action="store_true")
    x=a.parse_args()
    if x.csv_era: print("csv_era",csv_era(x.out))
    if not x.tidy_only: print("fetched",fetch_json(x.out,dt.date.fromisoformat(x.start),dt.date.fromisoformat(x.end),x.pause))
    print("tidy",tidy(x.out))
