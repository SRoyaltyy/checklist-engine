"""Measure full numeric retention while the approved universe build continues."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

REPO=Path(__file__).resolve().parents[1]
REQUEST=Path('ci/NUMERIC_RETENTION_REQUEST.json')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def worker(root,recipe):
    sys.path[:0]=[str(recipe),str(REPO)]
    import resource
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import facets_world as fw
    from world_timeframes import TIMEFRAMES,completed_candles,candle_features
    from world_numeric_codec import encode_numeric,decode_numeric
    config=json.loads((root/'INPUTS.json').read_text());ticker=config['ticker']
    bars=pd.read_parquet(root/'bars.parquet')
    if sha((root/'bars.parquet').read_bytes())!=config['source_sha256']:raise ValueError('source bars changed')
    calendar=pd.DatetimeIndex(pd.read_parquet(root/'market_sessions.parquet').date)
    funcs=fw.discover();registry={};rows=[];started=time.perf_counter();raw_bytes=0
    archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w') as tar:
        for tf in TIMEFRAMES:
            candles=completed_candles(bars,tf,session_calendar=calendar)
            frame=candle_features(candles,funcs,timeframe=tf)
            dates=frame.available_from.to_numpy(dtype='datetime64[ns]').view('<i8').tobytes()
            values=frame.drop(columns='available_from')
            matrix=values.to_numpy(dtype=np.float64)
            provenance=dict(input_manifest_sha256=config['inputs_sha256'],recipe_fingerprint=config['recipe_fingerprint'],
                            row_keys_sha256=sha(ticker.encode()+dates))
            columns=list(values);payload,metadata=encode_numeric(matrix,columns,provenance)
            restored=decode_numeric(payload,metadata,columns,provenance)
            if restored.tobytes()!=np.ascontiguousarray(matrix,dtype='<f8').tobytes():raise ValueError('numeric bitwise roundtrip differs')
            registry[tf]=dict(columns=columns,input_dtypes=[str(values[c].dtype) for c in values],
                              recipe_fingerprint=config['recipe_fingerprint'])
            metadata.update(timeframe=tf,ticker=ticker,dates_sha256=sha(dates),
                            date_encoding='little-endian int64 nanoseconds; zstd19',stored_rows='ALL_NATIVE_ROWS_INCLUDING_PRE2020_WARMUP')
            compressed_dates=bytes(pa.Codec('zstd',compression_level=19).compress(dates))
            if bytes(pa.Codec('zstd').decompress(compressed_dates,len(dates)))!=dates:
                raise ValueError('availability-date bitwise roundtrip differs')
            for suffix,raw in (('.numeric.zst',payload),('.json',json.dumps(metadata,sort_keys=True).encode()),('.dates.zst',compressed_dates)):
                member=tarfile.TarInfo(tf+suffix);member.size=len(raw);member.mtime=0;tar.addfile(member,io.BytesIO(raw))
            raw_bytes+=matrix.nbytes+len(dates)
            rows.append(dict(timeframe=tf,native_rows=len(values),columns=len(columns),raw_bytes=matrix.nbytes,
                             numeric_payload_bytes=len(payload),first_date=str(candles.date.min())[:10],
                             last_date=str(candles.date.max())[:10],roundtrip='ALL_FLOAT64_BITS_EXACT'))
    packed=bytes(pa.Codec('zstd',compression_level=19).compress(archive.getvalue()))
    file=root/(ticker.encode().hex()+'.all_native_values.tar.zst');file.write_bytes(packed)
    registry_file=root/(ticker.encode().hex()+'.column_registry.json');registry_file.write_text(json.dumps(registry,sort_keys=True,separators=(',',':')))
    query_years=len(bars[bars.date>=pd.Timestamp('2020-01-01')])/252
    report=dict(ticker=ticker,source_rows=len(bars),raw_numeric_and_date_bytes=raw_bytes,
        retained_value_container_bytes=len(packed),registry_bytes=registry_file.stat().st_size,
        bytes_per_query_stock_year=(len(packed)+registry_file.stat().st_size)/query_years,
        before_parquet_bytes=config['before_parquet_bytes'],
        before_bytes_per_query_stock_year=config['before_parquet_bytes']/query_years,
        compression_ratio=raw_bytes/len(packed),container_sha256=sha(packed),source_sha256=config['source_sha256'],
        recipe_fingerprint=config['recipe_fingerprint'],timeframes=rows,seconds=time.perf_counter()-started,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        scope='ALL_1044_COLUMNS_ALL_22_TIMEFRAMES_FULL_NATIVE_HISTORY; no row/column/value pruning, no downcasting',
        world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    (root/'NUMERIC_RETENTION_STOCK.json').write_text(json.dumps(report,indent=2)+'\n')
    print('NUMERIC_RETENTION_STOCK',json.dumps(report),flush=True)


def run(root,request):
    from ci.compact_world_build import snapshot,limited_process
    from ci.native_price_blocks import read_member
    from ci.release_assets import download_asset,gh_retry,publish_assets
    root.mkdir(parents=True,exist_ok=True)
    recipe,calendar=snapshot(root/'bound',request)
    inputs=json.loads((root/'bound'/'BUILD_INPUTS.json').read_text())
    file=download_asset(request['compact_source'],request['compact_part']+'.json',root/'source')
    manifest=json.loads(file.read_text())
    if manifest['recipe_fingerprint']!=inputs['recipe_fingerprint']:raise ValueError('compact source recipe differs')
    archive=download_asset(request['compact_source'],request['compact_part']+'.tar',root/'source')
    if sha(archive.read_bytes())!=manifest['archive_sha256']:raise ValueError('compact source archive differs')
    reports=[];errors=[];assets=[]
    previous=json.loads((REPO/'docs'/'PRICE_MATH_BUDGET_MEASURED_V2.json').read_text())
    if previous['corrected']['recipe_fingerprint']!=request['corrected_recipe_fingerprint']:
        raise ValueError('before/after numerical recipes differ')
    before={r['ticker']:r['compressed_bytes'] for r in previous['corrected']['entities']}
    for ticker in request['sample_tickers']:
        own=root/ticker.encode().hex();own.mkdir(exist_ok=True)
        raw=read_member(archive,manifest,ticker.encode().hex()+'.bars.parquet');(own/'bars.parquet').write_bytes(raw)
        (own/'market_sessions.parquet').write_bytes(calendar.read_bytes())
        config=dict(ticker=ticker,source_sha256=sha(raw),inputs_sha256=request['inputs_sha256'],
                    recipe_fingerprint=request['corrected_recipe_fingerprint'],before_parquet_bytes=before[ticker])
        (own/'INPUTS.json').write_text(json.dumps(config))
        outcome=limited_process([sys.executable,str(Path(__file__).resolve()),'--directory',str(own.resolve()),
            '--worker','--recipe',str(recipe.resolve())],own,request['stock_timeout_seconds'])
        if outcome['reason']:errors.append(dict(ticker=ticker,**outcome));continue
        report=json.loads((own/'NUMERIC_RETENTION_STOCK.json').read_text());reports.append(report)
        assets.extend([own/(ticker.encode().hex()+'.all_native_values.tar.zst'),own/(ticker.encode().hex()+'.column_registry.json')])
    estimate=max((r['retained_value_container_bytes']+r['registry_bytes'] for r in reports),default=0)*8727*1.25
    summary=dict(status='FULL_NUMERIC_RETENTION_MEASURED_SAMPLE_ONLY' if len(reports)==len(request['sample_tickers']) else 'INCOMPLETE_SAMPLE',
        source_commit=os.environ['GITHUB_SHA'],request=request,samples=reports,errors=errors,
        projected_full_universe_numeric_bytes=estimate,hard_world_cap_bytes=100000000000,
        numeric_scope_under_cap=bool(reports) and estimate<=100000000000,
        full_world_estimate_bytes=None,world_gate='NOT_PROVEN; add answers, raw/shared/nonprice dependencies and complete v3 coverage',
        approved_universe_run_preserved=40621517496,scoring_gate='CLOSED')
    file=root/'NUMERIC_RETENTION_MEASURED.json';file.write_text(json.dumps(summary,indent=2)+'\n')
    tag=f"numeric-retention-sample-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,file,*assets);gh_retry('release','edit',tag,'--draft=false')
    print('FULL_NUMERIC_RETENTION_ESTIMATE_GB',estimate/1e9,flush=True)
    if errors:raise RuntimeError('numeric retention sample incomplete; errors published, no approval inferred')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    parser.add_argument('--worker',action='store_true');parser.add_argument('--recipe')
    args=parser.parse_args();root=Path(args.directory)
    if args.worker:worker(root,Path(args.recipe))
    else:run(root,json.loads(REQUEST.read_text()))
