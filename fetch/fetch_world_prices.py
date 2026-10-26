"""Supplemental Yahoo price/event acquisition; never overwrites frozen inputs.
Adjusted OHLC supports ratios/indicators. Vendor quote fields are retained with
an explicit basis label; they are NOT asserted to be historical nominal prices.
A reconciliation/nominal-price gate is required before scoring or mcap filters.
"""
import argparse,hashlib,json,os,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
import numpy as np
import pandas as pd


SOURCE_FORMAT=3


def provider_symbol(ticker):
    return str(ticker).replace('.','-')


def period_end(end_date):
    if not end_date:return int(time.time())
    return int((pd.Timestamp(end_date)+pd.Timedelta(days=1)).tz_localize('America/New_York').timestamp())


def publish_checkpoint(out,shard,part,tickers,report,tag):
    import tarfile,subprocess
    attempt=os.environ.get('GITHUB_RUN_ATTEMPT','1')
    prefix=f'prices_shard_{shard:03d}_attempt_{attempt}_part_{part:03d}'
    archive=out.parent/(prefix+'.tar');manifest_path=out.parent/(prefix+'.json')
    members=[]
    for ticker in tickers:
        for suffix in ('.parquet','.events.parquet'):
            file=out/(ticker.encode().hex()+suffix)
            if file.exists():
                members.append(dict(name=file.name,bytes=file.stat().st_size,
                    sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    checkpoint=dict(source_commit=os.environ.get('GITHUB_SHA','local'),source_format=SOURCE_FORMAT,
        shard=shard,part=part,attempt=int(attempt),requested_end_date=report['requested_end_date'],
        batch_tickers=tickers,members=members,report=report,status='PROVISIONAL_SOURCE_CHECKPOINT')
    manifest_path.write_text(json.dumps(checkpoint,indent=2))
    with tarfile.open(archive,'w') as tar:
        for member in members:tar.add(out/member['name'],arcname=member['name'])
    checkpoint['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(checkpoint,indent=2))
    subprocess.run(['gh','release','upload',tag,str(archive),str(manifest_path)],check=True)
    archive.unlink()
    print('SOURCE_CHECKPOINT_UPLOADED',prefix,len(tickers),flush=True)
    return checkpoint


def chart_rows(ticker,payload):
    result=payload.get('chart',{}).get('result')
    if not result:raise ValueError('no chart result: '+str(payload.get('chart',{}).get('error')))
    result=result[0]
    granularity=result.get('meta',{}).get('dataGranularity')
    if granularity is not None and granularity!='1d':raise ValueError('provider returned non-daily granularity '+str(granularity))
    symbol=result.get('meta',{}).get('symbol')
    if symbol is not None and str(symbol).upper()!=provider_symbol(ticker).upper():raise ValueError('provider symbol identity mismatch')
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
    frame=frame.dropna(subset=['close']).sort_values('date')
    if frame.empty:raise ValueError('no usable daily bars')
    if frame.duplicated(['ticker','date']).any():raise ValueError('duplicate source sessions')
    if len(frame)>20:
        gaps=frame.date.diff().dropna().dt.total_seconds()/86400
        if gaps.median()>3:raise ValueError('price series is too sparse to be daily')
    return frame,pd.DataFrame(events,columns=['ticker','date','kind','value'])


def fetch(ticker,end_timestamp=None):
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(provider_symbol(ticker),safe='')+'?'+urllib.parse.urlencode({'period1':631152000,'period2':end_timestamp if end_timestamp is not None else int(time.time()),'interval':'1d','events':'div,splits'})
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
    ap.add_argument('--count',type=int,default=0);ap.add_argument('--end-date',default='')
    ap.add_argument('--publish-tag',default='');ap.add_argument('--checkpoint-every',type=int,default=50)
    args=ap.parse_args()
    if args.checkpoint_every<1:ap.error('checkpoint-every must be positive')
    if args.tickers:tickers=sorted(set(args.tickers.split(',')))
    elif args.universe:
        tickers=sorted(pd.read_parquet(args.universe,columns=['ticker']).ticker.unique(),
                       key=lambda t:hashlib.sha256(('world-prices-v2|'+str(t)).encode()).hexdigest())
    else:raise SystemExit('provide --tickers or --universe')
    tickers=tickers[args.shard::args.shards]
    if args.count:tickers=tickers[:args.count]
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    previous=json.loads((out/'PRICE_FETCH_REPORT.json').read_text()) if (out/'PRICE_FETCH_REPORT.json').exists() else {}
    source_commit=os.environ.get('GITHUB_SHA','local')
    report=dict(source='Yahoo chart v8',source_format=SOURCE_FORMAT,source_commit=source_commit,
        requested_end_date=args.end_date or 'latest',shard=args.shard,shards=args.shards,
        frozen_inputs_modified=False,nominal_price_basis_verified=False,
        quote_basis='vendor historical quote; not asserted nominal PIT',
        indicator_basis='vendor adjusted-close/quote-close factor',requested=tickers,completed={},errors={})
    ending=period_end(args.end_date);batch=[];part=0
    for index,ticker in enumerate(tickers):
        target=out/(ticker.encode().hex()+'.parquet')
        try:
            if target.exists():
                old=previous.get('completed',{}).get(ticker,{})
                if (previous.get('source_format')!=SOURCE_FORMAT or previous.get('source_commit')!=source_commit
                    or previous.get('requested_end_date')!=report['requested_end_date']
                    or old.get('sha256')!=hashlib.sha256(target.read_bytes()).hexdigest()):
                    raise ValueError('existing checkpoint has different source/period/fingerprint; refusing reuse')
                frame=pd.read_parquet(target)
            else:
                payload,url=fetch(ticker,ending)
                results=payload.get('chart',{}).get('result')
                if not results:raise ValueError('no chart result: '+str(payload.get('chart',{}).get('error')))
                meta=results[0].get('meta',{})
                if str(meta.get('symbol','')).upper()!=provider_symbol(ticker).upper():
                    raise ValueError('provider symbol identity not verified')
                frame,events=chart_rows(ticker,payload)
                if args.end_date:
                    frame=frame[frame.date<=pd.Timestamp(args.end_date)].copy()
                    events=events[events.date<=args.end_date].copy()
                if frame.empty:raise ValueError('no usable daily bars in requested period')
                frame['provider_symbol']=provider_symbol(ticker)
                frame.to_parquet(str(target)+'.tmp',index=False);os.replace(str(target)+'.tmp',target)
                events.to_parquet(out/(ticker.encode().hex()+'.events.parquet'),index=False)
            missing=int(frame[['open','high','low','close','volume']].isna().any(axis=1).sum())
            report['completed'][ticker]=dict(rows=len(frame),first=str(frame.date.min())[:10],last=str(frame.date.max())[:10],
                rows_2025_2026=int(frame.date.dt.year.isin([2025,2026]).sum()),missing_ohlcv_rows=missing,
                provider_symbol=provider_symbol(ticker),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            print('PRICE_CHECKPOINT',ticker,json.dumps(report['completed'][ticker]),flush=True)
        except Exception as exc:
            record=dict(error_type=type(exc).__name__,message=str(exc),provider_symbol=provider_symbol(ticker))
            if isinstance(exc,urllib.error.HTTPError):
                record.update(http_status=exc.code,url=exc.url)
                try:record['response_excerpt']=exc.read(1024).decode('utf8',errors='replace')
                except Exception:pass
            report['errors'][ticker]=record
            print('PRICE_SOURCE_ERROR',ticker,json.dumps(record),flush=True)
        (out/'PRICE_FETCH_REPORT.json').write_text(json.dumps(report,indent=2))
        batch.append(ticker)
        if args.publish_tag and (len(batch)>=args.checkpoint_every or index==len(tickers)-1):
            publish_checkpoint(out,args.shard,part,batch,report,args.publish_tag)
            batch=[];part+=1
        time.sleep(1)
    if report['errors'] or len(report['completed'])!=len(tickers):raise SystemExit(1)

if __name__=='__main__':main()
