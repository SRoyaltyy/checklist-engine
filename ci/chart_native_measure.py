"""Real-input default chart-tag proof; no full-world/variable-grid approval."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import time

import pandas as pd

from ci.relative_native_measure import checked_source,matrix_receipt
from ci.release_assets import gh_retry,publish_assets
from ci.verify_etf_daily_source import raw_asset
from market_storage import assert_exact_frame,exact_arrow_table
from world_chart_picture import DEFAULT,PIN,native_chart_picture
from world_context_native import KEYS
from world_timeframes import TIMEFRAMES

REQUEST=Path('ci/CHART_NATIVE_REQUEST.json')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def measure(root,request):
    import pyarrow.parquet as pq
    if request['pin']!=PIN or request['settings']!=asdict(DEFAULT):raise ValueError('chart proof must bind the exact named defaults')
    parent=json.loads(checked_source(request['parent_proof']))
    if parent['errors'] or parent['status']!='EXACT_RECOMPUTATION_SAMPLE_ONLY':raise ValueError('chart original sample proof differs')
    bindings=[*request['stocks'],dict(request['benchmark'],ticker='SPY')]
    if len(bindings)!=4 or {b['ticker'] for b in bindings}!={'MAN','MNTS','EYE','SPY'}:raise ValueError('chart proof requires original3 stocks plus SPY')
    original={r['ticker']:r['raw_source_sha256'] for r in parent['samples']};original['SPY']=parent['etf']['raw_source_sha256']
    if any(b['sha256']!=original[b['ticker']] for b in bindings):raise ValueError('chart immutable sample input changed')
    calendar=pd.DatetimeIndex(pd.read_parquet(io.BytesIO(checked_source(request['calendar']))).date).as_unit('ns')
    cuts=[pd.Timestamp(c) for c in request['cutoffs']]
    if len(cuts)!=2 or len(set(cuts))!=2 or any(c not in calendar for c in cuts):raise ValueError('two actual chart cutoff sessions required')
    root.mkdir(parents=True,exist_ok=True);samples=[]
    for binding in bindings:
        bars=pd.read_parquet(io.BytesIO(checked_source(binding)));checks=[];prefixes=[];started=time.perf_counter()
        for tf in TIMEFRAMES:
            full=native_chart_picture(bars,calendar,tf,calendar[-1])
            if (len(full.columns)-len(KEYS)!=request['expected_numeric_columns']
                    or not set(request['required_default_tags'])<=set(full.columns)):
                raise ValueError('chart pinned output schema differs')
            file=root/(binding['ticker']+'_'+tf+'.parquet')
            pq.write_table(exact_arrow_table(full),file,compression='zstd',compression_level=9)
            readback=pd.read_parquet(file);assert_exact_frame(full,readback)
            rebuilt=native_chart_picture(bars,calendar,tf,calendar[-1]);assert_exact_frame(readback,rebuilt)
            checks.append(dict(timeframe=tf,**matrix_receipt(rebuilt),persisted_bytes=file.stat().st_size,
                               persisted_sha256=sha(file.read_bytes()),source=full.attrs['source'],mismatches=0))
            for cut in cuts:
                # Truncate both raw inputs and calendar, preserving its original anchor.
                earlier=native_chart_picture(bars.loc[bars.date<cut],calendar[calendar<=cut],tf,cut)
                expected=full.loc[full.available_from<=cut].reset_index(drop=True)
                assert_exact_frame(expected,earlier)
                prefixes.append(dict(timeframe=tf,cut=str(cut.date()),**matrix_receipt(earlier),mismatches=0))
            progress=dict(status='INCOMPLETE_CHART_DEFAULT_SAMPLE',ticker=binding['ticker'],checks=checks,prefixes=prefixes)
            (root/'CHART_NATIVE_PROGRESS.json').write_text(json.dumps(progress,indent=2)+'\n',encoding='utf-8')
        samples.append(dict(ticker=binding['ticker'],source_sha256=binding['sha256'],checks=checks,prefixes=prefixes,seconds=time.perf_counter()-started))
        print('CHART_NATIVE_INPUT_COMPLETE',binding['ticker'],len(checks),len(prefixes),flush=True)
    code_names=('world_chart_picture.py','ci/chart_native_measure.py','ci/relative_native_measure.py','world_relative_context.py',
                'outside_compare.py','outside_market.py','world_bar_statistics.py','world_context_native.py','world_context_store.py',
                'world_timeframes.py','world_fred.py','world_dates.py','market_storage.py','requirements-world-v2.txt')
    return dict(status='FOUR_INPUT_CHART_NATIVE_DEFAULT_SAMPLE_ONLY',source_commit=os.environ['GITHUB_SHA'],request=request,
                samples=samples,timeframes=list(TIMEFRAMES),native_frames=sum(len(s['checks']) for s in samples),
                prefix_checks=sum(len(s['prefixes']) for s in samples),
                numeric_cells=sum(c['numeric_cells'] for s in samples for c in s['checks']),
                known_numeric_cells=sum(c['non_null_cells'] for s in samples for c in s['checks']),
                reference_bytes=sum(c['persisted_bytes'] for s in samples for c in s['checks']),
                code_sha256={name:sha(Path(name).read_bytes()) for name in code_names},
                column_aliases=full.attrs['aliases'],numeric_columns_per_frame=request['expected_numeric_columns'],
                runtime={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow')},
                storage='Temporary exact native references only; raw sources/code/settings remain bound for reconstruction.',
                full_registered_grid_gate='NOT_RUN_DEFAULTS_ONLY',full_universe_gate='NOT_RUN',full_world_gate='NOT_PROVEN',
                comprehensive_leak_gate='NOT_PROVEN',full_dependency_budget_gate='NOT_PROVEN',scoring_gate='CLOSED',protected_run_untouched=40621517496)


def run(root,request):
    report=measure(root,request);file=root/'CHART_NATIVE_MEASURED_V1.json'
    file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"chart-native-default-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','Original3 stocks plus SPY, pinned default chart tags on22 genuine grids with exact reconstruction/cutoff checks. Not full variable-grid/universe/world/quality/PIT/cap/scoring approval.')
    publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    if sha(raw_asset(tag,file.name))!=sha(file.read_bytes()):raise ValueError('chart public report readback differs')
    print('CHART_NATIVE_SAMPLE_COMPLETE',tag,report['native_frames'],report['prefix_checks'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    run(args.directory,json.loads(REQUEST.read_text(encoding='utf-8')))
