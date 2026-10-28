"""Build the inherited Tier1 ETF panel from authenticated published sources only."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from ci.release_assets import download_asset,gh_retry,publish_assets
from light_box_market import build_panel,build_candles,write_panel,write_candles
from market_storage import assert_exact_frame
from market_storage import exact_int64
from outside_market import NAMED_ETFS,INDUSTRY_ETFS,attach_available_from
from world_timeframes import TIMEFRAMES


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_download(tag,name,expected,root):
    file=download_asset(tag,name,root)
    if sha(file)!=expected:raise ValueError('released source fingerprint differs: '+name)
    return file


def overlap_proof(panel,native_manifest,request,root,canonical=None):
    """Measure both captures; optionally restore native values into a copy."""
    checks=[]
    if {r['ticker'] for r in native_manifest['records']}!=set(NAMED_ETFS):raise ValueError('native ETF universe differs')
    for row in native_manifest['records']:
        file=checked_download(request['native_release'],row['file'],row['sha256'],root/'native')
        prior=pd.read_parquet(file);prior['date']=pd.to_datetime(prior.date).astype('datetime64[ns]')
        current=panel[panel.ticker==row['ticker']]
        joined=prior.merge(current,on='date',suffixes=('_native','_panel'),validate='one_to_one')
        if len(joined)!=len(current[current.date<=prior.date.max()]):raise ValueError('native overlap dates incomplete')
        fields={};canonical_fields={}
        for column in ('open','high','low','close','volume'):
            left=joined[column+'_native'].to_numpy(dtype=np.float64);right=joined[column+'_panel'].to_numpy(dtype=np.float64)
            bad=left.view(np.uint64)!=right.view(np.uint64)
            fields[column]=dict(compared=len(left),bit_mismatches=int(bad.sum()),max_abs=float(np.max(np.abs(left-right))) if len(left) else None,
                differences=[dict(date=str(pd.Timestamp(joined.date.iloc[i]).date()),native=float(left[i]),light=float(right[i])) for i in np.flatnonzero(bad)])
            if canonical is not None:
                mask=(canonical.ticker==row['ticker'])&canonical.date.isin(joined.date)
                values=joined.set_index('date').reindex(canonical.loc[mask,'date'])[column+'_native'].to_numpy()
                if canonical[column].dtype.kind in 'iu':
                    values=exact_int64(values)
                    if values is None:raise ValueError('native source cannot fit canonical integer field without loss')
                canonical.loc[mask,column]=values
                restored=canonical.loc[mask,column].to_numpy(dtype=np.float64)
                expected=joined.set_index('date').reindex(canonical.loc[mask,'date'])[column+'_native'].to_numpy(dtype=np.float64)
                canonical_fields[column]=dict(compared=len(expected),bit_mismatches=int((restored.view(np.uint64)!=expected.view(np.uint64)).sum()))
        checks.append(dict(ticker=row['ticker'],native_file_sha256=sha(file),rows=len(joined),fields=fields,canonical_fields=canonical_fields))
    return checks


def prefix_checks(panel,calendar,full,cuts):
    checks=[]
    keys=['ticker','timeframe','date']
    for value in cuts:
        cut=pd.Timestamp(value)
        earlier=panel[panel.date<cut]
        actual=build_candles(earlier,calendar,cut-pd.Timedelta(days=1))
        actual=actual[actual.available_from<=cut].sort_values(keys).reset_index(drop=True)
        expected=full[full.available_from<=cut].sort_values(keys).reset_index(drop=True)
        assert_exact_frame(expected,actual)
        checks.append(dict(cut=value,native_rows=len(actual),columns=list(actual),timeframes=sorted(actual.timeframe.unique()),mismatches=0))
    return checks


def run(root,request):
    import exchange_calendars as xcals
    root.mkdir(parents=True,exist_ok=True);source=root/'source'
    manifest_file=checked_download(request['release'],'manifest.json',request['manifest_sha256'],source)
    manifest=json.loads(manifest_file.read_text());selected=[r for r in manifest['symbols'] if not r['symbol'].startswith('^')]
    expected=set(NAMED_ETFS)|{s for s,_ in INDUSTRY_ETFS}
    if len(selected)!=len(expected) or {r['symbol'] for r in selected}!=expected:raise ValueError('complete inherited 43 ETF universe required')
    for row in selected:checked_download(request['release'],row['file'],row['sha256'],source)
    panel,_,_=build_panel(source)
    frozen_file=checked_download(request['inputs_release'],'market_sessions.parquet',request['calendar_sha256'],root/'bound')
    frozen=pd.DatetimeIndex(pd.read_parquet(frozen_file).date).as_unit('ns')
    cutoff=pd.Timestamp(panel.date.max())
    exchange=xcals.get_calendar('XNYS',start=str(frozen[0].date()),end=str((cutoff+pd.Timedelta(days=45)).date()))
    calendar=pd.DatetimeIndex(exchange.sessions_in_range(str(frozen[0].date()),str((cutoff+pd.Timedelta(days=40)).date()))).tz_localize(None).as_unit('ns')
    if not frozen.equals(calendar[:len(frozen)]):raise ValueError('current session calendar does not preserve the frozen bucket anchor/prefix')
    panel=attach_available_from(panel,calendar)
    if panel.available_from.isna().any() or (panel.available_from<=panel.date).any():raise ValueError('next-session availability missing')
    native_file=checked_download(request['native_release'],'ETF_DAILY_SOURCE_MANIFEST.json',request['native_manifest_sha256'],root/'bound')
    canonical=panel.copy()
    for column in ('open','high','low','close','volume'):canonical['vendor_'+column]=panel[column].copy()
    overlap=overlap_proof(panel,json.loads(native_file.read_text()),request,root,canonical=canonical)
    mismatches=sum(m['bit_mismatches'] for row in overlap for m in row['fields'].values())
    canonical_mismatches=sum(m['bit_mismatches'] for row in overlap for m in row['canonical_fields'].values())
    daily_file=root/'outside_market_daily_v3.parquet';daily=write_panel(canonical,daily_file)
    candles=build_candles(canonical,calendar,cutoff)
    candle_file=root/'outside_market_candles_v3.parquet';native=write_candles(candles,candle_file)
    checks=prefix_checks(canonical,calendar,candles,request['cuts'])
    coverage=[]
    window=calendar[(calendar>=pd.Timestamp(manifest['window_start']))&(calendar<=cutoff)]
    for ticker,group in panel.groupby('ticker'):
        own=window[window>=group.date.min()];missing=own.difference(pd.DatetimeIndex(group.date))
        coverage.append(dict(ticker=ticker,rows=len(group),first=str(group.date.min().date()),last=str(group.date.max().date()),
            post_listing_expected=len(own),post_listing_missing=[str(d.date()) for d in missing],
            full_window_percent=100*len(group)/len(window),pre_listing='UNAVAILABLE_NEVER_ZERO'))
    complete=not canonical_mismatches and all(not c['post_listing_missing'] for c in coverage)
    report=dict(status='RELEASED_ETF_PANEL_MEASURED_NOT_FULL_WORLD' if complete else 'ETF_PANEL_SOURCE_OVERLAP_OR_COVERAGE_FAILED',
        producer=os.environ['GITHUB_SHA'],request=request,daily=daily,native_candles=native,coverage=coverage,
        overlap=overlap,overlap_bit_mismatches=mismatches,canonical_overlap_bit_mismatches=canonical_mismatches,prefix_checks=checks,raw_rows=len(panel),native_rows=len(candles),
        source_manifest_sha256=sha(manifest_file),frozen_calendar_sha256=sha(frozen_file),calendar_anchor=str(calendar[0].date()),
        extended_calendar_sha256=hashlib.sha256(calendar.to_numpy(dtype='datetime64[ns]').tobytes()).hexdigest(),
        first_available=str(panel.available_from.min().date()),last_available=str(panel.available_from.max().date()),
        environment={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','exchange_calendars')},
        semantics='Canonical OHLCV preserves frozen native history wherever present; light-daily capture retained exactly in vendor_* plus adj_close. Only absent/later sessions and the 18 industry series use light-daily canonical values. No source is overwritten, no level linking or tolerance rounding, no historical membership inferred.',
        historical_volume_vintage_gate='NOT_PROVEN; capture differences are retained explicitly and do not establish first-publication history',
        monthly_availability='Local ETF panel: next real session; shared world_timeframes.py and live pinned grid unchanged',
        provider_requests=0,world_gate='NOT_PROVEN',scoring_gate='CLOSED',protected_world_run_untouched=40621517496,
        remaining=['stock-day factor integration and warmup coverage','historical sector/industry membership and all comparison families',
                   'full existing question quality, comprehensive leak and dependency-budget gates'])
    file=root/'OUTSIDE_MARKET_RELEASED_MEASURED_V3.json';file.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    tag=f"outside-market-released-v3-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,daily_file,candle_file,file);gh_retry('release','edit',tag,'--draft=false')
    print('RELEASED_MARKET_PANEL',len(panel),len(candles),'CAPTURE_DIFFERENCES',mismatches,'CANONICAL_BIT_MISMATCHES',canonical_mismatches,flush=True)
    if not complete:raise RuntimeError('ETF source overlap or coverage failed; evidence retained, no acceptance')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    run(args.directory,json.loads(Path('ci/OUTSIDE_MARKET_RELEASED_REQUEST.json').read_text()))
