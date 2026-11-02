"""SEC structured data sets (no AI): Insider Transactions (Form 3/4/5) and Form 13F, 2020Q1..latest.
Usage: python scripts/nai/sec_datasets.py form345|form13f. One parquet per source zip; skips assets already uploaded (resumable).
Only structured / enumerated fields kept (no free-text titles/names, per Cyrus free-text rule)."""
import io, os, re, sys, zipfile
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import get, ensure_release, assets, upload

KIND = sys.argv[1]
PAGES = {"form345": "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets",
         "form13f": "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"}
TAG = f"nai-{KIND}-v1"
html = get(PAGES[KIND]).decode("utf-8", "replace")
links = sorted(set(re.findall(r'href="([^"]+\.zip)"', html)))
links = ["https://www.sec.gov" + l if l.startswith("/") else l for l in links]
def year(u):
    m = re.search(r"(20\d\d)", os.path.basename(u)); return int(m.group(1)) if m else 0
links = [u for u in links if year(u) >= 2020]
print(len(links), "zips"); [print(" ", u) for u in links]
ensure_release(TAG, f"No-AI SEC {KIND} data sets v1")
have = assets(TAG)
os.makedirs("_out", exist_ok=True)

def rd(z, stem, cols):
    n = next(x for x in z.namelist() if os.path.basename(x).upper().startswith(stem))
    df = pd.read_csv(io.BytesIO(z.read(n)), sep="\t", dtype=str, quoting=3, on_bad_lines="skip", low_memory=False)
    return df[[c for c in cols if c in df.columns]]

done = []
for u in links:
    name = os.path.basename(u).replace(".zip", ".parquet")
    if name in have:
        print("skip", name); continue
    try:
        zb = get(u, timeout=1200)
    except Exception as e:
        print("FAIL", u, e); continue
    z = zipfile.ZipFile(io.BytesIO(zb))
    if KIND == "form345":
        s = rd(z, "SUBMISSION", ["ACCESSION_NUMBER", "FILING_DATE", "PERIOD_OF_REPORT", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERTRADINGSYMBOL", "AFF10B5ONE"])
        o = rd(z, "REPORTINGOWNER", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP"])
        o = o.groupby("ACCESSION_NUMBER").agg(RPTOWNERCIK=("RPTOWNERCIK", "first"), RPTOWNER_RELATIONSHIP=("RPTOWNER_RELATIONSHIP", lambda x: ",".join(sorted(set(x.dropna()))))).reset_index()
        t = rd(z, "NONDERIV_TRANS", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "SHRS_OWND_FOLWNG_TRANS", "DIRECT_INDIRECT_OWNERSHIP", "EQUITY_SWAP_INVOLVED"])
        df = t.merge(s, on="ACCESSION_NUMBER", how="left").merge(o, on="ACCESSION_NUMBER", how="left")
        df["is_open_market_buy"] = df["TRANS_CODE"].eq("P"); df["is_open_market_sell"] = df["TRANS_CODE"].eq("S")
        df["is_acquired"] = df["TRANS_ACQUIRED_DISP_CD"].eq("A")
        for c in ["TRANS_SHARES", "TRANS_PRICEPERSHARE", "SHRS_OWND_FOLWNG_TRANS"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    else:
        s = rd(z, "SUBMISSION", ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"])
        it = rd(z, "INFOTABLE", ["ACCESSION_NUMBER", "CUSIP", "FIGI", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL", "INVESTMENTDISCRETION", "VOTING_AUTH_SOLE", "VOTING_AUTH_SHARED", "VOTING_AUTH_NONE"])
        df = it.merge(s, on="ACCESSION_NUMBER", how="left")
        for c in ["VALUE", "SSHPRNAMT", "VOTING_AUTH_SOLE", "VOTING_AUTH_SHARED", "VOTING_AUTH_NONE"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["is_put"] = df["PUTCALL"].str.upper().eq("PUT"); df["is_call"] = df["PUTCALL"].str.upper().eq("CALL")
    p = f"_out/{name}"; df.to_parquet(p, compression="zstd", index=False)
    upload(TAG, p); os.remove(p); done.append((name, len(df))); print("ok", name, len(df), flush=True)
print("uploaded", len(done), "skipped", len([u for u in links if os.path.basename(u).replace('.zip', '.parquet') in have]))
