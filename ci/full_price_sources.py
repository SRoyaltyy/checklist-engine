"""Prepare the frozen-universe acquisition and summarize durable shard checkpoints."""
import argparse,csv,hashlib,json,os
from pathlib import Path
import pandas as pd


def prepare(universe,out,end_date,shards):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    tickers=sorted(set(pd.read_parquet(universe,columns=['ticker']).ticker.dropna().astype(str)))
    if not tickers:raise ValueError('empty universe')
    pd.DataFrame({'ticker':tickers}).to_parquet(out/'price_universe.parquet',index=False)
    manifest=dict(status='SOURCE_ACQUISITION_ONLY',source_commit=os.environ.get('GITHUB_SHA','local'),
        universe_label='Frozen 2020-2024 survivors universe; no automatic exclusions',
        universe_asset='data-2020-24-v1/universe_2020_survivors_le2024.parquet',
        universe_sha256=hashlib.sha256(Path(universe).read_bytes()).hexdigest(),
        requested_end_date=end_date,shards=shards,ticker_count=len(tickers),tickers=tickers,
        partition='sort by sha256(world-prices-v2|ticker), then ordinal modulo shard count',
        nominal_historical_price_verified=False)
    (out/'WORLD_UNIVERSE.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k!='tickers'}),flush=True)


def summarize(universe,checkpoints,out):
    universe=json.loads(Path(universe).read_text());out=Path(out);out.mkdir(parents=True,exist_ok=True)
    latest={}
    for file in Path(checkpoints).glob('prices_shard_*_attempt_*_part_*.json'):
        record=json.loads(file.read_text())
        if record['source_commit']!=universe['source_commit']:raise ValueError('mixed checkpoint code commits')
        if record['requested_end_date']!=universe['requested_end_date']:raise ValueError('mixed checkpoint end dates')
        shard=record['shard'];key=(record['attempt'],record['part'])
        if shard not in latest or key>latest[shard][0]:latest[shard]=(key,record)
    completed={};errors={};owners={}
    for shard,(_,record) in latest.items():
        for ticker in record['report']['requested']:
            if ticker in owners:raise ValueError('ticker assigned to multiple shards')
            owners[ticker]=shard
        completed.update(record['report']['completed']);errors.update(record['report']['errors'])
    rows=[]
    for ticker in universe['tickers']:
        value=completed.get(ticker);error=errors.get(ticker);state='PENDING'
        if value:
            state='FETCHED'
            if value.get('missing_ohlcv_rows',0):state='INCOMPLETE_OHLCV'
            elif value['last']<universe['requested_end_date']:state='STALE_LAST_SESSION'
        elif error:state='ERROR'
        rows.append(dict(ticker=ticker,status=state,shard=owners.get(ticker,''),rows=value['rows'] if value else 0,
            first_date=value['first'] if value else '',last_date=value['last'] if value else '',
            rows_2025_2026=value['rows_2025_2026'] if value else 0,
            missing_ohlcv_rows=value.get('missing_ohlcv_rows',0) if value else '',
            provider_symbol=value.get('provider_symbol','') if value else '',
            error=json.dumps(error,sort_keys=True) if error else '',nominal_price_verified=False))
    counts={status:sum(r['status']==status for r in rows) for status in sorted(set(r['status'] for r in rows))}
    missing_shards=sorted(set(range(universe['shards']))-set(latest))
    summary=dict(status='PASS' if counts.get('FETCHED')==len(rows) and not missing_shards else 'FAIL',
        scope=universe['universe_label'],requested=len(rows),status_counts=counts,missing_shards=missing_shards,
        source_commit=universe['source_commit'],requested_end_date=universe['requested_end_date'],
        nominal_price_verified=False,world_coverage_approved=False)
    with open(out/'PRICE_SOURCE_COVERAGE.csv','w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'PRICE_SOURCE_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    if summary['status']!='PASS':raise SystemExit(1)


def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='operation',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--universe',required=True);prep.add_argument('--out',required=True)
    prep.add_argument('--end-date',required=True);prep.add_argument('--shards',type=int,default=16)
    summary=sub.add_parser('summarize');summary.add_argument('--universe',required=True)
    summary.add_argument('--checkpoints',required=True);summary.add_argument('--out',required=True)
    args=ap.parse_args()
    if args.operation=='prepare':prepare(args.universe,args.out,args.end_date,args.shards)
    else:summarize(args.universe,args.checkpoints,args.out)


if __name__=='__main__':main()
