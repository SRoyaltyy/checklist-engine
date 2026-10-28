"""Bounded exact-recomputation proof under James/Cyrus's 2026-10-28 plan."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))


def sha(raw):return hashlib.sha256(raw).hexdigest()


def compare_frame(frame,columns,metadata,date_column='available_from'):
    """Compare the complete regenerated matrix, including every NaN/sign bit."""
    import numpy as np
    if list(frame.drop(columns=date_column))!=columns:raise ValueError('recomputed column registry differs')
    values=np.ascontiguousarray(frame[columns].to_numpy(dtype=np.float64),dtype='<f8')
    dates=frame[date_column].to_numpy(dtype='datetime64[ns]').view('<i8').tobytes()
    if values.shape!=(metadata['rows'],len(columns)):raise ValueError('recomputed native shape differs')
    if sha(values.tobytes())!=metadata['raw_sha256']:raise ValueError('recomputed float64 bits differ')
    if sha(dates)!=metadata['dates_sha256']:raise ValueError('recomputed availability date bits differ')
    return dict(rows=len(values),columns=len(columns),numeric_cells=values.size,mismatches=0,
                raw_sha256=sha(values.tobytes()),dates_sha256=sha(dates))


def stock_worker(root,recipe):
    # Import the independently hash-checked historical recipe before the current repo.
    sys.path[:0]=[str(recipe),str(REPO)]
    import resource
    import pandas as pd
    import facets_world as fw
    from world_timeframes import TIMEFRAMES,completed_candles,candle_features
    from ci.numeric_reencode_measure import checked_members
    config=json.loads((root/'WORKER.json').read_text());started=time.perf_counter()
    raw=Path(config['bars']).read_bytes()
    if sha(raw)!=config['stock']['source_sha256']:raise ValueError('raw source bars differ')
    bars=pd.read_parquet(io.BytesIO(raw));calendar=pd.DatetimeIndex(pd.read_parquet(config['calendar']).date)
    members=checked_members(Path(config['container']).read_bytes())
    if sha(Path(config['container']).read_bytes())!=config['stock']['container_sha256']:raise ValueError('source numeric container differs')
    registry=json.loads(Path(config['registry']).read_text());funcs=fw.discover();checks=[]
    for tf in TIMEFRAMES:
        metadata=json.loads(members[tf+'.json'])
        frame=candle_features(completed_candles(bars,tf,session_calendar=calendar),funcs,timeframe=tf)
        check=compare_frame(frame,registry[tf]['columns'],metadata);check['timeframe']=tf;checks.append(check)
        print('EXACT_RECOMPUTE_FRAME',config['stock']['ticker'],tf,check['numeric_cells'],flush=True)
    result=dict(ticker=config['stock']['ticker'],raw_source_sha256=sha(raw),raw_source_bytes=len(raw),
        original_container_sha256=config['stock']['container_sha256'],original_container_bytes=Path(config['container']).stat().st_size,
        recipe_fingerprint=config['stock']['recipe_fingerprint'],checks=checks,all_native_values_bit_exact=True,
        seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (root/'RECOMPUTE_STOCK.json').write_text(json.dumps(result,indent=2)+'\n')


def etf_worker(root,recipe):
    sys.path[:0]=[str(recipe),str(REPO)]
    import numpy as np
    import pandas as pd
    from world_context_native import KEYS,price_native
    config=json.loads((root/'ETF_WORKER.json').read_text());started=time.perf_counter()
    raw=Path(config['bars']).read_bytes()
    if sha(raw)!=config['source_sha256']:raise ValueError('ETF daily source differs')
    bars=pd.read_parquet(io.BytesIO(raw));calendar=pd.DatetimeIndex(pd.read_parquet(config['calendar']).date);checks=[]
    for part in config['parts']:
        file=Path(part['path']);packed=file.read_bytes()
        if sha(packed)!=part['sha256']:raise ValueError('ETF persisted context differs')
        old=pd.read_parquet(io.BytesIO(packed));columns=[c for c in old if c.startswith('etf_spy_')]
        if not columns:raise ValueError('SPY block absent from source context')
        regenerated=price_native(bars,calendar,part['timeframe'],'etf_spy')
        if list(regenerated)!=[*KEYS,*columns]:raise ValueError('ETF recomputed schema differs')
        for key in KEYS:
            if old[key].to_numpy(dtype='datetime64[ns]').tobytes()!=regenerated[key].to_numpy(dtype='datetime64[ns]').tobytes():
                raise ValueError('ETF recomputed grid differs')
        expected=np.ascontiguousarray(old[columns].to_numpy(dtype='<f8'))
        actual=np.ascontiguousarray(regenerated[columns].to_numpy(dtype='<f8'))
        if expected.shape!=actual.shape or expected.tobytes()!=actual.tobytes():raise ValueError('ETF recomputed float64 bits differ')
        checks.append(dict(timeframe=part['timeframe'],rows=len(old),columns=len(columns),numeric_cells=expected.size,
                           raw_sha256=sha(actual.tobytes()),mismatches=0))
    (root/'ETF_RECOMPUTE.json').write_text(json.dumps(dict(symbol='SPY',checks=checks,seconds=time.perf_counter()-started,
        raw_source_sha256=sha(raw),raw_source_bytes=len(raw),all_native_values_bit_exact=True,
        storage_policy='ONE_RAW_ETF_SERIES_SHARED_BY_ALL_STOCKS; no historical membership claim'),indent=2)+'\n')


def run(root,request):
    from ci.compact_world_build import snapshot,limited_process
    from ci.native_price_blocks import read_member
    from ci.release_assets import download_asset,gh_retry,publish_assets
    from ci.numeric_reencode_measure import file_digest,FRAMES
    root.mkdir(parents=True,exist_ok=True);source_dir=root.parent/'numeric-reencode'/'source'
    source=download_asset(request['source_release'],'NUMERIC_RETENTION_MEASURED.json',source_dir)
    if file_digest(source)!=request['source_report_sha256']:raise ValueError('persisted measurement changed')
    source_report=json.loads(source.read_text());frozen=source_report['request'];stocks={r['ticker']:r for r in source_report['samples']}
    if source_report['errors'] or set(stocks)!=set(request['sample_tickers']) or len(request['sample_tickers'])!=len(stocks):raise ValueError('incomplete source sample')
    recipe,calendar=snapshot(root/'bound',frozen)
    manifest_file=download_asset(frozen['compact_source'],frozen['compact_part']+'.json',root/'source')
    manifest=json.loads(manifest_file.read_text());archive=download_asset(frozen['compact_source'],frozen['compact_part']+'.tar',root/'source')
    if file_digest(archive)!=manifest['archive_sha256']:raise ValueError('raw source archive differs')
    results=[];errors=[];assets=[]
    for ticker in request['sample_tickers']:
        stock=stocks[ticker];stem=ticker.encode().hex();own=root/stem;own.mkdir(exist_ok=True)
        bars=own/(stem+'.bars.parquet');bars.write_bytes(read_member(archive,manifest,stem+'.bars.parquet'))
        container=download_asset(request['source_release'],stem+'.all_native_values.tar.zst',source_dir)
        registry=download_asset(request['source_release'],stem+'.column_registry.json',source_dir)
        config=dict(stock=stock,bars=str(bars.resolve()),calendar=str(calendar.resolve()),container=str(container.resolve()),registry=str(registry.resolve()))
        (own/'WORKER.json').write_text(json.dumps(config))
        outcome=limited_process([sys.executable,str(Path(__file__).resolve()),'--worker','stock','--directory',str(own.resolve()),'--recipe',str(recipe.resolve())],own,900)
        assets.append(bars)
        if outcome['reason']:errors.append(dict(ticker=ticker,**outcome));continue
        results.append(json.loads((own/'RECOMPUTE_STOCK.json').read_text()))
    # One independently persisted ETF block, reconstructed from its own historical producer.
    etf=request['etf'];own=root/'etf';own.mkdir(exist_ok=True)
    status_file=download_asset(etf['release'],'ETF_CONTEXT_STATUS.json',own)
    if file_digest(status_file)!=etf['status_sha256']:raise ValueError('ETF source status differs')
    status=json.loads(status_file.read_text());etf_recipe=own/'recipe';etf_recipe.mkdir(exist_ok=True)
    subprocess.run(['git','fetch','--depth=1','origin',status['source_commit']],check=True)
    etf_code={}
    for name in ('world_context_native.py','world_timeframes.py','world_fred.py','world_dates.py'):
        raw=subprocess.check_output(['git','show',status['source_commit']+':'+name]);(etf_recipe/name).write_bytes(raw);etf_code[name]=sha(raw)
    daily=next(r for r in status['daily_sources'] if r['ticker']=='SPY')
    bars=download_asset(etf['release'],daily['file'],own)
    parts=[]
    if {p['timeframe'] for p in status['parts']}!=set(FRAMES):raise ValueError('ETF timeframe set differs')
    for part in status['parts']:
        file=download_asset(etf['release'],part['file'],own/'source')
        parts.append(dict(part,path=str(file.resolve())))
    (own/'ETF_WORKER.json').write_text(json.dumps(dict(bars=str(bars.resolve()),calendar=str(calendar.resolve()),source_sha256=daily['sha256'],parts=parts)))
    outcome=limited_process([sys.executable,str(Path(__file__).resolve()),'--worker','etf','--directory',str(own.resolve()),'--recipe',str(etf_recipe.resolve())],own,900)
    etf_result=None
    if outcome['reason']:errors.append(dict(block='ETF_SPY',**outcome))
    else:etf_result=json.loads((own/'ETF_RECOMPUTE.json').read_text())
    assets.append(bars)
    versions={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','TA-Lib')}
    summary=dict(status='EXACT_RECOMPUTATION_SAMPLE_ONLY' if not errors and len(results)==3 and etf_result else 'INCOMPLETE_RECOMPUTATION_SAMPLE',
        source_commit=os.environ['GITHUB_SHA'],authority='James/Cyrus 9f390e2 storage plan; supersedes prior no-recompute rule',
        request=request,samples=results,etf=etf_result,errors=errors,environment=dict(python=sys.version,packages=versions),
        stock_recipe_commit=frozen['corrected_commit'],stock_recipe_fingerprint=frozen['corrected_recipe_fingerprint'],
        etf_recipe_commit=status['source_commit'],etf_recipe_files=etf_code,
        raw_source_archive_sha256=manifest['archive_sha256'],calendar_sha256=file_digest(calendar),
        full_universe_estimate_bytes=None,world_gate='NOT_PROVEN; complete dependency inventory and full-universe reproducibility pending',scoring_gate='CLOSED',approved_world_run_untouched=40621517496)
    file=root/'NUMERIC_RECOMPUTE_MEASURED.json';file.write_text(json.dumps(summary,indent=2)+'\n')
    tag=f"numeric-recompute-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,file,*assets);gh_retry('release','edit',tag,'--draft=false')
    if errors:raise RuntimeError('recomputed values differ or timed out; no storage acceptance')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--worker',choices=('stock','etf'));parser.add_argument('--recipe',type=Path)
    args=parser.parse_args()
    if args.worker=='stock':stock_worker(args.directory,args.recipe)
    elif args.worker=='etf':etf_worker(args.directory,args.recipe)
    else:run(args.directory,json.loads((REPO/'ci/NUMERIC_REENCODE_REQUEST.json').read_text()))
