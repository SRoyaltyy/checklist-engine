"""Inspect saved public TICK identity, then test ordinary public history access."""
import csv,gzip,hashlib,html,io,json,os,re,subprocess,tarfile,urllib.request,urllib.parse,urllib.error
from pathlib import Path
ROOT=Path("tick-followup")
TAG="nyse-tick-source-v1-40308374864-1"
def get(name,url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"checklist-engine source coverage research"}),timeout=60) as r:raw=r.read();status=r.status
    except urllib.error.HTTPError as exc:raw=exc.read();status=exc.code
    except Exception as exc:raw=str(exc).encode();status=None
    (ROOT/(name+".raw")).write_bytes(raw)
    return raw,{"url":url,"http_status":status,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
def main():
    ROOT.mkdir(exist_ok=True)
    subprocess.run(["gh","release","download",TAG,"-p","nyse_tick_source.tar.gz","-p","nyse_tick_source.sha256","-D",str(ROOT)],check=True)
    archive=ROOT/"nyse_tick_source.tar.gz";wanted=(ROOT/"nyse_tick_source.sha256").read_text().split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=wanted:raise ValueError("prior TICK evidence changed")
    with tarfile.open(archive) as tar:raw=tar.extractfile("tick-source/investing_page.raw.gz").read()
    page=gzip.decompress(raw).decode("utf-8",errors="replace")
    scripts=re.findall(r"<script[^>]*>(.*?)</script>",page,re.S|re.I)
    documents=[]
    for text in scripts:
        try:documents.append(json.loads(text))
        except Exception:pass
    candidates=[];matching_names=[]
    def walk(value,where):
        if isinstance(value,dict):
            names=[str(value[k]) for k in ("name","shortName","fullName","instrumentName","displayName","longName") if k in value and isinstance(value[k],str)]
            # The page binds name.fullName and id on the same instrument object.
            if isinstance(value.get("name"),dict):
                names += [str(value["name"][k]) for k in ("fullName","shortName") if isinstance(value["name"].get(k),str)]
            matched=[n for n in names if re.sub(r"[^a-z]","",n.lower()) in ("nysetick","nysetickindex")]
            if matched:
                ids={k:str(value[k]) for k in ("id","instrumentId","instrument_id","pairId","pair_ID","pair_id") if k in value and str(value[k]).isdigit()}
                if isinstance(value.get("base"),dict):
                    for key in ("id","instrumentId","instrument_id","pairId","pair_ID","pair_id"):
                        if key in value["base"] and str(value["base"][key]).isdigit():ids["base."+key]=str(value["base"][key])
                matching_names.append({"path":where,"names":matched,"ids":ids,"keys":list(value)[:40]})
                for key,ident in ids.items():candidates.append({"path":where,"name":matched[0],"id_field":key,"instrument_id":ident})
            for key,item in value.items():walk(item,where+"."+str(key))
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,where+"["+str(i)+"]")
    for i,doc in enumerate(documents):walk(doc,"script"+str(i))
    ids={r["instrument_id"] for r in candidates}
    result={"status":"NO_COMPLETE_FREE_HISTORY_PROVEN","source_evidence_release":TAG,"prior_archive_sha256":wanted,
            "json_scripts":len(documents),"matching_name_objects":matching_names,"identity_candidates":candidates,
            "probes":[],"extreme_reading_count":"UNAVAILABLE_FROM_DAILY_OHLC",
            "run":os.environ["GITHUB_RUN_ID"],"no_bypass":True}
    print("TICK_IDENTITIES",json.dumps(matching_names),flush=True)
    if len(ids)==1:
        ident=next(iter(ids));result["verified_page_instrument_id"]=ident
        for year in range(2020,2027):
            query=urllib.parse.urlencode({"start-date":f"{year}-01-01","end-date":min(f"{year}-12-31","2026-10-23"),"time-frame":"Daily","add-missing-rows":"false"})
            raw,receipt=get("investing_"+str(year),"https://api.investing.com/api/financialdata/historical/"+ident+"?"+query)
            receipt["year"]=year;result["probes"].append(receipt)
            print("TICK_HISTORY_PROBE",json.dumps(receipt),flush=True)
            if receipt["http_status"]!=200:
                result["stopped_reason"]="Public API refused/failed normal access; no authentication or bot-control bypass attempted."
                break
            try:
                payload=json.loads(raw);receipt["top_level_keys"]=list(payload) if isinstance(payload,dict) else None
                values=payload.get("data",[]) if isinstance(payload,dict) else []
                receipt["returned_rows"]=len(values) if isinstance(values,list) else None
                receipt["first_row"]=values[0] if isinstance(values,list) and values else None
                print("TICK_HISTORY_SCHEMA",json.dumps(receipt),flush=True)
            except Exception as exc:receipt["parse_error"]=str(exc)
    else:result["stopped_reason"]="No unique instrument id on the same JSON object as the exact NYSE TICK name; navigation ids are not substituted."
    with tarfile.open(archive) as tar:
        for name in ("tick-source/stooq_5e7469636b.raw.gz","tick-source/stooq_7469636b2e6e797365.raw.gz"):
            try:
                data=gzip.decompress(tar.extractfile(name).read()).decode("utf-8",errors="replace")
                result.setdefault("stooq_preserved_response",[]).append({"member":name,"finding":"Provider requires browser verification; not a numeric history. No challenge was executed."})
            except KeyError:pass
    (ROOT/"NYSE_TICK_SOURCE_FOLLOWUP_V4.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
