"""Fetch public alternative price evidence; no replacement or source approval is inferred."""
import argparse,hashlib,io,json,os,subprocess,tarfile,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import pandas as pd
TICKERS=["ACA","ACVA","ATKR","AXG","AZTR","BDRX","BLFS","BTF","BZH","CCO","COCH","CYCN","GCTK","HCTI","IAE","IHD","IPW","LBRDA","LPSN","MUSQ","NIVF","ONEG","PERF","PPCB","PSKY","QNCX","QRVO","RETO","SBFM","SLP","SXTC","TWG","UUU","VTAK","WAR","WBD"]
COLUMNS=['open','high','low','close','volume']
def request(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/csv,*/*','Origin':'https://www.nasdaq.com'})
    with urllib.request.urlopen(req,timeout=25) as response:return response.read()
def normalize(ticker,frame):
    frame.columns=[str(c).strip().lower() for c in frame.columns]
    frame=frame.rename(columns={'close/last':'close'})
    if not {'date',*COLUMNS}<=set(frame):raise ValueError('Missing daily OHLCV columns')
    frame['date']=pd.to_datetime(frame.date,format='mixed',errors='raise')
    for c in COLUMNS:
        frame[c]=pd.to_numeric(frame[c].astype(str).str.replace('$','',regex=False).str.replace(',','',regex=False),errors='coerce')
    frame=frame[(frame.date>='1990-01-01')&(frame.date<='2026-10-23')].copy()
    if frame.empty:raise ValueError('No in-window daily bars')
    if frame.date.duplicated().any():raise ValueError('Duplicate source sessions')
    frame.insert(0,'ticker',ticker)
    return frame[['ticker','date',*COLUMNS]].sort_values('date')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--provider',choices=['stooq','nasdaq','yahoo-events'],required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
    root=Path('price-alternatives-'+a.provider);root.mkdir(exist_ok=True);records={}
    targets=['RETO','NIVF'] if a.provider=='yahoo-events' else TICKERS
    for ticker in targets:
        urls=[];details={}
        try:
            if a.provider=='stooq':
                url='https://stooq.com/q/d/l/?'+urllib.parse.urlencode(dict(s=ticker.lower()+'.us',i='d',d1='19900101',d2='20261023'));urls.append(url)
                raw=request(url);(root/(ticker+'.csv')).write_bytes(raw);frame=normalize(ticker,pd.read_csv(io.BytesIO(raw)))
            elif a.provider=='nasdaq':
                asset='etf' if ticker in ('BTF','MUSQ','WAR') else 'stocks'
                url='https://api.nasdaq.com/api/quote/'+urllib.parse.quote(ticker,safe='')+'/historical?'+urllib.parse.urlencode(dict(assetclass=asset,fromdate='2018-01-01',todate='2026-10-23',limit=5000));urls.append(url)
                raw=request(url);(root/(ticker+'.json')).write_bytes(raw);payload=json.loads(raw)
                data=payload.get('data') or {};returned=data.get('symbol')
                if returned and returned.upper()!=ticker:raise ValueError('Returned symbol mismatch')
                table=data.get('tradesTable') or {};rows=table.get('rows') or []
                if not rows:raise ValueError('No numeric Nasdaq table: '+json.dumps(payload.get('status'))[:300])
                if int(data.get('totalRecords',len(rows)))>len(rows):raise ValueError('Incomplete Nasdaq pagination; source not accepted')
                frame=normalize(ticker,pd.DataFrame(rows));details['returned_symbol']=returned
            else:
                url='https://query1.finance.yahoo.com/v8/finance/chart/'+ticker+'?'+urllib.parse.urlencode(dict(period1=631152000,period2=1792814400,interval='1d',events='div,splits'));urls.append(url)
                raw=request(url);(root/(ticker+'.json')).write_bytes(raw);payload=json.loads(raw);result=payload['chart']['result'][0]
                details=dict(returned_symbol=result.get('meta',{}).get('symbol'),events=result.get('events',{}).get('splits',{}))
                records[ticker]=dict(status='FETCHED_EVENTS',urls=urls,raw_sha256=hashlib.sha256(raw).hexdigest(),**details)
                print('ALTERNATIVE_SOURCE',a.provider,ticker,json.dumps(records[ticker]),flush=True);continue
            target=root/(ticker+'.parquet');frame.to_parquet(target,index=False)
            records[ticker]=dict(status='FETCHED_NUMERIC',urls=urls,rows=len(frame),first=str(frame.date.min())[:10],last=str(frame.date.max())[:10],missing_ohlcv_rows=int(frame[COLUMNS].isna().any(axis=1).sum()),raw_sha256=hashlib.sha256(raw).hexdigest(),parquet_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),used_as_replacement=False,**details)
        except Exception as exc:
            records[ticker]=dict(status='ERROR',urls=urls,error_type=type(exc).__name__,error=str(exc),http_status=getattr(exc,'code',None))
        print('ALTERNATIVE_SOURCE',a.provider,ticker,json.dumps(records[ticker]),flush=True);time.sleep(1)
    archive=Path(a.provider+'_price_alternatives.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(root.iterdir()):tar.add(p,arcname=p.name,recursive=False)
    report=dict(provider=a.provider,source_commit=os.environ['GITHUB_SHA'],records=records,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),scope='Provisional source evidence only. Strict overlap, identity, nominal-price and world gates remain.')
    target=Path(a.provider+'_price_alternatives.json');target.write_text(json.dumps(report,indent=2))
    subprocess.run(['gh','release','upload',a.tag,str(archive),str(target)],check=True)
    if not any(r['status'].startswith('FETCHED') for r in records.values()):raise SystemExit(1)
if __name__=='__main__':main()
