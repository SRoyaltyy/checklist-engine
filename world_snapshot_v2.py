"""Version-2 world build: genuine candle timeframes and per-ticker checkpoints.

No scoring. A build is PROVISIONAL until the measured coverage/leak gates pass.
The legacy frozen price input is preserved. Its actual date range is reported;
a 2026 label never turns a 2024-ending file into 2026 data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import facets_world as fw
from world_timeframes import world_timeframes,TIMEFRAMES


def by_ticker(frame,key='ticker'):
    if frame is None or frame.empty:return {}
    return {str(t):g.reset_index(drop=True) for t,g in frame.groupby(key)}


def load_reconciled_bars(tickers, directory='', report_path=None):
    from price_reconcile import reconcile_one
    frozen=fw.load_bars(tickers)
    if not directory:return frozen,{}
    reports={};frames=[]
    try:
        for ticker,old in frozen.groupby('ticker',sort=True):
            file=Path(directory)/(str(ticker).encode().hex()+'.parquet')
            new=pd.read_parquet(file)
            new=new[pd.to_datetime(new.date)<=pd.Timestamp(fw.END)]
            event_file=Path(directory)/(str(ticker).encode().hex()+'.events.parquet')
            events=pd.read_parquet(event_file) if event_file.exists() else None
            frame,evidence=reconcile_one(ticker,old,new,events=events)
            frames.append(frame);reports[ticker]=evidence
    except Exception as exc:
        reports['_error']=str(exc)
        if report_path:Path(report_path).write_text(json.dumps(reports,indent=2))
        raise
    if report_path:Path(report_path).write_text(json.dumps(reports,indent=2))
    return pd.concat(frames,ignore_index=True),reports


def context(tickers,supplemental_prices=''):
    funcs=fw.discover()
    etf_frame=None
    if supplemental_prices:
        symbols='SPY QQQ IWM XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY'.split()
        etf_frame=pd.concat([pd.read_parquet(Path(supplemental_prices)/(t.encode().hex()+'.parquet')) for t in symbols],ignore_index=True)
    breadth_path=fw.D('/workspace/updown/breadth_2020_24.parquet')
    breadth=pd.read_parquet(breadth_path)
    if 'date' not in breadth:breadth=breadth.reset_index()
    breadth['date']=pd.to_datetime(breadth.date).astype('datetime64[ns]')
    breadth=fw.extend_breadth(breadth)
    box=fw.load_box_ext(tickers)
    ext={}
    for block,groups in box.items():
        for ticker,frame in groups.items():ext.setdefault(ticker,{})[block]=frame
    from world_fred import compile_timelines
    fred=fw.load_fred()
    return dict(funcs=funcs,etf=fw.etf_wide(etf_frame),breadth=breadth,
        earnings=by_ticker(fw.load_earnings(tickers),'symbol'),ext=ext,
        peers=fw.build_peers(fw.load_bars(None)),mkt=fw.load_mkt(),
        an=by_ticker(fw.load_analyst(tickers)),xb=by_ticker(fw.load_xbrl(tickers)),
        gd=by_ticker(fw.load_gdelt(tickers)),f13=by_ticker(fw.load_f13(tickers)),fred=fred,fred_timelines=compile_timelines(fred))


def ticker_snapshot(ticker,bars,ctx):
    bars=bars.copy()
    bars['date']=pd.to_datetime(bars.date).astype('datetime64[ns]')
    ctx=ctx.copy()
    for key in ('etf','breadth','mkt'):
        if ctx[key] is not None:
            frame=ctx[key].copy()
            for column in ('date','vintage_date','obs_date'):
                if column in frame:frame[column]=pd.to_datetime(frame[column]).astype('datetime64[ns]')
            ctx[key]=frame
    daily=fw.ticker_frame(ticker,bars,ctx['funcs'],ctx['etf'],ctx['breadth'],ctx['earnings'].get(ticker),
        ext=ctx['ext'].get(ticker),peers=ctx['peers'],mkt=ctx['mkt'],
        an=ctx['an'].get(ticker),xb=ctx['xb'].get(ticker),gd=ctx['gd'].get(ticker),
        f13=ctx['f13'].get(ticker),fred=ctx['fred'],fred_timelines=ctx.get('fred_timelines'))
    own=set()
    for name in ctx['funcs']:
        outputs=list(fw.abstract.Function(name).output_names)
        own.update([name] if len(outputs)==1 else [name+'_'+x for x in outputs])
    external=daily[[c for c in daily if c not in own and (not c.startswith('tv_') or c=='tv_moon_age')]].copy()
    external['date']=pd.to_datetime(external.date).astype('datetime64[ns]')
    out=world_timeframes(bars,ctx['funcs'],external,query_start='2020-01-01')
    out.insert(0,'ticker',ticker)
    return out


def digest_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for piece in iter(lambda:stream.read(1024*1024),b''):h.update(piece)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    ap.add_argument('--shard',type=int,default=0)
    ap.add_argument('--shards',type=int,default=8)
    ap.add_argument('--tickers',default='')
    ap.add_argument('--supplemental-prices',default='')
    ap.add_argument('--part-tickers',type=int,default=25)
    args=ap.parse_args()
    output=Path(args.out);output.mkdir(parents=True,exist_ok=True)
    cp=output/'checkpoints';cp.mkdir(exist_ok=True)
    universe=pd.read_parquet(fw.D('/workspace/pricehist/universe_2020_survivors.parquet'),columns=['ticker'])
    tickers=sorted(universe.ticker.unique())
    if args.tickers:
        wanted=set(args.tickers.split(','));tickers=[t for t in tickers if t in wanted]
    mine=tickers[args.shard::args.shards]
    if not mine:raise SystemExit('No assigned tickers: refusing a successful empty shard')
    bars,reconciliation=load_reconciled_bars(set(mine),args.supplemental_prices,output/'PRICE_RECONCILIATION.json')
    ctx=context(set(mine),args.supplemental_prices)
    metadata=dict(price_reconciliation=reconciliation,nominal_historical_price_verified=False,shard=args.shard,timeframes=list(TIMEFRAMES),status='PROVISIONAL',
        source_commit=os.environ.get('GITHUB_SHA','local-regression-only'),
        talib_version=fw.talib.__version__,talib_functions=list(ctx['funcs']),
        talib_exclusions=fw.DISCOVERY_EXCLUSIONS,patterns=sum(x[0]=='pattern' for x in ctx['funcs'].values()),
        input_start=str(bars.date.min())[:10],input_end=str(bars.date.max())[:10],
        tickers_requested=mine,tickers_built=[],errors={},files=[])
    files=[]
    for ticker,group in bars.groupby('ticker',sort=True):
        checkpoint=cp/(str(ticker).encode().hex()+'.parquet')
        try:
            if not checkpoint.exists():
                frame=ticker_snapshot(ticker,group.sort_values('date').reset_index(drop=True),ctx)
                frame=frame[frame.date>=pd.Timestamp('2020-01-01')]
                if frame.empty:raise ValueError('no in-window world rows')
                frame.to_parquet(str(checkpoint)+'.tmp',index=False)
                os.replace(str(checkpoint)+'.tmp',checkpoint)
            files.append(checkpoint);metadata['tickers_built'].append(ticker)
            print('CHECKPOINT',ticker,len(files),'/',len(mine),flush=True)
        except Exception as exc:
            metadata['errors'][ticker]=repr(exc)
            import traceback
            traceback.print_exc()
            print('TICKER_ERROR',ticker,repr(exc),flush=True)
    # Align schema without holding all ticker frames in memory. Missing sources
    # stay null; coverage counts them in the full denominator.
    columns=set()
    for file in files:columns.update(pq.ParquetFile(file).schema_arrow.names)
    names=['ticker','date']+sorted(columns-{'ticker','date'})
    schema=pa.schema([(c,pa.string() if c=='ticker' else pa.timestamp('ns') if c=='date' else pa.float32()) for c in names])
    for part,offset in enumerate(range(0,len(files),args.part_tickers)):
        target=output/f'world_shard_{args.shard:03d}_part_{part:03d}.parquet'
        count=0
        with pq.ParquetWriter(target,schema,compression='zstd') as writer:
            for file in files[offset:offset+args.part_tickers]:
                frame=pd.read_parquet(file).reindex(columns=names)
                table=pa.Table.from_pandas(frame,schema=schema,preserve_index=False)
                writer.write_table(table);count+=len(frame)
        metadata['files'].append(dict(name=target.name,rows=count,sha256=digest_file(target),bytes=target.stat().st_size))
    metadata['columns']=names
    metadata['missing_tickers']=sorted(set(mine)-set(metadata['tickers_built']))
    path=output/f'world_shard_{args.shard:03d}.json'
    path.write_text(json.dumps(metadata,indent=2))
    print(json.dumps(dict(rows=sum(f['rows'] for f in metadata['files']),columns=len(names),
        patterns=metadata['patterns'],files=len(metadata['files']),errors=len(metadata['errors']),
        input_end=metadata['input_end'])),flush=True)
    if metadata['errors'] or metadata['missing_tickers']:raise SystemExit(1)

if __name__=='__main__':main()
