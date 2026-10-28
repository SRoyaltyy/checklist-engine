"""Persist the existing five VIX comparisons from verified native CBOE factors."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import pandas as pd

from ci.outside_market_released import checked_download
from ci.release_assets import download_asset,gh_retry,publish_assets
from ci.shared_context_build import normalize_index,verified_parquet
from market_storage import assert_exact_frame
from outside_vol import write_lossless
from world_context_native import KEYS,combine_contexts,index_native
from world_context_store import checked_weights,validate_factor,weighted_coverage
from world_timeframes import TIMEFRAMES
from world_volatility import term_native

LEVELS=('VIX','VIX9D','VIX3M','VVIX')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rebuild_indices(histories,calendar,tf):
    return combine_contexts([index_native(histories[name],calendar,tf,'cboe_'+name.lower()) for name in LEVELS])


def verify_cutoff(full,histories,calendar,value):
    cut=pd.Timestamp(value);earlier={name:frame[frame.DATE<cut] for name,frame in histories.items()};checks=[]
    for tf in TIMEFRAMES:
        rebuilt=rebuild_indices(earlier,calendar[calendar<=cut],tf)
        expected=full[tf][full[tf].available_from<=cut][list(rebuilt)].reset_index(drop=True)
        assert_exact_frame(expected,rebuilt)
        assert_exact_frame(term_native(expected),term_native(rebuilt))
        checks.append(dict(cut=value,timeframe=tf,native_rows=len(expected),source_columns=len(rebuilt.columns)-len(KEYS),ratio_columns=5,mismatches=0))
    return checks


def run(root,request):
    root.mkdir(parents=True,exist_ok=True)
    status_file=checked_download(request['shared_release'],'SHARED_CONTEXT_STATUS.json',request['shared_status_sha256'],root/'source')
    status=json.loads(status_file.read_text())
    if status['calendar_sha256']!=request['calendar_sha256'] or set(status['timeframes'])!=set(TIMEFRAMES):raise ValueError('native CBOE grid differs')
    if status['code_sha256']['world_context_native.py']!=sha('world_context_native.py'):raise ValueError('native source reader version differs')
    calendar_file=checked_download(request['inputs_release'],'market_sessions.parquet',request['calendar_sha256'],root/'source')
    calendar=pd.DatetimeIndex(pd.read_parquet(calendar_file).date).as_unit('ns')
    stocks_file=checked_download(request['stock_release'],'ACCEPTED_PRICE_STITCH.json',request['stock_status_sha256'],root/'stocks')
    stocks=json.loads(stocks_file.read_text())
    if stocks['accepted_tickers']!=8316 or stocks['original_universe']!=8727 or stocks['query_rows']!=12364370:raise ValueError('approved stock denominator differs')
    weights_file=checked_download(request['stock_release'],'ACCEPTED_PRICE_STOCK_DAYS.csv',stocks['stock_days_sha256'],root/'stocks')
    weights=pd.read_csv(weights_file);dates,numbers=checked_weights(weights)
    if int(numbers.sum())!=stocks['query_rows'] or not dates.isin(calendar).all():raise ValueError('stock-day weights differ')
    archive=checked_download(request['cboe_release'],'cboe_gap_source.tar.gz',request['cboe_archive_sha256'],root/'source')
    metadata=json.loads(Path('docs/CBOE_NUMERIC_SOURCE_STATUS_V1.json').read_text())['series'];histories={};sources=[]
    for name in LEVELS:
        frame,member=verified_parquet(archive,metadata[name]['parquet_sha256'])
        histories[name]=normalize_index(frame,metadata[name]);sources.append(dict(series=name,member=member,sha256=metadata[name]['parquet_sha256']))
    full={};bindings=[];coverage=[];files=[];rebuild_checks=[]
    parts={p['timeframe']:p for p in status['parts']}
    if len(parts)!=22:raise ValueError('native part count differs')
    tag=f"volatility-term-native-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    for tf in TIMEFRAMES:
        part=parts[tf];source=checked_download(request['shared_release'],part['file'],part['sha256'],root/'source')
        native=pd.read_parquet(source);rebuilt=rebuild_indices(histories,calendar,tf)
        assert_exact_frame(native[list(rebuilt)],rebuilt);full[tf]=native
        factor=term_native(native);columns=validate_factor(factor)
        file=root/('volatility_term_'+tf+'.parquet');stored=write_lossless(factor,file,())
        files.append(file);coverage.extend(weighted_coverage(factor,weights,tf,'volatility_term'))
        rebuild_checks.append(dict(timeframe=tf,native_rows=len(native),source_columns=len(rebuilt.columns)-len(KEYS),mismatches=0))
        bindings.append(dict(family='volatility_term',timeframe=tf,release=tag,asset=file.name,sha256=sha(file),
            columns=columns,numeric_dtypes={c:str(factor[c].dtype) for c in columns},native_rows=len(factor),
            source_release=request['shared_release'],source_asset=part['file'],source_sha256=part['sha256'],
            source_rule='Ratios of matching completed CBOE candle closes; explicit missing interval rows preserved; source availability unchanged'))
    prefix=[row for cut in request['cuts'] for row in verify_cutoff(full,histories,calendar,cut)]
    coverage_file=root/'VOLATILITY_TERM_STOCK_DAY_COVERAGE.csv'
    with coverage_file.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(coverage[0]));writer.writeheader();writer.writerows(coverage)
    store=dict(format='FACTORED_NATIVE_WORLD_CONTEXT_V1',stock_release=request['stock_release'],stock_status_sha256=request['stock_status_sha256'],
        stock_day_weight_asset='ACCEPTED_PRICE_STOCK_DAYS.csv',stock_day_weight_sha256=stocks['stock_days_sha256'],
        calendar_sha256=request['calendar_sha256'],calendar_release=request['inputs_release'],calendar_asset='market_sessions.parquet',
        original_universe=8727,accepted_stocks=8316,excluded_stocks=411,query_stock_days=stocks['query_rows'],
        source_commit=os.environ['GITHUB_SHA'],factors=bindings,reader='world_context_store.context_row_view',reader_sha256=sha('world_context_store.py'),
        world_gate='NOT_PROVEN',scoring_gate='CLOSED',scope='Five existing volatility comparisons only; no new data type or question')
    manifest_file=root/'VOLATILITY_TERM_FACTOR_STORE.json';manifest_file.write_text(json.dumps(store,indent=2)+'\n')
    report=dict(status='CBOE_NATIVE_TERM_FACTORS_MEASURED_NOT_FULL_WORLD',producer=os.environ['GITHUB_SHA'],request=request,
        source_members=sources,native_source_rebuild_checks=rebuild_checks,prefix_checks=prefix,
        factors=len(bindings),factor_bytes=sum(f.stat().st_size for f in files),column_timeframe_rows=len(coverage),
        zero_observation_rows=sum(r['non_null_stock_days']==0 for r in coverage),query_stock_days=stocks['query_rows'],
        manifest_sha256=sha(manifest_file),coverage_sha256=sha(coverage_file),source_status_sha256=sha(status_file),
        source_policy='Consistent CBOE numerator/denominator. Existing ALFRED VIXCLS levels and all original CBOE factors remain independently retained.',
        provider_requests=0,world_gate='NOT_PROVEN',scoring_gate='CLOSED',protected_world_run_untouched=40621517496,
        remaining=['integration with all other Tier1 factors','full existing-question quality and comprehensive world leak proof','historical eligibility and full dependency budget'])
    report_file=root/'VOLATILITY_TERM_MEASURED_V1.json';report_file.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,*files,coverage_file,manifest_file,report_file);gh_retry('release','edit',tag,'--draft=false')
    print('VOLATILITY_TERM_NATIVE',len(files),len(coverage),report['factor_bytes'],'PREFIX_CHECKS',len(prefix),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    run(args.directory,json.loads(Path('ci/VOLATILITY_TERM_REQUEST.json').read_text()))
