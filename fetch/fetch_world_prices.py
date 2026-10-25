"""Supplemental Yahoo price/event acquisition; never overwrites frozen inputs.
Adjusted OHLC supports ratios/indicators. Vendor quote fields are retained with
an explicit basis label; they are NOT asserted to be historical nominal prices.
A reconciliation/nominal-price gate is required before scoring or mcap filters.
"""
import argparse,hashlib,json,os,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
import numpy as np
import pandas as pd


def chart_rows(ticker,payload):
    result=payload.get('chart',{}).get('result')
    if not result:raise ValueError('no chart result: '+str(payload.get('chart',{}).get('error')))
    result=result[0]
    granularity=result.get('meta',{}).get('dataGranularity')
    if granularity is not None and granularity!='1d':raise ValueError('provider returned non-daily granularity '+str(granularity))
    timestamps=result.get('timestamp',[])
    quote=result['indicators']['quote'][0]
    adjusted=result['indicators'].get('adjclose',[{}])[0].get('adjclose',[])
    if len(adjusted)!=len(timestamps):raise ValueError('adjusted-close series missing')
    date=pd.to_datetime(timestamps,unit='s',utc=True).tz_convert('America/New_York').tz_localize(None).normalize()
    frame=pd.DataFrame({'ticker':ticker,'date':date})
    for column in ('open','high','low','close','volume'):
        values=quote.get(column,[])
        if len(values)!=len(frame):raise ValueError('quote array length mismatch '+column)
        frame['vendor_'+column]=pd.to_numeric(pd.Series(values),errors='coerce')
    frame['adjusted_close']=pd.to_numeric(pd.Series(adjusted),errors='coerce')
    factor=frame.adjusted_close/frame.vendor_close.replace(0,np.nan)
    for column in ('open','high','low','close'):frame[column]=frame['vendor_'+column]*factor
    frame['volume']=frame.vendor_volume
    events=[]
    for kind,key in [('dividend','dividends'),('split','splits')]:
        for event in result.get('events',{}).get(key,{}).values():
            stamp=pd.Timestamp(event['date'],unit='s',tz='UTC').tz_convert('America/New_York').date()
            value=event.get('amount') if kind=='dividend' else event.get('numerator',0)/event.get('denominator',1)
            events.append(dict(ticker=ticker,date=str(stamp),kind=kind,value=value))
    frame=frame.dropna(subset=['close']).drop_duplicates(['ticker','date']).sort_values('date')
    if len(frame)>20:
        gaps=frame.date.diff().dropna().dt.total_seconds()/86400
        if gaps.median()>3:raise ValueError('price series is too sparse to be daily')
    return frame,pd.DataFrame(events,columns=['ticker','date','kind','value'])


def fetch(ticker):
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(ticker,safe='')+'?'+urllib.parse.urlencode({'period1':631152000,'period2':int(time.time()),'interval':'1d','events':'div,splits'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90) as response:
                return json.load(response),url
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==3:raise
        except (OSError,TimeoutError):
            if attempt==3:raise
        time.sleep(min(2**attempt*3,30))
    raise RuntimeError('price fetch retries exhausted')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--tickers',default='')
    ap.add_argument('--universe');ap.add_argument('--shard',type=int,default=0);ap.add_argument('--shards',type=int,default=8)
    ap.add_argument('--count',type=int,default=0);args=ap.parse_args()
    if args.tickers:tickers=sorted(set(args.tickers.split(',')))
    elif args.universe:
        tickers=sorted(pd.read_parquet(args.universe,columns=['ticker']).ticker.unique(),key=lambda t:hashlib.sha256(('world-prices-v2|'+str(t)).encode()).hexdigest())
    else:raise SystemExit('provide --tickers or --universe')
    tickers=tickers[args.shard::args.shards]
    if args.count:tickers=tickers[:args.count]
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    report=dict(source='Yahoo chart v8',frozen_inputs_modified=False,nominal_price_basis_verified=False,
        quote_basis='vendor historical quote; not asserted nominal PIT',indicator_basis='vendor adjusted-close/quote-close factor',
        requested=tickers,completed={},errors={})
    for ticker in tickers:
        target=out/(ticker.encode().hex()+'.parquet')
        try:
            if target.exists():frame=pd.read_parquet(target)
            else:
                payload,url=fetch(ticker);frame,events=chart_rows(ticker,payload)
                frame.to_parquet(str(target)+'.tmp',index=False);os.replace(str(target)+'.tmp',target)
                events.to_parquet(out/(ticker.encode().hex()+'.events.parquet'),index=False)
            report['completed'][ticker]=dict(rows=len(frame),first=str(frame.date.min())[:10],last=str(frame.date.max())[:10],
                rows_2025_2026=int(frame.date.dt.year.isin([2025,2026]).sum()))
            print('PRICE_CHECKPOINT',ticker,json.dumps(report['completed'][ticker]),flush=True)
        except Exception as exc:
            report['errors'][ticker]=repr(exc);print('PRICE_SOURCE_ERROR',ticker,repr(exc),flush=True)
        (out/'PRICE_FETCH_REPORT.json').write_text(json.dumps(report,indent=2))
        time.sleep(1)
    if report['errors'] or len(report['completed'])!=len(tickers):raise SystemExit(1)

if __name__=='__main__':main()
