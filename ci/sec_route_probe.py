"""Probe official SEC structured endpoints through the mandatory relay; retain exact evidence."""
import hashlib,io,json,os,zipfile
from pathlib import Path
from fetch.sec_client import get_bytes

URLS=[
'https://www.sec.gov/files/company_tickers.json',
'https://www.sec.gov/files/company_tickers_exchange.json',
'https://www.sec.gov/files/company_tickers.json?source=checklist-engine',
'https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q3_form345.zip',
'https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2020q1_form345.zip',
'https://www.sec.gov/Archives/edgar/full-index/2026/QTR4/master.idx'
]
def main():
    root=Path('sec-route-probe');root.mkdir(exist_ok=True);records=[]
    for index,url in enumerate(URLS):
        try:
            raw=get_bytes(url)
            suffix='.zip' if url.endswith('.zip') else '.json' if '.json' in url else '.txt'
            path=root/(str(index)+suffix);path.write_bytes(raw)
            record=dict(url=url,status='FETCHED',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            if suffix=='.zip':
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    record['members']=z.namelist()
                    record['headers']={name:z.open(name).readline().decode('utf8',errors='replace').strip() for name in z.namelist() if name.lower().endswith('.tsv')}
            records.append(record)
        except Exception as exc:records.append(dict(url=url,status='ERROR',evidence=getattr(exc,'evidence',dict(error_type=type(exc).__name__,message=str(exc)))))
        print('SEC_STRUCTURED_ENDPOINT_PROBE',json.dumps(records[-1]),flush=True)
    (root/'SEC_STRUCTURED_ENDPOINT_PROBE.json').write_text(json.dumps(dict(source_commit=os.environ['GITHUB_SHA'],records=records),indent=2))
if __name__=='__main__':main()
