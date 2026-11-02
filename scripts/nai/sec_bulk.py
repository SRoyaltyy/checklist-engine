"""SEC bulk (no AI): tickers maps + submissions.zip + companyfacts.zip -> retained_8439 cohort parquet.
Run on GitHub runner. Output -> release nai-sec-bulk-v1."""
import json, os, sys, zipfile
import pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(__file__))
from common import get, cohort, ensure_release, upload

TAG = "nai-sec-bulk-v1"
OUT = "_out"; os.makedirs(OUT, exist_ok=True); os.makedirs("_dl", exist_ok=True)
norm = lambda t: t.upper().replace(".", "-").replace("/", "-").strip()

tickers = cohort()
# 1) archived identities (SEC_RETAINED_IDENTITY_MAP_V1)
arch = {}
for r in json.load(open("docs/SEC_RETAINED_IDENTITY_MAP_V1.json"))["records"]:
    if r.get("status") == "UNIQUE_CIK" and r.get("candidates"):
        arch[r["ticker"]] = int(r["candidates"][0]["cik"])
# 2) live maps
ct = json.loads(get("https://www.sec.gov/files/company_tickers.json"))
cte = json.loads(get("https://www.sec.gov/files/company_tickers_exchange.json"))
open(f"{OUT}/company_tickers.json", "w").write(json.dumps(ct))
open(f"{OUT}/company_tickers_exchange.json", "w").write(json.dumps(cte))
live = {}
for v in ct.values():
    live.setdefault(norm(v["ticker"]), set()).add(int(v["cik_str"]))
fi = cte["fields"]
for row in cte["data"]:
    d = dict(zip(fi, row)); live.setdefault(norm(d["ticker"]), set()).add(int(d["cik"]))

rows = []
for t in tickers:
    a = arch.get(t); l = live.get(norm(t), set())
    if a is not None:
        cik, method = a, "archived_identity_map_v1" + ("+live_agree" if a in l else ("+live_differs" if l else ""))
    elif len(l) == 1:
        cik, method = next(iter(l)), "live_company_tickers_current"
    elif len(l) > 1:
        cik, method = None, "ambiguous_live"
    else:
        cik, method = None, "no_cik"
    rows.append({"ticker": t, "cik": cik, "method": method})
ciks = {r["cik"] for r in rows if r["cik"]}
pq.write_table(pa.Table.from_pylist(rows), f"{OUT}/sec_identity_map_v2.parquet")
n_cik = sum(1 for r in rows if r["cik"])
cov = {"retained": len(tickers), "with_cik": n_cik, "pct": round(100 * n_cik / len(tickers), 2),
       "archived": sum(1 for r in rows if r["method"].startswith("archived")),
       "new_from_live": sum(1 for r in rows if r["method"] == "live_company_tickers_current"),
       "ambiguous": sum(1 for r in rows if r["method"] == "ambiguous_live"), "unique_ciks": len(ciks),
       "note": "live maps are CURRENT tickers only; delisted/renamed names stay no_cik (no dated history claimed)"}
print(json.dumps(cov))
ensure_release(TAG, "No-AI SEC bulk v1")
json.dump(cov, open(f"{OUT}/SEC_BULK_COVERAGE.json", "w"), indent=1)
upload(TAG, f"{OUT}/sec_identity_map_v2.parquet", f"{OUT}/SEC_BULK_COVERAGE.json", f"{OUT}/company_tickers.json", f"{OUT}/company_tickers_exchange.json")
if os.environ.get("IDENTITY_ONLY"):
    sys.exit(0)

def want(name):
    b = os.path.basename(name)
    if not b.startswith("CIK"):
        return None
    try:
        c = int(b[3:13])
    except ValueError:
        return None
    return c if c in ciks else None

# 3) submissions.zip -> entities + filings
sub = get("https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip", "_dl/submissions.zip", timeout=1800)
ent, fw = [], None
FCOLS = ["accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "form", "primaryDocument", "isXBRL"]
with zipfile.ZipFile(sub) as z:
    for n in z.namelist():
        c = want(n)
        if c is None:
            continue
        j = json.loads(z.read(n))
        rec = j.get("filings", {}).get("recent", j)
        if "filings" in j:
            ent.append({"cik": c, "name": j.get("name"), "tickers": ",".join(j.get("tickers") or []), "exchanges": ",".join(x or "" for x in (j.get("exchanges") or [])),
                        "sic": j.get("sic"), "sicDescription": j.get("sicDescription"), "stateOfIncorporation": j.get("stateOfIncorporation"),
                        "formerNames": json.dumps(j.get("formerNames") or [])})
        m = len(rec.get("accessionNumber", []))
        if not m:
            continue
        t = pa.table({"cik": [c] * m, **{k: [str(x) if x is not None else None for x in rec.get(k, [None] * m)] for k in FCOLS}})
        fw = fw or pq.ParquetWriter(f"{OUT}/sec_submissions_filings_retained.parquet", t.schema, compression="zstd")
        fw.write_table(t)
fw and fw.close()
pq.write_table(pa.Table.from_pylist(ent), f"{OUT}/sec_submissions_entities_retained.parquet")
os.remove(sub)
upload(TAG, f"{OUT}/sec_submissions_filings_retained.parquet", f"{OUT}/sec_submissions_entities_retained.parquet")

# 4) companyfacts.zip -> long facts
cf = get("https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip", "_dl/companyfacts.zip", timeout=1800)
schema = pa.schema([("cik", pa.int64()), ("taxonomy", pa.string()), ("concept", pa.string()), ("unit", pa.string()), ("start", pa.string()), ("end", pa.string()),
                    ("val", pa.float64()), ("accn", pa.string()), ("fy", pa.int64()), ("fp", pa.string()), ("form", pa.string()), ("filed", pa.string()), ("frame", pa.string())])
w = pq.ParquetWriter(f"{OUT}/sec_companyfacts_retained.parquet", schema, compression="zstd")
nf, nfacts = 0, 0
with zipfile.ZipFile(cf) as z:
    for n in z.namelist():
        c = want(n)
        if c is None:
            continue
        j = json.loads(z.read(n)); buf = []
        for tax, concepts in (j.get("facts") or {}).items():
            for con, body in concepts.items():
                for unit, facts in body.get("units", {}).items():
                    for f in facts:
                        try: v = float(f.get("val"))
                        except (TypeError, ValueError): continue
                        buf.append((c, tax, con, unit, f.get("start"), f.get("end"), v, f.get("accn"), f.get("fy"), f.get("fp"), f.get("form"), f.get("filed"), f.get("frame")))
        if buf:
            cols = list(zip(*buf)); w.write_table(pa.table([pa.array(cols[i], schema[i].type) for i in range(13)], schema=schema))
            nf += 1; nfacts += len(buf)
w.close(); os.remove(cf)
cov.update({"companyfacts_ciks": nf, "companyfacts_rows": nfacts, "submissions_entities": len(ent)})
json.dump(cov, open(f"{OUT}/SEC_BULK_COVERAGE.json", "w"), indent=1)
upload(TAG, f"{OUT}/sec_companyfacts_retained.parquet", f"{OUT}/SEC_BULK_COVERAGE.json")
print(json.dumps(cov))
