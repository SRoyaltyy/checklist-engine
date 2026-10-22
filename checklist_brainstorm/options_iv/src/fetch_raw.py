# Fetch DoltHub post-no-preference/options volatility_history, one CSV per year (raw, untouched values).
import sys, csv, json, time, os, urllib.request, urllib.parse
U="https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master"
def q(sql):
    for a in range(8):
        try:
            r=urllib.request.urlopen(U+"?"+urllib.parse.urlencode({"q":sql}),timeout=120)
            j=json.load(r)
            if j.get("query_execution_status")!="Success": raise RuntimeError(j.get("query_execution_message"))
            return j
        except Exception as e:
            print("retry",a,e,flush=True); time.sleep(5*(a+1))
    raise SystemExit("FAILED "+sql)
y=int(sys.argv[1]); lo=f"{y-1}-12-15"; hi=f"{y}-12-31"
out=f"raw/vol_history_{y}.csv"; part=out+".part"
import datetime as dt
dd=dt.date(y-1,12,15); dates=[]
while dd<=dt.date(y,12,31):
    if dd.weekday()<5: dates.append(dd.isoformat())
    dd+=dt.timedelta(1)
print(y,len(dates),"dates",flush=True)
done=set()
if os.path.exists(part):
    with open(part) as f: done={r["date"] for r in csv.DictReader(f)}
cols=None; f=open(part,"a",newline=""); w=None
for d in dates:
    if d in done: continue
    last=''; rows=[]
    while True:
        j=q(f"SELECT * FROM volatility_history WHERE date='{d}' AND act_symbol>'{last}' ORDER BY act_symbol LIMIT 1000")
        rr=j["rows"]; rows+=rr
        if cols is None and j["schema"]: cols=[c["columnName"] for c in j["schema"]]
        if len(rr)<1000: break
        last=rr[-1]["act_symbol"]
    if not rows: continue
    if w is None:
        w=csv.DictWriter(f,fieldnames=cols)
        if os.path.getsize(part)==0: w.writeheader()
    w.writerows(rows); f.flush(); print(d,len(rows),flush=True)
f.close(); os.replace(part,out); print("DONE",y,flush=True)
