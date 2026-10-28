"""Correct availability of the completed full-universe V2 breadth counters.

No raw rebuild or provider fetch: use the authenticated full-history release
whose all8316 source inputs and44 raw cutoff checks already passed.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from ci.audit_factor_assets import audit
from ci.breadth_native_history import checked_download, check_grid, legacy_overlap, native_factor, sha
from ci.release_assets import gh_retry, publish_assets, release_info
from market_storage import assert_exact_frame, exact_arrow_table
from outside_breadth import available_breadth, breadth_candles, checked_sessions, write_lossless
from world_context_native import KEYS
from world_context_store import checked_weights, validate_factor, weighted_coverage
from world_timeframes import TIMEFRAMES


def availability_changes(before,after,keys):
    before=before.sort_values(keys).reset_index(drop=True)
    after=after.sort_values(keys).reset_index(drop=True)
    if not before[keys].equals(after[keys]) or list(before)!=list(after):
        raise ValueError('availability correction changed rows or source schema')
    result={}
    for column in before:
        if column in keys or before[column].dtype.kind=='M':
            if not before[column].equals(after[column]):raise ValueError('availability correction changed source keys')
            continue
        a=before[column].to_numpy(dtype='float64');b=after[column].to_numpy(dtype='float64')
        known=~np.isnan(b)
        if (np.isnan(a)&known).any() or not np.array_equal(a[known].view('uint64'),b[known].view('uint64')):
            raise ValueError('availability correction changed an observed numeric value: '+column)
        lost=(~np.isnan(a))&np.isnan(b)
        if lost.any():result[column]=dict(newly_unavailable=int(lost.sum()),last_date=str(pd.Timestamp(after.loc[lost,'date'].max()).date()))
    return result


def corrected_prefix_checks(parent,full,native,calendar,cuts):
    checks=[]
    for value in cuts:
        cut=pd.Timestamp(value)
        earlier=available_breadth(parent.loc[parent.date<cut].reset_index(drop=True))
        assert_exact_frame(full.loc[full.date<cut].reset_index(drop=True),earlier)
        built=breadth_candles(earlier,calendar)
        for tf in TIMEFRAMES:
            expected=native.loc[(native.timeframe==tf)&(native.available_from<=cut)].reset_index(drop=True)
            actual=built.loc[(built.timeframe==tf)&(built.available_from<=cut)].reset_index(drop=True)
            assert_exact_frame(expected,actual)
            checks.append(dict(cut=value,timeframe=tf,native_rows=len(actual),mismatches=0))
    return checks


def run(root,request):
    import exchange_calendars as xcals
    root.mkdir(parents=True,exist_ok=True)
    tag=request['parent_release'];source=root/'parent'
    report_file=checked_download(tag,'BREADTH_NATIVE_HISTORY_MEASURED_V2.json',request['parent_report_sha256'],source)
    parent_report=json.loads(report_file.read_text(encoding='utf-8'))
    if (parent_report['source_commit']!='69929e44f2dfdb069a48b4846fe007a90bbb8b5a'
            or parent_report['accepted_names']!=8316 or parent_report['new_exclusions']
            or len(parent_report['raw_prefix_checks'])!=44
            or any(r['mismatches'] for r in parent_report['raw_prefix_checks'])):
        raise ValueError('parent full-universe proof differs')
    daily_file=checked_download(tag,'breadth_daily_full_history_v2.parquet',request['parent_daily_sha256'],source)
    native_file=checked_download(tag,'breadth_native_full_history_v2.parquet',request['parent_native_sha256'],source)
    parent=pd.read_parquet(daily_file);old_native=pd.read_parquet(native_file)
    frozen_file=checked_download(request['calendar_release'],'market_sessions.parquet',request['calendar_sha256'],root/'calendar')
    frozen=checked_sessions(pd.read_parquet(frozen_file).date)
    end=parent.date.max()+pd.Timedelta(days=45)
    exchange=xcals.get_calendar('XNYS',start='1990-01-01',end=str(end.date()))
    calendar=checked_sessions(exchange.sessions_in_range('1990-01-02',str(end.date())).tz_localize(None))
    if not np.array_equal(frozen.asi8,calendar[:len(frozen)].asi8):
        raise ValueError('availability correction changed the frozen calendar prefix')
    daily=available_breadth(parent)
    native=breadth_candles(daily,calendar)
    check_grid(native,calendar)
    daily_changes=availability_changes(parent,daily,['date'])
    native_changes=availability_changes(old_native,native,['timeframe','date'])
    if any(pd.Timestamp(row['last_date'])>=pd.Timestamp('2020-01-01') for row in [*daily_changes.values(),*native_changes.values()]):
        raise ValueError('unexpected availability change inside the measured study window')
    checks=corrected_prefix_checks(parent,daily,native,calendar,request['cutoffs'])
    prior=parent_report['request']
    old_daily_file=checked_download(prior['legacy_release'],'outside_breadth_daily.parquet',prior['legacy_daily_sha256'],root/'legacy')
    old_native_file=checked_download(prior['legacy_release'],'outside_breadth_candles.parquet',prior['legacy_native_sha256'],root/'legacy')
    overlap=legacy_overlap(daily,native,calendar,pd.read_parquet(old_daily_file),pd.read_parquet(old_native_file))
    weight_file=checked_download(prior['stock_release'],'ACCEPTED_PRICE_STOCK_DAYS.csv',prior['weights_sha256'],root/'weights')
    weights=pd.read_csv(weight_file);dates,multipliers=checked_weights(weights)
    if int(multipliers.sum())!=12364370 or not dates.isin(calendar).all():raise ValueError('breadth denominator differs')
    release=f"outside-breadth-native-v3-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    outputs=[]
    for frame,name in ((daily,'breadth_daily_full_history_v3.parquet'),(native,'breadth_native_full_history_v3.parquet')):
        file=root/name;write_lossless(frame,file);outputs.append(file)
    universe='SURVIVORS_ONLY_APPROVED_STITCH_V2; historical tradeability/size not established'
    bindings=[];coverage=[]
    for tf in TIMEFRAMES:
        frame=native_factor(native.loc[native.timeframe==tf].reset_index(drop=True))
        table=exact_arrow_table(frame)
        for index,name in enumerate(table.column_names):
            if name not in KEYS:
                field=table.schema.field(index).with_metadata({b'universe_label':universe.encode(),b'availability_rule':b'unknown history remains missing; source_candle_end < available_from <= stock D'})
                table=table.set_column(index,field,table.column(index))
        file=root/f'breadth_{tf}.parquet';pq.write_table(table,file,compression='zstd',compression_level=19)
        assert_exact_frame(frame,pd.read_parquet(file));outputs.append(file)
        columns=validate_factor(frame)
        bindings.append(dict(family='breadth',timeframe=tf,release=release,asset=file.name,sha256=sha(file),native_rows=len(frame),columns=columns,numeric_dtypes={c:str(frame[c].dtype) for c in columns}))
        coverage.extend(dict(row,universe_label=universe) for row in weighted_coverage(frame,weights,tf,'breadth'))
    cover=root/'BREADTH_STOCK_DAY_COVERAGE_V3.csv';pd.DataFrame(coverage).to_csv(cover,index=False);outputs.append(cover)
    store=dict(format='FACTORED_NATIVE_WORLD_CONTEXT_V1',source_commit=os.environ['GITHUB_SHA'],stock_release=prior['stock_release'],stock_status_sha256=prior['stock_status_sha256'],
               stock_day_weight_sha256=prior['weights_sha256'],calendar_sha256=prior['calendar_sha256'],query_stock_days=12364370,factors=bindings,
               reader='world_context_store.context_row_view',world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    manifest=root/'BREADTH_FACTOR_STORE_V3.json';manifest.write_text(json.dumps(store,indent=2)+'\n',encoding='utf-8');outputs.append(manifest)
    result=dict(status='FULL_HISTORY_BREADTH_WITH_EXPLICIT_UNKNOWN_WARMUP_NOT_WORLD',source_commit=os.environ['GITHUB_SHA'],request=request,
                parent_raw_run=40718683563,parent_report_sha256=sha(report_file),accepted_names=8316,new_exclusions=[],daily_rows=len(daily),native_rows=len(native),
                pre2020_daily_rows=int((daily.date<pd.Timestamp('2020-01-01')).sum()),timeframes=list(TIMEFRAMES),partial_native_buckets=0,
                parent_raw_prefix_checks=parent_report['raw_prefix_checks'],availability_prefix_checks=checks,
                daily_availability_changes=daily_changes,native_availability_changes=native_changes,changed_known_numeric_cells=0,legacy_overlap=overlap,
                source_counters_retained=dict(release=tag,asset=daily_file.name,sha256=sha(daily_file)),
                native_factor_bytes=sum((root[row['asset']]).stat().st_size for row in bindings),data_asset_bytes=sum(file.stat().st_size for file in outputs if file.suffix=='.parquet'),
                coverage_rows=len(coverage),minimum_non_null_stock_day_pct=min(row['non_null_pct'] for row in coverage),factor_manifest_sha256=sha(manifest),
                runtime={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','exchange_calendars')},
                world_gate='NOT_PROVEN',full_world_storage_gate='NOT_PROVEN',scoring_gate='CLOSED')
    measured=root/'BREADTH_WARMUP_MEASURED_V3.json';measured.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');outputs.append(measured)
    gh_retry('release','create',release,'--draft','--title',release,'--target',os.environ['GITHUB_SHA'],
             '--notes','Corrected unknown warmup from authenticated full-universe breadth V2; original counters and proofs remain immutable; not full-world approval.')
    publish_assets(release,*outputs);gh_retry('release','edit',release,'--draft=false')
    inventory=release_info(release);readback=root/'published-readback'
    for binding in bindings:checked_download(release,binding['asset'],binding['sha256'],readback/release)
    audited=audit(store,readback,{release:inventory},result['native_factor_bytes'])
    readback_file=root/'BREADTH_PUBLISHED_FACTOR_READBACK_V3.json';readback_file.write_text(json.dumps(audited,indent=2)+'\n',encoding='utf-8');publish_assets(release,readback_file)
    if audited['failures']:raise ValueError('published warmup factor readback failed')
    print('BREADTH_WARMUP_COMPLETE',release,len(daily),len(native),result['native_factor_bytes'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    run(args.directory,json.loads(Path('ci/BREADTH_WARMUP_FIX_REQUEST.json').read_text(encoding='utf-8')))
