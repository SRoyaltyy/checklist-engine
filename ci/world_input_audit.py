"""Audit the two frozen inputs and current durable source checkpoints without scoring."""
import argparse,collections,hashlib,io,json,os,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq


def input_info(file):
    parquet=pq.ParquetFile(file)
    frame=pd.read_parquet(file,columns=['ticker','date'])
    dates=pd.to_datetime(frame.date)
    names=set(frame.ticker.dropna().astype(str))
    return dict(file=str(file),sha256=hashlib.sha256(Path(file).read_bytes()).hexdigest(),
        rows=parquet.metadata.num_rows,columns={field.name:str(field.type) for field in parquet.schema_arrow},
        ticker_count=len(names),first_date=str(dates.min())[:10],last_date=str(dates.max())[:10]),names


def get(url,binary=False):
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'checklist-engine-source-audit'}
    if binary:headers['Accept']='application/octet-stream'
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as response:
        data=response.read()
    return data if binary else json.loads(data)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--universe',required=True);ap.add_argument('--bars',required=True)
    ap.add_argument('--source-tag',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    universe,universe_names=input_info(args.universe);bars,bar_names=input_info(args.bars)
    repo=os.environ['GITHUB_REPOSITORY'];api=f'https://api.github.com/repos/{repo}'
    release=get(api+'/releases/tags/'+args.source_tag);assets=[];page=1
    while True:
        batch=get(api+f"/releases/{release['id']}/assets?per_page=100&page={page}")
        assets.extend(batch)
        if len(batch)<100:break
        page+=1
    latest={}
    for asset in assets:
        match=re.fullmatch(r'prices_shard_(\d+)_attempt_(\d+)_part_(\d+)\.json',asset['name'])
        if match:
            shard,attempt,part=map(int,match.groups())
            if shard not in latest or (attempt,part)>latest[shard][0]:latest[shard]=((attempt,part),asset)
    completed={};errors={}
    for _,asset in latest.values():
        record=json.loads(get(asset['url'],binary=True));completed.update(record['report']['completed']);errors.update(record['report']['errors'])
    samples=[dict(ticker=t,in_frozen_bars=t in bar_names,**r) for t,r in sorted(errors.items())[:30]]
    listings={};listing_sources=[]
    for name in ('nasdaqlisted','otherlisted'):
        url=f'https://www.nasdaqtrader.com/dynamic/SymDir/{name}.txt'
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'checklist-engine research cyrus-checklist@users.noreply.github.com'})
            with urllib.request.urlopen(request,timeout=60) as response:raw=response.read().decode('utf8')
            table=pd.read_csv(io.StringIO(raw),sep='|',dtype=str,keep_default_na=False)
            for _,row in table.iterrows():
                for field in ('Symbol','ACT Symbol','CQS Symbol','NASDAQ Symbol'):
                    symbol=row.get(field)
                    if isinstance(symbol,str) and symbol and not symbol.startswith('File Creation'):
                        record=dict(etf=row.get('ETF'),test_issue=row.get('Test Issue'),name=row.get('Security Name'),source=url)
                        for alias in (symbol,symbol.replace('/','.'),symbol.replace('/','-'),symbol.replace('.','-')):listings[alias]=record
            (out/(name+'.txt')).write_text(raw)
            listing_sources.append(dict(url=url,status='FETCHED',rows=len(table),sha256=hashlib.sha256(raw.encode()).hexdigest(),fetched_at=datetime.now(timezone.utc).isoformat()))
        except Exception as exc:listing_sources.append(dict(url=url,status='ERROR',error=str(exc)))
    stale=[dict(ticker=t,**r,listing=listings.get(t,{})) for t,r in sorted(completed.items()) if r['last']<'2026-10-23']
    classification=collections.Counter(listings.get(t,{}).get('etf','UNKNOWN') for t in universe_names)
    pd.DataFrame([dict(ticker=t,classification='ETF' if listings.get(t,{}).get('etf')=='Y' else 'NON_ETF' if listings.get(t,{}).get('etf')=='N' else 'UNKNOWN',**listings.get(t,{})) for t in sorted(universe_names)]).to_csv(out/'CURRENT_LISTING_CLASSIFICATION.csv',index=False)
    unknown_names=sorted(t for t in universe_names if not listings.get(t,{}).get('etf') in ('N','Y'))
    universe_source_counts={}
    if 'source' in universe['columns']:
        universe_source_counts={str(k):int(v) for k,v in pd.read_parquet(args.universe,columns=['source']).source.value_counts().items()}
    report=dict(status='READ_ONLY_AUDIT',source_tag=args.source_tag,asset_count=len(assets),
        universe=universe,bars=bars,universe_without_frozen_bars=len(universe_names-bar_names),
        missing_bar_sample=sorted(universe_names-bar_names)[:60],universe_names=sorted(universe_names),
        frozen_bar_names=sorted(bar_names),checkpoint_shards=len(latest),currently_fetched=len(completed),
        currently_failed=len(errors),currently_pending=len(universe_names-set(completed)-set(errors)),
        error_types=dict(collections.Counter(str(r.get('http_status',r.get('error_type'))) for r in errors.values())),
        error_samples=samples,stale_sources=stale,listing_sources=listing_sources,listing_etf_flags=dict(classification),
        unknown_listing_names=unknown_names,universe_source_counts=universe_source_counts,bars_without_universe=len(bar_names-universe_names),
        bars_without_universe_sample=sorted(bar_names-universe_names)[:60],world_coverage_approved=False)
    (out/'WORLD_INPUT_AUDIT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('universe_names','frozen_bar_names')}),flush=True)


if __name__=='__main__':main()
