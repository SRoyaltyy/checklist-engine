"""Independently inspect public released ETF bytes; no vendor requests."""
import argparse
import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = {'SPY','QQQ','IWM','XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY'}
INPUTS_SHA = 'a57aee6ae2dd3b2f444d2433bac8242f44b9346a5aea826f0250c96ed376ccf4'


def raw_asset(tag, name, limit=32000000):
    if Path(name).name != name or not re.fullmatch(r'[A-Za-z0-9_.-]+',tag):
        raise ValueError('unsafe release asset path')
    url='https://github.com/SRoyaltyy/checklist-engine/releases/download/'+tag+'/'+urllib.parse.quote(name,safe='')
    with urllib.request.urlopen(url,timeout=90) as response:
        raw=response.read(limit+1)
    if len(raw)>limit:raise ValueError('ETF proof asset exceeds bound')
    return raw


def digest(raw):return hashlib.sha256(raw).hexdigest()


def verify(tag, head):
    raw=raw_asset(tag,'ETF_CONTEXT_STATUS.json');status=json.loads(raw);status_sha=digest(raw)
    if status['source_commit']!=head or status['source_complete'] is not True or status['missing_symbols']:
        raise ValueError('ETF source identity/completion differs')
    inputs_raw=raw_asset(status['request']['inputs_tag'],'BUILD_INPUTS.json')
    if digest(inputs_raw)!=INPUTS_SHA:raise ValueError('frozen input manifest differs')
    inputs=json.loads(inputs_raw)
    calendar_raw=raw_asset(status['request']['inputs_tag'],'market_sessions.parquet')
    if digest(calendar_raw)!=inputs['calendar_sha256']:raise ValueError('calendar differs')
    calendar=pd.DatetimeIndex(pd.read_parquet(io.BytesIO(calendar_raw)).date)
    raw=raw_asset(tag,'ETF_DAILY_SOURCE_MANIFEST.json')
    if digest(raw)!=status['daily_manifest_sha256']:raise ValueError('ETF daily manifest differs')
    manifest=json.loads(raw)
    if manifest['records']!=status['daily_sources']:raise ValueError('ETF daily status/manifest differs')
    names=[r['ticker'] for r in manifest['records']]
    if len(names)!=len(set(names)) or set(names)!=set(status['request']['symbols']) or not REQUIRED<=set(names):
        raise ValueError('ETF source requested/required symbol set differs')
    query=calendar[calendar>=pd.Timestamp('2020-01-01')]
    results=[]
    for record in manifest['records']:
        raw=raw_asset(tag,record['file'])
        if digest(raw)!=record['sha256']:raise ValueError('ETF daily bytes differ')
        frame=pd.read_parquet(io.BytesIO(raw))
        fields=['ticker','date','open','high','low','close','volume']
        if list(frame)!=fields or len(frame)!=record['rows'] or set(frame.ticker)!={record['ticker']}:
            raise ValueError('ETF daily schema/identity/count differs')
        dates=pd.DatetimeIndex(frame.date)
        if dates.has_duplicates or not dates.is_monotonic_increasing or not dates.isin(calendar).all():
            raise ValueError('ETF daily calendar differs')
        if str(dates.min().date())!=record['first'] or str(dates.max().date())!=record['last'] or record['last']!=inputs['as_of_completed_session']:
            raise ValueError('ETF daily source cutoff differs')
        values=frame[fields[2:]].to_numpy(float)
        if not np.isfinite(values).all() or (values[:,:4]<=0).any() or (values[:,4]<0).any():
            raise ValueError('ETF daily price/volume values invalid')
        tolerance=np.abs(frame.close)*1e-8+1e-12
        if ((frame.high+ tolerance < frame[['open','close']].max(axis=1)) |
            (frame.low-tolerance > frame[['open','close']].min(axis=1))).any():
            raise ValueError('ETF OHLC ordering differs')
        gaps=calendar[(calendar>=dates.min())&(calendar<=dates.max())].difference(dates)
        if [str(d.date()) for d in gaps]!=record['missing_sessions_after_first_source_date']:
            raise ValueError('ETF source missing-session manifest differs')
        missing_query=[str(d.date()) for d in query.difference(dates)]
        if record['ticker'] in REQUIRED and missing_query:
            raise ValueError('required ETF misses a 2020-through-cutoff session')
        results.append(dict(record,remote_bytes_verified=True,missing_query_sessions=missing_query))
    original=status['original_source_reference']
    raw=raw_asset(original['release'],original['asset'])
    if digest(raw)!=original['sha256']:raise ValueError('original ETF source differs')
    legacy=pd.read_parquet(io.BytesIO(raw))
    if not REQUIRED<=set(legacy.ticker):raise ValueError('original required ETFs absent')
    return dict(status='ALL_REQUESTED_ETF_DAILY_SOURCE_BYTES_VERIFIED_NOT_WORLD',release=tag,source_head=head,
                status_sha256=status_sha,daily_manifest_sha256=status['daily_manifest_sha256'],
                inputs_sha256=INPUTS_SHA,calendar_sha256=inputs['calendar_sha256'],
                stock_cutoff=inputs['as_of_completed_session'],required_symbols=sorted(REQUIRED),
                requested_symbols=sorted(names),original_source_reference=original,records=results,
                org_source_review='docs/EXISTING_SOURCE_AUDIT_v2.md and org-context-sources-v1-40478973715-1',
                stock_day_join_gate='NOT_RUN',full_indicator_grid_gate='NOT_RUN',
                historical_tradeability_gate='NOT_RUN',world_gate='NOT_RUN',scoring_gate='CLOSED')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True)
    parser.add_argument('--head',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();report=verify(args.tag,args.head)
    Path(args.out).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('ETF_SOURCE_BYTES_VERIFIED',len(report['records']),report['stock_cutoff'],flush=True)


if __name__=='__main__':main()
