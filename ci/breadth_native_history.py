"""Immutable full-history breadth from existing approved price archives only."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import tarfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from ci.release_assets import download_asset, gh_retry, publish_assets, release_info
from ci.audit_factor_assets import audit
from market_storage import assert_exact_frame, exact_arrow_table
from outside_breadth import COUNT_COLUMNS, WINDOW_START, aggregate, breadth_candles, checked_sessions, stock_contributions, write_lossless
from world_context_native import KEYS
from world_context_store import checked_weights, validate_factor, weighted_coverage
from world_timeframes import TIMEFRAMES


def sha(file):
    digest = hashlib.sha256()
    with Path(file).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def checked_download(tag, name, fingerprint, directory):
    file = download_asset(tag, name, directory)
    if sha(file) != fingerprint:
        raise ValueError('breadth source fingerprint differs: ' + name)
    return file


def native_factor(frame):
    out = frame.drop(columns='timeframe').rename(columns={'date':'source_candle_end'}).copy()
    features = [c for c in out if c not in KEYS]
    out = out.rename(columns={c:'breadth_'+c for c in features})
    out = out.loc[:,list(KEYS)+['breadth_'+c for c in features]].sort_values('available_from').reset_index(drop=True)
    validate_factor(out)
    return out


def check_grid(frame, calendar):
    if set(frame.timeframe) != set(TIMEFRAMES):
        raise ValueError('breadth native grid incomplete')
    calendar = checked_sessions(calendar)
    periods = calendar.to_period('M')
    for row in frame[['timeframe','candle_start','date','available_from']].itertuples(index=False):
        end = calendar.get_indexer([row.date])[0]
        if end < 0 or end+1 >= len(calendar) or row.available_from != calendar[end+1]:
            raise ValueError('breadth availability differs from the next frozen-prefix session')
        if row.timeframe == 'monthly':
            own = calendar[periods == pd.Timestamp(row.date).to_period('M')]
            if row.candle_start != own[0] or row.date != own[-1]:
                raise ValueError('partial breadth month')
        else:
            n = int(row.timeframe[:-1])
            if (end+1)%n or row.candle_start != calendar[end-n+1]:
                raise ValueError('partial or reanchored breadth candle')


def prefix_checks(full_daily, full_native, earlier, calendar):
    checks = []
    for cut, votes in earlier.items():
        cut = pd.Timestamp(cut)
        daily = aggregate(votes, calendar, cut-pd.Timedelta(days=1), retain_history=True)
        expected = full_daily.loc[full_daily.date < cut].reset_index(drop=True)
        assert_exact_frame(expected, daily)
        native = breadth_candles(daily, calendar)
        for tf in TIMEFRAMES:
            a = native.loc[(native.timeframe == tf)&(native.available_from <= cut)].reset_index(drop=True)
            b = full_native.loc[(full_native.timeframe == tf)&(full_native.available_from <= cut)].reset_index(drop=True)
            assert_exact_frame(b, a)
            checks.append(dict(cut=str(cut.date()), timeframe=tf, native_rows=len(a), columns=list(a), mismatches=0))
    return checks


def legacy_overlap(daily, native, calendar, old_daily, old_native):
    """Prove every V1 daily value, and every complete V1 native value retained."""
    offset = int(daily.loc[daily.date < WINDOW_START,'ad_net'].sum())
    restored = daily.loc[daily.date.isin(old_daily.date),list(old_daily)].reset_index(drop=True).copy()
    restored['ad_line'] -= offset
    assert_exact_frame(old_daily.reset_index(drop=True), restored)
    complete = []
    for row in old_native[['timeframe','candle_start','date']].itertuples(index=False):
        if row.timeframe == 'monthly':
            expected = calendar[calendar.to_period('M') == pd.Timestamp(row.date).to_period('M')][0]
        else:
            pos = calendar.get_indexer([row.date])[0]
            expected = calendar[pos-int(row.timeframe[:-1])+1]
        complete.append(row.candle_start == expected)
    old = old_native.loc[complete].sort_values(['timeframe','date']).reset_index(drop=True)
    keys = old[['timeframe','date']]
    matched = keys.merge(native,on=['timeframe','date'],how='left',validate='one_to_one').loc[:,list(old)]
    matched['ad_line'] -= offset
    assert_exact_frame(old, matched)
    return dict(daily_rows=len(old_daily), complete_native_rows=len(old), partial_v1_native_rows=int((~np.asarray(complete)).sum()),
                v1_ad_line_offset=offset, original_values='Every V1 daily field and complete native field reconstructed exactly; original immutable V1 files remain referenced.',
                line_origin='V2 cumulative A/D starts at the frozen calendar origin. V1 starts at 2020-01-02. Subtract the retained pre2020 net total to reconstruct every V1 post2020 line value.')


def run(root, request):
    import exchange_calendars as xcals
    root.mkdir(parents=True,exist_ok=True)
    source = checked_download(request['stock_release'],'ACCEPTED_PRICE_STITCH.json',request['stock_status_sha256'],root/'source')
    stock = json.loads(source.read_text(encoding='utf-8'))
    planned = [t for p in stock['parts'] for t in p['tickers']]
    if (stock['status'] != 'ACCEPTED_PRICE_BASE_WITH_LOGGED_EXCLUSIONS_NOT_WORLD'
            or stock['accepted_tickers'] != 8316 or stock['original_universe'] != 8727
            or stock['excluded_tickers'] != 411 or len(stock['records']) != 8316
            or stock['inputs_tag'] != request['calendar_release']
            or stock['stock_days_sha256'] != request['weights_sha256']
            or len(planned) != 8316 or len(set(planned)) != 8316
            or set(planned) != {r['ticker'] for r in stock['records']}):
        raise ValueError('approved breadth input universe differs')
    frozen = checked_download(request['calendar_release'],'market_sessions.parquet',request['calendar_sha256'],root/'calendar')
    frozen_dates = checked_sessions(pd.read_parquet(frozen).date)
    as_of = max(pd.Timestamp(r['last_query']) for r in stock['records'])
    cutoffs = [pd.Timestamp(value) for value in request['cutoffs']]
    if (len(cutoffs) != 2 or len(set(cutoffs)) != 2
            or any(t.tz is not None or not WINDOW_START < t <= as_of for t in cutoffs)
            or [str(t.date()) for t in cutoffs] != request['cutoffs']):
        raise ValueError('two canonical in-window raw cutoff dates required')
    exchange = xcals.get_calendar('XNYS', start='1990-01-01', end=str((as_of+pd.Timedelta(days=45)).date()))
    calendar = checked_sessions(exchange.sessions_in_range('1990-01-02',str((as_of+pd.Timedelta(days=45)).date())).tz_localize(None))
    if (frozen_dates[0] != pd.Timestamp('1990-01-02')
            or not np.array_equal(calendar[:len(frozen_dates)].asi8,frozen_dates.asi8)):
        raise ValueError('NYSE calendar changed from the approved frozen prefix')
    labels = ['full',*request['cutoffs']]
    stores = {label:{c:np.zeros(len(calendar),dtype='float64' if c.endswith('volume') else 'int64') for c in COUNT_COLUMNS} for label in labels}
    used = []
    for number, part in enumerate(stock['parts']):
        archive = checked_download(part['release'],part['part']+'.tar',part['archive_sha256'],root/'source')
        with tarfile.open(archive) as bundle:
            for ticker in part['tickers']:
                member = bundle.getmember(ticker.encode().hex()+'.bars.parquet')
                if not member.isfile():
                    raise ValueError('breadth price member is not a regular file')
                bars = pd.read_parquet(io.BytesIO(bundle.extractfile(member).read()))
                for label in labels:
                    own = bars if label == 'full' else bars.loc[pd.to_datetime(bars.date) < pd.Timestamp(label)]
                    votes = stock_contributions(own)
                    positions = calendar.get_indexer(pd.DatetimeIndex(votes.date).as_unit('ns'))
                    valid = positions >= 0
                    for column in COUNT_COLUMNS:
                        np.add.at(stores[label][column],positions[valid],votes[column].to_numpy()[valid])
                used.append(ticker)
        archive.unlink()
        print('BREADTH_RAW_PREFIX_PART',number,'NAMES',len(used),flush=True)
    if set(used) != set(planned) or len(used) != 8316:
        raise ValueError('breadth source stock membership incomplete')
    votes = {label:pd.DataFrame({'date':calendar,**values}) for label,values in stores.items()}
    daily = aggregate(votes.pop('full'),calendar,as_of,retain_history=True)
    native = breadth_candles(daily,calendar)
    check_grid(native,calendar)
    checks = prefix_checks(daily,native,votes,calendar)
    old_daily_file = checked_download(request['legacy_release'],'outside_breadth_daily.parquet',request['legacy_daily_sha256'],root/'legacy')
    old_native_file = checked_download(request['legacy_release'],'outside_breadth_candles.parquet',request['legacy_native_sha256'],root/'legacy')
    overlap = legacy_overlap(daily,native,calendar,pd.read_parquet(old_daily_file),pd.read_parquet(old_native_file))
    weights_file = checked_download(request['stock_release'],'ACCEPTED_PRICE_STOCK_DAYS.csv',request['weights_sha256'],root/'weights')
    weights = pd.read_csv(weights_file);dates,multipliers = checked_weights(weights)
    if int(multipliers.sum()) != 12364370 or not dates.isin(calendar).all():
        raise ValueError('breadth stock-day weights differ')
    tag = f"outside-breadth-native-v2-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    outputs = []
    for frame,name in ((daily,'breadth_daily_full_history_v2.parquet'),(native,'breadth_native_full_history_v2.parquet')):
        file=root/name;write_lossless(frame,file);outputs.append(file)
    bindings=[];coverage=[]
    universe='SURVIVORS_ONLY_APPROVED_STITCH_V2; every accepted name with a source bar votes; historical tradeability/size not established'
    for tf in TIMEFRAMES:
        frame=native_factor(native.loc[native.timeframe == tf].reset_index(drop=True))
        file=root/f'breadth_{tf}.parquet'
        table=exact_arrow_table(frame)
        for index,column in enumerate(table.column_names):
            if column not in KEYS:
                field=table.schema.field(index).with_metadata({b'universe_label':universe.encode(),b'availability_rule':b'source_candle_end < available_from <= stock D'})
                table=table.set_column(index,field,table.column(index))
        pq.write_table(table,file,compression='zstd',compression_level=19)
        assert_exact_frame(frame,pd.read_parquet(file));outputs.append(file)
        columns=validate_factor(frame)
        bindings.append(dict(family='breadth',timeframe=tf,release=tag,asset=file.name,sha256=sha(file),native_rows=len(frame),
                             columns=columns,numeric_dtypes={c:str(frame[c].dtype) for c in columns},
                             source_rule='Every native session present; source candle end < next-session availability <= query D; full1990-prefix history retained.'))
        coverage.extend(dict(row,universe_label=universe) for row in weighted_coverage(frame,weights,tf,'breadth'))
    coverage_file=root/'BREADTH_STOCK_DAY_COVERAGE_V2.csv';pd.DataFrame(coverage).to_csv(coverage_file,index=False);outputs.append(coverage_file)
    store=dict(format='FACTORED_NATIVE_WORLD_CONTEXT_V1',source_commit=os.environ['GITHUB_SHA'],stock_release=request['stock_release'],
               stock_status_sha256=request['stock_status_sha256'],stock_day_weight_sha256=request['weights_sha256'],calendar_sha256=request['calendar_sha256'],
               query_stock_days=int(multipliers.sum()),factors=bindings,reader='world_context_store.context_row_view',
               world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    manifest=root/'BREADTH_FACTOR_STORE_V2.json';manifest.write_text(json.dumps(store,indent=2)+'\n',encoding='utf-8');outputs.append(manifest)
    report=dict(status='FULL_HISTORY_BREADTH_MEASURED_COMPONENT_NOT_WORLD',source_commit=os.environ['GITHUB_SHA'],request=request,
                accepted_names=len(used),new_exclusions=[],as_of=str(as_of.date()),daily_rows=len(daily),native_rows=len(native),
                pre2020_daily_rows=int((daily.date < WINDOW_START).sum()),timeframes=list(TIMEFRAMES),partial_native_buckets=0,
                raw_prefix_checks=checks,legacy_overlap=overlap,native_factor_bytes=sum((root/r['asset']).stat().st_size for r in bindings),
                data_asset_bytes=sum(f.stat().st_size for f in outputs if f.suffix=='.parquet'),coverage_rows=len(coverage),
                minimum_non_null_stock_day_pct=min(r['non_null_pct'] for r in coverage),factor_manifest_sha256=sha(manifest),
                legacy_assets_retained=[dict(release=request['legacy_release'],asset=old_daily_file.name,sha256=sha(old_daily_file)),dict(release=request['legacy_release'],asset=old_native_file.name,sha256=sha(old_native_file))],
                runtime={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','exchange_calendars')},
                universe_label='Approved stitch-v2 names; survivors-only; no historical tradeability/size or stock-only-universe approval.',
                storage_scope='Actual breadth outputs only; raw approved archives and frozen calendar/code remain dependencies, not counted as a full-world cap proof.',
                world_gate='NOT_PROVEN',full_world_storage_gate='NOT_PROVEN',scoring_gate='CLOSED')
    report_file=root/'BREADTH_NATIVE_HISTORY_MEASURED_V2.json';report_file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');outputs.append(report_file)
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','Immutable full-history breadth and22 complete native grids; every source name and raw cutoff retained; not full-world approval.')
    publish_assets(tag,*outputs)
    gh_retry('release','edit',tag,'--draft=false')
    inventory=release_info(tag)
    readback=root/'published-readback'
    for binding in bindings:
        checked_download(tag,binding['asset'],binding['sha256'],readback/tag)
    audited=audit(store,readback,{tag:inventory},report['native_factor_bytes'])
    readback_file=root/'BREADTH_PUBLISHED_FACTOR_READBACK_V2.json'
    readback_file.write_text(json.dumps(audited,indent=2)+'\n',encoding='utf-8')
    publish_assets(tag,readback_file)
    if audited['failures']:
        raise ValueError('published breadth factor readback failed; immutable failure evidence retained')
    print('BREADTH_NATIVE_HISTORY_COMPLETE',tag,len(used),len(daily),len(native),len(checks),report['native_factor_bytes'],flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    run(args.directory,json.loads(Path('ci/BREADTH_NATIVE_HISTORY_REQUEST.json').read_text(encoding='utf-8')))
