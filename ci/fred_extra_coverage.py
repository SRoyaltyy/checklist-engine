"""Inspect released native ALFRED levels; emit explicit extra-series coverage."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

from world_context_native import KEYS
from world_context_store import checked_weights,weighted_coverage
from world_timeframes import TIMEFRAMES

SERIES=('T10Y3M','T5YIE','T10YIE','STICKCPIM159S','DFII10','CIVPART','INDPRO','BUSLOANS')
TAG='shared-context-v2-40636949344-1'
STATUS_SHA='4e13e4c9d3380b23d217156c83e7d2ee472dafd226b1626e128c06d9c65da643'
WEIGHTS_SHA='6961605c52041be1c437b425bc8c6251e65ee6c63270d185ea507605fe597114'
RECORDED_COVERAGE_SHA='286f071d25ef233aeeb1a08aad67cc536c2d812e4573eb3e2327e195377ce5d0'


def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()


def master_row(record,requested,official,binding):
    if record['native_column']!='fred_'+requested.lower():raise ValueError('FRED requested column differs')
    known=record['non_null_stock_days']>0
    return dict(namespace='fred_1635_native',item_id=requested,item=requested,timeframe=record['timeframe'],block='I',
                snapshot_columns=record['column'],non_null_pct_2020_2026=f"{record['non_null_pct']:.4f}",
                first_date_available=record['first_date'],status='MEASURED' if known else 'NO_OBSERVED_VALUES',
                reason=('Last-known ALFRED vintage level at native boundary; monthly facts are sampled, never interpolated. Full world/PIT stock eligibility remains separate.'
                        if known else 'No observed released level on the approved stock-day denominator; missing stays explicit.'),
                source_evidence=json.dumps(dict(run=40636949344,release=TAG,asset=binding['file'],sha256=binding['sha256'],
                                               requested_series=requested,source_series=official,source_archive='phase1-gap-fred-v2-40307954973-1/fred_gap_source.tar.gz',
                                               reader='world_context_store.context_row_view',vintage_rule='vintage_date < D',
                                               readback='FRED_1635_COVERAGE_READBACK_V1.json'),separators=(',',':')),
                column_measurements=json.dumps({record['column']:dict(query_stock_days=record['query_stock_days'],non_null_stock_days=record['non_null_stock_days'],
                                                                     query_market_sessions=record['query_market_sessions'],first_date=record['first_date'],last_date=record['last_date'])},separators=(',',':')),
                universe_scope='Shared ALFRED macro level measured on approved8316-name survivors-only stock-day weights; historical eligibility not established')


def measure(directory,weights_file,recorded_file,series_metadata):
    status_file=directory/'SHARED_CONTEXT_STATUS.json'
    if digest(status_file)!=STATUS_SHA or digest(weights_file)!=WEIGHTS_SHA or digest(recorded_file)!=RECORDED_COVERAGE_SHA:
        raise ValueError('FRED coverage source/status/denominator pin differs')
    status=json.loads(status_file.read_text(encoding='utf-8'))
    if status['source_commit']!='3c34201a5df8f009aef593b357fe9b6348e5d018' or len(status['prefix_checks'])!=44 or any(r['mismatches'] for r in status['prefix_checks']):
        raise ValueError('FRED shared producer/cutoff proof differs')
    parts={p['timeframe']:p for p in status['parts']}
    if len(parts)!=22 or set(parts)!=set(TIMEFRAMES) or set(series_metadata)!=set(SERIES):raise ValueError('FRED required series/timeframes differ')
    weights=pd.read_csv(weights_file);dates,multipliers=checked_weights(weights)
    if int(multipliers.sum())!=12364370 or len(dates)!=1712:raise ValueError('FRED stock-day denominator differs')
    recorded=pd.read_csv(recorded_file).set_index(['timeframe','native_column'])
    fields=['fred_'+sid.lower() for sid in SERIES];rows=[];master=[];assets=[]
    for tf in TIMEFRAMES:
        part=parts[tf];file=directory/part['file']
        if digest(file)!=part['sha256']:raise ValueError('FRED native bytes differ')
        native=pd.read_parquet(file,columns=[*KEYS,*fields])
        fresh=weighted_coverage(native,weights,tf,'fred_1635_native')
        if len(fresh)!=8:raise ValueError('FRED series silently missing from measured native factor')
        for row in fresh:
            old=recorded.loc[(tf,row['native_column'])]
            for key in ('query_stock_days','non_null_stock_days','non_null_pct','first_date','last_date','non_null_market_sessions'):
                if old[key]!=row[key]:raise ValueError('FRED measured stock-day coverage changed: '+row['column'])
            sid=row['native_column'].removeprefix('fred_').upper();meta=series_metadata[sid]
            if meta['requested_series']!=sid or meta['status']!='PASS':raise ValueError('FRED source identifier differs')
            rows.append(dict(row,requested_series=sid,source_series=meta['source_series']))
            master.append(master_row(row,sid,meta['source_series'],part))
        assets.append(dict(asset=file.name,sha256=digest(file),bytes=file.stat().st_size,native_rows=len(native)))
    if len(rows)!=176:raise ValueError('FRED full8x22 measurement incomplete')
    return rows,master,dict(status='PASS_EIGHT_FRED_NATIVE_LEVEL_COVERAGE_ONLY' if all(r['non_null_stock_days']>0 for r in rows) else 'INCOMPLETE_FRED_LEVEL_COVERAGE',
                           run=40636949344,source_commit=status['source_commit'],release=TAG,status_sha256=STATUS_SHA,
                           weight_sha256=WEIGHTS_SHA,recorded_coverage_sha256=RECORDED_COVERAGE_SHA,series=list(SERIES),timeframes=list(TIMEFRAMES),
                           measurements=len(rows),query_stock_days=12364370,query_market_sessions=1712,
                           minimum_non_null_stock_day_pct=min(r['non_null_pct'] for r in rows),native_assets=assets,
                           source_aliases={sid:series_metadata[sid]['source_series'] for sid in SERIES},
                           cutoff_checks=44,missing_policy='Missing/zero coverage remains explicit, never WIRED or filled with false/no.',
                           frequency_rule='Last-known published vintage at each native boundary; monthly source facts are not interpolated.',
                           full_world_gate='NOT_PROVEN',full_dependency_budget_gate='NOT_PROVEN',scoring_gate='CLOSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--weights',type=Path,required=True);parser.add_argument('--recorded-coverage',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    metadata=json.loads(Path('dictionary/FRED_1635_SERIES.json').read_text(encoding='utf-8'))['series']
    rows,master,report=measure(args.directory,args.weights,args.recorded_coverage,metadata)
    args.output.mkdir(parents=True,exist_ok=True)
    for values,name in ((rows,'FRED_1635_STOCK_DAY_COVERAGE_V1.csv'),(master,'FRED_1635_WORLD_COVERAGE_ROWS_V1.csv')):
        with (args.output/name).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    (args.output/'FRED_1635_COVERAGE_READBACK_V1.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('EIGHT_FRED_COVERAGE_MEASURED',len(rows),report['minimum_non_null_stock_day_pct'],report['status'])
