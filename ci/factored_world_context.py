"""Attach released numeric factors to every approved stock-day by exact weights."""
import argparse
import csv
import json
import os
from pathlib import Path
import pandas as pd
from ci.native_price_blocks import sha,write_json
from ci.release_assets import download_asset,gh_retry,publish_assets,asset_index
from world_context_native import KEYS
from world_context_store import checked_weights,validate_factor,weighted_coverage
from world_timeframes import TIMEFRAMES

REQUEST=Path('ci/FACTORED_CONTEXT_REQUEST.json')


def build(root,request,shared_release):
    root.mkdir(parents=True,exist_ok=True)
    file=download_asset(request['stock_release'],'ACCEPTED_PRICE_STITCH.json',root/'stocks')
    if sha(file)!=request['stock_status_sha256']:raise ValueError('approved stock stitch differs')
    stocks=json.loads(file.read_text())
    if (stocks['original_universe']!=8727 or stocks['accepted_tickers']!=8316
        or stocks['accepted_percent']<95):raise ValueError('context stock denominator differs')
    file=download_asset(stocks['inputs_tag'],'BUILD_INPUTS.json',root/'stocks')
    if sha(file)!=stocks['inputs_sha256']:raise ValueError('stock calendar input manifest differs')
    inputs=json.loads(file.read_text())
    if inputs['calendar_sha256']!=request['calendar_sha256']:raise ValueError('stock calendar registration differs')
    file=download_asset(stocks['inputs_tag'],'market_sessions.parquet',root/'stocks')
    if sha(file)!=request['calendar_sha256']:raise ValueError('stock calendar bytes differ')
    calendar=pd.DatetimeIndex(pd.read_parquet(file).date).as_unit('ns')
    file=download_asset(request['stock_release'],'ACCEPTED_PRICE_STOCK_DAYS.csv',root/'stocks')
    if sha(file)!=stocks['stock_days_sha256']:raise ValueError('approved stock-day weights differ')
    weights=pd.read_csv(file);dates,numbers=checked_weights(weights)
    if int(numbers.sum())!=stocks['query_rows']:raise ValueError('context stock-day total differs')
    if not dates.isin(calendar).all():raise ValueError('stock-day weights outside approved calendar')
    definitions=[('macro_cboe',shared_release,'SHARED_CONTEXT_STATUS.json'),
                 ('etf',request['etf_release'],'ETF_CONTEXT_STATUS.json')]
    bindings=[];coverage=[];factor_bytes=0
    for family,tag,name in definitions:
        report_file=download_asset(tag,name,root/family)
        if family=='etf' and sha(report_file)!=request['etf_status_sha256']:raise ValueError('ETF source status differs')
        report=json.loads(report_file.read_text())
        if report['calendar_sha256']!=request['calendar_sha256']:raise ValueError('shared/stock native calendars differ')
        if set(report['timeframes'])!=set(TIMEFRAMES):raise ValueError('context native timeframe grid incomplete')
        if family=='macro_cboe' and (report.get('format_version')!=2 or report.get('numeric_precision')!='float64; no unproven precision reduction'):
            raise ValueError('macro context must retain verified float64 precision in version 2')
        if family=='macro_cboe' and any(report['code_sha256'].get(name)!=sha(name) for name in
            ('world_context_native.py','world_fred.py','ci/shared_context_build.py')):
            raise ValueError('macro context code provenance differs from versioned builder')
        if family=='etf' and (not report['source_complete'] or len(report['available_symbols'])!=25):
            raise ValueError('required ETF sources incomplete')
        parts={part['timeframe']:part for part in report['parts']}
        if len(parts)!=len(report['parts']) or set(parts)!=set(TIMEFRAMES):raise ValueError('context factor file grid differs')
        inventory=asset_index(tag)
        for tf in TIMEFRAMES:
            part=parts[tf];file=download_asset(tag,part['file'],root/family)
            if sha(file)!=part['sha256']:raise ValueError('native context factor bytes differ')
            frame=pd.read_parquet(file);columns=validate_factor(frame)
            if len(frame)!=part['native_rows'] or len(columns)!=part['feature_columns']:
                raise ValueError('native context factor dimensions differ')
            if family=='macro_cboe' and any(str(frame[c].dtype)!='float64' for c in columns):
                raise ValueError('macro factor unexpectedly reduces numeric precision')
            rows=weighted_coverage(frame,weights,tf,family)
            coverage.extend(rows)
            factor_bytes+=inventory[part['file']]['size']
            bindings.append(dict(family=family,timeframe=tf,release=tag,asset=part['file'],sha256=part['sha256'],
                source_status_asset=name,source_status_sha256=sha(report_file),columns=columns,
                numeric_dtypes={c:str(frame[c].dtype) for c in columns},native_rows=len(frame),
                source_rule='source_candle_end < available_from <= stock query D; ALFRED vintage_date < sample availability',
                all_source_columns_preserved=True))
    names=[(row['timeframe'],row['column']) for row in coverage]
    if len(names)!=len(set(names)):raise ValueError('duplicate factor columns across families')
    file=root/'WORLD_SHARED_STOCK_DAY_COVERAGE.csv'
    with file.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(coverage[0]));writer.writeheader();writer.writerows(coverage)
    coverage_file=file
    store=dict(format='FACTORED_NATIVE_WORLD_CONTEXT_V1',stock_release=request['stock_release'],
        stock_status_sha256=request['stock_status_sha256'],stock_day_weight_asset='ACCEPTED_PRICE_STOCK_DAYS.csv',
        stock_day_weight_sha256=stocks['stock_days_sha256'],calendar_sha256=request['calendar_sha256'],
        calendar_release=stocks['inputs_tag'],calendar_asset='market_sessions.parquet',
        original_universe=8727,accepted_stocks=8316,excluded_stocks=411,query_stock_days=stocks['query_rows'],
        source_commit=os.environ['GITHUB_SHA'],factors=bindings,
        first_query_date=str(dates.min().date()),last_query_date=str(dates.max().date()),
        reader='world_context_store.context_row_view',reader_sha256=sha('world_context_store.py'),
        row_validation='caller supplies dates from authenticated accepted stock price members; this component does not create new stock sessions',
        layout='stored native numeric values once, exact date/availability joins; no indicator recomputation, field pruning or precision reduction',
        remaining=['stock-relative features and historical sector/industry membership','peer comparisons','other event/fundamental blocks (news dropped by Cyrus 2026-10-28)',
                   'complete v3 questions and full leak verification','historical tradeability/size eligibility','complete numeric-value retention and total world budget'],
        world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    file=root/'FACTORED_WORLD_CONTEXT_STORE.json';write_json(file,store)
    status=dict(status='STORED_NATIVE_CONTEXTS_ATTACHED_TO_APPROVED_STOCK_DAY_DENOMINATOR_NOT_FULL_WORLD',
        source_commit=os.environ['GITHUB_SHA'],accepted_stocks=8316,original_universe=8727,query_stock_days=stocks['query_rows'],
        context_column_timeframe_rows=len(coverage),native_factor_bytes=factor_bytes,
        manifest_sha256=sha(file),coverage_sha256=sha(coverage_file),stock_day_weights_sha256=stocks['stock_days_sha256'],
        zero_observation_rows=sum(row['non_null_stock_days']==0 for row in coverage),
        stock_day_attachment='all approved stock days measured exactly by date multiplicities',
        full_world_gate='NOT_PROVEN; declared remaining blocks/quality/PIT/retention gates remain',scoring_gate='CLOSED')
    status_file=root/'FACTORED_WORLD_CONTEXT_STATUS.json';write_json(status_file,status)
    tag=f"factored-world-context-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
        '--notes','Full approved stock-day macro/CBOE/ETF factor attachment and measured coverage. Remaining complete-world gates are explicit.')
    publish_assets(tag,file,coverage_file,status_file);gh_retry('release','edit',tag,'--draft=false')
    print('FACTORED_WORLD_CONTEXT_COMPLETE',tag,len(coverage),stocks['query_rows'],factor_bytes,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--shared-release',required=True)
    args=parser.parse_args();build(Path(args.directory),json.loads(REQUEST.read_text()),args.shared_release)
