"""Bounded real-input proof for native comparisons; never a world approval."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd

from ci.release_assets import gh_retry, publish_assets
from ci.verify_etf_daily_source import raw_asset
from market_storage import assert_exact_frame, exact_arrow_table
from world_context_native import KEYS
from world_relative_context import native_comparisons
from world_timeframes import TIMEFRAMES


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_source(binding):
    raw=raw_asset(binding['release'],binding['asset'])
    if digest(raw)!=binding['sha256']:
        raise ValueError('relative source bytes differ: '+binding['asset'])
    if 'bytes' in binding and len(raw)!=binding['bytes']:
        raise ValueError('relative source size differs: '+binding['asset'])
    return raw


def matrix_receipt(frame):
    columns=[c for c in frame if c not in KEYS]
    values=np.ascontiguousarray(frame[columns].to_numpy(dtype='<f8'))
    dates=np.ascontiguousarray(frame[list(KEYS)].to_numpy(dtype='datetime64[ns]').view('<i8'))
    return dict(rows=len(frame),columns=columns,numeric_cells=int(values.size),
                numeric_bits_sha256=digest(values.tobytes()),date_bits_sha256=digest(dates.tobytes()),
                non_null_cells=int((~np.isnan(values)).sum()))


def measure(root,request):
    import pyarrow.parquet as pq
    root.mkdir(parents=True,exist_ok=True)
    parent=json.loads(checked_source(request['parent_proof']))
    if (parent['status']!='EXACT_RECOMPUTATION_SAMPLE_ONLY' or parent['errors']
            or {r['ticker'] for r in parent['samples']}!={'MAN','MNTS','EYE'}):
        raise ValueError('original three-stock proof differs')
    bindings=request['stocks']
    if {r['ticker'] for r in bindings}!={'MAN','MNTS','EYE'} or len(bindings)!=3:
        raise ValueError('relative proof must retain the same three stocks')
    original={r['ticker']:r['raw_source_sha256'] for r in parent['samples']}
    for binding in bindings:
        if original[binding['ticker']]!=binding['sha256']:
            raise ValueError('relative sample changed original stock input')
    if request['benchmark']['sha256']!=parent['etf']['raw_source_sha256']:
        raise ValueError('relative sample changed original ETF input')
    calendar=pd.DatetimeIndex(pd.read_parquet(io.BytesIO(checked_source(request['calendar']))).date).as_unit('ns')
    benchmark=pd.read_parquet(io.BytesIO(checked_source(request['benchmark'])))
    cutoffs=[pd.Timestamp(value) for value in request['cutoffs']]
    if len(cutoffs)!=2 or any(day not in calendar for day in cutoffs):
        raise ValueError('relative proof requires two real cutoff sessions')
    results=[]
    for binding in bindings:
        stock=pd.read_parquet(io.BytesIO(checked_source(binding)))
        started=time.perf_counter();checks=[];prefixes=[]
        for tf in TIMEFRAMES:
            args=(binding['ticker'],'SPY',stock,benchmark,calendar,tf)
            baseline=native_comparisons(*args,calendar[-1])
            file=root/(binding['ticker']+'_'+tf+'.parquet')
            pq.write_table(exact_arrow_table(baseline),file,compression='zstd',compression_level=19)
            reopened=pd.read_parquet(file)
            assert_exact_frame(baseline,reopened)
            rebuilt=native_comparisons(*args,calendar[-1])
            assert_exact_frame(reopened,rebuilt)
            receipt=matrix_receipt(rebuilt)
            checks.append(dict(timeframe=tf,**receipt,stored_bytes=file.stat().st_size,
                               persisted_sha256=digest(file.read_bytes()),recomputed_mismatches=0))
            for cut in cutoffs:
                earlier=native_comparisons(binding['ticker'],'SPY',stock.loc[stock.date<cut],
                                           benchmark.loc[benchmark.date<cut],calendar,tf,cut)
                expected=baseline.loc[baseline.available_from<=cut].reset_index(drop=True)
                assert_exact_frame(expected,earlier)
                prefixes.append(dict(timeframe=tf,cut=str(cut.date()),**matrix_receipt(earlier),mismatches=0))
        results.append(dict(ticker=binding['ticker'],checks=checks,prefixes=prefixes,seconds=time.perf_counter()-started))
    code_names=('world_relative_context.py','outside_compare.py','outside_market.py','world_bar_statistics.py',
                'world_context_native.py','world_context_store.py','world_timeframes.py','world_fred.py','world_dates.py',
                'market_storage.py','ci/relative_native_measure.py','requirements-world-v2.txt')
    code={name:digest(Path(name).read_bytes()) for name in code_names}
    return dict(status='THREE_STOCK_ONE_ETF_NATIVE_SAMPLE_ONLY',source_commit=os.environ['GITHUB_SHA'],request=request,
                samples=results,timeframes=list(TIMEFRAMES),prefix_checks=sum(len(r['prefixes']) for r in results),
                raw_stock_bytes=sum(r['bytes'] for r in bindings),raw_etf_bytes=request['benchmark']['bytes'],
                code_sha256=code,runtime={n:importlib.metadata.version(n) for n in ('numpy','pandas','pyarrow')},
                storage='Native frames used only as independent persisted references; recompute from immutable raw sources and bound code.',
                universe='Three survivors only; no historical tradeability/sector/industry membership claim.',
                full_universe_estimate_bytes=None,full_world_storage_gate='NOT_PROVEN',world_gate='NOT_PROVEN',scoring_gate='CLOSED',
                protected_world_run_untouched=40621517496)


def run(root,request):
    report=measure(root,request)
    file=root/'RELATIVE_NATIVE_MEASURED_V1.json'
    file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"relative-native-sample-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','Three-stock/SPY exact native reconstruction and prefix checks; sample only, no full-world or storage-cap acceptance.')
    publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    if digest(raw_asset(tag,file.name))!=digest(file.read_bytes()):
        raise ValueError('published native comparison proof differs')
    print('RELATIVE_NATIVE_SAMPLE_COMPLETE',tag,len(report['samples']),report['prefix_checks'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    run(args.directory,json.loads(Path('ci/RELATIVE_NATIVE_REQUEST.json').read_text(encoding='utf-8')))
