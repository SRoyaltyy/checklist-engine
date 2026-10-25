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


def context(tickers):
    funcs=fw.discover()
    breadth_path=fw.D('/workspace/updown/breadth_2020_24.parquet')
    breadth=pd.read_parquet(breadth_path)
    if 'date' not in breadth:breadth=breadth.reset_index()
    breadth['date']=pd.to_datetime(breadth.date).astype('datetime64[ns]')
    breadth=fw.extend_breadth(breadth)
    box=fw.load_box_ext(tickers)
    ext={}
    for block,groups in box.items():
        for ticker,frame in groups.items():ext.setdefault(ticker,{})[block]=frame
    return dict(funcs=funcs,etf=fw.etf_wide(),breadth=breadth,
        earnings=by_ticker(fw.load_earnings(tickers),'symbol'),ext=ext,
        peers=fw.build_peers(fw.load_bars(None)),mkt=fw.load_mkt(),
        an=by_ticker(fw.load_analyst(tickers)),xb=by_ticker(fw.load_xbrl(tickers)),
        gd=by_ticker(fw.load_gdelt(tickers)),f13=by_ticker(fw.load_f13(tickers)),fred=fw.load_fred())


def ticker_snapshot(ticker,bars,ctx):
    daily=fw.ticker_frame(ticker,bars,ctx['funcs'],ctx['etf'],ctx['breadth'],ctx['earnings'].get(ticker),
        ext=ctx['ext'].get(ticker),peers=ctx['peers'],mkt=ctx['mkt'],
        an=ctx['an'].get(ticker),xb=ctx['xb'].get(ticker),gd=ctx['gd'].get(ticker),
        f13=ctx['f13'].get(ticker),fred=ctx['fred'])
    own=set()
    for name in ctx['funcs']:
        outputs=list(fw.abstract.Function(name).output_names)
        own.update([name] if len(outputs)==1 else [name+'_'+x for x in outputs])
    external=daily[[c for c in daily if c not in own and (not c.startswith('tv_') or c=='tv_moon_age')]].copy()
    external['date']=pd.to_datetime(external.date).astype('datetime64[ns]')
    out=world_timeframes(bars,ctx['funcs'],external)
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
    bars=fw.load_bars(set(mine))
    ctx=context(set(mine))
    metadata=dict(shard=args.shard,timeframes=list(TIMEFRAMES),status='PROVISIONAL',
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
